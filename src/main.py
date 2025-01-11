# -*- coding: utf-8 -*-

import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from ui.main_window import MainWindow
from pathlib import Path
from font_config import FontManager
from config import BASE_ASSETS_PATH

if __name__ == "__main__":
    app = QApplication([])

    # Inicializar fuentes
    fonts = FontManager.get_fonts()
    if fonts and 'robotoMediumFont' in fonts:
        app.setFont(fonts['robotoMediumFont'])  # Establece la fuente regular para toda la aplicación

    window = MainWindow()
    # Aquí estableces el ícono de la ventana
    window.setWindowIcon(QIcon(os.fspath(BASE_ASSETS_PATH / 'logos' / 'tecneu-logo.ico')))
    window.show()
    app.exec_()
