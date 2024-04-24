import os
from PyQt5.QtWidgets import QApplication
# from ui.main_window import MainWindow
from PyQt5.QtGui import QFont, QFontDatabase, QIcon
from PyQt5.QtCore import Qt, QDir
from src.ui.main_window import MainWindow
from pathlib import Path
# from src.font_config import fonts
# from .font_config import novaMediumFont, novaBoldFont
import faulthandler

faulthandler.enable()

CURRENT_DIRECTORY = Path(__file__).resolve().parent


def load_fonts_from_dir(directory):
    families = set()
    for fi in QDir(directory).entryInfoList(["*.otf", "*.ttf"]):
        _id = QFontDatabase.addApplicationFont(fi.absoluteFilePath())
        families |= set(QFontDatabase.applicationFontFamilies(_id))
    return families


if __name__ == "__main__":
    app = QApplication([])
    font_dir = CURRENT_DIRECTORY / ".." / "assets" / "fonts" / "proxima-nova"
    print(font_dir)
    families = load_fonts_from_dir(os.fspath(font_dir))
    print(families)
    db = QFontDatabase()
    styles = db.styles("Proxima Nova")
    print(styles)

    novaMediumFont = db.font("Proxima Nova", "Medium", 12)
    novaBoldFont = db.font("Proxima Nova", "Bold", 12)
    app.setFont(font)  # Aplica la fuente a toda la aplicación

    # novaMediumFont = fonts['medium']
    # novaBoldFont = fonts['bold']
    # app.setFont(novaMediumFont)
    # app.setFont(novaMediumFont)  # Aplica la fuente a toda la aplicación

    # Cargar la fuente desde el archivo
    # novaMediumId = QFontDatabase.addApplicationFont(
    #     "../assets/fonts/proxima-nova/ProximaNovaWide-Regular.otf")  # Ajusta la ruta a tu archivo de fuente
    # fontFamilies = QFontDatabase.applicationFontFamilies(novaMediumId)
    # if fontFamilies:  # Verifica si la fuente se cargó correctamente
    #     novaMediumFont = QFont(fontFamilies[0], 9, 600)  # Establece el tamaño de la fuente a 10 puntos
    #     # novaMediumFont.setLetterSpacing(QFont.PercentageSpacing, 110)  # Aumenta el espaciado entre letras en un 10%
    #     app.setFont(novaMediumFont)  # Aplica la fuente a toda la aplicación
    #
    # # Cargar la segunda fuente desde el archivo
    # novaBoldId = QFontDatabase.addApplicationFont("../assets/fonts/proxima-nova/ProximaNovaWide-Bold.otf")
    # specific_font_families = QFontDatabase.applicationFontFamilies(novaBoldId)
    # if specific_font_families:
    #     novaBoldFont = QFont(specific_font_families[0], 10)  # Establecer tamaño de 14 puntos para esta fuente
    #     # novaBoldFont.setLetterSpacing(QFont.PercentageSpacing, 120)  # Aumenta el espaciado entre letras en un 10%

    window = MainWindow()
    # Aquí estableces el ícono de la ventana
    window.setWindowIcon(QIcon('../assets/logos/tecneu-logo.ico'))
    window.show()
    app.exec_()
