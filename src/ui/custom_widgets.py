from PyQt5.QtWidgets import QTextEdit

# ui/custom_widgets.py
__all__ = ['CustomTextEdit']


class CustomTextEdit(QTextEdit):
    def insertFromMimeData(self, source):
        if source.hasText():
            text = source.text()
            # Elimina espacios en blanco y comillas dobles al principio y al final
            text = text.strip().strip('"')
            super(CustomTextEdit, self).insertPlainText(
                text)  # Usa insertPlainText para evitar la inserción de texto formateado
