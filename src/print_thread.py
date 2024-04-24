from PyQt5.QtCore import QThread, pyqtSignal
import re
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
                # z.output(single_copy_zpl)
                print("")
            except Exception as e:
                self.error_signal.emit(f"Error al imprimir{': ' if str(e) else ''}{e}.")
                break
            self.update_signal.emit(f"{self.copies - i - 1}")  # Etiquetas restantes
            # Mapeo inverso para el delay
            with self.condition:
                inverse_delay = 12 - (self.delay - 1) * (11.3 / 49)  # Mapeo de 50->0.7 y 1->12
                self.condition.wait(inverse_delay)

                if self.delay_updated:
                    # Si el delay fue actualizado, espera con el nuevo delay y resetea el flag
                    inverse_delay = 12 - (self.delay - 1) * (11.3 / 49)
                    self.condition.wait(inverse_delay)
                    self.delay_updated = False

            # if i < self.copies - 1:
            #     time.sleep(inverse_delay)

        if not self.manually_stopped:  # Emitir la señal solo si no se detuvo manualmente
            self.finished_signal.emit()

    def set_delay(self, delay):
        """
        Actualiza el valor de delay para la impresión en tiempo real.
        """
        # self.delay = delay
        with self.condition:
            self.delay = delay
            self.delay_updated = True
            self.condition.notify()  # Notificar al hilo de la actualización

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
