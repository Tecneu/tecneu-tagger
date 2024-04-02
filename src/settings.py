from PyQt5.QtCore import QSettings


def load_settings():
    settings = QSettings('Tecneu', 'TecneuTagger')
    return settings


def save_settings(key, value):
    settings = QSettings('Tecneu', 'TecneuTagger')
    settings.setValue(key, value)
