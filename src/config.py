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

LABEL_SIZES = [
    {
        "title": "38x25mm",
        "value": "4_x_2_5"
    },
    {
        "title": "76x51mm",
        "value": "8_x_5"
    },
    {
        "title": '4x6"',
        "value": "6_x_4"
    },
    {
        "title": '5x2.5cm',
        "value": "5_x_2_5"
    },
]

__all__ = ["MAX_DELAY", "BASE_ASSETS_PATH", "BASE_ENV_PATH", "LABEL_SIZES"]
