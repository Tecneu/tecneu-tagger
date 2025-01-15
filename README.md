## 🚀 Configuración del Entorno

1. **Instala Pyenv**
    - Windows: `pip install pyenv-win`
      - Establecer las siguientes rutas en la variable de entorno Path, en la parte superior, para que asigne prioridad a las versiones de python de pyenv-win sobre cualquier otra previamente instalada en el equipo:
      ```bash
      C:\Users\%USERPROFILE%\.pyenv\pyenv-win\bin
      C:\Users\%USERPROFILE%\.pyenv\pyenv-win\shims
    - Linux/MacOS: Seguir instrucciones de https://github.com/pyenv/pyenv

2. **Configura Pyenv**
   - Instalar la version de Python especificada en el archivo Pipfile: `pyenv install 3.x.x`
   - Asignar version instalada de uso global en el equipo: `pyenv global 3.x.x` o de uso local `pyenv local 3.x.x`
   - Verificar correcta selección de version de python en el equipo:
   ```bash
   pyenv global
   python --version

3. **Pipenv**
   - Instalarlo globalmente (Si prefieres evitar problemas de permisos): `python -m pip install pipenv` o localmente: `pip install --user pipenv`.
   - Ejecuta el comando `pyenv rehash` para detectar tu nueva instalación de pipenv y crear un shim.
   - Verificar instalación: `pipenv --version`.
   - Activar el entorno virtual del proyecto: `pipenv shell`.
   - Instalar dependencias `pipenv install` o para uso en Producción (Entornos Estables) instala versiones exactas según Pipfile.lock`pipenv install --deploy --ignore-pipfile`.
   - Ejecutar main.py: `python src/main.py`.
   - Salir del entorno virtual: `exit`.
   
[//]: # (5. **Instala dependencias** )

[//]: # (   ```bash)

[//]: # (   pip install -r requirements.txt)

## Otros

1. **Intellij IDEA**
   - Configurar que IntelliJ cree y gestione un entorno Pipenv:
     - Abrir la configuración de estructura del proyecto (Ctrl + Alt + Shift + S).
     - En el menu 'SDK' Haz clic en Add Interpreter o 'Add SDK' → selecciona Pipenv Environment (panel izquierdo).
     - En Base interpreter, elige: 
     ```bash
     C:\Users\%USERPROFILE%\.pyenv\pyenv-win\versions\3.x.x\python.exe
     ```
     - En Pipenv executable, puedes dejarlo en blanco si tu PATH incluye la carpeta “shims” o “Scripts” de pyenv, o puedes buscar el pipenv.exe correspondiente, algo como:
     ```bash
     C:\Users\%USERPROFILE%\.pyenv\pyenv-win\versions\3.x.x\Scripts\pipenv.exe
     ```
     ![img.png](img.png)
   - Seleccionar Content Root (Directorio raíz del proyecto:
   ![img_1.png](img_1.png)

2. **Actualizar dependencias necesarias para el proyecto**
   ```bash
   pip freeze > requirements.txt
   
3. **Regenera el lock (opcional si cambias a un Pipfile)**
   - Tras editar el Pipfile, ejecuta `pipenv lock`.
   - Luego vuelve a instalar: `pipenv install`
   
4. **Crear ejecutable**
    - Con instrucciones de .spec (Recomendable): `pyinstaller main.spec`
    - Ejecutable inline con icono: `pyinstaller --onefile --windowed --icon=assets/logos/tecneu-logo.ico main.spec`
