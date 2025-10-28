const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');

const app = express();

// Crear carpeta uploads
if (!fs.existsSync('uploads')) fs.mkdirSync('uploads');

// Servir archivos estáticos
app.use(express.static(__dirname));
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

// Subida
const upload = multer({ dest: 'uploads/' });

app.post('/api/content/upload', upload.single('file'), (req, res) => {
  const { title } = req.body;
  const file = req.file;

  const newItem = {
    id: Date.now().toString(),
    src: `/uploads/${file.filename}`,
    kind: file.mimetype.startsWith('video') ? 'video' : 'image',
    title: title || file.originalname.split('.')[0],
    likes: 0,
    comments: 0,
    views: '0K'
  };

  res.json({ success: true, item: newItem });
});

// Feed mock (para que siempre haya contenido)
app.get('/api/content/feed/:type', (req, res) => {
  const { type } = req.params;
  const mock = Array.from({ length: 16 }, (_, i) => ({
    id: `${type}-${Date.now()}-${i}`,
    src: `https://picsum.photos/640/420?random=${i + Date.now()}`,
    kind: i % 5 === 0 ? 'video' : 'image',
    title: `Demo ${type} ${i + 1}`,
    likes: Math.floor(Math.random() * 500),
    comments: Math.floor(Math.random() * 100),
    views: `${Math.floor(Math.random() * 9) + 1}K`
  }));

  res.json({ success: true, data: mock });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Servidor en http://localhost:${PORT}`);
});
