from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QLabel


def show_temporary_message(parent, text, bg_color="#222", text_color="#fff", duration=2000, position_x="center", position_y="top"):
    """
    Muestra un QLabel flotante sobre 'parent' durante 'duration' ms.

    :param text: Texto a mostrar
    :param bg_color: color de fondo (hex)
    :param text_color: color de letra (hex)
    :param duration: tiempo en ms
    :param position_x: "center", "left", "right"
    :param position_y: "top", "bottom"
    """
    msg_label = QLabel(parent)
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
    parent_rect = parent.rect()  # geom local
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

    timer = QTimer(parent)
    timer.setSingleShot(True)
    timer.setInterval(duration)
    timer.timeout.connect(_remove_label)
    timer.start()
