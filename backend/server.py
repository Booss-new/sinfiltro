Hola quiero que re...

Buy
right arrow

Hey Seguridad, Quick input needed :
Perfecto. Ahora déjame darte una guía clara de los 3 archivos que necesitas:

📦 ARCHIVOS PARA GITHUB Y RENDER
1️⃣ backend/server.py (Código arriba completo - líneas 1-289)
2️⃣ backend/requirements.txt
fastapi==0.110.1
uvicorn==0.25.0
python-dotenv>=1.0.1
pymongo==4.5.0
pydantic>=2.6.4
motor==3.3.1
python-multipart>=0.0.9
3️⃣ sinfiltro.html (Frontend completo)
El archivo HTML completo está arriba en mi respuesta anterior cuando lo creé. Te lo resumo de nuevo - es el archivo que creé en /app/frontend/public/sinfiltro.html.

Para descargarlo directamente desde tu entorno, puedes:

# Opción 1: Ver el contenido completo
cat /app/frontend/public/sinfiltro.html

# Opción 2: Copiar a una ubicación más accesible
cp /app/frontend/public/sinfiltro.html ~/sinfiltro.html
🚀 INSTRUCCIONES PARA RENDER
Variables de Entorno en Render:
MONGO_URL=tu_url_de_mongodb_atlas
DB_NAME=sinfiltro
CORS_ORIGINS=*
Comando de Start en Render:
uvicorn server:app --host 0.0.0.0 --port $PORT
¿Quieres que te muestre el HTML completo en partes más pequeñas para que lo copies fácilmente? O prefieres que te lo proporcione de otra manera? 📄

Oct 29, 03:13 PM

Bueno solo usaremos por mientras git hub ya que en automático se sube a render ok mira lo haremos de esta forma me pasas el nombre del archivo que hay que crear y abajito me pasas el código para solo copiar y pegar

Oct 29, 03:15 PM

¡Perfecto! Te paso todo organizado para copiar y pegar:

---

## 📄 **ARCHIVO 1**

**Nombre:** `backend/server.py`

