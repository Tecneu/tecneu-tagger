from PyQt5.QtCore import Qt, QTimer, QRect, QPoint, QObject, QEvent
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class GiantOverlayMessage(QWidget):
    """
    Un widget overlay semitransparente para mostrar un mensaje grande.
    Se mueve/redimensiona con la ventana principal si es 'child' de ella,
    o si se usa como toplevel, podemos anclarlo a la ventana con un eventFilter.
    """

    def __init__(self, parent=None):
        """
        :param parent: si no es None, este overlay será hijo del 'parent' y
                       se moverá/redimensionará automáticamente con él.
        """
        super().__init__(parent=parent)
        self._is_shown = False
        self._timer = None
        self._parent_window = parent  # la ventana "principal"
        self._carousel_ref = None
        self._relationships_ref = None

        # Flags para que no tenga bordes
        # Si parent es None => es toplevel
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        # Permite pintar fondo con alpha
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Layout y label internos
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignCenter)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background-color: transparent;")
        self.layout.addWidget(self.label, alignment=Qt.AlignCenter)

        # Color y tamaño del rect
        self._bg_color = QColor(0, 0, 0, 128)  # default semitransp
        self._width = 400
        self._height = 200

        # Si es toplevel y queremos que se mueva con la ventana principal,
        # luego llamaremos a set_parent_window(mainWindow)
        # para instalar un eventFilter.

    def set_references(self, main_window, carousel=None, relationships=None):
        """
        Guardamos referencias a la main_window, carousel, relationships_window
        por si queremos "center_all_windows=True".
        """
        self._parent_window = main_window
        self._carousel_ref = carousel
        self._relationships_ref = relationships

    def set_parent_window(self, parent_window):
        """
        Para caso toplevel. Instala un eventFilter en parent_window
        que rastrea move/resize y recoloca el overlay.
        """
        self._parent_window = parent_window
        parent_window.installEventFilter(self)

    def eventFilter(self, obj, event):
        """
        Reacciona cuando el parent se mueve o redimensiona, para recolocar el overlay.
        """
        if obj is self._parent_window:
            if event.type() in (QEvent.Move, QEvent.Resize):
                if self._is_shown:
                    self.update_position()
        return super().eventFilter(obj, event)

    def show_message(self,
                     message,
                     center_all_windows=False,
                     bg_color="rgba(0,0,0,0.5)",
                     text_color="#FFFFFF",
                     font_size=24,
                     width=400,
                     height=200,
                     duration=3000,
                     is_html=False):
        """
        Muestra el mensaje en un recuadro de size (width x height),
        con bg_color semitransparente, centrado sobre la ventana principal (o bounding rect).
        Si ya había un mensaje, se oculta y se reemplaza.
        """
        # Si ya estaba visible, ocultarlo
        if self._is_shown:
            self.hide_message()

        # Guardamos parámetros
        self._is_shown = True
        self._width = width
        self._height = height
        self._bg_color = self._parse_color(bg_color)

        # Redimensionar
        self.setFixedSize(self._width, self._height)

        # Texto
        if is_html:
            html_formatted = f"<span style='color:{text_color}; font-size:{font_size}pt;'>{message}</span>"
            self.label.setText(html_formatted)
        else:
            self.label.setStyleSheet(
                f"color: {text_color}; font-size: {font_size}pt; background-color: transparent;"
            )
            self.label.setText(message)

        # Temporizador de autodestrucción
        if duration > 0:
            self._timer = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.setInterval(duration)
            self._timer.timeout.connect(self.hide_message)
            self._timer.start()
        else:
            self._timer = None

        # Calculamos la posición
        bounding_rect = self._get_bounding_rect(center_all_windows)
        self._move_center(bounding_rect)

        # Si este widget es child de un parent => se moverá con el parent
        # de forma automática. Si es toplevel => actualizamos su geometry:
        if not self.parent():
            # Toplevel => setWindowFlags para forzar topmost
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            self.show()
            self.raise_()
            self.activateWindow()
        else:
            # Es child => con .show() bastará
            self.show()
            self.raise_()

    def hide_message(self):
        """
        Oculta y resetea el overlay. Llama a .close() y cancela el timer.
        """
        self._is_shown = False
        if self._timer:
            self._timer.stop()
            self._timer = None
        self.close()

    def is_visible(self):
        return self._is_shown

    def paintEvent(self, event):
        """
        Pintamos el fondo con la transparencia real, en lugar de usar styleSheet.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self._bg_color)
        super().paintEvent(event)

    def update_position(self):
        """
        Vuelve a centrar este widget si la ventana principal (o bounding rect) cambió.
        """
        bounding_rect = self._get_bounding_rect(center_all_windows=False)
        # Si queremos que 'center_all_windows' se mantenga, deberíamos
        # guardar esa bandera en un atributo y usarlo aquí. O lo definimos:
        # bounding_rect = self._get_bounding_rect(self._last_center_all).
        self._move_center(bounding_rect)

    def _move_center(self, bounding_rect):
        x = bounding_rect.center().x() - (self._width // 2)
        y = bounding_rect.center().y() - (self._height // 2)
        if self.parent():
            # Al ser child => mover en coordenadas de parent
            self.move(self.parent().mapFromGlobal(QPoint(x, y)))
        else:
            # toplevel => mover en coords globales
            self.move(x, y)

    def _get_bounding_rect(self, center_all):
        """
        Obtiene la geometría combinada (main_window + carousel + relationships).
        """
        if not self._parent_window:
            # fallback => tomamos geometry local
            return self.geometry()

        bounding_rect = self._parent_window.geometry()
        if center_all and self._carousel_ref and self._carousel_ref.is_visible:
            bounding_rect = bounding_rect.united(self._carousel_ref.geometry())
        if center_all and self._relationships_ref and self._relationships_ref.is_visible:
            bounding_rect = bounding_rect.united(self._relationships_ref.geometry())
        return bounding_rect

    def _parse_color(self, color_str):
        """
        Convierte "rgba(r,g,b,a)" o "#RRGGBBAA" a QColor con alpha real.
        """
        # Similar a lo hecho antes
        import re
        if color_str.startswith('#'):
            return QColor(color_str)
        m = re.match(r'rgba\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d\.]+)\s*\)', color_str.strip(), re.IGNORECASE)
        if m:
            r = int(m.group(1))
            g = int(m.group(2))
            b = int(m.group(3))
            a_float = float(m.group(4))
            a = max(0, min(int(a_float * 255), 255))
            return QColor(r, g, b, a)
        # Fallback
        return QColor(color_str)
