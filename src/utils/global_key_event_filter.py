from PyQt5.QtCore import QEvent, QObject, Qt


class GlobalKeyEventFilter(QObject):
    """
    Filtro de eventos que captura KeyPress a nivel global de la aplicación.
    Cuando detecta una tecla, llama a un método en la MainWindow
    para que maneje la lógica.
    """

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            # Reenviamos el evento a un método en main_window
            return self.main_window.handle_global_key_press(event)
        return super().eventFilter(obj, event)
