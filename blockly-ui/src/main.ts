import * as Blockly from 'blockly';
import 'blockly/blocks';
import './style.css';
import { registerBlocks, toolbox } from './blocks/definitions';
import { buildMarloweSpec } from './generator/marlowe';
import { loadMarloweSpec } from './importer/marlowe';
import { saveSpec } from './api/save';
import { PRESET_SPECS, type PresetName } from './templates/presets';

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
      <div class="hint">Timeout expects absolute Unix timestamp in milliseconds.</div>
      <div class="hint">Use a separate Extensions Root block when you need Oracle/ZKP declarations. Contract Root stays pure Marlowe.</div>
      <label>Financial Preset (JSON)</label>
      <select id="preset"></select>
      <button id="btn-load-preset" class="secondary">Load Preset Into Blockly</button>
      <label>Paste JSON</label>
      <textarea id="json-input" spellcheck="false" placeholder='Paste Marlowe JSON or { "contract": ..., "extensions": ... } here'></textarea>
      <input id="json-file" type="file" accept=".json,application/json" class="hidden-file-input" />
      <button id="btn-load-file" class="secondary">Load JSON File</button>
      <button id="btn-load-json" class="secondary">Load JSON Into Blockly</button>
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
const presetEl = document.getElementById('preset') as HTMLSelectElement;
const loadPresetBtn = document.getElementById('btn-load-preset') as HTMLButtonElement;
const jsonInputEl = document.getElementById('json-input') as HTMLTextAreaElement;
const jsonFileEl = document.getElementById('json-file') as HTMLInputElement;
const loadFileBtn = document.getElementById('btn-load-file') as HTMLButtonElement;
const loadJsonBtn = document.getElementById('btn-load-json') as HTMLButtonElement;

const presetNames = Object.keys(PRESET_SPECS) as PresetName[];
for (const name of presetNames) {
  const option = document.createElement('option');
  option.value = name;
  option.textContent = name;
  presetEl.appendChild(option);
}

function setStatus(message: string, isError = false) {
  statusEl.textContent = message;
  statusEl.className = isError ? 'status error' : 'status';
}

function prettyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function syncJsonText(spec: unknown) {
  jsonInputEl.value = prettyJson(spec);
}

function loadSpecIntoWorkspace(spec: unknown, successMessage: string) {
  loadMarloweSpec(workspace, spec);
  syncJsonText(spec);
  generateJson();
  setStatus(successMessage);
}

function generateJson() {
  try {
    const spec = buildMarloweSpec(workspace);
    const pretty = prettyJson(spec);
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

loadPresetBtn.addEventListener('click', () => {
  const presetName = presetEl.value as PresetName;
  const preset = PRESET_SPECS[presetName];
  try {
    const clonedPreset = JSON.parse(JSON.stringify(preset));
    loadSpecIntoWorkspace(clonedPreset, `Preset loaded into Blockly: ${presetName}`);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    setStatus(msg, true);
  }
});

loadFileBtn.addEventListener('click', () => {
  jsonFileEl.click();
});

jsonFileEl.addEventListener('change', async () => {
  const file = jsonFileEl.files?.[0];
  if (!file) {
    return;
  }
  try {
    const text = await file.text();
    const parsed = JSON.parse(text);
    loadSpecIntoWorkspace(parsed, `JSON file loaded into Blockly: ${file.name}`);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    setStatus(msg, true);
  } finally {
    jsonFileEl.value = '';
  }
});

loadJsonBtn.addEventListener('click', () => {
  const raw = jsonInputEl.value.trim();
  if (!raw) {
    setStatus('Paste JSON before loading into Blockly.', true);
    return;
  }
  try {
    const parsed = JSON.parse(raw);
    loadSpecIntoWorkspace(parsed, 'JSON loaded into Blockly.');
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    setStatus(msg, true);
  }
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
