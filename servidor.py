from fastapi import FastAPI
from fastapi.responses import FileResponse
import os
import uvicorn

# 1. Inicialización de la aplicación
app = FastAPI(
    title="SinFiltro Web App", 
    description="Servidor para el proyecto de videos e imágenes."
)

# 2. Definición de la Ruta Raíz ("/")
@app.get("/", response_class=FileResponse)
async def serve_pagina_web():
    """
    Sirve el archivo 'sinfiltro.html' cuando se accede a la URL principal.
    """
    # Verificamos que el archivo HTML exista en el directorio raíz (donde está servidor.py)
    html_file = "sinfiltro.html"
    if os.path.exists(html_file):
        return html_file
    else:
        # En caso de que falte el HTML, devolvemos una respuesta de error legible
        return {"error": "El archivo HTML principal no fue encontrado en el servidor.", "buscando": html_file}


# 3. Punto de entrada para Gunicorn/Uvicorn (opcional, pero buena práctica)
# Gunicorn o Uvicorn usarán la variable 'app' para ejecutar el servicio en Render.
if __name__ == "__main__":
    # Este bloque solo se usa para pruebas locales, no afecta el despliegue en Render
    uvicorn.run("servidor:app", host="0.0.0.0", port=8000, reload=True)
