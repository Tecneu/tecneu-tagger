import os

from PyQt5.QtCore import QRectF, QSize, Qt, QTimer, QUrl
from PyQt5.QtGui import QBrush, QColor, QMovie, QPainter, QPalette, QPen, QPixmap
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt5.QtWidgets import QAbstractItemView, QApplication, QHBoxLayout, QHeaderView, QLabel, QTableWidgetItem, QVBoxLayout, QWidget

from config import BASE_ASSETS_PATH
from custom_widgets.hover_zoom_window import HoverZoomWindow
from utils import show_temporary_message

from .custom_widgets import CustomTableWidget

__all__ = ["ItemRelationshipsWindow"]


class ItemRelationshipsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Parámetros personalizables
        self.THUMB_SIZE = 60  # Tamaño máximo de miniatura (ancho o alto)
        self.ZOOM_REGION = 40  # Tamaño (en px de la miniatura) del rect mostrado en el thumb
        self.ZOOM_WINDOW_SIZE = 390  # Tamaño de la ventana de zoom (ancho x alto)

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
                background-color: #0487D9;
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
        self.table = CustomTableWidget()
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
        self.table.setShowGrid(False)
        self.table.setStyleSheet(
            """
            QTableWidget::item {
                border: 4px solid gray;
                padding: 4px;
            }
            QTableView::item {
                border: 1px solid gray;
            }
            QTableView {
                gridline-color: transparent; /* o background-color: transparent; */
            }
            QTableWidget {
                background-color: transparent;
                color: white;
                /* gridline-color: gray; */
                border: none;
                selection-background-color: rgba(0, 0, 255, 80); /* Azul translúcido */
                selection-color: white;
                font-size: 11pt;
                padding: 0px;
                margin 0px;
            }
            /* Encabezados horizontales */
            QHeaderView::section {
                background-color: rgba(0, 0, 0, 0);  /* transparente */
                background-color: transparent; /* No sirven fondos transparentes aquí */
                /* background-color: gray; */
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
        """
        )

        # Ocultamos el encabezado vertical, ya que usaremos la 1ra columna como "Cant."
        self.table.verticalHeader().setVisible(False)
        # Ocultamos la cabecera horizontal por defecto mientras no definimos columnas
        # (la mostraremos al setear las columnas).
        #  - No es estrictamente necesario ocultarla aquí,
        #    pero lo hacemos para limpiar si no hay datos.
        self.table.horizontalHeader().setVisible(False)

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

        # Conectamos la señal de doble clic
        self.table.cellDoubleClicked.connect(self.handle_cell_double_clicked)

        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        # Ajustar el 'step' del scroll
        scrollbar = self.table.verticalScrollBar()
        scrollbar.setSingleStep(5)  # píxeles por 'paso' de rueda
        scrollbar.setPageStep(20)  # al pulsar area vacía en scrollbar

        # para horizontal, si procede
        scrollbar_h = self.table.horizontalScrollBar()
        scrollbar_h.setSingleStep(5)
        scrollbar_h.setPageStep(20)

        self.click_sound_player = QMediaPlayer()
        self.click_sound_player.setMedia(QMediaContent(QUrl.fromLocalFile(os.fspath(BASE_ASSETS_PATH / "sounds" / "click.mp3"))))

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
            opacity=0.80,
        )
        # Después de ajustar geometry, recalculamos anchos
        self._adjust_table_columns(parent_geometry.width())

    # ------------------------------------------------------------------
    # Ajustar columnas según ancho del parent
    # ------------------------------------------------------------------
    def _adjust_table_columns(self, parent_width):
        """
        Basado en el ancho del parent, repartimos:
         - col 0 => 70 px (Cant.)
         - col 1 => 70 px (Imagen)
         - col 2 => (restante * 0.7) si hay variante, o (restante * 1.0) si no
         - col 3 => (restante * 0.3) si hay variante
        """
        if self.table.columnCount() < 3:
            return  # Significa que no se han cargado datos

        # Primero, marcamos las 2 primeras columnas como fijas
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(1, 70)

        # Ancho restante para Título/Variante
        variant_additional_width = 16 if self._has_variant else 0
        used_width = 70 + 70 + 24 + variant_additional_width  # Cant., Imagen y padding
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
         - Col 0 → "Cant."
         - Col 1 → "Imagen"
         - Col 2 ⇾ "Título" + Bins
         - Col 3 ⇾ "Variante" (solo si alguna relación tiene variations)
        También actualiza el label superior con la cuenta de relaciones y la suma de cantidades.
        """
        self.clear_relationships()
        self._row_to_item_id.clear()

        if not relationships:
            return

        # Calculamos cuántos hay y suma de cantidades
        num_relations = len(relationships)
        total_qty = sum(rel.get("quantity", 0) for rel in relationships)

        if num_relations == 0:
            return

        # Texto con 2 puntos más grande y en negritas los números
        # Ejemplo: Relaciones: <b style='font-size:12pt'>3</b> | <b style='font-size:12pt'>20</b> Unidades │|║
        self.title_label.setText(
            f"<b style='font-size:16pt'>{num_relations}</b>"
            f" {'Producto/Relación' if num_relations == 1 else 'Productos/Relaciones'}   ║   "
            f"<b style='font-size:16pt'>{total_qty}</b> {'Unidad' if total_qty == 1 else 'Unidades'}"
        )

        self.table.horizontalHeader().setVisible(True)

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

            # QLabel con HTML parcial
            html_label = QLabel()
            html_label.setTextFormat(Qt.RichText)
            html_label.setAlignment(Qt.AlignCenter)
            html_label.setText(f"<b style='font-size:16pt'>{qty}</b> u.")

            # Ajustar estilo
            html_label.setStyleSheet(
                """
                QLabel {
                    background-color: transparent;
                    color: white;
                }
            """
            )

            self.table.setCellWidget(row_idx, 0, html_label)

            # 2) Col 1 => Imagen (QLabel con descarga asíncrona)
            label = QLabel()
            label.setFixedSize(self.THUMB_SIZE, self.THUMB_SIZE)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(
                """
                QLabel {
                    border: 1px solid white;
                    background-color: white;
                }
            """
            )
            image_container = QWidget()
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)  # sin margen
            layout.setSpacing(0)
            layout.addWidget(label, alignment=Qt.AlignCenter)
            image_container.setLayout(layout)
            spinner_path = os.fspath(BASE_ASSETS_PATH / "icons" / "spinner.gif")  # Ajusta la ruta
            if os.path.exists(spinner_path):
                spinner = QMovie(spinner_path)
                spinner.setScaledSize(QSize(int(self.THUMB_SIZE * 0.6), int(self.THUMB_SIZE * 0.6)))
                label.setMovie(spinner)
                spinner.start()
            else:
                spinner = None
                label.setText("Cargando...")

            self.table.setCellWidget(row_idx, 1, image_container)

            # Descargamos la imagen
            pictures = tecneu_item.get("pictures", [])
            if pictures:
                image_url = pictures[0].get("url", "")
                if image_url:
                    self.download_image(image_url, label, spinner)

            # 3) Col 2 => Título + Bins
            title_label = QLabel()
            title_label.setWordWrap(True)
            title_label.setTextFormat(Qt.RichText)
            title_label.setStyleSheet("background-color: transparent; color: white;")
            title_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            # Extraer los bins (contenedores)
            warehouse_bins = tecneu_item.get("tecneu_warehouse_bins", [])
            bins_list = []
            for b in warehouse_bins:
                formatted_bin = b.get("formatted_bin", "")
                if formatted_bin:
                    bins_list.append(str(formatted_bin))

            # Si existen bins, se construye el texto combinando título y bins;
            # se utiliza la función _format_bins_text para limitar la visualización a dos renglones.
            if bins_list:
                cell_width = self.table.columnWidth(2)
                print(f"cell_width ====> {cell_width}")
                if cell_width <= 0:
                    cell_width = 200  # valor por defecto si no se ha asignado ancho
                fm = title_label.fontMetrics()
                max_height = fm.lineSpacing() * 8  # permitimos 8 bins maximo
                truncated_bins = self._format_bins_text(bins_list, cell_width, fm, max_height)
                cell_text = (
                    f"<div>"
                    f"  <div style='font-size:14pt; font-weight:bold;'>{title}</div>"
                    f"  <div style='font-size:10pt; color: #BFBFBF'>{truncated_bins}</div>"
                    f"</div>"
                )
            else:
                cell_text = f"<div style='font-size:14pt; font-weight:bold;'>{title}</div>"

            title_label.setText(cell_text)
            self.table.setCellWidget(row_idx, 2, title_label)

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

        # Luego forzamos min 70, max 90
        for i in range(self.table.rowCount()):
            row_height = self.table.rowHeight(i)
            if row_height < 70:
                self.table.setRowHeight(i, 70)
            elif row_height > 90:
                self.table.setRowHeight(i, 90)

    # ------------------------------------------------------------------------
    # Función auxiliar para formatear (y truncar) el texto de los bins.
    # Se muestra la lista de bins separados por comas; si la cadena completa
    # excede el alto permitido (dos líneas), se van agregando uno a uno y,
    # al exceder el límite, se agrega "..." al final.
    # ------------------------------------------------------------------------
    def _format_bins_text(self, bins_list, cell_width, fm, max_height):
        full_text = ", ".join(bins_list)
        rect = fm.boundingRect(0, 0, cell_width, 10000, Qt.TextWordWrap, full_text)
        if rect.height() <= max_height:
            return full_text
        current_bins = []
        for b in bins_list:
            candidate = ", ".join(current_bins + [b])
            candidate_with_ellipsis = candidate + "..."
            rect_candidate = fm.boundingRect(0, 0, cell_width, 10000, Qt.TextWordWrap, candidate_with_ellipsis)
            if rect_candidate.height() <= max_height:
                current_bins.append(b)
            else:
                break
        truncated = ", ".join(current_bins)
        if len(current_bins) < len(bins_list):
            truncated += "..."
        return truncated

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
            self.click_sound_player.play()
            QApplication.clipboard().setText(item_id)
            # Mostramos un mensaje flotante, por ejemplo:
            show_temporary_message(
                parent=self, text=f"Copiado: {item_id}", bg_color="#222222", text_color="#FFFFFF", duration=2000, position_x="center", position_y="bottom"
            )

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
    # Lógica de Zoom (muy parecida a la del carrusel)
    # ------------------------------------------------------------------------
    def configure_label_for_zoom(self, label, img_url):
        """Configura el hover y el mouseMove si quieres zoom."""
        label.setMouseTracking(True)
        label.enterEvent = lambda event, lbl=label: self.show_zoom_window(event, lbl, img_url)
        label.leaveEvent = lambda event, lbl=label: self.clear_grid_and_hide_zoom(lbl)
        label.mouseMoveEvent = lambda event, lbl=label: self.update_zoom_position(event, lbl, img_url)

    def show_zoom_window(self, event, label, img_url):
        if self.hover_zoom_window is not None:
            self.hover_zoom_window.close()

        if img_url in self.original_images:
            original_pixmap = self.original_images[img_url]
            # Reusar tu HoverZoomWindow si deseas
            # self.hover_zoom_window = HoverZoomWindow(pixmap, self.parent())
            self.hover_zoom_window = HoverZoomWindow(original_pixmap, self.ZOOM_WINDOW_SIZE, parent=self.parent())
            self.hover_zoom_window.show()
            # Actualiza la posición inicial de zoom
            self.update_zoom_position(event, label, img_url)
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

    def update_zoom_position(self, event, label, img_url):
        """Actualiza el recorte de zoom basándose en la posición del mouse."""
        if not self.hover_zoom_window:
            return

        # Tamaño del pixmap escalado en el label (la miniatura)
        if not label.pixmap():
            return

        scaled_pix = label.pixmap()
        scaled_w = scaled_pix.width()
        scaled_h = scaled_pix.height()

        # Tamaño real del label (e.g. 100x100)
        label_w = label.width()
        label_h = label.height()

        # Offset por centrado (si la imagen no llena todo el QLabel)
        offset_x = (label_w - scaled_w) // 2
        offset_y = (label_h - scaled_h) // 2

        # Posición del mouse dentro del QLabel
        local_pos = event.pos()

        # Coordenadas dentro del área visible de la miniatura
        x_in_scaled = local_pos.x() - offset_x
        y_in_scaled = local_pos.y() - offset_y

        # Clampeamos para no salir del pixmap escalado
        x_in_scaled = max(0, min(x_in_scaled, scaled_w))
        y_in_scaled = max(0, min(y_in_scaled, scaled_h))

        # Ahora interpretamos ZOOM_REGION como tamaño en la miniatura
        region_size_thumb = self.ZOOM_REGION

        min_w = min(region_size_thumb, scaled_w)
        min_h = min(region_size_thumb, scaled_h)

        # Queremos centrar la región en (x_in_scaled, y_in_scaled)
        left_thumb = x_in_scaled - region_size_thumb / 2
        top_thumb = y_in_scaled - region_size_thumb / 2

        # Clampeamos para que la región no se salga de la miniatura
        if left_thumb < 0:
            left_thumb = 0
        if top_thumb < 0:
            top_thumb = 0
        if left_thumb + region_size_thumb > scaled_w:
            left_thumb = scaled_w - min_w
        if top_thumb + region_size_thumb > scaled_h:
            top_thumb = scaled_h - min_h

        # Dibujar rectángulo + cuadrícula en la miniatura
        if not hasattr(label, "_original_pixmap"):
            label._original_pixmap = scaled_pix.copy()

        temp_pix = label._original_pixmap.copy()
        painter = QPainter(temp_pix)
        painter.setRenderHint(QPainter.Antialiasing)

        # -- Rectángulo azul (semitransparente) --
        pen_rect = QPen(QColor(0, 0, 255, 128))  # Azul semitransparente
        pen_rect.setWidth(1)
        painter.setPen(pen_rect)
        painter.drawRect(QRectF(left_thumb, top_thumb, min_w, min_h))

        # -- Cuadrícula de puntos azules más claros --
        pen_grid = QPen(QColor(0, 0, 255, 60))  # Azul más claro
        pen_grid.setWidth(1)
        painter.setPen(pen_grid)

        grid_size = 2
        for gx in range(int(left_thumb), int(left_thumb + min_w), grid_size):
            for gy in range(int(top_thumb), int(top_thumb + min_h), grid_size):
                painter.drawPoint(gx, gy)

        painter.end()

        label.setPixmap(temp_pix)
        label.update()

        # ---- Calcular la región correspondiente en la imagen original ----
        # Relación de escala (original -> miniatura)
        original_pixmap = self.original_images[img_url]
        orig_w = original_pixmap.width()
        orig_h = original_pixmap.height()

        scale_x = orig_w / scaled_w
        scale_y = orig_h / scaled_h

        # Mapeo de la región en la miniatura a la región en la imagen original
        left_orig = left_thumb * scale_x
        top_orig = top_thumb * scale_y
        width_orig = region_size_thumb * scale_x
        height_orig = region_size_thumb * scale_y

        # Pasamos el QRect a la ventana flotante
        rect_in_original = QRectF(left_orig, top_orig, width_orig, height_orig)
        self.hover_zoom_window.update_zoom_rect(rect_in_original)

    def clear_focus_in_table(self):
        """
        Quita el foco y la selección de la tabla
        (o de cualquier otro widget que quieras).
        """
        self.table.clearSelection()
        self.table.clearFocus()


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
