# config.py
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Valor máximo para el delay slider
MAX_DELAY = 50

if getattr(sys, "frozen", False):
    # Estamos en un ejecutable PyInstaller => producción
    # Si es así, usa la ruta de _MEIPASS
    BASE_ASSETS_PATH = Path(sys._MEIPASS) / "assets"
    BASE_ENV_PATH = Path(sys._MEIPASS) / "env"
    env_file = ".env.production"
else:
    # Estamos corriendo como script normal => desarrollo
    # De lo contrario, usa la ruta relativa desde el archivo de script
    BASE_ASSETS_PATH = Path(__file__).resolve().parent.parent / "assets"
    BASE_ENV_PATH = Path(__file__).resolve().parent.parent / "env"
    env_file = ".env.development"

# Selección del entorno según variable de entorno (o "development" por defecto)
# ENV = os.getenv("TAGGER_ENV", "development").lower()
#
# if ENV == "production":
#     env_file = ".env.production"
# else:
#     env_file = ".env.development"

# Cargar el .env correspondiente
load_dotenv(BASE_ENV_PATH / env_file)

# Ahora ya puedes leer variables de entorno en todo tu proyecto
API_EMAIL = os.getenv("API_EMAIL", "")
API_PASSWORD = os.getenv("API_PASSWORD", "")
API_BASE_URL = os.getenv("API_BASE_URL", "")

LABEL_SIZES = [
    {"title": "38x25mm", "value": "4_x_2_5"},
    {"title": "76x51mm", "value": "8_x_5"},
    {"title": '4x6"', "value": "6_x_4"},
    {"title": "5x2.5cm", "value": "5_x_2_5"},
]

__all__ = ["MAX_DELAY", "BASE_ASSETS_PATH", "BASE_ENV_PATH", "LABEL_SIZES", "API_EMAIL", "API_PASSWORD", "API_BASE_URL", "ENV"]
