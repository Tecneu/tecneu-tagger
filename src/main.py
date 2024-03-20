import tkinter as tk
from tkinter import simpledialog
from zebra import Zebra
import time
import threading

# Define la función de impresión
def print_labels(copies, delay):
    global pause
    pause = False

    label = """
^XA
^CI28
^LH0,0
^FO75,18^BY2^BCN,54,N,N^FDSMBG62283^FS  // Ajustado de ^FO89,18 a ^FO105,18 para añadir 2mm más
^FT160,98^A0N,22,22^FH^FDSMBG62283^FS   // Ajustado de ^FT174,98 a ^FT190,98
^FT159,98^A0N,22,22^FH^FDSMBG62283^FS   // Ajustado de ^FT173,98 a ^FT189,98
^FO62,115^A0N,18,18^FB332,2,0,L^FH^FD120 Cables Jumpers Dupont H_2Dh_2C M_2Dm_2C H_2Dm 10cm Para Protoboard^FS  // Ajustado de ^FO46,115 a ^FO62,115 y reducido el ancho para compensar
^FO62,150^A0N,18,18^FB332,1,0,L^FH^FDMixto (40 C/U)^FS  // Ajustado de ^FO46,150 a ^FO62,150 y reducido el ancho para compensar
^FO61,150^A0N,18,18^FB332,1,0,L^FH^FDMixto (40 C/U)^FS  // Ajustado de ^FO45,150 a ^FO61,150 y reducido el ancho para compensar
^FO62,170^A0N,18,18^FH^FDCod. Universal: 788194520596^FS  // Ajustado de ^FO46,170 a ^FO62,170
^FO62,170^A0N,18,18^FH^FD^FS  // Ajustado de ^FO46,170 a ^FO62,170
^PQ1,0,1,Y^XZ
"""

    printer_name = 'ZD410'
    z = Zebra(printer_name)

    for _ in range(copies):
        # Verificar si se ha pausado la impresión
        while pause:
            time.sleep(1)

        z.output(label)
        print("Etiqueta enviada a la impresora.")
        time.sleep(delay)

# Función para manejar el inicio de la impresión
def start_printing():
    copies = int(copies_entry.get())
    delay = int(delay_entry.get())
    threading.Thread(target=print_labels, args=(copies, delay)).start()

# Función para pausar/reanudar la impresión
def toggle_pause(event):
    global pause
    pause = not pause

# Configuración de la ventana Tkinter
root = tk.Tk()
root.title("Tecneu - Tagger")

# Establecer un icono
root.iconbitmap('../assets/logos/tecneu-logo.ico')

# Establecer un tamaño mínimo de ventana
root.minsize(400, 200)

# Configuración de la entrada para el número de copias
tk.Label(root, text="Número de copias:").pack()
copies_entry = tk.Entry(root)
copies_entry.pack()

# Configuración de la entrada para el retraso
tk.Label(root, text="Retraso entre copias (segundos):").pack()
delay_entry = tk.Entry(root)
delay_entry.pack()

# Botón de inicio
start_button = tk.Button(root, text="Iniciar Impresión", command=start_printing)
start_button.pack()

# Configurar el evento de la tecla espacio para pausar/reanudar
root.bind('<space>', toggle_pause)

# Iniciar la interfaz de usuario
root.mainloop()
