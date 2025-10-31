import os
import random
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Importaciones de FastAPI (CORREGIDAS: UploadFile, File, Form, HTTPException deben venir de fastapi)
from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Dependencias de Utilidades
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ConfigDict
from motor.motor_asyncio import AsyncIOMotorClient
from aioshutil import copyfile

# ==========================================================
# Carga de Variables de Entorno y Configuración de Rutas
# ==========================================================

load_dotenv('./.env')  # Carga variables de entorno

# Nota: Esto asume que el archivo .env está en la raíz, junto a servidor.py
ROOT_DIR = Path(__file__).parent
UPLOAD_DIR = ROOT_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True) # Crea la carpeta 'uploads' si no existe

# ==========================================================
# Configuración de MongoDB
# ==========================================================

MONGO_URI = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME')

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

# ==========================================================
# Inicialización y Middleware
# ==========================================================

# Crea la app principal con el nombre 'app'
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Configuración del Middleware CORS
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_event():
    client.close()
    logger.info("Database client closed on shutdown.")

# ==========================================================
# Definición de Modelos (Pydantic)
# ==========================================================

class ContentItemCreate(BaseModel):
    model_config = ConfigDict(extra='ignore')
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    kind: str  # 'Image', 'Video'
    title: str
    url: str
    thumbnail: Optional[str] = None
    likes: int = 0
    comments: int = 0
    views: int = 0
    
class ContentItem(ContentItemCreate):
    # Campos que se rellenan al crear
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheck(BaseModel):
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_ok: bool = True

class LikeRequest(BaseModel):
    is_liked: bool

# ==========================================================
# Rutas de Estado y Contenido (API Router)
# ==========================================================

@api_router.get("/", tags=["Status"])
async def get_status():
    return {"message": "SinFiltro API - Ready"}

@api_router.post("/statuscheck", response_model=StatusCheck, tags=["Status"])
async def create_status_check(input: StatusCheck):
    # Convertir a ISODate antes de guardar en MongoDB
    doc = input.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    await db.status_checks.insert_one(doc)
    return input

@api_router.get("/statuschecks", response_model=List[StatusCheck], tags=["Status"])
async def get_status_checks():
    status_checks = await db.status_checks.find({}).sort("_id", -1).to_list(1000)
    
    # Convertir strings ISO de vuelta a objetos datetime para el modelo
    for check in status_checks:
        # Se asume que el campo timestamp se guarda en formato ISO.
        # Es necesario envolver esto en un try-except si hay inconsistencias.
        check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

@api_router.post("/content/upload", tags=["Content"])
async def upload_content(
    file: UploadFile = File(...),
    title: str = Form(""),
    kind: str = Form("")
):
    try:
        # Validar tipo de archivo (imagen o video)
        content_type = file.content_type
        if not (content_type.startswith("image/") or content_type.startswith("video/")):
            raise HTTPException(400, "Only images and videos are allowed")

        # Generar nombre de archivo único
        file_ext = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename

        # Guardar el archivo localmente
        async with file_path.open("wb") as buffer:
            # Usar aioshutil.copyfile en lugar de shutil para async
            await copyfile(file.file, buffer)
        
        # Determinar el tipo (kind) y crear el ContentItem
        content_kind = "video" if content_type.startswith("video/") else "image"
        
        # Guardar en base de datos
        item = ContentItemCreate(
            title=title if title else unique_filename,
            url=f"/uploads/{unique_filename}",
            kind=content_kind,
            # La miniatura solo se aplica si es un video (para la lógica de ejemplo)
            thumbnail=f"/uploads/{unique_filename}" if content_kind == "image" else None
        )
        
        doc = item.model_dump()
        doc['created_at'] = datetime.now(timezone.utc).isoformat()
        
        await db.content_uploads.insert_one(doc)
        
        return {"success": True, "message": "Upload successful", "data": doc}

    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(500, f"Upload failed: {str(e)}")

@api_router.post("/content/like/{item_id}", tags=["Content"])
async def toggle_like(item_id: str, request: LikeRequest):
    inc_value = 1 if request.is_liked else -1
    
    # Buscar y actualizar en colecciones de feeds (trends, reco, recent)
    for collection_name in ["content_trends", "content_reco", "content_recent"]:
        collection = db[collection_name]
        result = await collection.update_one(
            {"id": item_id},
            {"$inc": {"likes": inc_value}}
        )
        if result.modified_count > 0:
            return {"success": True, "message": "Like updated"}
            
    return {"success": False, "message": "Item not found"}

