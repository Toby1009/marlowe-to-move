import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs/promises';
import { spawn } from 'child_process';

const app = express();
const port = 5174;

app.use(cors());
app.use(express.json({ limit: '2mb' }));

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..', '..');
const specsDir = path.join(rootDir, 'specs');
const generatorDir = path.join(rootDir, 'generator');
const renderBpmnScript = path.join(generatorDir, 'render_bpmn_payload.py');

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

app.post('/bpmn', async (req, res) => {
  try {
    const { content, processName } = req.body ?? {};
    if (content === undefined) {
      return res.status(400).send('Missing content payload.');
    }

    const py = spawn('python3', [renderBpmnScript], {
      cwd: generatorDir,
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';

    py.stdout.setEncoding('utf8');
    py.stderr.setEncoding('utf8');
    py.stdout.on('data', (chunk) => {
      stdout += chunk;
    });
    py.stderr.on('data', (chunk) => {
      stderr += chunk;
    });

    const exitCode = await new Promise<number>((resolve, reject) => {
      py.on('error', reject);
      py.on('close', resolve);
      py.stdin.end(JSON.stringify({ content, process_name: processName ?? 'Marlowe Contract' }));
    });

    let parsed: any = null;
    if (stdout.trim()) {
      parsed = JSON.parse(stdout);
    }

    if (exitCode !== 0 || !parsed?.ok) {
      const errorMessage =
        parsed?.error ||
        stderr.trim() ||
        `BPMN generation failed with exit code ${exitCode}`;
      return res.status(500).send(errorMessage);
    }

    return res.json(parsed);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return res.status(500).send(msg);
  }
});

app.listen(port, () => {
  console.log(`Save API listening on http://localhost:${port}`);
});
