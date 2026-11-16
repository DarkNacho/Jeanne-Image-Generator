# ESTADO DE LA SESIÓN Y CONTEXTO DEL PROYECTO (SESSION HANDOFF)
**Fecha:** 16 de Noviembre de 2026  
**Proyecto:** Pipeline de Generación de Imágenes - Jeanne Alter (Fate) en ComfyUI  
**Objetivo:** Automatización de sesiones fotográficas continuas, consistentes y modulares con modelos LoRA sin necesidad de re-entrenamiento.

---

## 1. Resumen Ejecutivo de lo Realizado

1. **Entorno Local y Dependencias:**
   * Entorno virtual creado en `.venv/` con `requirements.txt` (`requests`, `websocket-client`).
   * Configuración de Git en rama `main`. Remoto vinculado: `https://github.com/DarkNacho/Jeanne-Image-Generator.git`.

2. **Parámetros Técnicos Validados para Pruebas:**
   * **Checkpoint:** `WAI-Nsfw-Illustrious-17.safetensors`
   * **LoRA Exacto:** `jeanne_d_arc_alter_fate.safetensors`
   * **Valores por Defecto:** Steps `15`, CFG `5.0`, Resolución `1024x1024`, Batch Size `1`, Sampler `euler_ancestral`, Scheduler `normal`.

3. **Arquitectura Modular Creada (`src/`):**
   * El código monolítico de `pipeline.py` se desacopló en submódulos de alta cohesión (<120 líneas c/u):
     * `src/database.py`: `PipelineDatabase` para carga e indexación de CSVs.
     * `src/assembler.py`: `PromptAssembler` con lógica de ensamble fotográfico, vestuario por capas y exclusión mutua de pose.
     * `src/workflow.py`: `ComfyUIWorkflowBuilder` construyendo el grafo API de 8 nodos para `/prompt`.
     * `src/client.py`: `ComfyUIClient` para comprobación de servidor y encolado HTTP.
     * `src/formatters.py`: `OutputFormatter` gestionando salida en consola (terminal/JSON), desglose conceptual y guardado condicional.
     * `src/cli.py`: Definición y parseo de argumentos de línea de comandos.
     * `main.py` y `pipeline.py`: Puntos de entrada compatibles.
     * `ARCHITECTURE.md`: Documento maestro de índice, clases, funciones y guía rápida de edición.

4. **Comportamiento de Salida Configurado:**
   * Por defecto `--format terminal`: Imprime prompts listos para copiar y pegar con un clic.
   * `--format json`: Emite el grafo raw en JSON.
   * `--save-json`: Por defecto **NO** se escriben archivos en disco, manteniendo el entorno limpio. Solo guarda si se especifica esta bandera.
   * `-v` / `--verbose`: Muestra el desglose de cada bloque con su `Concepto`, `Descripcion_Natural` e intención fotográfica.

---

## 2. Modificaciones Agregadas por el Usuario a Mano

El usuario incorporó las siguientes novedades en el repositorio:
1. **Nuevo CSV:** `tablas_pipeline_erotico_sexy.csv` con bloques atómicos adicionales y variantes sensuales/eróticas (capas de lencería, ropa interior mínima, vestidos y poses íntimas).
2. **Bandera `--erotica` en CLI:**
   * Argumento en `src/cli.py` (`--erotica <float>`, por defecto `1.0`).
   * Lógica de sesgo erótico conectada en `main.py` y `src/assembler.py` (`erotica_bias`) para ponderar entre outfits clásicos y sensuales.

---

## 3. Discusión en Curso: Auditoría de Poses y la "Opción C"

### El Problema Identificado en los CSVs
Al analizar `tablas_pipeline_jeanne_alter.csv`, se descubrieron solapamientos en `POSE_PACK`:
* `PACK-01`: Tiene `stone steps` (contaminación de escenografía que choca con otras locaciones) y `hands together` (duplica `ACC-05`).
* `PACK-02`: Tiene `shallow depth of field` (duplica el estilo obligatorio `EST-01`).
* `PACK-03` y `PACK-04`: Tienen `wind, hair blowing` (física/clima) y `holding sword` (utilería que contradice atuendos sin armas).

### La Solución Acordada: "Opción C" (Purificación + Micro-control Condicional)
Se acordó avanzar hacia la **Opción C**:
1. **Purificar `POSE_PACK` (Opción A):**
   * Quitar fondos, estilos, viento y utilería de los packs, dejándolos como cinemáticas corporales puras (`sitting, relaxed posture`, `combat stance, athletic stance`, etc.).
2. **Añadir Capa de Micro-Control de Extremidades:**
   * `BRA` (Acción de brazos/manos): Opciones como `arms at sides`, `hand on hip`, `arms crossed`, `hands clasped / on lap`, `leaning back on hands`, o `None / Auto`.
   * `PIE` (Modificador de piernas/stance): Opciones como `crossed legs`, `legs together`, `one knee up`, `wide stance`, o `None / Auto`.
3. **Reglas Condicionales Estrictas:**
   * **Condicional de Encuadre:** Si el plano es Plano Medio o Primer Plano (`CAM-03`, `CAM-04`, `PACK-02`), `PIE` se fuerza automáticamente a `None` (evita deformaciones de torso en retratos).
   * **Condicional de Cinemática:** Si la pose es de locomoción activa (`walking`), `PIE` no puede ser `crossed legs`.
   * **Opcionalidad Nula:** Si `BRA` o `PIE` son `None / Auto`, no se inyecta ningún tag adicional y se permite al generador componer la pose de forma natural y fluida.

---

## 4. Próximos Pasos para la Siguiente Sesión

1. Actualizar `tablas_pipeline_jeanne_alter.csv` (y `tablas_pipeline_erotico_sexy.csv`):
   * Purificar las definiciones de los `POSE_PACK`.
   * Registrar formalmente las nuevas categorías/filas para `PIE` (posturas de piernas) y `BRA` (brazos/manos).
2. Implementar los validadores de reglas condicionales en `src/assembler.py` para asegurar que las combinaciones imposibles se anulen automáticamente.
3. Actualizar `ARCHITECTURE.md` con las nuevas reglas condicionales de extremidades.
