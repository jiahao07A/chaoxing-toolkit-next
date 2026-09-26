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
  const scheduleCall = videoSource.indexOf('scheduleRandomPause();');
  const guardRead = videoSource.indexOf('config.randomPauseEnabled');

  assert.notEqual(guardRead, -1, 'random pause guard must read the shared configuration');
  assert.notEqual(scheduleCall, -1, 'video must schedule random pauses');
  assert.ok(
    configDeclaration !== -1 && configDeclaration < guardRead && configDeclaration < scheduleCall,
    'video must define config before the first random-pause read and call'
  );

  assert.match(videoSource, /const pauseBase = player\.pause/);
  assert.match(videoSource, /player\.pause = function/);
  assert.match(videoSource, /player\.on\("pause"/);
  assert.match(videoSource, /const pauseForRandomInterval/);
  assert.doesNotMatch(videoSource, /startPlayback\(\);\s*playerButton\?\.click\(\)/);
});

test('video guard restarts an unexpected pause and restores the native method on finish', async () => {
  const videoMethod = new Function(
    'waitElementLoaded',
    'getConfig',
    'installVideoDiagnostics',
    'mountVideoDiagnosticsPanel',
    `return ${videoSource.replace(/^async video/, 'async function video')}`
  )(
    async () => {},
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
