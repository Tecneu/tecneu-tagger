import os
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtCore import Qt, QDir
from pathlib import Path

# Ruta base para las fuentes, se asume que este archivo está en el mismo directorio que la carpeta 'assets'
BASE_FONT_PATH = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def load_fonts_from_dir(family_name):
    font_dir = BASE_FONT_PATH / family_name
    families = set()
    for fi in QDir(os.fspath(font_dir)).entryInfoList(["*.otf", "*.ttf"]):
        _id = QFontDatabase.addApplicationFont(fi.absoluteFilePath())
        families |= set(QFontDatabase.applicationFontFamilies(_id))
    return families


def load_fonts():
    families = load_fonts_from_dir('proxima-nova')
    print(families)
    db = QFontDatabase()
    styles = db.styles("Proxima Nova")
    print(styles)
    fonts = None
    # Cargar todas las fuentes necesarias y retornarlas en un diccionario
    if "Proxima Nova" in families:
        fonts = {
            'ProximaNova-Regular': db.font('Proxima Nova', 'Regular', 9),
            'ProximaNova-Bold': db.font('Proxima Nova', 'Bold', 10)
        }
        print("Fonts initialized successfully.")
    else:
        raise Exception("Proxima Nova font is not available")

    return fonts


# # Intenta cargar las fuentes al importar el módulo, y captura las excepciones si es necesario.
# try:
#     fonts = load_fonts()
# except Exception as e:
#     print(e)
#     fonts = {}

# Usar esta función para inicializar las fuentes en el lugar apropiado de la aplicación
def get_fonts():
    return load_fonts()
