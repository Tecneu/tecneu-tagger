import os
import sys
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, \
    QMessageBox, QSlider, QComboBox, QFrame, QGraphicsDropShadowEffect, QListView, QApplication
from PyQt5.QtCore import QTimer, QSettings, Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QIntValidator, QColor, QPixmap, QFont, QStandardItemModel, QStandardItem
import json
import re
from font_config import FontManager

from .custom_widgets import CustomTextEdit
from print_thread import PrintThread
from utils import list_printers_to_json

__all__ = ['MainWindow']

json_printers = json.loads(list_printers_to_json());


class MainWindow(QWidget):
    """
    Clase principal de la ventana que gestiona la interfaz de usuario y las interacciones.
    """

    if getattr(sys, 'frozen', False):
        # Si es así, usa la ruta de _MEIPASS
        BASE_ASSETS_PATH = Path(sys._MEIPASS) / "assets"
    else:
        # De lo contrario, usa la ruta relativa desde el archivo de script
        BASE_ASSETS_PATH = Path(__file__).resolve().parent.parent.parent / "assets"

    def __init__(self):
        super().__init__()
        self.settings = QSettings('Tecneu', 'TecneuTagger')
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

    def apply_new_delay(self):
        # Aplica el nuevo delay al hilo de impresión
        new_delay = self.delay_slider.value()
        if self.print_thread is not None:
            self.print_thread.set_delay(new_delay)

    def loadSettings(self):
        # Cargar el nombre de la impresora seleccionada
        printer_name = self.settings.value('printer_name', '')
        index = self.printer_selector.findText(printer_name)
        if index != -1:
            self.printer_selector.setCurrentIndex(index)

        # Cargar el último valor del delay slider
        delay_value = self.settings.value('delay_value', 25, type=int)
        self.delay_slider.setValue(delay_value)

    def saveSliderValue(self):
        self.settings.setValue('delay_value', self.delay_slider.value())

    def show_error_message(self, message):
        QMessageBox.critical(self, "Error", message)

    def init_ui(self):
        """
        Configura la interfaz de usuario de la ventana principal.
        """
        fonts = FontManager.get_fonts()
        robotoBoldFont = None
        robotoRegularFont = None
        digitalBoldFont = None
        mystericFont = None
        if fonts and 'robotoBoldFont' in fonts:
            robotoBoldFont = fonts['robotoBoldFont']
        if fonts and 'robotoRegularFont' in fonts:
            robotoRegularFont = fonts['robotoRegularFont']
        if fonts and 'digitalBoldFont' in fonts:
            digitalBoldFont = fonts['digitalBoldFont']
        if fonts and 'mystericFont' in fonts:
            mystericFont = fonts['mystericFont']

        self.setWindowTitle("Tecneu - Tagger")
        self.setGeometry(800, 100, 800, 400)  # x, y, width, height

        # Establecer el tamaño mínimo de la ventana
        self.setMinimumSize(700, 300)

        main_layout = QHBoxLayout()  # Usar QHBoxLayout para dividir la ventana
        control_layout = QVBoxLayout()
        # Contenedor principal para el QLineEdit y los botones
        entry_frame = QFrame()
        entry_layout = QHBoxLayout(entry_frame)
        entry_layout.setContentsMargins(0, 0, 0, 0)
        entry_layout.setSpacing(0)

        self.copies_entry = QLineEdit(entry_frame)
        self.copies_entry.setPlaceholderText("Número de copias")
        self.copies_entry.setValidator(QIntValidator(0, 999))
        self.copies_entry.setMinimumHeight(30)
        self.copies_entry.setMaximumWidth(140)
        self.copies_entry.textChanged.connect(self.update_zpl_from_copies)
        entry_layout.addWidget(self.copies_entry)

        # Contenedor para los botones
        button_container = QVBoxLayout()
        button_container.setSpacing(0)  # Eliminar espacio entre los botones

        self.incButton = QPushButton('▲')
        if robotoBoldFont: self.incButton.setFont(robotoBoldFont)
        self.incButton.clicked.connect(self.increment)
        self.incButton.setFixedSize(25, 19)
        button_container.addWidget(self.incButton)

        self.decButton = QPushButton('▼')
        if robotoBoldFont: self.decButton.setFont(robotoBoldFont)
        self.decButton.clicked.connect(self.decrement)
        self.decButton.setFixedSize(25, 19)
        button_container.addWidget(self.decButton)

        # Añadir el contenedor de botones al layout del frame
        entry_layout.addLayout(button_container)

        # Agregar el frame al layout principal
        control_layout.addWidget(entry_frame)

        # Configuración del QSlider para el retraso
        self.delay_slider_layout = QHBoxLayout()
        self.delay_slider = QSlider(Qt.Horizontal)
        self.delay_slider.setMinimum(1)
        self.delay_slider.setMaximum(50)
        self.delay_slider.setValue(25)  # Valor predeterminado
        self.delay_slider.setTickInterval(1)
        self.delay_slider.setTickPosition(QSlider.TicksBelow)
        self.delay_slider.valueChanged.connect(self.update_slider_label)
        self.delay_slider.sliderReleased.connect(self.apply_delay_change)

        self.delay_slider.setStyleSheet("""
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
        """)

        # Icono de tortuga para el lado lento
        self.turtle_icon_label = QLabel()
        turtle_pixmap = (QPixmap(os.fspath(MainWindow.BASE_ASSETS_PATH / 'icons' / 'turtle-du.svg'))
                         .scaled(35, 35, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.turtle_icon_label.setPixmap(turtle_pixmap)
        self.delay_slider_layout.addWidget(self.turtle_icon_label)

        self.delay_slider_layout.addWidget(self.delay_slider)

        # Icono de conejo para el lado rápido
        self.rabbit_icon_label = QLabel()
        rabbit_pixmap = (QPixmap(os.fspath(MainWindow.BASE_ASSETS_PATH / 'icons' / 'rabbit-running-du.svg'))
                         .scaled(35, 35, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.rabbit_icon_label.setPixmap(rabbit_pixmap)
        self.delay_slider_layout.addWidget(self.rabbit_icon_label)

        self.slider_label_frame = QFrame(self)
        # border: 1px solid gray;
        self.slider_label_frame.setStyleSheet("""
            background-color: white;
            border: 1px solid gray;
            border-radius: 5px;
            padding: 0px;
            margin: 0px;
        """)
        self.slider_label_frame.setLayout(QVBoxLayout())
        self.slider_label_frame.layout().setContentsMargins(0, 0, 0, 0)
        self.slider_label_frame.layout().setAlignment(Qt.AlignCenter)
        self.slider_label_frame.setFixedSize(26, 24)

        # Slider label setup
        self.slider_label = QLabel(self.slider_label_frame)
        if robotoRegularFont: self.slider_label.setFont(robotoRegularFont)
        self.slider_label.setStyleSheet("""
            background-color: transparent;
            border: none;
            padding: 0px;
            margin: 0px;
        """)
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
        self.control_button = QPushButton("Iniciar Impresión")
        self.control_button.clicked.connect(self.control_printing)
        if robotoBoldFont: self.control_button.setFont(robotoBoldFont)
        buttons_layout.addWidget(self.control_button)

        self.stop_button = QPushButton("Detener")
        self.stop_button.clicked.connect(self.stop_printing)
        if robotoBoldFont: self.stop_button.setFont(robotoBoldFont)
        buttons_layout.addWidget(self.stop_button)
        self.stop_button.setEnabled(False)  # Inicialmente, el botón de pausa está deshabilitado

        # Contenedor y layout para el contador de etiquetas
        counter_frame = QFrame()
        counter_frame.setStyleSheet("background-color: #444; border: 1px solid black;")
        counter_layout = QVBoxLayout(counter_frame)
        counter_layout.setAlignment(Qt.AlignCenter)

        # Label para el título del contador
        self.title_label = QLabel("Etiquetas restantes:")
        self.title_label.setStyleSheet("color: white;")
        counter_layout.addWidget(self.title_label)

        # Label para el número del contador
        self.count_label = QLabel("0")
        if robotoBoldFont: self.count_label.setFont(digitalBoldFont)
        self.count_label.setStyleSheet("color: yellow; font-size: 65px;")
        self.count_label.setAlignment(Qt.AlignRight)
        counter_layout.addWidget(self.count_label)

        # Añadir los dos contenedores verticales al layout horizontal
        buttons_and_counter_layout.addLayout(buttons_layout)
        buttons_and_counter_layout.addWidget(counter_frame)
        control_layout.addLayout(buttons_and_counter_layout)

        self.status_label = QLabel("")
        if mystericFont: self.status_label.setFont(mystericFont)
        self.status_label.setStyleSheet("color: #F27405; font-size: 17px;")
        control_layout.addWidget(self.status_label)

        # Layout para QTextEdit y el botón de borrar
        zpl_layout = QVBoxLayout()
        self.zpl_textedit = CustomTextEdit()
        self.zpl_textedit.setPlaceholderText("Ingrese el ZPL aquí...")
        self.zpl_textedit.textChanged.connect(self.validate_and_update_copies_from_zpl)
        zpl_layout.addWidget(self.zpl_textedit)

        # Configurar botones para el ZPL input/impresora
        zpl_buttons_layout = QHBoxLayout()
        # Creación del menú desplegable para las impresoras
        self.printer_selector = QComboBox()
        self.printer_selector.setView(QListView())  # Asegúrate de importar QListView
        self.printer_selector.setMinimumHeight(30)
        self.printer_selector.setStyleSheet("""
        QListView::item{
            padding: 5px 10px;
        }
        """)

        self.printer_selector.currentIndexChanged.connect(self.update_printer_icon)
        model = QStandardItemModel()

        # Crea el ítem "Seleccione una impresora" y hazlo no seleccionable
        defaultItem = QStandardItem(QIcon(os.fspath(MainWindow.BASE_ASSETS_PATH / 'icons' / 'printer.svg')),
                                    "Seleccione una impresora")
        defaultItem.setEnabled(False)  # Hace que el ítem sea no seleccionable
        model.appendRow(defaultItem)

        # Filtra y agrega los nombres de las impresoras al menú desplegable
        for printer in json_printers:
            if printer["EnableBIDI"] == "TRUE":
                item = QStandardItem(printer['Name'])
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
        self.clear_zpl_button.setIcon(QIcon(os.fspath(MainWindow.BASE_ASSETS_PATH / 'icons' / 'delete-left.svg')))
        self.clear_zpl_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 5px 10px;
            }
            QPushButton::icon {
                position: absolute;
                left: 50px;  /* Alinear el ícono a la derecha */
            }
        """)
        # Establecer el tamaño del ícono (opcional)
        self.clear_zpl_button.setIconSize(QSize(20, 20))
        self.clear_zpl_button.clicked.connect(self.zpl_textedit.clear)
        zpl_buttons_layout.addWidget(self.clear_zpl_button)

        # Botón para pegar desde el portapapeles
        self.paste_zpl_button = QPushButton()
        self.paste_zpl_button.setIcon(QIcon(os.fspath(MainWindow.BASE_ASSETS_PATH / 'icons' / 'paste.svg')))
        self.paste_zpl_button.setStyleSheet("""
            QPushButton {
                padding: 5px;
                icon-size: 20px;
            }
        """)
        self.paste_zpl_button.clicked.connect(self.paste_from_clipboard)
        zpl_buttons_layout.addWidget(self.paste_zpl_button)

        zpl_layout.addLayout(zpl_buttons_layout)

        # Agregar los layouts al layout principal
        main_layout.addLayout(control_layout)
        main_layout.addLayout(zpl_layout)  # Añadir el layout de ZPL al layout principal

        self.setLayout(main_layout)

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
        clipboard = QApplication.clipboard()
        # Elimina espacios en blanco y comillas dobles al principio y al final
        text = clipboard.text().strip().strip('"')
        if text == '':
            self.set_status_message("No hay texto para pegar", duration=5, countdown=True, color='#BD2A2E')
            return

        self.zpl_textedit.setPlainText(text)  # Pegar como texto plano

    def update_printer_icon(self, index):
        # Eliminar el ícono de todos los ítems
        for i in range(self.printer_selector.count()):
            self.printer_selector.setItemIcon(i, QIcon())

        # Establecer el ícono solo en el ítem seleccionado
        if index != 0:  # Asumiendo que el índice 0 es "Seleccione una impresora"
            (self.printer_selector
             .setItemIcon(index, QIcon(os.fspath(MainWindow.BASE_ASSETS_PATH / 'icons' / 'printer.svg'))))

    def increment(self):
        current_value = self.copies_entry.text()
        if current_value.isdigit():
            current_value = int(current_value)
        elif current_value != '':
            return

        value = int(current_value or 0)
        if value < 999:
            self.copies_entry.setText(str(value + 1))

    def decrement(self):
        current_value = self.copies_entry.text()
        if current_value.isdigit():
            current_value = int(current_value)
        elif current_value != '':
            return

        value = int(current_value or 0)
        if value > 0:
            self.copies_entry.setText(str(value - 1))

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
        slider_value = (value - self.delay_slider.minimum()) / (
                self.delay_slider.maximum() - self.delay_slider.minimum())
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
        zpl_text = self.zpl_textedit.toPlainText().strip()
        is_valid_zpl = self.is_valid_zpl(zpl_text)

        if zpl_text == '' or not is_valid_zpl:
            self.copies_entry.setText('')
        if zpl_text != '' and not is_valid_zpl:
            self.set_status_message("ZPL ingresado no es valido", duration=5, countdown=True, color='#BD2A2E')

        pq_index = zpl_text.find('^PQ')
        if is_valid_zpl and pq_index != -1:
            # Encuentra el número de copias en el ZPL
            start_index = pq_index + 3
            end_index = zpl_text.find(',', start_index)
            if end_index == -1:
                end_index = len(zpl_text)

            copies_str = zpl_text[start_index:end_index]
            if copies_str.isdigit():
                self.copies_entry.setText(copies_str)

        self.updating_copies = False

    def update_zpl_from_copies(self):
        if self.updating_copies:  # Evita la recursión si validate_and_update_copies_from_zpl ya está en proceso
            return

        self.updating_zpl = True
        copies_text = self.copies_entry.text()

        if copies_text == '':
            zpl_text = self.zpl_textedit.toPlainText().strip()
            pq_index = zpl_text.find('^PQ')
            if pq_index != -1 and self.is_valid_zpl(zpl_text):
                # Reemplazar el número de copias existente
                start_index = pq_index + 3
                end_index = zpl_text.find(',', start_index)
                if end_index == -1:
                    end_index = len(zpl_text)
                new_zpl_text = zpl_text[:start_index] + zpl_text[end_index:]
                self.zpl_textedit.setPlainText(new_zpl_text)

        if copies_text.isdigit():
            new_copies = int(copies_text)
            zpl_text = self.zpl_textedit.toPlainText().strip()
            is_valid_zpl = self.is_valid_zpl(zpl_text)
            pq_index = zpl_text.find('^PQ')
            if pq_index != -1 and is_valid_zpl:
                # Reemplazar el número de copias existente
                start_index = pq_index + 3
                end_index = zpl_text.find(',', start_index)
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
            self.settings.setValue('printer_name', self.printer_selector.currentText())
            self.clear_focus()

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
            self.clear_focus()
            self.control_printing()
            # Si se reanuda, comienza inmediatamente con la siguiente impresión sin esperar el delay
            if not self.is_paused and self.print_thread is not None:
                self.print_thread.pause = False
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

    def is_valid_zpl(self, zpl_text):
        """
        Verifica si el texto proporcionado es un ZPL válido.
        Esta función es básica y podría necesitar una lógica más compleja para validar ZPL de manera exhaustiva.
        """
        if re.search(r'^\^XA.*\^XZ$', zpl_text, re.DOTALL):
            return True
        return False

    def control_printing(self):
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
        if self.print_thread:
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

    def start_printing(self):
        self.set_status_message("")
        self.control_button.setText("Pausar")
        self.is_paused = False
        self.stop_button.setEnabled(True)
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
            QMessageBox.warning(self, "Impresora no seleccionada",
                                "Por favor, selecciona una impresora antes de imprimir.")
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
        else:
            # Si el hilo ya existe y está ejecutándose, actualiza las propiedades y continúa
            self.print_thread.copies = copies
            self.print_thread.zpl = zpl_text

        # Inicia el hilo de impresión si no está en ejecución
        if not self.print_thread.isRunning():
            self.print_thread.start()

    def update_status(self, message):
        self.count_label.setText(message)

    def printing_finished(self):
        # Una vez finalizado el proceso de impresión, vuelve a habilitar el botón
        # de iniciar impresión y deshabilita el botón de pausa.
        self.control_button.setText("Iniciar Impresión")  # Restablece el texto del botón de pausa
        self.stop_button.setEnabled(False)
        self.is_paused = False  # Restablece el estado de pausa
        self.set_status_message("Impresión completada... ", duration=10, countdown=True)
        self.copies_entry.setText('0')

    def closeEvent(self, event):
        # Guardar el nombre de la impresora seleccionada
        self.settings.setValue('printer_name', self.printer_selector.currentText())

        # Guardar el último valor del delay slider
        self.settings.setValue('delay_value', self.delay_slider.value())

        super().closeEvent(event)
