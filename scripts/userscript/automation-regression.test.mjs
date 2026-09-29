import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const script = fs.readFileSync(new URL("./学习通脚本.js", import.meta.url), "utf8");

const parseTaskStart = script.indexOf("parseChapterTaskInfo = (iframe) =>");
const parseTaskEnd = script.indexOf("}, removeHtml =", parseTaskStart);
assert.ok(parseTaskStart >= 0 && parseTaskEnd > parseTaskStart, "无法定位章节任务元数据解析函数");
const parseChapterTaskInfo = new Function(`return ${script.slice(parseTaskStart, parseTaskEnd + 1).replace(/^parseChapterTaskInfo = /, "")}`)();

test("章节任务元数据解析会区分有效对象与损坏数据", () => {
  assert.deepEqual(parseChapterTaskInfo({ getAttribute: () => '{"name":"视频"}' }), { name: "视频" });
  assert.equal(parseChapterTaskInfo({ getAttribute: () => "{broken" }), null);
  assert.equal(parseChapterTaskInfo({ getAttribute: () => null }), null);
});

test("章节启动应安全处理异常任务元数据，而不是中止整轮任务", () => {
  assert.match(script, /parseChapterTaskInfo\s*=\s*\(iframe\)/);
  assert.match(script, /const taskInfo = parseChapterTaskInfo\(iframe\);/);
  assert.match(script, /任务点元数据无效，下一轮重试/);
});

test("未知章节任务不能被当作已完成后自动跳过", () => {
  assert.match(script, /未知任务待人工确认，暂停自动切换/);
  assert.match(script, /chapterBlockedHref/);
  assert.match(script, /chapterBlockedHref\s*=\s*_self1\.location\.href/);
  assert.doesNotMatch(script, /未知任务跳过.*success/);
});

test("章节轮询保留互斥与退避，工作台指针逻辑已移除", () => {
  assert.match(script, /let chapterPollRunning = false/);
  assert.match(script, /if \(chapterPollRunning\) return/);
  assert.match(script, /5e3/);
  assert.doesNotMatch(script, /WorkbenchApp|cx-workbench|pointerFrameState|beginResize|requestPointerFrame/);
});

test("视频控制应保留播放器原生 pause 方法", () => {
  assert.doesNotMatch(script, /player\.pause\s*=\s*function/);
  assert.match(script, /createNativeVideoPlayer = \(video\)/);
  assert.match(script, /pause:\s*\(\) => video\.pause\(\)/);
  assert.match(script, /player\.pause\(\)/);
});
