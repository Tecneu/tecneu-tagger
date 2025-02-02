# config.py
import base64
import ctypes
import ctypes.wintypes
import logging
import os
import sys
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv


# --- Configuración de logging centralizada ---
def get_documents_folder():
    """
    Obtiene la ruta del directorio "Mis Documentos" de Windows de forma dinámica,
    utilizando la API de Windows. Si ocurre algún error, se utiliza como respaldo
    la carpeta "Documents" en el directorio home del usuario.
    """
    try:
        CSIDL_PERSONAL = 5  # Identificador para "Mis Documentos"
        SHGFP_TYPE_CURRENT = 0  # Valor actual, no el predeterminado
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
        return buf.value
    except Exception as e:
        # En caso de error, se usa el directorio "Documents" del home (podría no ser exacto en sistemas localizados)
        return os.path.join(Path.home(), "Documents")


# Obtener la carpeta Documents de forma dinámica
documents_folder = get_documents_folder()
# Construir la ruta para los logs dentro de Documents
log_dir = os.path.join(documents_folder, "LogTTagger")

# Si el directorio no existe, lo creamos
if not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir)
        print(f"Directorio creado: {log_dir}")
    except Exception as e:
        print(f"Error al crear el directorio {log_dir}: {e}")

# Definir la ruta completa del archivo de log
log_path = os.path.join(log_dir, "app.log")

# Configurar logging solo si aún no se han definido manejadores (para evitar reconfiguraciones)
if not logging.getLogger().hasHandlers():
    logging.basicConfig(
        level=logging.DEBUG,
        filename=log_path,
        filemode="a",  # Modo append para seguir registrando sin sobrescribir
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

# --- Fin de la configuración de logging ---


def generate_key(password: str, salt: bytes) -> bytes:
    """
    Deriva una clave de 32 bytes a partir de la contraseña y la sal usando PBKDF2HMAC.
    """
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=default_backend())
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def decrypt_env_file(enc_path: str, password: str) -> str:
    """
    Desencripta el archivo encriptado que contiene el .env y devuelve su contenido como string.
    Se asume que los primeros 16 bytes del archivo son la sal.
    """
    with open(enc_path, "rb") as f:
        data = f.read()
    salt = data[:16]
    encrypted = data[16:]
    key = generate_key(password, salt)
    fernet = Fernet(key)
    decrypted = fernet.decrypt(encrypted)
    return decrypted.decode("utf-8")


# Ejemplo: desencriptar el archivo .env.production.enc
# Define la contraseña utilizada para encriptar.
ENV_PASSWORD = "O6^A=G9mY0"

# Valor máximo para el delay slider
MAX_DELAY = 50

if getattr(sys, "frozen", False):
    # Estamos en un ejecutable PyInstaller => producción
    # Si es así, usa la ruta de _MEIPASS
    BASE_ASSETS_PATH = Path(sys._MEIPASS) / "assets"
    BASE_ENV_PATH = Path(sys._MEIPASS) / "env"
    ENV_FILE = BASE_ENV_PATH / ".env.production.enc"

    try:
        decrypted_content = decrypt_env_file(str(ENV_FILE), ENV_PASSWORD)
        # Escribir el contenido desencriptado en un archivo temporal.
        temp_env_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp")
        temp_env_file.write(decrypted_content)
        temp_env_file.close()
        env_to_load = Path(temp_env_file.name)
        logging.debug(f"Archivo .env desencriptado temporal: {env_to_load}")
        load_dotenv(env_to_load)
    except Exception as e:
        logging.error(f"Error al desencriptar el archivo .env: {e}")
else:
    # Estamos corriendo como script normal => desarrollo
    # De lo contrario, usa la ruta relativa desde el archivo de script
    BASE_ASSETS_PATH = Path(__file__).resolve().parent.parent / "assets"
    BASE_ENV_PATH = Path(__file__).resolve().parent.parent / "env"
    ENV_FILE = BASE_ENV_PATH / ".env.development"
    load_dotenv(ENV_FILE)

logging.debug(f"BASE_ASSETS_PATH: {BASE_ASSETS_PATH}")
logging.debug(f"ENV_FILE: {ENV_FILE}")

if getattr(sys, "frozen", False):
    logging.debug("Ambiente: Producción (encriptado)")
else:
    logging.debug("Ambiente: Desarrollo (sin encriptar)")

# Ahora ya puedes leer variables de entorno en todo tu proyecto
API_EMAIL = os.getenv("API_EMAIL", "")
API_PASSWORD = os.getenv("API_PASSWORD", "")
API_BASE_URL = os.getenv("API_BASE_URL", "")

LABEL_SIZES = [
    {"title": "38x25mm", "value": "4_x_2_5"},
    {"title": "76x51mm", "value": "8_x_5"},
    {"title": '4x6"', "value": "6_x_4"},
    {"title": "5x2.5cm", "value": "5_x_2_5"},
]

__all__ = ["MAX_DELAY", "BASE_ASSETS_PATH", "BASE_ENV_PATH", "LABEL_SIZES", "API_EMAIL", "API_PASSWORD", "API_BASE_URL", "ENV"]
