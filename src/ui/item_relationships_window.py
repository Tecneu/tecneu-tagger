from PyQt5.QtCore import Qt, QUrl, QTimer, QPoint, QSize
from PyQt5.QtGui import QPalette, QColor, QPixmap, QMovie, QPainter, QPen, QBrush, QFont
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QTableWidgetItem, QHBoxLayout, QLabel, QHeaderView, QApplication, QSizePolicy
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

import os
from config import BASE_ASSETS_PATH

from .custom_widgets import HoverZoomWindow

# spinner_path = os.fspath(BASE_ASSETS_PATH / "icons" / "spinner.gif")  # Ajusta la ruta

__all__ = ["ItemRelationshipsWindow"]


class ItemRelationshipsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Estado de visibilidad
        self._is_visible = False

        # Guardar si hay variante o no, para luego saber si asignar 70/30 o 100%.
        self._has_variant = False

        # Semi-transparencia en la paleta
        palette = self.palette()
        color = QColor(255, 255, 255, 51)  # 20% de opacidad
        palette.setColor(QPalette.Window, color)
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        # Layout principal
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # --------------------------------------------------
        # 1) Label que muestra "Relaciones: X | Y Unidades" arriba del encabezado
        # --------------------------------------------------
        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignCenter)
        # Fondo rojo claro y texto blanco
        self.title_label.setStyleSheet(
            """
            QLabel {
                background-color: rgb(255, 128, 128);
                color: white;
                font-weight: normal;  /* texto normal, usaremos HTML para negritas */
                padding: 5px;
            }
        """
        )
        self.main_layout.addWidget(self.title_label)

        # --------------------------------------------------
        # 2) QTableWidget para las relaciones (inicialmente 0 filas/0 columnas)
        # --------------------------------------------------
        self.table = QTableWidget()
        self.main_layout.addWidget(self.table)

        # Altura fija inicial (puedes ajustarla si lo deseas)
        self.setFixedHeight(250)

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
        # - Sin fondo
        # - Texto y bordes blancos
        # - Al seleccionar: azul translúcido
        # - Encabezado horizontal también transparente
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                color: white;
                gridline-color: white;
                selection-background-color: rgba(0, 0, 255, 80); /* Azul translúcido */
                selection-color: white;
                font-size: 11pt;
            }
            /* Encabezados horizontales */
            QHeaderView::section {
                background-color: rgba(0, 0, 0, 0);  /* transparente */
                background-color: transparent; /* No sirven fondos transparentes aquí */
                background-color: gray;
                color: black;
                border: 1px solid white;
                font-weight: bold;
                font-size: 12pt;
            }
            /* Esquina superior izquierda (cuando hay encabezado vertical) */
            QTableCornerButton::section {
                background-color: rgba(0, 0, 0, 0);
                border: 1px solid white;
            }
        """)

        # Ocultamos el encabezado vertical, ya que usaremos la 1ra columna como "Cant."
        self.table.verticalHeader().setVisible(False)
        # Ocultamos la cabecera horizontal por defecto mientras no definimos columnas
        # (la mostraremos al setear las columnas).
        #  - No es estrictamente necesario ocultarla aquí,
        #    pero lo hacemos para limpiar si no hay datos.
        # self.table.horizontalHeader().setVisible(False)

        # Hacer celdas read-only pero copiables:
        #   - QAbstractItemView::NoEditTriggers evita edición con doble clic
        #   - El usuario aún puede seleccionar y copiar
        self.table.setEditTriggers(self.table.NoEditTriggers)
        self.table.setSelectionBehavior(self.table.SelectItems)
        self.table.setSelectionMode(self.table.SingleSelection)

        # Ajustar altura del header horizontal
        self.table.horizontalHeader().setFixedHeight(30)

        # En lugar de la selección quedándose al perder foco, quitamos la selección.
        self.table.setFocusPolicy(Qt.StrongFocus)
        # Sobrescribimos el focusOutEvent para limpiar la selección:
        self.table.focusOutEvent = self._handle_table_focus_out

        # # Columnas expandibles
        # self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Conectamos la señal de doble clic
        self.table.cellDoubleClicked.connect(self.handle_cell_double_clicked)

    # ------------------------------------------------------------------
    #  Sobrescribir el evento de pérdida de foco
    # ------------------------------------------------------------------
    def _handle_table_focus_out(self, event):
        """Al perder el foco, quitamos la selección para que regrese a fondo transparente."""
        self.table.clearSelection()
        super(self.table.__class__, self.table).focusOutEvent(event)

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
        # Después de ajustar geometry, recalculamos anchos
        self._adjust_table_columns(parent_geometry.width())

    # ------------------------------------------------------------------
    # Ajustar columnas según ancho del parent
    # ------------------------------------------------------------------
    def _adjust_table_columns(self, parent_width):
        """
        Basado en el ancho del parent, repartimos:
         - col 0 => 65 px (Cant.)
         - col 1 => 100 px (Imagen)
         - col 2 => (restante * 0.7) si hay variante, o (restante * 1.0) si no
         - col 3 => (restante * 0.3) si hay variante
        """
        if self.table.columnCount() < 3:
            return  # Significa que no se han cargado datos

        # Primero, marcamos las 2 primeras columnas como fijas
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 65)
        self.table.setColumnWidth(1, 100)

        # Ancho restante para Título/Variante
        used_width = 65 + 100
        remaining_width = max(parent_width - used_width, 50)  # Evitar negativos

        if self._has_variant and self.table.columnCount() == 4:
            # col 2 => 70%, col 3 => 30%
            col2_width = int(remaining_width * 0.7)
            col3_width = int(remaining_width * 0.3)

            self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
            self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)

            self.table.setColumnWidth(2, max(col2_width, 50))
            self.table.setColumnWidth(3, max(col3_width, 50))

        else:
            # col 2 => 100% (stretch o fixed)
            self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
            self.table.setColumnWidth(2, remaining_width)

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
        Muestra las relaciones en la tabla:
         - Col 0 => "Cant."
         - Col 1 => "Imagen"
         - Col 2 => "Título"
         - Col 3 => "Variante" (sólo si alguna relación tiene variations)
        También actualiza el label superior con la cuenta de relaciones y la suma de cantidades.
        """
        self.clear_relationships()
        self._row_to_item_id.clear()

        if not relationships:
            return

        # Calculamos cuántos hay y suma de cantidades
        num_relations = len(relationships)
        total_qty = sum(rel.get("quantity", 0) for rel in relationships)

        # Texto con 2 puntos más grande y en negritas los números
        # Ejemplo: Relaciones: <b style='font-size:12pt'>3</b> | <b style='font-size:12pt'>20</b> Unidades
        self.title_label.setText(
            f"<b style='font-size:13pt'>{num_relations}</b>"
            f" {'Relación' if num_relations == 1 else 'Relaciones'} | "
            f"<b style='font-size:13pt'>{total_qty}</b> Unidades"
        )

        if num_relations == 0:
            return

        # ¿Hay alguna relación que tenga variant?
        self._has_variant = any(rel.get("tecneu_item", {}).get("variations") for rel in relationships)

        # Definimos las columnas:
        #  - 3 columnas si no hay variante: [Cant., Imagen, Título]
        #  - 4 columnas si sí hay variante: [Cant., Imagen, Título, Variante]
        if self._has_variant:
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(["Cant.", "Imagen", "Título", "Variante"])
        else:
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["Cant.", "Imagen", "Título"])

        # Tantas filas como relaciones
        self.table.setRowCount(num_relations)

        # Rellenamos fila por fila
        for row_idx, rel in enumerate(relationships):
            tecneu_item = rel.get("tecneu_item", {})
            _id = tecneu_item.get("_id", "")
            qty = rel.get("quantity", 0)
            title = tecneu_item.get("title", "Sin título")
            # Guardamos _id para doble clic
            self._row_to_item_id[row_idx] = _id

            # 1) QTableWidgetItem para copiar
            plain_text = f"{qty} u."
            copy_item = QTableWidgetItem(plain_text)
            copy_item.setFlags(copy_item.flags() & ~Qt.ItemIsEditable)
            # Establecer el color del texto a transparente
            copy_item.setForeground(QBrush(QColor(0, 0, 0, 0)))  # RGB (0,0,0) con alpha=0 (transparente)
            # copy_item.setBackground(QBrush(QColor(0, 0, 0, 0)))  # Opcional: fondo transparente
            self.table.setItem(row_idx, 0, copy_item)

            # 2) QLabel con HTML parcial
            html_label = QLabel()
            # html_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Permitir expansión
            # html_label.setContentsMargins(0, 0, 0, 0)  # Sin márgenes
            # html_label.setGeometry(0, 0, self.table.columnWidth(0), self.table.rowHeight(row_idx))
            html_label.setTextFormat(Qt.RichText)
            html_label.setAlignment(Qt.AlignCenter)
            html_label.setText(f"<b style='font-size:14pt'>{qty}</b> u.")

            # Ajustar estilo
            html_label.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    color: white;
                }
            """)

            self.table.setCellWidget(row_idx, 0, html_label)

            # 2) Col 1 => Imagen (QLabel con descarga asíncrona)
            label = QLabel()
            label.setFixedSize(100, 100)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    border: 1px solid white;
                    background-color: transparent;
                }
            """)
            spinner_path = os.fspath(BASE_ASSETS_PATH / "icons" / "spinner.gif")  # Ajusta la ruta
            if os.path.exists(spinner_path):
                spinner = QMovie(spinner_path)
                spinner.setScaledSize(QSize(60, 60))
                label.setMovie(spinner)
                spinner.start()
            else:
                spinner = None
                label.setText("Cargando...")

            self.table.setCellWidget(row_idx, 1, label)

            # Descargamos la imagen
            pictures = tecneu_item.get("pictures", [])
            if pictures:
                image_url = pictures[0].get("url", "")
                if image_url:
                    self.download_image(image_url, label, spinner)

            # 3) Col 2 => Título
            title_item = QTableWidgetItem(title)
            title_item.setFlags(title_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row_idx, 2, title_item)

            # 4) Col 3 => Variante (sólo si self._has_variant)
            if self._has_variant:
                variant_text = ""
                variations = tecneu_item.get("variations", [])
                if variations:
                    attr_name = variations[0].get("attribute_name", "")
                    val_name = variations[0].get("value_name", "")
                    attr_name = capitalize_first(attr_name)
                    val_name = capitalize_first(val_name)
                    variant_text = f"{attr_name}: {val_name}"

                var_item = QTableWidgetItem(variant_text)
                var_item.setFlags(var_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_idx, 3, var_item)

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
        item_id = self._row_to_item_id.get(row, "")
        if item_id:
            QApplication.clipboard().setText(item_id)
            print(f"Copiado _id={item_id} al portapapeles.")
            # Mostramos un mensaje flotante, por ejemplo:
            self.show_temporary_message(
                text=f"Copiado: {item_id}", bg_color="#222222", text_color="#FFFFFF", duration=2000, position_x="center", position_y="bottom"
            )
        # else:
        #     print("No se encontró _id para esa fila")

    def show_temporary_message(self, text, bg_color="#222", text_color="#fff", duration=2000, position_x="center", position_y="top"):
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
        msg_label.setStyleSheet(
            f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                padding: 6px 10px;
                border-radius: 4px;
            }}
        """
        )
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
                scaled = pixmap.scaled(label.width(), label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
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
            print(f"[ItemRelationships] Reintento {url} (attempt={attempt + 1})")
            self.download_image(url, label, spinner, attempt + 1, max_attempts)
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
        pen = QPen(QColor(0, 0, 255, 255))  # Azul oscuro
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
