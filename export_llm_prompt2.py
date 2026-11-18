#!/usr/bin/env python3
"""
==============================================================================
Script: export_llm_prompt.py
Responsabilidad: Lee los archivos CSV del proyecto (tablas y escenas), unifica los bloques
atómicos, inyecta las reglas de arquitectura y genera automáticamente un archivo
Markdown (.md) completo y actualizado (PROMPT_LLM_DIRECTOR_MODELAJE_EROTICO.md)
listo para copiar y pegar en cualquier LLM de chat o roleplay.

Este script genera la base de conocimiento completa para que el LLM actúe como:
>>> DIRECTOR DE MODELAJE DE SESIONES ERÓTICAS ≪
en lugar de un simple "Director de Fotografía", lo que implica una dirección
creativa completa sobre vestuario, narrativa de la sesión, dirección de poses,
gestos, expresión y narrativa del despojo gradual.
==============================================================================
"""

import csv
import sys
import datetime
from pathlib import Path
from typing import Dict, List, Any

# ----------------------------------------------------------------------------
# Archivos de entrada: Tablas de bloques y Guiones de escenas
# ----------------------------------------------------------------------------
MASTER_CSVS = [
    "tablas_pipeline_jeanne_alter.csv",
    "tablas_pipeline_erotico_sexy.csv"
]

SHOT_CSVS = [
    "escenas_sesion_jeanne_alter.csv",
    "escenas_sesion_avanzada_jeanne.csv"
]

# ----------------------------------------------------------------------------
# Nombre del documento generado actualizado a la nueva terminología profesional
# ----------------------------------------------------------------------------
DEFAULT_OUTPUT_FILE = "PROMPT_LLM_DIRECTOR_MODELAJE_EROTICO.md"

# ----------------------------------------------------------------------------
# Función de soporte: Generación de separadores visuales
# ----------------------------------------------------------------------------
def draw_line(length: int = 68, char: str = "=") -> str:
    return char * length

