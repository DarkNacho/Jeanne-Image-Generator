# ESTADO DE LA SESIÓN Y CONTEXTO DEL PROYECTO (SESSION HANDOFF)
**Fecha:** 16 de Noviembre de 2026 (actualizado: Composición Avanzada PIE/BRA)  
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

## 3. Opción C implementada: Purificación + Micro-control de Extremidades

### Fase 1 — Datos
* **`POSE_PACK` purificados** (cinemática pura):
  * `tablas_pipeline_jeanne_alter.csv`: se quitaron `stone steps`, `symmetry`, `shallow depth of field`, `wind, hair blowing`, `holding sword`, `dramatic tension`. (Las 4 filas habían quedado con 14 columnas tras la edición manual; se reescribieron a 9.)
  * `tablas_pipeline_erotico_sexy.csv`: se quitaron tags de expresión/mirada/estilo (`thoughtful expression`, `intense direct gaze`, `skin texture`…). Los `POS-01..03` se atomizaron en tags Danbooru simples para poder retirar solo la parte de manos/piernas.
  * `CAM-02` (sexy) usaba `knee up` como "desde las rodillas"; en Danbooru significa levantar la rodilla → se cambió a `cowboy shot`.
* **Nuevas categorías en `tablas_pipeline_erotico_sexy.csv`:** `PIE-01..07`, `BRA-01..08` y `CAM-03` (Plano Entero) / `CAM-04` (Plano Entero Contrapicado). Detalle en `ARCHITECTURE.md` §8.
* **Nuevo guion `escenas_sesion_avanzada_jeanne.csv`:** `ADV-01..05` (tomas de composición) + `VAL-01..05` (una toma por regla, para verificar el validador).

### Fase 2 — Código
* **`src/limb_rules.py` (`LimbRuleEngine`)**, llamado desde `PromptAssembler.assemble_from_sequence`:
  * Encuadre cerrado → `PIE` anulado.
  * Locomoción (`walking`) → `PIE` de piernas cruzadas anulado.
  * Mano primaria → la otra mano se auto-asigna Soporte (sentada) o Libre (de pie). Dos acciones de interacción a la vez solo con `BRA-08` (Ambas manos).
  * `PIE-04` (`manual_lower_interaction`) ocupa la Mano 1: los BRA solo gestionan la Mano 2, y `BRA-08` y las `Mano_Primaria` se eliminan cuando está activo.
  * Colisión de tags: PIE/BRA sustituyen los tags de piernas/manos de `POS`/`ACC`/`POSE_PACK`/`EXP` (EXP-05/06 traen manos). Sin BRA, las manos de EXP tienen prioridad sobre las de la pose.
* **CLI:** `--advanced` / `--composicion-avanzada` (cambia los CSV por defecto y activa PIE/BRA en random).
* **`--erotica [p]` corregida:** cambia el maestro a la tabla sexy; en random con `0 < p < 1` mezcla tablas por toma (verificado: `0.5` → 98/102 sobre 200 tomas). Sin bandera o con `0.0` → tabla clásica.
* **Salida:** cada corrección se muestra como `⚖️ REGLA:` y se guarda en `rule_notes`.

### Decisiones de interpretación (revisar)
* El ejemplo del plan *"manual_lower_interaction + primary_hand_action + support_hand_pose"* declara 3 acciones para 2 manos. Confirmado con el usuario: `PIE-04` es la Mano 1. `ADV-02` usa `PIE-04 + BRA-06`; `VAL-03` reproduce el ejemplo literal (se quita `BRA-01`) y `VAL-05` prueba `PIE-04 + BRA-08` (se quita `BRA-08`).
* El framing se detecta por tags y no por ID, porque `CAM-03` significa "Plano medio" en la tabla clásica y "Plano Entero" en la sexy.

---

## 4. Próximos Pasos

