# **Nombre:** servidor.py
# **Función:** Servidor principal de FastAPI.

import os
import shutil
import logging
import uuid
import datetime
import random

from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

# --- Inicialización y Conexión ---

# Cargar variables de entorno (para desarrollo local)
load_dotenv('.env')

# Directorios
ROOT_DIR = Path(__file__).parent
UPLOAD_DIR = ROOT_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True) # Crea el directorio si no existe

# Conexión a MongoDB (usando motor)
MONGO_URI = os.environ.get('MONGO_URL')
DB_NAME = 'sinfiltro_db'

if not MONGO_URI:
    # Esto es solo para que Render o un entorno de prueba no falle si no se encuentra la variable
    print("WARNING: MONGO_URL not found. Using a dummy client.")
    client = None
    db = None
else:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]

# Configuración principal de FastAPI
app = FastAPI(title="SinFiltro API", version="1.0")
api_router = APIRouter(prefix="/api")

# --- Modelos de Datos (Pydantic) ---

# Configuración base para modelos que interactúan con MongoDB
model_config_mongo = ConfigDict(
    populate_by_name=True,
    arbitrary_types_allowed=True,
    json_encoders={
        datetime.datetime: lambda dt: dt.isoformat()
    },
    extra='ignore' # Ignora el campo _id de MongoDB
)

class ContentItem(BaseModel):
    # Campos obligatorios
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    kind: str = Field(pattern=r'^(youtube|image|video)$')
    src: str
    title: str
    
    # Campos opcionales/metadata
    likes: int = 0
    comments: int = 0
    views: str = "0K" # Usar str para simplificar, como se ve en el sample data
    liked: bool = False
    
    # Timestamps
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    thumbnail: Optional[str] = None

    model_config = model_config_mongo

class LikeRequest(BaseModel):
    liked: bool

# --- Funciones de Datos de Muestra ---

