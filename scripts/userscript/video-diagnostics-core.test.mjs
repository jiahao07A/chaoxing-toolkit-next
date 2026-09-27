import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptPath = path.join(path.dirname(fileURLToPath(import.meta.url)), "学习通脚本.js");
const script = fs.readFileSync(scriptPath, "utf8");
assert.doesNotMatch(script, /\n\s*mountVideoDiagnosticsPanel\(\);/, "视频播放不应再自动挂载诊断悬浮窗");
const blockStart = script.indexOf('const VIDEO_DIAGNOSTICS_KEY = "videoDiagnostics"');
const blockEnd = script.indexOf("  let runtimeLogSink = null;", blockStart);
assert.ok(blockStart >= 0 && blockEnd > blockStart, "无法定位正式用户脚本中的诊断实现");
const diagnosticsBlock = script.slice(blockStart, blockEnd);

const createDiagnostics = (initial = [], enabled = true) => {
  let value = initial;
  const getValue = (_key, fallback) => value ?? fallback;
  const setValue = (_key, next) => { value = next; };
  const helpers = new Function("_GM_getValue", "_GM_setValue", "_unsafeWindow", "getConfig", `${diagnosticsBlock}; return { sanitizeVideoDiagnosticEvent, pruneVideoDiagnostics, recordVideoDiagnostic };`)(getValue, setValue, {}, () => ({ videoDiagnosticsEnabled: enabled }));
  return {
    get events() { return value; },
    ...helpers
  };
};

const TTL = 7 * 24 * 60 * 60 * 1000;

test("只保留脱敏播放器字段并舍弃任意附加内容", () => {
  const { sanitizeVideoDiagnosticEvent } = createDiagnostics();
  const event = sanitizeVideoDiagnosticEvent({
    timestamp: 1_000,
    event: "pause",
    currentTime: 12.3456,
    duration: 99.999,
    playbackRate: 99,
    readyState: 8,
    networkState: 2,
    paused: true,
    ended: false,
    url: "https://example.test/course?token=secret",
    question: "不应写入题目"
  }, 1_000);

  assert.deepEqual(event, {
    timestamp: 1_000,
    event: "pause",
    currentTime: 12.35,
    duration: 100,
    playbackRate: 16,
    readyState: 4,
    networkState: 2,
    paused: true,
    ended: false
  });
  assert.equal(JSON.stringify(event).includes("secret"), false);
  assert.equal(JSON.stringify(event).includes("不应写入题目"), false);
});

test("TTL 清理只保留最近七天事件", () => {
  const { pruneVideoDiagnostics } = createDiagnostics();
  const now = 10 * TTL;
  const retained = pruneVideoDiagnostics([
    { timestamp: now - TTL + 1, event: "play" },
    { timestamp: now - TTL - 1, event: "pause" },
    { timestamp: now + 1, event: "ended" }
  ], now);

  assert.deepEqual(retained.map((item) => item.event), ["play"]);
});

test("写入事件会先清理过期数据", () => {
  const diagnostics = createDiagnostics([
    { timestamp: 10 * TTL - TTL - 1, event: "pause" }
  ]);
  const now = 10 * TTL;
  diagnostics.recordVideoDiagnostic({ timestamp: now, event: "playing", currentTime: 3 }, now);

  assert.deepEqual(diagnostics.events, [{ timestamp: now, event: "playing", currentTime: 3 }]);
});
