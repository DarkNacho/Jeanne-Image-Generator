#!/usr/bin/env python3
"""
Pipeline de Generación de Imágenes - Jeanne Alter
Director de Fotografía & Arquitecto de Pipelines en ComfyUI

Este script implementa:
1. Lectura del Diccionario Maestro y Guion de Tomas (CSVs).
2. Ensamblado estricto con exclusión mutua de poses (Camino A vs Camino B).
3. Regla de capas de vestuario: LoRA_Strength dinámico y concatenación de negativos extra.
4. Modos de ejecución: Guionado (SHOT) y Creativo (RANDOM).
5. Exportación de prompts / workflows en JSON y TXT.
6. Envío directo opcional a la API de ComfyUI (HTTP/WebSocket).
"""

import os
import sys
import csv
import json
import uuid
import random
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Intentar importar librerías opcionales instaladas en el virtualenv
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import websocket
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False


class PipelineDatabase:
    """Carga y gestiona las tablas relacionales del pipeline."""

    def __init__(self, master_csv: str, shots_csv: str):
        self.master_csv = self._resolve_path(master_csv, [
            "tablas_pipeline_jeanne_alter.csv"
        ])
        self.shots_csv = self._resolve_path(shots_csv, [
            "escenas_sesion_jeanne_alter.csv"
        ])

        self.dictionary: Dict[str, Dict[str, Any]] = {}
        self.by_category: Dict[str, List[Dict[str, Any]]] = {}
        self.shots: List[Dict[str, Any]] = []

        self._load_master_dictionary()
        self._load_shots()

    def _resolve_path(self, user_path: str, fallbacks: List[str]) -> Path:
        p = Path(user_path)
        if p.exists():
            return p
        for fb in fallbacks:
            candidate = Path(fb)
            if candidate.exists():
                return candidate
        return p

    def _load_master_dictionary(self):
        if not self.master_csv.exists():
            raise FileNotFoundError(f"No se encontró el Diccionario Maestro en: {self.master_csv}")

        with open(self.master_csv, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                item_id = row["ID"].strip()
                cat = row["Categoria"].strip()
                block_type = row["Tipo_Bloque"].strip()
                concept = row["Concepto"].strip()
                desc = row["Descripcion_Natural"].strip()
                pos = row["Prompt_Positivo"].strip()
                neg_extra = row.get("Prompt_Negativo_Extra", "").strip()

                try:
                    lora_str = float(row.get("LoRA_Strength", 0.75) or 0.75)
                except ValueError:
                    lora_str = 0.75

                entry = {
                    "ID": item_id,
                    "Categoria": cat,
                    "Tipo_Bloque": block_type,
                    "Concepto": concept,
                    "Descripcion_Natural": desc,
                    "Prompt_Positivo": pos,
                    "Prompt_Negativo_Extra": neg_extra,
                    "LoRA_Strength": lora_str,
                    "Regla_Uso": row.get("Regla_Uso", "").strip()
                }

                self.dictionary[item_id] = entry
                self.by_category.setdefault(cat, []).append(entry)

    def _load_shots(self):
        if not self.shots_csv.exists():
            print(f"[!] Aviso: No se encontró archivo de tomas en: {self.shots_csv}")
            return

        with open(self.shots_csv, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.shots.append(row)

    def get_entry(self, item_id: str) -> Optional[Dict[str, Any]]:
        return self.dictionary.get(item_id)

    def get_entries_by_cat(self, cat: str) -> List[Dict[str, Any]]:
        return self.by_category.get(cat, [])


class PromptAssembler:
    """Ensambla prompts positivos y negativos respetando todas las reglas del pipeline."""

    def __init__(self, db: PipelineDatabase):
        self.db = db

    def assemble_from_sequence(self, sequence_ids: List[str], shot_meta: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Ensambla un prompt a partir de una secuencia explícita de IDs.
        Aplica:
        - LoRA strength definido por el outfit en la secuencia.
        - Concatenación de NEG-01 + Prompt_Negativo_Extra del outfit.
        """
        pos_parts = []
        outfit_entry = None
        neg_base = ""
        resolved_blocks = []

        for raw_id in sequence_ids:
            clean_id = raw_id.strip()
            if not clean_id:
                continue

            entry = self.db.get_entry(clean_id)
            if not entry:
                print(f"[!] ID no reconocido en el diccionario: {clean_id}")
                continue

            resolved_blocks.append(entry)

            # Detectar si es el Outfit para extraer LoRA_Strength y negativos extra
            if entry["Categoria"] == "OUTFIT":
                outfit_entry = entry

            # Si es el bloque de negativo base
            if entry["Categoria"] == "NEGATIVE":
                neg_base = entry["Prompt_Positivo"]
            else:
                if entry["Prompt_Positivo"]:
                    pos_parts.append(entry["Prompt_Positivo"])

        # Si no hubo NEG en la secuencia, tomar NEG-01 por defecto
        if not neg_base:
            neg_entry = self.db.get_entry("NEG-01")
            if neg_entry:
                neg_base = neg_entry["Prompt_Positivo"]

        # Determinar LoRA Strength
        lora_strength = outfit_entry["LoRA_Strength"] if outfit_entry else 0.75

        # Concatenar Prompt Negativo
        neg_extra = outfit_entry["Prompt_Negativo_Extra"] if outfit_entry else ""
        if neg_extra:
            neg_final = f"{neg_base}, {neg_extra}"
        else:
            neg_final = neg_base

        pos_final = ", ".join(pos_parts)

        return {
            "meta": shot_meta or {},
            "sequence_ids": sequence_ids,
            "outfit_id": outfit_entry["ID"] if outfit_entry else "UNKNOWN",
            "lora_strength": lora_strength,
            "positive_prompt": pos_final,
            "negative_prompt": neg_final,
            "resolved_blocks": resolved_blocks
        }

    def assemble_shot(self, shot_row: Dict[str, str]) -> Dict[str, Any]:
        """Ensambla una toma especificada en el CSV de escenas."""
        toma_id = shot_row.get("Toma_ID", "").strip()
        secuencia_raw = shot_row.get("Secuencia_IDs", "").strip()

        if secuencia_raw:
            id_list = [i.strip() for i in secuencia_raw.split("|") if i.strip()]
        else:
            # Reconstruir desde columnas individuales si Secuencia_IDs estuviera vacío
            id_list = []
            for col in ["ID_Identidad", "ID_Outfit", "ID_PosePack", "ID_CAM", "ID_POS", "ID_ACC",
                        "ID_Escena", "ID_EXP", "ID_MIR", "ID_LUZ", "ID_Estilo", "ID_Negative"]:
                val = shot_row.get(col, "").strip()
                if val:
                    id_list.append(val)

        meta = {
            "Toma_ID": toma_id,
            "Bloque_Sesion": shot_row.get("Bloque_Sesion", "").strip(),
            "Tipo_Pose": shot_row.get("Tipo_Pose", "").strip(),
            "Descripcion": shot_row.get("Descripcion", "").strip()
        }

        return self.assemble_from_sequence(id_list, meta)

    def generate_random_shot(self,
                             iteration_idx: int = 1,
                             outfit_id: Optional[str] = None,
                             escena_id: str = "ESC-01",
                             estilo_id: str = "EST-01",
                             luz_id: Optional[str] = None,
                             pose_path: str = "random") -> Dict[str, Any]:
        """
        Modo Creativo (RANDOM):
        Genera una combinación válida respetando la Regla de Pose Única (Exclusión Mutua).
        - Camino A: 1 CAM + 1 POS + 1 ACC
        - Camino B: 1 POSE_PACK
        """
        seq = ["ID-01"]

        # 1. Outfit
        if outfit_id:
            seq.append(outfit_id)
        else:
            outfits = self.db.get_entries_by_cat("OUTFIT")
            chosen_outfit = random.choice(outfits)
            seq.append(chosen_outfit["ID"])

        # 2. Pose (Regla de Exclusión Mutua)
        path = pose_path.lower()
        if path == "random":
            path = random.choice(["a", "b"])

        tipo_pose = "Pose_Modular" if path == "a" else "Pose_Completa"

        if path == "a":
            # Camino A: 1 CAM + 1 POS + 1 ACC
            cam = random.choice(self.db.get_entries_by_cat("CAM"))
            pos = random.choice(self.db.get_entries_by_cat("POS"))
            acc = random.choice(self.db.get_entries_by_cat("ACC"))
            seq.extend([cam["ID"], pos["ID"], acc["ID"]])
        else:
            # Camino B: 1 POSE_PACK
            pack = random.choice(self.db.get_entries_by_cat("POSE_PACK"))
            seq.append(pack["ID"])

        # 3. Escena
        seq.append(escena_id)

        # 4. Actuación y Ambiente (EXP, MIR, LUZ)
        exp = random.choice(self.db.get_entries_by_cat("EXP"))
        mir = random.choice(self.db.get_entries_by_cat("MIR"))
        seq.extend([exp["ID"], mir["ID"]])

        if luz_id:
            seq.append(luz_id)
        else:
            luz = random.choice(self.db.get_entries_by_cat("LUZ"))
            seq.append(luz["ID"])

        # 5. Estilo y Negativo
        seq.extend([estilo_id, "NEG-01"])

        meta = {
            "Toma_ID": f"RANDOM-{iteration_idx:03d}",
            "Bloque_Sesion": "Modo_Creativo",
            "Tipo_Pose": tipo_pose,
            "Descripcion": f"Toma creativa generada aleatoriamente ({tipo_pose})."
        }

        return self.assemble_from_sequence(seq, meta)


class ComfyUIWorkflowBuilder:
    """Construye el payload de grafo para la API de ComfyUI."""

    def __init__(self,
                 checkpoint_name: str = "WAI-Nsfw-Illustrious-17.safetensors",
                 lora_name: str = "jeanne_d_arc_alter_fate.safetensors",
                 steps: int = 15,
                 cfg: float = 5.0,
                 sampler_name: str = "euler_ancestral",
                 scheduler: str = "normal",
                 width: int = 1024,
                 height: int = 1024,
                 batch_size: int = 1):
        self.checkpoint_name = checkpoint_name
        self.lora_name = lora_name
        self.steps = steps
        self.cfg = cfg
        self.sampler_name = sampler_name
        self.scheduler = scheduler
        self.width = width
        self.height = height
        self.batch_size = batch_size

    def build_prompt_graph(self,
                           positive_prompt: str,
                           negative_prompt: str,
                           lora_strength: float,
                           seed: Optional[int] = None,
                           filename_prefix: str = "JAlter") -> Dict[str, Any]:
        """Genera el diccionario de nodos estándar para /prompt en ComfyUI."""
        if seed is None:
            seed = random.randint(1, 1125899906842624)

        return {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": self.checkpoint_name
                }
            },
            "2": {
                "class_type": "LoraLoader",
                "inputs": {
                    "lora_name": self.lora_name,
                    "strength_model": round(lora_strength, 2),
                    "strength_clip": round(lora_strength, 2),
                    "model": ["1", 0],
                    "clip": ["1", 1]
                }
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["2", 1],
                    "text": positive_prompt
                }
            },
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["2", 1],
                    "text": negative_prompt
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": self.width,
                    "height": self.height,
                    "batch_size": self.batch_size
                }
            },
            "6": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": self.steps,
                    "cfg": self.cfg,
                    "sampler_name": self.sampler_name,
                    "scheduler": self.scheduler,
                    "denoise": 1.0,
                    "model": ["2", 0],
                    "positive": ["3", 0],
                    "negative": ["4", 0],
                    "latent_image": ["5", 0]
                }
            },
            "7": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["6", 0],
                    "vae": ["1", 2]
                }
            },
            "8": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": filename_prefix,
                    "images": ["7", 0]
                }
            }
        }


class ComfyUIClient:
    """Gestiona la comunicación HTTP y WebSocket con el servidor ComfyUI."""

    def __init__(self, server_address: str = "127.0.0.1:8188"):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())

    def is_server_reachable(self) -> bool:
        url = f"http://{self.server_address}/system_stats"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ComfyUIPipeline/1.0"})
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status == 200
        except Exception:
            return False

    def queue_prompt(self, prompt_graph: Dict[str, Any]) -> Optional[str]:
        """Envía el prompt al endpoint /prompt de ComfyUI."""
        url = f"http://{self.server_address}/prompt"
        payload = json.dumps({"prompt": prompt_graph, "client_id": self.client_id}).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                prompt_id = res_data.get("prompt_id")
                return prompt_id
        except urllib.error.URLError as e:
            print(f"[!] Error conectando con ComfyUI en {url}: {e}")
            return None
        except Exception as e:
            print(f"[!] Error inesperado al enviar prompt: {e}")
            return None


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pipeline Director de Fotografía - Jeanne Alter (ComfyUI Generator)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Modos de Operación
    parser.add_argument("--mode", choices=["shot", "random"], default="shot",
                        help="Modo de ejecución: 'shot' (guionado según CSV) o 'random' (creativo)")
    parser.add_argument("--shot-id", type=str, default="all",
                        help="ID de toma específica (ej. 'SHOT-01' o 'SHOT-01,SHOT-03') o 'all'")
    parser.add_argument("--count", type=int, default=5,
                        help="Número de iteraciones para Modo Creativo (random)")

    # Parámetros ComfyUI (por defecto según especificaciones de prueba)
    parser.add_argument("--steps", type=int, default=15,
                        help="Número de pasos de muestreo (default: 15)")
    parser.add_argument("--width", type=int, default=1024,
                        help="Ancho de imagen en píxeles (default: 1024)")
    parser.add_argument("--height", type=int, default=1024,
                        help="Alto de imagen en píxeles (default: 1024)")
    parser.add_argument("--batch-size", type=int, default=1,
                        help="Tamaño de lote (batch size, default: 1)")
    parser.add_argument("--cfg", type=float, default=5.0,
                        help="Escala CFG (default: 5.0, optimizado para Illustrious)")
    parser.add_argument("--sampler", type=str, default="euler_ancestral",
                        help="Nombre del sampler en ComfyUI")
    parser.add_argument("--scheduler", type=str, default="normal",
                        help="Scheduler de ruido en ComfyUI")
    parser.add_argument("--seed", type=int, default=None,
                        help="Semilla fija (si no se indica, es aleatoria)")

    # Modelos
    parser.add_argument("--checkpoint", type=str, default="WAI-Nsfw-Illustrious-17.safetensors",
                        help="Nombre de archivo del Checkpoint en ComfyUI")
    parser.add_argument("--lora-name", type=str, default="jeanne_d_arc_alter_fate.safetensors",
                        help="Nombre exacto del LoRA en la carpeta de loras de ComfyUI")

    # Servidor y Envíos
    parser.add_argument("--server", type=str, default="127.0.0.1:8188",
                        help="Dirección IP/Host y puerto de ComfyUI")
    parser.add_argument("--queue", action="store_true",
                        help="Enviar los trabajos automáticamente a la cola de ComfyUI vía API")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Modo Verbose: Acompaña cada prompt con el desglose fotográfico de Concepto y Descripción Natural de cada bloque")
    parser.add_argument("--format", choices=["terminal", "json"], default="terminal",
                        help="Formato de salida en la terminal: 'terminal' (prompts listos para copiar/pegar) o 'json' (grafo API ComfyUI)")
    parser.add_argument("--save-json", "--save", dest="save_json", action="store_true", default=False,
                        help="Guarda los archivos JSON y resumen en disco. Por defecto NO guarda archivos (solo salida en terminal)")
    parser.add_argument("--output-dir", type=str, default="output_prompts",
                        help="Directorio donde exportar los archivos generados (solo si se usa --save-json)")

    # Archivos CSV
    parser.add_argument("--master-csv", type=str, default="tablas_pipeline_jeanne_alter.csv",
                        help="Ruta al CSV Diccionario Maestro")
    parser.add_argument("--shots-csv", type=str, default="escenas_sesion_jeanne_alter.csv",
                        help="Ruta al CSV Guion de Escenas")

    # Filtros para Modo Creativo (Random)
    parser.add_argument("--outfit", type=str, default=None,
                        help="Filtro opcional para fijar un Outfit específico en modo random (ej. 'OUT-01B')")
    parser.add_argument("--pose-path", choices=["a", "b", "random"], default="random",
                        help="Camino de pose para modo random: 'a' (modular), 'b' (pack) o 'random'")
    parser.add_argument("--luz", type=str, default=None,
                        help="Filtro opcional para fijar iluminación en modo random (ej. 'LUZ-02')")

    return parser.parse_args()


def main():
    args = parse_arguments()
    is_json_output = (args.format == "json")

    def log(msg: str):
        if is_json_output:
            sys.stderr.write(msg + "\n")
        else:
            print(msg)

    log("=" * 70)
    log("  DIRECTOR DE FOTOGRAFÍA - PIPELINE DE GENERACIÓN COMFYUI")
    log("  Personaje: Jeanne d'Arc Alter (Fate)")
    log("=" * 70)

    # 1. Cargar Base de Datos Relacional
    try:
        db = PipelineDatabase(args.master_csv, args.shots_csv)
        log(f"[+] Diccionario Maestro cargado: {len(db.dictionary)} bloques atómicos.")
        log(f"[+] Guion de Escenas cargado: {len(db.shots)} tomas registradas.")
    except Exception as e:
        log(f"[!] Error al inicializar base de datos: {e}")
        sys.exit(1)

    assembler = PromptAssembler(db)
    wf_builder = ComfyUIWorkflowBuilder(
        checkpoint_name=args.checkpoint,
        lora_name=args.lora_name,
        steps=args.steps,
        cfg=args.cfg,
        sampler_name=args.sampler,
        scheduler=args.scheduler,
        width=args.width,
        height=args.height,
        batch_size=args.batch_size
    )

    client = ComfyUIClient(args.server)
    can_queue = False
    if args.queue:
        if client.is_server_reachable():
            log(f"[+] Servidor ComfyUI detectado online en http://{args.server}")
            can_queue = True
        else:
            log(f"[!] ATENCIÓN: Servidor ComfyUI no responde en http://{args.server}.")

    # 2. Determinar Tomas a Procesar
    assembled_shots: List[Dict[str, Any]] = []

    if args.mode == "shot":
        if not db.shots:
            log("[!] No hay tomas en el archivo de guion para procesar.")
            sys.exit(1)

        target_ids = [s.strip() for s in args.shot_id.split(",")] if args.shot_id != "all" else None

        for row in db.shots:
            t_id = row.get("Toma_ID", "").strip()
            if target_ids and t_id not in target_ids:
                continue
            assembled = assembler.assemble_shot(row)
            assembled_shots.append(assembled)

        log(f"[+] Modo Guionado: {len(assembled_shots)} tomas compiladas.\n")

    elif args.mode == "random":
        log(f"[+] Modo Creativo (Random): Generando {args.count} variaciones válidas...\n")
        for i in range(1, args.count + 1):
            assembled = assembler.generate_random_shot(
                iteration_idx=i,
                outfit_id=args.outfit,
                pose_path=args.pose_path,
                luz_id=args.luz
            )
            assembled_shots.append(assembled)

    # 3. Preparar Payloads y Salida en Terminal
    batch_payloads = []
    output_text_lines = []

    for idx, shot in enumerate(assembled_shots, 1):
        meta = shot["meta"]
        toma_id = meta.get("Toma_ID", f"SHOT-{idx:02d}")
        desc = meta.get("Descripcion", "")
        seq_str = " | ".join(shot["sequence_ids"])
        lora_str = shot["lora_strength"]
        pos_prompt = shot["positive_prompt"]
        neg_prompt = shot["negative_prompt"]

        prefix = f"JAlter_{toma_id}"
        shot_seed = args.seed if args.seed is not None else random.randint(1, 1125899906842624)

        graph = wf_builder.build_prompt_graph(
            positive_prompt=pos_prompt,
            negative_prompt=neg_prompt,
            lora_strength=lora_str,
            seed=shot_seed,
            filename_prefix=prefix
        )

        batch_item = {
            "toma_id": toma_id,
            "meta": meta,
            "secuencia": shot["sequence_ids"],
            "lora_strength": lora_str,
            "seed": shot_seed,
            "positive_prompt": pos_prompt,
            "negative_prompt": neg_prompt,
            "prompt_workflow": graph
        }

        if args.verbose:
            batch_item["desglose_conceptual"] = [
                {
                    "id": b["ID"],
                    "categoria": b["Categoria"],
                    "concepto": b["Concepto"],
                    "descripcion_natural": b["Descripcion_Natural"],
                    "tags_danbooru": b["Prompt_Positivo"]
                }
                for b in shot["resolved_blocks"]
            ]

        batch_payloads.append(batch_item)

        # Si el formato es terminal, construir salida lista para copiar/pegar
        if not is_json_output:
            print("=" * 80)
            print(f"🎬 TOMA: {toma_id} | LoRA: {lora_str} ({shot.get('outfit_id', 'OUTFIT')}) | Seed: {shot_seed} | Steps: {args.steps} | CFG: {args.cfg} | {args.width}x{args.height}")
            if desc:
                print(f"📝 DESCRIPCIÓN: {desc}")
            print(f"🔗 SECUENCIA: {seq_str}")
            print("-" * 80)

            if args.verbose:
                print("📋 DESGLOSE CONCEPTUAL Y FOTOGRÁFICO:")
                for b in shot["resolved_blocks"]:
                    cat = b["Categoria"]
                    cid = b["ID"]
                    concepto = b["Concepto"]
                    descnat = b["Descripcion_Natural"]
                    tags = b["Prompt_Positivo"]
                    print(f"  • [{cid}] ({cat}) {concepto} -> {descnat}")
                    if tags and cat != "NEGATIVE":
                        print(f"    Tags: {tags}")
                if shot.get("outfit_id") and any(b["Categoria"] == "OUTFIT" and b["Prompt_Negativo_Extra"] for b in shot["resolved_blocks"]):
                    outfit_b = next(b for b in shot["resolved_blocks"] if b["Categoria"] == "OUTFIT")
                    print(f"  • [SUPRESIÓN EXTRA NEGATIVA]: {outfit_b['Prompt_Negativo_Extra']}")
                print("-" * 80)

            print("[PROMPT POSITIVO - COPIAR Y PEGAR]:")
            print(pos_prompt)
            print("\n[PROMPT NEGATIVO - COPIAR Y PEGAR]:")
            print(neg_prompt)
            print("=" * 80 + "\n")

        # Encolar en ComfyUI si corresponde
        if can_queue:
            log(f"--> Encolando {toma_id} en ComfyUI API...")
            p_id = client.queue_prompt(graph)
            if p_id:
                log(f"    OK (Prompt ID: {p_id})")
            else:
                log("    FALLÓ el envío a la API.")

    # 4. Salida en formato JSON a la terminal si fue solicitado
    if is_json_output:
        if len(batch_payloads) == 1:
            # Imprimir el payload individual directamente en formato API ComfyUI {"prompt": {...}}
            single_out = {"prompt": batch_payloads[0]["prompt_workflow"]}
            if args.verbose:
                single_out["extra_data"] = {
                    "toma_id": batch_payloads[0]["toma_id"],
                    "meta": batch_payloads[0]["meta"],
                    "desglose_conceptual": batch_payloads[0].get("desglose_conceptual", [])
                }
            print(json.dumps(single_out, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(batch_payloads, indent=2, ensure_ascii=False))

    # 5. Guardar archivos solo si se indicó --save-json
    if args.save_json:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        summary_file = out_dir / "sesion_prompts_resumen.txt"
        batch_json_file = out_dir / "comfyui_batch_payloads.json"

        with open(summary_file, mode="w", encoding="utf-8") as sum_f:
            sum_f.write("RESUMEN DE SESIÓN FOTOGRÁFICA - JEANNE ALTER\n")
            sum_f.write(f"Checkpoint: {args.checkpoint}\n")
            sum_f.write(f"LoRA: {args.lora_name}\n")
            sum_f.write(f"Steps: {args.steps} | CFG: {args.cfg} | Res: {args.width}x{args.height} | Batch: {args.batch_size}\n")
            sum_f.write("=" * 80 + "\n\n")

            for item in batch_payloads:
                toma_id = item["toma_id"]
                desc = item["meta"].get("Descripcion", "")
                seq_str = " | ".join(item["secuencia"])
                lora_str = item["lora_strength"]
                shot_seed = item["seed"]
                pos_prompt = item["positive_prompt"]
                neg_prompt = item["negative_prompt"]

                sum_f.write(f"[{toma_id}] {desc}\n")
                sum_f.write(f"  Secuencia: {seq_str}\n")
                sum_f.write(f"  LoRA Strength: {lora_str}\n")
                sum_f.write(f"  Seed: {shot_seed}\n")
                if "desglose_conceptual" in item:
                    sum_f.write("  DESGLOSE CONCEPTUAL:\n")
                    for d in item["desglose_conceptual"]:
                        sum_f.write(f"    • [{d['id']}] {d['concepto']}: {d['descripcion_natural']}\n")
                sum_f.write(f"  POSITIVE: {pos_prompt}\n")
                sum_f.write(f"  NEGATIVE: {neg_prompt}\n")
                sum_f.write("-" * 80 + "\n\n")

                # Archivo individual ComfyUI API
                single_file = out_dir / f"{toma_id}_comfy_api.json"
                single_data = {"prompt": item["prompt_workflow"]}
                if "desglose_conceptual" in item:
                    single_data["extra_data"] = item["desglose_conceptual"]
                with open(single_file, mode="w", encoding="utf-8") as sf:
                    json.dump(single_data, sf, indent=2, ensure_ascii=False)

        with open(batch_json_file, mode="w", encoding="utf-8") as bf:
            json.dump(batch_payloads, bf, indent=2, ensure_ascii=False)

        log(f"\n[✔] Archivos guardados en disco en: {out_dir.resolve()}")
    else:
        log("\n[i] Modo sin guardado en disco activo (use --save-json para exportar archivos).")


if __name__ == "__main__":
    main()
