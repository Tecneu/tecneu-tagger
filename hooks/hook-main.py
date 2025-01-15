from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules("src.utils") + collect_submodules("src.config")

# Asume que tienes archivos o recursos adicionales en un directorio específico que también necesitas incluir.
# Si tienes múltiples directorios, puedes llamar a `collect_data_files` con diferentes rutas y sumar las listas.
datas = collect_data_files("src/assets")  # Ajusta el directorio según dónde guardés archivos como imágenes, etc.

# Si necesitas asegurarte de que ciertos archivos binarios también sean incluidos, puedes agregarlos manualmente.
# Ejemplo: binaries = [(r'path_to_binary', 'destination_directory')]
binaries = []