# ----------------------------------------------------------------------------
# Carga y fusión de diccionarios desde CSV
# ----------------------------------------------------------------------------
def load_and_merge_dictionaries(csv_paths: List[str]) -> Dict[str, Dict[str, str]]:
    """Carga y fusiona los diccionarios CSV deduplicando por ID."""
    merged: Dict[str, Dict[str, str]] = {}
    for path_str in csv_paths:
        p = Path(path_str)
        if not p.exists():
            print(f"  [!] Advertencia: No se encontró {path_str}, saltando.")
            continue
        print(f"  [*] Leyendo {path_str}...")
        with open(p, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                item_id = (row.get("ID") or "").strip()
                if not item_id:
                    continue
                # Si ya existe, nos aseguramos de no sobreescribir con valores vacíos
                if item_id in merged:
                    for k, v in row.items():
                        if v and not merged[item_id].get(k):
                            merged[item_id][k] = v.strip()
                else:
                    merged[item_id] = {k: (v.strip() if v else "") for k, v in row.items()}
    return merged

# ----------------------------------------------------------------------------
# Carga de guiones de escenas
# ----------------------------------------------------------------------------
def load_shot_scripts(csv_paths: List[str]) -> List[Dict[str, str]]:
    """Carga los guiones de escenas (shots) de los archivos CSV."""
    shots: List[Dict[str, str]] = []
    for path_str in csv_paths:
        p = Path(path_str)
        if not p.exists():
            print(f"  [!] Advertencia: No se encontró {path_str}, saltando.")
            continue
        print(f"  [*] Leyendo guion {path_str}...")
        with open(p, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                shot_id = (row.get("SHOT_ID") or "").strip()
                if shot_id:
                    shots.append({k: (v.strip() if v else "") for k, v in row.items()})
    return shots

# ----------------------------------------------------------------------------
# Agrupación por categoría canónica (con normalización)
# ----------------------------------------------------------------------------
def group_by_category(dictionary: Dict[str, Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    """Agrupa los bloques por categoría canónica con normalización de nombres."""
    cat_order = [
        "IDENTITY", "SCENE", "STYLE", "NEGATIVE",
        "OUTFIT", "CAMERA", "POSTURE", "GESTURE", "POSE_PACK",
        "LEGS", "HANDS", "EXPRESSION", "GAZE", "LIGHT"
    ]
    groups: Dict[str, List[Dict[str, str]]] = {cat: [] for cat in cat_order}
    groups["OTROS"] = []

    for item in dictionary.values():
        cat = item.get("Categoria", "").strip().upper()
        
        # Normalizaciones retrocompatibles para soportar variantes en el CSV
        if cat in ("CAMARA", "CAM"):
            cat = "CAMERA"
        elif cat in ("POSTURA", "POS"):
            cat = "POSTURE"
        elif cat in ("GESTO", "ACC"):
            cat = "GESTURE"
        elif cat in ("PIERNAS", "PIE"):
            cat = "LEGS"
        elif cat in ("MANOS", "BRA"):
            cat = "HANDS"
        elif cat in ("EXPRESION", "EXP"):
            cat = "EXPRESSION"
        elif cat in ("MIRADA", "MIR", "LOOK"):
            cat = "GAZE"
        elif cat in ("LUZ",):
            cat = "LIGHT"
        elif cat in ("IDENTIDAD",):
            cat = "IDENTITY"
        elif cat in ("ESCENA",):
            cat = "SCENE"
        elif cat in ("ESTILO",):
            cat = "STYLE"

        if cat in groups:
            groups[cat].append(item)
        else:
            groups["OTROS"].append(item)

    return groups

# ----------------------------------------------------------------------------
# Generador de tablas Markdown
# ----------------------------------------------------------------------------
def format_table_general(items: List[Dict[str, str]], columns: List[str], headers: List[str]) -> str:
    """Genera una tabla Markdown para una lista de bloques con tratamiento de caracteres."""
    if not items:
        return "*(Sin elementos)*\n"
    
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join([":---" for _ in headers]) + " |"
    ]
    for it in items:
        row_vals = []
        for col in columns:
            val = it.get(col, "").replace("\n", " ").replace("|", "\\|")
            row_vals.append(val)
        lines.append("| " + " | ".join(row_vals) + " |")
    
    return "\n".join(lines) + "\n"

# ----------------------------------------------------------------------------
# Función para generar el encabezado del prompt maestro
# ----------------------------------------------------------------------------
def generate_markdown_header() -> str:
    """Genera el encabezado profesional del prompt para el LLM."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    return f"""# 🎬 DIRECTOR DE MODELAJE: SESIÓN FOTOGRÁFICA ERÓTICA

{draw_line(70, "=")}
╔══════════════════════════════════════════════════════════════╗
║        DIRECTOR DE MODELAJE ERÓTICO — Sistema Maestro       ║
║        Generado el: {now}                            ║
╚══════════════════════════════════════════════════════════════╝
{draw_line(70, "=")}

## 🎭 ROL DEL LLM

Actúa como el **Director de Modelaje Creativo** para una sesión fotográfica de modelaje erótico de la serie de personajes **Fate/Grand Order** (específicamente **Jeanne d'Arc Alter**).

Tu función es recibir un guion de tomas (shots) y generar **prompts de imagen (positivos y negativos)** optimizados para el modelo **Illustrious-XL** en ComfyUI.

### Tus responsabilidades:
1. 👗 **Dirección de vestuario**: Controlar qué prendas tiene el modelo en cada toma.
2. 📸 **Dirección de poses**: Generar poses coherentes con la narrativa.
3. 🎭 **Dirección de expresión**: Controlar la mirada, labios y rostro según la toma.
4. 🔥 **Narrativa de desnudez**: Gestionar el despojo gradual de ropa con coherencia.
5. ✨ **Calidad visual**: Generar prompts de alta calidad cinematográfica.

---

"""

# ----------------------------------------------------------------------------
# Generador de las secciones de reglas y protocolos
# ----------------------------------------------------------------------------
def generate_rules_section() -> str:
    """Genera la sección de reglas y protocolos del sistema."""
    return """## 🛠 REGLAS Y PROTOCOLOS DE OPERACIÓN

{draw_line(70, "=")}

### 1. Protocolo de Generación de Prompts
Para cada toma solicitada, debes producir:

```
╔══════════════════════════════════════════════════════════╗
║         ┌─ PROMPT POSITIVO                             ║
╚══════════════════════════════════════════════════════════╝
(aquí el prompt positivo estructurado)

╔══════════════════════════════════════════════════════════╗
║         ┌─ PROMPT NEGATIVO                            ║
╚══════════════════════════════════════════════════════════╝
(aquí el prompt negativo estructurado)
```

### 2. Reglas de Dirección de Modelaje

- 👗 **Vestuario**: El modelo debe llevar las prendas especificadas por el bloque OUTFIT.
- 👙 **Lencería**: Si el outfit es de lencería, mantén el brasier y panties visibles.
- 🖐️ **Manos**: Si hay interacción manual, detalla la posición de los dedos y el contacto.
- 👁️ **Mirada**: Dirige la mirada según el bloque GAZE o la toma.
- 💋 **Labios**: Controla labios entreabiertos para tomas eróticas.

### 3. Protocolo de Despojo Gradual (Stripping Sequence)
Cuando la sesión sigue una secuencia de desnudez:
1. Cada toma debe ser coherente con la anterior en vestuario.
2. La ropa se quita paso a paso: Armadura → Ropa civil → Top/Camisa → Panties/Panties abierta → Desnudez.
3. Las expresiones de placer o deseo deben aumentar gradualmente.

{draw_line(70, "=")}
"""

# ----------------------------------------------------------------------------
# Función principal que genera el documento completo
# ----------------------------------------------------------------------------
def generate_markdown_content(dictionary: Dict[str, Dict[str, str]], shots: List[Dict[str, str]]) -> str:
    """Construye el documento Markdown maestro con todo el contexto unificado."""
    groups = group_by_category(dictionary)
    
    content = []
    
    # 1. Encabezado
    content.append(generate_markdown_header())
    
    # 2. Reglas
    content.append(generate_rules_section())
    
    # 3. Diccionarios por categoría
    content.append(f"{draw_line(70, '=')}")
    content.append("## 📚 BLOQUES ATÓMICOS (DICCIONARIOS)")
    content.append(f"{draw_line(70, '=')}")
    
    # Identidad (Fijo)
    content.append("\n### 🎭 BLOQUES DE IDENTIDAD (Fijos)")
    content.append(format_table_general(
        groups["IDENTITY"], 
        ["ID", "Concepto", "Descripción_Natural"], 
        ["ID", "Concepto", "Descripción_Natural"]
    ))
    
    # Escenas (Fijo)
    content.append("\n### 🖼 BLOQUES DE ESCENA")
    content.append(format_table_general(
        groups["SCENE"], 
        ["ID", "Concepto", "Descripción_Natural"], 
        ["ID", "Concepto", "Descripción_Natural"]
    ))
    
    # Estilos (Fijo)
    content.append("\n### 🎨 BLOQUES DE ESTILO")
    content.append(format_table_general(
        groups["STYLE"], 
        ["ID", "Concepto", "Descripción_Natural"], 
        ["ID", "Concepto", "Descripción_Natural"]
    ))
    
    # Negativos (Fijo)
    content.append("\n### 🚫 BLOQUES NEGATIVOS")
    content.append(format_table_general(
        groups["NEGATIVE"], 
        ["ID", "Concepto", "Descripción_Natural"], 
        ["ID", "Concepto", "Descripción_Natural"]
    ))
    
    # Outfit
    content.append("\n### 👗 BLOQUES DE VESTUARIO (OUTFIT)")
    content.append(format_table_general(
        groups["OUTFIT"], 
        ["ID", "Concepto", "Prompt_Positivo", "LoRA_Strength"], 
        ["ID", "Concepto", "Prompt Positivo", "LoRA"]
    ))
    
    # Cámara
    content.append("\n### 📸 BLOQUES DE CÁMARA")
    content.append(format_table_general(
        groups["CAMERA"], 
        ["ID", "Concepto", "Prompt_Positivo", "Regla_Uso"], 
        ["ID", "Concepto", "Prompt", "Regla"]
    ))
    
    # Postura
    content.append("\n### 🧘 BLOQUES DE POSTURA")
    content.append(format_table_general(
        groups["POSTURE"], 
        ["ID", "Concepto", "Prompt_Positivo", "Regla_Uso"], 
        ["ID", "Concepto", "Prompt", "Regla"]
    ))
    
    # Gesto
    content.append("\n### 🎭 BLOQUES DE GESTOS")
    content.append(format_table_general(
        groups["GESTURE"], 
        ["ID", "Concepto", "Prompt_Positivo", "Regla_Uso"], 
        ["ID", "Concepto", "Prompt", "Regla"]
    ))
    
    # Pose Pack
    content.append("\n### 🎲 BLOQUES DE POSE PACK")
    content.append(format_table_general(
        groups["POSE_PACK"], 
        ["ID", "Concepto", "Prompt_Positivo"], 
        ["ID", "Concepto", "Prompt"]
    ))
    
    # Piernas
    content.append("\n### 🦵 BLOQUES DE PIERNAS")
    content.append(format_table_general(
        groups["LEGS"], 
        ["ID", "Concepto", "Prompt_Positivo", "Regla_Uso"], 
        ["ID", "Concepto", "Prompt", "Regla"]
    ))
    
    # Manos
    content.append("\n### 🖐 BLOQUES DE MANOS")
    content.append(format_table_general(
        groups["HANDS"], 
        ["ID", "Concepto", "Prompt_Positivo", "Regla_Uso"], 
        ["ID", "Concepto", "Prompt", "Regla"]
    ))
    
    # Expresión
    content.append("\n### 🎭 BLOQUES DE EXPRESIÓN")
    content.append(format_table_general(
        groups["EXPRESSION"], 
        ["ID", "Concepto", "Prompt_Positivo"], 
        ["ID", "Concepto", "Prompt"]
    ))
    
    # Mirada
    content.append("\n### 👁 BLOQUES DE MIRADA")
    content.append(format_table_general(
        groups["GAZE"], 
        ["ID", "Concepto", "Prompt_Positivo"], 
        ["ID", "Concepto", "Prompt"]
    ))
    
    # Luz
    content.append("\n### 💡 BLOQUES DE LUZ")
    content.append(format_table_general(
        groups["LIGHT"], 
        ["ID", "Concepto", "Prompt_Positivo", "Regla_Uso"], 
        ["ID", "Concepto", "Prompt", "Regla"]
    ))
    
    # Otros
    if groups["OTROS"]:
        content.append("\n### ➕ BLOQUES ADICIONALES")
        content.append(format_table_general(
            groups["OTROS"], 
            ["ID", "Concepto", "Prompt_Positivo"], 
            ["ID", "Concepto", "Prompt"]
        ))
    
    # 4. Guiones de escenas
    content.append(f"\n{draw_line(70, '=')}")
    content.append("## 📜 GUIONES DE ESCENAS CARGADOS")
    content.append(f"{draw_line(70, '=')}")
    
    if not shots:
        content.append("\n*(No se cargaron guiones de escenas. El documento mostrará solo los bloques atómicos.)*\n")
    else:
        content.append(f"\nSe han cargado **{len(shots)} tomas** de guion.\n")
        
        # Mostrar resumen de guion
        for shot in shots:
            shot_id = shot.get("SHOT_ID", "UNKNOWN")
            outfit = shot.get("OUTFIT", "Sin definir")
            pose = shot.get("POSTURE", "Sin definir")
            gesture = shot.get("GESTURE", "Sin definir")
            expression = shot.get("EXPRESSION", "Sin definir")
            content.append(f"- **{shot_id}** | 👗 {outfit} | 🧘 {pose} | 🎭 {gesture} | 😀 {expression}")
        
    # 5. Reglas de ComfyUI
    content.append(f"\n{draw_line(70, '=')}")
    content.append("## 🔧 REGLAS PARA COMFYUI / SDXL")
    content.append(f"{draw_line(70, '=')}")
    
    content.append("""
- El modelo debe ser **Illustrious-XL**
- Usar el LoRA de Jeanne d'Arc Alter con fuerza base de **0.75**
- Mantener los tags de la cámara en el prefijo de cada prompt
- Combinar correctamente los bloques según el guion
- Respetar el orden de las capas de ropa (Outfit → Cámara → Postura → Gesto)
""")
    
    # 6. Ejemplo de salida esperada
    content.append(f"\n{draw_line(70, '=')}")
    content.append("## 📋 EJEMPLO DE SALIDA ESPERADA")
    content.append(f"{draw_line(70, '=')}")
    
    content.append("""
```
╔══════════════════════════════════════════════════════════╗
║         ┌─ PROMPT POSITIVO                             ║
╚══════════════════════════════════════════════════════════╝
(Aquí el prompt positivo construido por el LLM según la toma)

╔══════════════════════════════════════════════════════════╗
║         ┌─ PROMPT NEGATIVO                            ║
╚══════════════════════════════════════════════════════════╝
(Aquí el prompt negativo construido por el LLM según la toma)
```
""")
    
    content.append(f"\n{draw_line(70, '=')}")
    content.append("## ✅ INSTRUCCIÓN DE INICIO")
    content.append(f"{draw_line(70, '=')}")
    
    content.append("""
Copia todo este documento y pégalo en el LLM. Una vez que lo haya leído, envíale tu guion de escenas y dile:

> "Soy el Director de Modelaje. Mi guion es este: [PEGA AQUÍ TU GUION]. Genera cada toma siguiendo los protocolos especificados."

Y el LLM trabajará como tu **Director de Modelaje de Sesiones Eróticas**.
""")
    
    return "\n".join(content)

# ----------------------------------------------------------------------------
# Función principal
# ----------------------------------------------------------------------------
def main():
    """Punto de entrada principal del script."""
    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║  EXPORTADOR DE PROMPTS PARA LLM                         ║
    ║  DIRECTOR DE MODELAJE ERÓTICO                           ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Carga de diccionarios
    print(f"  [*] Cargando tablas de bloques...")
    dictionary = load_and_merge_dictionaries(MASTER_CSVS)
    
    if not dictionary:
        print(f"  [!] Error: No se encontraron datos en los CSV. Asegúrate de que existan:")
        print(f"      - {MASTER_CSVS[0]}")
        print(f"      - {MASTER_CSVS[1]}")
        return
    
    print(f"  [*] {len(dictionary)} bloques totales cargados.")
    
    # Carga de guiones
    print(f"  [*] Cargando guiones de escenas...")
    shots = load_shot_scripts(SHOT_CSVS)
    
    if shots:
        print(f"  [*] {len(shots)} tomas de guion cargadas.")
    else:
        print(f"  [*] Sin guiones cargados (solo bloques atómicos).")
    
    # Generación del documento
    print(f"  [*] Generando documento:")
    print(f"      → {DEFAULT_OUTPUT_FILE}")
    
    markdown_content = generate_markdown_content(dictionary, shots)
    
    # Escritura del archivo
    with open(DEFAULT_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    print(f"  [*] ¡Hecho!")
    print(f"  [*] Documento generado: {DEFAULT_OUTPUT_FILE}")
    print(f"  [*] Título del sistema: DIRECTOR DE MODELAJE ≪")
    print(f"  [+] Copia el contenido de '{DEFAULT_OUTPUT_FILE}' y pégalo en tu LLM.")
    print(f"  [+] El LLM actuará como DIRECTOR DE MODELAJE para tus sesiones.")
    
    # Resumen final
    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║         RESUMEN DE LA SESIÓN                          ║
    ╠══════════════════════════════════════════════════════════╣
    ║  Bloques cargados:  {len(dictionary)}                         ║
    ║  Guiones cargados:  {len(shots)}                         ║
    ║  Documento generado: {DEFAULT_OUTPUT_FILE}                    ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    if shots:
        print(f"  [!] No olvides copiar la primera tanda de tomas para empezar la sesión.")

if __name__ == "__main__":
    main()
