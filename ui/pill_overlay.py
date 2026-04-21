"""
ui/pill_overlay.py — Floating pill-shaped overlay widget for YapClean.

Runs its own tkinter Toplevel in a dedicated daemon thread.
All external calls are thread-safe via queue.Queue.
"""

import math
import platform
import queue
import random
import threading
import time
import tkinter as tk
from typing import Optional

from i18n.translator import t
from utils.logger import get_logger

logger = get_logger("yapclean.pill_overlay")

# ── Pill geometry ──────────────────────────────────────────────────────────────
PILL_W = 420
PILL_H = 64
CORNER_R = 32
BOTTOM_OFFSET = 80       # higher above taskbar
PILL_ALPHA = 0.92        # semi-transparent

# ── Font ───────────────────────────────────────────────────────────────────────
FONT_MAIN = ("Segoe UI", 14)
FONT_BOLD = ("Segoe UI", 14, "bold")

# ── Colors ─────────────────────────────────────────────────────────────────────
BG_COLOR = "#1C1C1E"
COLOR_RECORDING = "#7C3AED"
COLOR_TRANSCRIBING = "#2563EB"
COLOR_FORMATTING = "#D97706"
COLOR_DONE_OK = "#059669"
COLOR_DONE_ERR = "#DC2626"
COLOR_TEXT = "#FFFFFF"
COLOR_TEXT_DIM = "#AAAAAA"

WAVEFORM_COLORS = {
    "recording": "#A78BFA",
    "transcribing": "#60A5FA",
    "formatting": "#FCD34D",
}

# ── Waveform constants ─────────────────────────────────────────────────────────
BAR_COUNT = 12
BAR_WIDTH = 4
BAR_GAP = 3
BAR_MAX_HEIGHT = 28
BAR_MIN_HEIGHT = 4

# ── Layout x-positions ─────────────────────────────────────────────────────────
APP_NAME_X = 16
APP_NAME_MAX_W = 90
WAVEFORM_X_CENTER = 190   # center of waveform zone
WAVEFORM_Y_CENTER = PILL_H // 2
STATUS_X = 310            # right-side status text anchor
TIMER_X = 350


# ── Helpers ────────────────────────────────────────────────────────────────────

def _truncate(name: str, max_chars: int = 20) -> str:
    """Truncate app name to max_chars, appending … if needed."""
    if len(name) <= max_chars:
        return name
    return name[:max_chars] + "\u2026"


def _format_timer(seconds: int) -> str:
    m = seconds // 60
    s = seconds % 60
    return f"{m}:{s:02d}"


# ══════════════════════════════════════════════════════════════════════════════
# WaveformAnimator
# ══════════════════════════════════════════════════════════════════════════════

