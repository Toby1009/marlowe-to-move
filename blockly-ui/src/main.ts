import * as Blockly from 'blockly';
import 'blockly/blocks';
import './style.css';
import { registerBlocks, toolbox } from './blocks/definitions';
import { buildContractSpec } from './generator/marlowe';
import { loadMarloweSpec } from './importer/marlowe';
import { saveSpec } from './api/save';
import { generateBpmn, type BpmnResult } from './api/bpmn';
import { PRESET_SPECS, type PresetName } from './templates/presets';

type BindingKind = 'choice' | 'observation' | 'choice_or_notify';

type OracleRequirementForm = {
  id: string;
  type: string;
  description: string;
  pair: string;
  feedKey: string;
  timestamp: string;
  maxStalenessSec: string;
  sourceChain: string;
  signedBy: string;
  signatureScheme: string;
  requiredQuorum: string;
  bindKind: BindingKind;
  bindName: string;
};

type ZkpRequirementForm = {
  id: string;
  proofSystem: string;
  statement: string;
  publicInputs: string;
  verifierChain: string;
  verifierModule: string;
  verifierFunction: string;
  bindKind: BindingKind;
  bindName: string;
  reveals: string;
  hides: string;
};

type ExtensionsState = {
  oracles: OracleRequirementForm[];
  zkp: ZkpRequirementForm[];
};

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
      <div class="hint">Oracle and ZKP requirements live in the form below. Contract Root stays pure Marlowe.</div>
      <label>Financial Preset (JSON)</label>
      <select id="preset"></select>
      <button id="btn-load-preset" class="secondary">Load Preset Into Blockly</button>
      <label>Paste JSON</label>
      <textarea id="json-input" spellcheck="false" placeholder='Paste Marlowe JSON or { "contract": ..., "extensions": ... } here'></textarea>
      <input id="json-file" type="file" accept=".json,application/json" class="hidden-file-input" />
      <button id="btn-load-file" class="secondary">Load JSON File</button>
      <button id="btn-load-json" class="secondary">Load JSON Into Blockly</button>
      <button id="btn-generate" class="secondary">Generate JSON</button>
      <button id="btn-generate-bpmn" class="secondary">Generate BPMN</button>
      <button id="btn-save">Save to specs/</button>
      <div id="status" class="status"></div>
    </div>
    <div class="extensions-panel">
      <div class="extension-section">
        <div class="section-header">
          <div>
            <h2>Oracle Requirements</h2>
            <div class="hint">Binds external oracle inputs to a contract-facing ChoiceId.</div>
          </div>
          <button id="btn-add-oracle" class="secondary" type="button">Add Oracle</button>
        </div>
        <div id="oracle-list" class="extension-list"></div>
      </div>
      <div class="extension-section">
        <div class="section-header">
          <div>
            <h2>ZKP Requirements</h2>
            <div class="hint">Declares proof system, verifier hook, privacy, and contract binding.</div>
          </div>
          <button id="btn-add-zkp" class="secondary" type="button">Add ZKP</button>
        </div>
        <div id="zkp-list" class="extension-list"></div>
      </div>
    </div>
    <div class="result-tabs">
      <button id="tab-json" class="tab-button active">JSON</button>
      <button id="tab-bpmn-diagram" class="tab-button">BPMN Diagram</button>
      <button id="tab-bpmn-xml" class="tab-button">BPMN XML</button>
    </div>
    <div id="panel-json" class="result-panel active">
      <label>JSON Preview</label>
      <pre id="preview">{}</pre>
    </div>
    <div id="panel-bpmn-diagram" class="result-panel">
      <div class="bpmn-toolbar">
        <a id="download-bpmn" class="download-link hidden" download="contract.bpmn">Download .bpmn</a>
        <a id="download-svg" class="download-link hidden" download="contract.svg">Download .svg</a>
        <div class="bpmn-zoom-controls">
          <button id="btn-bpmn-zoom-out" class="secondary" type="button" aria-label="Zoom out BPMN">-</button>
          <button id="btn-bpmn-zoom-reset" class="secondary" type="button">100%</button>
          <button id="btn-bpmn-zoom-in" class="secondary" type="button" aria-label="Zoom in BPMN">+</button>
          <span id="bpmn-zoom-label" class="bpmn-zoom-label">100%</span>
        </div>
      </div>
      <div id="bpmn-meta" class="hint">Generate BPMN to preview the flow diagram.</div>
      <div id="bpmn-diagram" class="bpmn-diagram empty">No BPMN generated yet.</div>
    </div>
    <div id="panel-bpmn-xml" class="result-panel">
      <label>BPMN XML</label>
      <pre id="bpmn-xml-preview"></pre>
    </div>
  </div>
  <div id="bpmn-lightbox" class="bpmn-lightbox hidden">
    <div id="bpmn-lightbox-backdrop" class="bpmn-lightbox-backdrop">
      <div id="bpmn-lightbox-content" class="bpmn-lightbox-content">
        <div class="bpmn-lightbox-toolbar">
          <div class="bpmn-lightbox-hint">Click outside the diagram to close</div>
          <div class="bpmn-zoom-controls">
            <button id="btn-bpmn-lightbox-zoom-out" class="secondary" type="button" aria-label="Zoom out BPMN">-</button>
            <button id="btn-bpmn-lightbox-zoom-reset" class="secondary" type="button">100%</button>
            <button id="btn-bpmn-lightbox-zoom-in" class="secondary" type="button" aria-label="Zoom in BPMN">+</button>
            <span id="bpmn-lightbox-zoom-label" class="bpmn-zoom-label">100%</span>
          </div>
        </div>
        <div id="bpmn-lightbox-diagram" class="bpmn-lightbox-diagram"></div>
      </div>
    </div>
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
const generateBpmnBtn = document.getElementById('btn-generate-bpmn') as HTMLButtonElement;
const saveBtn = document.getElementById('btn-save') as HTMLButtonElement;
const presetEl = document.getElementById('preset') as HTMLSelectElement;
const loadPresetBtn = document.getElementById('btn-load-preset') as HTMLButtonElement;
const jsonInputEl = document.getElementById('json-input') as HTMLTextAreaElement;
const jsonFileEl = document.getElementById('json-file') as HTMLInputElement;
const loadFileBtn = document.getElementById('btn-load-file') as HTMLButtonElement;
const loadJsonBtn = document.getElementById('btn-load-json') as HTMLButtonElement;
const addOracleBtn = document.getElementById('btn-add-oracle') as HTMLButtonElement;
const addZkpBtn = document.getElementById('btn-add-zkp') as HTMLButtonElement;
const oracleListEl = document.getElementById('oracle-list') as HTMLDivElement;
const zkpListEl = document.getElementById('zkp-list') as HTMLDivElement;
const bpmnDiagramEl = document.getElementById('bpmn-diagram') as HTMLDivElement;
const bpmnMetaEl = document.getElementById('bpmn-meta') as HTMLDivElement;
const bpmnXmlPreviewEl = document.getElementById('bpmn-xml-preview') as HTMLPreElement;
const downloadBpmnEl = document.getElementById('download-bpmn') as HTMLAnchorElement;
const downloadSvgEl = document.getElementById('download-svg') as HTMLAnchorElement;
const bpmnZoomOutEl = document.getElementById('btn-bpmn-zoom-out') as HTMLButtonElement;
const bpmnZoomResetEl = document.getElementById('btn-bpmn-zoom-reset') as HTMLButtonElement;
const bpmnZoomInEl = document.getElementById('btn-bpmn-zoom-in') as HTMLButtonElement;
const bpmnZoomLabelEl = document.getElementById('bpmn-zoom-label') as HTMLSpanElement;
const tabJsonEl = document.getElementById('tab-json') as HTMLButtonElement;
const tabBpmnDiagramEl = document.getElementById('tab-bpmn-diagram') as HTMLButtonElement;
const tabBpmnXmlEl = document.getElementById('tab-bpmn-xml') as HTMLButtonElement;
const panelJsonEl = document.getElementById('panel-json') as HTMLDivElement;
const panelBpmnDiagramEl = document.getElementById('panel-bpmn-diagram') as HTMLDivElement;
const panelBpmnXmlEl = document.getElementById('panel-bpmn-xml') as HTMLDivElement;
const bpmnLightboxEl = document.getElementById('bpmn-lightbox') as HTMLDivElement;
const bpmnLightboxBackdropEl = document.getElementById('bpmn-lightbox-backdrop') as HTMLDivElement;
const bpmnLightboxContentEl = document.getElementById('bpmn-lightbox-content') as HTMLDivElement;
const bpmnLightboxDiagramEl = document.getElementById('bpmn-lightbox-diagram') as HTMLDivElement;
const bpmnLightboxZoomOutEl = document.getElementById('btn-bpmn-lightbox-zoom-out') as HTMLButtonElement;
const bpmnLightboxZoomResetEl = document.getElementById('btn-bpmn-lightbox-zoom-reset') as HTMLButtonElement;
const bpmnLightboxZoomInEl = document.getElementById('btn-bpmn-lightbox-zoom-in') as HTMLButtonElement;
const bpmnLightboxZoomLabelEl = document.getElementById('bpmn-lightbox-zoom-label') as HTMLSpanElement;

