"""HuoHuo Adapters Layer.

Contains concrete implementations of domain and application ports.
Dependencies point inward towards Domain and Application layers.
"""

from huohuo.adapters.json_kizuna_repository import JsonKizunaRepository
from huohuo.adapters.llama_server_adapter import LlamaServerAdapter
from huohuo.adapters.markdown_vault_repository import MarkdownVaultRepository
from huohuo.adapters.piper_tts_adapter import PiperTTSAdapter
from huohuo.adapters.rvc_adapter import RVCAdapter
from huohuo.adapters.sounddevice_player_adapter import SounddevicePlayerAdapter
from huohuo.adapters.webview_ui_adapter import WebviewUIAdapter

__all__ = [
    "JsonKizunaRepository",
    "LlamaServerAdapter",
    "MarkdownVaultRepository",
    "PiperTTSAdapter",
    "RVCAdapter",
    "SounddevicePlayerAdapter",
    "WebviewUIAdapter",
]
