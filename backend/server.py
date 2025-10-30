from flask import Flask, send_file, request, jsonify, send_from_directory
import os
import uuid

# --- CONFIG ---
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- RUTA PRINCIPAL ---
@app.route('/')
def index():
    return send_file('sinfiltro.html')

# --- SUBIDAS ---
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/api/content/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify(success=False, message="No file"), 400
    
    file = request.files['file']
    title = request.form.get('title', file.filename)
    
    if file.filename == '':
        return jsonify(success=False, message="No file"), 400
    
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    return jsonify({
        "success": True,
        "item": {
            "id": f"upload-{uuid.uuid4().hex}",
            "kind": "video" if file.mimetype.startswith('video') else "image",
            "url": f"/uploads/{filename}",
            "title": title,
            "likes": 0,
            "views": "0K"
        }
    })

# --- FEED ---
@app.route('/api/content/feed/<feed_type>')
def get_feed(feed_type):
    sample = [
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
    return jsonify(data=sample)

# --- HEALTH ---
@app.route('/health')
def health():
    return jsonify(status="ok")

# --- RUN ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
