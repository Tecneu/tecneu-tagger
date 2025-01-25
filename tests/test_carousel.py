from PyQt5.QtTest import QTest

from custom_widgets.image_carousel import ImageCarousel


def test_two_failures(qtbot):
    """
    Simula 2 imágenes con URL inválida. Verifica que tras
    3 reintentos (timeout 4s c/u) queden como 'Failed to load'.
    """
    carousel = ImageCarousel(None)
    qtbot.addWidget(carousel)

    # URLs intencionalmente inválidas o un servidor que no existe
    invalid_urls = [
        "http://127.0.0.1:9999/this_does_not_exist.jpg",
        "http://some.nonexistentdomain/fake_image.jpg",
    ]

    carousel.set_images(invalid_urls)
    carousel.show()

    # Esperamos el tiempo necesario para que se agoten los 3 reintentos:
    #   3 intentos * 4 seg c/u = 12 seg, agregamos un margen
    QTest.qWait(20000)  # 20 segundos de espera

    # Verificamos que los 2 QLabel terminen en "Failed to load"
    assert carousel.image_layout.count() == 2

    for i in range(carousel.image_layout.count()):
        item = carousel.image_layout.itemAt(i)
        label = item.widget()
        # Debe mostrar 'Failed to load' tras agotar reintentos
        assert label.text() == "Failed to load", f"Label {i} no terminó con 'Failed to load' tras repetidos fallos"


def test_three_failures(qtbot):
    """
    Simula 3 imágenes que fallan simultáneamente.
    Todas deben terminar en 'Failed to load'.
    """
    carousel = ImageCarousel(None)
    qtbot.addWidget(carousel)

    invalid_urls = [
        "http://localhost:12345/not_found1.jpg",
        "http://localhost:12345/not_found2.jpg",
        "http://localhost:12345/not_found3.jpg",
    ]

    carousel.set_images(invalid_urls)
    carousel.show()

    QTest.qWait(20000)  # Esperamos a que pasen reintentos y timeouts

    assert carousel.image_layout.count() == 3

    for i in range(carousel.image_layout.count()):
        item = carousel.image_layout.itemAt(i)
        label = item.widget()
        assert label.text() == "Failed to load", f"Label {i} no terminó con 'Failed to load' tras repetidos fallos"
