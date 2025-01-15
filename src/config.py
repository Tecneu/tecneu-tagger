# config.py
import sys
from pathlib import Path

# Valor máximo para el delay slider
MAX_DELAY = 50

if getattr(sys, "frozen", False):
    # Si es así, usa la ruta de _MEIPASS
    BASE_ASSETS_PATH = Path(sys._MEIPASS) / "assets"
    BASE_ENV_PATH = Path(sys._MEIPASS) / "env"
else:
    # De lo contrario, usa la ruta relativa desde el archivo de script
    BASE_ASSETS_PATH = Path(__file__).resolve().parent.parent / "assets"
    BASE_ENV_PATH = Path(__file__).resolve().parent.parent / "env"

__all__ = ["MAX_DELAY", "BASE_ASSETS_PATH", "BASE_ENV_PATH"]
