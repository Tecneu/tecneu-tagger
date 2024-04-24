# font_config.py
import os
from PyQt5.QtGui import QFont, QFontDatabase
from pathlib import Path

# Ruta base para las fuentes, se asume que este archivo está en el mismo directorio que la carpeta 'assets'
BASE_FONT_PATH = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def load_font(family_name, style, size):
    # Cargar y retornar un QFont individual
    path = BASE_FONT_PATH / family_name / f"{style}.otf"
    font_id = QFontDatabase.addApplicationFont(str(path))
    if font_id == -1:
        raise IOError(f"Failed to load font at: {path}")
    family = QFontDatabase.applicationFontFamilies(font_id)[0]
    return QFont(family, size)


def load_fonts():
    # Cargar todas las fuentes necesarias y retornarlas en un diccionario
    fonts = {
        'ProximaNova-Regular': load_font('proxima-nova', 'Medium', 9),
        'ProximaNova-Bold': load_font('proxima-nova', 'Bold', 10)
    }
    return fonts


# Exportar fuentes como atributos individuales para facilitar la importación
fonts = load_fonts()
novaMediumFont = fonts['ProximaNova-Regular']
novaBoldFont = fonts['ProximaNova-Bold']
