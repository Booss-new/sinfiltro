from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import random
import time

# ========================================================================
# 1. Configuración de la Aplicación FastAPI
# ========================================================================

app = FastAPI(
    title="SinFiltro Web App", 
    description="Servidor para la aplicación móvil de videos e imágenes."
)

# Permitir CORS (crucial para que el frontend pueda llamar al backend en Render)
# Ya que el frontend está en la misma URL, técnicamente no es necesario, pero
# es buena práctica para evitar problemas de desarrollo.
app.add_middleware(
    CORSMiddleware,
    # El origen debe coincidir con la URL de tu Render
    allow_origins=["https://sinfiltro-fbb8.onrender.com", "http://localhost:8000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================================================================
# 2. Ruta Raíz ("/") para Servir el HTML
# ========================================================================

@app.get("/", response_class=FileResponse)
async def serve_pagina_web():
    """
    Sirve el archivo 'sinfiltro.html' cuando se accede a la URL principal.
    """
    html_file = "sinfiltro.html"
    
    if os.path.exists(html_file):
        return html_file
    else:
        return JSONResponse(
            status_code=500,
            content={"error": "Archivo HTML no encontrado", "mensaje": "Asegúrate de que sinfiltro.html está en el directorio raíz."}
        )

# ========================================================================
# 3. Rutas de API (Mocks para que tu JS funcione)
# ========================================================================

# Pool de datos de demostración
MOCK_POOL = []
for i in range(50):
    MOCK_POOL.append({
        'id': f'item-{i}', 
        'src': f'https://picsum.photos/640/420?random={i+1000}', 
        'kind': 'video' if i % 6 == 0 else 'image',
        'title': ['Retrato Urbano', 'Callejón Neon', 'Sunset Vibes', 'Arte Moderno'][i % 4] + f' #{i}',
        'likes': random.randint(100, 1000), 
        'comments': random.randint(5, 150), 
        'views': f'{random.randint(1, 9)}.K'
    })


@app.get("/api/content/feed/{type}")
async def get_feed_content(type: str):
    """
    Simula la carga de contenido para las secciones.
    """
    # Mezclamos y devolvemos una porción del pool
    random.shuffle(MOCK_POOL)
    
    # Simulamos el tiempo de carga para sentirnos como un servidor real
    time.sleep(0.5) 

    return {
        "success": True, 
        "data": MOCK_POOL[:random.randint(15, 30)],
        "message": f"Contenido simulado para {type} cargado."
    }

@app.post("/api/content/upload")
async def upload_content(file: UploadFile = File(...), title: str = Form("Contenido Sin Título")):
    """
    Simula el endpoint de subida de archivos que usa tu JavaScript.
    
    Recibe el archivo y el título. Simula el procesamiento y devuelve el nuevo item.
    """
    
    # 1. Simular guardar o procesar el archivo
    # (En un entorno real, aquí se guardaría en S3/Blob Storage)
    file_type = file.content_type.split('/')[0] # 'image' o 'video'
    
    # 2. Simular un tiempo de procesamiento para que el modal de progreso se vea
    time.sleep(2) 
    
    # 3. Crear el nuevo ítem con datos simulados
    new_item = {
        'id': f'new-{random.randint(100, 999)}',
        'src': f'https://picsum.photos/640/420?random={random.randint(10000, 99999)}',
        'kind': file_type, 
        'title': title if title else f'Subido: {file.filename}',
        'likes': 0,
        'comments': 0,
        'views': '0'
    }

    # 4. Devolver respuesta de éxito
    return {
        "success": True, 
        "item": new_item, 
        "message": f"Archivo '{file.filename}' procesado y guardado correctamente."
    }

# ========================================================================
# 4. Bloque de Ejecución (Punto de entrada para Gunicorn)
# ========================================================================

if __name__ == "__main__":
    uvicorn.run("servidor:app", host="0.0.0.0", port=8000, reload=True)
