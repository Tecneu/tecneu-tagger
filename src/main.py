import os

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from config import BASE_ASSETS_PATH
from font_config import FontManager
from ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication([])

    # Inicializar fuentes
    fonts = FontManager.get_fonts()
    if fonts and "robotoMediumFont" in fonts:
        app.setFont(fonts["robotoMediumFont"])  # Establece la fuente regular para toda la aplicación

    window = MainWindow()
    # Aquí estableces el ícono de la ventana
    window.setWindowIcon(QIcon(os.fspath(BASE_ASSETS_PATH / "logos" / "tecneu-logo.ico")))
    window.show()
    app.exec_()
