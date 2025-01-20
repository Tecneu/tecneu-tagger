# zpl_worker.py
from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

class ZplWorkerSignals(QObject):
    finished = pyqtSignal(dict, str)
    # Podríamos emitir dos cosas:
    #  - El 'item' (dict) devuelto por la API
    #  - El ZPL modificado (str) o lo que necesites devolver

class ZplWorker(QRunnable):
    def __init__(self, api, inventory_id, query_params, new_zpl_text):
        super().__init__()
        self.api = api
        self.inventory_id = inventory_id
        self.query_params = query_params
        self.new_zpl_text = new_zpl_text
        self.signals = ZplWorkerSignals()

    @pyqtSlot()
    def run(self):
        """Método que se ejecuta en segundo plano."""
        # Llamada potencialmente costosa a la API
        item = self.api.get_mercadolibre_item(self.inventory_id, self.query_params)

        # Emitimos la señal con el resultado (item) y el ZPL final que quieras usar
        self.signals.finished.emit(item, self.new_zpl_text)
