import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const script = fs.readFileSync(new URL('./学习通脚本.js', import.meta.url), 'utf8');

test('userscript settings dialog stays inside the viewport and scrolls its body', () => {
  assert.match(script, /cx-settings-dialog/);
  assert.match(script, /max-height:\s*calc\(100vh\s*-\s*24px\)/);
  assert.match(script, /overflow-y:\s*auto/);
  assert.match(script, /width:\s*min\(720px,\s*calc\(100vw\s*-\s*24px\)\)/);
  assert.match(script, /cx-runtime-dialog/);
  assert.match(script, /cx-workbench/);
  assert.match(script, /cx-workbench__tabs/);
  assert.match(script, /cx-workbench-settings/);
  assert.match(script, /cx-answer-source/);
  assert.match(script, /this\.panelOpen/);
  assert.match(script, /const WorkbenchApp = vue\.defineComponent/);
  assert.match(script, /vue\.createApp\(WorkbenchApp\)/);
  assert.match(script, /panelLayout/);
  assert.match(script, /cx_workbench_layout/);
  assert.match(script, /beginDrag/);
  assert.match(script, /beginResize/);
  assert.match(script, /pointermove/);
  assert.match(script, /pointerup/);
  assert.match(script, /cx-workbench__resize-handle/);
  assert.match(script, /resetLayout/);
  assert.match(script, /拖动调整工作台大小/);
  assert.match(script, /this\.app = null/);
  assert.doesNotMatch(script, /this\.app = vue\.createApp\(Ask\)/);
  assert.match(script, /right:20px;left:auto/);
  assert.match(script, /question_ti/);
  assert.ok((script.match(/cx-settings-dialog/g) || []).length >= 3);
});
