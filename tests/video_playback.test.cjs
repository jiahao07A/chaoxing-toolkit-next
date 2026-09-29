const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'scripts', 'userscript', '学习通脚本.js'), 'utf8');
const start = source.indexOf('    async video(iframeWindow) {');
const end = source.indexOf('    work(iframeWindow) {', start);
assert.ok(start >= 0 && end > start, 'video method can be loaded from the maintained script');
const videoMethod = source.slice(start, end);

test('buffering event bursts do not cause repeated play requests', async () => {
  const listeners = new Map();
  const cleanup = new Set();
  const logs = [];
  const runtime = {
    destroyed: false,
    register(handler) {
      cleanup.add(handler);
      return () => cleanup.delete(handler);
    }
  };
  let playCalls = 0;
  const player = {
    on(name, handler) {
      if (!listeners.has(name)) listeners.set(name, new Set());
      listeners.get(name).add(handler);
    },
    off(name, handler) { listeners.get(name)?.delete(handler); },
    emit(name) { for (const handler of listeners.get(name) || []) handler(); },
    play() { playCalls++; return Promise.resolve(); },
    pause() {},
    paused() { return true; },
    muted() {},
    playbackRate(value) { return value === undefined ? 1 : value; },
    currentTime() { return 0; },
    duration() { return 100; },
    ended() { return false; }
  };
  const iframeWindow = { isUnFinishJob: () => true };
  const playerWindow = {
    document: { addEventListener() {}, removeEventListener() {} }
  };
  const context = {
    runtime,
    waitVideoPlayerContext: async () => ({ window: playerWindow, player, video: null }),
    syncConfigFromServer: async () => {},
    getConfig: () => ({ randomPauseEnabled: false }),
    installVideoDiagnostics: () => () => {},
    serializeLogArg: String,
    console: { log() {}, warn: (...args) => logs.push(args.join(' ')), info: (...args) => logs.push(args.join(' ')) },
    setTimeout, clearTimeout, setInterval, clearInterval
  };
  const Model = vm.runInNewContext(`(class { ${videoMethod} })`, context);
  const model = new Model();
  model.askStore = { reset() {}, task: { video: {}, status: '' } };
  const videoPromise = model.video(iframeWindow);
  await new Promise((resolve) => setTimeout(resolve, 20));
  try {
    for (let index = 0; index < 12; index++) {
      player.emit('waiting');
      player.emit('pause');
      await new Promise((resolve) => setTimeout(resolve, 25));
    }
    assert.ok(playCalls <= 2, `buffering triggered ${playCalls} play() calls in 300 ms`);
    assert.ok(logs.length <= 2, `buffering generated ${logs.length} repeated status logs`);
  } finally {
    runtime.destroyed = true;
    for (const handler of [...cleanup]) handler();
    await videoPromise;
  }
});
