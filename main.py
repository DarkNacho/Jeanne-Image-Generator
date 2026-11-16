#!/usr/bin/env python3
"""
Orquestador Principal - Pipeline de Generación ComfyUI (Jeanne Alter)
Punto de entrada de la aplicación modular.
"""

import sys
import random
from typing import List, Dict, Any

from src.cli import parse_arguments
from src.database import PipelineDatabase
from src.assembler import PromptAssembler
from src.workflow import ComfyUIWorkflowBuilder
from src.client import ComfyUIClient
from src.formatters import OutputFormatter


def main():
    args = parse_arguments()
    is_json = (args.format == "json")

    def log(msg: str):
        if is_json:
            sys.stderr.write(msg + "\n")
        else:
            print(msg)

    log("=" * 70)
    log("  DIRECTOR DE FOTOGRAFÍA - PIPELINE DE GENERACIÓN COMFYUI")
    log("  Personaje: Jeanne d'Arc Alter (Fate)")
    log("=" * 70)

    # 1. Base de Datos Relacional
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

    # 2. Compilar Tomas
    assembled_shots: List[Dict[str, Any]] = []

    if args.mode == "shot":
        if not db.shots:
            log("[!] No hay tomas en el guion para procesar.")
            sys.exit(1)

        target_ids = [s.strip() for s in args.shot_id.split(",")] if args.shot_id != "all" else None
        for row in db.shots:
            t_id = row.get("Toma_ID", "").strip()
            if target_ids and t_id not in target_ids:
                continue
            assembled_shots.append(assembler.assemble_shot(row))

        log(f"[+] Modo Guionado: {len(assembled_shots)} tomas compiladas.\n")

    elif args.mode == "random":
        log(f"[+] Modo Creativo (Random): Generando {args.count} variaciones válidas...\n")
        log(f"    Sesgo erotico: {args.erotica:.1f} (1.0=100% sexy, 0.5=50/50, 0.0=100% normal)")
        for i in range(1, args.count + 1):
            assembled_shots.append(
                assembler.generate_random_shot(
                    iteration_idx=i,
                    outfit_id=args.outfit,
                    pose_path=args.pose_path,
                    luz_id=args.luz,
                    erotica_bias=args.erotica
                )
            )

    # 3. Construir Grafo y Renderizar Salida
    batch_payloads = []

    for idx, shot in enumerate(assembled_shots, 1):
        meta = shot["meta"]
        toma_id = meta.get("Toma_ID", f"SHOT-{idx:02d}")
        shot_seed = args.seed if args.seed is not None else random.randint(1, 1125899906842624)

        graph = wf_builder.build_prompt_graph(
            positive_prompt=shot["positive_prompt"],
            negative_prompt=shot["negative_prompt"],
            lora_strength=shot["lora_strength"],
            seed=shot_seed,
            filename_prefix=f"JAlter_{toma_id}"
        )

        batch_item = {
            "toma_id": toma_id,
            "meta": meta,
            "secuencia": shot["sequence_ids"],
            "lora_strength": shot["lora_strength"],
            "seed": shot_seed,
            "positive_prompt": shot["positive_prompt"],
            "negative_prompt": shot["negative_prompt"],
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

        if not is_json:
            OutputFormatter.print_terminal_shot(shot, args, shot_seed)

        if can_queue:
            log(f"--> Encolando {toma_id} en ComfyUI API...")
            p_id = client.queue_prompt(graph)
            if p_id:
                log(f"    OK (Prompt ID: {p_id})")
            else:
                log("    FALLÓ el envío.")

    # 4. Formato JSON en Consola
    if is_json:
        OutputFormatter.print_json(batch_payloads, args)

    # 5. Persistencia Condicional en Disco
    if args.save_json:
        OutputFormatter.save_to_disk(batch_payloads, args, args.output_dir)
        log(f"[✔] Archivos guardados en: {args.output_dir}")
    else:
        log("[i] Modo sin guardado en disco activo (use --save-json para exportar archivos).")


if __name__ == "__main__":
    main()
