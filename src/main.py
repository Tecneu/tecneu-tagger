import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from ui.main_window import MainWindow
from pathlib import Path
from font_config import get_fonts

if __name__ == "__main__":
    app = QApplication([])

    fonts = get_fonts()
    if 'ProximaNova-Regular' in fonts:
        app.setFont(fonts['ProximaNova-Regular'])  # Establece la fuente para toda la aplicación

    # print(get_fonts())

    # Inicializar fuentes
    # novaRegularFont, novaBoldFont = get_fonts()
    # novaRegularFont, novaBoldFont = (get_fonts()[k] for k in ['novaRegularFont', 'novaBoldFont'])
    # app.setFont(novaRegularFont)  # Aplica la fuente a toda la aplicación

    window = MainWindow()
    # Aquí estableces el ícono de la ventana
    window.setWindowIcon(QIcon('../assets/logos/tecneu-logo.ico'))
    window.show()
    app.exec_()
