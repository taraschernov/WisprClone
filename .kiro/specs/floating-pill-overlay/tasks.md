# YapClean Floating Pill Overlay — Implementation Tasks

## Phase 1: Core Widget

- [ ] 1. Create `ui/pill_overlay.py` — PillOverlay class skeleton
  - [ ] 1.1 Create `PillOverlay` class with `queue.Queue` + daemon thread architecture
  - [ ] 1.2 Implement `_run()` — starts `tk.Tk()` mainloop in daemon thread
  - [ ] 1.3 Implement `_setup_window()` — frameless, topmost, alpha=0, positioned bottom-center
  - [ ] 1.4 Implement platform-specific no-focus-steal: Windows (WS_EX_NOACTIVATE), macOS (-type utility), Linux (-type dock)
  - [ ] 1.5 Implement `set_state(state, persona, error)` — thread-safe via queue
  - [ ] 1.6 Implement `set_amplitude(rms)` — thread-safe via queue
  - [ ] 1.7 Implement `_process_queue()` — drains queue in tkinter thread via `after()`
  - [ ] 1.8 Implement `destroy()` — graceful shutdown

- [ ] 2. Implement pill Canvas drawing
  - [ ] 2.1 Draw rounded rectangle (pill shape) on `tk.Canvas` — background `#1C1C1E`
  - [ ] 2.2 Draw app name text (left side, truncated to 20 chars)
  - [ ] 2.3 Draw status text area (right side — timer or state label)
  - [ ] 2.4 Implement `_update_canvas()` — redraws all elements on state change

- [ ] 3. Implement WaveformAnimator
  - [ ] 3.1 Create `WaveformAnimator` class with 12 bars on Canvas
  - [ ] 3.2 Implement `update_amplitude(rms)` — scales rms, generates target bar heights with center-weighted distribution
  - [ ] 3.3 Implement `tick()` — smooth interpolation (lerp 0.3) toward target heights, redraws bars
  - [ ] 3.4 Implement idle animation — slow sine wave when amplitude = 0
  - [ ] 3.5 Wire animation loop: `root.after(33, tick)` — 30fps

- [ ] 4. Implement state rendering
  - [ ] 4.1 `recording` state — purple accent, waveform + timer (M:SS format, increments every second)
  - [ ] 4.2 `transcribing` state — blue accent, fading waveform + "Transcribing..." text
  - [ ] 4.3 `formatting` state — amber accent, 3-dot spinner animation + "Formatting..." text
  - [ ] 4.4 `done` state (success) — green accent, checkmark ✓ + persona name
  - [ ] 4.5 `done` state (error) — red accent, ✗ + error text
  - [ ] 4.6 `hidden` state — fade-out 250ms then `withdraw()`

- [ ] 5. Implement fade in/out animations
  - [ ] 5.1 `_fade_in(duration_ms=150)` — alpha 0→1 in 10 steps
  - [ ] 5.2 `_fade_out(duration_ms=250, callback)` — alpha 1→0 in 10 steps, calls callback when done
  - [ ] 5.3 Auto-hide after done state: 1500ms delay then fade_out → hidden

---

## Phase 2: Integration

- [ ] 6. Update `audio_manager.py` — add amplitude callback
  - [ ] 6.1 Add `self.amplitude_callback = None` to `__init__`
  - [ ] 6.2 In `callback()`, compute RMS and call `amplitude_callback(rms)` if set

- [ ] 7. Update `main.py` — wire PillOverlay
  - [ ] 7.1 Instantiate `PillOverlay` in `App.__init__` if `show_pill_overlay` is True
  - [ ] 7.2 Set `self.audio.amplitude_callback = self.pill.set_amplitude`
  - [ ] 7.3 Call `self.pill.set_state("recording")` in `on_hotkey_press`
  - [ ] 7.4 Call `self.pill.set_state("transcribing")` in `on_hotkey_release`
  - [ ] 7.5 Call `self.pill.destroy()` in `on_exit`
  - [ ] 7.6 Pass `pill` instance to `Pipeline` constructor

- [ ] 8. Update `core/pipeline.py` — add pill state transitions
  - [ ] 8.1 Add `pill` parameter to `Pipeline.__init__`
  - [ ] 8.2 Call `pill.set_state("formatting")` before LLM refine call
  - [ ] 8.3 Call `pill.set_state("done", persona=persona)` after successful inject
  - [ ] 8.4 Call `pill.set_state("done", error=str(e))` in exception handler

- [ ] 9. Update `settings_ui.py` — add toggle
  - [ ] 9.1 Add `show_pill_overlay` checkbox to General tab using `t("settings.pill_overlay")`
  - [ ] 9.2 Save `show_pill_overlay` in `save_and_close()`

- [ ] 10. Update `storage/config_manager.py` — add default
  - [ ] 10.1 Add `"show_pill_overlay": True` to `_load_default_settings()`

- [ ] 11. Update i18n locale files
  - [ ] 11.1 Add `pill.*` and `settings.pill_overlay` keys to `i18n/locales/en.json`
  - [ ] 11.2 Add Russian translations to `i18n/locales/ru.json`

---

## Phase 3: Polish & Testing

- [ ] 12. Platform testing and fixes
  - [ ] 12.1 Test on Windows 10/11 — verify no focus steal, correct DPI positioning
  - [ ] 12.2 Test on macOS — verify topmost, no dock icon, Cmd+V still works after overlay
  - [ ] 12.3 Test on Linux (X11) — verify -type dock attribute works

- [ ] 13. Write tests
  - [ ] 13.1 `tests/test_pill_overlay.py` — CP: state machine valid transitions only
  - [ ] 13.2 CP: `set_state('hidden')` is idempotent
  - [ ] 13.3 CP: app name truncation (≤20 chars unchanged, >20 chars truncated to 21 with …)
  - [ ] 13.4 CP: pipeline result identical with `show_pill_overlay=False` vs `True`