let bpmnBlobUrls: string[] = [];
let extensionsState: ExtensionsState = emptyExtensionsState();
let currentSpecCacheKey = '';
let lastGeneratedBpmnCacheKey = '';
let lastGeneratedBpmnProcessName = '';
let lastGeneratedBpmnResult: BpmnResult | null = null;
let bpmnZoom = 1;

const BPMN_ZOOM_MIN = 0.5;
const BPMN_ZOOM_MAX = 2.5;
const BPMN_ZOOM_STEP = 0.1;

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

function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function emptyExtensionsState(): ExtensionsState {
  return { oracles: [], zkp: [] };
}

function defaultOracleRequirement(): OracleRequirementForm {
  return {
    id: 'fx_usdc_twd',
    type: 'price_feed',
    description: 'USDC/TWD exchange rate',
    pair: 'USDC/TWD',
    feedKey: 'chainlink.fx.usdc_twd',
    timestamp: 'tx_time',
    maxStalenessSec: '3600',
    sourceChain: 'ethereum',
    signedBy: 'OracleProviderA',
    signatureScheme: 'ed25519',
    requiredQuorum: '1',
    bindKind: 'choice',
    bindName: '',
  };
}

function defaultZkpRequirement(): ZkpRequirementForm {
  return {
    id: 'eligibility_proof',
    proofSystem: 'groth16',
    statement: 'Applicant is eligible for the grant',
    publicInputs: 'applicant_id_hash,policy_id',
    verifierChain: 'sui',
    verifierModule: 'zk_verifier',
    verifierFunction: 'verify_eligibility',
    bindKind: 'choice',
    bindName: '',
    reveals: 'eligible_only',
    hides: 'income,full_identity',
  };
}

