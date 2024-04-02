from PyQt5.QtWidgets import QApplication
# from ui.main_window import MainWindow
from PyQt5.QtGui import QFont, QFontDatabase, QIcon
from src.ui.main_window import MainWindow
from .font_config import novaMediumFont, novaBoldFont

if __name__ == "__main__":
    app = QApplication([])
    app.setFont(novaMediumFont)  # Aplica la fuente a toda la aplicación

    # # Cargar la fuente desde el archivo
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
