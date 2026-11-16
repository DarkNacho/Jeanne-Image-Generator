"""
Módulo: src/cli.py
Responsabilidad: Definición y análisis de argumentos de línea de comandos (argparse).
"""

import argparse

NORMAL_MASTER_CSV = "tablas_pipeline_jeanne_alter.csv"
EROTIC_MASTER_CSV = "tablas_pipeline_erotico_sexy.csv"
NORMAL_SHOTS_CSV = "escenas_sesion_jeanne_alter.csv"
ADVANCED_SHOTS_CSV = "escenas_sesion_avanzada_jeanne.csv"


def parse_arguments() -> argparse.Namespace:
    """Configura y analiza los argumentos de consola para la ejecución del pipeline."""
    parser = argparse.ArgumentParser(
        description="Pipeline Director de Fotografía - Jeanne Alter (ComfyUI Generator)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Modos de Operación
    parser.add_argument("--mode", choices=["shot", "random"], default="shot",
                        help="Modo de ejecución: 'shot' (guionado según CSV) o 'random' (creativo)")
    parser.add_argument("--shot-id", type=str, default="all",
                        help="ID de toma específica (ej. 'SHOT-01' o 'SHOT-01,SHOT-03') o 'all'")
    parser.add_argument("--count", type=int, default=5,
                        help="Número de iteraciones para Modo Creativo (random)")

    # Parámetros ComfyUI
    parser.add_argument("--steps", type=int, default=15,
                        help="Número de pasos de muestreo")
    parser.add_argument("--width", type=int, default=1024,
                        help="Ancho de imagen en píxeles")
    parser.add_argument("--height", type=int, default=1024,
                        help="Alto de imagen en píxeles")
    parser.add_argument("--batch-size", type=int, default=1,
                        help="Tamaño de lote (batch size)")
    parser.add_argument("--cfg", type=float, default=5.0,
                        help="Escala CFG (optimizado para Illustrious)")
    parser.add_argument("--sampler", type=str, default="euler_ancestral",
                        help="Nombre del sampler en ComfyUI")
    parser.add_argument("--scheduler", type=str, default="normal",
                        help="Scheduler de ruido en ComfyUI")
    parser.add_argument("--seed", type=int, default=None,
                        help="Semilla fija (si se omite, se genera aleatoria)")

    # Modelos
    parser.add_argument("--checkpoint", type=str, default="WAI-Nsfw-Illustrious-17.safetensors",
                        help="Nombre de archivo del Checkpoint en ComfyUI")
    parser.add_argument("--lora-name", type=str, default="jeanne_d_arc_alter_fate.safetensors",
                        help="Nombre exacto del LoRA en ComfyUI")

    # Servidor y Envíos
    parser.add_argument("--server", type=str, default="127.0.0.1:8188",
                        help="Dirección IP/Host y puerto de ComfyUI")
    parser.add_argument("--queue", action="store_true",
                        help="Enviar los trabajos automáticamente a la cola de ComfyUI vía API")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Modo Verbose: Acompaña cada prompt con el desglose fotográfico conceptual")
    parser.add_argument("--format", choices=["terminal", "json"], default="terminal",
                        help="Formato de salida en la terminal: 'terminal' (prompts listos) o 'json'")
    parser.add_argument("--save-json", "--save", dest="save_json", action="store_true", default=False,
                        help="Guarda los archivos JSON y resumen en disco. Por defecto NO guarda")
    parser.add_argument("--output-dir", type=str, default="output_prompts",
                        help="Directorio donde exportar los archivos generados (si se usa --save-json)")

    # Archivos CSV
    parser.add_argument("--master-csv", type=str, default=None,
                        help="Ruta al CSV Diccionario Maestro (default: tablas_pipeline_jeanne_alter.csv; "
                             "con --advanced o --erotica: tablas_pipeline_erotico_sexy.csv)")
    parser.add_argument("--shots-csv", type=str, default=None,
                        help="Ruta al CSV Guion de Escenas (default: escenas_sesion_jeanne_alter.csv; "
                             "con --advanced: escenas_sesion_avanzada_jeanne.csv)")
    parser.add_argument("--advanced", "--composicion-avanzada", dest="advanced", action="store_true",
                        help="Composición Avanzada: usa las tablas con PIE/BRA y el guion avanzado, "
                             "y en modo random añade modificadores de piernas y manos")

    # Filtros para Modo Creativo (Random)
    parser.add_argument("--outfit", type=str, default=None,
                        help="Filtro opcional para fijar un Outfit específico en modo random (ej. 'OUT-01B')")
    parser.add_argument("--pose-path", choices=["a", "b", "random"], default="random",
                        help="Camino de pose para modo random: 'a' (modular), 'b' (pack) o 'random'")
    parser.add_argument("--luz", type=str, default=None,
                        help="Filtro opcional para fijar iluminación en modo random (ej. 'LUZ-02')")
    parser.add_argument("--erotica", type=float, nargs="?", const=1.0, default=None,
                        help="Activa la tabla sexy como fuente de datos. Sin valor = 1.0. En modo random "
                             "el valor (0.0-1.0) es la probabilidad por toma de usar la tabla sexy frente a "
                             "la clásica (0.5 = 50/50, 0.0 = solo clásica). Sin la bandera: tabla clásica")

    args = parser.parse_args()
    if args.erotica is not None and not 0.0 <= args.erotica <= 1.0:
        parser.error("--erotica debe estar entre 0.0 y 1.0")

    erotica_active = args.erotica is not None and args.erotica > 0.0
    args.master_csv_explicit = args.master_csv is not None
    if args.master_csv is None:
        args.master_csv = EROTIC_MASTER_CSV if (args.advanced or erotica_active) else NORMAL_MASTER_CSV
    if args.shots_csv is None:
        args.shots_csv = ADVANCED_SHOTS_CSV if args.advanced else NORMAL_SHOTS_CSV
    return args
