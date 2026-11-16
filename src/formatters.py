"""
Módulo: src/formatters.py
Responsabilidad: Formateo de salida a consola (terminal estándar / verbose),
emisión JSON limpia y guardado condicional en disco.
"""

import json
from pathlib import Path
from typing import List, Dict, Any


class OutputFormatter:
    """Gestiona la presentación de resultados en terminal y la persistencia en disco."""

    @staticmethod
    def print_terminal_shot(shot: Dict[str, Any], args: Any, shot_seed: int) -> None:
        """Imprime un bloque de toma listo para copiar y pegar en la terminal."""
        meta = shot["meta"]
        toma_id = meta.get("Toma_ID", "SHOT")
        desc = meta.get("Descripcion", "")
        seq_str = " | ".join(shot["sequence_ids"])
        lora_str = shot["lora_strength"]
        outfit_id = shot.get("outfit_id", "OUTFIT")
        pos_prompt = shot["positive_prompt"]
        neg_prompt = shot["negative_prompt"]

        print("=" * 80)
        print(f"🎬 TOMA: {toma_id} | LoRA: {lora_str} ({outfit_id}) | Seed: {shot_seed} | Steps: {args.steps} | CFG: {args.cfg} | {args.width}x{args.height}")
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
            if outfit_id and any(b["Categoria"] == "OUTFIT" and b["Prompt_Negativo_Extra"] for b in shot["resolved_blocks"]):
                outfit_b = next(b for b in shot["resolved_blocks"] if b["Categoria"] == "OUTFIT")
                print(f"  • [SUPRESIÓN EXTRA NEGATIVA]: {outfit_b['Prompt_Negativo_Extra']}")
            print("-" * 80)

        print("[PROMPT POSITIVO - COPIAR Y PEGAR]:")
        print(pos_prompt)
        print("\n[PROMPT NEGATIVO - COPIAR Y PEGAR]:")
        print(neg_prompt)
        print("=" * 80 + "\n")

    @staticmethod
    def print_json(batch_payloads: List[Dict[str, Any]], args: Any) -> None:
        """Emite el payload JSON directamente en stdout para tuberías o consumo externo."""
        if len(batch_payloads) == 1:
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

    @staticmethod
    def save_to_disk(batch_payloads: List[Dict[str, Any]], args: Any, output_dir: str) -> None:
        """Escribe los archivos JSON individuales, batch consolidado y resumen legible en disco."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        summary_file = out_path / "sesion_prompts_resumen.txt"
        batch_json_file = out_path / "comfyui_batch_payloads.json"

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

                single_file = out_path / f"{toma_id}_comfy_api.json"
                single_data = {"prompt": item["prompt_workflow"]}
                if "desglose_conceptual" in item:
                    single_data["extra_data"] = item["desglose_conceptual"]
                with open(single_file, mode="w", encoding="utf-8") as sf:
                    json.dump(single_data, sf, indent=2, ensure_ascii=False)

        with open(batch_json_file, mode="w", encoding="utf-8") as bf:
            json.dump(batch_payloads, bf, indent=2, ensure_ascii=False)
