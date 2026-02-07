export async function saveSpec(filename: string, content: unknown) {
  const res = await fetch('http://localhost:5174/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, content }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Save failed: ${res.status}`);
  }

  return res.json();
}
