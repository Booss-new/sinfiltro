from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import uuid

app = Flask(__name__, template_folder='.', static_folder='.')
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # CORREGIDO: Crea carpeta

@app.route('/')
def index():
    return render_template('sinfiltro.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/api/content/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify(success=False, message="No file"), 400
    
    file = request.files['file']
    title = request.form.get('title', file.filename)  # CORREGIDO: 'title'
    
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
            "comments": 0,
            "views": "0K"
        }
    })

# Feed simulado (Pexels o tuyo)
@app.route('/api/content/feed/<feed_type>')
def get_feed(feed_type):
    sample = [
        {
            "id": "pexels1",
            "kind": "video",
            "url": "https://player.vimeo.com/external/371604939.sd.mp4?s=8c1b8b8a8f8f8f8f8f8f8f8f8f8f8f8f&profile_id=165",
            "title": "Naturaleza",
            "likes": 1234,
            "views": "12K"
        },
        {
            "id": "pexels2",
            "kind": "image",
            "url": "https://images.pexels.com/photos/358457/pexels-photo-358457.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1",
            "title": "Atardecer",
            "likes": 890,
            "views": "8K"
        }
    ]
    return jsonify(data=sample)

@app.route('/health')
def health():
    return jsonify(status="ok")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
