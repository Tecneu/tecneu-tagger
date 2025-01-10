import requests
from dotenv import load_dotenv
from os.path import join, dirname
import os
from requests.exceptions import RequestException, Timeout

from config import BASE_ENV_PATH
# from app_secrets import API_EMAIL, API_PASSWORD, API_BASE_URL

# dotenv_path = join(dirname(__file__), '.env.production')
load_dotenv(BASE_ENV_PATH / ".env.development")

API_EMAIL = os.getenv('API_EMAIL')
API_PASSWORD = os.getenv('API_PASSWORD')
API_BASE_URL = os.getenv('API_BASE_URL')


class HTTPInterceptor:
    def __init__(self):
        self.base_url = API_BASE_URL
        self.access_token = None
        self.max_retries = 3
        self.timeout = 2.5  # Timeout en segundos

    def login(self):
        # print(f"API_EMAIL: {API_EMAIL}")
        # print(f"API_PASSWORD: {API_PASSWORD}")
        # print(f"API_BASE_URL: {API_BASE_URL}")
        """Realiza login para obtener un nuevo access_token."""
        login_url = f"{self.base_url}/auth/login"
        try:
            response = requests.post(login_url, json={
                "email": API_EMAIL,
                "password": API_PASSWORD
            }, timeout=self.timeout)

            if response.status_code == 200:
                self.access_token = response.json().get("access_token")
                print("Login exitoso. Nuevo token obtenido.")
                # print(self.access_token)
                return True
            else:
                print(f"Error en login: {response.status_code} - {response.text}")
        except (RequestException, Timeout) as e:
            print(f"Error al realizar login: {e}")
        return False

    def request(self, method, endpoint, params=None, data=None):
        """Realiza una solicitud HTTP con manejo de errores e intentos de reintento."""
        url = f"{self.base_url}{endpoint}"
        retries = 0
        login_attempts = 0

        while retries < self.max_retries:
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }  # Actualiza el token en cada intento

            try:
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=data,
                    timeout=self.timeout
                )

                # print(f"""
                #     {method},
                #     {url},
                #     {headers},
                #     {params},
                #     {data},
                #     {self.timeout}""")
                # print(response)

                if response.status_code == 401:
                    # Intentar renovar token una vez
                    if login_attempts < 1:
                        print("Token expirado. Intentando renovar.")
                        if self.login():
                            login_attempts += 1
                            continue
                    print("Error: No se pudo renovar el token.")
                    break

                elif 400 <= response.status_code < 500 or response.status_code >= 500:
                    retries += 1
                    print(f"Error HTTP {response.status_code}: Reintentando ({retries}/{self.max_retries})")
                    continue

                # Respuesta exitosa
                return response

            except Timeout:
                retries += 1
                print(f"Timeout alcanzado: Reintentando ({retries}/{self.max_retries})")
            except RequestException as e:
                print(f"Error en la petición: {e}")
                break

        print(f"Error: La solicitud a {url} falló después de {self.max_retries} intentos.")
        return None