@api_router.get("/content/feed/{content_type}", tags=["Content"])
async def get_content_feed(content_type: str):
    """Obtiene el feed de contenido por tipo: trends, reco, recent"""
    
    collection_name = f"content_{content_type}"
    collection = db[collection_name]
    
    try:
        items = await collection.find({}).sort("_id", -1).to_list(300)
        
        if not items:
            # Si está vacío, cargar datos de muestra (seed)
            items = await seed_sample_data(content_type)
            
        return {"success": True, "data": items}
        
    except Exception as e:
        logger.error(f"Error fetching content: {e}")
        return {"success": False, "message": str(e), "data": []}

# ==========================================================
# Funciones de Datos de Muestra (Seeding)
# ==========================================================

async def seed_sample_data(content_type: str):
    """Carga datos de muestra para propósitos de demostración"""
    
    # Datos de muestra de YouTube (reales, URLs de miniaturas funcionales)
    youtube_videos = [
        {"id": "dQw4w9WgXcQ", "title": "Rick Astley - Never Gonna Give You Up"},
        {"id": "9bZYu2j19fM", "title": "Luis Fonsi - Despacito"},
        {"id": "9bZYu2j19fM", "title": "Piso 21 - Pa' Olvidarme de Ella"},
        {"id": "9bZYu2j19fM", "title": "Bruno Mars - Uptown Funk"},
        {"id": "9bZYu2j19fM", "title": "Queen - Bohemian Rhapsody"},
        {"id": "9bZYu2j19fM", "title": "Ed Sheeran - Shape of You"},
    ]

    # Datos de muestra de Unsplash (imágenes sin problemas CORS)
    unsplash_images = [
        {"url": "https://images.unsplash.com/photo-1469594292607-ad2c47da4842?w=700&q=80", "title": "Montañas al atardecer"},
        {"url": "https://images.unsplash.com/photo-1447432768560-ad2c47da4842?w=700&q=80", "title": "Naturaleza salvaje"},
        {"url": "https://images.unsplash.com/photo-1581729112255-a221f5791789?w=700&q=80", "title": "Carretera infinita"},
        {"url": "https://images.unsplash.com/photo-1469594292607-ad2c47da4842?w=700&q=80", "title": "Buena mañana"},
        {"url": "https://images.unsplash.com/photo-1518843875323-8685160b73c4?w=700&q=80", "title": "Minimalismo"},
        {"url": "https://images.unsplash.com/photo-15118843875323-8685160b73c4?w=700&q=80", "title": "Olas del oceano"},
    ]

    items = []
    # Crear una mezcla de 50/50 entre videos e imágenes
    for i in range(12):
        if i % 2 == 0:
            # Video de YouTube
            video = random.choice(youtube_videos)
            item = {
                "id": str(uuid.uuid4()),
                "kind": "video",
                "title": video["title"],
                "url": f"https://www.youtube.com/watch?v={video['id']}",
                "likes": random.randint(300, 5000),
                "comments": random.randint(10, 500),
                "views": random.randint(1, 999) * 1000,
                "isLiked": False,
                "thumbnail": f"https://img.youtube.com/vi/{video['id']}/maxresdefault.jpg",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            # Imagen de Unsplash
            image = random.choice(unsplash_images)
            item = {
                "id": str(uuid.uuid4()),
                "kind": "image",
                "title": image["title"],
                "url": image["url"],
                "likes": random.randint(300, 5000),
                "comments": random.randint(10, 500),
                "views": random.randint(1, 999) * 1000,
                "isLiked": False,
                "thumbnail": image["url"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
        items.append(item)

    # Limpiar y guardar en base de datos
    collection_name = f"content_{content_type}"
    # Limpiar cualquier item_id antiguo
    
    # El código original era confuso, simplificamos la inserción si los items no tienen '_id'
    # Si tienen, el driver de MongoDB lo ignora o lo crea.

    await db[collection_name].insert_many(items)
    return items

# ==========================================================
# Servicio de Archivos y Frontend (SinFiltro)
# ==========================================================

# Montar directorio de subidas (archivos estáticos)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Incluir las rutas de la API en la aplicación principal
app.include_router(api_router, prefix="/api")

# Servir Sinfiltro HTML
@app.get("/sinfiltro/")
async def serve_sinfiltro():
    # Asume que sinfiltro.html está en la raíz, junto a servidor.py
    html_path = Path(__file__).parent / "sinfiltro.html"
    if html_path.exists():
        return FileResponse(html_path, media_type="text/html")
    else:
        raise HTTPException(404, "Sinfiltro page not found")
