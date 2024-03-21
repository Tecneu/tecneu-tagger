import subprocess


def listar_impresoras_zebra():
    # cmd = 'wmic printer get name, portname, status'
    cmd = 'wmic printer get name, status, ExtendedPrinterStatus, Network, PortName, PNPDeviceID, Local, Location, WorkOffline, PrinterStatus, DeviceID, EnableBIDI'
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)

    lines = result.stdout.strip().split('\n')
    print(lines)
    # impresoras_zebra = [line.strip() for line in lines if 'Zebra' in line]

    # for impresora in lines:
    #     parts = impresora.split()
    #     name = parts[0]
    #     port = parts[-2]  # Suponiendo que el puerto siempre precede al estado
    #     status = parts[-1]
    #     print(f"Nombre: {name}, Puerto: {port}, Estado: {status}")


listar_impresoras_zebra()
