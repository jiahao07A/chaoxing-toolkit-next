import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const script = fs.readFileSync(new URL("./学习通脚本.js", import.meta.url), "utf8");
const runtime = {
  destroyed: false,
  register(handler) {
    return () => {};
  }
};
const waitIframeStart = script.indexOf("waitIframeLoaded = (");
const waitElementStart = script.indexOf("waitElementLoaded =", waitIframeStart);
assert.ok(waitIframeStart >= 0 && waitElementStart > waitIframeStart, "无法定位 iframe 等待函数");
const waitIframeSource = script.slice(waitIframeStart, waitElementStart).replace(/\),\s*$/, ")").replace(/^waitIframeLoaded = /, "");
const waitIframeLoaded = new Function("runtime", `return ${waitIframeSource}`)(runtime);
const removeHtmlStart = script.indexOf("removeHtml =", waitElementStart);
const waitElementEnd = script.indexOf(", createNativeVideoPlayer =", waitElementStart);
assert.ok(removeHtmlStart > waitElementStart, "无法定位元素等待函数结束位置");
const waitElementSource = script.slice(waitElementStart, Math.min(removeHtmlStart, waitElementEnd > waitElementStart ? waitElementEnd : removeHtmlStart)).replace(/,\s*$/, "").replace(/^waitElementLoaded = /, "");
const waitElementLoaded = new Function("runtime", `return ${waitElementSource}`)(runtime);
const decodeStart = script.indexOf("decode = async (iframeWindow) => {");
const decodeEnd = script.indexOf("}, hasUsableAnswer", decodeStart);
assert.ok(decodeStart >= 0 && decodeEnd > decodeStart, "无法定位章节题目解码函数");
const decodeSource = script.slice(decodeStart, decodeEnd + 1).replace(/^decode = /, "const decode = ");

assert.match(script, /let chapterWorkRunning = false/);
assert.match(script, /let chapterPollRunning = false/);
assert.match(script, /if \(chapterPollRunning\) return/);
assert.match(script, /const Timu = iframeWindow\.document\.querySelectorAll\("\.TiMu"\);\s*if \(!Timu \|\| Timu\.length === 0\)/);
assert.match(script, /题目加载超时，下一轮重试/);
assert.match(script, /题目仍在加载，等待下一轮重试/);
assert.match(script, /章节测验处理失败，下一轮重试/);
assert.match(script, /const started = await startWork\(\);\s*if \(!runtime\.destroyed && started\) iframeCom = _self1\.location\.href/);

test("等待章节 iframe 时只注册一个 load 监听", async () => {
  const listeners = [];
  const iframe = {
    contentDocument: { readyState: "loading" },
    addEventListener(event, handler) {
      if (event === "load") listeners.push(handler);
    }
  };

  const loaded = waitIframeLoaded(iframe);
  await new Promise((resolve) => setTimeout(resolve, 250));
  const listenerCount = listeners.length;
  iframe.contentDocument.readyState = "complete";
  listeners.forEach((handler) => handler());
  await loaded;

  assert.equal(listenerCount, 1, "iframe 加载等待期间不应重复注册 load 监听");
});

test("缺失 iframe 会快速返回失败，不会创建永久等待", async () => {
  assert.equal(await waitIframeLoaded(null, 5), false);
});

test("iframe 已进入 interactive 状态时立即视为可用", async () => {
  let listeners = 0;
  const iframe = {
    contentDocument: { readyState: "interactive" },
    addEventListener() {
      listeners += 1;
    }
  };

  assert.equal(await waitIframeLoaded(iframe, 5), true);
  assert.equal(listeners, 0, "load 已经发生后不应再次等待事件");
});

test("iframe 超时后返回失败并清理监听", async () => {
  let removed = 0;
  const iframe = {
    contentDocument: { readyState: "loading" },
    addEventListener() {},
    removeEventListener() { removed += 1; }
  };

  assert.equal(await waitIframeLoaded(iframe, 5), false);
  assert.equal(removed, 1);
});