# La misma estructura de datos que enviaste en la captura
def seed_sample_data(content_type: str):
    # Videos de YouTube (URLs reales)
    youtube_videos = [
        {"id": "dQw4w9WgXcQ", "title": "Rick Astley - Never Gonna Give You Up"},
        {"id": "hBf101GzX7k", "title": "¡La Casa! - Despacito"},
        {"id": "9bZ4u7Y19YM", "title": "Psy - GANGNAM STYLE"},
        {"id": "vSg0gK30R_Y", "title": "Mark Ronson - Uptown Funk ft. Bruno Mars"},
        {"id": "fJ9rZ394ZzQ", "title": "Queen - Bohemian Rhapsody"},
        {"id": "3GwWM3c8X8I", "title": "Ed Sheeran - Shape of You"}
    ]

    # Imágenes de Unsplash (URLs reales)
    sample_images = [
        {"src": "https://images.unsplash.com/photo-1580696950926-21bdd3d2fa6a?w=400&q=80", "title": "Montañas al amanecer"},
        {"src": "https://images.unsplash.com/photo-1442949574843-15be3e042b31?w=400&q=80", "title": "Naturaleza salvaje"},
        {"src": "https://images.unsplash.com/photo-1581178417684-25e6e8976b32?w=400&q=80", "title": "Carretera infinita"},
        {"src": "https://images.unsplash.com/photo-1466921544026-6211846c75cc?w=400&q=80", "title": "Playa de ensueño"},
        {"src": "https://images.unsplash.com/photo-1445778235215-6ac32007ce4a?w=400&q=80", "title": "Explosión de color"},
        {"src": "https://images.unsplash.com/photo-1511884642898-46fb2b0d0d1b?w=400&q=80", "title": "Olas del océano"}
    ]

    items = []
    
    # Crear mezcla de contenido
    for i in range(12):
        if i % 2 == 0:
            # YouTube video
            vid = random.choice(youtube_videos)
            item = {
                "id": str(uuid.uuid4()),
                "kind": "youtube",
                "src": f"https://www.youtube.com/watch?v={vid['id']}",
                "title": vid['title'],
                "likes": random.randint(100, 5000),
                "comments": random.randint(10, 500),
                "views": f"{random.randint(1, 99)}K",
                "liked": False,
                "thumbnail": f"https://img.youtube.com/vi/{vid['id']}/maxresdefault.jpg",
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        else:
            # Imagen
            img = random.choice(sample_images)
            item = {
                "id": str(uuid.uuid4()),
                "kind": "image",
                "src": f"{img['src']}&h=400&w=600&fit=crop",
                "title": img['title'],
                "likes": random.randint(50, 2000),
                "comments": random.randint(0, 300),
                "views": f"{random.randint(1, 500)}K",
                "liked": False,
                "thumbnail": f"{img['src']}&h=400&w=600&fit=crop",
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        items.append(item)
    
    return items

async def await_seed_sample_data(content_type: str):
    items = seed_sample_data(content_type)
    
    if items and db:
        collection_name = f"content_{content_type}"
        # Remover IDs de MongoDB si existen antes de insertar
        clean_items = []
        for item in items:
            clean_item = {k: v for k, v in item.items() if k != '_id'}
            clean_items.append(clean_item)
        
        await db[collection_name].insert_many(clean_items)
    
    return items

# --- Content API Routes ---

@api_router.get("/content/feed/{content_type}")
async def get_content_feed(content_type: str):
    """Obtiene contenido filtrado por tipo: trends, reco, recent."""
    if content_type not in ["trends", "reco", "recent"]:
        raise HTTPException(status_code=400, detail="Invalid content type")

    collection_name = f"content_{content_type}"
    
    try:
        if db:
            # Obtener contenido de la base de datos (últimos 100)
            items = await db[collection_name].find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
        else:
            items = []

        # Si está vacío, devolver datos de muestra
        if not items:
            items = await await_seed_sample_data(content_type)

        return {"success": True, "data": items}

    except Exception as e:
        logging.error(f"Error fetching content: {e}")
        return {"success": False, "message": str(e), "data": []}

@api_router.post("/content/upload")
async def upload_content(
    file: UploadFile = File(...), 
    title: str = Form(""),
):
    """Sube imagen o video."""
    
    # Validar tipo de archivo
    content_type = file.content_type
    if not (content_type.startswith('image/') or content_type.startswith('video/')):
        raise HTTPException(
            status_code=400, 
            detail="Tipo de archivo no válido. Solo se permiten imágenes y videos."
        )

    # Generar nombre de archivo único
    file_ext = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = UPLOAD_DIR / unique_filename

    # Guardar archivo de forma asíncrona
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logging.error(f"Error al guardar archivo: {e}")
        raise HTTPException(status_code=500, detail="Error al guardar el archivo en el servidor.")
    finally:
        await file.close()

    # Determinar el tipo y crear el ítem
    kind = "image" if content_type.startswith('image/') else "video"
    
    new_item = ContentItem(
        kind=kind,
        src=f"/uploads/{unique_filename}",
        title=title,
        thumbnail=f"/uploads/{unique_filename}" if kind == "image" else None
    )

    # Guardar en la base de datos
    try:
        doc = new_item.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        if db:
            await db.content_uploads.insert_one(doc)
        
        return {"success": True, "item": new_item.model_dump()}

    except Exception as e:
        logging.error(f"Error al guardar en BD: {e}")
        # Opcional: eliminar el archivo subido si falla la BD
        file_path.unlink(missing_ok=True) 
        raise HTTPException(status_code=500, detail="Error al guardar metadatos en la base de datos.")

@api_router.post("/content/{item_id_str}/like")
async def like_content(item_id_str: str, request: LikeRequest):
    """Toggle like en un contenido."""
    
    update_data = {}
    if request.liked:
        update_data = {'$set': {'liked': True}, '$inc': {'likes': 1}}
    else:
        update_data = {'$set': {'liked': False}, '$inc': {'likes': -1}}
    
    # Buscar y actualizar en todas las colecciones relevantes
    collections = ["content_trends", "content_reco", "content_recent", "content_uploads"]
    
    try:
        modified_count = 0
        if db:
            for collection_name in collections:
                result = await db[collection_name].update_one({"id": item_id_str}, update_data)
                modified_count += result.modified_count

        if modified_count > 0:
            return {"success": True, "message": "Like actualizado"}
        else:
            return {"success": False, "message": "Item no encontrado"}
            
    except Exception as e:
        logging.error(f"Error al guardar like: {e}")
        return {"success": False, "message": str(e)}

# --- Configuración de App principal ---

# Incluir las rutas de API
app.include_router(api_router)

# Montar directorio de subidas (archivos estáticos subidos)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Servir sinfiltro.html
@app.get("/", include_in_schema=False)
async def serve_sinfiltro():
    html_path = ROOT_DIR / "sinfiltro.html"
    if html_path.exists():
        # Devuelve el archivo HTML como respuesta de tipo FileResponse
        return FileResponse(html_path, media_type="text/html")
    else:
        # Esto es lo que causaba el 404/502 Bad Gateway
        raise HTTPException(status_code=404, detail="Error 404: No se encontró el archivo 'sinfiltro.html'.")

# CORS Middleware (necesario para la subida de archivos y APIs)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', "*").split(','), # Acepta CORS_ORIGINS de .env o '*'
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Shutdown hook (si se usa en un entorno con cliente)
@app.on_event("shutdown")
async def shutdown_event():
    if client:
        client.close()
