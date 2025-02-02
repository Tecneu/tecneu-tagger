# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.building.api import PYZ, EXE
from PyInstaller.building.build_main import Analysis

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
    datas=collect_data_files('assets', 'assets') + collect_data_files('env', 'env'),
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