test("章节题目等待超时后返回失败，不会永久轮询", async () => {
  const iframeWindow = { document: { querySelector: () => null } };
  assert.equal(await waitElementLoaded(iframeWindow, ".TiMu", 5), false);
});

test("章节题目解码只处理页面中实际出现的字符", async () => {
  let glyphCalls = 0;
  const decode = new Function(
    "Typr$1",
    "md5",
    "_GM_getResourceText",
    `${decodeSource}; return decode;`
  )(
    {
      parse: () => ({}),
      U: {
        codeToGlyph: () => { glyphCalls += 1; return 1; },
        glyphToPath: () => ({})
      }
    },
    () => "000000000000000000000000glyphkey",
    () => JSON.stringify({ glyphkey: "乙" })
  );
  const fontElement = { innerHTML: "甲", classList: { remove() {} } };
  await decode({
    document: {
      querySelectorAll(selector) {
        if (selector === "style") return [{ textContent: "font-cxsecret url(data:font/ttf;base64,AAAA')" }];
        if (selector === ".font-cxsecret") return [fontElement];
        return [];
      }
    }
  });

  assert.ok(glyphCalls <= 2, `解码不应遍历整个汉字区间，实际调用 ${glyphCalls} 次`);
});

test("章节字体解码会让出主线程，避免页面无响应", async () => {
  let finished = false;
  const characters = Array.from({ length: 256 }, (_, index) => String.fromCharCode(19968 + index)).join("");
  const decode = new Function(
    "Typr$1",
    "md5",
    "_GM_getResourceText",
    `${decodeSource}; return decode;`
  )(
    {
      parse: () => ({}),
      U: {
        codeToGlyph: () => 1,
        glyphToPath: () => ({})
      }
    },
    () => "000000000000000000000000glyphkey",
    () => JSON.stringify({ glyphkey: "乙" })
  );
  const pending = Promise.resolve(decode({
    document: {
      querySelectorAll(selector) {
        if (selector === "style") return [{ textContent: "font-cxsecret url(data:font/ttf;base64,AAAA'" }];
        if (selector === ".font-cxsecret") return [{ textContent: characters, innerHTML: characters, classList: { remove() {} } }];
        return [];
      }
    }
  })).then(() => {
    finished = true;
  });
  assert.equal(typeof pending?.then, "function", "字体解码必须是可等待的异步任务");
  const yielded = await new Promise((resolve) => setTimeout(() => resolve(!finished), 0));
  assert.equal(yielded, true, "解码期间应允许定时器执行");
  await pending;
});

test("章节字体解码不依赖后台 iframe 的 requestAnimationFrame", async () => {
  const characters = Array.from({ length: 256 }, (_, index) => String.fromCharCode(19968 + index)).join("");
  const decode = new Function(
    "Typr$1",
    "md5",
    "_GM_getResourceText",
    `${decodeSource}; return decode;`
  )(
    {
      parse: () => ({}),
      U: {
        codeToGlyph: () => 1,
        glyphToPath: () => ({})
      }
    },
    () => "000000000000000000000000glyphkey",
    () => JSON.stringify({ glyphkey: "乙" })
  );
  const fontElement = { textContent: characters, innerHTML: characters, classList: { remove() {} } };
  let animationFrameCalls = 0;
  const pending = decode({
    requestAnimationFrame() {
      animationFrameCalls += 1;
    },
    document: {
      querySelectorAll(selector) {
        if (selector === "style") return [{ textContent: "font-cxsecret url(data:font/ttf;base64,AAAA')" }];
        if (selector === ".font-cxsecret") return [fontElement];
        return [];
      }
    }
  });

  await Promise.race([
    pending,
    new Promise((_, reject) => setTimeout(() => reject(new Error("字体解码依赖未触发的 requestAnimationFrame")), 500))
  ]);
  assert.equal(animationFrameCalls, 0, "解码让步不应依赖 requestAnimationFrame");
});
