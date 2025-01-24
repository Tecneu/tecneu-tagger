import os

from PyQt5.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, QRect, QRectF, QSize, Qt, QTimer, QUrl, pyqtProperty, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QIntValidator, QKeySequence, QMovie, QPainter, QPalette, QPen, QPixmap, QTextDocument
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QPushButton,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import BASE_ASSETS_PATH
from font_config import FontManager

# ui/custom_widgets.py
__all__ = ["CustomTextEdit", "SpinBoxWidget", "CustomSearchBar", "CustomComboBox", "ImageCarousel", "HoverZoomWindow", "CustomTableWidget"]

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


class ImageCarousel(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Parámetros personalizables
        self.THUMB_SIZE = 100  # Tamaño máximo de miniatura (ancho o alto)
        self.ZOOM_REGION = 65  # Tamaño (en px de la miniatura) del rect mostrado en el thumb
        self.ZOOM_WINDOW_SIZE = 390  # Tamaño de la ventana de zoom (ancho x alto)

        # Estado de visibilidad del carrusel
        self._is_visible = False

        # Set semi-transparent background
        palette = self.palette()
        color = QColor(255, 255, 255, 51)  # 20% opacity
        palette.setColor(QPalette.Window, color)
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        self.main_layout = QVBoxLayout()
        self.image_layout = QHBoxLayout()

        # self.image_layout.setContentsMargins(15, 0, 15, 0)  # Padding around the entire layout
        # self.image_layout.setSpacing(15)  # Spacing between images
        # self.image_layout.setSpacing(20)  # Set spacing between images
        self.main_layout.addLayout(self.image_layout)
        self.setLayout(self.main_layout)

        self.setFixedHeight(150)
        self.network_manager = QNetworkAccessManager(self)
        self.images = []
        self.original_images = {}  # Store the original images
        self.hover_zoom_window = None

    @property
    def is_visible(self):
        """Return the visibility state of the carousel."""
        return self._is_visible

    def toggle_visibility(self, parent_geometry=None):
        """Toggle the visibility of the carousel."""
        if self._is_visible:
            self.hide_carousel()
        else:
            self.show_carousel(parent_geometry)

    def show_carousel(self, parent_geometry=None):
        """Show the carousel and update state."""
        if not self._is_visible:
            if parent_geometry:
                self._configure_geometry(parent_geometry)
            self.show()
            self._is_visible = True

    def hide_carousel(self):
        """Hide the carousel and update state."""
        if self._is_visible:
            self.hide()
            self.hide_zoom_window()  # Oculta ventana de zoom si existe
            self._is_visible = False

    def _configure_geometry(self, parent_geometry):
        """Configura la geometría y apariencia del carrusel."""
        self.setGeometryWithBackground(
            x=parent_geometry.x(),
            y=parent_geometry.y() + parent_geometry.height(),  # Se posiciona justo debajo de la ventana principal
            width=parent_geometry.width(),  # Ajusta el ancho al de la ventana principal
            height=150,  # Altura fija del carrusel
            background_color="#000000",  # Fondo negro
            opacity=0.65,  # 65% de opacidad
        )

    def set_images(self, images):
        """Agrega imágenes al carrusel, creando QLabels con placeholders y spinner."""
        self.clear_images()
        self.images = images

        for img_url in images:
            label = QLabel()
            label.setAlignment(Qt.AlignCenter)
            # Fijamos el QLabel para que no sobrepase THUMB_SIZE x THUMB_SIZE
            label.setFixedSize(self.THUMB_SIZE, self.THUMB_SIZE)
            # label.setStyleSheet("border: 1px solid gray; position: relative; background-color: white;")
            # position: relative;
            label.setStyleSheet(
                """
                QLabel {
                    border: 1px solid gray;
                    background-color: white; /* Optional for better visibility */
                    margin: 0;  /* Reset internal margins */
                }
            """
            )

            # Show spinner while loading
            spinner = QMovie(os.fspath(BASE_ASSETS_PATH / "icons" / "spinner.gif"))  # Replace with the path to your local spinner GIF
            # Fuerza el tamaño del spinner al 60% del tamaño THUMB_SIZE
            spinner.setScaledSize(QSize(int(self.THUMB_SIZE * 0.6), int(self.THUMB_SIZE * 0.6)))
            label.setMovie(spinner)
            spinner.start()

            # Add the QLabel to the layout
            self.image_layout.addWidget(label, alignment=Qt.AlignCenter)

            # Inicia la descarga con reintentos
            self.download_image(img_url, label, spinner, attempt=1)

        print("All requests sent.")

    def download_image(self, url, label, spinner, attempt):
        """
        Lanza una petición GET con un QNetworkRequest y QTimer de timeout (5s).
        Almacena la información necesaria en las propiedades del reply para
        poder manejarla en handle_reply y handle_timeout.
        """
        request = QNetworkRequest(QUrl(url))
        reply = self.network_manager.get(request)

        # Guardamos info en el QNetworkReply para recuperarla luego
        reply.setProperty("url", url)
        reply.setProperty("label", label)
        reply.setProperty("spinner", spinner)
        reply.setProperty("attempt", attempt)

        # Creamos un QTimer de 5s para timeout
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(4000)  # 4 segundos
        # Cuando ocurra el timeout, llamamos a self.handle_timeout(reply)
        timer.timeout.connect(lambda: self.handle_timeout(reply))
        reply.setProperty("timer", timer)

        # Conectamos la señal finished para procesar la respuesta
        reply.finished.connect(lambda: self.handle_reply(reply))

        timer.start()
        print(f"Sending request to {url}, attempt={attempt}")

    def handle_timeout(self, reply):
        """
        Se llama si pasan 5s sin que el reply haya terminado.
        Abortamos la conexión y dejamos que handle_reply gestione
        el reintento.
        """
        if reply.isRunning():
            print(f"Timeout for {reply.property('url')}, aborting...")
            reply.abort()  # Forzamos la finalización

    def handle_reply(self, reply):
        """
        Maneja la respuesta final, sea por éxito, error o timeout (abort).
        Decide si reintentar o fallar definitivamente.
        """
        url = reply.property("url")
        label = reply.property("label")
        spinner = reply.property("spinner")
        attempt = reply.property("attempt")
        timer = reply.property("timer")

        # Detener el timer para que no dispare más
        if timer and timer.isActive():
            timer.stop()
            timer.deleteLater()

        if reply.error() == QNetworkReply.NoError:
            # print("Image loaded successfully.")
            data = reply.readAll()

            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                # Store the original image
                self.original_images[url] = pixmap

                # Quitar spinner
                if spinner:
                    spinner.stop()
                    spinner.deleteLater()
                label.setMovie(None)  # QMovie no es necesario una vez no hay animación

                # Ajustamos la imagen al tamaño THUMB_SIZE, manteniendo relación
                thumb = pixmap.scaled(self.THUMB_SIZE, self.THUMB_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label.setPixmap(thumb)

                # Activamos eventos de mouse
                self.configure_label_for_zoom(label, url)
            else:
                # Datos corruptos o no es una imagen válida
                print(f"Invalid image data from {url}")
                self.retry_or_fail(url, label, spinner, attempt, "Invalid Image")
        else:
            # Error (puede ser error real o .abort() por timeout)
            print(f"Failed to load image from {url}, error={reply.error()}")
            self.retry_or_fail(url, label, spinner, attempt, "Failed to load")

        reply.deleteLater()

    def configure_label_for_zoom(self, label, img_url):
        """Configura el hover y el mouseMove si quieres zoom."""
        label.setMouseTracking(True)
        label.enterEvent = lambda event, lbl=label: self.show_zoom_window(event, lbl, img_url)
        label.leaveEvent = lambda event, lbl=label: self.clear_grid_and_hide_zoom(lbl)
        label.mouseMoveEvent = lambda event, lbl=label: self.update_zoom_position(event, lbl, img_url)

    def retry_or_fail(self, url, label, spinner, attempt, fail_text):
        """
        Maneja la lógica de reintento hasta 3 veces.
        Si ya se ha intentado 3, marcamos como fallido definitivamente.
        De lo contrario, reintenta con attempt+1.
        """
        if attempt < 3:
            # Reintentar
            new_attempt = attempt + 1
            print(f"Retrying {url} (attempt={new_attempt})")
            self.download_image(url, label, spinner, new_attempt)
        else:
            # Ya no reintentamos más
            if spinner:
                spinner.stop()
                spinner.deleteLater()
            label.setMovie(None)
            label.setText(fail_text)

    def clear_images(self):
        """Clear the current images in the carousel."""
        while self.image_layout.count():
            child = self.image_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def show_zoom_window(self, event, label, img_url):
        """Show a zoomed-in portion of the image based on the QLabel's pixmap."""
        if self.hover_zoom_window is not None:
            self.hide_zoom_window()

        # Recupera el pixmap original
        if img_url in self.original_images:
            original_pixmap = self.original_images[img_url]
            self.hover_zoom_window = HoverZoomWindow(original_pixmap, self.ZOOM_WINDOW_SIZE, parent=self.parent())
            self.hover_zoom_window.show()
            # Actualiza la posición inicial de zoom
            self.update_zoom_position(event, label, img_url)
        else:
            print("No pixmap available for zooming.")

    def clear_grid_and_hide_zoom(self, label):
        """Clear the grid from the label and hide the zoom window."""
        self.restore_original_pixmap(label)
        self.hide_zoom_window()

    def restore_original_pixmap(self, label):
        """Restaura el pixmap original del label, si se modificó para dibujar algo."""
        if hasattr(label, "_original_pixmap"):
            label.setPixmap(label._original_pixmap)
            label.update()
            del label._original_pixmap

    def hide_zoom_window(self):
        """Oculta la ventana flotante de zoom si existe."""
        if self.hover_zoom_window:
            self.hover_zoom_window.close()
            self.hover_zoom_window = None

    def update_zoom_position(self, event, label, img_url):
        """Actualiza el recorte de zoom basándose en la posición del mouse."""
        if not self.hover_zoom_window:
            return

        # Tamaño del pixmap escalado en el label (la miniatura)
        if not label.pixmap():
            return

        scaled_pix = label.pixmap()
        scaled_w = scaled_pix.width()
        scaled_h = scaled_pix.height()

        # Tamaño real del label (e.g. 100x100)
        label_w = label.width()
        label_h = label.height()

        # Offset por centrado (si la imagen no llena todo el QLabel)
        offset_x = (label_w - scaled_w) // 2
        offset_y = (label_h - scaled_h) // 2

        # Posición del mouse dentro del QLabel
        local_pos = event.pos()

        # Coordenadas dentro del área visible de la miniatura
        x_in_scaled = local_pos.x() - offset_x
        y_in_scaled = local_pos.y() - offset_y

        # Clampeamos para no salir del pixmap escalado
        x_in_scaled = max(0, min(x_in_scaled, scaled_w))
        y_in_scaled = max(0, min(y_in_scaled, scaled_h))

        # Ahora interpretamos ZOOM_REGION como tamaño en la miniatura
        region_size_thumb = self.ZOOM_REGION

        # Queremos centrar la región en (x_in_scaled, y_in_scaled)
        left_thumb = x_in_scaled - region_size_thumb / 2
        top_thumb = y_in_scaled - region_size_thumb / 2

        # Clampeamos para que la región no se salga de la miniatura
        if left_thumb < 0:
            left_thumb = 0
        if top_thumb < 0:
            top_thumb = 0
        if left_thumb + region_size_thumb > scaled_w:
            left_thumb = scaled_w - region_size_thumb
        if top_thumb + region_size_thumb > scaled_h:
            top_thumb = scaled_h - region_size_thumb

        # Dibujar rectángulo + cuadrícula en la miniatura
        if not hasattr(label, "_original_pixmap"):
            label._original_pixmap = scaled_pix.copy()

        temp_pix = label._original_pixmap.copy()
        painter = QPainter(temp_pix)
        painter.setRenderHint(QPainter.Antialiasing)

        # -- Rectángulo azul (semitransparente) --
        pen_rect = QPen(QColor(0, 0, 255, 128))  # Azul semitransparente
        pen_rect.setWidth(1)
        painter.setPen(pen_rect)
        painter.drawRect(QRectF(left_thumb, top_thumb, region_size_thumb, region_size_thumb))

        # -- Cuadrícula de puntos azules más claros --
        pen_grid = QPen(QColor(0, 0, 255, 60))  # Azul más claro
        pen_grid.setWidth(1)
        painter.setPen(pen_grid)

        grid_size = 2
        for gx in range(int(left_thumb), int(left_thumb + region_size_thumb), grid_size):
            for gy in range(int(top_thumb), int(top_thumb + region_size_thumb), grid_size):
                painter.drawPoint(gx, gy)

        painter.end()

        label.setPixmap(temp_pix)
        label.update()

        # ---- Calcular la región correspondiente en la imagen original ----
        # Relación de escala (original -> miniatura)
        original_pixmap = self.original_images[img_url]
        orig_w = original_pixmap.width()
        orig_h = original_pixmap.height()

        scale_x = orig_w / scaled_w
        scale_y = orig_h / scaled_h

        # Mapeo de la región en la miniatura a la región en la imagen original
        left_orig = left_thumb * scale_x
        top_orig = top_thumb * scale_y
        width_orig = region_size_thumb * scale_x
        height_orig = region_size_thumb * scale_y

        # Pasamos el QRect a la ventana flotante
        rect_in_original = QRectF(left_orig, top_orig, width_orig, height_orig)
        self.hover_zoom_window.update_zoom_rect(rect_in_original)

    def setGeometryWithBackground(self, x, y, width, height, background_color="#000000", opacity=0.8):
        """
        Establece la geometría de la ventana junto con un fondo personalizado.

        :param x: Posición en X de la ventana.
        :param y: Posición en Y de la ventana.
        :param width: Ancho de la ventana.
        :param height: Altura de la ventana.
        :param background_color: Color de fondo en formato HEX.
        :param opacity: Opacidad del fondo (0.0 a 1.0).
        """
        # Establecer geometría
        self.setGeometry(x, y, width, height)

        # Configurar fondo semiopaco
        r, g, b = QColor(background_color).getRgb()[:3]
        alpha = int(opacity * 255)
        self.background_color = QColor(r, g, b, alpha)
        self.update()  # Forzar redibujado

    def paintEvent(self, event):
        """Dibujar el fondo personalizado."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(self.background_color))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())
        painter.end()


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

        # Recortamos y escalamos para la ventana de zoom
        cropped = self.original_pixmap.copy(source_rect)
        zoomed_pixmap = cropped.scaled(self.zoom_window_size, self.zoom_window_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.zoom_label.setPixmap(zoomed_pixmap)


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
