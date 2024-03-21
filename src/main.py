from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
from PyQt5.QtGui import QIcon, QValidator, QIntValidator, QDoubleValidator
from PyQt5.QtCore import QThread, pyqtSignal
import re
import time
from zebra import Zebra


class PrintThread(QThread):
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, copies, delay, printer_name='ZD410'):
        super().__init__()
        self.copies = copies
        self.delay = delay
        self.printer_name = printer_name
        self.pause = False
        self.stopped = False

    def run(self):
        z = Zebra(self.printer_name)
        z.setqueue(self.printer_name)
        label = """
^XA
^CI28
^LH0,0
^FO75,18^BY2^BCN,54,N,N^FDSMBG62283^FS  // Ajustado de ^FO89,18 a ^FO105,18 para añadir 2mm más
^FT160,98^A0N,22,22^FH^FDSMBG62283^FS   // Ajustado de ^FT174,98 a ^FT190,98
^FT159,98^A0N,22,22^FH^FDSMBG62283^FS   // Ajustado de ^FT173,98 a ^FT189,98
^FO62,115^A0N,18,18^FB326,2,0,L^FH^FD120 Cables Jumpers Dupont H_2Dh_2C M_2Dm_2C H_2Dm 10cm Para Protoboard^FS  // Ajustado de ^FO46,115 a ^FO62,115 y reducido el ancho para compensar
^FO62,150^A0N,18,18^FB326,1,0,L^FH^FDMixto (40 C/U)^FS  // Ajustado de ^FO46,150 a ^FO62,150 y reducido el ancho para compensar
^FO61,150^A0N,18,18^FB326,1,0,L^FH^FDMixto (40 C/U)^FS  // Ajustado de ^FO45,150 a ^FO61,150 y reducido el ancho para compensar
^FO62,170^A0N,18,18^FH^FDCod. Universal: 788194520596^FS  // Ajustado de ^FO46,170 a ^FO62,170
^FO62,170^A0N,18,18^FH^FD^FS  // Ajustado de ^FO46,170 a ^FO62,170
^PQ1,0,1,Y^XZ
"""
        for i in range(self.copies):
            if self.stopped:
                break
            while self.pause:
                time.sleep(1)
            z.output(label)
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
        super(CustomDoubleValidator, self).__init__(bottom, top, decimals, parent)

    def validate(self, string, pos):
        if not string:  # Si el string está vacío, es aceptable.
            return QValidator.Acceptable, string, pos
        try:
            value = float(string)
            if self.bottom() <= value <= self.top():
                return QValidator.Acceptable, string, pos
            return QValidator.Invalid, string, pos
        except ValueError:
            return QValidator.Invalid, string, pos

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.print_thread = None

    def init_ui(self):
        self.setWindowTitle("Tecneu - Tagger")
        self.setGeometry(800, 100, 400, 200)  # x, y, width, height

        # Establecer el tamaño mínimo de la ventana
        self.setMinimumSize(400, 200)

        layout = QVBoxLayout()

        self.copies_entry = QLineEdit()
        self.copies_entry.setPlaceholderText("Número de copias")
        # Aplicar validador para asegurar solo entrada de enteros
        self.copies_entry.setValidator(QIntValidator(0, 999))
        layout.addWidget(self.copies_entry)

        self.delay_entry = QLineEdit()
        self.delay_entry.setPlaceholderText("Retraso entre copias (segundos)")
        validator = CustomDoubleValidator(0, 20.99, 2)
        self.delay_entry.setValidator(validator)
        # self.delay_entry.textChanged.connect(self.check_delay_value)
        layout.addWidget(self.delay_entry)

        self.start_button = QPushButton("Iniciar Impresión")
        self.start_button.clicked.connect(self.start_printing)
        layout.addWidget(self.start_button)

        self.pause_button = QPushButton("Pausar")
        self.pause_button.clicked.connect(self.toggle_pause)
        layout.addWidget(self.pause_button)

        self.status_label = QLabel("Etiquetas restantes: 0")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def check_delay_value(self, text):
        try:
            value = float(text)
            if value > 20.99:
                self.delay_entry.setText("20.99")
        except ValueError:
            pass  # En caso de valor no convertible, no hacer nada (el validador manejará esto).

    def validate_float(self, text):
        return bool(re.match(r"^[0-9]*\.?[0-9]{0,2}$", text))

    def validate_int(self, text):
        return bool(re.match("^[0-9]{0,3}$", text))

    def start_printing(self):
        copies_text = self.copies_entry.text()
        delay_text = self.delay_entry.text()

        if not self.validate_int(copies_text) or not self.validate_float(delay_text):
            QMessageBox.warning(self, "Error de validación", "Por favor, ingresa valores válidos.")
            return

        copies = int(copies_text)
        delay = float(delay_text)

        if self.print_thread is not None and self.print_thread.isRunning():
            QMessageBox.warning(self, "Advertencia", "Ya hay un proceso de impresión en curso.")
            return

        self.print_thread = PrintThread(copies, delay)
        self.print_thread.update_signal.connect(self.update_status)
        self.print_thread.finished_signal.connect(self.printing_finished)
        self.print_thread.start()

    def toggle_pause(self):
        if self.print_thread and self.print_thread.isRunning():
            self.print_thread.toggle_pause()

    def update_status(self, message):
        self.status_label.setText(message)

    def printing_finished(self):
        self.status_label.setText("Impresión completada.")
        QMessageBox.information(self, "Impresión completada", "Todas las etiquetas han sido impresas.")


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    # Aquí estableces el ícono de la ventana
    window.setWindowIcon(QIcon('../assets/logos/tecneu-logo.ico'))
    window.show()
    app.exec_()
