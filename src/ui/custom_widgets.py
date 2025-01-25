from PyQt5.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, QRect, Qt, pyqtProperty, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QIntValidator, QKeySequence, QPainter, QTextDocument
from PyQt5.QtWidgets import QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListView, QPushButton, QTableWidget, QTextEdit, QWidget

from font_config import FontManager

# ui/custom_widgets.py
__all__ = ["CustomTextEdit", "SpinBoxWidget", "CustomSearchBar", "CustomComboBox", "CustomTableWidget", "TransparentOverlayFrame"]

QApplication.processEvents()


class CustomTextEdit(QTextEdit):
    textPasted = pyqtSignal()  # Señal que no lleva datos

    def insertFromMimeData(self, source):
        if source.hasText():
            text = source.text()
            # Elimina espacios en blanco y comillas dobles al principio y al final
            text = text.strip().strip('"')
            (super(CustomTextEdit, self).insertPlainText(text))  # Usa insertPlainText para evitar la inserción de texto formateado
            self.textPasted.emit()  # Emitir la señal cuando se pega el texto


class PasteEventFilter(QObject):
    # Definimos una señal que transporte el texto pegado
    pasted = pyqtSignal(str)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if (event.modifiers() & Qt.ControlModifier) and (event.key() == Qt.Key_V):
                # Obtenemos el QLineEdit que disparó el evento
                if isinstance(obj, QLineEdit):
                    mime_data = QApplication.clipboard().mimeData()
                    if mime_data.hasText():
                        text = mime_data.text().strip().strip('"')
                        # Remplaza el texto anterior por el nuevo valor a pegar
                        obj.setText(text)
                        # Emitimos la señal con el texto
                        self.pasted.emit(text)
                        return True  # Evento manejado
        return super().eventFilter(obj, event)


