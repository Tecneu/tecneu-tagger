import subprocess
import json
import unicodedata
import string

# utils.py
__all__ = ['list_printers_to_json', 'normalize_zpl']


def list_printers_to_json():
    """
    Función que lista las impresoras disponibles y devuelve una cadena JSON con los detalles.
    """
    cmd = 'wmic printer get name, ExtendedPrinterStatus, PortName, Local, WorkOffline, PrinterStatus, DeviceID, EnableBIDI'
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)

    # Dividir el resultado en líneas
    lines = result.stdout.strip().split('\n')

    # La primera línea contiene los nombres de las columnas
    columns = [column.strip() for column in lines[0].split('  ') if column]

    # Lista para almacenar los diccionarios de cada impresora
    printers = []

    # Procesar cada impresora
    for line in lines[1:]:
        if not line.strip():  # Si la línea está vacía, continuar
            continue
        values = [value.strip() for value in line.split('  ') if value]
        # Asegurarse de que el número de valores no exceda el número de columnas
        values = values[:len(columns)]
        # Llenar con None si faltan valores
        while len(values) < len(columns):
            values.append(None)
        printer = {columns[i]: values[i] for i in range(len(columns))}
        printers.append(printer)

    # Convertir la lista en JSON
    return json.dumps(printers, indent=4)


def normalize_zpl(zpl):
    """
    Normaliza los textos dentro del código ZPL reemplazando caracteres especiales y no ASCII.
    """
    # Primero, realicemos los reemplazos específicos antes de normalizar completamente
    replacements = {
        '®': '(R)',
        '©': '(C)',
        '™': '(TM)',
        '½': '1/2',
        '~': '-'
        # Añade más caracteres y sus sustitutos según necesario
    }
    for original, substitute in replacements.items():
        zpl = zpl.replace(original, substitute)

    # Permitir caracteres básicos de ASCII y algunos específicos como parte del ZPL y saltos de línea
    allowed_characters = set(
        string.ascii_letters + string.digits + " .,:;!?()[]{}@#%&-+/\\^_<>*~|aáàäeéëiíïoóöòuüúùAÁÀÄEÉËIÍÏOÓÖÒUÜÚÙ\n")
    # Sustituir cualquier caracter no permitido por '?'
    normalized_zpl = ''.join(c if c in allowed_characters else '?' for c in zpl)

    # Normalización NFKD para separar letras de diacríticos (acentos)
    normalized_zpl = unicodedata.normalize('NFKD', normalized_zpl).encode('ASCII', 'ignore').decode('ASCII')

    return normalized_zpl
