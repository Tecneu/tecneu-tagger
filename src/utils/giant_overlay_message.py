from PyQt5.QtCore import QEvent, QPoint, QRect, Qt, QTimer
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from font_config import FontManager


class OverlayMessage(QWidget):
    """
    Un widget overlay semitransparente para mostrar un mensaje grande,
    centrado en el parent que se pase (por ejemplo, MainWindow).

    - Se comporta como un child widget del parent, por lo que se moverá
      y redimensionará automáticamente con la ventana principal.
    - Muestra un rectángulo (width x height) con color semitransparente de fondo
      y un texto (HTML o plano) centrado.
    """

    def __init__(self, parent=None):
        """
        :param parent: la ventana (QWidget) sobre la cual se centrará el overlay.
        """
        super().__init__(parent=parent)
        self._is_shown = False
        self._timer = None

        fonts = FontManager.get_fonts()
        mysteric_font = None
        if fonts and "mystericFont" in fonts:
            mysteric_font = fonts["mystericFont"]

        # Parámetros por defecto
        self._bg_color = QColor(0, 0, 0, 128)
        self._width = 400
        self._height = 200

        # Flags: Sin bordes, pero ES child de 'parent' => no es toplevel
        # Esto hace que se superponga como overlay dentro del parent.
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Widget)
        # Permite pintar fondo con alpha
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Layout interno
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)

        # Label para el texto
        self.label = QLabel(self)
        if mysteric_font:
            self.label.setFont(mysteric_font)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background-color: transparent;")
        layout.addWidget(self.label, alignment=Qt.AlignCenter)

        self.hide()  # Inicia oculto

    def show_message(self, message, bg_color="rgba(0,0,0,0.5)", text_color="#FFFFFF", font_size=24, width=400, height=200, duration=3000, is_html=False):
        """
        Muestra un rectángulo semitransparente (width x height) centrado en el parent,
        con un texto. Se cierra automáticamente tras 'duration' ms (si > 0).

        :param message: el texto a mostrar (HTML si is_html=True).
        :param bg_color: ej. "rgba(0, 0, 128, 0.5)" => ~50% opaco
        :param text_color: color del texto
        :param font_size: tamaño del texto en pt (solo si is_html=False, se aplica QSS)
        :param width: ancho del rect
        :param height: alto del rect
        :param duration: ms que se muestra (0 => indefinido)
        :param is_html: si True, 'message' se interpreta como HTML
        """
        # Oculta mensaje anterior si estaba visible
        if self._is_shown:
            self.hide_message()

        self._is_shown = True
        self._bg_color = self._parse_color(bg_color)
        self._width = width
        self._height = height
        self.setFixedSize(self._width, self._height)

        # Configurar el texto
        if is_html:
            # Inserta color y font_size inline, si quieres
            html_str = f"<span style='color:{text_color}; font-size:{font_size}pt;'>{message}</span>"
            self.label.setText(html_str)
        else:
            # Texto plano con QSS
            self.label.setStyleSheet(f"background-color: transparent; color: {text_color}; font-size: {font_size}pt;")
            self.label.setText(message)

        # Si se define un duration, creamos un QTimer para autodestrucción
        if duration > 0:
            self._timer = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.setInterval(duration)
            self._timer.timeout.connect(self.hide_message)
            self._timer.start()
        else:
            self._timer = None

        # Centrar dentro del parent
        self._move_center_in_parent()

        # Mostrar
        self.show()
        self.raise_()

    def hide_message(self):
        """Oculta el overlay y resetea."""
        self._is_shown = False
        if self._timer:
            self._timer.stop()
            self._timer = None
        self.hide()

    def paintEvent(self, event):
        """Pintar fondo semitransparente con QPainter."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self._bg_color)
        super().paintEvent(event)

    def is_visible(self):
        return self._is_shown

    def _move_center_in_parent(self):
        """
        Calcula la posición (x, y) para centrar este widget
        en el rectángulo del parent (en coordenadas de parent).
        """
        if not self.parent():
            return

        parent_rect = self.parent().rect()  # en coords de parent
        x = (parent_rect.width() - self._width) // 2
        y = (parent_rect.height() - self._height) // 2
        self.move(x, y)

    def _parse_color(self, color_str):
        """
        Convierte un string 'rgba(r,g,b,a)' (a en [0..1]) o '#RRGGBBAA' a QColor con alpha.
        """
        import re

        if color_str.startswith("#"):
            return QColor(color_str)

        pattern = r"rgba\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d\.]+)\s*\)"
        m = re.match(pattern, color_str.strip(), re.IGNORECASE)
        if m:
            r = int(m.group(1))
            g = int(m.group(2))
            b = int(m.group(3))
            a_float = float(m.group(4))
            alpha = max(0, min(int(a_float * 255), 255))
            return QColor(r, g, b, alpha)

        # fallback
        return QColor(color_str)
