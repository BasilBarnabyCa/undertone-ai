"""User config: TOML file at ~/.config/undertone/config.toml, created on first run."""

import tomllib
from dataclasses import dataclass, replace
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "undertone"
CONFIG_PATH = CONFIG_DIR / "config.toml"
LOG_PATH = CONFIG_DIR / "undertone.log"

DEFAULT_CONFIG_TOML = """\
# undertone configuration

# Key to hold while speaking. One of:
# right_option, left_option, right_command, right_ctrl, f13
hotkey = "right_option"

# HuggingFace repo of the mlx-whisper model.
# Smaller/faster alternative: "mlx-community/whisper-small.en-mlx"
whisper_model = "mlx-community/whisper-large-v3-turbo"

# Language hint for Whisper ("en", "fr", ...); empty string = auto-detect.
language = "en"

# LLM cleanup pass via local Ollama (can also be toggled from the menu bar).
cleanup_enabled = true
ollama_model = "llama3.2:3b"
ollama_url = "http://localhost:11434"
# Seconds to wait for cleanup before falling back to the raw transcript.
cleanup_timeout = 6.0

# Subtle start/stop ticks (off by default; also toggleable from the menu bar).
# Names come from /System/Library/Sounds (without the .aiff). Volume is 0.0-1.0.
sounds_enabled = false
sound_start = "Glass"
sound_stop = "Pop"
sound_volume = 0.5
"""


@dataclass
class Config:
    hotkey: str = "right_option"
    whisper_model: str = "mlx-community/whisper-large-v3-turbo"
    language: str = "en"
    cleanup_enabled: bool = True
    ollama_model: str = "llama3.2:3b"
    ollama_url: str = "http://localhost:11434"
    cleanup_timeout: float = 6.0
    sounds_enabled: bool = False
    sound_start: str = "Glass"
    sound_stop: str = "Pop"
    sound_volume: float = 0.5


def load() -> Config:
    """Load config, writing the commented default file on first run."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(DEFAULT_CONFIG_TOML)
        return Config()
    data = tomllib.loads(CONFIG_PATH.read_text())
    known = {f for f in Config.__dataclass_fields__}
    return replace(Config(), **{k: v for k, v in data.items() if k in known})
