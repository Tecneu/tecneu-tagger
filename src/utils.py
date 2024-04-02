import subprocess
import json

# utils.py
__all__ = ['list_printers_to_json']


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
