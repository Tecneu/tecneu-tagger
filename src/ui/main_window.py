from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, \
    QMessageBox, QSlider, QComboBox, QFrame, QGraphicsDropShadowEffect
from PyQt5.QtCore import QTimer, QSettings, Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QIntValidator, QColor, QPixmap, QFont, QStandardItemModel, QStandardItem
import json
import re

# ui/main_window.py
from .custom_widgets import CustomTextEdit
from src.print_thread import PrintThread
from src.utils import list_printers_to_json
from src.font_config import novaBoldFont

__all__ = ['MainWindow']

json_printers = json.loads(list_printers_to_json());


class MainWindow(QWidget):
    """
    Clase principal de la ventana que gestiona la interfaz de usuario y las interacciones.
    """

    def __init__(self):
        super().__init__()
        self.settings = QSettings('Tecneu', 'TecneuTagger')
        self.print_thread = None
        self.selected_printer_name = None  # Inicializa la variable para almacenar el nombre de la impresora seleccionada
        self.is_paused = False  # Inicializa un atributo para llevar el seguimiento del estado de pausa
        self.slider_label_timer = QTimer(self)
        self.slider_label_timer.setInterval(2000)  # 2000 ms = 2 s
        self.slider_label_timer.setSingleShot(True)
        # self.delay_update_timer = QTimer(self)  # Timer para actualizar el delay
        # self.delay_update_timer.setInterval(500)  # Intervalo antes de actualizar el delay
        # self.delay_update_timer.setSingleShot(True)
        self.updating_copies = False  # Flag para controlar la recursión entre métodos
        self.updating_zpl = False  # Flag para controlar la recursión entre métodos
        self.init_ui()
        self.loadSettings()

        self.slider_label_timer.timeout.connect(self.slider_label_frame.hide)
        self.slider_label_timer.timeout.connect(self.slider_label.hide)
        self.slider_label_timer.timeout.connect(self.saveSliderValue)
        # self.delay_update_timer.timeout.connect(self.apply_new_delay)
        # self.delay_slider.valueChanged.connect(self.schedule_delay_update)

    # def schedule_delay_update(self):
    #     # Reinicia el temporizador cada vez que el valor del slider cambia
    #     self.delay_update_timer.start()

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
        self.incButton.clicked.connect(self.increment)
        self.incButton.setFixedSize(25, 15)
        button_container.addWidget(self.incButton)

        self.decButton = QPushButton('▼')
        self.decButton.clicked.connect(self.decrement)
        self.decButton.setFixedSize(25, 15)
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
        turtle_pixmap = QPixmap("../../assets/icons/turtle-du.svg").scaled(35, 35, Qt.KeepAspectRatio)
        self.turtle_icon_label.setPixmap(turtle_pixmap)
        self.delay_slider_layout.addWidget(self.turtle_icon_label)

        self.delay_slider_layout.addWidget(self.delay_slider)

        # Icono de conejo para el lado rápido
        self.rabbit_icon_label = QLabel()
        rabbit_pixmap = QPixmap("../../assets/icons/rabbit-running-du.svg").scaled(35, 35, Qt.KeepAspectRatio)
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
        self.slider_label_frame.setFixedSize(35, 28)

        # Slider label setup
        self.slider_label = QLabel(self.slider_label_frame)
        self.slider_label.setStyleSheet("""
            background-color: transparent;
            border: none;
            padding: 0px;
            margin: 0px;
        """)
        self.slider_label.setAlignment(Qt.AlignCenter)
        self.slider_label_frame.layout().addWidget(self.slider_label)

        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setBlurRadius(5)
        shadow_effect.setColor(QColor(0, 0, 0, 60))
        shadow_effect.setOffset(2, 2)
        self.slider_label_frame.setGraphicsEffect(shadow_effect)

        # Asegúrate de que el frame esté oculto inicialmente
        self.slider_label_frame.hide()

        # En MainWindow.init_ui(), asegúrate de conectar el valor del slider con update_slider_label
        # self.delay_slider.valueChanged.connect(self.update_slider_label)

        control_layout.addLayout(self.delay_slider_layout)

        self.start_button = QPushButton("Iniciar Impresión")
        self.start_button.clicked.connect(self.start_printing)
        self.start_button.setFont(novaBoldFont)
        control_layout.addWidget(self.start_button)

        self.pause_button = QPushButton("Pausar")
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setFont(novaBoldFont)
        control_layout.addWidget(self.pause_button)
        self.pause_button.setEnabled(False)  # Inicialmente, el botón de pausa está deshabilitado

        self.status_label = QLabel("Etiquetas restantes: 0")
        control_layout.addWidget(self.status_label)

        main_layout.addLayout(control_layout)  # Agrega control_layout a main_layout

        # Layout para QTextEdit y el botón de borrar
        zpl_layout = QVBoxLayout()
        self.zpl_textedit = CustomTextEdit()
        self.zpl_textedit.setPlaceholderText("Ingrese el ZPL aquí...")
        self.zpl_textedit.textChanged.connect(self.validate_and_update_copies_from_zpl)
        zpl_layout.addWidget(self.zpl_textedit)

        # Creación del menú desplegable para las impresoras
        self.printer_selector = QComboBox()
        model = QStandardItemModel()

        # Crea el ítem "Seleccione una impresora" y hazlo no seleccionable
        defaultItem = QStandardItem(QIcon("../../assets/icons/printer.svg"), "Seleccione una impresora")
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
        zpl_layout.addWidget(self.printer_selector)

        # Botón para borrar el contenido de QTextEdit
        self.clear_zpl_button = QPushButton("Borrar ZPL")
        # Establecer el ícono en el botón
        self.clear_zpl_button.setIcon(QIcon("../../assets/icons/delete-left.svg"))
        # // padding: 0px 20px 0px 0px;
        # // margin: 15px
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
        zpl_layout.addWidget(self.clear_zpl_button)

        # Agregar los layouts al layout principal
        main_layout.addLayout(control_layout)
        main_layout.addLayout(zpl_layout)  # Añadir el layout de ZPL al layout principal

        self.setLayout(main_layout)

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
            self.delay_slider.setValue(self.delay_slider.value() - 1)
        elif key == Qt.Key_Right:
            # Aumentar el valor del slider
            self.delay_slider.setValue(self.delay_slider.value() + 1)
        elif key == Qt.Key_Space:
            # Pausar/reanudar la impresión
            self.clear_focus()
            self.toggle_pause()
            # Si se reanuda, comienza inmediatamente con la siguiente impresión sin esperar el delay
            if not self.is_paused and self.print_thread is not None:
                self.print_thread.pause = False
        elif key == Qt.Key_F5:
            # Iniciar/detener la impresión
            self.clear_focus()
            if self.print_thread is None or not self.print_thread.isRunning():
                self.start_printing()
            else:
                self.stop_printing()
        elif key in (Qt.Key_Up, Qt.Key_Down):
            if event.key() == Qt.Key_Up:
                self.increment()
            elif event.key() == Qt.Key_Down:
                self.decrement()
        else:
            super().keyPressEvent(event)  # Llama al método base para manejar otras teclas

    def stop_printing(self):
        if self.print_thread:
            self.print_thread.stop_printing()
            self.print_thread = None
            self.status_label.setText("Impresión detenida.")
            # Reestablecer el UI para permitir una nueva impresión
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.pause_button.setText("Pausar")
            QMessageBox.information(self, "Impresión detenida", "La impresión ha sido detenida.")

    def is_valid_zpl(self, zpl_text):
        """
        Verifica si el texto proporcionado es un ZPL válido.
        Esta función es básica y podría necesitar una lógica más compleja para validar ZPL de manera exhaustiva.
        """
        if re.search(r'^\^XA.*\^XZ$', zpl_text, re.DOTALL):
            return True
        return False

    def start_printing(self):
        copies_text = self.copies_entry.text()
        zpl_text = self.zpl_textedit.toPlainText()
        delay = self.delay_slider.value()

        # Asegurarse de que los campos no estén vacíos
        if not copies_text or not zpl_text:
            QMessageBox.warning(self, "Error de validación", "Los campos no pueden estar vacíos.")
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

        copies = int(copies_text)

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

        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)

        # Inicia el hilo de impresión si no está en ejecución
        if not self.print_thread.isRunning():
            self.print_thread.start()

    def toggle_pause(self):
        # Cambia el estado de pausa
        if self.print_thread and self.print_thread.isRunning():
            if self.is_paused:
                self.pause_button.setText("Pausar")
                self.is_paused = False
            else:
                self.pause_button.setText("Reanudar")
                self.is_paused = True
            self.print_thread.toggle_pause()

    def update_status(self, message):
        self.status_label.setText(message)

    def printing_finished(self):
        # Una vez finalizado el proceso de impresión, vuelve a habilitar el botón
        # de iniciar impresión y deshabilita el botón de pausa.
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText("Pausar")  # Restablece el texto del botón de pausa
        self.is_paused = False  # Restablece el estado de pausa
        self.status_label.setText("Impresión completada.")
        self.copies_entry.setText('0')

    def closeEvent(self, event):
        # Guardar el nombre de la impresora seleccionada
        self.settings.setValue('printer_name', self.printer_selector.currentText())

        # Guardar el último valor del delay slider
        self.settings.setValue('delay_value', self.delay_slider.value())

        super().closeEvent(event)
