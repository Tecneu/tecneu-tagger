import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def generate_key(password: str, salt: bytes) -> bytes:
    """
    Deriva una clave de 32 bytes usando PBKDF2HMAC a partir de una contraseña y una sal.
    """
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=default_backend())
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt_file(input_path: str, output_path: str, password: str):
    # Generar una sal fija o aleatoria. Si usas una sal aleatoria, deberás almacenarla junto al archivo.
    salt = os.urandom(16)  # Guarda la sal en los primeros 16 bytes del archivo encriptado.
    key = generate_key(password, salt)
    fernet = Fernet(key)

    with open(input_path, "rb") as f:
        data = f.read()

    encrypted = fernet.encrypt(data)
    with open(output_path, "wb") as f:
        # Almacenar la sal concatenada con el contenido encriptado.
        f.write(salt + encrypted)
    print(f"Archivo encriptado y guardado en {output_path}")
