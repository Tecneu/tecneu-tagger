# search_worker.py
from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot


class WorkerSignals(QObject):
    # Señal que emite el resultado de la tarea.
    finished = pyqtSignal(object)  # Devuelve el objeto que obtengas (por ej. item)


class SearchWorker(QRunnable):
    def __init__(self, api, inventory_id, query_params):
        super().__init__()
        self.api = api
        self.inventory_id = inventory_id
        self.query_params = query_params
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        """Este método se ejecuta en segundo plano para evitar bloquear la UI."""
        # Llamada a tu API que puede demorar
        item = self.api.get_mercadolibre_item(self.inventory_id, self.query_params)
        # Emite la señal con el resultado
        self.signals.finished.emit(item)
