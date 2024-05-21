from PyQt5.QtCore import QThread, pyqtSignal
import re
import math
import time
import threading
from zebra import Zebra

# print_thread.py
__all__ = ['PrintThread']


class PrintThread(QThread):
    """
    Clase para gestionar la impresión en un hilo separado.
    """
    update_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    request_pause_signal = pyqtSignal()  # Nueva señal para solicitar pausa

    def __init__(self, copies, delay, zpl, printer_name):
        super().__init__()
        self.copies = copies
        self.delay = delay
        self.zpl = zpl
        self.printer_name = printer_name
        self.pause = False
        self.stopped = False
        self.manually_stopped = False
        self.condition = threading.Condition()
        self.lock = threading.Lock()  # Lock para proteger el acceso a self.copies
        self.z = Zebra(self.printer_name)  # Inicializa aquí
        try:
            self.z.setqueue(self.printer_name)
        except Exception as e:
            self.error_signal.emit(f"Error al establecer la cola de la impresora{': ' if str(e) else ''}{e}.")

    def run(self):
        """
        Método principal del hilo que maneja el proceso de impresión.
        """
        while not self.stopped:
            if self.copies <= 0:
                self.finished_signal.emit()
                break

            # Espera aquí mientras estamos pausados
            while self.pause:
                with self.condition:
                    self.condition.wait()

            # Imprime una etiqueta a la vez
            self.print_label()
            print(f"self.copies: {self.copies}.")
            with self.lock:
                self.copies -= 1  # Asegurar la operación atómica sobre self.copies

            self.update_signal.emit(f"{self.copies}")  # Etiquetas restantes

            if self.copies > 0:  # No esperar después de la última etiqueta
                self.wait_with_delay()

        if not self.manually_stopped:  # Emitir la señal solo si no se detuvo manualmente
            self.finished_signal.emit()

    def print_label(self):
        """
        Modifica el ZPL para imprimir una copia a la vez y maneja la impresión.
        """
        single_copy_zpl = re.sub(r'\^PQ[0-9]+', '^PQ1', self.zpl, flags=re.IGNORECASE)
        try:
            self.z.output(single_copy_zpl)
            print(f"Impresión realizada")
        except Exception as e:
            self.error_signal.emit(f"Error al imprimir{': ' if str(e) else ''}{e}.")

    def print_and_pause(self):
        """
        Imprime inmediatamente una etiqueta y luego pausa la impresión.
        """
        # if not self.pause:
        if (self.copies > 0):
            self.print_label()
            with self.lock:
                self.copies -= 1  # Asegurar la operación atómica sobre self.copies
            self.update_signal.emit(str(self.copies))
            print(f"self.copies: {self.copies}.")
            if (self.copies != 0):
                self.pause = True
                self.request_pause_signal.emit()  # Emite una señal para que la UI maneje la pausa
            else:
                print("finished_signal.emit")
                self.finished_signal.emit()

    def set_copies_and_zpl(self, copies, zpl):
        with self.lock:
            self.copies = copies
            self.zpl = zpl
            self.pause = False  # Reinicia la pausa para asegurar que no esté pausada al cambiar de trabajo

    def wait_with_delay(self):
        """
        Este método espera un tiempo basado en el valor de 'delay' antes de imprimir la siguiente etiqueta.
        """
        base = 1.05
        min_delay = 1
        logaritmic_delay = math.log(self.delay + 1 - min_delay, base)
        inverse_logaritmic_delay = self.calculate_inverse_delay(logaritmic_delay, 0.5, 80)
        with self.condition:
            self.condition.wait(inverse_logaritmic_delay)

    def calculate_inverse_delay(self, slider_value, min_slider, max_slider):
        max_delay = 12
        min_delay = 0.7

        # Aplicamos la fórmula de mapeo inverso
        delay = max_delay + (slider_value - min_slider) * (min_delay - max_delay) / (max_slider - min_slider)
        return delay

    def set_delay(self, delay):
        """
        Actualiza el valor de delay para la impresión en tiempo real.
        """
        # self.delay = delay
        with self.condition:
            self.delay = delay
            # self.condition.notify()  # Notificar al hilo de la actualización

    def apply_delay_change(self):
        """
        Notifica al hilo de la impresión que el delay ha sido actualizado y
        que puede proceder con la impresión si es necesario.
        """
        with self.condition:
            self.condition.notify()

    def toggle_pause(self):
        """
        Método para pausar o reanudar la impresión.
        """
        print("toggle_pause called")
        self.pause = not self.pause
        if not self.pause:  # Si se está reanudando la impresión
            with self.condition:
                self.condition.notify()  # Despierta el hilo si estaba esperando debido a una pausa

    def stop_printing(self):
        """
        Método para detener la impresión.
        """
        self.stopped = True
