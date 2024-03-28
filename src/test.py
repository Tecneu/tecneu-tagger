import subprocess
import json

def listar_impresoras_a_json():
    cmd = 'wmic printer get name, ExtendedPrinterStatus, PortName, Local, WorkOffline, PrinterStatus, DeviceID, EnableBIDI'
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)

    # Dividir el resultado en líneas
    lineas = result.stdout.strip().split('\n')

    # La primera línea contiene los nombres de las columnas
    columnas = [columna.strip() for columna in lineas[0].split('  ') if columna]

    # Lista para almacenar los diccionarios de cada impresora
    impresoras = []

    # Procesar cada impresora
    for linea in lineas[1:]:
        if not linea.strip():  # Si la línea está vacía, continuar
            continue
        valores = [valor.strip() for valor in linea.split('  ') if valor]
        impresora = {columnas[i]: valores[i] for i in range(len(valores))}
        impresoras.append(impresora)

    # Convertir la lista en JSON
    return json.dumps(impresoras, indent=4)
    # print(json_impresoras)

print(listar_impresoras_a_json())