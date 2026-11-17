"""
Módulo: src/database.py
Responsabilidad: Lectura y gestión relacional de los archivos CSV (Diccionario Maestro y Guion de Tomas).
"""

import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any


class PipelineDatabase:
    """Carga y gestiona las tablas relacionales del pipeline desde archivos CSV."""

    def __init__(self, master_csv: str = "tablas_pipeline_jeanne_alter.csv",
                 shots_csv: str = "escenas_sesion_jeanne_alter.csv"):
        self.master_csv = self._resolve_path(master_csv, ["tablas_pipeline_jeanne_alter.csv"])
        self.shots_csv = self._resolve_path(shots_csv, ["escenas_sesion_jeanne_alter.csv"])

        self.dictionary: Dict[str, Dict[str, Any]] = {}
        self.by_category: Dict[str, List[Dict[str, Any]]] = {}
        self.shots: List[Dict[str, Any]] = []

        self._load_master_dictionary()
        self._load_shots()

    def _resolve_path(self, user_path: str, fallbacks: List[str]) -> Path:
        """Resuelve la ruta del archivo verificando existencia o probando alternativas."""
        p = Path(user_path)
        if p.exists():
            return p
        for fb in fallbacks:
            candidate = Path(fb)
            if candidate.exists():
                return candidate
        return p

    def _load_master_dictionary(self) -> None:
        """Lee el CSV del Diccionario Maestro y mapea los bloques atómicos por ID y Categoría."""
        if not self.master_csv.exists():
            raise FileNotFoundError(f"No se encontró el Diccionario Maestro en: {self.master_csv}")

        with open(self.master_csv, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for line_num, row in enumerate(reader, start=2):
                # Detectar líneas vacías o corruptas
                if not any(row.values()):
                    continue

                if None in row:
                    sys.stderr.write(
                        f"[!] ADVERTENCIA: Línea {line_num} en '{self.master_csv.name}' tiene más columnas "
                        f"de las esperadas (posible coma sin comillas). Datos extra: {row[None]}\n"
                    )

                item_id = (row.get("ID") or "").strip()
                cat = (row.get("Categoria") or "").strip()

                if not item_id or not cat:
                    sys.stderr.write(
                        f"[!] ADVERTENCIA: Línea {line_num} en '{self.master_csv.name}' omitida por falta de ID o Categoria.\n"
                    )
                    continue

                pos = row.get("Prompt_Positivo", "").strip()
                neg_extra = row.get("Prompt_Negativo_Extra", "").strip()

                try:
                    lora_str = float(row.get("LoRA_Strength", 0.75) or 0.75)
                except ValueError:
                    lora_str = 0.75

                entry = {
                    "ID": item_id,
                    "Categoria": cat,
                    "Tipo_Bloque": row.get("Tipo_Bloque", "").strip(),
                    "Concepto": row.get("Concepto", "").strip(),
                    "Descripcion_Natural": row.get("Descripcion_Natural", "").strip(),
                    "Prompt_Positivo": pos,
                    "Prompt_Negativo_Extra": neg_extra,
                    "LoRA_Strength": lora_str,
                    "Regla_Uso": row.get("Regla_Uso", "").strip()
                }

                if item_id in self.dictionary:
                    sys.stderr.write(
                        f"[!] ADVERTENCIA: ID duplicado '{item_id}' en '{self.master_csv.name}' (Línea {line_num}). "
                        f"Sobrescribiendo entrada previa.\n"
                    )
                    # Mantener sincronizado by_category reemplazando la entrada existente
                    cat_list = self.by_category.get(cat, [])
                    for idx, existing in enumerate(cat_list):
                        if existing["ID"] == item_id:
                            cat_list[idx] = entry
                            break
                else:
                    self.by_category.setdefault(cat, []).append(entry)

                self.dictionary[item_id] = entry

    def _load_shots(self) -> None:
        """Lee el archivo CSV de escenas con las tomas planificadas."""
        if not self.shots_csv.exists():
            return

        seen_tomas = set()
        with open(self.shots_csv, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for line_num, row in enumerate(reader, start=2):
                if not any(row.values()):
                    continue
                toma_id = (row.get("Toma_ID") or "").strip()
                if not toma_id:
                    continue
                if toma_id in seen_tomas:
                    sys.stderr.write(
                        f"[!] ADVERTENCIA: Toma_ID duplicado '{toma_id}' en '{self.shots_csv.name}' (Línea {line_num}).\n"
                    )
                seen_tomas.add(toma_id)
                self.shots.append(row)

    def get_entry(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Recupera un bloque atómico por su ID."""
        return self.dictionary.get(item_id)

    def get_entries_by_cat(self, cat: str) -> List[Dict[str, Any]]:
        """Recupera la lista de bloques correspondientes a una categoría dada."""
        return self.by_category.get(cat, [])
