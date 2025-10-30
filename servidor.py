from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import uuid
from pathlib import Path

app = FastAPI()

# === CARPETA DE SUBIDAS ===
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# === SIRVE TU HTML ORIGINAL ===
@app.get("/", response_class=HTMLResponse)
async def root():
    filepath = Path(__file__).parent / "sinfiltro.html"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="sinfiltro.html no encontrado")
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

# === API: SUBIR ARCHIVO (EXACTO como tu JS espera) ===
@app.post("/api/content/upload")
async def upload_file(file: UploadFile = File(...), title: str = Form(None)):
    if not file.filename:
        return JSONResponse({"success": False, "message": "No file"}, status_code=400)
    
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / filename
    
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    
    return JSONResponse({
        "success": True,
        "item": {
            "id": f"upload-{uuid.uuid4().hex}",
            "kind": "video" if file.content_type.startswith("video/") else "image",
            "url": f"/uploads/{filename}",
            "title": title or file.filename,
            "likes": 0,
            "views": "0K"
        }
    })

# === API: FEED (EXACTO como tu JS espera) ===
@app.get("/api/content/feed/{tipo_feed}")
async def obtener_feed(tipo_feed: str):
    # Datos de ejemplo (tu JS los usa si no hay DB)
    sample_data = [
        {
            "id": "1",
            "kind": "video",
            "url": "https://player.vimeo.com/external/371604939.sd.mp4?s=8c1b8b8a8f8f8f8f8f8f8f8f8f8f8f8f&profile_id=165",
            "title": "Naturaleza",
            "likes": 1234,
            "views": "12K"
        },
        {
            "id": "2",
            "kind": "image",
            "url": "https://images.pexels.com/photos/358457/pexels-photo-358457.jpeg",
            "title": "Atardecer",
            "likes": 890,
            "views": "8K"
        }
    ]
    return JSONResponse({"data": sample_data})

# === HEALTH CHECK ===
@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})