function splitCsv(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function csvText(value: unknown): string {
  if (!Array.isArray(value)) {
    return '';
  }
  return value.map((item) => String(item)).join(',');
}

function normalizeExtensions(extensions: unknown): ExtensionsState {
  if (!isRecord(extensions)) {
    return emptyExtensionsState();
  }
  const oracles = Array.isArray(extensions.oracles)
    ? extensions.oracles.map((item) => normalizeOracleRequirement(item))
    : [];
  const zkp = Array.isArray(extensions.zkp)
    ? extensions.zkp.map((item) => normalizeZkpRequirement(item))
    : [];
  return { oracles, zkp };
}

function normalizeOracleRequirement(value: unknown): OracleRequirementForm {
  const item = isRecord(value) ? value : {};
  const inputs = isRecord(item.inputs) ? item.inputs : {};
  const integrity = isRecord(item.integrity) ? item.integrity : {};
  const bindTo = isRecord(item.bind_to) ? item.bind_to : {};
  return {
    id: stringValue(item.id, defaultOracleRequirement().id),
    type: stringValue(item.type, defaultOracleRequirement().type),
    description: stringValue(item.description, defaultOracleRequirement().description),
    pair: stringValue(inputs.pair, ''),
    feedKey: stringValue(inputs.feed_key, ''),
    timestamp: stringValue(inputs.timestamp, defaultOracleRequirement().timestamp),
    maxStalenessSec: stringValue(inputs.max_staleness_sec, defaultOracleRequirement().maxStalenessSec),
    sourceChain: stringValue(inputs.source_chain, ''),
    signedBy: csvText(integrity.signed_by) || defaultOracleRequirement().signedBy,
    signatureScheme: stringValue(integrity.signature_scheme, defaultOracleRequirement().signatureScheme),
    requiredQuorum: stringValue(integrity.required_quorum, defaultOracleRequirement().requiredQuorum),
    bindKind: bindingKindValue(bindTo.kind, 'choice'),
    bindName: stringValue(bindTo.name, ''),
  };
}

function normalizeZkpRequirement(value: unknown): ZkpRequirementForm {
  const item = isRecord(value) ? value : {};
  const verifier = isRecord(item.verifier) ? item.verifier : {};
  const bindTo = isRecord(item.bind_to) ? item.bind_to : {};
  const privacy = isRecord(item.privacy) ? item.privacy : {};
  return {
    id: stringValue(item.id, defaultZkpRequirement().id),
    proofSystem: stringValue(item.proof_system, defaultZkpRequirement().proofSystem),
    statement: stringValue(item.statement, defaultZkpRequirement().statement),
    publicInputs: csvText(item.public_inputs) || defaultZkpRequirement().publicInputs,
    verifierChain: stringValue(verifier.chain, defaultZkpRequirement().verifierChain),
    verifierModule: stringValue(verifier.module, defaultZkpRequirement().verifierModule),
    verifierFunction: stringValue(verifier.function, defaultZkpRequirement().verifierFunction),
    bindKind: bindingKindValue(bindTo.kind, 'choice'),
    bindName: stringValue(bindTo.name, ''),
    reveals: csvText(privacy.reveals),
    hides: csvText(privacy.hides),
  };
}

function stringValue(value: unknown, fallback = ''): string {
  if (value === undefined || value === null) {
    return fallback;
  }
  return String(value);
}

function bindingKindValue(value: unknown, fallback: BindingKind): BindingKind {
  if (value === 'choice' || value === 'observation' || value === 'choice_or_notify') {
    return value;
  }
  return fallback;
}

function isRecord(value: unknown): value is Record<string, any> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function clearBlobUrls() {
  for (const url of bpmnBlobUrls) {
    URL.revokeObjectURL(url);
  }
  bpmnBlobUrls = [];
}

function getBpmnSvg(container: HTMLElement): SVGSVGElement | null {
  return container.querySelector('svg');
}

function hasBpmnSvg() {
  return getBpmnSvg(bpmnDiagramEl) !== null;
}

function clampBpmnZoom(value: number) {
  return Math.min(BPMN_ZOOM_MAX, Math.max(BPMN_ZOOM_MIN, value));
}

function ensureBpmnSvgBaseSize(svg: SVGSVGElement) {
  if (svg.dataset.baseWidth && svg.dataset.baseHeight) {
    return;
  }

  const widthAttr = Number(svg.getAttribute('width'));
  const heightAttr = Number(svg.getAttribute('height'));
  const viewBox = svg.viewBox.baseVal;
  const baseWidth = Number.isFinite(widthAttr) && widthAttr > 0 ? widthAttr : viewBox?.width || 0;
  const baseHeight = Number.isFinite(heightAttr) && heightAttr > 0 ? heightAttr : viewBox?.height || 0;

  if (baseWidth > 0) {
    svg.dataset.baseWidth = String(baseWidth);
  }
  if (baseHeight > 0) {
    svg.dataset.baseHeight = String(baseHeight);
  }
}

function applyZoomToContainer(container: HTMLElement) {
  const svg = getBpmnSvg(container);
  if (!svg) {
    return;
  }

  ensureBpmnSvgBaseSize(svg);
  const baseWidth = Number(svg.dataset.baseWidth);
  const baseHeight = Number(svg.dataset.baseHeight);

  if (baseWidth > 0) {
    svg.style.width = `${Math.round(baseWidth * bpmnZoom)}px`;
  }
  if (baseHeight > 0) {
    svg.style.height = `${Math.round(baseHeight * bpmnZoom)}px`;
  }
}

function syncBpmnZoomUi() {
  const percent = `${Math.round(bpmnZoom * 100)}%`;
  bpmnZoomLabelEl.textContent = percent;
  bpmnLightboxZoomLabelEl.textContent = percent;

  const disabled = !hasBpmnSvg();
  for (const button of [
    bpmnZoomOutEl,
    bpmnZoomResetEl,
    bpmnZoomInEl,
    bpmnLightboxZoomOutEl,
    bpmnLightboxZoomResetEl,
    bpmnLightboxZoomInEl,
  ]) {
    button.disabled = disabled;
  }
}

function renderBpmnZoom() {
  applyZoomToContainer(bpmnDiagramEl);
  applyZoomToContainer(bpmnLightboxDiagramEl);
  syncBpmnZoomUi();
}

function setBpmnZoom(nextZoom: number) {
  bpmnZoom = clampBpmnZoom(nextZoom);
  renderBpmnZoom();
}

function adjustBpmnZoom(delta: number) {
  setBpmnZoom(Number((bpmnZoom + delta).toFixed(2)));
}

function setActiveTab(tab: 'json' | 'bpmn-diagram' | 'bpmn-xml') {
  const mapping = [
    [tabJsonEl, panelJsonEl, 'json'],
    [tabBpmnDiagramEl, panelBpmnDiagramEl, 'bpmn-diagram'],
    [tabBpmnXmlEl, panelBpmnXmlEl, 'bpmn-xml'],
  ] as const;
  for (const [button, panel, key] of mapping) {
    const active = key === tab;
    button.classList.toggle('active', active);
    panel.classList.toggle('active', active);
  }
}

function closeBpmnLightbox() {
  bpmnLightboxEl.classList.add('hidden');
  bpmnLightboxDiagramEl.innerHTML = '';
}

function openBpmnLightbox() {
  if (bpmnDiagramEl.classList.contains('empty') || !bpmnDiagramEl.innerHTML.trim()) {
    return;
  }
  bpmnLightboxDiagramEl.innerHTML = bpmnDiagramEl.innerHTML;
  renderBpmnZoom();
  bpmnLightboxEl.classList.remove('hidden');
}

function invalidateBpmn(message = 'BPMN preview is stale. Generate BPMN again.') {
  closeBpmnLightbox();
  clearBlobUrls();
  bpmnDiagramEl.innerHTML = '';
  bpmnDiagramEl.textContent = 'No BPMN generated yet.';
  bpmnDiagramEl.classList.add('empty');
  bpmnXmlPreviewEl.textContent = '';
  bpmnMetaEl.textContent = message;
  downloadBpmnEl.classList.add('hidden');
  downloadSvgEl.classList.add('hidden');
  downloadBpmnEl.removeAttribute('href');
  downloadSvgEl.removeAttribute('href');
  lastGeneratedBpmnResult = null;
  lastGeneratedBpmnCacheKey = '';
  lastGeneratedBpmnProcessName = '';
  syncBpmnZoomUi();
}

function syncJsonText(spec: unknown) {
  jsonInputEl.value = prettyJson(spec);
}

function collectChoiceNames(): string[] {
  const names = new Set<string>();
  for (const block of workspace.getAllBlocks(false)) {
    if (block.type !== 'choice_id') {
      continue;
    }
    const name = String(block.getFieldValue('NAME') ?? '').trim();
    if (name) {
      names.add(name);
    }
  }
  return Array.from(names).sort((lhs, rhs) => lhs.localeCompare(rhs));
}

function optionHtml(value: string, label: string, selectedValue: string): string {
  const selected = value === selectedValue ? ' selected' : '';
  return `<option value="${escapeHtml(value)}"${selected}>${escapeHtml(label)}</option>`;
}

function bindNameOptionsHtml(selectedValue: string): string {
  const names = collectChoiceNames();
  const options = [...names];
  if (selectedValue && !options.includes(selectedValue)) {
    options.unshift(selectedValue);
  }
  if (options.length === 0) {
    return '<option value="">Define ChoiceId in Contract Root first</option>';
  }
  return [
    '<option value="">Select contract ChoiceId</option>',
    ...options.map((name) => optionHtml(name, name, selectedValue)),
  ].join('');
}

function bindKindOptionsHtml(selectedValue: BindingKind): string {
  return [
    optionHtml('choice', 'choice', selectedValue),
    optionHtml('observation', 'observation', selectedValue),
    optionHtml('choice_or_notify', 'choice_or_notify', selectedValue),
  ].join('');
}

function oracleTypeOptionsHtml(selectedValue: string): string {
  return [
    optionHtml('price_feed', 'price_feed', selectedValue),
    optionHtml('attestation', 'attestation', selectedValue),
    optionHtml('cross_chain_message', 'cross_chain_message', selectedValue),
    optionHtml('custom', 'custom', selectedValue),
  ].join('');
}

function proofSystemOptionsHtml(selectedValue: string): string {
  return [
    optionHtml('groth16', 'groth16', selectedValue),
    optionHtml('plonk', 'plonk', selectedValue),
    optionHtml('halo2', 'halo2', selectedValue),
    optionHtml('custom', 'custom', selectedValue),
  ].join('');
}

function renderExtensionsForms() {
  oracleListEl.innerHTML =
    extensionsState.oracles.length > 0
      ? extensionsState.oracles.map((item, index) => renderOracleCard(item, index)).join('')
      : '<div class="extension-empty">No Oracle requirements yet.</div>';
  zkpListEl.innerHTML =
    extensionsState.zkp.length > 0
      ? extensionsState.zkp.map((item, index) => renderZkpCard(item, index)).join('')
      : '<div class="extension-empty">No ZKP requirements yet.</div>';
}

function renderOracleCard(item: OracleRequirementForm, index: number): string {
  return `
    <div class="extension-card" data-kind="oracle" data-index="${index}">
      <div class="extension-card-header">
        <strong>Oracle ${index + 1}</strong>
        <button type="button" class="danger-button" data-action="remove">Remove</button>
      </div>
      <div class="extension-grid">
        <label>Id<input data-field="id" value="${escapeHtml(item.id)}" /></label>
        <label>Type<select data-field="type">${oracleTypeOptionsHtml(item.type)}</select></label>
        <label class="span-2">Description<input data-field="description" value="${escapeHtml(item.description)}" /></label>
        <label>Pair<input data-field="pair" value="${escapeHtml(item.pair)}" /></label>
        <label>Feed Key<input data-field="feedKey" value="${escapeHtml(item.feedKey)}" /></label>
        <label>Timestamp<input data-field="timestamp" value="${escapeHtml(item.timestamp)}" /></label>
        <label>Max Staleness Sec<input data-field="maxStalenessSec" type="number" min="0" value="${escapeHtml(item.maxStalenessSec)}" /></label>
        <label>Source Chain<input data-field="sourceChain" value="${escapeHtml(item.sourceChain)}" /></label>
        <label>Signed By<input data-field="signedBy" value="${escapeHtml(item.signedBy)}" /></label>
        <label>Scheme<input data-field="signatureScheme" value="${escapeHtml(item.signatureScheme)}" /></label>
        <label>Quorum<input data-field="requiredQuorum" type="number" min="1" value="${escapeHtml(item.requiredQuorum)}" /></label>
        <label>Bind Kind<select data-field="bindKind">${bindKindOptionsHtml(item.bindKind)}</select></label>
        <label>Bind Name<select data-field="bindName">${bindNameOptionsHtml(item.bindName)}</select></label>
      </div>
    </div>
  `;
}

function renderZkpCard(item: ZkpRequirementForm, index: number): string {
  return `
    <div class="extension-card" data-kind="zkp" data-index="${index}">
      <div class="extension-card-header">
        <strong>ZKP ${index + 1}</strong>
        <button type="button" class="danger-button" data-action="remove">Remove</button>
      </div>
      <div class="extension-grid">
        <label>Id<input data-field="id" value="${escapeHtml(item.id)}" /></label>
        <label>Proof System<select data-field="proofSystem">${proofSystemOptionsHtml(item.proofSystem)}</select></label>
        <label class="span-2">Statement<input data-field="statement" value="${escapeHtml(item.statement)}" /></label>
        <label class="span-2">Public Inputs<input data-field="publicInputs" value="${escapeHtml(item.publicInputs)}" /></label>
        <label>Verifier Chain<input data-field="verifierChain" value="${escapeHtml(item.verifierChain)}" /></label>
        <label>Verifier Module<input data-field="verifierModule" value="${escapeHtml(item.verifierModule)}" /></label>
        <label>Verifier Function<input data-field="verifierFunction" value="${escapeHtml(item.verifierFunction)}" /></label>
        <label>Bind Kind<select data-field="bindKind">${bindKindOptionsHtml(item.bindKind)}</select></label>
        <label>Bind Name<select data-field="bindName">${bindNameOptionsHtml(item.bindName)}</select></label>
        <label>Reveals<input data-field="reveals" value="${escapeHtml(item.reveals)}" /></label>
        <label>Hides<input data-field="hides" value="${escapeHtml(item.hides)}" /></label>
      </div>
    </div>
  `;
}

function syncExtensionsStateFromDom() {
  extensionsState = {
    oracles: Array.from(oracleListEl.querySelectorAll<HTMLElement>('.extension-card')).map((card) =>
      readOracleCard(card)
    ),
    zkp: Array.from(zkpListEl.querySelectorAll<HTMLElement>('.extension-card')).map((card) => readZkpCard(card)),
  };
}

function readValue(card: HTMLElement, field: string): string {
  const el = card.querySelector<HTMLInputElement | HTMLSelectElement>(`[data-field="${field}"]`);
  return el?.value.trim() ?? '';
}

function readOracleCard(card: HTMLElement): OracleRequirementForm {
  return {
    id: readValue(card, 'id'),
    type: readValue(card, 'type'),
    description: readValue(card, 'description'),
    pair: readValue(card, 'pair'),
    feedKey: readValue(card, 'feedKey'),
    timestamp: readValue(card, 'timestamp'),
    maxStalenessSec: readValue(card, 'maxStalenessSec'),
    sourceChain: readValue(card, 'sourceChain'),
    signedBy: readValue(card, 'signedBy'),
    signatureScheme: readValue(card, 'signatureScheme'),
    requiredQuorum: readValue(card, 'requiredQuorum'),
    bindKind: bindingKindValue(readValue(card, 'bindKind'), 'choice'),
    bindName: readValue(card, 'bindName'),
  };
}

function readZkpCard(card: HTMLElement): ZkpRequirementForm {
  return {
    id: readValue(card, 'id'),
    proofSystem: readValue(card, 'proofSystem'),
    statement: readValue(card, 'statement'),
    publicInputs: readValue(card, 'publicInputs'),
    verifierChain: readValue(card, 'verifierChain'),
    verifierModule: readValue(card, 'verifierModule'),
    verifierFunction: readValue(card, 'verifierFunction'),
    bindKind: bindingKindValue(readValue(card, 'bindKind'), 'choice'),
    bindName: readValue(card, 'bindName'),
    reveals: readValue(card, 'reveals'),
    hides: readValue(card, 'hides'),
  };
}

function setExtensionsState(state: ExtensionsState) {
  extensionsState = state;
  renderExtensionsForms();
}

function requireText(value: string, label: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    throw new Error(`${label} is required.`);
  }
  return trimmed;
}

