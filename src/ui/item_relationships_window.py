from PyQt5.QtCore import (
    Qt, QUrl, QTimer, QPoint, QSize
)
from PyQt5.QtGui import (
    QPalette, QColor, QPixmap, QMovie, QPainter, QPen, QBrush
)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QTableWidgetItem, QHBoxLayout, QLabel, QHeaderView, QApplication
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

        # Creamos la tabla (inicialmente 0 filas/0 columnas)
        self.table = QTableWidget()
        self.main_layout.addWidget(self.table)

        # # Creamos la tabla con 3 columnas:
        # #   Columna 0 -> Imagen
        # #   Columna 1 -> Título
        # #   Columna 2 -> Variante
        # # El encabezado vertical lo usaremos para "Cantidad"
        # self.table = QTableWidget()
        # self.table.setColumnCount(3)
        # self.table.setHorizontalHeaderLabels(["Imagen", "Título", "Variante"])
        # self.main_layout.addWidget(self.table)

        # Altura fija inicial (puedes ajustarla si lo deseas)
        self.setFixedHeight(200)

        # Manager para descargas
        self.network_manager = QNetworkAccessManager(self)
        self.original_images = {}
        self.hover_zoom_window = None

        # Diccionario para mapear row -> tecneu_item_id
        self._row_to_item_id = {}

        # Fondo/Color que pintaremos (negro 65% opaco). Se setea con setGeometryWithBackground
        self.background_color = QColor(0, 0, 0, 0)  # Negro sin opacidad en inicio

        # --------------------------
        # Ajustes de estilo en la tabla
        # --------------------------
        # Hacemos transparente todo, texto y bordes blancos
        # Y controlamos la selección para que, al des-seleccionar, quede transparente.
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;       /* Fondo transparente */
                color: white;                        /* Texto blanco */
                gridline-color: white;               /* Líneas en blanco */
                selection-background-color: rgba(0, 0, 255, 80); /* Azul transparente al seleccionar */
                selection-color: white;              /* Texto blanco cuando se selecciona */
            }
            QHeaderView::section {
                background-color: transparent;       /* Encabezados sin fondo */
                color: white;                        /* Texto blanco */
                border: 1px solid white;             /* Bordes blancos */
                font-weight: bold;                   /* Negritas */
                font-size: 12pt;                     /* Tamaño de letra */
            }
            QTableCornerButton::section {
                background-color: transparent;       /* Esquina sup-izq sin fondo */
                border: 1px solid white;
            }
        """)

        # Ajustar altura del header horizontal
        self.table.horizontalHeader().setFixedHeight(30)

        # Ocultamos el header horizontal de filas (números) y lo usamos para la cantidad
        # Realmente NO lo ocultamos, sino que ocultamos la numeración automática:
        #  - setVerticalHeader() visible, pero setVerticalHeaderItem() con la cantidad
        #  - Deshabilitar la numeración por defecto:
        self.table.verticalHeader().setVisible(True)  # Para mostrar la columna lateral, si deseamos
        # self.table.verticalHeader().setDefaultSectionSize(30)  # Altura de cada "encabezado" de fila
        # Fijamos ancho de la cabecera vertical a 20 px
        self.table.verticalHeader().setFixedWidth(20)
        # Dejarlo visible para mostrar la cantidad en esa parte
        # Si no deseas ver la barra de la izquierda, usa setVisible(False) y en su lugar
        # añade otra columna. Pero según lo pedido, la usaremos para la cantidad.

        # Columnas expandibles
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Hacer celdas read-only pero copiables:
        #   - QAbstractItemView::NoEditTriggers evita edición con doble clic
        #   - El usuario aún puede seleccionar y copiar
        self.table.setEditTriggers(self.table.NoEditTriggers)
        self.table.setSelectionBehavior(self.table.SelectItems)
        self.table.setSelectionMode(self.table.SingleSelection)

        # Conectamos la señal de doble clic
        self.table.cellDoubleClicked.connect(self.handle_cell_double_clicked)

    # ------------------------------------------------------------------------
    # Manejo de visibilidad (similar a ImageCarousel)
    # ------------------------------------------------------------------------
    @property
    def is_visible(self):
        """Retorna si la ventana de relaciones está visible."""
        return self._is_visible

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
        self._row_to_item_id.clear()

        if not relationships:
            return

        # ¿Hay alguna relación que tenga variant?
        has_variant = any(
            rel.get("tecneu_item", {}).get("variations")
            for rel in relationships
        )

        # Si hay variantes, tendremos 3 columnas: Imagen, Título, Variante
        # Si no, solo 2 columnas: Imagen, Título
        if has_variant:
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["Imagen", "Título", "Variante"])
        else:
            self.table.setColumnCount(2)
            self.table.setHorizontalHeaderLabels(["Imagen", "Título"])

        # +1 fila adicional para poner en la fila 0 el título "Relaciones"
        row_count = len(relationships) + 1
        self.table.setRowCount(row_count)

        # ------------------------------------------------------------------
        # Fila 0 => título "Relaciones" (se expande en todas las columnas)
        # ------------------------------------------------------------------
        self.table.setSpan(0, 0, 1, self.table.columnCount())
        titulo_item = QTableWidgetItem("Relaciones")
        # Fondo rojo claro y texto centrado
        titulo_item.setBackground(QColor(255, 128, 128))
        titulo_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(0, 0, titulo_item)

        # Encabezado vertical para la fila 0 => "Cant."
        self.table.setVerticalHeaderItem(0, QTableWidgetItem("Cant."))

        # ------------------------------------------------------------------
        # Rellenamos de la fila 1 hacia abajo
        # ------------------------------------------------------------------
        for i, rel in enumerate(relationships, start=1):
            tecneu_item = rel.get("tecneu_item", {})
            tecneu_item_id = tecneu_item.get("_id", "")
            quantity = rel.get("quantity", 0)
            title = tecneu_item.get("title", "Sin título")

            # Guardamos el _id para doble clic
            self._row_to_item_id[i] = tecneu_item_id

            # ~~~~~ Encabezado vertical con "X x" ~~~~~
            # Concatena " x" al valor
            self.table.setVerticalHeaderItem(i, QTableWidgetItem(f"{quantity} x"))

            # ~~~~~ Col 0 => Imagen ~~~~~
            label = QLabel()
            label.setFixedSize(100, 100)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    border: 1px solid white;  
                    background-color: transparent;
                }
            """)
            # Spinner
            spinner_path = "spinner.gif"
            if os.path.exists(spinner_path):
                spinner = QMovie(spinner_path)
                spinner.setScaledSize(QSize(60, 60))
                label.setMovie(spinner)
                spinner.start()
            else:
                spinner = None
                label.setText("Cargando...")

            self.table.setCellWidget(i, 0, label)

            # Descarga imagen
            pictures = tecneu_item.get("pictures", [])
            if pictures:
                image_url = pictures[0].get("url", "")
                if image_url:
                    self.download_image(image_url, label, spinner)

            # ~~~~~ Col 1 => Título ~~~~~
            title_item = QTableWidgetItem(title)
            title_item.setFlags(title_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 1, title_item)

            # ~~~~~ Col 2 => Variante (solo si has_variant) ~~~~~
            if has_variant:
                variant_text = ""
                variations = tecneu_item.get("variations", [])
                if variations:
                    attr_name = variations[0].get("attribute_name", "")
                    val_name = variations[0].get("value_name", "")
                    attr_name = capitalize_first(attr_name)
                    val_name = capitalize_first(val_name)
                    variant_text = f"{attr_name}: {val_name}".strip()

                variant_item = QTableWidgetItem(variant_text)
                variant_item.setFlags(variant_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, 2, variant_item)

        # ------------------------------------------------------------------
        # Ajustamos anchos según lo pedido
        # ------------------------------------------------------------------
        # - VerticalHeader => ancho 20px (ya fijado con setFixedWidth(20)).
        # - Col 0 => "Imagen" => 100 px fijos
        self.table.setColumnWidth(0, 100)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)

        # Para las columnas restantes, usaremos "Stretch" para ocupar el espacio sobrante.
        # Si hay "Variante":
        #    - "Título" => 70%
        #    - "Variante" => 30%
        # De lo contrario (2 columnas):
        #    - "Título" => 100%
        total_stretch = 1000  # una base para la relación

        if has_variant:
            # Col 1 => Título => ~70% del espacio
            # Col 2 => Variante => ~30%
            # Truco: Asignamos anchos iniciales proporcionales
            self.table.setColumnWidth(1, int(total_stretch * 0.7))
            self.table.setColumnWidth(2, int(total_stretch * 0.3))
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        else:
            # Solo 2 columnas: Imagen, Título => Título 100% del sobrante
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        # Ajustar altura de filas
        self.table.resizeRowsToContents()

    def clear_relationships(self):
        """Limpia la tabla y pixmaps."""
        self.table.setRowCount(0)
        # Si deseas limpiar self.original_images, hazlo aquí
        self.original_images.clear()

    # ------------------------------------------------------------------------
    # Copiar _id al hacer doble clic
    # ------------------------------------------------------------------------
    def handle_cell_double_clicked(self, row, column):
        """
        Doble clic en cualquier celda => copiar el _id de esa fila,
        mostrar mensaje flotante.
        """
        # Omitimos la fila 0 (que es "Relaciones")
        if row == 0:
            return

        item_id = self._row_to_item_id.get(row, "")
        if item_id:
            QApplication.clipboard().setText(item_id)
            print(f"Copiado _id={item_id} al portapapeles.")
            # Mostramos un mensaje flotante, por ejemplo:
            self.show_temporary_message(
                text=f"Copiado: {item_id}",
                bg_color="#222222",
                text_color="#FFFFFF",
                duration=2000,
                position_x="center",
                position_y="bottom"
            )
        # else:
        #     print("No se encontró _id para esa fila")

    def show_temporary_message(self, text, bg_color="#222", text_color="#fff",
                               duration=2000, position_x="center", position_y="top"):
        """
        Muestra un QLabel flotante y transparente sobre esta ventana,
        que se oculta automáticamente tras 'duration' ms.

        :param text: Texto a mostrar
        :param bg_color: color de fondo (hex)
        :param text_color: color de letra (hex)
        :param duration: tiempo en ms
        :param position_x: "center", "left", "right"
        :param position_y: "top", "bottom"
        """
        msg_label = QLabel(self)
        msg_label.setText(text)
        msg_label.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                padding: 6px 10px;
                border-radius: 4px;
            }}
        """)
        msg_label.adjustSize()

        # Calculamos posición
        parent_rect = self.rect()  # geom local
        label_w = msg_label.width()
        label_h = msg_label.height()

        # Eje X
        if position_x == "center":
            x = (parent_rect.width() - label_w) // 2
        elif position_x == "right":
            x = parent_rect.width() - label_w - 10
        else:
            # "left" por defecto
            x = 10

        # Eje Y
        if position_y == "bottom":
            y = parent_rect.height() - label_h - 10
        else:
            # "top" por defecto
            y = 10

        msg_label.move(x, y)
        msg_label.show()

        # Timer para autodestruir
        def _remove_label():
            msg_label.deleteLater()

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(duration)
        timer.timeout.connect(_remove_label)
        timer.start()

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
        if not pm:
            return

        pixmap_w, pixmap_h = pm.size().width(), pm.size().height()

        # Escalas
        scale_x = pixmap_w / label_w
        scale_y = pixmap_h / label_h

        pixmap_x = int(local_pos.x() * scale_x)
        pixmap_y = int(local_pos.y() * scale_y)

        # Centramos zoom en un rect 40x40
        zoom_x = max(0, min(pixmap_x - 20, pixmap_w - 40))
        zoom_y = max(0, min(pixmap_y - 20, pixmap_h - 40))

        self.hover_zoom_window.update_zoom(QPoint(zoom_x, zoom_y), scale_x, scale_y)

        # Dibuja cuadrícula (opcional), igual que en ImageCarousel
        if not hasattr(label, "_original_pixmap"):
            label._original_pixmap = pm.copy()

        pixmap_copy = label._original_pixmap.copy()
        painter = QPainter(pixmap_copy)
        pen = QPen(QColor(0, 0, 255, 255)) # Azul oscuro
        pen.setWidth(1)
        painter.setPen(pen)

        grid_size = 2
        for gx in range(zoom_x, zoom_x + 40, grid_size):
            for gy in range(zoom_y, zoom_y + 40, grid_size):
                painter.drawPoint(gx, gy)
        painter.end()

        label.setPixmap(pixmap_copy)
        label.update()

# ---------------------------------------------------------
# Función auxiliar para normalizar texto: primera letra mayúscula, resto minúscula
# ---------------------------------------------------------
def capitalize_first(text):
    if not text:
        return ""
    if len(text) == 1:
        return text.upper()
    # Primera letra mayúscula, resto minúsculas
    return text[0].upper() + text[1:].lower()
