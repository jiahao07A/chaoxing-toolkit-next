import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const script = fs.readFileSync(new URL('./学习通脚本.js', import.meta.url), 'utf8');
const videoStart = script.indexOf('async video(iframeWindow)');
const videoEnd = script.indexOf('\n    work(iframeWindow)', videoStart);
const videoSource = script.slice(videoStart, videoEnd);

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

  assert.match(videoSource, /const pauseBase = player\.pause/);
  assert.match(videoSource, /player\.pause = function/);
  assert.match(videoSource, /player\.on\("pause"/);
  assert.match(videoSource, /const pauseForRandomInterval/);
  assert.match(videoSource, /pauseDeadline/);
  assert.match(videoSource, /pendingRandomPause/);
  assert.match(videoSource, /visibilitychange/);
  assert.match(videoSource, /页面进入后台/);
  assert.match(videoSource, /randomPauseDuration/);
  assert.match(videoSource, /计划暂停/);
  assert.match(videoSource, /设置范围/);
  assert.doesNotMatch(videoSource, /startPlayback\(\);\s*playerButton\?\.click\(\)/);
});

test('video guard restarts an unexpected pause and restores the native method on finish', async () => {
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
  const guardedPause = player.pause;
  guardedPause.call(player);
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.notEqual(guardedPause, nativePause);
  assert.equal(nativePauseCalls, 0);
  assert.equal(paused, false);
  assert.ok(playCalls >= 2);

  unfinished = false;
  await videoPromise;
  assert.equal(player.pause, nativePause);
});
