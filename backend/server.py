from fastapi import FastAPI, APIRouter, UploadFile, File, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Union
import uuid
import os
import shutil
from pathlib import Path

# Imports para manejo de modelos y datos
from pydantic import BaseModel
from datetime import datetime, timezone
import random
import time

# --- Configuración y Conexión ---

# Variables de entorno para la URI de MongoDB
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
DB_NAME = os.environ.get('DB_NAME', 'mi_base_de_datos')
CLIENT = AsyncIOMotorClient(MONGO_URL)
DB = CLIENT[DB_NAME]

# Directorio de subidas
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Inicialización de FastAPI
app = FastAPI(title="Mi API", prefix="/api")
router = APIRouter(prefix="/api")

# --- Modelos Pydantic ---

class StatusCheck(BaseModel):
    status: str = Field(..., description="Estado de la aplicación/servicio.")
    db_check: bool = Field(False, description="Estado de la conexión a la DB.")
    client_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckResponse(BaseModel):
    timestamp: datetime
    status_check: StatusCheck

class ContentItemBaseModel(BaseModel):
    id: str
    title: str
    url: str
    kind: str = Field("image", description="Tipo de contenido: 'image' o 'video'")
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    views: int = 0
    likes: int = 0
    is_liked: bool = False
    parent: Optional[str] = None
    tags: Optional[List[str]] = None

class ContentItem(ContentItemBaseModel):
    # Modelo completo para guardar en la base de datos
    pass

class ItemLikeRequest(BaseModel):
    kind: str # 'like' o 'dislike'
    
# --- Endpoints de Status y Salud ---

# Raíz
@app.get("/")
def read_root():
    return {"message": "Sinfiltro API Ready"}

# Estado (Health Check)
@router.get("/status", response_model=StatusCheckResponse)
async def check_status():
    status_check = StatusCheck()
    try:
        # Intenta obtener el estado del servidor de MongoDB (ping)
        await CLIENT.admin.command('ping')
        status_check.db_check = True
    except Exception as e:
        print(f"Error de DB: {e}")
        status_check.db_check = False
        status_check.status = "Error en DB"
    else:
        status_check.status = "OK"

    doc = StatusCheckResponse(
        timestamp=datetime.now(timezone.utc),
        status_check=status_check
    )
    return doc.dict(by_alias=True)

# Listado de estados (simulado)
@router.get("/status/history", response_model=List[StatusCheckResponse])
async def get_status_history(timestamp: Optional[int] = None, limit: int = 10):
    collection_name = 'status_checks'
    
    # Simulación de obtener datos de la colección
    # Aquí iría la lógica real de consulta a la DB
    if timestamp:
        # Filtro por timestamp
        pass 
    
    # Devuelve una lista simulada de StatusCheckResponse
    return [
        StatusCheckResponse(
            timestamp=datetime.now(timezone.utc).timestamp() - (i * 60), # Ejemplo con marcas de tiempo decrecientes
            status_check=StatusCheck(status="OK", db_check=True)
        )
        for i in range(limit)
    ]

# --- Endpoints de Contenido ---

# Obtener feed de contenido
@router.get("/content/feed/{content_type}")
async def get_feed(content_type: str, limit: int = 50):
    collection_name = f'content_{content_type}'
    
    # Lógica de consulta a la DB
    try:
        # Ejemplo: obtener los últimos 'limit' items ordenados por fecha
        items = await DB[collection_name].find().sort('_id', -1).to_list(limit)
        
        # Si no hay items, poblar con datos de ejemplo
        if not items:
            raise Exception("No real content found, using fallback data.")
            
        return {"success": True, "data": items}
    
    except Exception as e:
        print(f"Error fetching content: {e}")
        # Fallback a datos estáticos/simulados si falla la DB o no hay datos
        # (Esto se genera en la sección final del código)
        
        # Simulando la mezcla de datos de ejemplo si falla la DB o no hay contenido
        items = []
        for i in range(int(limit/2)): # mitad items de ejemplo
            if random.random() < 0.5: # 50% chance de video
                idx = random.choice(list(youtube_videos.keys()))
                item = youtube_videos[idx].copy()
                item["id"] = uuid.uuid4().hex
                item["created_at"] = datetime.now(timezone.utc).isoformat()
            else: # 50% chance de imagen
                idx = random.choice(list(sample_images.keys()))
                item = sample_images[idx].copy()
                item["id"] = uuid.uuid4().hex
                item["created_at"] = datetime.now(timezone.utc).isoformat()
                
            # Añadir datos extra simulados
            item["views"] = random.randint(100, 5000)
            item["likes"] = random.randint(10, 500)
            item["user_id"] = uuid.uuid4().hex[:8]
            
            items.append(item)
            
        return {"success": True, "data": items, "message": "Using fallback data."}


# Subir archivo de contenido
@router.post("/content/upload")
async def upload_content(
    file: UploadFile = File(...),
    title_title: Optional[str] = Form(None), # Cambiado 'title' a 'title_title' para evitar conflicto con 'title' interno del item
    user_id: Optional[str] = Form(None),
):
    try:
        content_type = file.content_type
        
        # Validar tipo de contenido: imagen o video
        if not content_type or not any(ct in content_type for ct in ['image/', 'video/']):
             raise HTTPException(status_code=400, detail="Invalid content type. Must be 'image' or 'video'.")

        kind = 'image' if 'image/' in content_type else 'video'
        
        file_ext = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        
        # Directorio de destino: 'uploads/image' o 'uploads/video'
        file_path = UPLOADS_DIR / kind / unique_filename
        file_path.parent.mkdir(parents=True, exist_ok=True) # Asegurar que el subdirectorio exista

        # Guardar el archivo en el sistema de archivos
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Crear el documento para la DB
        item = ContentItem(
            id=uuid.uuid4().hex,
            title=title_title or unique_filename,
            url=f"/uploads/{kind}/{unique_filename}", # URL pública simulada
            kind=kind,
            user_id=user_id or "anonymous",
        )
        
        doc = item.dict(by_alias=True)
        doc['created_at'] = doc['created_at'].isoformat() # Convertir a ISO string para guardar
        doc['updated_at'] = doc['updated_at'].isoformat()
        
        # Insertar en la base de datos
        collection_name = f'content_{kind}s' # Ejemplo: content_images o content_videos
        await DB[collection_name].insert_one(doc)
        
        return {"success": True, "item": item.dict(), "message": "Upload successful"}
        
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")
        