class CustomSearchBar(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.paste_event_filter = PasteEventFilter()
        # Instala el filtro de eventos sobre sí mismo
        self.installEventFilter(self.paste_event_filter)
        # self.paste_event_filter.pasted.connect(self.on_pasted)

    # def on_pasted(self, text):
    #     # Si quieres, puedes setear aquí el texto al QLineEdit
    #     self.setText(text)


class CustomComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Reemplazamos la vista por un QListView
        # Usamos un QListView como vista
        list_view = QListView()
        self.setView(list_view)
        # IMPORTANTÍSIMO: Instalamos el eventFilter en la *viewport* de la vista,
        # no en la vista directa
        list_view.viewport().installEventFilter(self)

    def eventFilter(self, source, event):
        # Verificamos si el evento proviene de la viewport
        if source == self.view().viewport():
            if event.type() == QEvent.MouseButtonRelease:
                pos = event.pos()
                # Determinamos el índice sobre el que se hizo clic
                index = self.view().indexAt(pos)
                # print("ENTRA ACA EVENTO COMBO")
                # print(index)
                if index.isValid():
                    item = self.model().item(index.row())
                    if item is not None and not item.isEnabled():
                        # Ítem deshabilitado => Ignoramos el clic
                        print("Click en ítem deshabilitado, ignorando...")
                        return True
        return super().eventFilter(source, event)


class SpinBoxWidget(QWidget):
    valueChanged = pyqtSignal(int)  # Definir una nueva señal que pasa el valor actual

    def __init__(self, parent=None):
        super(SpinBoxWidget, self).__init__(parent)

        fonts = FontManager.get_fonts()
        robotoRegularFont = None
        if fonts and "robotoRegularFont" in fonts:
            robotoRegularFont = fonts["robotoRegularFont"]

        # Marco contenedor con tamaño fijo
        self.frame = QFrame(self)
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setStyleSheet("QFrame { background-color: white; border: 1px solid #BFBFBF; border-radius: 5px; }")
        self.frame.setFixedSize(120, 38)  # Ancho y alto fijos

        # Configuración del QLineEdit
        self.lineEdit = QLineEdit(self.frame)
        self.lineEdit.setPlaceholderText("Copias")
        self.lineEdit.setValidator(QIntValidator(0, 999))
        self.lineEdit.setText("0")
        self.lineEdit.setAlignment(Qt.AlignCenter)
        self.lineEdit.setStyleSheet("QLineEdit { border: none; background-color: transparent; }")
        self.lineEdit.setMinimumHeight(30)
        self.lineEdit.setMaximumWidth(130)

        # Conectar el cambio de texto a un manejador que emita la señal valueChanged
        self.lineEdit.textChanged.connect(self.on_text_changed)

        # Configuración de los botones
        self.incrementButton = QPushButton("+", self.frame)
        self.decrementButton = QPushButton("-", self.frame)
        if robotoRegularFont:
            self.incrementButton.setFont(robotoRegularFont)
            self.decrementButton.setFont(robotoRegularFont)

        # Estilos de los botones
        button_style = """
        QPushButton {
            background-color: transparent;
            color: #0E5FA4;
            border: none;
            font-size: 28px;
        }
        QPushButton:hover {
            color: #1175ca;
        }
        """
        self.incrementButton.setStyleSheet(button_style)
        self.decrementButton.setStyleSheet(button_style)
        self.incrementButton.setFixedSize(30, 30)
        self.decrementButton.setFixedSize(30, 30)

        # Conectar botones con las funciones
        self.incrementButton.clicked.connect(self.incrementValue)
        self.decrementButton.clicked.connect(self.decrementValue)

        # Layout horizontal para los botones y el line edit
        layout = QHBoxLayout(self.frame)
        layout.addWidget(self.decrementButton, 0, Qt.AlignVCenter)
        layout.addWidget(self.lineEdit, 1)
        layout.addWidget(self.incrementButton, 0, Qt.AlignVCenter)
        layout.setSpacing(2)
        layout.setContentsMargins(5, 5, 5, 5)

        # Configurar el layout del widget principal
        mainLayout = QHBoxLayout(self)
        mainLayout.addWidget(self.frame)
        mainLayout.setAlignment(Qt.AlignCenter)  # Centrar el QFrame en el widget
        mainLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(mainLayout)

    def on_text_changed(self, text):
        self.valueChanged.emit(text)

    def incrementValue(self):
        value = self.lineEdit.text()
        if value.isdigit():
            value = int(value)
        elif value != "":
            return

        value = int(value or 0)
        if value < 999:
            self.setValue(str(value + 1))

    def decrementValue(self):
        value = self.lineEdit.text()
        if value.isdigit():
            value = int(value)
        elif value != "":
            return

        value = int(value or 0)
        if value > 0:
            self.setValue(str(value - 1))

    def hasAcceptableInput(self):
        return self.lineEdit.hasAcceptableInput()

    def text(self):
        # return int(self.lineEdit.text())
        return self.lineEdit.text()

    def setValue(self, value):
        if self.text() != value:  # Verificar cambio para evitar bucle infinito
            self.lineEdit.setText(str(value))


class ToggleSwitch(QWidget):
    """
    Un switch tipo iOS. Emite señales on/off al hacer clic.
    Internamente actúa como un 'checkbox'.
    """

    toggled = pyqtSignal(bool)  # <--- Señal que emite el estado checked

    def __init__(self, parent=None, width=60, height=30, checked=False):
        """
        :param width: Ancho total del toggle en pixeles.
        :param height: Alto total del toggle en pixeles.
        :param checked: Estado inicial (True = ON, False = OFF).
        """
        super().__init__(parent)
        # Guardamos ancho y alto
        self._width = width
        self._height = height

        # Fijamos el tamaño total del widget
        self.setFixedSize(self._width, self._height)

        # Estado inicial
        self._checked = checked

        # Cálculos para el círculo:
        # Dejar un margen de 3px en la parte superior e inferior
        # => el diámetro del círculo será (altura - 6)
        self._circle_size = self._height - 6

        # Posiciones “apagado” (OFF) y “encendido” (ON)
        self._off_position = 3
        self._on_position = self._width - self._circle_size - 3

        # Determinamos la posición inicial del círculo según el estado
        self._circle_position = self._on_position if self._checked else self._off_position

        # Animación suave del círculo
        self._animation = QPropertyAnimation(self, b"circle_position", self)
        self._animation.setEasingCurve(QEasingCurve.OutQuad)
        self._animation.setDuration(200)

        # Cambiamos el cursor a “manita” sobre el toggle
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        """
        Dibuja el fondo, el texto grabado ON/OFF y la perilla (círculo).
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        # 1. Dibujar fondo
        if self._checked:
            background_color = QColor("#4cd964")  # color ON (verde)
        else:
            background_color = QColor("#c2c2c2")  # color OFF (gris)

        p.setBrush(QBrush(background_color))
        p.setPen(Qt.NoPen)
        # RoundedRect con radios equivalentes a la mitad de la altura
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)

        # 2. Dibujar texto “grabado”
        #    - Lo hacemos en un color un poco más oscuro que el fondo
        #      para simular que está “hundido” en el mismo color.
        text_color = background_color.darker(120)
        p.setPen(text_color)

        # font = p.font()
        font = QFont()
        font.setPointSize(8)  # Texto pequeño
        p.setFont(font)

        if self._checked:
            # Dibujar "ON" a la izquierda, con un poco de margen
            p.drawText(rect.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, "ON")
        else:
            # Dibujar "OFF" a la derecha, con un poco de margen
            p.drawText(rect.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignRight, "OFF")

        # 3. Dibujar la perilla (el círculo blanco)
        p.setBrush(QBrush(QColor("#ffffff")))
        circle_rect = QRect(self._circle_position, 3, self._circle_size, self._circle_size)
        p.drawEllipse(circle_rect)

        p.end()

    def mousePressEvent(self, event):
        """
        Al hacer clic, invertimos el estado (checked).
        """
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)
        super().mousePressEvent(event)

    def isChecked(self):
        return self._checked

    def setChecked(self, state):
        """
        Actualiza el estado y lanza la animación de la perilla.
        """
        if self._checked == state:
            return
        self._checked = state

        start = self._circle_position
        end = self._on_position if self._checked else self._off_position
        self._animation.stop()
        self._animation.setStartValue(start)
        self._animation.setEndValue(end)
        self._animation.start()

        # Emitir la señal con el nuevo estado
        self.toggled.emit(self._checked)

        self.update()

    @pyqtProperty(int)
    def circle_position(self):
        return self._circle_position

    @circle_position.setter
    def circle_position(self, pos):
        """
        Este setter se usa internamente por la animación.
        """
        self._circle_position = pos
        self.update()


class CustomTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            self.copy_selected_cells()
        else:
            super().keyPressEvent(event)

    def copy_selected_cells(self):
        selected_ranges = self.selectedRanges()
        if not selected_ranges:
            return

        copied_text = ""
        for selected_range in selected_ranges:
            for row in range(selected_range.topRow(), selected_range.bottomRow() + 1):
                row_data = []
                for col in range(selected_range.leftColumn(), selected_range.rightColumn() + 1):
                    if col == 0:
                        # Obtener el QLabel de la celda
                        cell_widget = self.cellWidget(row, col)
                        if isinstance(cell_widget, QLabel):
                            # Usar QTextDocument para extraer el texto plano
                            doc = QTextDocument()
                            doc.setHtml(cell_widget.text())
                            cell_text = doc.toPlainText()
                        else:
                            cell_text = ""
                    else:
                        # Obtener el texto del QTableWidgetItem
                        item = self.item(row, col)
                        cell_text = item.text() if item else ""
                    row_data.append(cell_text)
                copied_text += "\t".join(row_data) + "\n"

        # Establecer el texto en el portapapeles
        QApplication.clipboard().setText(copied_text)

class TransparentOverlayFrame(QFrame):
    """
    Un QFrame personalizado que pinta un color semitransparente en su paintEvent,
    en lugar de usar styleSheet para el fondo (que a veces ignora alpha).
    """
    def __init__(self, bg_color, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Guardamos el color en formato string y creamos un QColor con alpha
        self.bg_color = self._parse_color(bg_color)
        # Habilitamos fondo translúcido
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.bg_color)
        super().paintEvent(event)

    def _parse_color(self, color_str):
        """
        Convierte un string como 'rgba(0,0,128,0.4)' o '#00008080' a QColor con alpha.
        Maneja algunos casos básicos. Si algo falla, retorna QColor negro sin alpha.
        """
        # 1) Si empieza con '#', interpretamos como hex RGBA => #RRGGBBAA
        if color_str.startswith('#'):
            # asume que color_str = "#RRGGBBAA" (8 hex)
            if len(color_str) == 9:  # # + 8 hex => #AARRGGBB o #RRGGBBAA
                return QColor(color_str)
            # fallback
            return QColor(color_str)  # Qt intentará parsearlo
        # 2) Si es tipo "rgba(r, g, b, a)"
        elif color_str.lower().startswith('rgba'):
            # Ejemplo: rgba(0, 0, 128, 0.4)
            # Intentamos extraer los 4 valores
            import re
            pattern = r'rgba\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d\.]+)\s*\)'
            m = re.match(pattern, color_str.strip(), re.IGNORECASE)
            if m:
                r = int(m.group(1))
                g = int(m.group(2))
                b = int(m.group(3))
                # alpha entre 0..1 => multiplicamos por 255
                a_float = float(m.group(4))
                a = max(0, min(int(a_float * 255), 255))
                return QColor(r, g, b, a)
            return QColor(0, 0, 0, 128)  # fallback
        else:
            # Intentamos parsear con QColor directamente
            return QColor(color_str)
