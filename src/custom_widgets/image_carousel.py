import os

from PyQt5.QtCore import QRectF, QSize, Qt, QTimer, QUrl
from PyQt5.QtGui import QBrush, QColor, QMovie, QPainter, QPalette, QPen, QPixmap
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from config import BASE_ASSETS_PATH
from custom_widgets import HoverZoomWindow


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
            opacity=0.8,  # 80% de opacidad
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

        min_w = min(region_size_thumb, scaled_w)
        min_h = min(region_size_thumb, scaled_h)

        # Queremos centrar la región en (x_in_scaled, y_in_scaled)
        left_thumb = x_in_scaled - region_size_thumb / 2
        top_thumb = y_in_scaled - region_size_thumb / 2

        # Clampeamos para que la región no se salga de la miniatura
        if left_thumb < 0:
            left_thumb = 0
        if top_thumb < 0:
            top_thumb = 0
        if left_thumb + region_size_thumb > scaled_w:
            left_thumb = scaled_w - min_w
        if top_thumb + region_size_thumb > scaled_h:
            top_thumb = scaled_h - min_h

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
        painter.drawRect(QRectF(left_thumb, top_thumb, min_w, min_h))

        # -- Cuadrícula de puntos azules más claros --
        pen_grid = QPen(QColor(0, 0, 255, 60))  # Azul más claro
        pen_grid.setWidth(1)
        painter.setPen(pen_grid)

        grid_size = 2
        for gx in range(int(left_thumb), int(left_thumb + min_w), grid_size):
            for gy in range(int(top_thumb), int(top_thumb + min_h), grid_size):
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
