import json
import os
import re
import sys

from PyQt5.QtCore import QSettings, QSize, Qt, QThreadPool, QTimer
from PyQt5.QtGui import QColor, QIcon, QMovie, QPixmap, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from api.endpoints import APIEndpoints
from config import BASE_ASSETS_PATH, LABEL_SIZES, MAX_DELAY
from font_config import FontManager
from print_thread import PrintThread
from utils import list_printers_to_json
from workers.search_by_zpl_worker import ZplWorker
from workers.search_worker import SearchWorker

from .custom_widgets import CustomComboBox, CustomSearchBar, CustomTextEdit, ImageCarousel, SpinBoxWidget, ToggleSwitch
from .zpl_preview import LabelViewer

__all__ = ["MainWindow"]

json_printers = json.loads(list_printers_to_json())


class MainWindow(QWidget):
    """
    Clase principal de la ventana que gestiona la interfaz de usuario y las interacciones.
    """

    def __init__(self):
        super().__init__()
        self.settings = QSettings("Tecneu", "TecneuTagger")
        self.api = APIEndpoints()

        # Para gestionar tareas en segundo plano
        self.threadpool = QThreadPool()

        # Crea un overlay pero no lo muestres aún
        self.loading_overlay = None

        self.updating_zpl_from_result = False
        self.latest_item_data = None

        self.print_thread = None
        self.selected_printer_name = None  # Inicializa la variable para almacenar el nombre de la impresora seleccionada
        self.is_paused = False  # Inicializa un atributo para llevar el seguimiento del estado de pausa
        self.slider_label_timer = QTimer(self)
        self.slider_label_timer.setInterval(2000)  # 2000 ms = 2 s
        self.slider_label_timer.setSingleShot(True)
        self.updating_copies = False  # Flag para controlar la recursión entre métodos
        self.updating_zpl = False  # Flag para controlar la recursión entre métodos
        self.init_ui()
        self.loadSettings()
        self.connect_buttons()

        self.slider_label_timer.timeout.connect(self.slider_label_frame.hide)
        self.slider_label_timer.timeout.connect(self.slider_label.hide)
        self.slider_label_timer.timeout.connect(self.saveSliderValue)

        self.delay_update_timer = QTimer(self)
        self.delay_update_timer.setInterval(700)  # 700 ms de retardo
        self.delay_update_timer.setSingleShot(True)
        self.delay_update_timer.timeout.connect(self.apply_delay_change_arrows)

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.clear_status_message)

        self.space_press_timer = QTimer(self)
        self.space_press_timer.setInterval(240)  # 400 ms para la detección de doble clic
        self.space_press_timer.setSingleShot(True)
        self.space_press_timer.timeout.connect(self.handle_single_space_press)
        self.space_press_count = 0

    def apply_new_delay(self):
        # Aplica el nuevo delay al hilo de impresión
        new_delay = self.delay_slider.value()
        if self.print_thread is not None:
            self.print_thread.set_delay(new_delay)

    def loadSettings(self):
        # Cargar el nombre de la impresora seleccionada
        printer_name = self.settings.value("printer_name", "")
        index = self.printer_selector.findText(printer_name)
        if index != -1:
            self.printer_selector.setCurrentIndex(index)

        # Cargar el último valor del delay slider
        delay_value = self.settings.value("delay_value", 25, type=int)
        self.delay_slider.setValue(delay_value)

    def saveSliderValue(self):
        self.settings.setValue("delay_value", self.delay_slider.value())

    def show_error_message(self, message):
        QMessageBox.critical(self, "Error", message)

    def show_loading_overlay(self):
        """Muestra un overlay translúcido con un spinner en el centro."""
        if self.loading_overlay is not None:
            return  # Ya está mostrado

        # 1) Crear el overlay "flotante" encima de MainWindow
        self.loading_overlay = QFrame(self)
        self.loading_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 125);")  # ~50% opacidad
        self.loading_overlay.setGeometry(self.rect())  # Cubre toda la ventana

        # 2) Crear un layout para centrar el spinner
        layout = QVBoxLayout(self.loading_overlay)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        # 3) Crear un QLabel con el QMovie (spinner.gif)
        self.spinner_label = QLabel()
        self.spinner_label.setStyleSheet("background-color: transparent; border: none;")
        # self.spinner_label.setAttribute(Qt.WA_TranslucentBackground)
        spinner_path = os.fspath(BASE_ASSETS_PATH / "icons" / "spinner_overlay.gif")
        self.spinner_movie = QMovie(spinner_path)
        self.spinner_movie.setScaledSize(QSize(180, 180))
        self.spinner_label.setMovie(self.spinner_movie)

        layout.addWidget(self.spinner_label, alignment=Qt.AlignCenter)

        # Mostrar
        self.loading_overlay.show()
        self.spinner_movie.start()

    def hide_loading_overlay(self):
        """Oculta el overlay con el spinner."""
        if self.loading_overlay is not None:
            self.loading_overlay.hide()
            self.spinner_movie.stop()
            self.loading_overlay = None

    def init_ui(self):
        """
        Configura la interfaz de usuario de la ventana principal.
        """
        fonts = FontManager.get_fonts()
        robotoBoldFont = None
        robotoRegularFont = None
        digitalBoldFont = None
        mystericFont = None
        if fonts and "robotoBoldFont" in fonts:
            robotoBoldFont = fonts["robotoBoldFont"]
        if fonts and "robotoRegularFont" in fonts:
            robotoRegularFont = fonts["robotoRegularFont"]
        if fonts and "digitalBoldFont" in fonts:
            digitalBoldFont = fonts["digitalBoldFont"]
        if fonts and "mystericFont" in fonts:
            mystericFont = fonts["mystericFont"]

        self.setWindowTitle("Tecneu - Tagger")
        self.setGeometry(800, 100, 850, 400)  # x, y, width, height

        # Establecer el tamaño mínimo de la ventana
        self.setMinimumSize(850, 400)

        # self.setStyleSheet("background-color: lightblue;")

        main_layout = QHBoxLayout()  # Usar QHBoxLayout para dividir la ventana
        control_layout = QVBoxLayout()

        # Define un nuevo widget para la vista previa de etiquetas
        self.labelViewer = LabelViewer()
        control_layout.addWidget(self.labelViewer)

        # Configuración del QSlider para el retraso
        self.delay_slider_layout = QHBoxLayout()
        self.delay_slider = QSlider(Qt.Horizontal)
        self.delay_slider.setMinimum(1)
        self.delay_slider.setMaximum(MAX_DELAY)
        self.delay_slider.setValue(round(MAX_DELAY / 2))  # Valor predeterminado
        self.delay_slider.setTickInterval(1)
        self.delay_slider.setTickPosition(QSlider.TicksBelow)
        self.delay_slider.valueChanged.connect(self.update_slider_label)
        self.delay_slider.sliderReleased.connect(self.apply_delay_change)

        self.delay_slider.setStyleSheet(
            """
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 6px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #51acff;
                border: 6px solid #6b6b6b;
                width: 16px;
                height: 16px;
                margin: -6px 0px;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                border: 2px solid #6b6b6b;
                width: 22px;
                height: 22px;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:pressed {
                border: 8px solid #6b6b6b;
                width: 8px;
                height: 8px;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                /* background: transparent;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #66e, stop:1 #bbf);
                background: qlineargradient(x1: 0, y1: 0.2, x2: 1, y2: 1, stop: 0 #bbf, stop: 1 #55f); */
                background: #51acff;
                border: none;
                height: 6px;
                border-radius: 4px;
            }
            QSlider::add-page:horizontal {
                background: transparent;
                border: none;
                height: 6px;
                border-radius: 4px;
            }
        """
        )

        # Icono de tortuga para el lado lento
        self.turtle_icon_label = QLabel()
        turtle_pixmap = QPixmap(os.fspath(BASE_ASSETS_PATH / "icons" / "turtle-du.svg")).scaled(35, 35, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.turtle_icon_label.setPixmap(turtle_pixmap)
        self.delay_slider_layout.addWidget(self.turtle_icon_label)

        self.delay_slider_layout.addWidget(self.delay_slider)

        # Icono de conejo para el lado rápido
        self.rabbit_icon_label = QLabel()
        rabbit_pixmap = QPixmap(os.fspath(BASE_ASSETS_PATH / "icons" / "rabbit-running-du.svg")).scaled(35, 35, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.rabbit_icon_label.setPixmap(rabbit_pixmap)
        self.delay_slider_layout.addWidget(self.rabbit_icon_label)

        self.slider_label_frame = QFrame(self)
        # border: 1px solid gray;
        self.slider_label_frame.setStyleSheet(
            """
            background-color: white;
            border: 1px solid gray;
            border-radius: 5px;
            padding: 0px;
            margin: 0px;
        """
        )
        self.slider_label_frame.setLayout(QVBoxLayout())
        self.slider_label_frame.layout().setContentsMargins(0, 0, 0, 0)
        self.slider_label_frame.layout().setAlignment(Qt.AlignCenter)
        self.slider_label_frame.setFixedSize(26, 24)
        self.slider_label_frame.raise_()  # Asegura que el frame del slider esté siempre en primer plano

        # Asegúrate de llamar a self.raise_slider_labels() después de cualquier operación que afecte la visibilidad
        self.labelViewer.imageLoaded.connect(self.raise_slider_labels)  # Suponiendo que imageLoaded es una señal emitida después de cargar la imagen

        # Slider label setup
        self.slider_label = QLabel(self.slider_label_frame)
        if robotoRegularFont:
            self.slider_label.setFont(robotoRegularFont)
        self.slider_label.setStyleSheet(
            """
            background-color: transparent;
            border: none;
            padding: 0px;
            margin: 0px;
        """
        )
        self.slider_label.setAlignment(Qt.AlignCenter)
        self.slider_label.setWordWrap(True)  # Enable word wrapping
        self.slider_label_frame.layout().addWidget(self.slider_label)

        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setBlurRadius(5)
        shadow_effect.setColor(QColor(0, 0, 0, 60))
        shadow_effect.setOffset(2, 2)
        self.slider_label_frame.setGraphicsEffect(shadow_effect)

        # Asegúrate de que el frame esté oculto inicialmente
        self.slider_label_frame.hide()

        control_layout.addLayout(self.delay_slider_layout)

        # Layout horizontal que contendrá dos contenedores verticales
        buttons_and_counter_layout = QHBoxLayout()

        # Contenedor y layout para los botones
        buttons_layout = QVBoxLayout()
        buttons_layout.setAlignment(Qt.AlignTop)
        buttons_frame = QFrame()
        buttons_frame.setLayout(buttons_layout)
        buttons_frame.setMinimumWidth(200)
        buttons_frame.setMaximumWidth(250)

        entry_frame = QFrame()
        entry_layout = QHBoxLayout(entry_frame)
        entry_layout.setContentsMargins(0, 0, 0, 0)
        entry_layout.setSpacing(0)

        self.copies_entry = SpinBoxWidget(entry_frame)
        # self.copies_entry.setPlaceholderText("Número de copias")
        # self.copies_entry.textChanged.connect(self.update_zpl_from_copies)
        self.copies_entry.valueChanged.connect(self.update_zpl_from_copies)

        # Contenedor para los botones
        button_container = QVBoxLayout()
        button_container.setSpacing(0)  # Eliminar espacio entre los botones
        entry_layout.addWidget(self.copies_entry)
        entry_layout.addLayout(button_container)
        buttons_layout.addWidget(entry_frame)

        self.control_button = QPushButton("Iniciar Impresión")
        self.control_button.clicked.connect(self.control_printing)
        if robotoBoldFont:
            self.control_button.setFont(robotoBoldFont)
        buttons_layout.addWidget(self.control_button)

        self.stop_button = QPushButton("Detener")
        self.stop_button.clicked.connect(self.stop_printing)
        if robotoBoldFont:
            self.stop_button.setFont(robotoBoldFont)
        buttons_layout.addWidget(self.stop_button)
        # Inicialmente, el botón de pausa está deshabilitado
        self.stop_button.setEnabled(False)

        # Contenedor y layout para el contador de etiquetas
        counter_frame = QFrame()
        counter_frame.setStyleSheet("background-color: #444; border: 1px solid black;")
        counter_frame.setMinimumWidth(150)
        counter_frame.setMaximumWidth(200)
        counter_layout = QVBoxLayout(counter_frame)
        counter_layout.setAlignment(Qt.AlignCenter)

        # Label para el título del contador
        self.title_label = QLabel("Etiquetas restantes:")
        self.title_label.setStyleSheet("color: white;")
        counter_layout.addWidget(self.title_label)

        # Label para el número del contador
        self.count_label = QLabel("0")
        if robotoBoldFont:
            self.count_label.setFont(digitalBoldFont)
        self.count_label.setStyleSheet("color: yellow; font-size: 65px;")
        self.count_label.setAlignment(Qt.AlignRight)
        counter_layout.addWidget(self.count_label)

        # Agregar un espacio flexible para alinear los elementos a la derecha si alcanzan el ancho máximo
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        buttons_and_counter_layout.addSpacerItem(spacer)

        # Añadir los dos contenedores al layout horizontal
        buttons_and_counter_layout.addWidget(counter_frame, stretch=1)
        buttons_and_counter_layout.addWidget(buttons_frame, stretch=1)

        # Agregar el layout horizontal al control_layout
        control_layout.addLayout(buttons_and_counter_layout)

        self.status_label = QLabel("")
        if mystericFont:
            self.status_label.setFont(mystericFont)
        self.status_label.setStyleSheet("color: #F27405; font-size: 17px;")
        control_layout.addWidget(self.status_label)

        # Layout para QTextEdit y el botón de borrar
        zpl_layout = QVBoxLayout()

        # Layout para el Search Bar
        search_layout = QHBoxLayout()
        # Campo de búsqueda
        self.search_bar = CustomSearchBar()
        self.search_bar.setPlaceholderText("Buscar por Inventory_id...")
        self.search_bar.setFixedHeight(30)
        self.search_bar.returnPressed.connect(self.execute_search)  # Buscar al presionar Enter
        # Conectamos la señal 'pasted' al método 'execute_search'
        self.search_bar.paste_event_filter.pasted.connect(self.execute_search)

        # Botón de búsqueda con icono de lupa
        self.search_button = QPushButton()
        search_icon = QIcon(os.fspath(BASE_ASSETS_PATH / "icons" / "search.svg"))  # Asegúrate de tener el ícono
        self.search_button.setIcon(search_icon)
        self.search_button.setFixedSize(30, 30)
        self.search_button.clicked.connect(self.execute_search)  # Buscar al hacer clic en la lupa

        # Creación del menú desplegable para las impresoras
        self.label_size_selector = CustomComboBox()
        self.label_size_selector.setMinimumSize(70, 30)
        self.label_size_selector.setMaximumWidth(200)
        self.label_size_selector.setStyleSheet(
            """
        QListView::item{
            padding: 5px 10px;
        }
        """
        )

        self.label_size_selector.currentIndexChanged.connect(self.update_label_size_icon)
        model = QStandardItemModel()

        # Crea el ítem "Seleccione una impresora" y hazlo no seleccionable
        defaultItem = QStandardItem(
            QIcon(os.fspath(BASE_ASSETS_PATH / "icons" / "badge_blue_check.svg")),
            "Seleccione un tamaño",
        )  # Texto que se muestra
        defaultItem.setData("", Qt.UserRole)  # Valor asociado
        defaultItem.setEnabled(False)  # Hace que el ítem sea no seleccionable
        model = QStandardItemModel()
        model.appendRow(defaultItem)

        # Filtra y agrega los nombres de las impresoras al menú desplegable
        # Poblar QComboBox con los datos
        # El 'title' se muestra al usuario y 'value' lo almacenamos como userData
        for size_item in LABEL_SIZES:
            qitem = QStandardItem()
            # El texto que se muestra al usuario
            qitem.setData(size_item["title"], Qt.DisplayRole)
            # El valor "oculto" (equivalente a userData)
            qitem.setData(size_item["value"], Qt.UserRole)

            model.appendRow(qitem)

        self.label_size_selector.setModel(model)
        self.label_size_selector.setCurrentIndex(1)  # Establece el primer tamaño como el valor por defecto
        # Asegúrate de que "Seleccione una impresora" no sea seleccionable después de la inicialización
        self.label_size_selector.model().item(0).setEnabled(False)

        self.label_size_selector.currentIndexChanged.connect(self.on_label_size_changed)

        # Botón para pegar del portapapeles
        self.paste_search_button = QPushButton()
        paste_icon = QIcon(os.fspath(BASE_ASSETS_PATH / "icons" / "paste.svg"))
        self.paste_search_button.setIcon(paste_icon)
        self.paste_search_button.setFixedSize(30, 30)
        self.paste_search_button.clicked.connect(self.paste_and_search)  # Buscar al pegar

        # Añadir widgets al layout del Search Bar
        search_layout.addWidget(self.search_bar)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.paste_search_button)
        search_layout.addWidget(self.label_size_selector)

        zpl_layout.addLayout(search_layout)

        self.zpl_textedit = CustomTextEdit()
        self.zpl_textedit.setPlaceholderText("Ingrese el ZPL aquí...")
        self.zpl_textedit.textChanged.connect(self.validate_and_update_copies_from_zpl)
        self.zpl_textedit.textPasted.connect(lambda: self.search_bar.setText(""))  # Conectar la señal al método adecuado
        zpl_layout.addWidget(self.zpl_textedit)

        # Configurar botones para el ZPL input/impresora
        zpl_buttons_layout = QHBoxLayout()
        # Creación del menú desplegable para las impresoras
        self.printer_selector = CustomComboBox()
        self.printer_selector.setMinimumHeight(30)
        self.printer_selector.setStyleSheet(
            """
        QListView::item{
            padding: 5px 10px;
        }
        """
        )

        self.printer_selector.currentIndexChanged.connect(self.update_printer_icon)
        model = QStandardItemModel()

        # Crea el ítem "Seleccione una impresora" y hazlo no seleccionable
        defaultItem = QStandardItem(
            QIcon(os.fspath(BASE_ASSETS_PATH / "icons" / "printer.svg")),
            "Seleccione una impresora",
        )
        defaultItem.setEnabled(False)  # Hace que el ítem sea no seleccionable
        model.appendRow(defaultItem)

        # Filtra y agrega los nombres de las impresoras al menú desplegable
        for printer in json_printers:
            if printer["EnableBIDI"] and printer["IsThermal"]:
                item = QStandardItem(printer["Name"])
                model.appendRow(item)

        self.printer_selector.setModel(model)
        self.printer_selector.setCurrentIndex(0)  # Establece "Seleccione una impresora" como el valor por defecto
        # Asegúrate de que "Seleccione una impresora" no sea seleccionable después de la inicialización
        self.printer_selector.model().item(0).setEnabled(False)

        self.printer_selector.currentTextChanged.connect(self.on_printer_selected)  # Conectar la señal al método
        zpl_buttons_layout.addWidget(self.printer_selector)

        # Botón para borrar el contenido de QTextEdit
        self.clear_zpl_button = QPushButton("Borrar ZPL")
        # Establecer el ícono en el botón
        self.clear_zpl_button.setIcon(QIcon(os.fspath(BASE_ASSETS_PATH / "icons" / "delete-left.svg")))
        self.clear_zpl_button.setStyleSheet(
            """
            QPushButton {
                text-align: left;
                padding: 5px 10px;
            }
            QPushButton::icon {
                position: absolute;
                left: 50px;  /* Alinear el ícono a la derecha */
            }
        """
        )
        # Establecer el tamaño del ícono (opcional)
        self.clear_zpl_button.setIconSize(QSize(20, 20))
        self.clear_zpl_button.clicked.connect(lambda: self.reset_all(True))
        zpl_buttons_layout.addWidget(self.clear_zpl_button)

        # Botón para pegar desde el portapapeles
        self.paste_zpl_button = QPushButton()
        self.paste_zpl_button.setIcon(QIcon(os.fspath(BASE_ASSETS_PATH / "icons" / "paste.svg")))
        self.paste_zpl_button.setStyleSheet(
            """
            QPushButton {
                padding: 5px;
                icon-size: 20px;
            }
        """
        )
        self.paste_zpl_button.clicked.connect(self.paste_from_clipboard)
        zpl_buttons_layout.addWidget(self.paste_zpl_button)

        self.toggle_button = ToggleSwitch(checked=False)
        self.toggle_button.toggled.connect(self.toggle_always_on_top)
        zpl_buttons_layout.addWidget(self.toggle_button)

        zpl_layout.addLayout(zpl_buttons_layout)

        # Agregar los layouts al layout principal
        main_layout.addLayout(control_layout)
        main_layout.addLayout(zpl_layout)  # Añadir el layout de ZPL al layout principal

        self.carousel = ImageCarousel(self)

        self.setLayout(main_layout)

    def reset_all(self, include_search_bar=True, include_zpl_textedit=True):
        self.carousel.hide_carousel()
        self.labelViewer.clear_preview()
        if include_zpl_textedit:
            self.zpl_textedit.clear()
        if include_search_bar:
            self.search_bar.clear()

    def execute_search(self, custom_search_text=None):
        """Executes a search using the text from the search bar."""
        search_text = custom_search_text or self.search_bar.text().strip()
        if not search_text and not custom_search_text:
            self.set_status_message(
                "Por favor ingresa un ID o código para buscar.",
                duration=5,
                countdown=True,
                color="#BD2A2E",
            )
            return

        self.copies_entry.setValue("0")
        # copies_str = self.copies_entry.text()

        index = self.label_size_selector.currentIndex()
        label_size = self.label_size_selector.itemData(index, Qt.UserRole)
        query_params = {
            "label_size": label_size,
            # "qty": copies_str if copies_str.isdigit() else "0",
            "qty": "0",
        }

        self.reset_all(False)

        # 1) Muestra overlay + spinner
        self.show_loading_overlay()

        # 2) Crea el worker
        worker = SearchWorker(self.api, search_text, query_params)

        # 3) Conecta la señal finished a la función que procesa el resultado
        worker.signals.finished.connect(self.handle_search_result)

        # 4) Inicia el worker en el pool
        self.threadpool.start(worker)

    def handle_search_result(self, item):
        """Se llama cuando la tarea en segundo plano termina."""
        # Oculta el overlay
        self.hide_loading_overlay()

        if item and "label" in item:
            # 1) Guardamos el item por si luego lo usamos
            self.latest_item_data = item
            # 2) Activamos el flag para indicar que vamos a cambiar 'zpl_textedit' desde el código
            self.updating_zpl_from_result = True

            # 3) Este setPlainText dispara textChanged, por lo que
            #    en validate_and_update_copies_from_zpl podemos saber
            #    que NO debe volver a llamar a la API, sino usar 'latest_item_data'
            self.zpl_textedit.setPlainText(item["label"])  # Pega el ZPL en el campo
            self.latest_item_data = item  # Guarda la respuesta completa para otras funciones
            self.set_status_message("Etiqueta cargada correctamente.", duration=3, color="#28A745")
        else:
            self.set_status_message(
                "No se encontró ningún resultado.",
                duration=5,
                countdown=True,
                color="#BD2A2E",
            )

    def paste_and_search(self):
        """Pega el contenido del portapapeles y ejecuta la búsqueda."""
        clipboard_text = QApplication.clipboard().text().strip().strip('"')
        # print(f"====================================> {clipboard_text}")
        if clipboard_text:
            self.search_bar.setText(clipboard_text)
            self.execute_search()
        else:
            self.set_status_message(
                "El portapapeles está vacío.",
                duration=5,
                countdown=True,
                color="#BD2A2E",
            )

    # Asegúrate de llamar a esta función después de operaciones que cambian la visibilidad o el orden de los widgets
    def raise_slider_labels(self):
        self.slider_label_frame.raise_()  # Vuelve a poner el frame del slider en primer plano
        if self.slider_label.isVisible():
            self.slider_label.raise_()  # También maneja la etiqueta del slider si es necesario

    def connect_buttons(self):
        # Conecta todos los botones a la función que manejará el clic
        for button in self.findChildren(QPushButton):
            button.clicked.connect(self.handle_button_click)

        for slider in self.findChildren(QSlider):
            slider.sliderReleased.connect(self.handle_widget_interaction)

        for combo in self.findChildren(QComboBox):
            combo.currentIndexChanged.connect(self.handle_widget_interaction)

    #
    def handle_button_click(self):
        """
        Maneja el evento de clic en cualquier botón y limpia el foco.
        """
        self.clear_focus()

    def handle_widget_interaction(self):
        """
        Maneja la interacción con sliders y comboboxes, y limpia el foco.
        """
        self.clear_focus()

    def set_status_message(self, message, duration=None, countdown=False, color="#F27405"):
        """
        Establece un mensaje de estado con una duración opcional y cuenta regresiva.

        Args:
        message (str): El mensaje a mostrar.
        duration (int, optional): Duración en segundos para mostrar el mensaje. None para indefinido.
        countdown (bool, optional): Si es True, muestra la cuenta regresiva junto al mensaje.
        color (str, optional): Código de color para el mensaje.
        """
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 17px;")
        if duration:
            self.countdown = duration
            if countdown:
                self.status_label.setText(f"{message} ({self.countdown} s)")
            self.status_timer.start(1000)  # Cada segundo
        else:
            self.status_timer.stop()

    def clear_status_message(self):
        """
        Limpia el mensaje de estado y detiene el temporizador si no es indefinido.
        """
        if self.countdown > 1:
            self.countdown -= 1
            self.status_label.setText(f"{self.status_label.text().split('(')[0]}({self.countdown} s)")
        else:
            self.status_label.setText("")
            self.status_timer.stop()

    def paste_from_clipboard(self):
        self.search_bar.setText("")
        clipboard = QApplication.clipboard()
        # Elimina espacios en blanco y comillas dobles al principio y al final
        text = clipboard.text().strip().strip('"')
        if text == "":
            self.set_status_message("No hay texto para pegar.", duration=5, countdown=True, color="#BD2A2E")
            return

        self.zpl_textedit.setPlainText(text)  # Pegar como texto plano

    def update_printer_icon(self, index):
        # Eliminar el ícono de todos los ítems
        for i in range(self.printer_selector.count()):
            self.printer_selector.setItemIcon(i, QIcon())

        # Establecer el ícono solo en el ítem seleccionado
        if index != 0:  # Asumiendo que el índice 0 es "Seleccione una impresora"
            (self.printer_selector.setItemIcon(index, QIcon(os.fspath(BASE_ASSETS_PATH / "icons" / "printer.svg"))))

    def update_label_size_icon(self, index):
        # Eliminar el ícono de todos los ítems
        for i in range(self.label_size_selector.count()):
            self.label_size_selector.setItemIcon(i, QIcon())

        # Establecer el ícono solo en el ítem seleccionado
        if index != 0:  # Asumiendo que el índice 0 es "Seleccione una impresora"
            (self.label_size_selector.setItemIcon(index, QIcon(os.fspath(BASE_ASSETS_PATH / "icons" / "badge_blue_check.svg"))))

    def increment(self):
        self.copies_entry.incrementValue()

    def decrement(self):
        self.copies_entry.decrementValue()

    def apply_delay_change(self):
        """
        Aplica el nuevo delay al hilo de impresión.
        """
        if self.print_thread is not None:
            self.print_thread.apply_delay_change()

    def apply_delay_change_arrows(self):
        """
        Aplica el nuevo delay al hilo de impresión desde las flechas.
        """
        new_delay = self.delay_slider.value()
        if self.print_thread is not None:
            self.print_thread.set_delay(new_delay)
            self.print_thread.apply_delay_change()

    # Modificar update_slider_label para ajustar la posición del frame
    def update_slider_label(self, value):
        # Actualiza el delay en el hilo de impresión en tiempo real
        if self.print_thread is not None:
            self.print_thread.set_delay(value)

        self.slider_label.setText(str(value))
        slider_pos = self.delay_slider.pos()
        slider_length = self.delay_slider.width()
        slider_value = (value - self.delay_slider.minimum()) / (self.delay_slider.maximum() - self.delay_slider.minimum())
        slider_offset = int(slider_length * slider_value - self.slider_label_frame.width() / 2)
        self.slider_label_frame.move(slider_pos.x() + slider_offset, slider_pos.y() - 40)
        self.slider_label_frame.show()
        self.slider_label.show()

        # Reinicia el temporizador cada vez que el valor del slider cambia
        self.slider_label_timer.stop()
        self.slider_label_timer.start(2000)  # Asumiendo que slider_label_timer ya está configurado

    def validate_and_update_copies_from_zpl(self):
        if self.updating_zpl:  # Evita la recursión si update_zpl_from_copies ya está en proceso
            return

        self.updating_copies = True

        # 1) Detectar si este cambio viene de handle_search_result
        if self.updating_zpl_from_result:
            # a) Desactivamos el flag
            self.updating_zpl_from_result = False
            if self.latest_item_data:
                # b) Tenemos 'item' en self.latest_item_data.
                item = self.latest_item_data

                # c) Parseamos el ZPL para actualizar copias, preview, etc. (opcional)
                zpl_text = self.zpl_textedit.toPlainText().strip()
                self.parse_zpl_and_update_ui(zpl_text)

                # d) Usamos el 'item' para, por ejemplo, mostrar imágenes, etc.
                self.use_item_data(item)
            self.latest_item_data = None
            self.updating_copies = False
            return

        # 2) Caso normal: el texto lo cambió el usuario
        zpl_text = self.zpl_textedit.toPlainText().strip()

        #    Validamos y, si es válido, o si necesitamos más datos del API,
        #    podemos llamar a otro Worker. Aquí lo encapsulamos en un método aparte:
        self.process_zpl_text_and_call_api_if_needed(zpl_text)

        self.updating_copies = False

    def parse_zpl_and_update_ui(self, zpl_text):
        """
        Ejemplo de parsing de ^PQ en el ZPL para actualizar self.copies_entry
        y quizá la vista previa local (si la tienes).
        """
        is_valid_zpl = self.is_valid_zpl(zpl_text)

        if not zpl_text or not is_valid_zpl:
            self.copies_entry.setValue("")
            if zpl_text and not is_valid_zpl:
                self.set_status_message(
                    "ZPL ingresado no es valido",
                    duration=5,
                    countdown=True,
                    color="#BD2A2E",
                )
            self.labelViewer.clear_preview()
            self.updating_copies = False
            return

        # En este punto, el ZPL es válido. Extraemos ^PQ y el barcode
        pq_index = zpl_text.find("^PQ")
        if pq_index != -1:
            # Encuentra el número de copias en el ZPL
            start_index = pq_index + 3
            end_index = zpl_text.find(",", start_index)

            if end_index == -1:
                end_index = len(zpl_text)

            copies_str = zpl_text[start_index:end_index]
            if copies_str.isdigit():
                self.copies_entry.setValue(copies_str)

            # Ajusta el ZPL para previsualizar con 1 copia
            new_zpl_text = zpl_text[:start_index] + "1,0,1,Y^XZ"
            print("ACTUALIZA PREVIEW LABEL=> parse_zpl_and_update_ui")
            self.labelViewer.preview_label(new_zpl_text)

    def use_item_data(self, item):
        """
        Maneja la información del 'item' obtenido. Por ejemplo,
        mostrar imágenes en un carrusel, actualizar la UI, etc.
        """
        if "pictures" in item:
            image_urls = [picture["url"] for picture in item.get("pictures", [])]
            if image_urls:
                self.carousel.set_images(image_urls)
                self.carousel.show_carousel(parent_geometry=self.geometry())
                self.set_status_message(f"Se encontraron {len(image_urls)} imágenes", duration=3, color="#28A745")
            else:
                self.set_status_message(
                    "No se encontraron imágenes del producto",
                    duration=5,
                    countdown=True,
                    color="#BD2A2E",
                )

    def process_zpl_text_and_call_api_if_needed(self, zpl_text):
        """
        Si el ZPL está bien formado y necesitamos más datos del API,
        aquí puedes lanzar otro Worker o simplemente parsear y mostrar en la UI.
        """
        is_valid_zpl = self.is_valid_zpl(zpl_text)

        if not zpl_text or not is_valid_zpl:
            self.copies_entry.setValue("")
            if zpl_text and not is_valid_zpl:
                self.set_status_message(
                    "ZPL ingresado no es valido",
                    duration=5,
                    countdown=True,
                    color="#BD2A2E",
                )
            self.labelViewer.clear_preview()
            self.updating_copies = False
            return

        # En este punto, el ZPL es válido. Extraemos ^PQ y el barcode
        pq_index = zpl_text.find("^PQ")
        if pq_index != -1:
            # Encuentra el número de copias en el ZPL
            start_index = pq_index + 3
            end_index = zpl_text.find(",", start_index)

            if end_index == -1:
                end_index = len(zpl_text)

            copies_str = zpl_text[start_index:end_index]
            if copies_str.isdigit():
                self.copies_entry.setValue(copies_str)

            # Ajusta el ZPL para previsualizar con 1 copia
            new_zpl_text = zpl_text[:start_index] + "1,0,1,Y^XZ"

            # print(f"BARCODE ========== {self.extract_barcode(zpl_text)}")
            # Obtener informacion del item
            inventory_id = self.extract_barcode(zpl_text)
            # print(f"COPIES_STR: {copies_str if copies_str.isdigit() else '0'}")

            index = self.label_size_selector.currentIndex()
            label_size = self.label_size_selector.itemData(index, Qt.UserRole)
            query_params = {
                "label_size": label_size,
                "qty": copies_str if copies_str.isdigit() else "0",
            }

            # Falta ubicar cuando viene previsamente de un execute_search, y cuando entra unicamente a validate_and_update (Por modificar directamente el ZPL)
            self.reset_all(True, False)

            # Muestra overlay + spinner antes de iniciar el worker
            self.show_loading_overlay()

            # Crea el worker
            worker = ZplWorker(self.api, inventory_id, query_params, new_zpl_text)

            # Conecta la señal finished a la función que procesa el resultado
            worker.signals.finished.connect(self.handle_zpl_worker_result)

            # Ejecuta en el pool de hilos
            self.threadpool.start(worker)

    def handle_zpl_worker_result(self, item, new_zpl_text):
        """Se llama cuando el ZplWorker termina."""
        self.hide_loading_overlay()

        if not item:
            # Manejar error al obtener el item
            self.set_status_message(
                "Fallo el obtener el item",
                duration=5,
                countdown=True,
                color="#BD2A2E",
            )
            self.labelViewer.clear_preview()
            return

        # Reutilizar la lógica para mostrar imágenes, etc.
        self.use_item_data(item)

        # Actualiza la vista previa con el ZPL modificado
        print("ACTUALIZA PREVIEW LABEL: handle_zpl_worker_result")
        self.labelViewer.preview_label(new_zpl_text)

        # Liberamos el flag
        self.updating_copies = False

    def extract_barcode(self, zpl_text):
        """
        Extracts the barcode from a ZPL code.

        :param zpl_text: ZPL content as a string.
        :return: Extracted barcode or None if not found.
        """
        # Patrón para encontrar el bloque ^BCN seguido de ^FD...^FS
        pattern = r"\^BCN.*?\^FD(.*?)\^FS"

        # Buscar el patrón en el texto ZPL
        match = re.search(pattern, zpl_text, re.DOTALL)

        if match:
            return match.group(1).strip()
        else:
            return None

    def update_zpl_from_copies(self):
        if self.updating_copies:  # Evita la recursión si validate_and_update_copies_from_zpl ya está en proceso
            return

        self.updating_zpl = True
        copies_text = self.copies_entry.text()

        if copies_text == "":
            zpl_text = self.zpl_textedit.toPlainText().strip()
            pq_index = zpl_text.find("^PQ")
            if pq_index != -1 and self.is_valid_zpl(zpl_text):
                # Reemplazar el número de copias existente
                start_index = pq_index + 3
                end_index = zpl_text.find(",", start_index)
                if end_index == -1:
                    end_index = len(zpl_text)
                new_zpl_text = zpl_text[:start_index] + zpl_text[end_index:]
                self.zpl_textedit.setPlainText(new_zpl_text)

        if copies_text.isdigit():
            new_copies = int(copies_text)
            zpl_text = self.zpl_textedit.toPlainText().strip()
            is_valid_zpl = self.is_valid_zpl(zpl_text)
            pq_index = zpl_text.find("^PQ")
            if pq_index != -1 and is_valid_zpl:
                # Reemplazar el número de copias existente
                start_index = pq_index + 3
                end_index = zpl_text.find(",", start_index)
                if end_index == -1:
                    end_index = len(zpl_text)
                new_zpl_text = zpl_text[:start_index] + str(new_copies) + zpl_text[end_index:]
                self.zpl_textedit.setPlainText(new_zpl_text)
            elif is_valid_zpl:
                # Añadir la instrucción ^PQ con el número de copias al final si no existe
                self.zpl_textedit.setPlainText(zpl_text + f"\n^PQ{new_copies},0,1,Y^XZ")

        self.updating_zpl = False

    def on_printer_selected(self, name):
        if name != "Seleccione una impresora":
            self.selected_printer_name = name
            self.settings.setValue("printer_name", self.printer_selector.currentText())
            self.clear_focus()

    def on_label_size_changed(self, index):
        zpl_text = self.zpl_textedit.toPlainText().strip().strip('"')
        inventory_id = self.extract_barcode(zpl_text)
        self.execute_search(inventory_id)

    def clear_focus(self):
        """
        Método para quitar el foco de cualquier widget.
        """
        focused_widget = self.focusWidget()
        if focused_widget:
            focused_widget.clearFocus()

    def mousePressEvent(self, event):
        """
        Quita el foco de cualquier widget cuando se hace clic fuera de ellos en la ventana.
        """
        self.clear_focus()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        """
        Maneja eventos de teclado para quitar el foco y otros controles.
        """
        key = event.key()

        if key == Qt.Key_Left:
            # Disminuir el valor del slider
            current_value = self.delay_slider.value()
            if current_value > self.delay_slider.minimum():
                self.delay_slider.setValue(current_value - 1)
                self.delay_update_timer.start()  # Reinicia el temporizador
        elif key == Qt.Key_Right:
            # Aumentar el valor del slider
            current_value = self.delay_slider.value()
            if current_value < self.delay_slider.maximum():
                self.delay_slider.setValue(current_value + 1)
                self.delay_update_timer.start()  # Reinicia el temporizador
        elif key == Qt.Key_Space:
            # Pausar/reanudar la impresión
            # self.control_printing()
            # self.space_press_count += 1
            # if self.space_press_count == 1:
            self.space_press_timer.start()
            # elif self.space_press_count == 2:
            #     self.space_press_timer.stop()
            #     self.handle_double_space_press()
            self.clear_focus()
        elif key == Qt.Key_Delete:
            # Detener la impresión
            self.clear_focus()
            self.stop_printing()
        elif key == Qt.Key_Escape:
            self.clear_focus()
        elif key in (Qt.Key_Up, Qt.Key_Down):
            if event.key() == Qt.Key_Up:
                self.increment()
            elif event.key() == Qt.Key_Down:
                self.decrement()
        else:
            super().keyPressEvent(event)  # Llama al método base para manejar otras teclas

    def handle_single_space_press(self):
        """Handle single space key press for pausing/resuming."""
        self.space_press_count = 0
        self.control_printing()

    def handle_double_space_press(self):
        """Handle double space key press for immediate print and pause."""
        print("handle_double_space_press called")
        self.space_press_count = 0
        if self.print_thread is None or not self.print_thread.isRunning():
            self.start_printing(True)  # Start printing with flag
            self.print_thread.print_and_pause()
            self.is_paused = True
            self.print_thread.pause = True
        else:
            print("print_and_pause called")
            self.print_thread.print_and_pause()
            self.is_paused = True
            self.print_thread.pause = True
            # self.control_button.setText("Reanudar")
            # self.set_status_message("Impresión pausada")

    # def pause_printing(self):
    #     if self.print_thread:
    #         # self.is_paused = True
    #         self.control_button.setText("Reanudar")
    #         self.set_status_message("Impresión pausada")
    #     return

    def is_valid_zpl(self, zpl_text):
        """
        Verifica si el texto proporcionado es un ZPL válido.
        Esta función es básica y podría necesitar una lógica más compleja para validar ZPL de manera exhaustiva.
        """
        if re.search(r"^\^XA.*\^XZ$", zpl_text, re.DOTALL):
            return True
        return False

    def control_printing(self):
        # print("self.print_thread.isRunning():")
        # print("TRUE" if self.print_thread is not None and self.print_thread.isRunning() else "FALSE");
        if self.print_thread is None or not self.print_thread.isRunning():
            self.start_printing()
        elif self.print_thread and self.print_thread.isRunning():
            if self.is_paused:
                self.resume_printing()
            else:
                self.pause_printing()

    def pause_printing(self):
        if self.print_thread:
            self.is_paused = True
            self.control_button.setText("Reanudar")
            self.set_status_message("Impresión pausada")
            self.print_thread.toggle_pause()

    def resume_printing(self):
        print("Resuming printing")
        if self.print_thread and self.is_paused:
            self.is_paused = False
            self.control_button.setText("Pausar")
            self.set_status_message("")
            self.print_thread.toggle_pause()

    def stop_printing(self):
        if self.print_thread and self.print_thread.isRunning():
            self.print_thread.stop_printing()
            self.print_thread = None
            self.set_status_message("Impresión detenida... ", duration=10, countdown=True)
            # Reestablecer el UI para permitir una nueva impresión
            self.count_label.setText("0")
            self.stop_button.setEnabled(False)
            self.control_button.setText("Iniciar Impresión")
            QMessageBox.information(self, "Impresión detenida", "La impresión ha sido detenida.")

    def start_printing(self, initiated_by_double_click=False):
        copies_text = self.copies_entry.text()
        zpl_text = self.zpl_textedit.toPlainText()
        delay = self.delay_slider.value()

        # Asegurarse de que los campos no estén vacíos
        if not copies_text or not zpl_text:
            QMessageBox.warning(self, "Error de validación", "Los campos no pueden estar vacíos.")
            return

        copies = int(copies_text)

        # Asegurarse de que la cantidad de copias sea al menos una
        if copies <= 0:
            QMessageBox.warning(self, "Error de validación", "La cantidad de copias no puede ser cero.")
            return

        # Verificar que se haya seleccionado una impresora
        if not self.selected_printer_name or self.selected_printer_name == "Seleccione una impresora":
            QMessageBox.warning(
                self,
                "Impresora no seleccionada",
                "Por favor, selecciona una impresora antes de imprimir.",
            )
            return

        # Validar que el texto ZPL sea válido
        if not self.is_valid_zpl(zpl_text):
            QMessageBox.warning(self, "Error de validación", "Por favor, ingresa un código ZPL válido.")
            return

        # Utilizar hasAcceptableInput para verificar si el contenido de los campos es válido
        # if not self.copies_entry.hasAcceptableInput() or not self.delay_entry.hasAcceptableInput():
        if not self.copies_entry.hasAcceptableInput():
            QMessageBox.warning(self, "Error de validación", "Por favor, ingresa valores válidos.")
            return

        if self.print_thread is not None and self.print_thread.isRunning():
            QMessageBox.warning(self, "Advertencia", "Ya hay un proceso de impresión en curso.")
            return

        # Crea el hilo de impresión si no existe
        if self.print_thread is None:
            self.print_thread = PrintThread(copies, delay, zpl_text, self.selected_printer_name)
            self.print_thread.update_signal.connect(self.update_status)
            self.print_thread.finished_signal.connect(self.printing_finished)
            self.print_thread.error_signal.connect(self.show_error_message)
            self.print_thread.request_pause_signal.connect(self.pause_printing)
        else:
            # Si el hilo ya existe y está ejecutándose, actualiza las propiedades y continúa
            self.print_thread.set_copies_and_zpl(copies, zpl_text)

        print("initiated_by_double_click: ", initiated_by_double_click)
        self.print_thread.initiated_by_double_click = initiated_by_double_click  # Set the flag directly here

        self.set_status_message("")
        self.control_button.setText("Pausar")
        self.is_paused = False
        self.stop_button.setEnabled(True)

        # Inicia el hilo de impresión si no está en ejecución
        if not self.print_thread.isRunning():
            self.print_thread.start()

    def update_status(self, message):
        self.count_label.setText(message)

    def printing_finished(self):
        # Una vez finalizado el proceso de impresión, vuelve a habilitar el botón
        # de iniciar impresión y deshabilita el botón de pausa.
        print("Impresión completada...")
        self.control_button.setText("Iniciar Impresión")  # Restablece el texto del botón de pausa
        self.stop_button.setEnabled(False)
        self.is_paused = False  # Restablece el estado de pausa
        # Traceback (most recent call last):
        # File "C:\Users\Jonathan\Documents\DesarrolloSoftware\TecneuTagger\src\ui\main_window.py", line 800, in printing_finished
        # self.print_thread.stopped = False
        # AttributeError: 'NoneType' object has no attribute 'stopped'
        if self.print_thread:
            self.print_thread.stopped = False
        self.set_status_message("Impresión completada... ", duration=10, countdown=True)
        self.copies_entry.setValue("0")

    def toggle_always_on_top(self, checked):
        """
        Activa o desactiva el modo 'Always on Top'.
        """
        print(f"checked=> {checked}")

        flags = self.windowFlags()

        if checked:
            # Activar "Always on Top"
            flags |= Qt.WindowStaysOnTopHint
        else:
            # Desactivar "Always on Top"
            flags &= ~Qt.WindowStaysOnTopHint

        self.setWindowFlags(flags)
        self.show()  # Es necesario volver a mostrar la ventana para que el cambio surta efecto.

    def closeEvent(self, event):
        # Guardar el nombre de la impresora seleccionada
        self.settings.setValue("printer_name", self.printer_selector.currentText())

        # Guardar el último valor del delay slider
        self.settings.setValue("delay_value", self.delay_slider.value())

        super().closeEvent(event)

    def update_carousel_position(self):
        """Update the carousel position to align with the main window."""
        if self.carousel.is_visible:
            self.carousel._configure_geometry(parent_geometry=self.geometry())

    def moveEvent(self, event):
        """Update the carousel's position when the main window moves."""
        self.update_carousel_position()
        if self.loading_overlay is not None:
            self.loading_overlay.setGeometry(self.rect())
        super().moveEvent(event)

    def resizeEvent(self, event):
        """Update the carousel's position when the main window resizes."""
        self.update_carousel_position()
        if self.loading_overlay is not None:
            self.loading_overlay.setGeometry(self.rect())
        super().resizeEvent(event)  # Mantiene el comportamiento original
