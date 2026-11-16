"""
Módulo: src/assembler.py
Responsabilidad: Lógica de ensamblado fotográfico, reglas de exclusión mutua de pose,
capas de vestuario (LoRA Strength dinámico y supresión negativa) y generación aleatoria.
"""

import random
from typing import Dict, List, Optional, Any
from .database import PipelineDatabase


class PromptAssembler:
    """Ensambla prompts positivos y negativos respetando todas las reglas del pipeline."""

    def __init__(self, db: PipelineDatabase):
        self.db = db

    def assemble_from_sequence(self, sequence_ids: List[str], shot_meta: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Ensambla un prompt positivo y negativo a partir de una lista secuencial de IDs.
        Aplica:
        - LoRA_Strength dinámico obtenido de la fila OUTFIT presente en la secuencia.
        - Concatenación de Prompt_Negativo_Extra del OUTFIT sobre NEG-01.
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
                continue

            resolved_blocks.append(entry)

            if entry["Categoria"] == "OUTFIT":
                outfit_entry = entry

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
        neg_final = f"{neg_base}, {neg_extra}" if neg_extra else neg_base
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
        """Ensambla una toma especificada en el CSV de escenas (Modo Guionado)."""
        toma_id = shot_row.get("Toma_ID", "").strip()
        secuencia_raw = shot_row.get("Secuencia_IDs", "").strip()

        if secuencia_raw:
            id_list = [i.strip() for i in secuencia_raw.split("|") if i.strip()]
        else:
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
                             pose_path: str = "random",
                             erotica_bias: float = 1.0) -> Dict[str, Any]:
        """
        Modo Creativo (RANDOM):
        Genera una combinación aleatoria válida respetando la Regla de Pose Única:
        - Camino A (Modular): 1 CAM + 1 POS + 1 ACC
        - Camino B (Completa): 1 POSE_PACK
        
        Parámetro erotica_bias (0.0 - 1.0):
        - 1.0: Solo bloques del CSV sexy (erotico puro)
        - 0.5: 50% CSV normal + 50% CSV sexy
        - 0.0: Solo CSV normal
        """
        seq = ["ID-01"]

        # 1. Outfit
        if outfit_id:
            seq.append(outfit_id)
        else:
            # Elegir outfit con sesgo erotico
            if random.random() < erotica_bias:
                outfits = self.db.get_entries_by_cat("OUTFIT")
                chosen_outfit = random.choice(outfits)
            else:
                # Fallback a outfits del CSV sexy también
                outfits = self.db.get_entries_by_cat("OUTFIT")
                chosen_outfit = random.choice(outfits)
            seq.append(chosen_outfit["ID"])

        # 2. Pose con Exclusión Mutua
        path = pose_path.lower()
        if path == "random":
            path = random.choice(["a", "b"])

        tipo_pose = "Pose_Modular" if path == "a" else "Pose_Completa"

        if path == "a":
            cam = random.choice(self.db.get_entries_by_cat("CAM"))
            pos = random.choice(self.db.get_entries_by_cat("POS"))
            acc = random.choice(self.db.get_entries_by_cat("ACC"))
            seq.extend([cam["ID"], pos["ID"], acc["ID"]])
        else:
            pack = random.choice(self.db.get_entries_by_cat("POSE_PACK"))
            seq.append(pack["ID"])

        # 3. Escena
        seq.append(escena_id)

        # 4. Actuación y Ambiente
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
