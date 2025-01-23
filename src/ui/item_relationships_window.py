from PyQt5.QtCore import (
    Qt, QUrl, QTimer, QPoint, QSize
)
from PyQt5.QtGui import (
    QPalette, QColor, QPixmap, QMovie, QPainter, QPen, QBrush
)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QTableWidgetItem, QHBoxLayout, QLabel, QHeaderView
)
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

import os
from config import BASE_ASSETS_PATH

from .custom_widgets import HoverZoomWindow


# Ajusta a la ruta real de tu spinner.gif
# from paths import BASE_ASSETS_PATH  # Si tienes tu ruta base definida en otro lado

__all__ = ["ItemRelationshipsWindow"]

class ItemRelationshipsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Estado de visibilidad
        self._is_visible = False

        # Semi-transparencia en la paleta
        palette = self.palette()
        color = QColor(255, 255, 255, 51)  # 20% de opacidad
        palette.setColor(QPalette.Window, color)
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        # Layout principal
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Creamos la tabla
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Imagen", "Título", "Cantidad"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.main_layout.addWidget(self.table)

        # Altura fija inicial (puedes ajustarla si lo deseas)
        self.setFixedHeight(200)

        # Manager para descargas de imágenes
        self.network_manager = QNetworkAccessManager(self)

        # Diccionario para almacenar pixmaps originales (igual que en el carrusel)
        self.original_images = {}

        # Control de zoom (si deseas reusar la misma ventana de zoom)
        self.hover_zoom_window = None

        # Fondo/Color que pintaremos (negro 65% opaco). Se setea con setGeometryWithBackground
        self.background_color = QColor(0, 0, 0, 0)  # Negro sin opacidad en inicio

    @property
    def is_visible(self):
        """Retorna si la ventana de relaciones está visible."""
        return self._is_visible

    # ------------------------------------------------------------------------
    # Métodos de visibilidad (similar a ImageCarousel)
    # ------------------------------------------------------------------------
    def toggle_visibility(self, parent_geometry=None):
        if self._is_visible:
            self.hide_relationships()
        else:
            self.show_relationships(parent_geometry)

    def show_relationships(self, parent_geometry=None):
        if not self._is_visible:
            if parent_geometry:
                self._configure_geometry(parent_geometry)
            self.show()
            self._is_visible = True

    def hide_relationships(self):
        if self._is_visible:
            self.hide()
            self.hide_zoom_window()  # Por si hubiera un zoom abierto
            self._is_visible = False

    def _configure_geometry(self, parent_geometry):
        """
        Posiciona la ventana "justo debajo" del carrusel,
        recordando que el carrusel mide 150px de alto.

        De modo que:
          y = parent_geometry.y() + parent_geometry.height() (ventana principal)
            + 150 (carrusel)
        """
        self.setGeometryWithBackground(
            x=parent_geometry.x(),
            y=parent_geometry.y() + parent_geometry.height() + 150,
            width=parent_geometry.width(),
            height=self.height(),  # Usamos la altura actual fija
            background_color="#000000",  # Negro
            opacity=0.65,
        )

    def setGeometryWithBackground(self, x, y, width, height, background_color="#000000", opacity=0.8):
        """
        Aplica geometría y configura el color de fondo semiopaco.
        """
        self.setGeometry(x, y, width, height)

        r, g, b = QColor(background_color).getRgb()[:3]
        alpha = int(opacity * 255)
        self.background_color = QColor(r, g, b, alpha)
        self.update()  # Forzar repintado

    def paintEvent(self, event):
        """Dibuja el rect semiopaco en el fondo."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(self.background_color))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())
        painter.end()

    # ------------------------------------------------------------------------
    # Carga de datos en la tabla
    # ------------------------------------------------------------------------
    def set_relationships_data(self, relationships):
        """
        Recibe el array "tecneu_item_relationships" y lo muestra
        en la tabla.
        """
        self.clear_relationships()

        if not relationships:
            return

        self.table.setRowCount(len(relationships))

        for row, rel in enumerate(relationships):
            # Extraemos la info
            quantity = rel.get("quantity", 0)
            tecneu_item = rel.get("tecneu_item", {})
            title = tecneu_item.get("title", "Sin título")
            pictures = tecneu_item.get("pictures", [])

            image_url = ""
            if pictures:
                image_url = pictures[0].get("url", "")  # Tomar la primera

            # 1) Columna de Imagen
            label = QLabel()
            label.setFixedSize(100, 100)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    border: 1px solid gray;
                    background-color: white;
                }
            """)

            # Mostramos spinner mientras se descarga
            spinner_gif_path = os.fspath(BASE_ASSETS_PATH / "icons" / "spinner.gif")  # Ajusta la ruta
            if os.path.exists(spinner_gif_path):
                spinner = QMovie(spinner_gif_path)
                spinner.setScaledSize(QSize(60, 60))
                label.setMovie(spinner)
                spinner.start()
            else:
                spinner = None
                label.setText("Cargando...")

            self.table.setCellWidget(row, 0, label)

            # Llamamos a descargar la imagen (con reintentos)
            if image_url:
                self.download_image(image_url, label, spinner)

            # 2) Columna de Título
            title_item = QTableWidgetItem(title)
            self.table.setItem(row, 1, title_item)

            # 3) Columna de Cantidad
            quantity_item = QTableWidgetItem(str(quantity))
            self.table.setItem(row, 2, quantity_item)

        # Ajuste de alto de filas (opcional)
        self.table.resizeRowsToContents()

    def clear_relationships(self):
        """Limpia la tabla y pixmaps."""
        self.table.setRowCount(0)
        # Si deseas limpiar self.original_images, hazlo aquí
        self.original_images.clear()

    # ------------------------------------------------------------------------
    # Manejo de descarga de imágenes (similar a ImageCarousel)
    # ------------------------------------------------------------------------
    def download_image(self, url, label, spinner, attempt=1, max_attempts=3):
        request = QNetworkRequest(QUrl(url))
        reply = self.network_manager.get(request)

        # Metemos propiedades para recuperarlas en el manejador
        reply.setProperty("url", url)
        reply.setProperty("label", label)
        reply.setProperty("spinner", spinner)
        reply.setProperty("attempt", attempt)
        reply.setProperty("max_attempts", max_attempts)

        # Timer para timeout (4s)
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(4000)
        timer.timeout.connect(lambda: self.handle_timeout(reply))
        reply.setProperty("timer", timer)
        timer.start()

        # finished signal
        reply.finished.connect(lambda: self.handle_reply(reply))

    @staticmethod
    def handle_timeout(reply):
        """Si pasa el timeout, abortamos la descarga."""
        if reply.isRunning():
            print(f"[ItemRelationships] Timeout. Abort: {reply.property('url')}")
            reply.abort()

    def handle_reply(self, reply):
        url = reply.property("url")
        label = reply.property("label")
        spinner = reply.property("spinner")
        attempt = reply.property("attempt")
        max_attempts = reply.property("max_attempts")
        timer = reply.property("timer")

        if timer and timer.isActive():
            timer.stop()
        if timer:
            timer.deleteLater()

        if reply.error() == QNetworkReply.NoError:
            # Éxito
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                # Guardamos el pixmap original
                self.original_images[url] = pixmap

                # Quitar spinner
                if spinner:
                    spinner.stop()
                label.setMovie(None)

                # Mostrar pixmap escalado a la celda
                scaled = pixmap.scaled(label.width(), label.height(),
                                       Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label.setPixmap(scaled)

                # Configuramos eventos para hover zoom
                self.configure_label_for_zoom(label, url)
            else:
                print(f"[ItemRelationships] Imagen corrupta: {url}")
                self.retry_or_fail(url, label, spinner, attempt, max_attempts, "Imagen inválida")
        else:
            # Error en descarga o abort
            print(f"[ItemRelationships] Error al descargar: {url}")
            self.retry_or_fail(url, label, spinner, attempt, max_attempts, "Error descarga")

        reply.deleteLater()

    def retry_or_fail(self, url, label, spinner, attempt, max_attempts, fail_text):
        if attempt < max_attempts:
            print(f"[ItemRelationships] Reintento {url} (attempt={attempt+1})")
            self.download_image(url, label, spinner, attempt+1, max_attempts)
        else:
            # Sin más reintentos
            if spinner:
                spinner.stop()
            label.setMovie(None)
            label.setText(fail_text)

    # ------------------------------------------------------------------------
    # Lógica de zoom (muy parecida a la del carrusel)
    # ------------------------------------------------------------------------
    def configure_label_for_zoom(self, label, img_url):
        label.setMouseTracking(True)
        label.enterEvent = lambda e, lbl=label: self.show_zoom_window(e, lbl, img_url)
        label.leaveEvent = lambda e, lbl=label: self.clear_grid_and_hide_zoom(lbl)
        label.mouseMoveEvent = lambda e, lbl=label: self.update_zoom_position(e, lbl)

    def show_zoom_window(self, event, label, img_url):
        if self.hover_zoom_window is not None:
            self.hover_zoom_window.close()

        if img_url in self.original_images:
            pixmap = self.original_images[img_url]
            # Reusar tu HoverZoomWindow si deseas
            self.hover_zoom_window = HoverZoomWindow(pixmap, self.parent())
            self.hover_zoom_window.show()
            self.update_zoom_position(event, label)
        else:
            print("[ItemRelationships] No pixmap para zoom")

    def clear_grid_and_hide_zoom(self, label):
        self.restore_original_pixmap(label)
        self.hide_zoom_window()

    def restore_original_pixmap(self, label):
        if hasattr(label, "_original_pixmap"):
            label.setPixmap(label._original_pixmap)
            del label._original_pixmap

    def hide_zoom_window(self):
        if self.hover_zoom_window:
            self.hover_zoom_window.close()
            self.hover_zoom_window = None

    def update_zoom_position(self, event, label):
        if not self.hover_zoom_window:
            return

        local_pos = event.pos()
        label_w, label_h = label.width(), label.height()
        pm = label.pixmap()
        if pm is None:
            return

        pixmap_w, pixmap_h = pm.size().width(), pm.size().height()

        # Escalas
        scale_x = pixmap_w / label_w
        scale_y = pixmap_h / label_h

        pixmap_x = int(local_pos.x() * scale_x)
        pixmap_y = int(local_pos.y() * scale_y)

        # Centramos zoom
        zoom_x = max(0, min(pixmap_x - 20, pixmap_w - 40))
        zoom_y = max(0, min(pixmap_y - 20, pixmap_h - 40))

        self.hover_zoom_window.update_zoom(QPoint(zoom_x, zoom_y), scale_x, scale_y)

        # Dibuja cuadrícula (opcional), igual que en ImageCarousel
        if not hasattr(label, "_original_pixmap"):
            label._original_pixmap = pm.copy()

        pixmap_copy = label._original_pixmap.copy()
        painter = QPainter(pixmap_copy)
        pen = QPen(QColor(0, 0, 255, 128))
        pen.setWidth(1)
        painter.setPen(pen)
        grid_size = 2
        for gx in range(zoom_x, zoom_x + 40, grid_size):
            for gy in range(zoom_y, zoom_y + 40, grid_size):
                painter.drawPoint(gx, gy)
        painter.end()

        label.setPixmap(pixmap_copy)
        label.update()

