import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const script = fs.readFileSync(new URL('./学习通脚本.js', import.meta.url), 'utf8');
const videoStart = script.indexOf('async video(iframeWindow)');
const videoEnd = script.indexOf('\n    work(iframeWindow)', videoStart);
const videoSource = script.slice(videoStart, videoEnd);

test('playback error serialization keeps cross-frame error details', () => {
  const serializeStart = script.indexOf('const serializeLogArg =');
  const serializeEnd = script.indexOf('\n  const inferLogLevel', serializeStart);
  assert.notEqual(serializeStart, -1, 'log serializer must exist');
  assert.notEqual(serializeEnd, -1, 'log serializer boundary must exist');
  const serializeLogArg = new Function(`${script.slice(serializeStart, serializeEnd)}; return serializeLogArg;`)();

  assert.equal(
    serializeLogArg({ name: 'AbortError', message: 'The play() request was interrupted' }),
    'AbortError: The play() request was interrupted'
  );
});

test('video playback path defines its config before scheduling random pauses', () => {
  assert.notEqual(videoStart, -1, 'video method must exist');
  assert.notEqual(videoEnd, -1, 'video method boundary must exist');

  const configDeclaration = videoSource.indexOf('const config = getConfig()');
  const syncCall = videoSource.indexOf('await syncConfigFromServer()');
  const scheduleCall = videoSource.indexOf('scheduleRandomPause();');
  const guardRead = videoSource.indexOf('config.randomPauseEnabled');

  assert.notEqual(syncCall, -1, 'video must refresh the shared server configuration before reading it');
  assert.notEqual(guardRead, -1, 'random pause guard must read the shared configuration');
  assert.notEqual(scheduleCall, -1, 'video must schedule random pauses');
  assert.ok(
    configDeclaration !== -1 && syncCall < configDeclaration && configDeclaration < guardRead && configDeclaration < scheduleCall,
    'video must sync configuration before reading it and scheduling random pauses'
  );

  assert.doesNotMatch(videoSource, /player\.pause\s*=\s*function/);
  assert.match(videoSource, /player\.on\("pause"/);
  assert.match(videoSource, /const pauseForRandomInterval/);
  assert.match(videoSource, /pauseDeadline/);
  assert.match(videoSource, /pendingRandomPause/);
  assert.match(videoSource, /visibilitychange/);
  assert.match(videoSource, /页面回到前台，已恢复播放/);
  assert.match(videoSource, /!isPageVisible\(\)/);
  assert.match(videoSource, /playbackRequest/);
  assert.match(videoSource, /isVideoUnfinished/);
  assert.match(videoSource, /randomPauseDuration/);
  assert.match(videoSource, /计划暂停/);
  assert.match(videoSource, /设置范围/);
  assert.doesNotMatch(videoSource, /startPlayback\(\);\s*playerButton\?\.click\(\)/);
});

test('video guard restarts an unexpected pause without replacing the native method', async () => {
  let syncCalls = 0;
  const videoMethod = new Function(
    'waitElementLoaded',
    'syncConfigFromServer',
    'getConfig',
    'installVideoDiagnostics',
    'mountVideoDiagnosticsPanel',
    `return ${videoSource.replace(/^async video/, 'async function video')}`
  )(
    async () => {},
    async () => { syncCalls += 1; },
    () => ({
      videoDiagnosticsEnabled: false,
      randomPauseEnabled: false,
    }),
    () => () => {},
    () => {}
  );

  const handlers = new Map();
  let paused = false;
  let playCalls = 0;
  let nativePauseCalls = 0;
  let unfinished = true;
  const nativePause = function nativePause() {
    nativePauseCalls += 1;
    paused = true;
    handlers.get('pause')?.forEach((handler) => handler());
  };
  const player = {
    play() {
      playCalls += 1;
      paused = false;
      return Promise.resolve();
    },
    pause: nativePause,
    paused: () => paused,
    currentTime: () => 10,
    duration: () => 100,
    ended: () => false,
    muted: () => {},
    playbackRate: (value) => value ?? 1,
    on(event, handler) {
      if (!handlers.has(event)) handlers.set(event, []);
      handlers.get(event).push(handler);
    },
    off(event, handler) {
      handlers.set(event, (handlers.get(event) || []).filter((item) => item !== handler));
    },
  };
  const iframeWindow = {
    videojs: () => player,
    document: { querySelector: () => null },
    isUnFinishJob: () => unfinished,
  };
  const context = { askStore: { reset() {}, task: { name: '', video: { status: 0 } } } };

  const videoPromise = videoMethod.call(context, iframeWindow);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(syncCalls, 1, 'video must refresh server settings before playback control starts');
  assert.equal(player.pause, nativePause);
  player.pause.call(player);
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(player.pause, nativePause);
  assert.equal(nativePauseCalls, 1);
  assert.equal(paused, false);
  assert.ok(playCalls >= 2);

  unfinished = false;
  await videoPromise;
  assert.equal(player.pause, nativePause);
});

test('video keeps background pauses native and resumes once after returning to foreground', async () => {
  const videoMethod = new Function(
    'waitElementLoaded',
    'syncConfigFromServer',
    'getConfig',
    'installVideoDiagnostics',
    'mountVideoDiagnosticsPanel',
    `return ${videoSource.replace(/^async video/, 'async function video')}`
  )(
    async () => {},
    async () => {},
    () => ({ videoDiagnosticsEnabled: false, randomPauseEnabled: false }),
    () => () => {},
    () => {}
  );

  const handlers = new Map();
  const visibilityHandlers = new Map();
  let paused = false;
  let playCalls = 0;
  let nativePauseCalls = 0;
  let unfinished = true;
  const nativePause = function nativePause() {
    nativePauseCalls += 1;
    paused = true;
    handlers.get('pause')?.forEach((handler) => handler());
  };
  const player = {
    play() {
      playCalls += 1;
      paused = false;
      return Promise.resolve();
    },
    pause: nativePause,
    paused: () => paused,
    currentTime: () => 10,
    duration: () => 100,
    ended: () => false,
    muted: () => {},
    playbackRate: (value) => value ?? 1,
    on(event, handler) {
      if (!handlers.has(event)) handlers.set(event, []);
      handlers.get(event).push(handler);
    },
    off(event, handler) {
      handlers.set(event, (handlers.get(event) || []).filter((item) => item !== handler));
    }
  };
  const document = {
    visibilityState: 'hidden',
    querySelector: () => null,
    addEventListener(event, handler) {
      visibilityHandlers.set(event, handler);
    },
    removeEventListener() {}
  };
  const iframeWindow = {
    videojs: () => player,
    document,
    isUnFinishJob: () => unfinished
  };
  const context = { askStore: { reset() {}, task: { name: '', video: { status: 0 } } } };

  const videoPromise = videoMethod.call(context, iframeWindow);
  await new Promise((resolve) => setTimeout(resolve, 0));
  const initialPlayCalls = playCalls;
  player.pause.call(player);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(nativePauseCalls, 1);
  assert.equal(playCalls, initialPlayCalls, '后台暂停不应立即触发播放请求');
  await new Promise((resolve) => setTimeout(resolve, 1_100));
  assert.equal(playCalls, initialPlayCalls, '后台轮询不应触发播放请求');

  document.visibilityState = 'visible';
  visibilityHandlers.get('visibilitychange')?.();
  await new Promise((resolve) => setTimeout(resolve, 300));
  assert.equal(playCalls, initialPlayCalls + 1, '回到前台后只应恢复播放一次');

  unfinished = false;
  await videoPromise;
});

test('video reschedules a background random pause instead of pausing immediately on foreground', async () => {
  const videoMethod = new Function(
    'waitElementLoaded',
    'syncConfigFromServer',
    'getConfig',
    'installVideoDiagnostics',
    'mountVideoDiagnosticsPanel',
    `return ${videoSource.replace(/^async video/, 'async function video')}`
  )(
    async () => {},
    async () => {},
    () => ({
      videoDiagnosticsEnabled: false,
      randomPauseEnabled: true,
      randomPauseIntervalMin: 1,
      randomPauseIntervalMax: 1,
      randomPauseDurationMin: 1,
      randomPauseDurationMax: 1,
    }),
    () => () => {},
    () => {}
  );

  const handlers = new Map();
  const visibilityHandlers = new Map();
  let paused = false;
  let playCalls = 0;
  let nativePauseCalls = 0;
  let unfinished = true;
  const nativePause = function nativePause() {
    nativePauseCalls += 1;
    paused = true;
    handlers.get('pause')?.forEach((handler) => handler());
  };
  const player = {
    play() {
      playCalls += 1;
      paused = false;
      return Promise.resolve();
    },
    pause: nativePause,
    paused: () => paused,
    currentTime: () => 10,
    duration: () => 100,
    ended: () => false,
    muted: () => {},
    playbackRate: (value) => value ?? 1,
    on(event, handler) {
      if (!handlers.has(event)) handlers.set(event, []);
      handlers.get(event).push(handler);
    },
    off(event, handler) {
      handlers.set(event, (handlers.get(event) || []).filter((item) => item !== handler));
    }
  };
  const document = {
    visibilityState: 'hidden',
    querySelector: () => null,
    addEventListener(event, handler) {
      visibilityHandlers.set(event, handler);
    },
    removeEventListener() {}
  };
  const iframeWindow = {
    videojs: () => player,
    document,
    isUnFinishJob: () => unfinished
  };
  const context = { askStore: { reset() {}, task: { name: '', video: { status: 0 } } } };

  const videoPromise = videoMethod.call(context, iframeWindow);
  await new Promise((resolve) => setTimeout(resolve, 1_150));
  const initialPlayCalls = playCalls;
  assert.equal(nativePauseCalls, 0, '后台随机暂停到期时不应暂停视频');

  document.visibilityState = 'visible';
  visibilityHandlers.get('visibilitychange')?.();
  await new Promise((resolve) => setTimeout(resolve, 300));
  assert.equal(nativePauseCalls, 0, '回到前台后不应立即触发随机暂停');
  assert.equal(playCalls, initialPlayCalls, '视频仍在播放时不应重复调用播放');

  await new Promise((resolve) => setTimeout(resolve, 1_150));
  assert.equal(nativePauseCalls, 1, '重新安排的随机暂停应在完整间隔后触发');

  unfinished = false;
  handlers.get('ended')?.forEach((handler) => handler());
  await videoPromise;
});

test('video retries a transient play rejection without surfacing a recovered warning', async () => {
  const videoMethod = new Function(
    'waitElementLoaded',
    'syncConfigFromServer',
    'getConfig',
    'installVideoDiagnostics',
    'mountVideoDiagnosticsPanel',
    `return ${videoSource.replace(/^async video/, 'async function video')}`
  )(
    async () => {},
    async () => {},
    () => ({ videoDiagnosticsEnabled: false, randomPauseEnabled: false }),
    () => () => {},
    () => {}
  );

  const handlers = new Map();
  const warnings = [];
  const originalWarn = console.warn;
  let paused = false;
  let playCalls = 0;
  let unfinished = true;
  console.warn = (...args) => warnings.push(args.map((value) => String(value)).join(' '));
  const nativePause = function nativePause() {
    paused = true;
    handlers.get('pause')?.forEach((handler) => handler());
  };
  const player = {
    play() {
      playCalls += 1;
      if (playCalls === 1) {
        paused = true;
        return Promise.reject({ name: 'AbortError', message: 'The play() request was interrupted' });
      }
      paused = false;
      return Promise.resolve();
    },
    pause: nativePause,
    paused: () => paused,
    currentTime: () => 10,
    duration: () => 100,
    ended: () => false,
    muted: () => {},
    playbackRate: (value) => value ?? 1,
    on(event, handler) {
      if (!handlers.has(event)) handlers.set(event, []);
      handlers.get(event).push(handler);
    },
    off(event, handler) {
      handlers.set(event, (handlers.get(event) || []).filter((item) => item !== handler));
    }
  };
  const iframeWindow = {
    videojs: () => player,
    document: { visibilityState: 'visible', querySelector: () => null },
    isUnFinishJob: () => unfinished
  };
  const context = { askStore: { reset() {}, task: { name: '', video: { status: 0 } } } };
  let videoPromise;

  try {
    videoPromise = videoMethod.call(context, iframeWindow);
    await new Promise((resolve) => setTimeout(resolve, 450));
    assert.ok(playCalls >= 2, '暂态播放失败后应自动重试');
    assert.equal(warnings.filter((message) => message.includes('播放请求未成功')).length, 0, '已恢复的暂态失败不应保留警告');

    unfinished = false;
    handlers.get('ended')?.forEach((handler) => handler());
    await videoPromise;
  } finally {
    unfinished = false;
    handlers.get('ended')?.forEach((handler) => handler());
    if (videoPromise) await videoPromise;
    console.warn = originalWarn;
  }
});
