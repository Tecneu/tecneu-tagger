from PyQt5.QtWidgets import QTextEdit, QWidget, QPushButton, QLineEdit, QHBoxLayout, QVBoxLayout, QFrame, QLabel, \
    QScrollArea
from PyQt5.QtGui import QIntValidator, QPixmap, QColor, QPalette, QPen, QPainter
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QRect, QTimer

from font_config import FontManager

# ui/custom_widgets.py
__all__ = ['CustomTextEdit', 'SpinBoxWidget']


class CustomTextEdit(QTextEdit):
    def insertFromMimeData(self, source):
        if source.hasText():
            text = source.text()
            # Elimina espacios en blanco y comillas dobles al principio y al final
            text = text.strip().strip('"')
            (super(CustomTextEdit, self)
             .insertPlainText(text))  # Usa insertPlainText para evitar la inserción de texto formateado


class SpinBoxWidget(QWidget):
    valueChanged = pyqtSignal(int)  # Definir una nueva señal que pasa el valor actual

    def __init__(self, parent=None):
        super(SpinBoxWidget, self).__init__(parent)

        fonts = FontManager.get_fonts()
        robotoRegularFont = None
        if fonts and 'robotoRegularFont' in fonts:
            robotoRegularFont = fonts['robotoRegularFont']

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
        elif value != '':
            return

        value = int(value or 0)
        if value < 999:
            self.setValue(str(value + 1))

    def decrementValue(self):
        value = self.lineEdit.text()
        if value.isdigit():
            value = int(value)
        elif value != '':
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

        # Set semi-transparent background
        palette = self.palette()
        color = QColor(255, 255, 255, 51)  # 20% opacity
        palette.setColor(QPalette.Window, color)
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        self.main_layout = QVBoxLayout()
        self.image_layout = QHBoxLayout()
        self.image_layout.setSpacing(20)  # Set spacing between images
        self.main_layout.addLayout(self.image_layout)
        self.setLayout(self.main_layout)

        self.setFixedHeight(200)
        self.images = []
        self.hover_zoom_window = None
        self.last_label = None  # To track the last label with a grid

    def set_images(self, images):
        """Add images to the carousel."""
        self.clear_images()
        self.images = images
        for img_path in images:
            label = QLabel()
            pixmap = QPixmap(img_path)
            scaled_pixmap = pixmap.scaled(140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(scaled_pixmap)
            label.setAlignment(Qt.AlignCenter)
            label.setFixedSize(140, 140)
            label.setStyleSheet("border: 1px solid gray; position: relative;")
            label.setMouseTracking(True)
            label.enterEvent = lambda event, path=img_path, lbl=label: self.show_zoom_window(event, path, lbl)
            label.leaveEvent = lambda event, lbl=label: self.clear_grid_and_hide_zoom(lbl)
            label.mouseMoveEvent = lambda event, lbl=label: self.update_zoom_position(event, lbl)
            self.image_layout.addWidget(label)

    def clear_images(self):
        """Clear the current images in the carousel."""
        while self.image_layout.count():
            child = self.image_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def show_zoom_window(self, event, img_path, label):
        """Show a zoomed-in portion of the image based on hover position."""
        if self.hover_zoom_window is not None:
            self.hover_zoom_window.close()

        self.hover_zoom_window = HoverZoomWindow(img_path, self.parent())
        self.hover_zoom_window.show()
        self.update_zoom_position(event, label)

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
            pixmap_width, pixmap_height = label.pixmap().size().width(), label.pixmap().size().height()

            # Correct proportional mapping based on pixmap scaling
            scale_x = pixmap_width / label_width
            scale_y = pixmap_height / label_height

            pixmap_x = int(local_pos.x() * scale_x)
            pixmap_y = int(local_pos.y() * scale_y)

            # Adjust zoom to center on the mouse position
            zoom_x = max(0, min(pixmap_x - 20, pixmap_width - 40))
            zoom_y = max(0, min(pixmap_y - 20, pixmap_height - 40))

            print("=================")
            print(f"{zoom_x}, {zoom_y}")
            print(f"{pixmap_width}, {pixmap_height}")
            print(f"{pixmap_x}, {pixmap_y}")
            print("=================")
            self.hover_zoom_window.update_zoom(QPoint(zoom_x, zoom_y))

            # Save original pixmap if not already saved
            if not hasattr(label, '_original_pixmap'):
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


class HoverZoomWindow(QWidget):
    def __init__(self, img_path, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("border: 1px solid black; background-color: white;")

        self.setFixedSize(420, 420)
        self.move(parent.geometry().center() - QPoint(210, 210))

        self.pixmap = QPixmap(img_path)
        self.zoom_label = QLabel(self)
        self.zoom_label.setFixedSize(420, 420)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.update_zoom(QPoint(70, 70))

    def update_zoom(self, pos):
        """Update the zoomed-in portion of the image dynamically."""
        ratio = 1.6
        zoom_size = round(40 * ratio)
        print(zoom_size // 2)
        print(f"QRECT ===== {pos.x()}, {pos.y()}")
        print(f"Max_X = {max(0, pos.x())}")
        print(f"Max_Y = {max(0, pos.y())}")
        source_rect = QRect(
            round(max(0, pos.x()) * ratio),
            round(max(0, pos.y()) * ratio),
            # round(60 * ratio), round(60 * ratio),
            zoom_size,
            zoom_size
        )

        zoomed_pixmap = self.pixmap.copy(source_rect).scaled(420, 420, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.zoom_label.setPixmap(zoomed_pixmap)
