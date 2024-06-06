import os
import sys
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtCore import QDir
from pathlib import Path
from config import BASE_ASSETS_PATH


class FontManager:
    # Ruta base para las fuentes, se asume que este archivo está en el mismo directorio que la carpeta 'assets'
    # Cambia esto para reflejar la estructura dentro del ejecutable

    fonts = None

    @staticmethod
    def load_fonts_from_dir(family_name):
        font_dir = BASE_ASSETS_PATH / "fonts" / family_name
        families = set()
        for fi in QDir(os.fspath(font_dir)).entryInfoList(["*.otf", "*.ttf"]):
            _id = QFontDatabase.addApplicationFont(fi.absoluteFilePath())
            families |= set(QFontDatabase.applicationFontFamilies(_id))
        return families

    @staticmethod
    def initialize_fonts():
        db = QFontDatabase()

        # Initialize fonts dict if not already initialized
        if FontManager.fonts is None:
            FontManager.fonts = {}

        # Load and setup Proxima Nova fonts
        nova_families = FontManager.load_fonts_from_dir('proxima-nova')
        if "Proxima Nova" in nova_families:
            FontManager.fonts['novaRegularFont'] = FontManager.create_font('Proxima Nova', 'Regular', 9, 50, 110)
            FontManager.fonts['novaMediumFont'] = FontManager.create_font('Proxima Nova', 'Medium', 10, 700, 110)
            FontManager.fonts['novaBoldFont'] = FontManager.create_font('Proxima Nova', 'Bold', 11, 700, 110)
            print("Proxima Nova fonts initialized successfully.")
        else:
            raise Exception("Proxima Nova font is not available")

        # Load and setup Roboto fonts
        roboto_families = FontManager.load_fonts_from_dir('roboto')
        if "Roboto" in roboto_families:
            FontManager.fonts['robotoRegularFont'] = FontManager.create_font('Roboto', 'Regular', 9)
            FontManager.fonts['robotoMediumFont'] = FontManager.create_font('Roboto Medium', 'Regular', 10)
            FontManager.fonts['robotoBoldFont'] = FontManager.create_font('Roboto', 'Bold', 11)
            print("Roboto fonts initialized successfully.")
        else:
            raise Exception("Roboto font is not available")

        # Load and setup DS-DIGITAL fonts
        ds_digital_families = FontManager.load_fonts_from_dir('ds-digital')
        if "DS-Digital" in ds_digital_families:
            FontManager.fonts['digitalNormalFont'] = FontManager.create_font('DS-Digital', 'Normal', 15)
            FontManager.fonts['digitalBoldFont'] = FontManager.create_font('DS-Digital', 'Bold', 11)
            print("DS-Digital fonts initialized successfully.")
        else:
            raise Exception("DS-Digital font is not available")

        # Load and setup Mysteric fonts
        mysteric_families = FontManager.load_fonts_from_dir('mysteric')
        # print(mysteric_families)
        # styles = db.styles("Mysteric")
        # print(styles)
        if "Mysteric" in mysteric_families:
            FontManager.fonts['mystericFont'] = FontManager.create_font('Mysteric', 'Regular', 15)
            print("Mysteric font initialized successfully.")
        else:
            raise Exception("DS-Digital font is not available")

    @staticmethod
    def create_font(family, style, size, weight=None, letter_spacing=100):
        font = QFontDatabase().font(family, style, size)
        if weight:
            font.setWeight(weight)  # Ajustar el peso de la fuente
        font.setLetterSpacing(QFont.PercentageSpacing, letter_spacing)  # Ajustar el espaciado entre letras
        return font

    @staticmethod
    def get_fonts():
        if FontManager.fonts is None:
            FontManager.initialize_fonts()
        return FontManager.fonts
