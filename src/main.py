# import tkinter as tk
# from tkinter import simpledialog
# from zebra import Zebra
# import time
# import threading
#
# # Define la función de impresión
# def print_labels(copies, delay):
#     global pause
#     pause = False
#
#     label = """
# ^XA
# ^CI28
# ^LH0,0
# ^FO75,18^BY2^BCN,54,N,N^FDSMBG62283^FS  // Ajustado de ^FO89,18 a ^FO105,18 para añadir 2mm más
# ^FT160,98^A0N,22,22^FH^FDSMBG62283^FS   // Ajustado de ^FT174,98 a ^FT190,98
# ^FT159,98^A0N,22,22^FH^FDSMBG62283^FS   // Ajustado de ^FT173,98 a ^FT189,98
# ^FO62,115^A0N,18,18^FB332,2,0,L^FH^FD120 Cables Jumpers Dupont H_2Dh_2C M_2Dm_2C H_2Dm 10cm Para Protoboard^FS  // Ajustado de ^FO46,115 a ^FO62,115 y reducido el ancho para compensar
# ^FO62,150^A0N,18,18^FB332,1,0,L^FH^FDMixto (40 C/U)^FS  // Ajustado de ^FO46,150 a ^FO62,150 y reducido el ancho para compensar
# ^FO61,150^A0N,18,18^FB332,1,0,L^FH^FDMixto (40 C/U)^FS  // Ajustado de ^FO45,150 a ^FO61,150 y reducido el ancho para compensar
# ^FO62,170^A0N,18,18^FH^FDCod. Universal: 788194520596^FS  // Ajustado de ^FO46,170 a ^FO62,170
# ^FO62,170^A0N,18,18^FH^FD^FS  // Ajustado de ^FO46,170 a ^FO62,170
# ^PQ1,0,1,Y^XZ
# """
#
#     printer_name = 'ZD410'
#     z = Zebra(printer_name)
#
#     for _ in range(copies):
#         # Verificar si se ha pausado la impresión
#         while pause:
#             time.sleep(1)
#
#         z.output(label)
#         print("Etiqueta enviada a la impresora.")
#         time.sleep(delay)
#
# # Función para manejar el inicio de la impresión
# def start_printing():
#     copies = int(copies_entry.get())
#     delay = int(delay_entry.get())
#     threading.Thread(target=print_labels, args=(copies, delay)).start()
#
# # Función para pausar/reanudar la impresión
# def toggle_pause(event):
#     global pause
#     pause = not pause
#
# # Configuración de la ventana Tkinter
# root = tk.Tk()
# root.title("Tecneu - Tagger")
#
# # Establecer un icono
# root.iconbitmap('../assets/logos/tecneu-logo.ico')
#
# # Establecer un tamaño mínimo de ventana
# root.minsize(400, 200)
#
# # Configuración de la entrada para el número de copias
# tk.Label(root, text="Número de copias:").pack()
# copies_entry = tk.Entry(root)
# copies_entry.pack()
#
# # Configuración de la entrada para el retraso
# tk.Label(root, text="Retraso entre copias (segundos):").pack()
# delay_entry = tk.Entry(root)
# delay_entry.pack()
#
# # Botón de inicio
# start_button = tk.Button(root, text="Iniciar Impresión", command=start_printing)
# start_button.pack()
#
# # Configurar el evento de la tecla espacio para pausar/reanudar
# root.bind('<space>', toggle_pause)
#
# # Iniciar la interfaz de usuario
# root.mainloop()

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import re
import subprocess
from zebra import Zebra

# Variable para controlar si se está imprimiendo
printing = False


class PlaceholderEntry(ttk.Entry):
    """Una clase de Entry que soporta placeholders."""

    def __init__(self, master=None, placeholder="PLACEHOLDER", color='grey', **kw):
        super().__init__(master, **kw)

        self.placeholder = placeholder
        self.placeholder_color = color
        self.default_fg_color = self['foreground']

        self.bind("<FocusIn>", self._clear_placeholder)
        self.bind("<FocusOut>", self._add_placeholder)

        self._add_placeholder()

    def _clear_placeholder(self, e):
        if self['foreground'] == self.placeholder_color:
            self.delete(0, "end")
            self['foreground'] = self.default_fg_color

    def _add_placeholder(self, e=None):
        if not self.get():
            self.insert(0, self.placeholder)
            self['foreground'] = self.placeholder_color


