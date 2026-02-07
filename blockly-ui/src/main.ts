import * as Blockly from 'blockly';
import 'blockly/blocks';
import './style.css';
import { registerBlocks, toolbox } from './blocks/definitions';
import { buildMarloweSpec } from './generator/marlowe';
import { saveSpec } from './api/save';

const app = document.getElementById('app');
if (!app) {
  throw new Error('Missing app container');
}

app.innerHTML = `
  <div id="blockly-root"></div>
  <div class="panel">
    <h1>Marlowe Blockly Editor</h1>
    <div class="toolbar">
      <label>Filename (saved into specs/)</label>
      <input id="filename" value="swap_custom.json" />
      <button id="btn-generate" class="secondary">Generate JSON</button>
      <button id="btn-save">Save to specs/</button>
      <div id="status" class="status"></div>
    </div>
    <label>JSON Preview</label>
    <pre id="preview">{}</pre>
  </div>
`;

registerBlocks();

const workspace = Blockly.inject('blockly-root', {
  toolbox,
  scrollbars: true,
  trashcan: true,
  zoom: {
    controls: true,
    wheel: true,
  },
});

const initialState = {
  blocks: {
    languageVersion: 0,
    blocks: [
      {
        type: 'contract_root',
        x: 40,
        y: 40,
      },
    ],
  },
};
Blockly.serialization.workspaces.load(initialState as any, workspace);

const previewEl = document.getElementById('preview') as HTMLPreElement;
const statusEl = document.getElementById('status') as HTMLDivElement;
const filenameEl = document.getElementById('filename') as HTMLInputElement;
const generateBtn = document.getElementById('btn-generate') as HTMLButtonElement;
const saveBtn = document.getElementById('btn-save') as HTMLButtonElement;

function setStatus(message: string, isError = false) {
  statusEl.textContent = message;
  statusEl.className = isError ? 'status error' : 'status';
}

function generateJson() {
  try {
    const spec = buildMarloweSpec(workspace);
    const pretty = JSON.stringify(spec, null, 2);
    previewEl.textContent = pretty;
    setStatus('JSON generated.');
    return spec;
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    setStatus(msg, true);
    previewEl.textContent = '{}';
    return null;
  }
}

workspace.addChangeListener(() => {
  generateJson();
});

generateBtn.addEventListener('click', () => {
  generateJson();
});

saveBtn.addEventListener('click', async () => {
  const spec = generateJson();
  if (!spec) return;
  const filename = filenameEl.value.trim();
  if (!filename) {
    setStatus('Filename is required.', true);
    return;
  }
  try {
    const result = await saveSpec(filename, spec);
    setStatus(`Saved: ${result.path}`);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    setStatus(msg, true);
  }
});
