const express = require('express');
const path = require('path');
const cors = require('cors');
const multer = require('multer'); 
const fs = require('fs'); 

const app = express();
const PORT = process.env.PORT || 3000;

// !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
//  IMPORTANTE: EN RENDER, ESTA CARPETA NO ES PERMANENTE.
//  Los archivos subidos se perderán al reiniciar el servidor.
// !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
const UPLOAD_DIR = path.join(__dirname, 'uploads');
if (!fs.existsSync(UPLOAD_DIR)) {
    fs.mkdirSync(UPLOAD_DIR);
}

const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, UPLOAD_DIR); // Guarda en la carpeta 'uploads'
    },
    filename: (req, file, cb) => {
        // Nombre único: timestamp + nombre original
        cb(null, Date.now() + '-' + file.originalname);
    }
});
const upload = multer({ 
    storage: storage,
    limits: { fileSize: 50 * 1024 * 1024 } // Límite de 50MB (para videos)
});

// --- BASE DE DATOS MOCKUP EN MEMORIA ---
// El SRC de demostración usa Picsum; el KIND es 'video' o 'image'
const serverDataStore = {
    content: Array.from({length: 160}).map((_, i) => ({
        id: 'p' + i,
        src: `https://picsum.photos/640/420?server_demo=${i}`,
        kind: (i % 6 === 0) ? 'video' : 'image',
        title: ['Contenido de Servidor 1', 'Paisaje Único', 'Retrato Premium', 'Arte Digital'][i % 4],
        likes: (Math.floor(Math.random() * 5000) + 100),
        comments: (Math.floor(Math.random() * 500) + 50),
        views: (Math.floor(Math.random() * 50) + 10) + 'K',
        userId: 'u_server'
    })),
};

// Middleware:
// CORS es CRUCIAL para que el frontend de GitHub Pages pueda hablar con el backend de Render
app.use(cors()); 
app.use(express.json()); 
app.use('/uploads', express.static(UPLOAD_DIR)); // Servir archivos subidos

// --- SERVICIO DEL FRONTEND (Para probar en local o si lo sirves todo desde Express) ---
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html')); 
});
app.use(express.static(path.join(__dirname, ''))); 

// --- ENDPOINT DE OBTENCIÓN DEL FEED ---
app.get('/api/content/feed/:type', (req, res) => {
    // Usamos pool de datos grande para las peticiones
    const allContent = [...serverDataStore.content].sort(() => 0.5 - Math.random());
    const type = req.params.type;
    let items;

    // Lógica simple para devolver diferentes secciones (Tendencias, Recomendados, etc.)
    switch(type) {
        case 'trends':
            items = allContent.slice(0, 20); 
            break;
        case 'reco':
            items = allContent.slice(20, 40); 
            break;
        case 'recent': 
            items = allContent; // Pool grande para el grid/reciente
            break;
        default:
            items = [];
    }

    res.json({ success: true, data: items });
});

// --- NUEVO ENDPOINT DE SUBIDA DE ARCHIVOS REAL ---
app.post('/api/content/upload', upload.single('file'), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ success: false, message: 'No se subió ningún archivo.' });
    }
    
    // Obtener la URL base del servidor (necesario para Render o cualquier hosting externo)
    // Esto asegura que la URL sea completa para que el frontend pueda acceder al archivo subido.
    const baseUrl = req.protocol + '://' + req.get('host');

    // Crear el nuevo objeto de contenido
    const newItem = {
        id: Date.now().toString(),
        // SRC: URL COMPLETA para que funcione desde GitHub Pages
        src: `${baseUrl}/uploads/${req.file.filename}`, 
        kind: req.file.mimetype.startsWith('video/') ? 'video' : 'image',
        title: req.body.title || req.file.originalname,
        likes: 0, comments: 0, views: '0K',
        userId: 'u_uploaded'
    };

    // Agregar a la base de datos simulada (al principio para que se vea)
    serverDataStore.content.unshift(newItem); 

    res.json({ 
        success: true, 
        message: 'Archivo subido con éxito', 
        item: newItem 
    });
});

// --- INICIAR SERVIDOR ---
app.listen(PORT, () => {
    console.log(`🚀 Servidor Express escuchando en el puerto ${PORT}`);
});
