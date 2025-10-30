import os
from pathlib import Path

from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException, responses
from fastapi.staticfiles import StaticFiles

# --- CONFIGURACIÓN DE RUTAS ---
# Directorio donde se encuentra este script (backend/)
BASE_DIR = Path(__file__).resolve().parent

# Directorio Raíz de tu proyecto (un nivel arriba de backend/)
# Asumimos que el HTML principal está aquí (sinfiltro.html)
ROOT_DIR = BASE_DIR.parent 

# Directorio para archivos subidos (ej: /uploads)
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True) 

# --- FASTAPI APP ---
# Se define sin root_path="/api" para que coincida con la corrección en el HTML.
APP = FastAPI(title="sinfiltra-api")

# --- SERVIR ARCHIVOS ESTÁTICOS ---
# Montar el directorio donde está el HTML y otros archivos estáticos (JS, CSS, etc.)
# Esto sirve archivos como 'sinfiltro.html' si está en la raíz del proyecto.
# Si tienes otros archivos estáticos fuera de la carpeta 'backend', úsalo.
APP.mount("/static", StaticFiles(directory=ROOT_DIR), name="static")

# Montar el directorio de subidas
APP.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# --- ENDPOINT PRINCIPAL (SIRVE EL HTML) ---
# Este endpoint responde a la URL principal (la raíz)
@APP.get("/", response_class=responses.HTMLResponse)
async def serve_frontend():
    """Sirve el archivo HTML principal (frontend)."""
    
    # Asume que tu archivo HTML principal se llama 'sinfiltro.html'
    html_path = ROOT_DIR / "sinfiltro.html" 
    
    if not html_path.exists():
        # Si el archivo no existe en la raíz, busca una alternativa (si aplica)
        raise HTTPException(status_code=404, detail="Error 404: No se encontró el archivo 'sinfiltro.html'.")
        
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    return responses.HTMLResponse(content=html_content)


# --- ENDPOINTS DE API ---
# Nota: Ahora deben ir SIN el prefijo /api, ya que la conexión del HTML fue corregida.

@APP.post("/content/upload")
async def upload_content(file: UploadFile = File(...), title: str = Form(...)):
    """Maneja la subida de archivos."""
    
    # **Tu lógica existente de subida de archivos va aquí**
    # Ejemplo de guardado:
    file_location = UPLOAD_DIR / file.filename
    with open(file_location, "wb") as f:
        f.write(file.file.read())
        
    return {"success": True, "message": "Archivo subido correctamente."}

@APP.get("/content/feed/{type}")
async def get_feed(type: str, limit: int = 10):
    """Devuelve el feed de contenido (ej: 'feed', 'reco', 'explore')."""
    # **Tu lógica para obtener el feed va aquí**
    
    # Simulación de respuesta para evitar error 404 al arrancar:
    return {"data": [
        {"id": 1, "title": "Video de Prueba", "url": "/uploads/test.mp4", "kind": "video", "views": 100, "likes": 5, "is_liked": False},
        {"id": 2, "title": "Imagen de Prueba", "url": "/uploads/test.jpg", "kind": "image", "views": 50, "likes": 10, "is_liked": True}
    ]}

@APP.post("/content/{id}/like")
async def update_like(id: int, kind: dict):
    """Actualiza el estado de 'Me Gusta'."""
    # **Tu lógica de likes va aquí**
    return {"success": True, "message": f"Like/Dislike actualizado para {id}"}

# **Asegúrate de copiar todos tus otros endpoints de la API aquí, sin el prefijo /api.**
