import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs/promises';

const app = express();
const port = 5174;

app.use(cors());
app.use(express.json({ limit: '2mb' }));

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..', '..');
const specsDir = path.join(rootDir, 'specs');

function isSafeFilename(filename: string) {
  if (!filename.endsWith('.json')) return false;
  if (filename.includes('..')) return false;
  if (path.isAbsolute(filename)) return false;
  if (filename !== path.basename(filename)) return false;
  return true;
}

app.post('/save', async (req, res) => {
  try {
    const { filename, content } = req.body ?? {};
    if (typeof filename !== 'string' || !isSafeFilename(filename)) {
      return res.status(400).send('Invalid filename. Must be a simple *.json name.');
    }

    const targetPath = path.join(specsDir, filename);
    let payload: string;

    if (typeof content === 'string') {
      const parsed = JSON.parse(content);
      payload = JSON.stringify(parsed, null, 2);
    } else {
      payload = JSON.stringify(content, null, 2);
    }

    await fs.writeFile(targetPath, payload, 'utf8');
    return res.json({ ok: true, path: targetPath });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return res.status(500).send(msg);
  }
});

app.listen(port, () => {
  console.log(`Save API listening on http://localhost:${port}`);
});
