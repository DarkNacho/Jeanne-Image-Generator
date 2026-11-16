"""
Módulo: src/database.py
Responsabilidad: Lectura y gestión relacional de los archivos CSV (Diccionario Maestro y Guion de Tomas).
"""

import csv
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
            for row in reader:
                item_id = row["ID"].strip()
                cat = row["Categoria"].strip()
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

                self.dictionary[item_id] = entry
                self.by_category.setdefault(cat, []).append(entry)

    def _load_shots(self) -> None:
        """Lee el archivo CSV de escenas con las tomas planificadas."""
        if not self.shots_csv.exists():
            return

        with open(self.shots_csv, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.shots.append(row)

    def get_entry(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Recupera un bloque atómico por su ID."""
        return self.dictionary.get(item_id)

    def get_entries_by_cat(self, cat: str) -> List[Dict[str, Any]]:
        """Recupera la lista de bloques correspondientes a una categoría dada."""
        return self.by_category.get(cat, [])
