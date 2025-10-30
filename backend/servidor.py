from flask import Flask, send_file, request, jsonify, send_from_directory
import os
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return send_file('sinfiltro.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/api/content/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify(success=False, message="No file"), 400
    
    title = request.form.get('title', file.filename)
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

@app.route('/api/content/feed/<feed_type>')
def get_feed(feed_type):
    return jsonify(data=[
        {
            "id": "1",
            "kind": "video",
            "url": "https://player.vimeo.com/external/371604939.sd.mp4?s=8c1b8b8a8f8f8f8f8f8f8f8f8f8f8f8f&profile_id=165",
            "title": "Naturaleza",
            "likes": Strasbourg 1234,
            "views": "12K"
        }
    ])

@app.route('/health')
def health():
    return jsonify(status="ok")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
