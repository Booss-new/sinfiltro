from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse
from datetime import datetime
import random
import os
import shutil
from pathlib import Path
from uvicorn import run
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import logging
import uuid
import json

ROOT_DIR = Path(__file__).parent.parent
LOAD_DATA_DIR = ROOT_DIR / 'data'
UPLOAD_DIR = ROOT_DIR / 'uploads'
CONFIG_FILE = LOAD_DATA_DIR / 'config.json'

APP = FastAPI(
    title="sinfiltro API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

origins = [
    "*",
]

APP.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StatusCheck(BaseModel):
    ready: bool = Field(..., example=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ContentType(BaseModel):
    id: str
    src: str
    title: str
    type: str
    views: int = 0
    likes: int = 0
    description: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class LikeStatus(BaseModel):
    success: bool
    message: str

@APP.get("/")
def read_root():
    return {"status": "sinfiltro API is ready"}

@APP.get("/api/status", response_model=StatusCheck)
def get_status_check():
    return StatusCheck(ready=True)

sample_images = [
    {
        "id": str(uuid.uuid4()), "title": "Playa Secreta", "src": "https://images.unsplash.com/photo-1500000000-0000000000",
        "type": "image", "views": random.randint(100, 5000), "likes": random.randint(10, 500), "created_at": datetime.now().isoformat()
    },
]

sample_youtube_videos = [
    {
        "id": str(uuid.uuid4()), "title": "Video Musical", "src": "https://www.youtube.com/watch?v={id}",
        "type": "youtube", "views": random.randint(1000, 50000), "likes": random.randint(100, 5000), "created_at": datetime.now().isoformat()
    },
]

def get_sample_data(content_type: str, count: int = 10) -> List[Dict[str, Any]]:
    if content_type == 'trends':
        items = sample_images + sample_youtube_videos
        random.shuffle(items)
        return items[:count]
    elif content_type == 'recomendar':
        items = sample_images + sample_youtube_videos
        random.shuffle(items)
        return items[:count]
    else:
        items = sample_images + sample_youtube_videos
        random.shuffle(items)
        return items

@APP.get("/api/content/{content_type}", response_model=List[ContentType])
def get_content(content_type: str, offset: int = 0, limit: int = 20):
    try:
        data_items = get_sample_data(content_type)
        
        start = offset
        end = offset + limit
        
        if start >= len(data_items):
            return {"success": True, "data": []}
            
        data_slice = data_items[start:end]
        
        for item in data_slice:
            if 'views' not in item:
                item['views'] = random.randint(100, 5000)
            if 'likes' not in item:
                item['likes'] = random.randint(10, 500)
                
        content_list = [ContentType(**item) for item in data_slice]
        
        return content_list
        
    except Exception as e:
        logging.error(f"Error al obtener contenido: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@APP.post("/api/upload")
async def upload_file_endpoint(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None)
):
    content_type = file.content_type
    
    if content_type.startswith("image/"):
        kind = "image"
        allowed_types = ("image/jpeg", "image/png", "image/gif", "image/webp")
    elif content_type.startswith("video/"):
        kind = "video"
        allowed_types = ("video/mp4", "video/webm", "video/ogg")
    else:
        raise HTTPException(status_code=400, detail="Tipo de archivo no permitido")

    if content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Tipo de archivo no permitido")
    
    unique_filename = f"{uuid.uuid4()}-{file.filename}"
    file_path = UPLOAD_DIR / unique_filename
    
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        new_item = {
            "id": str(uuid.uuid4()),
            "title": title or file.filename,
            "src": f"/uploads/{unique_filename}",
            "type": kind,
            "views": 0,
            "likes": 0,
            "created_at": datetime.utcnow().isoformat()
        }
        
        return {"success": True, "message": "Subida exitosa", "item": new_item}
        
    except Exception as e:
        logging.error(f"Error al guardar archivo: {e}")
        raise HTTPException(status_code=500, detail="Fallo al guardar archivo")

@APP.post("/api/content/like", response_model=LikeStatus)
async def post_like(request: Request, content_id: str):
    try:
        return LikeStatus(success=True, message="Like updated")
        
    except Exception as e:
        logging.error(f"Error al manejar like: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar like")

@APP.get("/uploads/{filename}")
async def get_upload_file(filename: str):
    file_path = UPLOAD_DIR / filename
    
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
    return FileResponse(path=file_path, filename=filename)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == '__main__':
    os.makedirs(UPLOAD_DIR, exist_ok=True)
