from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "userscript" / "学习通脚本.js"


def test_verify_detector_is_top_level_throttled_and_does_not_clone_page():
    source = SCRIPT.read_text(encoding="utf-8")

    assert "@updateURL" not in source
    assert "@downloadURL" not in source
    assert "if (window !== window.top) return;" in source
    assert "attributes: true" not in source
    assert "characterData: true" not in source
    assert "document.body.innerText" not in source
    assert "window.open(currentUrl, '_blank')" not in source
    assert "navigator.clipboard.writeText(currentUrl)" not in source
    assert "window.close()" not in source
    assert "lifecycleRuntime?.destroy?.()" in source


def test_chapter_polling_has_a_backoff_and_runtime_cleanup():
    source = SCRIPT.read_text(encoding="utf-8")

    assert "}, 5e3);" in source
    assert "runtime.register(() =>" in source
    assert "observer?.disconnect()" in source
    assert "settingsDialogTimer = setTimeout(() =>" in source


def test_video_recovery_is_rate_limited_and_does_not_emit_synthetic_mouse_events():
    source = SCRIPT.read_text(encoding="utf-8")

    assert '"randomPauseEnabled":false' in source
    assert "PLAYBACK_DEFAULTS_MIGRATION_KEY" in source
    assert "config.randomPauseEnabled = false" in source
    assert "playbackRate: 1.5" in source
    assert "autoplay: true" in source
    assert "retryInterval: 2000" in source
    assert "maxRetries: 10" in source
    assert "videoCheckInterval: 1000" in source
    assert "guardNoProgressMs: 7000" in source
    assert "guardResumeCooldownMs: 1500" in source
    assert "nextPlaybackAttemptAt" in source
    assert "Date.now() < nextPlaybackAttemptAt" in source
    assert "createNativeVideoPlayer" in source
    assert "markPlaybackFailure" in source
    assert "playbackRetryTimer || playbackRequest" in source
    assert "if (!mutedFallbackApplied)" in source
    assert "await sleep(lastTaskWasVideo ? 1 : formStore.forminput.interval)" in source
    assert "new playerWindow.MouseEvent" not in source
    assert "scheduleMouseMovement" not in source


def test_image_captcha_detection_pauses_the_runtime():
    source = SCRIPT.read_text(encoding="utf-8")

    assert "input[placeholder*=\"验证码\"]" in source
    assert "frame.contentDocument" in source
    assert "lifecycleRuntime.verificationBlocked = true" in source
