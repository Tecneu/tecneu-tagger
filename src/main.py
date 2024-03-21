from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, \
    QMessageBox, QTextEdit
from PyQt5.QtGui import QIcon, QValidator, QIntValidator, QDoubleValidator, QFont, QFontDatabase
from PyQt5.QtCore import QThread, pyqtSignal, Qt
import time
from zebra import Zebra


class PrintThread(QThread):
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, copies, delay, zpl, printer_name='ZD410'):
        super().__init__()
        self.copies = copies
        self.delay = delay
        self.zpl = zpl
        self.printer_name = printer_name
        self.pause = False
        self.stopped = False

    def run(self):
        z = Zebra(self.printer_name)
        z.setqueue(self.printer_name)
        #         label = """
        # ^XA
        # ^CI28
        # ^LH0,0
        # ^FO75,18^BY2^BCN,54,N,N^FDSMBG62283^FS
        # ^FT160,98^A0N,22,22^FH^FDSMBG62283^FS
        # ^FT159,98^A0N,22,22^FH^FDSMBG62283^FS
        # ^FO62,115^A0N,18,18^FB304,2,0,L^FH^FD120 Cables Jumpers Dupont H_2Dh_2C M_2Dm_2C H_2Dm 10cm Para Protoboard^FS
        # ^FO62,150^A0N,18,18^FB304,1,0,L^FH^FDMixto (40 C/U)^FS
        # ^FO61,150^A0N,18,18^FB304,1,0,L^FH^FDMixto (40 C/U)^FS
        # ^FO62,170^A0N,18,18^FH^FDCod. Universal: 788194520596^FS
        # ^FO62,170^A0N,18,18^FH^FD^FS
        # ^PQ1,0,1,Y^XZ
        # """
        for i in range(self.copies):
            if self.stopped:
                break
            while self.pause:
                time.sleep(1)
            z.output(self.zpl)
            self.update_signal.emit(f"Etiquetas restantes: {self.copies - i - 1}")
            if i < self.copies - 1:
                time.sleep(self.delay)
        self.finished_signal.emit()

    def toggle_pause(self):
        self.pause = not self.pause

    def stop_printing(self):
        self.stopped = True


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
        # Inicializa un atributo para llevar el seguimiento del estado de pausa
        self.is_paused = False

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
        control_layout.addWidget(self.copies_entry)

        self.delay_entry = QLineEdit()
        self.delay_entry.setPlaceholderText("Retraso entre copias (segundos)")
        validator = CustomDoubleValidator(0, 15.99, 2)
        self.delay_entry.setValidator(validator)
        # self.delay_entry.textChanged.connect(self.check_delay_value)
        control_layout.addWidget(self.delay_entry)

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
        zpl_layout.addWidget(self.zpl_textedit)

        # Botón para borrar el contenido de QTextEdit
        self.clear_zpl_button = QPushButton("Borrar ZPL")
        self.clear_zpl_button.clicked.connect(self.zpl_textedit.clear)
        zpl_layout.addWidget(self.clear_zpl_button)

        # Agregar los layouts al layout principal
        main_layout.addLayout(control_layout)
        main_layout.addLayout(zpl_layout)  # Añadir el layout de ZPL al layout principal

        self.setLayout(main_layout)

    def keyPressEvent(self, event):
        print(event.key())
        # Verifica si la tecla presionada es la tecla espacio
        if event.key() == Qt.Key_Space:
            self.toggle_pause()
        else:
            super().keyPressEvent(event)  # Llama al método base para manejar otras teclas

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
        self.print_thread = PrintThread(copies, delay, zpl_text)
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
        QMessageBox.information(self, "Impresión completada", "Todas las etiquetas han sido impresas.")


if __name__ == "__main__":
    app = QApplication([])

    # Cargar la fuente desde el archivo
    novaMediumId = QFontDatabase.addApplicationFont(
        "../assets/fonts/proxima-nova/ProximaNovaWide-Regular.otf")  # Ajusta la ruta a tu archivo de fuente
    fontFamilies = QFontDatabase.applicationFontFamilies(novaMediumId)
    if fontFamilies:  # Verifica si la fuente se cargó correctamente
        novaMediumFont = QFont(fontFamilies[0], 9)  # Establece el tamaño de la fuente a 10 puntos
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
