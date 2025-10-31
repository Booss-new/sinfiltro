import uvicorn
import os
from typing import Annotated, UploadFile, File, Form, HTTTPException

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from dotenv import load_dotenv

from akryptos.base_model import AkryptosBaseModel
from akryptos.client import AkryptosApiClient
from akryptos.db_model import AkryptosDbModel
from akryptos.config import AkryptosConfig

from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from pydantic_extra_types.uuid import Uuid
from datetime import timezone

import shutil
import logging
from typing import List, Optional

load_dotenv(ROOT_DIR / ".env")

ROOT_DIR = Path(__file__).parent.parent
DB_URI = os.getenv("AKRYPTOS_DB_URI")
API_KEY = os.getenv("AKRYPTOS_API_KEY")
UPLOAD_DIR = ROOT_DIR / 'uploads'
CONFIG_FILE = ROOT_DIR / 'config.json'

db_client = AkryptosDbModel(DB_URI)
api_client = AkryptosApiClient(API_KEY, "https://api.akryptos.com/api/v1")

app = FastAPI()

if not UPLOAD_DIR.exists():
    UPLOAD_DIR.mkdir()

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuración de CORS
origins = [
    "http://localhost",
    "http://localhost:8080",
    "https://pp.emergent.sh",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model_config = ConfigDict(extra="ignore")

api_router = FastAPI(prefix="/api")

# Definición de modelos Pydantic
class ContentItemBaseModel(BaseModel):
    model_config = model_config
    title: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class ContentItemCreate(ContentItemBaseModel):
    kind: str # 'video' or 'image'
    url: str
    thumb: str
    tags: Optional[List[str]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ContentItem(ContentItemCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    views: int = 0
    likes: int = 0
    comments: int = 0

class LikeRequest(BaseModel):
    liked: bool

# Funciones de la base de datos
async def get_db_client():
    return db_client

@app.on_event("startup")
async def startup_db_client():
    await db_client.connect()
    logger.info("Database connected.")
    
    # Crear índices
    db_client.db['content'].create_index([("tags", 1)])
    db_client.db['content'].create_index([("created_at", -1)])
    db_client.db['content'].create_index([("kind", 1)])

@app.on_event("shutdown")
async def shutdown_db_client():
    await db_client.close()
    logger.info("Database disconnected.")


# Endpoints
@api_router.get("/")
async def root():
    return {"message": "SinFiltro API - Ready"}

@api_router.post("/status/")
async def status_check(
    db: AkryptosDbModel = Depends(get_db_client)
):
    try:
        # Aquí se asume que la función 'run_status_check' existe en la clase AkryptosDbModel y devuelve un objeto de estado
        status_db = db.run_status_check()
    except Exception as e:
        status_db = {"status": "error", "message": str(e)}

    # Aquí se asume que 'api_client.check_status()' existe y devuelve un objeto de estado
    status_api = api_client.check_status()
    
    # Aquí se asume que existe una colección llamada 'status_checks'
    db.db['status_checks'].insert_one(status_db)

    return {"status_db": status_db, "status_api": status_api}

@api_router.get("/content/{content_type}")
async def get_content(
    content_type: str, 
    page: int = 1, 
    limit: int = 20,
    db: AkryptosDbModel = Depends(get_db_client)
):
    
    if content_type not in ["all", "video", "image"]:
        raise HTTTPException(status_code=400, detail="Invalid content type")

    collection = db.db['content']
    query = {}
    if content_type != "all":
        query['kind'] = content_type

    # Obtener el número total de documentos
    total_items = collection.count_documents(query)
    
    # Calcular el salto (skip)
    skip = (page - 1) * limit
    
    # Consulta a la base de datos, ordenando por 'created_at' de forma descendente (-1)
    items_cursor = collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
    items = [ContentItem(**item).model_dump(by_alias=True) for item in await items_cursor.to_list(limit)]
    
    # Si la lista de items está vacía, intentar obtener un 'sample_data'
    if not items:
        try:
            items = await send_sample_data(content_type, db)
        except Exception as e:
            logger.error(f"Error fetching sample data: {e}")
            raise HTTTPException(status_code=500, detail="Error fetching content and sample data.")
            
    # Devolver la respuesta con los datos, información de paginación y mensaje de éxito
    return {
        "success": True, 
        "message": "Data fetched successfully", 
        "data": items, 
        "total": total_items, 
        "page": page, 
        "limit": limit
    }


@api_router.post("/upload/")
async def upload_file(
    file: Annotated[UploadFile, File()], 
    title: Annotated[str, Form()], 
    db: AkryptosDbModel = Depends(get_db_client)
):
    
    # Validar el tipo de archivo y determinar si es imagen o video
    content_type = file.content_type
    
    if content_type.startswith("image/"):
        kind = "image"
    elif content_type.startswith("video/"):
        kind = "video"
    else:
        raise HTTTPException(status_code=400, detail="Only images and videos are allowed")

    file_ext = Path(file.filename).suffix
    unique_filename = str(uuid.uuid4()) + file_ext
    file_path = UPLOAD_DIR / unique_filename

    # Guardar el archivo en el sistema de archivos
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Determinar el URL
        # Se asume que el servidor web sirve el directorio 'uploads' en el path '/uploads/'
        file_url = f"/uploads/{unique_filename}" 

        # Crear el objeto ContentItem
        # Se necesita un 'thumb' para la previsualización, se está usando la URL del archivo mismo como placeholder
        item = ContentItemCreate(
            title=title,
            kind=kind,
            url=file_url,
            thumb=file_url if kind == 'image' else '/path/to/video/thumb.jpg', # Esto debe ser mejorado para videos
            created_at=datetime.now(timezone.utc),
            tags=None
        )
        
        # Insertar en la base de datos
        result = db.db['content'].insert_one(item.model_dump(by_alias=True))
        
        # Devolver respuesta
        return {"success": True, "message": "File uploaded successfully", "data": item.model_dump(by_alias=True)}

    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTTPException(status_code=500, detail=f"An error occurred during upload: {str(e)}")
        
    finally:
        file.file.close() # Cerrar el buffer del archivo
        
@api_router.post("/content/{id}/like")
async def like_content(
    id: str, 
    request: LikeRequest, 
    db: AkryptosDbModel = Depends(get_db_client)
):
    
    # Actualizar el contador de 'likes' en la base de datos
    collection = db.db['content']
    
    if request.liked:
        # Incrementar likes
        update_result = collection.update_one(
            {"id": id}, 
            {"$inc": {"likes": 1}}
        )
        message = "Content liked successfully"
    else:
        # Decrementar likes, asegurándose de que no sea menor a cero
        update_result = collection.update_one(
            {"id": id, "likes": {"$gt": 0}}, 
            {"$inc": {"likes": -1}}
        )
        message = "Content unliked successfully"

    if update_result.modified_count == 0:
        logger.warning(f"Like/Unlike update failed for ID: {id} and liked: {request.liked}. Content may not exist or like count is already 0.")
        # Se puede lanzar una excepción HTTP si el contenido no existe
        # raise HTTTPException(status_code=404, detail="Content not found or like count already 0.")

    return {"success": True, "message": message, "data": {"id": id, "liked": request.liked}}

# Función para enviar datos de ejemplo si la DB está vacía
async def send_sample_data(content_type: str, db: AkryptosDbModel):
    
    video_directs = [
        # URLs de videos (ejemplos con formato directo MP4)
        {"url": "https://cdn.pixabay.com/v/2023/10/25/11/44/sunrise-8340428_502_mp4.mp4", "thumb": "https://cdn.pixabay.com/photo/2023/10/25/11/44/sunrise-8340428_640.jpg", "title": "Sunrise Video"},
        {"url": "https://cdn.pixabay.com/v/2023/10/25/11/44/sunrise-8340428_502_mp4.mp4", "thumb": "https://cdn.pixabay.com/photo/2023/10/25/11/44/sunrise-8340428_640.jpg", "title": "Another Video"},
        {"url": "https://cdn.pixabay.com/v/2023/10/25/11/44/sunrise-8340428_502_mp4.mp4", "thumb": "https://cdn.pixabay.com/photo/2023/10/25/11/44/sunrise-8340428_640.jpg", "title": "Video Test"},
    ]
    
    sample_images = [
        # URLs de imágenes (ejemplos)
        {"url": "https://images.unsplash.com/photo-1698284755106-96b1d4e7240c", "thumb": "https://images.unsplash.com/photo-1698284755106-96b1d4e7240c?w=400&h=400&fit=crop", "title": "Mountain Image"},
        {"url": "https://images.unsplash.com/photo-1698284755106-96b1d4e7240c", "thumb": "https://images.unsplash.com/photo-1698284755106-96b1d4e7240c?w=400&h=400&fit=crop", "title": "Another Image"},
        {"url": "https://images.unsplash.com/photo-1698284755106-96b1d4e7240c", "thumb": "https://images.unsplash.com/photo-1698284755106-96b1d4e7240c?w=400&h=400&fit=crop", "title": "Image Test"},
    ]

    items_to_insert = []
    
    # Insertar 6 items (3 videos, 3 imágenes)
    for i in range(1, 4): 
        # Video
        video_data = video_directs[i-1]
        items_to_insert.append(ContentItemCreate(
            title=video_data['title'],
            kind="video",
            url=video_data['url'],
            thumb=video_data['thumb'],
            tags=["random", "viral"],
            created_at=datetime.now(timezone.utc)
        ).model_dump(by_alias=True))
        
        # Imagen
        image_data = sample_images[i-1]
        items_to_insert.append(ContentItemCreate(
            title=image_data['title'],
            kind="image",
            url=image_data['url'],
            thumb=image_data['thumb'],
            tags=["random", "nature"],
            created_at=datetime.now(timezone.utc)
        ).model_dump(by_alias=True))

    collection = db.db['content']
    
    # Asegurarse de no duplicar si ya hay contenido
    if collection.count_documents({}) < 10: # Si hay menos de 10 elementos, insertar
        collection.insert_many(items_to_insert)
        
    # Devolver los datos de ejemplo insertados
    # Re-consultar para asegurar que se devuelvan los objetos completos con IDs, etc.
    query = {}
    if content_type != "all":
        query['kind'] = content_type
        
    items_cursor = collection.find(query).sort("created_at", -1).limit(6) 
    return [ContentItem(**item).model_dump(by_alias=True) for item in await items_cursor.to_list(6)]


# Se añade el router a la aplicación principal
app.include_router(api_router)

# El bloque de ejecución uvicorn (no visible pero común en FastAPI)
# if __name__ == "__main__":
#     uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

