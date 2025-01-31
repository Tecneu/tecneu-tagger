def show_message_overlay(
    self,
    message,
    center_all_windows=False,
    parent=None,
    bg_color="rgba(0, 0, 0, 125)",
    text_color="#FFFFFF",
    font_size=24,
    width=400,
    height=200,
    duration=3000,
    is_html=False,
):
    """
    Muestra un recuadro de 'width x height' con fondo 'bg_color' y un texto grande centrado.
    Por defecto se centra en la ventana principal, pero si 'center_all_windows=True',
    unirá la geometría de self.carousel y self.relationships_window para abarcar toda el área visible.

    :param message: Texto a mostrar (puede ser HTML si is_html=True).
    :param center_all_windows: Si True, calcula un bounding rect que incluye
                               self, self.carousel y self.relationships_window (si están visibles).
                               Si False, usa solo 'parent' o la main_window como referencia.
    :param parent: Si no es None, se usará esa geometría como referencia para el centrado.
                   Si es None y center_all_windows=False, se usará la geometría de la ventana principal (self).
    :param bg_color: Color de fondo (puede ser RGBA "rgba(0,0,0,125)" o "#000000" con alpha).
    :param text_color: Color del texto.
    :param font_size: Tamaño de letra (puntos).
    :param width: Ancho del recuadro (en px).
    :param height: Alto del recuadro (en px).
    :param duration: Tiempo en ms que se mostrará; 0 o negativo => se muestra indefinidamente.
    :param is_html: Si True, 'message' se interpretará como HTML. Caso contrario, texto plano.
    """

    # 1) Calcular el rectángulo donde vamos a centrar
    from PyQt5.QtCore import QRect, QTimer
    from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout

    if center_all_windows:
        # Tomamos la geometría de la ventana principal
        bounding_rect = self.geometry()
        # Si hay carousel visible, unimos su geometría
        if hasattr(self, "carousel") and self.carousel.is_visible:
            bounding_rect = bounding_rect.united(self.carousel.geometry())
        # Si hay relationships_window visible, unimos su geometría
        if hasattr(self, "relationships_window") and self.relationships_window.is_visible:
            bounding_rect = bounding_rect.united(self.relationships_window.geometry())
    else:
        # Si no centramos en todo, usamos parent o, en su defecto, la main_window
        if parent is not None:
            bounding_rect = parent.geometry()
        else:
            # Por defecto: la geometría de la ventana principal (self)
            bounding_rect = self.geometry()

    # 2) Creamos el QFrame que contendrá el mensaje
    #    Usamos None como parent para que sea una ventana flotante independiente
    #    (Pero si quieres forzar que sea hijo de self, usa self en lugar de None).
    overlay_frame = QFrame(None)
    overlay_frame.setObjectName("GiantMessageOverlay")
    overlay_frame.setStyleSheet(f"QFrame#GiantMessageOverlay {{ background-color: {bg_color}; }}")

    # 3) Ajustar flags: sin bordes, encima de todo
    from PyQt5.QtCore import Qt

    overlay_frame.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)  # para que no aparezca en la barra de tareas

    # 4) Ajustar tamaño
    overlay_frame.setFixedSize(width, height)

    # 5) Calcular posición para centrarlo en bounding_rect
    center_x = bounding_rect.center().x() - (width // 2)
    center_y = bounding_rect.center().y() - (height // 2)
    overlay_frame.move(center_x, center_y)

    # 6) Layout interno para el texto
    layout = QVBoxLayout(overlay_frame)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.setAlignment(Qt.AlignCenter)

    label = QLabel()
    label.setAlignment(Qt.AlignCenter)

    if is_html:
        # Insertar color y tamaño de fuente via HTML inline, si lo deseas
        html_formatted = f"<span style='color:{text_color}; font-size:{font_size}pt;'>{message}</span>"
        label.setText(html_formatted)
        label.setStyleSheet("background-color: transparent;")
    else:
        # Texto plano: definimos color y tamaño con QSS
        label.setText(message)
        label.setStyleSheet(f"background-color: transparent; color: {text_color}; font-size: {font_size}pt;")

    layout.addWidget(label, alignment=Qt.AlignCenter)

    # 7) Mostrar
    overlay_frame.show()
    overlay_frame.raise_()

    # 8) Si duration > 0 => ocultarlo automáticamente
    if duration > 0:

        def _close_overlay():
            if overlay_frame is not None:
                overlay_frame.close()

        QTimer.singleShot(duration, _close_overlay)
