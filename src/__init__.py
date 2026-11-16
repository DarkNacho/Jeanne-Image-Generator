"""
Package: src
Pipeline modular para generación fotográfica consistente en ComfyUI.
"""

from .database import PipelineDatabase
from .assembler import PromptAssembler
from .limb_rules import LimbRuleEngine
from .workflow import ComfyUIWorkflowBuilder
from .client import ComfyUIClient
from .formatters import OutputFormatter
from .cli import parse_arguments

__all__ = [
    "PipelineDatabase",
    "PromptAssembler",
    "LimbRuleEngine",
    "ComfyUIWorkflowBuilder",
    "ComfyUIClient",
    "OutputFormatter",
    "parse_arguments",
]
