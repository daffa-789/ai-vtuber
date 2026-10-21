"""Silver Wolf Adapters Layer.

Contains concrete implementations of domain and application ports.
Dependencies point inward towards Domain and Application layers.
"""

from silverwolf.adapters.json_kizuna_repository import JsonKizunaRepository
from silverwolf.adapters.llama_server_adapter import LlamaServerAdapter
from silverwolf.adapters.markdown_vault_repository import MarkdownVaultRepository
from silverwolf.adapters.piper_tts_adapter import PiperTTSAdapter
from silverwolf.adapters.rvc_adapter import RVCAdapter
from silverwolf.adapters.sounddevice_player_adapter import SounddevicePlayerAdapter
from silverwolf.adapters.webview_ui_adapter import WebviewUIAdapter

__all__ = [
    "JsonKizunaRepository",
    "LlamaServerAdapter",
    "MarkdownVaultRepository",
    "PiperTTSAdapter",
    "RVCAdapter",
    "SounddevicePlayerAdapter",
    "WebviewUIAdapter",
]
