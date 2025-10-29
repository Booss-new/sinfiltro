// server.js

// Importar el módulo Express
const express = require('express');

// Inicializar la aplicación Express
const app = express();

// Definir el puerto donde escuchará el servidor
// Usa el puerto que te asigne el entorno (ej. Heroku) o por defecto el 3000
const PORT = process.env.PORT || 3000;

// Middleware para servir archivos estáticos
// Esto hace que todo el contenido de la carpeta 'public' sea accesible
// directamente desde la raíz del servidor.
app.use(express.static('public'));

// Ruta principal (opcional, ya que express.static ya maneja el index.html)
// Sirve el archivo index.html si no se encuentra en el middleware anterior
app.get('/', (req, res) => {
    // Si estás usando 'express.static', esta línea puede ser redundante,
    // pero asegura que la página principal se sirva correctamente.
    res.sendFile(__dirname + '/public/index.html');
});

// Iniciar el servidor
app.listen(PORT, () => {
    console.log(`🚀 Servidor corriendo en http://localhost:${PORT}`);
    console.log('¡Listo para servir tu página móvil pro!');
});
