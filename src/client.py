"""
Módulo: src/client.py
Responsabilidad: Comunicación con el servidor ComfyUI (HTTP/API) para verificación y encolado de prompts.
"""

import json
import uuid
import urllib.request
import urllib.error
from typing import Dict, Any, Optional


class ComfyUIClient:
    """Gestiona la comunicación con la API de ComfyUI."""

    def __init__(self, server_address: str = "127.0.0.1:8188"):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())

    def is_server_reachable(self) -> bool:
        """Verifica si el servidor ComfyUI está activo y respondiendo."""
        url = f"http://{self.server_address}/system_stats"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ComfyUIPipeline/1.0"})
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status == 200
        except Exception:
            return False

    def queue_prompt(self, prompt_graph: Dict[str, Any]) -> Optional[str]:
        """Envía el grafo de generación al endpoint /prompt de ComfyUI."""
        url = f"http://{self.server_address}/prompt"
        payload = json.dumps({"prompt": prompt_graph, "client_id": self.client_id}).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data.get("prompt_id")
        except urllib.error.URLError as e:
            print(f"[!] Error de conexión con ComfyUI en {url}: {e}")
            return None
        except Exception as e:
            print(f"[!] Error inesperado al enviar prompt: {e}")
            return None
