# Mapa Arquitectónico del Pipeline (Guía de Referencia Rápida)

Este documento describe la arquitectura modular del proyecto. Su propósito es servir como índice integral para que cualquier desarrollador o agente de IA pueda entender el sistema completo, localizar funciones específicas y modificar componentes sin necesidad de inspeccionar todo el código fuente.

---

## Índice General

1. [Visión General del Sistema](#visión-general-del-sistema)
2. [Diagrama de Flujo Modular](#diagrama-de-flujo-modular)
3. [Estructura del Proyecto y Archivos](#estructura-del-proyecto-y-archivos)
4. [Detalle por Fichero, Clases y Funciones](#detalle-por-fichero-clases-y-funciones)
   * [1. `main.py` & `pipeline.py`](#1-mainpy--pipelinepy)
   * [2. `src/cli.py`](#2-srcclipy)
   * [3. `src/database.py`](#3-srcdatabasepy)
   * [4. `src/assembler.py`](#4-srcassemblerpy)
   * [5. `src/workflow.py`](#5-srcworkflowpy)
   * [6. `src/client.py`](#6-srcclientpy)
   * [7. `src/formatters.py`](#7-srcformatterspy)
   * [8. `src/limb_rules.py`](#8-srclimb_rulespy)
5. [Guía de Navegación Rápida ("Dónde ir si quiero cambiar X")](#guía-de-navegación-rápida)

---

## Visión General del Sistema

El pipeline toma datos relacionales de dos CSVs (un diccionario maestro y un guion de tomas). Con `--advanced` (Composición Avanzada) usa `tablas_pipeline_erotico_sexy.csv` + `escenas_sesion_avanzada_jeanne.csv`; sin la bandera, `tablas_pipeline_jeanne_alter.csv` + `escenas_sesion_jeanne_alter.csv`. Luego aplica reglas estrictas de dirección de fotografía (vestuario por capas, exclusión mutua de pose, ajuste dinámico de LoRA y validadores de extremidades PIE/BRA), y genera prompts listos para copiar/pegar o grafos JSON compatibles con la API de ComfyUI.

```mermaid
flowchart TD
    CLI["src/cli.py (argparse)"] --> Main["main.py (Orquestador)"]
    DB_CSV["CSVs (Diccionario & Guion)"] --> DB["src/database.py (PipelineDatabase)"]
    DB --> Main
    Main --> Asm["src/assembler.py (PromptAssembler)"]
    Asm <--> Limb["src/limb_rules.py (LimbRuleEngine)"]
    Asm --> WF["src/workflow.py (ComfyUIWorkflowBuilder)"]
    WF --> Out["src/formatters.py (OutputFormatter)"]
    WF --> Client["src/client.py (ComfyUIClient)"]
    Out --> Terminal["Consola (Terminal / JSON)"]
    Out -.->|--save-json| Disk["Archivos en Disco (output_prompts/)"]
    Client -.->|--queue| Comfy["ComfyUI Server (127.0.0.1:8188)"]
```

---

## Estructura del Proyecto y Archivos

| Fichero | Líneas | Responsabilidad General |
| :--- | :--- | :--- |
| `main.py` | ~120 | Orquestador principal del ciclo de vida del pipeline. |
| `pipeline.py` | ~10 | Alias de compatibilidad hacia `main.py`. |
| `src/__init__.py` | ~20 | Exportación del paquete modular. |
| `src/cli.py` | ~65 | Configuración y parseo de argumentos de línea de comandos. |
| `src/database.py` | ~85 | Lectura, validación y acceso relacional a los CSVs. |
| `src/assembler.py` | ~200 | Reglas de fotografía: ensamble, capas de ropa, poses y random. |
| `src/limb_rules.py` | ~190 | Validadores de extremidades PIE/BRA: encuadre, cinemática, manos y colisiones de tags. |
| `src/workflow.py` | ~100 | Generador del grafo de nodos JSON para `/prompt` en ComfyUI. |
| `src/client.py` | ~50 | Cliente HTTP para verificar y enviar prompts a ComfyUI. |
| `src/formatters.py` | ~120 | Presentación en terminal, formato JSON y exportación a disco. |
| `tablas_pipeline_jeanne_alter.csv` | - | Diccionario maestro clásico (sin PIE/BRA). |
| `tablas_pipeline_erotico_sexy.csv` | - | Tablas de Composición Avanzada: incluye `PIE`, `BRA`, `CAM-03/04`. |
| `escenas_sesion_jeanne_alter.csv` | - | Guion clásico (`SHOT-XX`). |
| `escenas_sesion_avanzada_jeanne.csv` | - | Guion avanzado (`ADV-XX`) + tomas de validación de reglas (`VAL-01..05`). |
| `README.md` | - | Documentación de usuario y parámetros. |
| `ARCHITECTURE.md` | - | Este mapa arquitectónico. |

---

## Detalle por Fichero, Clases y Funciones

### 1. `main.py` & `pipeline.py`
* **Rol:** Punto de entrada del pipeline. Coordina la lectura, el ensamblaje, la generación de grafos y la salida.
* **Funciones:**
  * `main() -> None`: Orquesta la secuencia completa:
    1. Llama a `parse_arguments()`.
    2. Instancia `PipelineDatabase`.
    3. Conecta con `PromptAssembler` y `ComfyUIWorkflowBuilder`.
    4. Procesa Modo Guionado (`shot`) o Modo Creativo (`random`).
    5. Envía a `OutputFormatter` para imprimir en consola o guardar.
    6. Opcionalmente despacha a `ComfyUIClient` si `--queue` está activo.

---

### 2. `src/cli.py`
* **Rol:** Define la interfaz de línea de comandos (`argparse`).
* **Funciones:**
  * `parse_arguments() -> argparse.Namespace`:
    * `--mode`: `'shot'` (guionado) o `'random'` (creativo).
    * `--shot-id`: Toma específica (ej. `SHOT-01`) o `'all'`.
    * `--count`: Cantidad de iteraciones en modo random.
    * `--steps`, `--width`, `--height`, `--batch-size`, `--cfg`, `--sampler`, `--scheduler`, `--seed`.
    * `--checkpoint`: Checkpoint a cargar (default: `WAI-Nsfw-Illustrious-17.safetensors`).
    * `--lora-name`: Nombre del LoRA (default: `jeanne_d_arc_alter_fate.safetensors`).
    * `--format`: `'terminal'` (por defecto, copiar/pegar) o `'json'` (grafo raw).
    * `--save-json` / `--save`: Booleano para forzar escritura en disco (por defecto `False`).
    * `--output-dir`: Carpeta de destino al guardar.
    * `-v` / `--verbose`: Activa desglose conceptual fotográfico.
    * `--outfit`, `--pose-path`, `--luz`: Filtros opcionales para modo random.
    * `--erotica [p]`: Activa la tabla sexy como fuente de datos (sin valor = `1.0`). Si `--master-csv` no se indica, el maestro pasa a `tablas_pipeline_erotico_sexy.csv`. En modo random, con `0 < p < 1`, `main.py` carga también la tabla clásica y cada toma usa la sexy con probabilidad `p` (un `--outfit` que solo existe en la sexy fuerza esa fuente). `0.0` o sin bandera = tabla clásica. La fuente de cada toma se imprime como `🗂️ FUENTE:`.
    * `--advanced` / `--composicion-avanzada`: Activa Composición Avanzada. Si `--master-csv` / `--shots-csv` no se indican, cambia sus defaults a las tablas sexy y al guion avanzado; en modo random añade PIE/BRA.

---

### 3. `src/database.py`
* **Rol:** Abstracción de datos. Carga los CSVs y provee métodos de consulta rápida indexados por ID y Categoría.
* **Clase:** `PipelineDatabase`
  * `__init__(master_csv, shots_csv)`: Inicializa rutas y estructuras en memoria (`dictionary`, `by_category`, `shots`).
  * `_resolve_path(user_path, fallbacks) -> Path`: Resuelve la ruta del archivo con soporte de nombres alternativos.
  * `_load_master_dictionary() -> None`: Parsea `tablas_pipeline_jeanne_alter.csv`, indexa los 41 bloques atómicos, convierte `LoRA_Strength` a float y agrupa por categoría.
  * `_load_shots() -> None`: Parsea el guion de tomas. El guion avanzado añade columnas `ID_PIE` e `ID_BRA` (varios IDs separados por `;`).
  * `get_entry(item_id: str) -> Optional[Dict]`: Retorna el bloque atómico asociado al ID (ej. `OUT-01A`, `CAM-01`).
  * `get_entries_by_cat(cat: str) -> List[Dict]`: Retorna todos los bloques pertenecientes a una categoría (`OUTFIT`, `CAM`, `POS`, `ACC`, `PIE`, `BRA`, `EXP`, etc.).

---

### 4. `src/assembler.py`
* **Rol:** El "cerebro" fotográfico. Aplica las reglas del Director de Fotografía para generar prompts coherentes.
* **Clase:** `PromptAssembler`
  * `__init__(db: PipelineDatabase)`: Recibe la base de datos para resolver bloques.
  * `assemble_from_sequence(sequence_ids: List[str], shot_meta: Optional[Dict]) -> Dict`:
    * Resuelve cada ID en la secuencia (los IDs inexistentes se reportan en `rule_notes`).
    * Pasa los bloques por `LimbRuleEngine.apply()` (ver sección 8) antes de concatenar.
    * Identifica el bloque `OUTFIT`:
      1. Extrae su `LoRA_Strength` dinámico (`0.75` con armadura, `0.60–0.65` sin armadura).
      2. Si tiene `Prompt_Negativo_Extra`, lo concatena con `NEG-01` para supresión de armadura/piezas metálicas.
    * Concatena en orden los tags Danbooru para el Prompt Positivo.
    * Retorna dict con prompts, metadata, LoRA strength, bloques resueltos, `sequence_ids` (secuencia final tras reglas), `requested_ids` (secuencia pedida) y `rule_notes` (correcciones aplicadas).
  * `assemble_shot(shot_row: Dict[str, str]) -> Dict`:
    * Resuelve una toma del guion leyendo `Secuencia_IDs` (o reconstruyéndola desde columnas ID individuales, incluidas `ID_PIE` / `ID_BRA`).
  * `generate_random_shot(iteration_idx, outfit_id, escena_id, estilo_id, luz_id, pose_path) -> Dict`:
    * **Regla de Pose Única (Exclusión Mutua):**
      * Si Camino A: Selecciona exactamente `1 CAM` + `1 POS` + `1 ACC`.
      * Si Camino B: Selecciona exactamente `1 POSE_PACK` (nunca mezcla con CAM/POS/ACC).
    * Añade libremente actuación (`EXP`), mirada (`MIR`) y luz (`LUZ`).
    * Con `advanced=True`: `_random_limbs()` añade 0–1 `PIE` (50%) y 0–1 acción de mano `BRA` primaria/secundaria (60%). Si hay `BRA`, en Camino A se omite `ACC`.

---

### 5. `src/workflow.py`
* **Rol:** Construye la estructura de grafo requerida por ComfyUI.
* **Clase:** `ComfyUIWorkflowBuilder`
  * `__init__(checkpoint_name, lora_name, steps, cfg, sampler_name, scheduler, width, height, batch_size)`: Almacena parámetros del pipeline.
  * `build_prompt_graph(positive_prompt, negative_prompt, lora_strength, seed, filename_prefix) -> Dict`:
    * Genera el diccionario JSON de 8 nodos estándar:
      * Nodo `1`: `CheckpointLoaderSimple`
      * Nodo `2`: `LoraLoader` (con `strength_model` y `strength_clip` dinámicos)
      * Nodo `3`: `CLIPTextEncode` (Prompt Positivo)
      * Nodo `4`: `CLIPTextEncode` (Prompt Negativo)
      * Nodo `5`: `EmptyLatentImage` (width, height, batch_size)
      * Nodo `6`: `KSampler` (steps, cfg, sampler, scheduler, seed, denoise 1.0)
      * Nodo `7`: `VAEDecode`
      * Nodo `8`: `SaveImage`

---

### 6. `src/client.py`
* **Rol:** Comunicación HTTP / API con ComfyUI.
* **Clase:** `ComfyUIClient`
  * `__init__(server_address: str = "127.0.0.1:8188")`: Guarda la URL del servidor y genera un `client_id` único (UUID).
  * `is_server_reachable() -> bool`: Consulta `http://{server}/system_stats` con timeout corto para verificar si el servidor está en línea.
  * `queue_prompt(prompt_graph: Dict) -> Optional[str]`: Hace POST a `http://{server}/prompt` con el payload JSON. Retorna el `prompt_id` asignado o `None` en caso de fallo.

---

### 7. `src/formatters.py`
* **Rol:** Capa de presentación y persistencia. Separa el formato visual de la lógica del pipeline.
* **Clase:** `OutputFormatter`
  * `print_terminal_shot(shot: Dict, args, shot_seed: int) -> None`:
    * Imprime encabezado con parámetros de cámara y toma.
    * Si `-v` está activo, imprime el desglose de cada bloque (`[ID] Categoria - Concepto -> Intención`).
    * Imprime los bloques `[PROMPT POSITIVO - COPIAR Y PEGAR]` y `[PROMPT NEGATIVO - COPIAR Y PEGAR]`.
  * `print_json(batch_payloads: List[Dict], args) -> None`:
    * Serializa e imprime a `sys.stdout` el JSON compatible con la API de ComfyUI.
  * `save_to_disk(batch_payloads: List[Dict], args, output_dir: str) -> None`:
    * Crea `output_dir` y exporta `sesion_prompts_resumen.txt`, `comfyui_batch_payloads.json` y archivos individuales `<toma_id>_comfy_api.json`.

---

### 8. `src/limb_rules.py`
* **Rol:** Validadores condicionales de extremidades. Opera sobre la lista de bloques resueltos y devuelve `(bloques_corregidos, notas)`. Toda la clasificación es por datos (`Categoria`, `Tipo_Bloque` y tags), no por IDs fijos, así que funciona con cualquier diccionario maestro.
* **Categorías nuevas (en `tablas_pipeline_erotico_sexy.csv`):**

  | ID | Tipo_Bloque | Concepto (clave del plan) | Tags |
  | :--- | :--- | :--- | :--- |
  | `PIE-01` | `Pierna_Apertura` | `legs_open_wide` | `legs apart, wide stance` |
  | `PIE-02` | `Pierna_Perfil` | `profile_lower_view` | `from side, legs in profile, long legs` |
  | `PIE-03` | `Pierna_Enfoque` | `lower_body_focus` | `leg focus, thighs, long legs` |
  | `PIE-04` | `Interaccion_Manual` | `manual_lower_interaction` (ocupa una mano) | `adjusting legwear, hand on own thigh` |
  | `PIE-05` | `Pierna_Cruzada` | Piernas cruzadas | `crossed legs` |
  | `PIE-06` | `Pierna_Juntas` | Piernas juntas | `legs together` |
  | `PIE-07` | `Pierna_Rodilla` | Rodilla elevada | `knee up` |
  | `BRA-01/02` | `Mano_Primaria` | `primary_hand_action` | `hand in own hair` / `adjusting clothes` |
  | `BRA-03/04` | `Mano_Secundaria` | `secondary_hand_action` | `finger to mouth` / `hand on own chest` |
  | `BRA-05/06` | `Mano_Soporte` | `support_hand_pose` | `arm support` / `hand on own hip` |
  | `BRA-07` | `Mano_Libre` | `free_hand_pose` | `arm at side` |
  | `BRA-08` | `Ambas_Manos` | Modificador explícito | `both hands` |

* **Clase:** `LimbRuleEngine`
  * `apply(blocks) -> (blocks, notes)`: Ejecuta en orden:
    1. `_dedupe`: elimina IDs repetidos.
    2. `_rule_framing` (**Encuadre**): si un `CAM`/`POSE_PACK` lleva tags de plano cerrado (`upper body`, `close-up`, `portrait`, `waist up`, `medium shot`, `head and shoulders`, `torso focus`…), se anulan todos los `PIE`.
    3. `_rule_locomotion` (**Cinemática**): si la pose tiene `walking`/`running`/`mid-stride`, se anulan los `PIE` de tipo `Pierna_Cruzada` o con tag `crossed legs`.
    4. `_rule_hands` (**Manos**):
       * **`PIE-04` ocupa la Mano 1** (`_reserve_hand_one`): los `BRA` solo gestionan la Mano 2. Se eliminan `BRA-08` (no quedan dos manos libres) y cualquier `Mano_Primaria` (sería una segunda interacción); en la Mano 2 solo cabe un `BRA` Secundaria/Soporte/Libre.
       * Sin `PIE-04`: solo se conserva la primera `Mano_Primaria`; las demás se eliminan salvo `BRA-08`.
       * Con `BRA-08`: la acción primaria ocupa ambas manos y se eliminan los `BRA` secundarios/soporte/libres.
       * Presupuesto de 2 manos: si se declaran más, se descarta en orden Libre → Soporte → Secundaria.
       * Si hay una acción de interacción y ninguna otra mano declarada, se inserta automáticamente `Mano_Soporte` (pose sentada/inclinada/tumbada/arrodillada) o `Mano_Libre` (resto), tomando la primera fila de ese rol en el CSV.
    5. `_rule_tag_collisions` (**Colisión**): si hay `PIE`, se quitan los tags de piernas (`legs`, `knee`, `wide stance`, `one leg`) de `POS`/`ACC`/`POSE_PACK`/`EXP`; si hay `BRA` (o `PIE-04`), se quitan los de manos (`hand`, `arm`, `fist`, `finger`). Sin `BRA`, si un `EXP` trae tags de manos (`EXP-05`/`EXP-06`), éstos tienen prioridad y se quitan los tags de manos de `POS`/`ACC`/`POSE_PACK`. Un bloque que queda vacío se elimina.
  * Las notas se muestran en terminal como `⚖️ REGLA:` y se guardan en el resumen de disco y en el JSON batch (`rule_notes`).

---

## Guía de Navegación Rápida

| Si necesitas... | Ve directamente a... | Función / Variable a modificar |
| :--- | :--- | :--- |
| **Cambiar cómo se combinan las poses (Camino A vs B)** | `src/assembler.py` | `PromptAssembler.generate_random_shot` |
| **Ajustar el cálculo del LoRA según el outfit** | `src/assembler.py` | `PromptAssembler.assemble_from_sequence` |
| **Modificar qué tags negativos se añaden** | `src/assembler.py` | `PromptAssembler.assemble_from_sequence` |
| **Añadir un nodo nuevo a ComfyUI (ej. FaceDetailer o VAE)** | `src/workflow.py` | `ComfyUIWorkflowBuilder.build_prompt_graph` |
| **Cambiar resolución o steps por defecto** | `src/cli.py` | `parse_arguments` (flags `--steps`, `--width`, etc.) |
| **Cambiar el texto o diseño de la salida en consola** | `src/formatters.py` | `OutputFormatter.print_terminal_shot` |
| **Cambiar cómo se guardan los archivos en disco** | `src/formatters.py` | `OutputFormatter.save_to_disk` |
| **Cambiar endpoint o autenticación de ComfyUI** | `src/client.py` | `ComfyUIClient.queue_prompt` |
| **Añadir columnas o campos nuevos a los CSVs** | `src/database.py` | `PipelineDatabase._load_master_dictionary` |
| **Cambiar qué cuenta como plano cerrado / locomoción** | `src/limb_rules.py` | `CLOSE_FRAMING_TAGS`, `LOCOMOTION_TAGS` |
| **Cambiar la lógica de mano primaria/soporte/libre** | `src/limb_rules.py` | `LimbRuleEngine._rule_hands` |
| **Añadir una pose de piernas o manos** | `tablas_pipeline_erotico_sexy.csv` | Nueva fila `PIE`/`BRA` con su `Tipo_Bloque` |
| **Cambiar la probabilidad de PIE/BRA en random** | `src/assembler.py` | `PromptAssembler._random_limbs` |
