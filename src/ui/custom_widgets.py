from PyQt5.QtWidgets import QTextEdit, QWidget, QPushButton, QLineEdit, QHBoxLayout, QVBoxLayout, QFrame, QLabel, QScrollArea
from PyQt5.QtGui import QIntValidator, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal

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
        self.setStyleSheet("background-color: white; border: 1px solid gray;")

        self.main_layout = QVBoxLayout()
        self.image_layout = QHBoxLayout()
        self.main_layout.addLayout(self.image_layout)
        self.setLayout(self.main_layout)

        self.setFixedHeight(120)

    def set_images(self, images):
        """Add images to the carousel."""
        self.clear_images()
        for img_path in images:
            label = QLabel()
            pixmap = QPixmap(img_path).scaledToHeight(180, Qt.SmoothTransformation)
            label.setPixmap(pixmap)
            label.setAlignment(Qt.AlignCenter)
            label.mousePressEvent = lambda event, path=img_path: self.expand_image(path)
            self.image_layout.addWidget(label)

    def clear_images(self):
        """Clear the current images in the carousel."""
        while self.image_layout.count():
            child = self.image_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def expand_image(self, img_path):
        """Expand the selected image to cover both the main and carousel windows."""
        expanded_window = ImageZoomWindow(img_path, self.parent())
        expanded_window.show()


class ImageZoomWindow(QWidget):
    def __init__(self, img_path, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.image_label = QLabel()
        self.image_label.setPixmap(QPixmap(img_path).scaledToWidth(800, Qt.SmoothTransformation))
        self.image_label.setAlignment(Qt.AlignCenter)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setWidgetResizable(True)

        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_in_button.clicked.connect(self.zoom_in)

        self.zoom_out_button = QPushButton("Zoom Out")
        self.zoom_out_button.clicked.connect(self.zoom_out)

        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.zoom_in_button)
        self.button_layout.addWidget(self.zoom_out_button)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addLayout(self.button_layout)
        self.setLayout(self.main_layout)

    def zoom_in(self):
        current_pixmap = self.image_label.pixmap()
        if current_pixmap:
            new_size = current_pixmap.size() * 1.2
            self.image_label.setPixmap(current_pixmap.scaled(new_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def zoom_out(self):
        current_pixmap = self.image_label.pixmap()
        if current_pixmap:
            new_size = current_pixmap.size() * 0.8
            self.image_label.setPixmap(current_pixmap.scaled(new_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
