# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# Agrega la carpeta 'src' al sys.path
sys.path.insert(0, os.path.abspath('src'))

from PyInstaller.building.api import PYZ, EXE
from PyInstaller.building.build_main import Analysis

from config import BASE_ENV_PATH

# --- Paso de encriptación previo al Analysis ---

# Define la contraseña a usar para la encriptación/desencriptación
ENV_PASSWORD = "O6^A=G9mY0"

# Directorio base: asume que el spec se encuentra en el directorio raíz del proyecto
# base_dir = os.path.dirname(os.path.abspath(__file__))

# Construir las rutas de entrada y salida para el archivo .env.production
input_env_file = os.fspath(BASE_ENV_PATH / ".env.production")
output_env_file = os.fspath(BASE_ENV_PATH / ".env.production.enc")

# Si ya existe un archivo encriptado previo, lo eliminamos
if os.path.exists(output_env_file):
    os.remove(output_env_file)
    print(f"El archivo encriptado previo '{output_env_file}' ha sido eliminado.")

# Verificar que el archivo de entrada exista
if not os.path.exists(input_env_file):
    print(f"El archivo de entrada '{input_env_file}' no existe. Verifica que el archivo .env.production esté presente.")
    sys.exit(1)

# Importar la función de encriptación desde encrypt_env.py
from encrypt_env import encrypt_file

# Encriptar el archivo .env.production y generar .env.production.enc
encrypt_file(input_env_file, output_env_file, ENV_PASSWORD)

# --- Fin del paso de encriptación ---

block_cipher = None

def collect_data_files(source_dir, dest_folder):
    """
    Recorre recursivamente source_dir y retorna una lista de tuplas (ruta_origen, ruta_destino)
    donde los archivos se ubicarán dentro de dest_folder en el paquete final.
    """
    paths = []
    for (path, directories, filenames) in os.walk(source_dir):
        for filename in filenames:
            filepath = os.path.join(path, filename)
            # Calculamos la ruta relativa del archivo con respecto al directorio fuente
            parent_directory = os.path.relpath(path, source_dir)
            # Definimos la ruta destino dentro del paquete, conservando la estructura
            destination_path = os.path.join(dest_folder, parent_directory)
            paths.append((filepath, destination_path))
    return paths

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    # Se recopilan tanto los archivos de "assets" como los de "env"
    datas=collect_data_files('assets', 'assets') + [('env/.env.production.enc', 'env')],
    hiddenimports=['src.utils', 'src.config'],
    hookspath=['./hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\logos\\tecneu-logo.ico'],
)
