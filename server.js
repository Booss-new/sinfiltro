const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');

const app = express();
const upload = multer({ dest: 'uploads/' });

app.use(express.static('.'));
app.use('/uploads', express.static('uploads'));

app.post('/api/content/upload', upload.single('file'), (req, res) => {
  const { file, body: { title } } = req;
  const ext = path.extname(file.originalname);
  const newPath = `uploads/${Date.now()}-${Math.random().toString(36).substr(2, 9)}${ext}`;
  fs.renameSync(file.path, newPath);
  res.json({
    success: true,
    item: {
      id: `upload-${Date.now()}`,
      kind: file.mimetype.startsWith('video') ? 'video' : 'image',
      src: `/${newPath}`,
      title: title || file.originalname,
      likes: 0,
      comments: 0,
      views: '0K'
    }
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server en http://localhost:${PORT}`));
