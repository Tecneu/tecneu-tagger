from PyQt5.QtCore import QPoint, QRect, QRectF, Qt
from PyQt5.QtWidgets import QLabel, QWidget


class HoverZoomWindow(QWidget):
    def __init__(self, pixmap, zoom_window_size, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("border: 1px solid black; background-color: white;")

        # Parámetros configurables
        self.zoom_window_size = zoom_window_size

        self.setFixedSize(self.zoom_window_size, self.zoom_window_size)

        # Centrar la ventana flotante en torno al padre
        if parent:
            center_pt = parent.geometry().center()
            self.move(center_pt - QPoint(self.zoom_window_size // 2, self.zoom_window_size // 2))

        self.original_pixmap = pixmap
        self.zoom_label = QLabel(self)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.zoom_label.setFixedSize(self.zoom_window_size, self.zoom_window_size)

    def update_zoom_rect(self, rect_in_original: QRectF):
        """
        Recibe la región (QRectF) de la imagen original que se desea mostrar,
        la clamea si excede los bordes, y hace el .copy() y .scaled() para
        mostrarla en la etiqueta.
        """
        left = rect_in_original.x()
        top = rect_in_original.y()
        w = rect_in_original.width()
        h = rect_in_original.height()

        # Clampeo por si la región excede la imagen original
        max_left = self.original_pixmap.width() - w
        max_top = self.original_pixmap.height() - h

        if left < 0:
            left = 0
        if top < 0:
            top = 0
        if left > max_left:
            left = max_left
        if top > max_top:
            top = max_top

        source_rect = QRect(int(left), int(top), int(w), int(h))

        # Evitar que el ancho/alto sean negativos por redondeos
        if source_rect.width() <= 0 or source_rect.height() <= 0:
            return

        # Recortamos y escálamos para la ventana de zoom
        cropped = self.original_pixmap.copy(source_rect)
        zoomed_pixmap = cropped.scaled(self.zoom_window_size, self.zoom_window_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.zoom_label.setPixmap(zoomed_pixmap)
