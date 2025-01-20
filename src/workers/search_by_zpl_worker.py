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
        # 1) Llamada (potencialmente costosa) a la API
        item = self.api.get_mercadolibre_item(self.inventory_id, self.query_params)

        # 2) Determinar qué ZPL usar:
        #    - Si la API devolvió un ZPL nuevo en 'item["label"]', úsalo.
        #    - De lo contrario, usa el ZPL original que venía en 'self.new_zpl_text'.
        if item and "label" in item:
            final_zpl = item["label"]
        else:
            final_zpl = self.new_zpl_text

        # 3) Emitimos la señal con el 'item' y el ZPL final que se usará
        self.signals.finished.emit(item, final_zpl)
