from flask import Flask, send_file, request, jsonify, send_from_directory
import os
import uuid

# === CONFIGURACIÓN ===
app = Flask(__name__)
CARPETA_SUBIDAS = 'uploads'
os.makedirs(CARPETA_SUBIDAS, exist_ok=True)

# === RUTA PRINCIPAL (CON PRUEBA DE SEGURIDAD) ===
@app.route('/')
def inicio():
    # Primero intenta servir el HTML
    if os.path.exists('sinfiltro.html'):
        return send_file('sinfiltro.html')
    else:
        # Si no existe, muestra mensaje claro
        return """
        <h1 style="color:#ff3366; text-align:center; margin-top:100px;">
            ¡SINFILTRO ESTÁ VIVO!
        </h1>
        <p style="text-align:center; color:#ccc;">
            Pero <code>sinfiltro.html</code> no está en la raíz.<br>
            Súbelo a la misma carpeta que <code>servidor.py</code>
        </p>
        <p style="text-align:center;">
            <a href="/health" style="color:#00ff00;">Health Check</a>
        </p>
        """, 200

# === VER ARCHIVO SUBIDO ===
@app.route('/uploads/<nombre_archivo>')
def archivo_subido(nombre_archivo):
    return send_from_directory(CARPETA_SUBIDAS, nombre_archivo)

# === SUBIR ARCHIVO ===
@app.route('/api/content/upload', methods=['POST'])
def subir_archivo():
    archivo = request.files.get('file')
    if not archivo or archivo.filename == '':
        return jsonify(success=False, message="No hay archivo"), 400
    
    titulo = request.form.get('title', archivo.filename)
    extension = os.path.splitext(archivo.filename)[1]
    nombre_nuevo = f"{uuid.uuid4().hex}{extension}"
    ruta_guardar = os.path.join(CARPETA_SUBIDAS, nombre_nuevo)
    archivo.save(ruta_guardar)
    
    return jsonify({
        "success": True,
        "item": {
            "id": f"upload-{uuid.uuid4().hex}",
            "kind": "video" if archivo.mimetype.startswith('video') else "image",
            "url": f"/uploads/{nombre_nuevo}",
            "title": titulo,
            "likes": 0,
            "views": "0K"
        }
    })

# === OBTENER FEED ===
@app.route('/api/content/feed/<tipo_feed>')
def obtener_feed(tipo_feed):
    return jsonify(data=[
        {
            "id": "1",
            "kind": "video",
            "url": "https://player.vimeo.com/external/371604939.sd.mp4?s=8c1b8b8a8f8f8f8f8f8f8f8f8f8f8f8f&profile_id=165",
            "title": "Naturaleza",
            "likes": 1234,
            "views": "12K"
        }
    ])

# === SALUD ===
@app.route('/health')
def salud():
    return jsonify(status="ok")

# === INICIAR SERVIDOR ===
if __name__ == '__main__':
    puerto = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=puerto)
