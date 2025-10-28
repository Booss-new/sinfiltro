const express = require('express');
const path = require('path');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3000;

// --- BASE DE DATOS MOCKUP EN MEMORIA DEL SERVIDOR ---
// Simula datos de contenido para el feed
const serverDataStore = {
    content: Array.from({length: 16}).map((_, i) => ({
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
app.use(cors()); 
app.use(express.json()); 


// --- SERVICIO DEL FRONTEND ---
// Servimos el archivo índice.html cuando se accede a la raíz (/)
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'índice.html')); 
});

// Permitir acceso a otros recursos estáticos (CSS, JS)
app.use(express.static(path.join(__dirname, ''))); 

// --- ENDPOINT DE OBTENCIÓN DEL FEED (API REAL) ---
// La ruta que tu frontend llama con fetch('/api/content/feed/trends')
app.get('/api/content/feed/:type', (req, res) => {
    const type = req.params.type;
    let items;

    switch(type) {
        case 'trends':
            items = serverDataStore.content.slice(0, 8); 
            break;
        case 'reco':
            items = serverDataStore.content.slice(4, 12); 
            break;
        case 'grid':
        case 'recent': 
            items = [...serverDataStore.content].sort(() => 0.5 - Math.random());
            break;
        default:
            items = [];
    }

    res.json({
        success: true,
        data: items
    });
});

// --- INICIAR SERVIDOR ---
app.listen(PORT, () => {
    console.log(`🚀 Servidor Express escuchando en el puerto ${PORT}`);
});
