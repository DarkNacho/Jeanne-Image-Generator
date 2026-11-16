"""
Módulo: src/workflow.py
Responsabilidad: Construcción del grafo de nodos para la API de ComfyUI (Checkpoint, LoRA, KSampler, etc.).
"""

import random
from typing import Dict, Any, Optional


class ComfyUIWorkflowBuilder:
    """Construye el grafo de nodos en formato JSON para la API de ComfyUI (/prompt)."""

    def __init__(self,
                 checkpoint_name: str = "WAI-Nsfw-Illustrious-17.safetensors",
                 lora_name: str = "jeanne_d_arc_alter_fate.safetensors",
                 steps: int = 15,
                 cfg: float = 5.0,
                 sampler_name: str = "euler_ancestral",
                 scheduler: str = "normal",
                 width: int = 1024,
                 height: int = 1024,
                 batch_size: int = 1):
        self.checkpoint_name = checkpoint_name
        self.lora_name = lora_name
        self.steps = steps
        self.cfg = cfg
        self.sampler_name = sampler_name
        self.scheduler = scheduler
        self.width = width
        self.height = height
        self.batch_size = batch_size

    def build_prompt_graph(self,
                           positive_prompt: str,
                           negative_prompt: str,
                           lora_strength: float,
                           seed: Optional[int] = None,
                           filename_prefix: str = "JAlter") -> Dict[str, Any]:
        """Genera el diccionario de nodos estándar compatible con el endpoint /prompt."""
        if seed is None:
            seed = random.randint(1, 1125899906842624)

        return {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": self.checkpoint_name
                }
            },
            "2": {
                "class_type": "LoraLoader",
                "inputs": {
                    "lora_name": self.lora_name,
                    "strength_model": round(lora_strength, 2),
                    "strength_clip": round(lora_strength, 2),
                    "model": ["1", 0],
                    "clip": ["1", 1]
                }
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["2", 1],
                    "text": positive_prompt
                }
            },
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["2", 1],
                    "text": negative_prompt
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": self.width,
                    "height": self.height,
                    "batch_size": self.batch_size
                }
            },
            "6": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": self.steps,
                    "cfg": self.cfg,
                    "sampler_name": self.sampler_name,
                    "scheduler": self.scheduler,
                    "denoise": 1.0,
                    "model": ["2", 0],
                    "positive": ["3", 0],
                    "negative": ["4", 0],
                    "latent_image": ["5", 0]
                }
            },
            "7": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["6", 0],
                    "vae": ["1", 2]
                }
            },
            "8": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": filename_prefix,
                    "images": ["7", 0]
                }
            }
        }
