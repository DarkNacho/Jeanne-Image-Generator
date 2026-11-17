# Pipeline de Generación de Imágenes - Jeanne Alter (ComfyUI)

Sistema de automatización para generar lotes de imágenes continuas y consistentes con modelos LoRA en ComfyUI, simulando una sesión fotográfica real.

---

## 📸 Arquitectura del Sistema

### 1. Base de Datos Relacional (CSV)
* **`tablas_pipeline_jeanne_alter.csv` / `tablas_pipeline_erotico_sexy.csv` (Diccionario Maestro):** Bloques atómicos con IDs nemotécnicos legibles (`ID-JEANNE`, `OUT-LINGERIE`, `CAM-FULL`, `POS-RELAXED`, `HAND-HIP`, `LEG-CROSSED`, etc.) clasificados por categoría funcional (`IDENTITY`, `OUTFIT`, `CAMERA`, `POSTURE`, `GESTURE`, `POSE_PACK`, `LEGS`, `HANDS`, `SCENE`, `EXPRESSION`, `GAZE`, `LIGHT`, `STYLE`, `NEGATIVE`).
* **`escenas_sesion_jeanne_alter.csv` / `escenas_sesion_avanzada_jeanne.csv` (Guion de Tomas):** Tomas curadas (`SHOT-XX` y `ADV-XX`) con secuencias nemotécnicas resueltas.

### 2. Reglas de Ensamblaje
* **Bloques Fijos:** Toda toma contiene obligatoriamente `IDENTITY` (`ID-JEANNE`), `OUTFIT` (`OUT-XXX`), `SCENE` (`SCENE-CATHEDRAL`), `STYLE` (`STYLE-PHOTO`) y `NEGATIVE` (`NEG-BASE`).
* **Regla de Vestuario por Capas (`OUTFIT`):**
  * Ajusta dinámicamente `LoRA_Strength` según el outfit (ej. `0.75` con armadura completa vs. `0.60–0.65` sin armadura o lencería).
  * Concatena automáticamente `Prompt_Negativo_Extra` para suprimir piezas de armadura o prendas retiradas.
* **Regla de Pose Única (Exclusión Mutua):**
  * **Camino A (`Modular_Pose`):** `1 CAMERA` + `1 POSTURE` + `1 GESTURE` (o micro-control con `HANDS`/`LEGS`).
  * **Camino B (`Full_Pose` / `POSE_PACK`):** `1 PACK-XXX` (bloque cerrado que define encuadre, postura y manos).
* **Actuación y Ambiente (`EXPRESSION`, `GAZE`, `LIGHT`):** Se combinan libremente sobre cualquiera de los dos caminos de pose.

### 2.1. Asistente Creativo para otros LLMs
* **[`PROMPT_LLM_DIRECTOR_FOTOGRAFIA.md`](PROMPT_LLM_DIRECTOR_FOTOGRAFIA.md):** Archivo maestro autocontenido para copiar y pegar en ChatGPT, Claude o cualquier LLM sin agente, permitiéndole entender toda la arquitectura y reglas para proponer nuevas tomas válidas.

### 3. Parámetros Técnicos (ComfyUI)
* **Checkpoint:** `WAI-Nsfw-Illustrious-17.safetensors`
* **LoRA:** `jeanne_d_arc_alter_fate.safetensors`
* **Configuración por defecto:** `Steps: 15`, `CFG: 5.0`, `Sampler: euler_ancestral`, `Scheduler: normal`, `Resolución: 1024x1024`, `Batch: 1`.

---

## 🚀 Instalación

```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
```

---

## 🛠️ Modos de Uso

### 1. Salida en Terminal lista para copiar y pegar (Por Defecto)
```bash
# Ejecutar toma específica
python pipeline.py --mode shot --shot-id SHOT-01

# Ejecutar con desglose fotográfico y conceptual (Verbose)
python pipeline.py --mode shot --shot-id SHOT-07 -v

# Modo Creativo (Random - 5 variaciones válidas)
python pipeline.py --mode random --count 5
```

### 2. Salida en Formato JSON (Grafo API ComfyUI)
```bash
python pipeline.py --mode shot --shot-id SHOT-01 --format json
```

### 3. Encolado Directo a la API de ComfyUI
```bash
python pipeline.py --mode shot --shot-id SHOT-01 --queue --server 127.0.0.1:8188
```

### 4. Exportar Archivos a Disco
Por defecto, el pipeline **no escribe archivos en disco** para mantener el espacio limpio. Para exportar los JSONs y el resumen de sesión:
```bash
python pipeline.py --mode shot --save-json --output-dir output_prompts
```

### 5. Generar Prompt Maestro para LLMs de Rol / Chat (ChatGPT, Claude, Gemini)
El pipeline determinista concatena bloques, pero para interpretar **conceptos complejos, poéticos o inéditos**, puedes usar un LLM externo como Director de Fotografía.

El script `export_llm_prompt.py` fusiona automáticamente los diccionarios CSV, sincroniza los 88 bloques atómicos, inyecta las reglas anatómicas y genera el archivo maestro listo para usar:

```bash
# Opción A: Mediante el script dedicado
python export_llm_prompt.py

# Opción B: Mediante bandera en el pipeline
python pipeline.py --export-llm
```

#### Flujo de Trabajo con el LLM:
1. **Ejecuta el exportador:** Se genera/actualiza el archivo [`PROMPT_LLM_DIRECTOR_FOTOGRAFIA.md`](PROMPT_LLM_DIRECTOR_FOTOGRAFIA.md).
2. **Copia y pega:** Pega todo el contenido de ese archivo en tu LLM (ChatGPT, Claude, etc.). El modelo adoptará el rol de Director de Fotografía conociendo todas las reglas y bloques.
3. **Pídele cualquier escena compleja en lenguaje natural:**
   > *"Quiero a Jeanne en lencería sentada en el altar, con una copa de vino en la mano y una expresión melancólica pero seductora en hora azul."*
4. **Respuesta inteligente del LLM:**
   * El LLM interpretará la escena y traducirá los conceptos a tags Danbooru para el LoRA y el modelo *Illustrious-XL*.
   * Si una acción o elemento no existe (ej. la copa de vino), **creará el nuevo bloque atómico** (`HAND-WINE-GLASS`), validará el presupuesto anatómico de 2 manos y te dará la **fila CSV de 9 columnas** lista para agregar a tu base de datos si lo deseas.
   * Te entregará los prompts positivo y negativo compilados listos para copiar directo a ComfyUI.

### 6. Composición Avanzada (Micro-control de extremidades: `LEGS` y `HANDS`)
```bash
# Guion avanzado (ADV-XX + tomas de validación VAL-XX) con las tablas sexy
python pipeline.py --advanced

# Random con modificadores de piernas y manos
python pipeline.py --advanced --mode random --count 5
```
Añadir `--erotica` (o `--erotica 0.5` para mezclar 50/50 en random) cambia la fuente a la tabla sexy.

Los validadores anulan automáticamente las combinaciones imposibles (piernas en planos cerrados, piernas cruzadas al caminar, dos manos con la misma acción sin `HAND-BOTH`, etc.) y lo informan en consola con `⚖️ REGLA:`. Ver detalles en [`ARCHITECTURE.md`](ARCHITECTURE.md) §8.
