from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, \
    QMessageBox, QTextEdit, QSlider, QComboBox
from PyQt5.QtGui import QIcon, QValidator, QIntValidator, QDoubleValidator, QFont, QFontDatabase, QPixmap
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QSize
import time
import subprocess
import json
from zebra import Zebra


class PrintThread(QThread):
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, copies, delay, zpl, printer_name):
        super().__init__()
        self.copies = copies
        self.delay = delay
        self.zpl = zpl
        self.printer_name = printer_name
        self.pause = False
        self.stopped = False
        self.manually_stopped = False

    def run(self):
        z = Zebra(self.printer_name)
        z.setqueue(self.printer_name)
        for i in range(self.copies):
            if self.stopped:
                self.manually_stopped = True  # Indicar que la impresión fue detenida manualmente
                break
            while self.pause:
                time.sleep(1)
            print(f"Numero de copia: {i}")
            z.output(self.zpl)
            self.update_signal.emit(f"Etiquetas restantes: {self.copies - i - 1}")
            if i < self.copies - 1:
                time.sleep(self.delay)
        if not self.manually_stopped:  # Emitir la señal solo si no se detuvo manualmente
            self.finished_signal.emit()

    def toggle_pause(self):
        self.pause = not self.pause

    def stop_printing(self):
        self.stopped = True


def list_printers_to_json():
    cmd = 'wmic printer get name, ExtendedPrinterStatus, PortName, Local, WorkOffline, PrinterStatus, DeviceID, EnableBIDI'
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)

    # Dividir el resultado en líneas
    lines = result.stdout.strip().split('\n')

    # La primera línea contiene los nombres de las columnas
    columns = [column.strip() for column in lines[0].split('  ') if column]

    # Lista para almacenar los diccionarios de cada impresora
    printers = []

    # Procesar cada impresora
    for line in lines[1:]:
        if not line.strip():  # Si la línea está vacía, continuar
            continue
        values = [value.strip() for value in line.split('  ') if value]
        # Asegurarse de que el número de valores no exceda el número de columnas
        values = values[:len(columns)]
        # Llenar con None si faltan valores
        while len(values) < len(columns):
            values.append(None)
        printer = {columns[i]: values[i] for i in range(len(columns))}
        printers.append(printer)

    # Convertir la lista en JSON
    return json.dumps(printers, indent=4)


json_printers = json.loads(list_printers_to_json());


