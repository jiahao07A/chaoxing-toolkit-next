import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const script = fs.readFileSync(new URL('./学习通脚本.js', import.meta.url), 'utf8');

test('userscript settings dialog stays inside the viewport and scrolls its body', () => {
  assert.match(script, /cx-settings-dialog/);
  assert.match(script, /max-height:\s*calc\(100vh\s*-\s*24px\)/);
  assert.match(script, /overflow-y:\s*auto/);
  assert.match(script, /width:\s*min\(720px,\s*calc\(100vw\s*-\s*24px\)\)/);
  assert.ok((script.match(/cx-settings-dialog/g) || []).length >= 3);
});

