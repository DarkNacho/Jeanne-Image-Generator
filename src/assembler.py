"""
Módulo: src/assembler.py
Responsabilidad: Lógica de ensamblado fotográfico, reglas de exclusión mutua de pose,
capas de vestuario (LoRA Strength dinámico y supresión negativa), validadores de
extremidades PIE/BRA (delegados a LimbRuleEngine) y generación aleatoria.
"""

import random
from typing import Dict, List, Optional, Any
from .database import PipelineDatabase
from .limb_rules import LimbRuleEngine, ROLE_PRIMARY, ROLE_SECONDARY


class PromptAssembler:
    """Ensambla prompts positivos y negativos respetando todas las reglas del pipeline."""

    def __init__(self, db: PipelineDatabase):
        self.db = db
        self.limb_rules = LimbRuleEngine(db)

    def assemble_from_sequence(self, sequence_ids: List[str], shot_meta: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Ensambla un prompt positivo y negativo a partir de una lista secuencial de IDs.
        Aplica:
        - LoRA_Strength dinámico obtenido de la fila OUTFIT presente en la secuencia.
        - Concatenación de Prompt_Negativo_Extra del OUTFIT sobre NEG-01.
        - Reglas de extremidades PIE/BRA (encuadre, cinemática, manos, colisiones).
        """
        pos_parts = []
        outfit_entry = None
        neg_base = ""
        resolved_blocks = []
        missing_ids = []

        for raw_id in sequence_ids:
            clean_id = raw_id.strip()
            if not clean_id:
                continue
            entry = self.db.get_entry(clean_id)
            if entry:
                resolved_blocks.append(entry)
            else:
                missing_ids.append(clean_id)

        resolved_blocks, limb_notes = self.limb_rules.apply(resolved_blocks)
        if missing_ids:
            limb_notes.insert(0, f"IDs no encontrados en el diccionario (ignorados): {', '.join(missing_ids)}.")

        for entry in resolved_blocks:
            if entry["Categoria"] == "OUTFIT":
                outfit_entry = entry

            if entry["Categoria"] == "NEGATIVE":
                neg_base = entry["Prompt_Positivo"]
            else:
                if entry["Prompt_Positivo"]:
                    pos_parts.append(entry["Prompt_Positivo"])

        # Si no hubo NEG en la secuencia, tomar NEG-BASE / NEG-01 por defecto
        if not neg_base:
            neg_entry = self.db.get_entry("NEG-BASE") or self.db.get_entry("NEG-01") or \
                (self.db.get_entries_by_cat("NEGATIVE") or [None])[0]
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
            "sequence_ids": [b["ID"] for b in resolved_blocks],
            "requested_ids": sequence_ids,
            "rule_notes": limb_notes,
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
            for col in ["ID_Identidad", "ID_Outfit", "ID_PosePack",
                        "ID_CAM", "ID_CAMARA", "ID_POS", "ID_POSTURA",
                        "ID_ACC", "ID_GESTO", "ID_PIE", "ID_PIERNAS",
                        "ID_BRA", "ID_MANOS", "ID_Escena", "ID_EXP",
                        "ID_EXPRESION", "ID_MIR", "ID_MIRADA", "ID_LUZ",
                        "ID_Estilo", "ID_Negative"]:
                # Admite varios IDs separados por ';'
                id_list.extend(v.strip() for v in (shot_row.get(col) or "").split(";") if v.strip())

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
                             escena_id: Optional[str] = None,
                             estilo_id: Optional[str] = None,
                             luz_id: Optional[str] = None,
                             pose_path: str = "random",
                             advanced: bool = False) -> Dict[str, Any]:
        """
        Modo Creativo (RANDOM):
        Genera una combinación aleatoria válida respetando la Regla de Pose Única:
        - Camino A (Modular): 1 CAM + 1 POS + 1 ACC
        - Camino B (Completa): 1 POSE_PACK
        """
        id_entry = self.db.get_entry("ID-JEANNE") or self.db.get_entry("ID-01") or \
            (self.db.get_entries_by_cat("IDENTITY") or self.db.get_entries_by_cat("IDENTIDAD") or [None])[0]
        seq = [id_entry["ID"] if id_entry else "ID-JEANNE"]

        # 1. Outfit
        if outfit_id:
            seq.append(outfit_id)
        else:
            seq.append(random.choice(self.db.get_entries_by_cat("OUTFIT"))["ID"])

        # 2. Pose con Exclusión Mutua
        path = pose_path.lower()
        if path == "random":
            path = random.choice(["a", "b"])

        tipo_pose = "Pose_Modular" if path == "a" else "Pose_Completa"

        limb_ids = self._random_limbs() if advanced else []
        has_bra = any(i.startswith("BRA") or i.startswith("MAN-") or i.startswith("HAND-") for i in limb_ids)

        if path == "a":
            cams = self.db.get_entries_by_cat("CAMERA") or self.db.get_entries_by_cat("CAMARA") or self.db.get_entries_by_cat("CAM")
            poses = self.db.get_entries_by_cat("POSTURE") or self.db.get_entries_by_cat("POSTURA") or self.db.get_entries_by_cat("POS")
            cam = random.choice(cams)
            pos = random.choice(poses)
            seq.extend([cam["ID"], pos["ID"]])
            if not has_bra:
                acc_entries = self.db.get_entries_by_cat("GESTURE") or self.db.get_entries_by_cat("GESTO") or self.db.get_entries_by_cat("ACC")
                if acc_entries:
                    seq.append(random.choice(acc_entries)["ID"])
        else:
            pack = random.choice(self.db.get_entries_by_cat("POSE_PACK"))
            seq.append(pack["ID"])

        seq.extend(limb_ids)

        # 3. Escena
        if not escena_id:
            esc_entry = self.db.get_entry("SCENE-CATHEDRAL") or self.db.get_entry("ESC-CATEDRAL") or self.db.get_entry("ESC-01") or \
                (self.db.get_entries_by_cat("SCENE") or self.db.get_entries_by_cat("ESCENA") or [None])[0]
            escena_id = esc_entry["ID"] if esc_entry else "SCENE-CATHEDRAL"
        seq.append(escena_id)

        # 4. Actuación y Ambiente
        exps = self.db.get_entries_by_cat("EXPRESSION") or self.db.get_entries_by_cat("EXPRESION") or self.db.get_entries_by_cat("EXP")
        mirs = self.db.get_entries_by_cat("GAZE") or self.db.get_entries_by_cat("LOOK") or self.db.get_entries_by_cat("MIRADA") or self.db.get_entries_by_cat("MIR")
        seq.extend([random.choice(exps)["ID"], random.choice(mirs)["ID"]])

        if luz_id:
            seq.append(luz_id)
        else:
            luz = random.choice(self.db.get_entries_by_cat("LIGHT") or self.db.get_entries_by_cat("LUZ"))
            seq.append(luz["ID"])

        # 5. Estilo y Negativo
        if not estilo_id:
            est_entry = self.db.get_entry("STYLE-PHOTO") or self.db.get_entry("EST-FOTO") or self.db.get_entry("EST-01") or \
                (self.db.get_entries_by_cat("STYLE") or self.db.get_entries_by_cat("ESTILO") or [None])[0]
            estilo_id = est_entry["ID"] if est_entry else "STYLE-PHOTO"

        neg_entry = self.db.get_entry("NEG-BASE") or self.db.get_entry("NEG-01") or \
            (self.db.get_entries_by_cat("NEGATIVE") or [None])[0]
        neg_id = neg_entry["ID"] if neg_entry else "NEG-BASE"

        seq.extend([estilo_id, neg_id])

        meta = {
            "Toma_ID": f"RANDOM-{iteration_idx:03d}",
            "Bloque_Sesion": "Modo_Creativo",
            "Tipo_Pose": tipo_pose,
            "Descripcion": f"Toma creativa generada aleatoriamente ({tipo_pose})."
        }

        return self.assemble_from_sequence(seq, meta)

    def _random_limbs(self) -> List[str]:
        """Selecciona 0-1 PIE/PIERNA y 0-1 acción de mano (primaria/secundaria) al azar."""
        ids = []
        pies = self.db.get_entries_by_cat("LEGS") or self.db.get_entries_by_cat("PIERNAS") or self.db.get_entries_by_cat("PIE")
        if pies and random.random() < 0.5:
            ids.append(random.choice(pies)["ID"])
        hands_pool = self.db.get_entries_by_cat("HANDS") or self.db.get_entries_by_cat("MANOS") or self.db.get_entries_by_cat("BRA")
        valid_roles = (ROLE_PRIMARY if isinstance(ROLE_PRIMARY, tuple) else (ROLE_PRIMARY,)) + \
                      (ROLE_SECONDARY if isinstance(ROLE_SECONDARY, tuple) else (ROLE_SECONDARY,))
        hands = [b for b in hands_pool if b.get("Tipo_Bloque") in valid_roles]
        if hands and random.random() < 0.6:
            ids.append(random.choice(hands)["ID"])
        return ids
