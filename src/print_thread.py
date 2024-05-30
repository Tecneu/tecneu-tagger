from PyQt5.QtCore import QThread, pyqtSignal
import re
import math
import time
import threading
from zebra import Zebra
from config import MAX_DELAY

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
        self.lock = threading.Lock()  # Lock para proteger el acceso a self.copies
        self.z = Zebra(self.printer_name)  # Inicializa aquí
        self.reset_thread_state()  # Asegurar que el estado del hilo esté correcto cada vez que se inicie run()
        try:
            self.z.setqueue(self.printer_name)
        except Exception as e:
            self.error_signal.emit(f"Error al establecer la cola de la impresora{': ' if str(e) else ''}{e}.")

    def reset_thread_state(self):
        """
        Restablece las variables del hilo a su estado inicial.
        """
        self.pause = False
        self.stopped = False
        self.manually_stopped = False
        self.initiated_by_double_click = False
        self.condition = threading.Condition()

    def run(self):
        """
        Método principal del hilo que maneja el proceso de impresión.
        """
        first_iteration = True
        while not self.stopped:
            # Espera aquí mientras estamos pausados
            if self.pause or (first_iteration and self.initiated_by_double_click):
                with self.condition:
                    while (self.pause or (first_iteration and self.initiated_by_double_click)) and not self.stopped:
                        first_iteration = False
                        self.condition.wait()

            # Imprime una etiqueta a la vez
            self.print_label()

            self.update_signal.emit(str(self.copies))  # Etiquetas restantes

            if self.copies <= 0 or self.stopped:
                break  # Sal del ciclo si no hay más copias o se ha solicitado detener.

            # print(f"self.copies_mult: {self.copies}.")

            if self.copies > 0:  # No esperar después de la última etiqueta
                self.wait_with_delay()

        if not self.manually_stopped:  # Emitir la señal solo si no se detuvo manualmente
            self.finished_signal.emit()

        self.reset_thread_state()  # Asegurar que el estado del hilo esté correcto cada vez que se inicie run()

    def print_label(self):
        """
        Modifica el ZPL para imprimir una copia a la vez y maneja la impresión.
        """
        if self.delay == MAX_DELAY:  # Supongamos que MAX_DELAY es el valor máximo del slider
            # Modifica ZPL para imprimir todas las etiquetas restantes
            all_copies_zpl = re.sub(r'\^PQ[0-9]+', f'^PQ{self.copies}', self.zpl, flags=re.IGNORECASE)
            zpl_to_print = all_copies_zpl
            with self.lock:
                self.copies = 0  # Asegurar la operación atómica sobre self.copies
        else:
            # Modifica ZPL para imprimir una copia a la vez
            single_copy_zpl = re.sub(r'\^PQ[0-9]+', '^PQ1', self.zpl, flags=re.IGNORECASE)
            zpl_to_print = single_copy_zpl
            with self.lock:
                self.copies -= 1  # Asegurar la operación atómica sobre self.copies

        try:
            self.z.output(zpl_to_print)
            print(f"Impresión realizada")
        except Exception as e:
            self.error_signal.emit(f"Error al imprimir{': ' if str(e) else ''}{e}.")

    def stop_printing(self):
        """
        Método para detener la impresión. Configura la bandera `stopped` y notifica todas las esperas.
        """
        with self.condition:
            self.stopped = True
            self.condition.notify_all()  # Asegúrate de despertar todos los hilos que están esperando

        if self.isRunning():
            self.wait()  # Espera a que el hilo termine

    def print_and_pause(self):
        """
        Imprime inmediatamente una etiqueta y luego pausa la impresión.
        """
        if self.copies > 0:
            self.print_label()
            with self.lock:
                self.copies -= 1  # Asegurar la operación atómica sobre self.copies
            self.update_signal.emit(str(self.copies))
            print(f"self.copies_single: {self.copies}.")
            if self.copies > 0:
                self.pause = True
                self.request_pause_signal.emit()  # Emite una señal para que la UI maneje la pausa
            else:
                with self.condition:
                    self.stopped = True  # Detiene el hilo si no quedan más copias
                    self.condition.notify_all()  # Asegúrate de despertar el hilo si está esperando.
                print("Finalización emitida desde print_and_pause después de la última etiqueta.")

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
