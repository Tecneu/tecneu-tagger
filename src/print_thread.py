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
        self.delay_updated = False  # Nuevo flag para rastrear la actualización del delay

    def run(self):
        """
        Método principal del hilo que maneja el proceso de impresión.
        """
        z = Zebra(self.printer_name)
        try:
            z.setqueue(self.printer_name)
        except Exception as e:
            self.error_signal.emit(f"Error al establecer la cola de la impresora{': ' if str(e) else ''}{e}.")
            return
        for i in range(self.copies):
            if self.stopped:
                self.manually_stopped = True  # Indicar que la impresión fue detenida manualmente
                break
            while self.pause:
                time.sleep(1)

            # Modificar el ZPL para imprimir una copia a la vez
            single_copy_zpl = re.sub(r'\^PQ[0-9]+', '^PQ1', self.zpl, flags=re.IGNORECASE)

            print(f"Numero de copia: {i}")
            try:
                z.output(single_copy_zpl)
            except Exception as e:
                self.error_signal.emit(f"Error al imprimir{': ' if str(e) else ''}{e}.")
                break
            self.update_signal.emit(f"{self.copies - i - 1}")  # Etiquetas restantes
            # Mapeo inverso para el delay
            with self.condition:
                # inverse_delay = 12 - (self.delay - 1) * (11.3 / 49)  # Mapeo de 50->0.7 y 1->12
                # Ajusta 'base' para cambiar la curva exponencial
                base = 1.05  # Un número mayor que 1
                min_delay = 1  # El menor delay posible para evitar math.log(0)
                logaritmic_delay = math.log(self.delay + 1 - min_delay, base)
                inverse_logaritmic_delay = self.calculate_inverse_delay(logaritmic_delay, 0.5, 80)
                print('inverse_logaritmic_delay:', inverse_logaritmic_delay)
                self.condition.wait(inverse_logaritmic_delay)

                if self.delay_updated:
                    # Si el delay fue actualizado, espera con el nuevo delay y resetea el flag
                    # Ajusta 'base' para cambiar la curva exponencial
                    base = 1.05  # Un número mayor que 1
                    min_delay = 1  # El menor delay posible para evitar math.log(0)
                    logaritmic_delay = math.log(self.delay + 1 - min_delay, base)
                    inverse_logaritmic_delay = self.calculate_inverse_delay(logaritmic_delay, 0.5, 80)
                    print('inverse_logaritmic_delay:', inverse_logaritmic_delay)
                    self.condition.wait(inverse_logaritmic_delay)
                    self.delay_updated = False

            # if i < self.copies - 1:
            #     time.sleep(inverse_delay)

        if not self.manually_stopped:  # Emitir la señal solo si no se detuvo manualmente
            self.finished_signal.emit()

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
            self.delay_updated = True
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
        self.pause = not self.pause

    def stop_printing(self):
        """
        Método para detener la impresión.
        """
        self.stopped = True