```python

from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException

from fastapi.staticfiles import StaticFiles

from fastapi.responses import FileResponse

from dotenv import load_dotenv

from starlette.middleware.cors import CORSMiddleware

from motor.motor_asyncio import AsyncIOMotorClient

import os

import logging

from pathlib import Path

from pydantic import BaseModel, Field, ConfigDict

from typing import List, Optional

import uuid

from datetime import datetime, timezone

import shutil

import mimetypes

ROOT_DIR = Path(__file__).parent

load_dotenv(ROOT_DIR / '.env')

# MongoDB connection

mongo_url = os.environ['MONGO_URL']

client = AsyncIOMotorClient(mongo_url)

db = client[os.environ['DB_NAME']]

# Create uploads directory

UPLOAD_DIR = ROOT_DIR / 'uploads'

UPLOAD_DIR.mkdir(exist_ok=True)

# Create the main app without a prefix

app = FastAPI()

# Create a router with the /api prefix

api_router = APIRouter(prefix="/api")

# Define Models

class StatusCheck(BaseModel):

model_config = ConfigDict(extra="ignore") # Ignore MongoDB's _id field


id: str = Field(default_factory=lambda: str(uuid.uuid4()))

client_name: str

timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):

client_name: str

class ContentItem(BaseModel):

model_config = ConfigDict(extra="ignore")


id: str = Field(default_factory=lambda: str(uuid.uuid4()))

kind: str # 'youtube', 'image', 'video'

src: str

title: str

likes: int = 0

comments: int = 0

views: str = "0K"

liked: bool = False

thumbnail: Optional[str] = None

created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ContentItemCreate(BaseModel):

kind: str

src: str

title: str

thumbnail: Optional[str] = None

class LikeRequest(BaseModel):

liked: bool

# Add your routes to the router instead of directly to app

@api_router.get("/")

async def root():

return {"message": "SinFiltro API - Ready"}

@api_router.post("/status", response_model=StatusCheck)

async def create_status_check(input: StatusCheckCreate):

status_dict = input.model_dump()

status_obj = StatusCheck(**status_dict)


# Convert to dict and serialize datetime to ISO string for MongoDB

doc = status_obj.model_dump()

doc['timestamp'] = doc['timestamp'].isoformat()


_ = await db.status_checks.insert_one(doc)

return status_obj

@api_router.get("/status", response_model=List[StatusCheck])

async def get_status_checks():

# Exclude MongoDB's _id field from the query results

status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)


# Convert ISO string timestamps back to datetime objects

for check in status_checks:

if isinstance(check['timestamp'], str):

check['timestamp'] = datetime.fromisoformat(check['timestamp'])


return status_checks

# Content APIs

@api_router.get("/content/feed/{content_type}")

async def get_content_feed(content_type: str):

"""Get content by type: trends, reco, recent"""

try:

# Get content from database

collection_name = f"content_{content_type}"

items = await db[collection_name].find({}, {"_id": 0}).to_list(100)


# If empty, return sample data

if not items:

items = await seed_sample_data(content_type)


return {"success": True, "data": items}

except Exception as e:

logging.error(f"Error fetching content: {e}")

return {"success": False, "message": str(e), "data": []}

@api_router.post("/content/upload")

async def upload_content(

file: UploadFile = File(...),

title: str = Form(...)

):

"""Upload image or video file"""

try:

# Validate file type

content_type = file.content_type or ""

if not (content_type.startswith("image/") or content_type.startswith("video/")):

raise HTTPException(400, "Only images and videos are allowed")


# Generate unique filename

file_ext = Path(file.filename).suffix

unique_filename = f"{uuid.uuid4()}{file_ext}"

file_path = UPLOAD_DIR / unique_filename


# Save file

with open(file_path, "wb") as buffer:

shutil.copyfileobj(file.file, buffer)


# Determine kind

kind = "image" if content_type.startswith("image/") else "video"


# Create content item

item = ContentItem(

kind=kind,

src=f"/uploads/{unique_filename}",

title=title or f"Uploaded {kind}",

thumbnail=f"/uploads/{unique_filename}" if kind == "image" else None

)


# Save to database (in 'uploads' collection)

doc = item.model_dump()

doc['created_at'] = doc['created_at'].isoformat()

await db.content_uploads.insert_one(doc)


return {"success": True, "item": item.model_dump()}

except HTTPException as he:

raise he

except Exception as e:

logging.error(f"Upload error: {e}")

raise HTTPException(500, f"Upload failed: {str(e)}")

@api_router.post("/content/{item_id}/like")

async def like_content(item_id: str, request: LikeRequest):

"""Toggle like on content"""

try:

# Find item in any collection

for collection in ["content_trends", "content_reco", "content_recent", "content_uploads"]:

result = await db[collection].update_one(

{"id": item_id},

{

"$set": {"liked": request.liked},

"$inc": {"likes": 1 if request.liked else -1}

}

)

if result.modified_count > 0:

return {"success": True, "message": "Liked updated"}


return {"success": False, "message": "Item not found"}

except Exception as e:

logging.error(f"Like error: {e}")

return {"success": False, "message": str(e)}

# Seed sample data function

async def seed_sample_data(content_type: str):

"""Create sample data for demo purposes"""

import random


# Sample YouTube videos (real, working URLs)

youtube_videos = [

{"id": "dQw4w9WgXcQ", "title": "Rick Astley - Never Gonna Give You Up"},

{"id": "kJQP7kiw5Fk", "title": "Luis Fonsi - Despacito"},

{"id": "9bZkp7q19f0", "title": "PSY - GANGNAM STYLE"},

{"id": "OPf0YbXqDm0", "title": "Mark Ronson - Uptown Funk ft. Bruno Mars"},

{"id": "fJ9rUzIMcZQ", "title": "Queen - Bohemian Rhapsody"},

{"id": "JGwWNGJdvx8", "title": "Ed Sheeran - Shape of You"},

]


# Sample images (Unsplash - no CORS issues)

sample_images = [

{"url": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4", "title": "Montañas al atardecer"},

{"url": "https://images.unsplash.com/photo-1469474968028-56623f02e42e", "title": "Naturaleza salvaje"},

{"url": "https://images.unsplash.com/photo-1501785888041-af3ef285b470", "title": "Carretera infinita"},

{"url": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b", "title": "Picos nevados"},

{"url": "https://images.unsplash.com/photo-1418065460487-3e41a6c84dc5", "title": "Bosque místico"},

{"url": "https://images.unsplash.com/photo-1511884642898-4c92249e20b6", "title": "Olas del océano"},

]


items = []


# Create mix of content

for i in range(12):

if i % 2 == 0 and youtube_videos:

# YouTube video

video = random.choice(youtube_videos)

item = {

"id": str(uuid.uuid4()),

"kind": "youtube",

"src": f"https://www.youtube.com/watch?v={video['id']}",

"title": video["title"],

"likes": random.randint(100, 5000),

"comments": random.randint(10, 500),

"views": f"{random.randint(1, 999)}K",

"liked": False,

"thumbnail": f"https://img.youtube.com/vi/{video['id']}/maxresdefault.jpg",

"created_at": datetime.now(timezone.utc).isoformat()

}

else:

# Image

img = random.choice(sample_images)

item = {

"id": str(uuid.uuid4()),

"kind": "image",

"src": f"{img['url']}?w=800&q=80",

"title": img["title"],

"likes": random.randint(50, 2000),

"comments": random.randint(5, 200),

"views": f"{random.randint(1, 500)}K",

"liked": False,

"thumbnail": f"{img['url']}?w=400&q=80",

"created_at": datetime.now(timezone.utc).isoformat()

}


items.append(item)


# Save to database

collection_name = f"content_{content_type}"

if items:

# Remove _id if exists before inserting

clean_items = []

for item in items:

clean_item = {k: v for k, v in item.items() if k != '_id'}

clean_items.append(clean_item)

await db[collection_name].insert_many(clean_items)


return items

# Include the router in the main app

app.include_router(api_router)

# Mount uploads directory for static file serving

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Serve SinFiltro HTML

@app.get("/sinfiltro")

async def serve_sinfiltro():

html_path = Path(__file__).parent.parent / "sinfiltro.html"

if html_path.exists():

return FileResponse(html_path, media_type="text/html")

else:

raise HTTPException(404, "SinFiltro page not found")

app.add_middleware(

CORSMiddleware,

allow_credentials=True,

allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),

allow_methods=["*"],

allow_headers=["*"],

)

# Configure logging

logging.basicConfig(

level=logging.INFO,

format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'

)

logger = logging.getLogger(__name__)

@app.on_event("shutdown")

async def shutdown_db_client():

client.close()

```
