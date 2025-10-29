const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');

const app = express();
const PORT = process.env.PORT || 3000;

// Configuración de almacenamiento
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = 'uploads/';
    if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir);
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname);
    cb(null, `${uuidv4()}${ext}`);
  }
});
const upload = multer({ storage });

// Servir estáticos
app.use(express.static(__dirname));
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

// Base de datos en memoria (simulada)
let contentDB = {
  trends: [],
  reco: [],
  recent: []
};

// --- API: Obtener feed ---
app.get('/api/content/feed/:type', (req, res) => {
  const type = req.params.type;
  const data = contentDB[type] || [];
  res.json({ success: true, data });
});

// --- API: Subir archivo ---
app.post('/api/content/upload', upload.single('file'), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ success: false, message: 'No file uploaded' });
  }

  const { title = 'Sin título' } = req.body;
  // 💥 MODIFICACIÓN CLAVE AQUÍ: Usar solo la ruta relativa
  const fileUrl = `/uploads/${req.file.filename}`;
  // 💥 (Antes: const fileUrl = `${req.protocol}://${req.get('host')}/uploads/${req.file.filename}`;)

  const isVideo = req.file.mimetype.startsWith('video/');

  const newItem = {
    id: uuidv4(),
    src: fileUrl, // Ahora src es /uploads/nombre-de-archivo.ext
    kind: isVideo ? 'video' : 'image',
    title: title,
    likes: 0,
    comments: 0,
    views: '0K',
    uploadedAt: new Date().toISOString()
  };

  // Añadir a todas las secciones
  contentDB.trends.unshift(newItem);
  contentDB.reco.unshift(newItem);
  contentDB.recent.unshift(newItem);

  // Limitar a 50 por sección
  Object.keys(contentDB).forEach(key => {
    if (contentDB[key].length > 50) contentDB[key].pop();
  });

  res.json({ success: true, item: newItem });
});

// --- Ruta principal ---
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`SinFiltro corriendo en http://localhost:${PORT}`);
  console.log(`Deploy en Render: OK`);
});
