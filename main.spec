# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

def collect_data_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            filepath = os.path.join(path, filename)
            parent_directory = os.path.relpath(path, directory)
            destination_path = os.path.join('assets', parent_directory)
            paths.append((filepath, destination_path))
    return paths

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=collect_data_files('assets'),  # Modificado para incluir recursivamente todos los archivos
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
