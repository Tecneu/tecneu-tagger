# src/font_config.py
import os
from PyQt5.QtGui import QFont, QFontDatabase

# Obtiene la ruta al directorio actual del script
current_dir = os.path.dirname(__file__)

# Carga las fuentes y devuelve las instancias de QFont
def load_fonts():
    fonts = {}

    nova_medium_path = os.path.join(current_dir, "..", "assets", "fonts", "proxima-nova", "ProximaNovaWide-Regular.otf")
    nova_bold_path = os.path.join(current_dir, "..", "assets", "fonts", "proxima-nova", "ProximaNovaWide-Bold.otf")

    print(nova_medium_path)
    print(nova_bold_path)

    # nova_medium_id = QFontDatabase.addApplicationFont(nova_medium_path)

    novaMediumId = QFontDatabase.addApplicationFont("../assets/fonts/proxima-nova/ProximaNovaWide-Regular.otf")  # Ajusta la ruta a tu archivo de fuente
    # nova_bold_id = QFontDatabase.addApplicationFont(nova_bold_path)

    medium_family = QFontDatabase.applicationFontFamilies(novaMediumId)
    # bold_family = QFontDatabase.applicationFontFamilies(nova_bold_id)

    if medium_family:
        # novaMediumFont = QFont(medium_family[0], 9, 600)  # Establece el tamaño de la fuente a 10 puntos
        fonts['medium'] = QFont(medium_family[0], 9, 600)

    # if bold_family:
    #     fonts['bold'] = QFont(bold_family[0], 10)

    return fonts


fonts = load_fonts()
novaMediumFont = fonts.get('medium')
novaBoldFont = fonts.get('bold')