class WaveformAnimator:
    """Draws and animates 12 vertical bars on a Canvas."""

    def __init__(self, canvas: tk.Canvas, x_center: int, y_center: int, color: str):
        self._canvas = canvas
        self._x_center = x_center
        self._y_center = y_center
        self._color = color
        self._bars: list[int] = []          # canvas item IDs
        self._heights = [float(BAR_MIN_HEIGHT)] * BAR_COUNT
        self._target_heights = [float(BAR_MIN_HEIGHT)] * BAR_COUNT
        self._amplitude = 0.0
        self._idle_phase = 0.0             # for sine idle animation
        self._visible = True
        self._fade_alpha = 1.0             # 0.0 → 1.0 for transcribing fade
        self._create_bars()

    # ── public ────────────────────────────────────────────────────────────────

    def set_color(self, color: str) -> None:
        self._color = color
        for bar_id in self._bars:
            self._canvas.itemconfig(bar_id, fill=color, outline=color)

    def set_visible(self, visible: bool) -> None:
        self._visible = visible
        state = tk.NORMAL if visible else tk.HIDDEN
        for bar_id in self._bars:
            self._canvas.itemconfig(bar_id, state=state)

    def set_fade(self, alpha: float) -> None:
        """alpha in [0,1] — used for transcribing fade-out effect."""
        self._fade_alpha = max(0.0, min(1.0, alpha))
        # Blend bar color toward BG_COLOR
        self._apply_fade_color()

    def update_amplitude(self, rms: float) -> None:
        """Called at ~30fps. rms in [0.0, 1.0]."""
        self._amplitude = min(rms * 8.0, 1.0)
        for i in range(BAR_COUNT):
            center_factor = 1.0 - abs(i - BAR_COUNT / 2.0) / (BAR_COUNT / 2.0) * 0.4
            noise = random.uniform(0.7, 1.3)
            h = BAR_MIN_HEIGHT + (BAR_MAX_HEIGHT - BAR_MIN_HEIGHT) * self._amplitude * center_factor * noise
            self._target_heights[i] = h

    def tick(self) -> None:
        """Smooth lerp toward target heights, then redraw."""
        if self._amplitude < 0.01:
            # Idle sine wave
            self._idle_phase += 0.08
            for i in range(BAR_COUNT):
                phase_offset = i / BAR_COUNT * math.pi * 2
                sine_val = (math.sin(self._idle_phase + phase_offset) + 1.0) / 2.0
                idle_h = BAR_MIN_HEIGHT + (BAR_MAX_HEIGHT * 0.25 - BAR_MIN_HEIGHT) * sine_val
                self._target_heights[i] = idle_h

        for i in range(BAR_COUNT):
            self._heights[i] += (self._target_heights[i] - self._heights[i]) * 0.3

        self._redraw()

    # ── private ───────────────────────────────────────────────────────────────

    def _create_bars(self) -> None:
        total_w = BAR_COUNT * BAR_WIDTH + (BAR_COUNT - 1) * BAR_GAP
        x0 = self._x_center - total_w // 2
        for i in range(BAR_COUNT):
            x = x0 + i * (BAR_WIDTH + BAR_GAP)
            bar_id = self._canvas.create_rectangle(
                x, self._y_center, x + BAR_WIDTH, self._y_center,
                fill=self._color, outline=self._color, tags="waveform"
            )
            self._bars.append(bar_id)

    def _redraw(self) -> None:
        if not self._visible:
            return
        total_w = BAR_COUNT * BAR_WIDTH + (BAR_COUNT - 1) * BAR_GAP
        x0 = self._x_center - total_w // 2
        for i, bar_id in enumerate(self._bars):
            h = max(BAR_MIN_HEIGHT, self._heights[i])
            x = x0 + i * (BAR_WIDTH + BAR_GAP)
            y1 = self._y_center - h / 2
            y2 = self._y_center + h / 2
            self._canvas.coords(bar_id, x, y1, x + BAR_WIDTH, y2)

    def _apply_fade_color(self) -> None:
        """Blend bar color toward background based on fade_alpha."""
        def _blend(hex_fg: str, hex_bg: str, alpha: float) -> str:
            def _parse(h: str):
                h = h.lstrip("#")
                return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            fr, fg, fb = _parse(hex_fg)
            br, bg, bb = _parse(hex_bg)
            r = int(fr * alpha + br * (1 - alpha))
            g = int(fg * alpha + bg * (1 - alpha))
            b = int(fb * alpha + bb * (1 - alpha))
            return f"#{r:02x}{g:02x}{b:02x}"

        blended = _blend(self._color, BG_COLOR, self._fade_alpha)
        for bar_id in self._bars:
            self._canvas.itemconfig(bar_id, fill=blended, outline=blended)


# ══════════════════════════════════════════════════════════════════════════════
# PillOverlay
# ══════════════════════════════════════════════════════════════════════════════

