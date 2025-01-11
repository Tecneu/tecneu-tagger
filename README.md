## 🚀 Configuración del Entorno

1. **Instala Pyenv**
    - Windows: `pip install pyenv-win`
    - Linux/MacOS: Seguir instrucciones de https://github.com/pyenv/pyenv

2. **Instala la versión de Python del proyecto**
   ```bash
   pyenv install
   pyenv local
   
3. **Instala dependencias** 
   ```bash
   pip install -r requirements.txt

## Otros

1. **Actualizar dependencias necesarias para el proyecto**
   ```bash
   pip freeze > requirements.txt
   
2. **Crear ejecutable**
    - Con instrucciones de .spec (Recomendable): `pyinstaller main.spec`
    - Ejecutable inline con icono: `pyinstaller --onefile --windowed --icon=assets/logos/tecneu-logo.ico main.spec`

3. **Instalar pipenv de manera global en PC**
   ```bash
   python -m pip install pipenv
   
4. **Agregar al PATH de las variables de entorno**
    - La ruta al ejecutable de Pipenv "C:\Users\%USERPROFILE%\AppData\Roaming\Python\Python310\Scripts"
    - La ruta a la version de Python "C:\Users\%USERPROFILE%\AppData\Local\Programs\Python\Python310"