def validate_float(text):
    """Valida si el texto es un float válido con hasta dos decimales."""
    if re.match("^[0-9]*\.?[0-9]{0,2}$", text) or text == "":
        return True
    else:
        return False


def validate_int(text):
    """Valida si el texto es un int válido con hasta 3 digitos."""
    if re.match("^[0-9]{0,3}$", text) or text == "":
        return True
    else:
        return False


def on_validate_delay(P):
    """Validación del retraso."""
    return validate_float(P)


def on_validate_copies(P):
    """Validación del número de copias."""
    return validate_int(P)


# Función de impresión con Zebra (simplificada)
def print_labels(copies, delay):
    global pause
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
    z.setqueue(printer_name)

    global printing
    for i in range(copies):
        if pause:
            while pause:
                continue  # Simplemente espera aquí si está pausado
        z.output(label)
        print("Etiqueta enviada a la impresora.")
        copies_left_var.set(f"Etiquetas restantes: {copies - i - 1}")
        if copies - i - 1 > 0:
            time.sleep(delay)
        else:
            printing = False
            start_button['state'] = 'enable'  # Desactivar botón de inicio


# Función para manejar el inicio de la impresión
def start_printing():
    global printing
    if printing:
        messagebox.showwarning("Advertencia", "Ya hay un proceso de impresión en curso.")
        return
    try:
        copies = int(copies_entry.get())
        delay = float(delay_entry.get())
        if copies > 0 and delay >= 0:
            printing = True
            start_button['state'] = 'disabled'  # Desactivar botón de inicio
            threading.Thread(target=print_labels, args=(copies, delay), daemon=True).start()
        else:
            messagebox.showerror("Error de validación", "Por favor, ingresa valores válidos.")
    except ValueError:
        messagebox.showerror("Error de validación", "Por favor, ingresa valores válidos.")


# Función para pausar/reanudar la impresión y actualizar el botón
def toggle_pause():
    global pause
    pause = not pause
    pause_button.config(text="Reanudar" if pause else "Pausar")


# Configuración de la ventana Tkinter y tema oscuro
root = tk.Tk()
root.title("Tecneu - Tagger")
style = ttk.Style(root)
style.theme_use('clam')  # Usando 'clam' como base para el tema oscuro

# Establecer un icono
root.iconbitmap('../assets/logos/tecneu-logo.ico')

# Establecer un tamaño mínimo de ventana
root.minsize(400, 200)

# Colores para el tema oscuro
style.configure('TButton', background='#333333', foreground='white', borderwidth=1)
style.configure('TLabel', background='#333333', foreground='white')
style.configure('TEntry', background='#555555', foreground='white')

root.configure(bg='#333333')  # Fondo de la ventana principal

# Inicialización de variables globales
pause = False
copies_left_var = tk.StringVar(value="Etiquetas restantes: 0")

# Configuración de la entrada para el número de copias y su validación
# ttk.Label(root, text="Número de copias:").pack(pady=(10, 0))
# copies_entry = ttk.Entry(root)
# copies_entry.pack(pady=(0, 10))
vcmd_int = (root.register(on_validate_copies), '%P')
copies_entry = PlaceholderEntry(root, "Número de copias", 'grey', validate='key', validatecommand=vcmd_int)
copies_entry.pack(pady=(0, 10))

# Configuración de la entrada para el retraso y su validación
# ttk.Label(root, text="Retraso entre copias (segundos):").pack(pady=(10, 0))
# delay_entry = ttk.Entry(root)
# delay_entry.pack(pady=(0, 10))
vcmd_float = (root.register(on_validate_delay), '%P')
delay_entry = PlaceholderEntry(root, placeholder="Retraso entre copias", color='grey', validate="key",
                               validatecommand=vcmd_float)
delay_entry.pack(pady=(0, 10))

# Botón de inicio
start_button = ttk.Button(root, text="Iniciar Impresión", command=start_printing)
start_button.pack(pady=(0, 10))

# Botón de pausa/reanudar
pause_button = ttk.Button(root, text="Pausar", command=toggle_pause)
pause_button.pack(pady=(0, 10))

# Configurar el evento de la tecla espacio para pausar/reanudar
root.bind('<space>', toggle_pause)

# Etiqueta para mostrar las etiquetas restantes por imprimir
label_counter = ttk.Label(root, textvariable=copies_left_var)
label_counter.pack(pady=(10, 0))

# Iniciar la interfaz de usuario
root.mainloop()