# Manejar likes/dislikes
@router.post("/content/{content_id}/like")
async def update_like(content_id: str, request: ItemLikeRequest):
    kind = request.kind # 'like' o 'dislike'
    
    # Validaciones para content_id
    if not content_id:
        raise HTTPException(status_code=400, detail="Content ID is required.")
    
    # Determinar si es una imagen o video (asumiendo que content_id no lo indica)
    # En una aplicación real, se buscaría en ambas colecciones o en una única colección unificada
    
    # Por simplicidad, probaremos ambas colecciones de ejemplo
    collections = ['content_images', 'content_videos'] 
    updated_count = 0
    
    for collection_name in collections:
        if kind == 'like':
            update_op = {'$inc': {'likes': 1}}
        elif kind == 'dislike':
            update_op = {'$inc': {'likes': -1}} # Asume que dislike es reducir el contador
        else:
            raise HTTPException(status_code=400, detail="Invalid 'kind' in request. Must be 'like' or 'dislike'.")
            
        result = await DB[collection_name].update_one(
            {'id': content_id},
            update_op
        )
        
        updated_count += result.modified_count
        
    if updated_count > 0:
        return {"success": True, "message": f"Like/Dislike successful ({kind} applied: {updated_count} item(s) updated)"}
    else:
        # logging.warning(f"Like error: Item not found for ID {content_id}")
        return {"success": False, "message": "Like/Dislike failed: Item not found"}

# --- Datos de Ejemplo (Fallback) ---

# Videos de YouTube de ejemplo (simulados)
youtube_videos = {
    "vid1": {"id": "KAdI6nBwYls", "title": "Bley Agulay - Knows (Give You Up)", "url": "https://www.youtube.com/watch?v=KAdI6nBwYls", "kind": "video", "thumbnail": "https://i.ytimg.com/vi/KAdI6nBwYls/mqdefault.jpg"},
    "vid2": {"id": "LXeYFwY9G94", "title": "Luis Fonsi, Demi Lovato - Échame La Culpa", "url": "https://www.youtube.com/watch?v=LXeYFwY9G94", "kind": "video", "thumbnail": "https://i.ytimg.com/vi/LXeYFwY9G94/mqdefault.jpg"},
    "vid3": {"id": "QnUq9YfU51w", "title": "Maroon 5 - Girls Like You ft. Cardi B", "url": "https://www.youtube.com/watch?v=QnUq9YfU51w", "kind": "video", "thumbnail": "https://i.ytimg.com/vi/QnUq9YfU51w/mqdefault.jpg"},
    "vid4": {"id": "ErShY6f92mU", "title": "Ed Sheeran - Shape of You", "url": "https://www.youtube.com/watch?v=ErShY6f92mU", "kind": "video", "thumbnail": "https://i.ytimg.com/vi/ErShY6f92mU/mqdefault.jpg"},
}

# Imágenes de Unsplash de ejemplo (simuladas)
sample_images = {
    "img1": {"url": "https://images.unsplash.com/photo-1000026467...", "title": "Flor en macro", "kind": "image"},
    "img2": {"url": "https://images.unsplash.com/photo-1000026468...", "title": "Perro jugando", "kind": "image"},
    "img3": {"url": "https://images.unsplash.com/photo-1000026466...", "title": "Montañas nevadas", "kind": "image"},
    "img4": {"url": "https://images.unsplash.com/photo-1000026465...", "title": "Playa al atardecer", "kind": "image"},
}

# --- Montaje de archivos estáticos y finalización ---

# Montar el router a la aplicación principal
app.include_router(router)

# Servir archivos subidos (ej: images y videos)
app.mount(
    "/uploads", 
    StaticFiles(directory=UPLOADS_DIR), 
    name="uploads"
)

# Endpoint para servir un archivo específico (ej: de prueba)
@app.get("/sinfiltro/html")
async def sinfiltro_html():
    file_path = Path("sinfiltro.html")
    if file_path.exists() and file_path.is_file():
        # En una app real, se usaría FileResponse o StreamingResponse
        # Aquí, simplemente simula una respuesta si el archivo existe
        with open(file_path, "r") as f:
            return f.read()
    raise HTTPException(status_code=404, detail="sinfiltro.html not found")

# --- Configuración CORS ---

# Permite peticiones CORS desde cualquier origen (para desarrollo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Reemplazar con dominios específicos en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de Logging (simple)
# Esto es solo un placeholder, la configuración real de logging es más compleja
# logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format='%(levelname)s - %(name)s - %(message)s')

# Manejo de eventos (opcional)
@app.on_event("startup")
async def startup_event():
    # print("Starting up...")
    pass

@app.on_event("shutdown")
async def shutdown_event():
    # Cerrar la conexión con la DB al apagar
    if CLIENT:
        CLIENT.close()
    # print("Shutting down...")