function requirePositiveInteger(value: string, label: string, minValue = 0): number {
  const number = Number(value);
  if (!Number.isInteger(number) || number < minValue) {
    throw new Error(`${label} must be an integer >= ${minValue}.`);
  }
  return number;
}

function buildExtensionsPayload(): Record<string, unknown> | null {
  syncExtensionsStateFromDom();

  const oracles = extensionsState.oracles.map((item, index) => {
    const prefix = `Oracle ${index + 1}`;
    return {
      id: requireText(item.id, `${prefix} id`),
      type: requireText(item.type, `${prefix} type`),
      description: requireText(item.description, `${prefix} description`),
      inputs: {
        ...(item.pair ? { pair: item.pair } : {}),
        ...(item.feedKey ? { feed_key: item.feedKey } : {}),
        timestamp: requireText(item.timestamp, `${prefix} timestamp`),
        max_staleness_sec: requirePositiveInteger(item.maxStalenessSec || '0', `${prefix} max staleness sec`, 0),
        ...(item.sourceChain ? { source_chain: item.sourceChain } : {}),
      },
      integrity: {
        signed_by: splitCsv(requireText(item.signedBy, `${prefix} signed_by`)),
        signature_scheme: requireText(item.signatureScheme, `${prefix} signature scheme`),
        required_quorum: requirePositiveInteger(item.requiredQuorum || '1', `${prefix} quorum`, 1),
      },
      bind_to: {
        kind: item.bindKind,
        name: requireText(item.bindName, `${prefix} bind name`),
      },
    };
  });

  const zkp = extensionsState.zkp.map((item, index) => {
    const prefix = `ZKP ${index + 1}`;
    return {
      id: requireText(item.id, `${prefix} id`),
      statement: requireText(item.statement, `${prefix} statement`),
      public_inputs: splitCsv(requireText(item.publicInputs, `${prefix} public inputs`)),
      proof_system: requireText(item.proofSystem, `${prefix} proof system`),
      verifier: {
        chain: requireText(item.verifierChain, `${prefix} verifier chain`),
        module: requireText(item.verifierModule, `${prefix} verifier module`),
        function: requireText(item.verifierFunction, `${prefix} verifier function`),
      },
      bind_to: {
        kind: item.bindKind,
        name: requireText(item.bindName, `${prefix} bind name`),
      },
      privacy: {
        reveals: splitCsv(item.reveals),
        hides: splitCsv(item.hides),
      },
    };
  });

  if (oracles.length === 0 && zkp.length === 0) {
    return null;
  }

  const payload: Record<string, unknown> = {};
  if (oracles.length > 0) {
    payload.oracles = oracles;
  }
  if (zkp.length > 0) {
    payload.zkp = zkp;
  }
  return payload;
}

