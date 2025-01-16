import os
import re
import threading

import requests
from PyQt5.QtCore import QEvent, QSize, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QMovie, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QStackedLayout, QVBoxLayout, QWidget

from config import BASE_ASSETS_PATH
from utils import normalize_zpl


class LabelViewer(QWidget):
    # Definir una señal que pueda enviar un booleano indicando el éxito de la carga y una cadena con el mensaje
    imageLoaded = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.last_zpl = ""  # Almacena la última versión del ZPL relevante
        self.last_load_successful = True  # Índica si la última carga fue exitosa

    def init_ui(self):
        self.setWindowTitle("Label Preview")
        self.setGeometry(100, 100, 400, 300)

        # Cambiamos QVBoxLayout a QStackedLayout para que la imagen y el spinner se superpongan
        self.layout = QStackedLayout()
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)  # Asegurar que la imagen esté centrada

        # self.button = QPushButton('Generate Label Preview', self)

        # Configuración del spinner
        self.spinner = QLabel(self)
        self.spinner.setAlignment(Qt.AlignCenter)
        self.spinner_movie = QMovie(os.fspath(BASE_ASSETS_PATH / "icons" / "spinner.gif"))
        self.spinner_movie.setScaledSize(QSize(120, 120))
        self.spinner.setMovie(self.spinner_movie)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.spinner)  # Agregamos el spinner al layout

        # Contenedor para el botón (para que no esté en el mismo stack)
        # button_container = QVBoxLayout()
        # button_container.addWidget(self.button)
        # button_container.addStretch()

        # La disposición principal de la ventana ahora incluye el stack y el contenedor del botón
        main_layout = QVBoxLayout()
        main_layout.addLayout(self.layout)
        # main_layout.addLayout(button_container)
        self.setLayout(main_layout)

        # self.button.clicked.connect(self.preview_label)
        self.spinner.setVisible(False)  # Ocultar el spinner al inicio

        # Temporizador para controlar el tiempo de visualización del spinner
        self.timer = QTimer()
        self.timer.setInterval(600)  # Tiempo de visualización del spinner
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_spinner)

    def preview_label(self, zpl_label):
        current_zpl = self._strip_pq(zpl_label)  # Obtener ZPL sin información de cantidad
        if current_zpl != self.last_zpl or not self.last_load_successful:
            self.last_zpl = current_zpl
            self._start_loading(zpl_label)

    def _start_loading(self, zpl_label):
        # Mostrar el spinner y empezar el temporizador
        self.layout.setCurrentWidget(self.spinner)
        self.spinner.setVisible(True)
        self.spinner_movie.start()
        self.timer.start()

        # Limpiar la etiqueta anterior y preparar para mostrar la imagen
        self.label.clear()

        # Ejecutar la carga de la imagen en un hilo separado para no bloquear la GUI
        threading.Thread(target=self.load_image, args=(zpl_label,), daemon=True).start()

    def _strip_pq(self, zpl_code):
        # Elimina la información de cantidad de copias (PQ) del ZPL para comparaciones
        return re.sub(r"\^PQ\d+,\d+,\d+,\w", "", zpl_code)

    def load_and_display_image(self, zpl_label):
        # Calcular las dimensiones dentro del hilo para evitar condiciones de carrera
        dimensions = self.estimate_zpl_dimensions(zpl_label)
        label_size = f"{round(dimensions[0], 2)}x{round(dimensions[1], 2)}"
        image_data = get_image_from_zpl(zpl_label, label_size)

        # Postear un evento personalizado o usar signals para actualizar la interfaz de usuario de forma segura
        if image_data:
            # Asegurarse de que la actualización de la UI se haga en el hilo principal
            QApplication.instance().postEvent(self, ImageLoadedEvent(image_data))
        else:
            QApplication.instance().postEvent(self, ImageLoadedEvent(None))

    def load_image(self, zpl_label):
        zpl_label = normalize_zpl(zpl_label)
        dimensions = self.estimate_zpl_dimensions(zpl_label)
        label_size = f"{round(dimensions[0], 2)}x{round(dimensions[1], 2)}"
        image_data = get_image_from_zpl(zpl_label, label_size)
        if image_data:
            self.last_load_successful = True
            self.imageLoaded.emit(True, "Imagen cargada correctamente.")
        else:
            # Si la carga falla, prepara para un nuevo intento
            self.last_load_successful = False
            self.imageLoaded.emit(False, "Error al cargar la imagen.")

        # Ejecutar la actualización de la UI en el hilo principal
        QApplication.instance().postEvent(self, ImageLoadedEvent(image_data))

    def customEvent(self, event):
        # Este método se llama cuando 'postEvent' envía datos al hilo principal
        if isinstance(event, ImageLoadedEvent):
            if event.image_data:
                pixmap = QPixmap()
                pixmap.loadFromData(event.image_data)
                self.label.setPixmap(pixmap)
                self.label.adjustSize()
            else:
                self.label.setText("Error al cargar la imagen.")

    def clear_preview(self):
        self.label.clear()
        self.label.setText("No preview available.")
        self.layout.setCurrentWidget(self.label)

    def hide_spinner(self):
        # Ocultar el spinner y detener la animación
        self.spinner_movie.stop()
        self.spinner.setVisible(False)
        self.layout.setCurrentWidget(self.label)  # Cambiar al widget de la imagen

    def estimate_zpl_dimensions(self, zpl_code):
        max_x = max_y = 0
        min_x = min_y = float("inf")

        # Coordenadas de inicio
        for match in re.finditer(r"\^FO(\d+),(\d+)", zpl_code):
            x, y = int(match.group(1)), int(match.group(2))
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

        # Considerar altura de los códigos de barras
        for match in re.finditer(r"\^BC\w+,\s*(\d+)", zpl_code):
            barcode_height = int(match.group(1))
            max_y += barcode_height  # Asumiendo que el código de barras comienza en el último Y encontrado

        # Considerar ancho de campos de bloque y códigos de barras
        for match in re.finditer(r"\^FB(\d+)", zpl_code):
            block_width = int(match.group(1))
            max_x = max(max_x, block_width)  # Asumir que el campo de bloque comienza en el último X encontrado

        # Considerar el ancho definido en los campos de bloque `^FB`
        for match in re.finditer(r"\^FB(\d+),", zpl_code):
            block_width = int(match.group(1))
            # El ancho real utilizado será el máximo entre el definido por `^FO` y `^FB`
            max_x = max(max_x, min_x + block_width)

        for match in re.finditer(r"\^BY(\d+)", zpl_code):
            barcode_module_width = int(match.group(1))
            max_x += barcode_module_width * 10  # Aproximación del ancho del código de barras

        # Convertir puntos a pulgadas usando 203 DPI
        width_in_inches = ((max_x - min_x) / 203) + 0.02
        height_in_inches = (max_y - min_y) / 203
        # print("Estimated Dimensions (Width x Height in inches):", width_in_inches, height_in_inches)
        return (width_in_inches, height_in_inches)


def get_image_from_zpl(zpl_label, label_size):
    # print(label_size)
    # print(zpl_label)
    print_density = "8dpmm"
    url = f"http://api.labelary.com/v1/printers/{print_density}/labels/{label_size}/0"
    headers = {
        "Accept": "image/png",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    response = requests.post(url, headers=headers, data=zpl_label)
    if response.status_code == 200:
        return response.content
    else:
        print("Failed to get label:", response.status_code, response.text)
        return None


class ImageLoadedEvent(QEvent):
    # Definición del evento personalizado
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, image_data):
        super().__init__(ImageLoadedEvent.EVENT_TYPE)
        self.image_data = image_data
