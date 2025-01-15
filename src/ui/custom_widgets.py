import os

from PyQt5.QtCore import QPoint, QRect, Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QIntValidator, QMovie, QPainter, QPalette, QPen, QPixmap
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt5.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget

from config import BASE_ASSETS_PATH
from font_config import FontManager

# ui/custom_widgets.py
__all__ = ["CustomTextEdit", "SpinBoxWidget", "CustomSearchBar"]

QApplication.processEvents()


class CustomTextEdit(QTextEdit):
    def insertFromMimeData(self, source):
        if source.hasText():
            text = source.text()
            # Elimina espacios en blanco y comillas dobles al principio y al final
            text = text.strip().strip('"')
            (super(CustomTextEdit, self).insertPlainText(text))  # Usa insertPlainText para evitar la inserción de texto formateado


class CustomSearchBar(QLineEdit):
    def insertFromMimeData(self, source):
        print("ENTRO AQUI MIME DATA")
        if source.hasText():
            print("ENTRO AQUI MIME DATA")
            text = source.text()
            # Elimina espacios en blanco y comillas dobles al principio y al final
            text = text.strip().strip('"')
            (super(CustomSearchBar, self).insertPlainText(text))  # Usa insertPlainText para evitar la inserción de texto formateado


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
        self.last_label = None  # To track the last label with a grid

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
            self.hide_zoom_window()  # Ensure zoom window is hidden
            self._is_visible = False

    def _configure_geometry(self, parent_geometry):
        """Configures the geometry and appearance of the carousel."""
        self.setGeometryWithBackground(
            x=parent_geometry.x(),
            y=parent_geometry.y() + parent_geometry.height(),  # Se posiciona justo debajo de la ventana principal
            width=parent_geometry.width(),  # Ajusta el ancho al de la ventana principal
            height=150,  # Altura fija del carrusel
            background_color="#000000",  # Fondo negro
            opacity=0.65,  # 65% de opacidad
        )

    def set_images(self, images):
        """Add images to the carousel."""
        self.clear_images()
        self.images = images
        # self.spinners = {}  # Track spinners to ensure they are properly handled
        # self.labels = {}  # Track labels to associate them with their respective images

        for img_url in images:
            label = QLabel()
            label.setAlignment(Qt.AlignCenter)
            label.setFixedSize(100, 100)
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
            label.setMovie(spinner)
            spinner.start()

            # Add the QLabel to the layout
            self.image_layout.addWidget(label, alignment=Qt.AlignCenter)

            request = QNetworkRequest(QUrl(img_url))
            print(f"Sending request to {img_url}")

            reply = self.network_manager.get(request)
            reply.finished.connect(lambda r=reply, lbl=label, sp=spinner, url=img_url: self.handle_reply(r, lbl, sp, url))

        print("All requests sent.")

    def handle_reply(self, reply, label, spinner, img_url):
        # spinner = self.spinners.get(img_url)  # Safely retrieve the spinner
        # label = self.labels.get(img_url)  # Retrieve the correct label for the URL
        if reply.error() == QNetworkReply.NoError:
            print("Image loaded successfully.")
            data = reply.readAll()
            print(f"Data length: {len(data)}")
            content_length = int(reply.rawHeader(b"Content-Length").data())
            print(f"Expected Content-Length: {content_length}")

            print(f"{len(data)}, {content_length}")

            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                # Store the original image
                self.original_images[img_url] = pixmap

                # Set the loaded image to the label
                label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))

                # Configure mouse events dynamically after successful load
                label.setMouseTracking(True)
                print(f"AQUI URL: {reply.url().toString()}")
                label.enterEvent = lambda event, lbl=label: self.show_zoom_window(event, lbl, img_url)
                label.leaveEvent = lambda event, lbl=label: self.clear_grid_and_hide_zoom(lbl)
                label.mouseMoveEvent = lambda event, lbl=label: self.update_zoom_position(event, lbl)
            else:
                print("Failed to load pixmap.")
                label.setText("Invalid Image")
        else:
            print(f"Failed to load image: {reply.error()}")
            label.setText("Failed to load")

        # Safely stop and delete spinner
        if spinner:
            spinner.stop()
            spinner.deleteLater()
            # del self.spinners[img_url]  # Remove spinner from tracking
        reply.deleteLater()

    def clear_images(self):
        """Clear the current images in the carousel."""
        while self.image_layout.count():
            child = self.image_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def show_zoom_window(self, event, label, img_url):
        """Show a zoomed-in portion of the image based on the QLabel's pixmap."""
        if self.hover_zoom_window is not None:
            self.hover_zoom_window.close()

        # Retrieve the original image
        if img_url in self.original_images:
            pixmap = self.original_images[img_url]
            self.hover_zoom_window = HoverZoomWindow(pixmap, self.parent())
            self.hover_zoom_window.show()
            self.update_zoom_position(event, label)
        else:
            print("No pixmap available for zooming.")

    def clear_grid_and_hide_zoom(self, label):
        """Clear the grid from the label and hide the zoom window."""
        self.restore_original_pixmap(label)
        self.hide_zoom_window()

    def restore_original_pixmap(self, label):
        """Restore the original pixmap of the label."""
        if hasattr(label, "_original_pixmap"):
            label.setPixmap(label._original_pixmap)
            label.update()
            del label._original_pixmap

    def hide_zoom_window(self):
        """Hide the zoom window when leaving the hover area."""
        if self.hover_zoom_window:
            self.hover_zoom_window.close()
            self.hover_zoom_window = None

    def update_zoom_position(self, event, label):
        """Update the zoomed area dynamically based on mouse position."""
        if self.hover_zoom_window:
            local_pos = event.pos()
            label_width, label_height = label.width(), label.height()
            pixmap_width, pixmap_height = (
                label.pixmap().size().width(),
                label.pixmap().size().height(),
            )

            # Correct proportional mapping based on pixmap scaling
            scale_x = pixmap_width / label_width
            scale_y = pixmap_height / label_height

            pixmap_x = int(local_pos.x() * scale_x)
            pixmap_y = int(local_pos.y() * scale_y)

            # Adjust zoom to center on the mouse position
            zoom_x = max(0, min(pixmap_x - 20, pixmap_width - 40))
            zoom_y = max(0, min(pixmap_y - 20, pixmap_height - 40))

            print("=================")
            print(f"scale_x: {scale_x}, scale_y: {scale_y}")
            print(f"{label_width}, {label_height}, {pixmap_width}, {pixmap_height}")
            print(f"{zoom_x}, {zoom_y}")
            print(f"{pixmap_width}, {pixmap_height}")
            print(f"{pixmap_x}, {pixmap_y}")
            print("=================")
            # self.hover_zoom_window.update_zoom(QPoint(zoom_x, zoom_y))
            self.hover_zoom_window.update_zoom(QPoint(zoom_x, zoom_y), scale_x, scale_y)

            # Save original pixmap if not already saved
            if not hasattr(label, "_original_pixmap"):
                label._original_pixmap = label.pixmap().copy()

            # Draw grid on the original image
            pixmap = label._original_pixmap.copy()
            painter = QPainter(pixmap)
            pen = QPen(QColor(0, 0, 255, 128))  # Semi-transparent blue
            pen.setWidth(1)
            painter.setPen(pen)

            grid_size = 2
            for gx in range(zoom_x, zoom_x + 40, grid_size):
                for gy in range(zoom_y, zoom_y + 40, grid_size):
                    painter.drawPoint(gx, gy)

            painter.end()
            label.setPixmap(pixmap)
            label.update()

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
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.w = 360
        self.h = 360
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("border: 1px solid black; background-color: white;")

        self.setFixedSize(self.w, self.h)
        self.move(parent.geometry().center() - QPoint(self.w // 2, self.h // 2))

        # self.img_path = img_path
        # self.pixmap = QPixmap(img_path)
        self.pixmap = pixmap
        self.zoom_label = QLabel(self)
        self.zoom_label.setFixedSize(self.w, self.h)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        # Get the original image size
        self.original_width = pixmap.width()
        self.original_height = pixmap.height()
        self.scaled_w = (self.w / 100) * self.original_width
        self.scaled_h = (self.h / 100) * self.original_height
        self.scale_x = self.scaled_w / self.w
        self.scale_y = self.scaled_h / self.h
        print(f"HOLAA=== {self.scale_x}; {self.scale_y}")
        # self.update_zoom(QPoint(50, 50))
        # self.update_zoom(QPoint(50, 50), 1, 1)

    def update_zoom(self, pos, scale_x, scale_y):
        """Update the zoomed-in portion of the image dynamically."""
        max_scale = max(self.scale_x, self.scale_y)
        zoom_size = round(40 * max_scale)
        print(zoom_size // 2)
        print(f"{self.original_width}; {self.original_height}")
        print(f"QRECT ===== {pos.x()}, {pos.y()}")
        print(f"Max_X = {max(0, pos.x())}")
        print(f"Max_Y = {max(0, pos.y())}")
        print(f"ScaleX: {self.scale_x}; ScakeY: {self.scale_y}")
        source_rect = QRect(
            round(max(0, pos.x()) * self.scale_x),
            round(max(0, pos.y()) * self.scale_y),
            zoom_size,
            zoom_size,
        )

        zoomed_pixmap = self.pixmap.copy(source_rect).scaled(self.w, self.h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.zoom_label.setPixmap(zoomed_pixmap)