class CustomDoubleValidator(QDoubleValidator):
    def __init__(self, bottom, top, decimals, parent=None):
        super().__init__(bottom, top, decimals, parent)

    def validate(self, string, pos):
        # Primero, verifica si el string está vacío, lo cual es siempre aceptable.
        if not string:
            return QValidator.Acceptable, string, pos

        # Intenta convertir el string a float y verifica el rango.
        try:
            value = float(string)
            # Divide el string en partes entera y decimal usando el punto como separador.
            parts = string.split('.')
            # Verifica si el valor está dentro del rango permitido.
            if self.bottom() <= value <= self.top():
                # Si solo hay una parte o la parte decimal es menor o igual a 2 dígitos, es aceptable.
                if len(parts) == 1 or len(parts[1]) <= 2:
                    return QValidator.Acceptable, string, pos
            # Si el valor no está en el rango permitido o tiene más de 2 decimales, es inválido.
            return QValidator.Invalid, string, pos
        except ValueError:
            # Si el string no se puede convertir a float, es inválido.
            return QValidator.Invalid, string, pos


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.print_thread = None
        self.selected_printer_name = None  # Inicializa la variable para almacenar el nombre de la impresora seleccionada
        self.is_paused = False  # Inicializa un atributo para llevar el seguimiento del estado de pausa

    def init_ui(self):
        self.setWindowTitle("Tecneu - Tagger")
        self.setGeometry(800, 100, 800, 400)  # x, y, width, height

        # Establecer el tamaño mínimo de la ventana
        self.setMinimumSize(700, 300)

        main_layout = QHBoxLayout()  # Usar QHBoxLayout para dividir la ventana
        control_layout = QVBoxLayout()
        # self.setLayout(main_layout)

        self.copies_entry = QLineEdit()
        self.copies_entry.setPlaceholderText("Número de copias")
        # Aplicar validador para asegurar solo entrada de enteros
        self.copies_entry.setValidator(QIntValidator(0, 999))
        self.copies_entry.textChanged.connect(self.update_zpl_from_copies)
        control_layout.addWidget(self.copies_entry)

        self.delay_entry = QLineEdit()
        self.delay_entry.setPlaceholderText("Retraso entre copias (segundos)")
        validator = CustomDoubleValidator(0, 15.99, 2)
        self.delay_entry.setValidator(validator)
        # self.delay_entry.textChanged.connect(self.check_delay_value)
        control_layout.addWidget(self.delay_entry)

        # Configuración del QSlider para el retraso
        self.delay_slider_layout = QHBoxLayout()
        self.delay_slider = QSlider(Qt.Horizontal)
        self.delay_slider.setMinimum(1)
        self.delay_slider.setMaximum(10)
        self.delay_slider.setValue(5)  # Valor predeterminado
        self.delay_slider.setTickInterval(1)
        self.delay_slider.setTickPosition(QSlider.TicksBelow)

        # Icono de tortuga para el lado lento
        self.turtle_icon_label = QLabel()
        turtle_pixmap = QPixmap("../assets/icons/turtle-du.svg").scaled(35, 35, Qt.KeepAspectRatio)
        self.turtle_icon_label.setPixmap(turtle_pixmap)
        self.delay_slider_layout.addWidget(self.turtle_icon_label)

        self.delay_slider_layout.addWidget(self.delay_slider)

        # Icono de conejo para el lado rápido
        self.rabbit_icon_label = QLabel()
        rabbit_pixmap = QPixmap("../assets/icons/rabbit-running-du.svg").scaled(35, 35, Qt.KeepAspectRatio)
        self.rabbit_icon_label.setPixmap(rabbit_pixmap)
        self.delay_slider_layout.addWidget(self.rabbit_icon_label)

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
        self.zpl_textedit = QTextEdit()
        self.zpl_textedit.setPlaceholderText("Ingrese el ZPL aquí...")
        self.zpl_textedit.textChanged.connect(self.validate_and_update_copies_from_zpl)
        zpl_layout.addWidget(self.zpl_textedit)

        # Creación del menú desplegable para las impresoras
        self.printer_selector = QComboBox()
        self.printer_selector.addItem(QIcon("../assets/icons/printer.svg"), "Seleccione una impresora",
                                      None)  # Opción por defecto
        # self.printer_selector.addItem(QIcon("../assets/icons/printer.svg"), "Impresora 1", None)

        # self.printer_selector.setStyleSheet("""
        #     QComboBox:on {
        #         padding-top: 15px;
        #         padding-left: 15px;
        #     }
        # """)

        #         self.printer_selector.setStyleSheet("""
        #                 QComboBox:!editable, QComboBox::drop-down:editable {
        #      background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        #                                  stop: 0 #E1E1E1, stop: 0.4 #DDDDDD,
        #                                  stop: 0.5 #D8D8D8, stop: 1.0 #D3D3D3);
        # }
        #         """)

        # Filtra y agrega los nombres de las impresoras al menú desplegable
        for printer in json_printers:
            if printer["EnableBIDI"] == "TRUE":
                self.printer_selector.addItem(QIcon("../assets/icons/printer.svg"), printer['Name'],
                                              printer['DeviceID'])

        self.printer_selector.currentTextChanged.connect(self.on_printer_selected)  # Conectar la señal al método
        zpl_layout.addWidget(self.printer_selector)

        # Botón para borrar el contenido de QTextEdit
        self.clear_zpl_button = QPushButton("Borrar ZPL")
        # Establecer el ícono en el botón
        self.clear_zpl_button.setIcon(QIcon("../assets/icons/delete-left.svg"))
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

    def validate_and_update_copies_from_zpl(self):
        zpl_text = self.zpl_textedit.toPlainText()
        pq_index = zpl_text.find('^PQ')
        if pq_index != -1:
            # Encuentra el número de copias en el ZPL
            start_index = pq_index + 3
            end_index = zpl_text.find(',', start_index)
            if end_index == -1:
                end_index = len(zpl_text)

            copies_str = zpl_text[start_index:end_index]
            if copies_str.isdigit():
                self.copies_entry.setText(copies_str)

    def update_zpl_from_copies(self):
        copies_text = self.copies_entry.text()
        if copies_text.isdigit():
            new_copies = int(copies_text)
            zpl_text = self.zpl_textedit.toPlainText()
            pq_index = zpl_text.find('^PQ')
            if pq_index != -1:
                # Reemplazar el número de copias existente
                start_index = pq_index + 3
                end_index = zpl_text.find(',', start_index)
                if end_index == -1:
                    end_index = len(zpl_text)
                new_zpl_text = zpl_text[:start_index] + str(new_copies) + zpl_text[end_index:]
                self.zpl_textedit.setPlainText(new_zpl_text)
            else:
                # Añadir la instrucción ^PQ con el número de copias al final si no existe
                self.zpl_textedit.setPlainText(zpl_text + f"\n^PQ{new_copies},0,1,Y^XZ")

    def on_printer_selected(self, name):
        if name != "Seleccione una impresora":
            self.selected_printer_name = name
            print(name)

    def keyPressEvent(self, event):
        key = event.key()

        if key == Qt.Key_Left:
            # Disminuir el valor del slider
            self.delay_slider.setValue(self.delay_slider.value() - 1)
        elif key == Qt.Key_Right:
            # Aumentar el valor del slider
            self.delay_slider.setValue(self.delay_slider.value() + 1)
        elif key == Qt.Key_Space:
            # Pausar/reanudar la impresión
            self.toggle_pause()
            # Si se reanuda, comienza inmediatamente con la siguiente impresión sin esperar el delay
            if not self.is_paused and self.print_thread is not None:
                self.print_thread.pause = False
        elif key == Qt.Key_F5:
            # Iniciar/detener la impresión
            if self.print_thread is None or not self.print_thread.isRunning():
                self.start_printing()
            else:
                self.stop_printing()
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

    def check_delay_value(self, text):
        try:
            value = float(text)
            if value > 20.99:
                self.delay_entry.setText("20.99")
        except ValueError:
            pass  # En caso de valor no convertible, no hacer nada (el validador manejará esto).

    def start_printing(self):
        copies_text = self.copies_entry.text()
        delay_text = self.delay_entry.text()
        zpl_text = self.zpl_textedit.toPlainText()
        print(zpl_text)

        # Asegurarse de que los campos no estén vacíos
        if not copies_text or not delay_text:
            QMessageBox.warning(self, "Error de validación", "Los campos no pueden estar vacíos.")
            return

        # Utilizar hasAcceptableInput para verificar si el contenido de los campos es válido
        if not self.copies_entry.hasAcceptableInput() or not self.delay_entry.hasAcceptableInput():
            QMessageBox.warning(self, "Error de validación", "Por favor, ingresa valores válidos.")
            return

        copies = int(copies_text)
        delay = float(delay_text)

        if self.print_thread is not None and self.print_thread.isRunning():
            QMessageBox.warning(self, "Advertencia", "Ya hay un proceso de impresión en curso.")
            return

        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.print_thread = PrintThread(copies, delay, zpl_text, self.selected_printer_name)
        self.print_thread.update_signal.connect(self.update_status)
        self.print_thread.finished_signal.connect(self.printing_finished)
        self.print_thread.start()

    def toggle_pause(self):
        # Cambia el estado de pausa
        if self.print_thread and self.print_thread.isRunning():
            self.pause_button.setText("Reanudar")
            self.is_paused = True
            self.print_thread.toggle_pause()
        else:
            self.pause_button.setText("Pausar")
            self.is_paused = False

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
        # QMessageBox.information(self, "Impresión completada", "Todas las etiquetas han sido impresas.")