class PillOverlay:
    """
    Floating pill-shaped overlay widget.
    Runs its own tkinter Toplevel in a dedicated daemon thread.
    Communicates with main thread via thread-safe queue.
    """

    def __init__(self) -> None:
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True, name="PillOverlay")
        self._thread.start()

    # ── Public thread-safe API ─────────────────────────────────────────────────

    def set_state(self, state: str, persona: str = "", error: str = "") -> None:
        """Thread-safe. Called from any thread."""
        self._queue.put(("state", state, persona, error))

    def set_amplitude(self, rms: float) -> None:
        """Thread-safe. Called from AudioManager callback thread."""
        self._queue.put(("amplitude", rms))

    def destroy(self) -> None:
        """Thread-safe graceful shutdown."""
        self._queue.put(("quit",))

    # ── Tkinter thread ─────────────────────────────────────────────────────────

    def _run(self) -> None:
        """Runs entirely in the daemon thread — owns the tkinter mainloop."""
        try:
            self._root = tk.Tk()
            self._root.withdraw()  # hide root window; we use Toplevel

            self._state = "hidden"
            self._app_name = ""
            self._persona = ""
            self._error = ""
            self._recording_start: Optional[float] = None
            self._timer_after_id: Optional[str] = None
            self._spinner_after_id: Optional[str] = None
            self._spinner_step = 0
            self._waveform: Optional[WaveformAnimator] = None
            self._transcribing_fade = 1.0
            self._autohide_after_id: Optional[str] = None

            self._setup_window()
            self._build_canvas()
            self._process_queue()
            self._root.mainloop()
        except Exception as e:
            logger.error(f"PillOverlay thread crashed: {e}", exc_info=True)

    def _setup_window(self) -> None:
        self._win = tk.Toplevel(self._root)
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        self._win.attributes("-alpha", 0.0)
        self._win.resizable(False, False)

        x, y = self._get_position()
        self._win.geometry(f"{PILL_W}x{PILL_H}+{x}+{y}")
        sys_name = platform.system()
        if sys_name == "Windows":
            try:
                import ctypes
                # DPI awareness
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(2)
                except Exception:
                    pass
                hwnd = ctypes.windll.user32.GetParent(self._win.winfo_id())
                GWL_EXSTYLE = -20
                WS_EX_NOACTIVATE = 0x08000000
                WS_EX_TOOLWINDOW = 0x00000080
                WS_EX_TRANSPARENT = 0x00000020
                style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(
                    hwnd, GWL_EXSTYLE,
                    style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TRANSPARENT
                )
            except Exception as e:
                logger.warning(f"Windows no-focus-steal setup failed: {e}")
        elif sys_name == "Darwin":
            try:
                self._win.attributes("-type", "utility")
            except Exception:
                pass
        elif sys_name == "Linux":
            try:
                self._win.attributes("-type", "dock")
            except Exception:
                pass

        self._win.withdraw()  # start hidden

    def _get_position(self) -> tuple[int, int]:
        screen_w = self._win.winfo_screenwidth()
        screen_h = self._win.winfo_screenheight()
        x = (screen_w - PILL_W) // 2
        y = screen_h - PILL_H - BOTTOM_OFFSET
        return x, y

    def _build_canvas(self) -> None:
        self._canvas = tk.Canvas(
            self._win,
            width=PILL_W, height=PILL_H,
            bg=BG_COLOR, highlightthickness=0, bd=0
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)

        # ── Pill background (rounded rectangle via polygon) ──────────────────
        self._pill_bg = self._draw_pill(BG_COLOR)

        # ── App name text ────────────────────────────────────────────────────
        self._app_name_id = self._canvas.create_text(
            APP_NAME_X, PILL_H // 2,
            text="", anchor="w",
            fill=COLOR_TEXT_DIM, font=FONT_MAIN
        )

        # ── Status / timer text (right side) ─────────────────────────────────
        self._status_text_id = self._canvas.create_text(
            TIMER_X, PILL_H // 2,
            text="", anchor="e",
            fill=COLOR_TEXT, font=FONT_MAIN
        )

        # ── Waveform animator ─────────────────────────────────────────────────
        self._waveform = WaveformAnimator(
            self._canvas, WAVEFORM_X_CENTER, WAVEFORM_Y_CENTER,
            WAVEFORM_COLORS["recording"]
        )
        self._waveform.set_visible(False)

        # ── Spinner dots ──────────────────────────────────────────────────────
        self._dot_ids: list[int] = []
        dot_spacing = 14
        dot_r = 4
        dot_y = PILL_H // 2
        dot_x_start = WAVEFORM_X_CENTER - dot_spacing
        for i in range(3):
            cx = dot_x_start + i * dot_spacing
            dot_id = self._canvas.create_oval(
                cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r,
                fill=COLOR_FORMATTING, outline="", state=tk.HIDDEN
            )
            self._dot_ids.append(dot_id)

        # ── Done icon (checkmark / X) ─────────────────────────────────────────
        self._done_icon_id = self._canvas.create_text(
            WAVEFORM_X_CENTER - 20, PILL_H // 2,
            text="", anchor="center",
            fill=COLOR_DONE_OK, font=("Segoe UI", 18, "bold")
        )

        # ── Accent line at bottom of pill ─────────────────────────────────────
        self._accent_line_id = self._canvas.create_rectangle(
            CORNER_R, PILL_H - 3, PILL_W - CORNER_R, PILL_H - 1,
            fill=COLOR_RECORDING, outline="", state=tk.HIDDEN
        )

        # Start animation loop
        self._animation_tick()

    def _draw_pill(self, color: str) -> int:
        """Draw a rounded-rectangle pill shape and return its canvas item ID."""
        r = CORNER_R
        w, h = PILL_W, PILL_H
        # Build polygon points for a pill shape
        points = []
        # Top-left arc
        for angle in range(90, 181, 5):
            rad = math.radians(angle)
            points += [r + r * math.cos(rad), r + r * math.sin(rad)]
        # Bottom-left arc
        for angle in range(180, 271, 5):
            rad = math.radians(angle)
            points += [r + r * math.cos(rad), h - r + r * math.sin(rad)]
        # Bottom-right arc
        for angle in range(270, 361, 5):
            rad = math.radians(angle)
            points += [w - r + r * math.cos(rad), h - r + r * math.sin(rad)]
        # Top-right arc
        for angle in range(0, 91, 5):
            rad = math.radians(angle)
            points += [w - r + r * math.cos(rad), r + r * math.sin(rad)]

        return self._canvas.create_polygon(
            points, fill=color, outline=color, smooth=False, tags="pill_bg"
        )

    # ── Queue processing ───────────────────────────────────────────────────────

    def _process_queue(self) -> None:
        """Drain the queue in the tkinter thread. Reschedules itself via after()."""
        try:
            while True:
                msg = self._queue.get_nowait()
                self._handle_message(msg)
        except queue.Empty:
            pass
        self._root.after(16, self._process_queue)

    def _handle_message(self, msg: tuple) -> None:
        kind = msg[0]
        if kind == "state":
            _, state, persona, error = msg
            self._apply_state(state, persona, error)
        elif kind == "amplitude":
            _, rms = msg
            if self._waveform and self._state in ("recording", "transcribing"):
                self._waveform.update_amplitude(rms)
        elif kind == "quit":
            self._do_destroy()

    # ── State machine ──────────────────────────────────────────────────────────

    def _apply_state(self, state: str, persona: str, error: str) -> None:
        prev = self._state

        # Cancel any pending autohide
        if self._autohide_after_id:
            self._root.after_cancel(self._autohide_after_id)
            self._autohide_after_id = None

        self._state = state
        self._persona = persona
        self._error = error

        # Stop timers/spinners from previous state
        self._stop_timer()
        self._stop_spinner()

        if state == "recording":
            self._handle_recording_state(prev)
        elif state == "transcribing":
            self._handle_transcribing_state()
        elif state == "formatting":
            self._handle_formatting_state()
        elif state == "done":
            self._handle_done_state()
        elif state == "hidden":
            self._handle_hidden_state()

    def _handle_recording_state(self, prev_state: str) -> None:
        # Capture active app name
        try:
            from core.app_awareness import AppAwarenessManager
            self._app_name = AppAwarenessManager().get_active_process()
        except Exception:
            self._app_name = ""

        self._recording_start = time.monotonic()
        self._transcribing_fade = 1.0

        self._update_canvas_recording()

        if prev_state == "hidden":
            self._win.deiconify()
            self._fade_in()
        else:
            self._win.deiconify()

        self._start_timer()

    def _handle_transcribing_state(self) -> None:
        self._transcribing_fade = 1.0
        self._update_canvas_transcribing()
        self._start_transcribing_fade()

    def _handle_formatting_state(self) -> None:
        self._update_canvas_formatting()
        self._start_spinner()

    def _handle_done_state(self) -> None:
        self._update_canvas_done()
        # Auto-hide after 1500ms
        self._autohide_after_id = self._root.after(1500, self._auto_hide)

    def _handle_hidden_state(self) -> None:
        self._fade_out(callback=lambda: self._win.withdraw())

    # ── Canvas update helpers ──────────────────────────────────────────────────

    def _update_canvas_recording(self) -> None:
        accent = COLOR_RECORDING
        self._set_accent(accent)
        self._canvas.itemconfig(self._app_name_id, text=_truncate(self._app_name), fill=COLOR_TEXT_DIM)
        self._canvas.itemconfig(self._status_text_id, text=_format_timer(0))
        self._waveform.set_color(WAVEFORM_COLORS["recording"])
        self._waveform.set_visible(True)
        self._waveform.set_fade(1.0)
        self._hide_spinner()
        self._canvas.itemconfig(self._done_icon_id, text="")

    def _update_canvas_transcribing(self) -> None:
        accent = COLOR_TRANSCRIBING
        self._set_accent(accent)
        self._canvas.itemconfig(self._app_name_id, text=_truncate(self._app_name), fill=COLOR_TEXT_DIM)
        self._canvas.itemconfig(self._status_text_id, text=t("pill.transcribing"))
        self._waveform.set_color(WAVEFORM_COLORS["transcribing"])
        self._waveform.set_visible(True)
        self._hide_spinner()
        self._canvas.itemconfig(self._done_icon_id, text="")

    def _update_canvas_formatting(self) -> None:
        accent = COLOR_FORMATTING
        self._set_accent(accent)
        self._canvas.itemconfig(self._app_name_id, text=_truncate(self._app_name), fill=COLOR_TEXT_DIM)
        self._canvas.itemconfig(self._status_text_id, text=t("pill.formatting"))
        self._waveform.set_visible(False)
        self._canvas.itemconfig(self._done_icon_id, text="")
        self._show_spinner()

    def _update_canvas_done(self) -> None:
        is_error = bool(self._error)
        accent = COLOR_DONE_ERR if is_error else COLOR_DONE_OK
        self._set_accent(accent)
        self._canvas.itemconfig(self._app_name_id, text=_truncate(self._app_name), fill=COLOR_TEXT_DIM)
        self._waveform.set_visible(False)
        self._hide_spinner()

        if is_error:
            icon = "\u2717"  # ✗
            label = _truncate(self._error, 20) if self._error else t("pill.error")
            self._canvas.itemconfig(self._done_icon_id, text=icon, fill=COLOR_DONE_ERR)
            self._canvas.itemconfig(self._status_text_id, text=label, fill=COLOR_DONE_ERR)
        else:
            icon = "\u2713"  # ✓
            label = _truncate(self._persona, 20) if self._persona else t("pill.done")
            self._canvas.itemconfig(self._done_icon_id, text=icon, fill=COLOR_DONE_OK)
            self._canvas.itemconfig(self._status_text_id, text=label, fill=COLOR_DONE_OK)

    def _set_accent(self, color: str) -> None:
        self._canvas.itemconfig(self._accent_line_id, fill=color, state=tk.NORMAL)

    # ── Timer (recording) ──────────────────────────────────────────────────────

    def _start_timer(self) -> None:
        self._tick_timer()

    def _tick_timer(self) -> None:
        if self._state != "recording":
            return
        elapsed = int(time.monotonic() - (self._recording_start or time.monotonic()))
        self._canvas.itemconfig(self._status_text_id, text=_format_timer(elapsed))
        self._timer_after_id = self._root.after(1000, self._tick_timer)

    def _stop_timer(self) -> None:
        if self._timer_after_id:
            self._root.after_cancel(self._timer_after_id)
            self._timer_after_id = None

    # ── Spinner (formatting) ───────────────────────────────────────────────────

    def _show_spinner(self) -> None:
        for dot_id in self._dot_ids:
            self._canvas.itemconfig(dot_id, state=tk.NORMAL)

    def _hide_spinner(self) -> None:
        for dot_id in self._dot_ids:
            self._canvas.itemconfig(dot_id, state=tk.HIDDEN)

    def _start_spinner(self) -> None:
        self._spinner_step = 0
        self._tick_spinner()

    def _tick_spinner(self) -> None:
        if self._state != "formatting":
            return
        for i, dot_id in enumerate(self._dot_ids):
            if i == self._spinner_step % 3:
                self._canvas.itemconfig(dot_id, fill=COLOR_FORMATTING)
            else:
                self._canvas.itemconfig(dot_id, fill="#5a3a00")
        self._spinner_step += 1
        self._spinner_after_id = self._root.after(200, self._tick_spinner)

    def _stop_spinner(self) -> None:
        if self._spinner_after_id:
            self._root.after_cancel(self._spinner_after_id)
            self._spinner_after_id = None

    # ── Transcribing fade ──────────────────────────────────────────────────────

    def _start_transcribing_fade(self) -> None:
        self._transcribing_fade = 1.0
        self._tick_transcribing_fade()

    def _tick_transcribing_fade(self) -> None:
        if self._state != "transcribing":
            return
        self._transcribing_fade = max(0.0, self._transcribing_fade - 0.02)
        if self._waveform:
            self._waveform.set_fade(self._transcribing_fade)
        if self._transcribing_fade > 0.0:
            self._root.after(33, self._tick_transcribing_fade)

    # ── Animation loop ─────────────────────────────────────────────────────────

    def _animation_tick(self) -> None:
        """30fps animation loop — runs in tkinter thread via after()."""
        if self._waveform and self._state in ("recording", "transcribing"):
            self._waveform.tick()
        self._root.after(33, self._animation_tick)

    # ── Fade in / out ──────────────────────────────────────────────────────────

    def _fade_in(self, duration_ms: int = 150) -> None:
        steps = 10
        step_ms = max(1, duration_ms // steps)
        for i in range(steps + 1):
            alpha = (i / steps) * PILL_ALPHA
            self._root.after(i * step_ms, lambda a=alpha: self._win.attributes("-alpha", a))

    def _fade_out(self, duration_ms: int = 250, callback=None) -> None:
        steps = 10
        step_ms = max(1, duration_ms // steps)
        for i in range(steps + 1):
            alpha = PILL_ALPHA * (1.0 - i / steps)
            delay = i * step_ms
            if i == steps and callback:
                self._root.after(delay, callback)
            else:
                self._root.after(delay, lambda a=alpha: self._win.attributes("-alpha", a))

    def _auto_hide(self) -> None:
        """Called after done state timeout — fade out then withdraw."""
        self._autohide_after_id = None
        self._fade_out(duration_ms=250, callback=self._on_fade_out_done)

    def _on_fade_out_done(self) -> None:
        self._state = "hidden"
        self._win.withdraw()

    # ── Destroy ────────────────────────────────────────────────────────────────

    def _do_destroy(self) -> None:
        self._stop_timer()
        self._stop_spinner()
        try:
            self._root.quit()
            self._root.destroy()
        except Exception:
            pass
