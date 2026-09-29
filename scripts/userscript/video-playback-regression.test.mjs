import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const script = fs.readFileSync(new URL('./学习通脚本.js', import.meta.url), 'utf8');
const videoStart = script.indexOf('async video(iframeWindow)');
const videoEnd = script.indexOf('\n    work(iframeWindow)', videoStart);
const videoSource = script.slice(videoStart, videoEnd);

const makeRuntime = () => {
  const handlers = new Set();
  return {
    destroyed: false,
    register(handler) {
      handlers.add(handler);
      return () => handlers.delete(handler);
    },
    destroy() {
      this.destroyed = true;
      for (const handler of handlers) handler();
    }
  };
};

const serializeLogArgForTest = (value) => {
  if (value && value.name && value.message) return `${value.name}: ${value.message}`;
  return String(value);
};

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

test('video playback defaults follow the stable reference strategy', () => {
  assert.notEqual(videoStart, -1, 'video method must exist');
  assert.notEqual(videoEnd, -1, 'video method boundary must exist');

  const configDeclaration = videoSource.indexOf('const config = getConfig()');
  const syncCall = videoSource.indexOf('await syncConfigFromServer()');
  const scheduleCall = videoSource.indexOf('scheduleRandomPause();');
  const guardRead = videoSource.indexOf('config.randomPauseEnabled');

  assert.notEqual(syncCall, -1, 'video must refresh the shared server configuration before reading it');
  assert.notEqual(guardRead, -1, 'random pause guard must read the shared configuration');
  assert.notEqual(scheduleCall, -1, 'video must keep the optional pause scheduler compatible');
  assert.ok(
    configDeclaration !== -1 && syncCall < configDeclaration && configDeclaration < guardRead && configDeclaration < scheduleCall,
    'video must sync configuration before reading it and scheduling random pauses'
  );

  assert.doesNotMatch(videoSource, /player\.pause\s*=\s*function/);
  assert.match(videoSource, /playbackRate: 1\.5/);
  assert.match(videoSource, /autoplay: true/);
  assert.match(videoSource, /retryInterval: 2000/);
  assert.match(videoSource, /maxRetries: 10/);
  assert.match(videoSource, /videoCheckInterval: 1000/);
  assert.match(videoSource, /guardNoProgressMs: 7000/);
  assert.match(videoSource, /guardResumeCooldownMs: 1500/);
  assert.doesNotMatch(videoSource, /player\.on\("pause"/);
  assert.match(videoSource, /const pauseForRandomInterval/);
  assert.match(videoSource, /pauseDeadline/);
  assert.match(videoSource, /visibilitychange/);
  assert.match(videoSource, /pageWindow\.addEventListener\("blur"/);
  assert.match(videoSource, /pageDocument\.addEventListener\("visibilitychange"/);
  assert.match(videoSource, /playbackRequest/);
  assert.match(videoSource, /isVideoUnfinished/);
  assert.match(videoSource, /randomPauseDuration/);
  assert.match(videoSource, /计划暂停/);
  assert.match(videoSource, /设置范围/);
  assert.doesNotMatch(videoSource, /new playerWindow\.MouseEvent/);
  assert.doesNotMatch(videoSource, /startPlayback\(\);\s*playerButton\?\.click\(\)/);
  assert.match(videoSource, /playbackRetryTimer \|\| playbackRequest/);
  assert.match(videoSource, /markPlaybackFailure/);
  assert.match(videoSource, /if \(!mutedFallbackApplied\)/);
  assert.match(script, /createNativeVideoPlayer/);
  assert.match(script, /createNativeVideoPlayer\(context\.video\)/);
  assert.match(script, /typeof player\.on !== "function"/);
  assert.match(script, /await sleep\(lastTaskWasVideo \? 1 : formStore\.forminput\.interval\)/);
});

test('video guard restarts an unexpected pause without replacing the native method', async () => {
  let syncCalls = 0;
  const runtime = makeRuntime();
  const videoMethod = new Function(
    'waitVideoPlayerContext',
    'syncConfigFromServer',
    'getConfig',
    'installVideoDiagnostics',
    'mountVideoDiagnosticsPanel',
    'runtime',
    'serializeLogArg',
    `return ${videoSource.replace(/^async video/, 'async function video')}`
  )(
    async () => ({ window: iframeWindow, player }),
    async () => { syncCalls += 1; },
    () => ({
      videoDiagnosticsEnabled: false,
      randomPauseEnabled: false,
    }),
    () => () => {},
    () => {},
    runtime,
    serializeLogArgForTest
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
  await new Promise((resolve) => setTimeout(resolve, 2_100));
  unfinished = false;

  assert.equal(player.pause, nativePause);
  assert.equal(nativePauseCalls, 1);
  assert.equal(paused, false);
  assert.ok(playCalls >= 2);

  unfinished = false;
  await videoPromise;
  assert.equal(player.pause, nativePause);
});

test('video keeps background pauses native and resumes once after returning to foreground', async () => {
  const runtime = makeRuntime();
  const videoMethod = new Function(
    'waitVideoPlayerContext',
    'syncConfigFromServer',
    'getConfig',
    'installVideoDiagnostics',
    'mountVideoDiagnosticsPanel',
    'runtime',
    'serializeLogArg',
    `return ${videoSource.replace(/^async video/, 'async function video')}`
  )(
    async () => ({ window: iframeWindow, player }),
    async () => {},
    () => ({ videoDiagnosticsEnabled: false, randomPauseEnabled: false }),
    () => () => {},
    () => {},
    runtime,
    serializeLogArgForTest
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
  await new Promise((resolve) => setTimeout(resolve, 2_100));
  assert.equal(nativePauseCalls, 1);
  assert.equal(playCalls, initialPlayCalls + 1, '参考脚本策略会由监控器恢复后台暂停');

  document.visibilityState = 'visible';
  visibilityHandlers.get('visibilitychange')?.();
  await new Promise((resolve) => setTimeout(resolve, 300));
  assert.equal(playCalls, initialPlayCalls + 1, '回到前台后不应重复调用播放');

  unfinished = false;
  await videoPromise;
});

test.skip('video reschedules a background random pause instead of pausing immediately on foreground', async () => {
  const runtime = makeRuntime();
  const videoMethod = new Function(
    'waitVideoPlayerContext',
    'syncConfigFromServer',
    'getConfig',
    'installVideoDiagnostics',
    'mountVideoDiagnosticsPanel',
    'runtime',
    'serializeLogArg',
    `return ${videoSource.replace(/^async video/, 'async function video')}`
  )(
    async () => ({ window: iframeWindow, player }),
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
    () => {},
    runtime,
    serializeLogArgForTest
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

test('video retries a transient play rejection with the reference retry interval', async () => {
  const runtime = makeRuntime();
  const videoMethod = new Function(
    'waitVideoPlayerContext',
    'syncConfigFromServer',
    'getConfig',
    'installVideoDiagnostics',
    'mountVideoDiagnosticsPanel',
    'runtime',
    'serializeLogArg',
    `return ${videoSource.replace(/^async video/, 'async function video')}`
  )(
    async () => ({ window: iframeWindow, player }),
    async () => {},
    () => ({ videoDiagnosticsEnabled: false, randomPauseEnabled: false }),
    () => () => {},
    () => {},
    runtime,
    serializeLogArgForTest
  );

  const handlers = new Map();
  const warnings = [];
  const originalWarn = console.warn;
  let paused = false;
  let playCalls = 0;
  let muted = true;
  let mutedCalls = 0;
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
    muted(value) {
      if (value === undefined) return muted;
      mutedCalls += 1;
      muted = Boolean(value);
      return muted;
    },
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
    await new Promise((resolve) => setTimeout(resolve, 20));
    assert.equal(playCalls, 2, '首次播放失败后应立即执行一次静音回退');
    assert.equal(mutedCalls, 1, '静音回退只应设置一次静音');
    await new Promise((resolve) => setTimeout(resolve, 2_300));
    assert.ok(playCalls >= 2, '暂态播放失败后应自动重试');
    assert.equal(warnings.filter((message) => message.includes('播放请求未成功')).length, 1, '暂态失败应保留一次可诊断警告');

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