if __name__ == "__main__":
    app = QApplication([])

    # Cargar la fuente desde el archivo
    novaMediumId = QFontDatabase.addApplicationFont(
        "../assets/fonts/proxima-nova/ProximaNovaWide-Regular.otf")  # Ajusta la ruta a tu archivo de fuente
    fontFamilies = QFontDatabase.applicationFontFamilies(novaMediumId)
    if fontFamilies:  # Verifica si la fuente se cargó correctamente
        novaMediumFont = QFont(fontFamilies[0], 9, 600)  # Establece el tamaño de la fuente a 10 puntos
        # novaMediumFont.setLetterSpacing(QFont.PercentageSpacing, 110)  # Aumenta el espaciado entre letras en un 10%
        app.setFont(novaMediumFont)  # Aplica la fuente a toda la aplicación

    # Cargar la segunda fuente desde el archivo
    novaBoldId = QFontDatabase.addApplicationFont("../assets/fonts/proxima-nova/ProximaNovaWide-Bold.otf")
    specific_font_families = QFontDatabase.applicationFontFamilies(novaBoldId)
    if specific_font_families:
        novaBoldFont = QFont(specific_font_families[0], 10)  # Establecer tamaño de 14 puntos para esta fuente
        # novaBoldFont.setLetterSpacing(QFont.PercentageSpacing, 120)  # Aumenta el espaciado entre letras en un 10%

    window = MainWindow()
    # Aquí estableces el ícono de la ventana
    window.setWindowIcon(QIcon('../assets/logos/tecneu-logo.ico'))
    window.show()
    app.exec_()