1. Generar las tomas `ADV-XX` en ComfyUI y revisar visualmente manos/piernas (el validador asegura coherencia del *prompt*, no de la imagen).
2. Decidir si `PIE`/`BRA` deben añadirse también a la tabla clásica.
3. [RESUELTO] Se sanearon las tablas de `tablas_pipeline_erotico_sexy.csv`: eliminados duplicados (IDs repetidos, copypaste de MIR en EXP), corregidas comas sin entrecomillar (`OUT-02E`, `POS-04`), asignados `Tipo_Bloque` correctos a `PIE` (`PIE-01..09`) y `BRA` (`BRA-01..12`), y agregadas protecciones de validación en `src/database.py`. Todas las tomas ADV y VAL pasan al 100%.
4. [RESUELTO] Migración a IDs y campos legibles en Inglés para la máquina, con Concepto y Descripciones en Español para el usuario:
   * **Diccionarios (`tablas_pipeline_jeanne_alter.csv` y `tablas_pipeline_erotico_sexy.csv`):**
     * IDs en inglés nemotécnico: `ID-JEANNE`, `SCENE-CATHEDRAL`, `STYLE-PHOTO`, `NEG-BASE`, `OUT-ARMOR`, `OUT-NO-ARMOR`, `OUT-LINGERIE`, `CAM-FULL`, `POS-RELAXED`, `HAND-HAIR`, `LEG-WIDE`, `EXP-SERENE`, `LOOK-DIRECT`, `LIGHT-GOLDEN`, etc.
     * Categorías en inglés: `IDENTITY`, `SCENE`, `STYLE`, `NEGATIVE`, `OUTFIT`, `CAMERA`, `POSTURE`, `GESTURE`, `POSE_PACK`, `LEGS`, `HANDS`, `EXPRESSION`, `GAZE`, `LIGHT`.
     * `Tipo_Bloque` en inglés: `Session_Fixed`, `Layer_Armor`, `Layer_Dress`, `Layer_Lingerie`, `Open_Framing`, `Close_Framing`, `Modular_Pose`, `Full_Pose`, `Primary_Hand`, `Secondary_Hand`, `Support_Hand`, `Free_Hand`, `Both_Hands`, `Leg_Wide`, `Manual_Interaction`, etc.
     * `Concepto` y `Descripcion_Natural` conservados en Español para lectura humana cómoda.
   * **Guiones de Tomas (`escenas_sesion_jeanne_alter.csv` y `escenas_sesion_avanzada_jeanne.csv`):**
     * Actualizados a IDs en inglés en `Secuencia_IDs` y columnas individuales (`ID_Identidad`, `ID_Outfit`, `ID_PosePack`, etc.).
     * `Descripcion` conservada en Español.
   * **Código Python (`src/limb_rules.py`, `src/assembler.py`, `src/database.py`):**
     * Soporte bilingüe y adaptado a roles en inglés (`Primary_Hand`, `Manual_Interaction`, etc.) y categorías en inglés (`HANDS`, `LEGS`, `CAMERA`, etc.).
   * **Verificación de Pruebas:**
     * Tomas estándar: `SHOT-01..08` (8/8 pasaron).
     * Tomas avanzadas y reglas: `ADV-01..05`, `VAL-01..05` (10/10 pasaron).
     * Modo aleatorio (estándar, erótico y avanzado) verificado al 100%.
5. [NUEVO] Creado `PROMPT_LLM_DIRECTOR_FOTOGRAFIA.md` y script automatizado `export_llm_prompt.py`:
   * Script generador: Ejecuta `python export_llm_prompt.py` o `python pipeline.py --export-llm`. Lee ambos CSVs con soporte UTF-8-sig, fusiona y deduplica los 88 bloques atómicos por categoría funcional, inyecta las reglas anatómicas (Limb Rules), el protocolo de creación de nuevos bloques (Concept-to-Pipeline) y emite el archivo Markdown listo para copiar y pegar en ChatGPT, Claude o LLMs de roleplay.
   * Flujo de trabajo resultante: El usuario solo corre el script, copia el .md a su LLM, y en el siguiente turno describe en lenguaje natural su escena compleja para recibir la secuencia, prompts y filas CSV listas.