function buildFullSpec(): unknown {
  const contract = buildContractSpec(workspace);
  const extensions = buildExtensionsPayload();
  if (!extensions) {
    return contract;
  }
  return { contract, extensions };
}

function loadSpecIntoWorkspace(spec: unknown, successMessage: string) {
  const envelope = loadMarloweSpec(workspace, spec);
  setExtensionsState(normalizeExtensions(envelope.extensions));
  syncJsonText(spec);
  generateJson();
  setStatus(successMessage);
}

function generateJson() {
  try {
    const spec = buildFullSpec();
    const pretty = prettyJson(spec);
    const previousSpecCacheKey = currentSpecCacheKey;
    currentSpecCacheKey = pretty;
    if (previousSpecCacheKey && previousSpecCacheKey !== currentSpecCacheKey) {
      invalidateBpmn();
    }
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

function buildProcessName(filename: string, fallback = 'Marlowe Contract') {
  const trimmed = filename.trim();
  if (!trimmed) {
    return fallback;
  }
  return trimmed.replace(/\.json$/i, '');
}

function applyBpmnResult(result: BpmnResult, processName: string) {
  clearBlobUrls();
  bpmnDiagramEl.innerHTML = result.svg;
  bpmnDiagramEl.classList.remove('empty');
  bpmnXmlPreviewEl.textContent = result.bpmn_xml;
  if (!bpmnLightboxEl.classList.contains('hidden')) {
    bpmnLightboxDiagramEl.innerHTML = result.svg;
  }
  renderBpmnZoom();

  const warnings = result.warnings.length > 0 ? ` Warnings: ${result.warnings.join(' | ')}` : '';
  bpmnMetaEl.textContent = result.valid
    ? `BPMN generated for ${processName}.${warnings}`.trim()
    : `BPMN generated with validation errors: ${result.errors.join(' | ')}${warnings}`;

  const bpmnUrl = URL.createObjectURL(new Blob([result.bpmn_xml], { type: 'application/xml' }));
  const svgUrl = URL.createObjectURL(new Blob([result.svg], { type: 'image/svg+xml' }));
  bpmnBlobUrls = [bpmnUrl, svgUrl];

  downloadBpmnEl.href = bpmnUrl;
  downloadBpmnEl.download = `${processName}.bpmn`;
  downloadBpmnEl.classList.remove('hidden');

  downloadSvgEl.href = svgUrl;
  downloadSvgEl.download = `${processName}.svg`;
  downloadSvgEl.classList.remove('hidden');

  lastGeneratedBpmnResult = result;
  lastGeneratedBpmnCacheKey = currentSpecCacheKey;
  lastGeneratedBpmnProcessName = processName;
}

function handleExtensionMutation() {
  generateJson();
}

workspace.addChangeListener(() => {
  syncExtensionsStateFromDom();
  renderExtensionsForms();
  generateJson();
});

oracleListEl.addEventListener('input', handleExtensionMutation);
oracleListEl.addEventListener('change', handleExtensionMutation);
zkpListEl.addEventListener('input', handleExtensionMutation);
zkpListEl.addEventListener('change', handleExtensionMutation);

oracleListEl.addEventListener('click', (event) => {
  const target = event.target as HTMLElement;
  if (target.dataset.action !== 'remove') {
    return;
  }
  syncExtensionsStateFromDom();
  const card = target.closest<HTMLElement>('.extension-card');
  const index = Number(card?.dataset.index ?? '-1');
  if (index >= 0) {
    extensionsState.oracles.splice(index, 1);
    renderExtensionsForms();
    handleExtensionMutation();
  }
});

bpmnDiagramEl.addEventListener('click', () => {
  openBpmnLightbox();
});

for (const button of [bpmnZoomOutEl, bpmnLightboxZoomOutEl]) {
  button.addEventListener('click', () => {
    adjustBpmnZoom(-BPMN_ZOOM_STEP);
  });
}

for (const button of [bpmnZoomInEl, bpmnLightboxZoomInEl]) {
  button.addEventListener('click', () => {
    adjustBpmnZoom(BPMN_ZOOM_STEP);
  });
}

for (const button of [bpmnZoomResetEl, bpmnLightboxZoomResetEl]) {
  button.addEventListener('click', () => {
    setBpmnZoom(1);
  });
}

bpmnLightboxBackdropEl.addEventListener('click', () => {
  closeBpmnLightbox();
});

bpmnLightboxContentEl.addEventListener('click', (event) => {
  event.stopPropagation();
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !bpmnLightboxEl.classList.contains('hidden')) {
    closeBpmnLightbox();
  }
});

zkpListEl.addEventListener('click', (event) => {
  const target = event.target as HTMLElement;
  if (target.dataset.action !== 'remove') {
    return;
  }
  syncExtensionsStateFromDom();
  const card = target.closest<HTMLElement>('.extension-card');
  const index = Number(card?.dataset.index ?? '-1');
  if (index >= 0) {
    extensionsState.zkp.splice(index, 1);
    renderExtensionsForms();
    handleExtensionMutation();
  }
});

addOracleBtn.addEventListener('click', () => {
  syncExtensionsStateFromDom();
  extensionsState.oracles.push(defaultOracleRequirement());
  renderExtensionsForms();
  handleExtensionMutation();
});

addZkpBtn.addEventListener('click', () => {
  syncExtensionsStateFromDom();
  extensionsState.zkp.push(defaultZkpRequirement());
  renderExtensionsForms();
  handleExtensionMutation();
});

tabJsonEl.addEventListener('click', () => setActiveTab('json'));
tabBpmnDiagramEl.addEventListener('click', () => setActiveTab('bpmn-diagram'));
tabBpmnXmlEl.addEventListener('click', () => setActiveTab('bpmn-xml'));

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

generateBpmnBtn.addEventListener('click', async () => {
  const spec = generateJson();
  if (!spec) {
    return;
  }
  const processName = buildProcessName(filenameEl.value);
  if (
    lastGeneratedBpmnResult &&
    lastGeneratedBpmnCacheKey === currentSpecCacheKey &&
    lastGeneratedBpmnProcessName === processName
  ) {
    applyBpmnResult(lastGeneratedBpmnResult, processName);
    setActiveTab('bpmn-diagram');
    setStatus('Reused existing BPMN for unchanged spec.');
    return;
  }
  try {
    generateBpmnBtn.disabled = true;
    setStatus('Generating BPMN...');
    const result = await generateBpmn(spec, processName);
    applyBpmnResult(result, processName);
    setActiveTab('bpmn-diagram');
    setStatus(result.valid ? 'BPMN generated.' : 'BPMN generated with validation errors.', !result.valid);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    invalidateBpmn('BPMN generation failed.');
    setStatus(msg, true);
  } finally {
    generateBpmnBtn.disabled = false;
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

setExtensionsState(emptyExtensionsState());
invalidateBpmn('Generate BPMN to preview the flow diagram.');
syncBpmnZoomUi();
generateJson();
