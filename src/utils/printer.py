import json
import string
import unicodedata

import win32print

# printer.py
__all__ = ["list_printers_to_json", "normalize_zpl"]


@staticmethod
def is_thermal_printer(printer_name):
    """
    Verifica si una impresora es térmica basada en su controlador, procesador de impresión o nombre del puerto.
    """
    try:
        printer_handle = win32print.OpenPrinter(printer_name)
        printer_info = win32print.GetPrinter(printer_handle, 2)  # Nivel 2 tiene detalles del controlador
        driver_name = printer_info.get("pDriverName", "").lower()
        print_processor = printer_info.get("pPrintProcessor", "").lower()
        port_name = printer_info.get("pPortName", "").lower()

        win32print.ClosePrinter(printer_handle)
        # print(f"{printer_info}; {driver_name}; {print_processor}; {port_name}")
        # print("==================================================================\n");

        # Busca palabras clave comunes en el controlador, procesador o nombre del puerto
        if any(
            keyword in driver_name
            for keyword in [
                "zdesigner",
                "4barcode",
                "thermal",
                "pos",
                "zebra",
                "receipt",
                "label",
            ]
        ):
            return True
        if any(keyword in print_processor for keyword in ["thermal", "pos", "zebra"]):
            return True
        if any(keyword in port_name for keyword in ["lan_zdesigner", "zebra", "4barcode", "label"]):
            return True

        return False
    except Exception as e:
        print(f"Error al consultar la impresora {printer_name}: {e}")
        return False


def list_printers_to_json():
    """
    Función que lista las impresoras disponibles y devuelve una cadena JSON con los detalles.
    """
    # Enumerar las impresoras instaladas
    printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)

    # Lista para almacenar los detalles de cada impresora
    printer_list = []

    for printer in printers:
        printer_details = {
            "Name": printer[2],
            "PortName": printer[1],
            "PrinterStatus": None,  # Este campo puede ser agregado con más información específica
            "WorkOffline": None,  # Este campo depende de detalles adicionales
            "Local": None,  # Puedes determinar si es local usando banderas específicas
            "EnableBIDI": None,  # Este dato no está directamente accesible por win32print
            "IsThermal": None,  # Indicador de si es una impresora térmica
        }

        # Intentar obtener información adicional sobre la impresora
        try:
            printer_handle = win32print.OpenPrinter(printer[2])
            printer_info = win32print.GetPrinter(printer_handle, 2)

            printer_details.update(
                {
                    "PrinterStatus": printer_info.get("Status", "Unknown"),
                    "WorkOffline": bool(printer_info.get("Attributes", 0) & win32print.PRINTER_ATTRIBUTE_WORK_OFFLINE),
                    "Local": bool(printer_info.get("Attributes", 0) & win32print.PRINTER_ATTRIBUTE_LOCAL),
                    "EnableBIDI": bool(printer_info.get("Attributes", 0) & win32print.PRINTER_ATTRIBUTE_ENABLE_BIDI),
                    "IsThermal": is_thermal_printer(printer[2]),
                }
            )

            win32print.ClosePrinter(printer_handle)
        except Exception as e:
            # Si ocurre un error, registrar la información mínima disponible
            printer_details["Error"] = str(e)

        printer_list.append(printer_details)

    # Convertir la lista a formato JSON
    return json.dumps(printer_list, indent=4)


def normalize_zpl(zpl):
    """
    Normaliza los textos dentro del código ZPL reemplazando caracteres especiales y no ASCII.
    """
    # Primero, realicemos los reemplazos específicos antes de normalizar completamente
    replacements = {
        "®": "(R)",
        "©": "(C)",
        "™": "(TM)",
        "½": "1/2",
        "~": "-",
        # Añade más caracteres y sus sustitutos según necesario
    }
    for original, substitute in replacements.items():
        zpl = zpl.replace(original, substitute)

    # Permitir caracteres básicos de ASCII y algunos específicos como parte del ZPL y saltos de línea
    allowed_characters = set(string.ascii_letters + string.digits + " .,:;!?()[]{}@#%&-+/\\^_<>*~|aáàäeéëiíïoóöòuüúùAÁÀÄEÉËIÍÏOÓÖÒUÜÚÙ\n")
    # Sustituir cualquier caracter no permitido por '?'
    normalized_zpl = "".join(c if c in allowed_characters else "?" for c in zpl)

    # Normalización NFKD para separar letras de diacríticos (acentos)
    normalized_zpl = unicodedata.normalize("NFKD", normalized_zpl).encode("ASCII", "ignore").decode("ASCII")

    return normalized_zpl
