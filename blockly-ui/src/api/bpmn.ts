export type BpmnResult = {
  ok: true;
  bpmn_xml: string;
  svg: string;
  warnings: string[];
  errors: string[];
  valid: boolean;
};

export async function generateBpmn(content: unknown, processName: string): Promise<BpmnResult> {
  const res = await fetch('http://localhost:5174/bpmn', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, processName }),
  });

  if (!res.ok) {
    const text = await res.text();
    if (text.includes('Cannot POST /bpmn')) {
      throw new Error('Blockly backend does not expose /bpmn yet. Restart the local server so it loads the new BPMN route.');
    }
    if (text.includes('<!DOCTYPE html>')) {
      throw new Error('Blockly backend returned HTML instead of BPMN JSON. Restart the local server and try again.');
    }
    throw new Error(text || `BPMN generation failed: ${res.status}`);
  }

  return res.json();
}
