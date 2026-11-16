# Pipeline de Generación de Imágenes - Jeanne Alter (ComfyUI)

Sistema de automatización para generar lotes de imágenes continuas y consistentes con modelos LoRA en ComfyUI, simulando una sesión fotográfica real.

---

## 📸 Arquitectura del Sistema

### 1. Base de Datos Relacional (CSV)
* **`tablas_pipeline_jeanne_alter.csv` (Diccionario Maestro):** Bloques atómicos clasificados por categoría (`IDENTIDAD`, `OUTFIT`, `CAM`, `POS`, `ACC`, `POSE_PACK`, `ESCENA`, `EXP`, `MIR`, `LUZ`, `ESTILO`, `NEGATIVE`).
* **`escenas_sesion_jeanne_alter.csv` (Guion de Tomas):** Tomas curadas (`SHOT-XX`) con metadatos y secuencias de IDs resueltas.

### 2. Reglas de Ensamblaje
* **Bloques Fijos:** Toda toma contiene obligatoriamente `IDENTIDAD` (`ID-01`), `OUTFIT` (`OUT-XX`), `ESCENA` (`ESC-01`), `ESTILO` (`EST-01`) y `NEGATIVE` (`NEG-01`).
* **Regla de Vestuario por Capas (`OUTFIT`):**
  * Ajusta dinámicamente `LoRA_Strength` según el outfit (ej. `0.75` con armadura completa vs. `0.60–0.65` sin armadura).
  * Concatena automáticamente `Prompt_Negativo_Extra` para suprimir piezas de armadura o prendas retiradas.
* **Regla de Pose Única (Exclusión Mutua):**
  * **Camino A (`Pose_Modular`):** `1 CAM` + `1 POS` + `1 ACC` (poses neutras de pie combinables).
  * **Camino B (`Pose_Completa` / `POSE_PACK`):** `1 PACK-XX` (bloque cerrado que define encuadre, postura y manos).
* **Actuación y Ambiente (`EXP`, `MIR`, `LUZ`):** Se combinan libremente sobre cualquiera de los dos caminos de pose.

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
