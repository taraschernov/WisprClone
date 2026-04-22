"""
ui/pill_overlay.py — Floating pill-shaped overlay widget for YapClean.
Inspired by Spokenly / Cursor voice overlay design.
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

# ── Geometry ───────────────────────────────────────────────────────────────────
PILL_W_REC    = 340
PILL_W_SMALL  = 180
PILL_H        = 60
CORNER_R      = 30          # full pill shape
PILL_ALPHA    = 0.95      # slightly transparent
BOTTOM_OFFSET = 90

# ── Colors ─────────────────────────────────────────────────────────────────────
BG_COLOR      = "#1A1A1C"   # slightly darker charcoal
COLOR_REC     = "#9B59F5"   # purple
COLOR_TRANS   = "#4A9EF5"   # blue
COLOR_FMT     = "#F5A623"   # amber
COLOR_OK      = "#27AE60"   # green
COLOR_ERR     = "#E74C3C"   # red
COLOR_TEXT    = "#FFFFFF"
COLOR_DIM     = "#888888"
TRANS_KEY     = "#000001"   # Chroma key for transparency

# ── Waveform / Spinner ─────────────────────────────────────────────────────────
BAR_COUNT    = 16
BAR_W        = 3
BAR_GAP      = 2
BAR_MAX_H    = 26
BAR_MIN_H    = 3

# ── Layout ─────────────────────────────────────────────────────────────────────
# We use relative positioning now for dynamic width
FONT         = ("Segoe UI Semibold", 13)
FONT_ICON    = ("Segoe UI", 18, "bold")


def _fmt_timer(sec: int) -> str:
    return f"{sec // 60}:{sec % 60:02d}"


def _truncate(s: str, n: int = 18) -> str:
    return s if len(s) <= n else s[:n] + "\u2026"


# ══════════════════════════════════════════════════════════════════════════════
class WaveformAnimator:
    def __init__(self, canvas: tk.Canvas, color: str):
        self._c = canvas
        self._color = color
        self._heights = [float(BAR_MIN_H)] * BAR_COUNT
        self._targets = [float(BAR_MIN_H)] * BAR_COUNT
        self._amp = 0.0
        self._phase = 0.0
        self._visible = False
        self._bars: list[int] = []
        self._create()

    def _create(self):
        # Initial positions, will be updated in tick()
        for i in range(BAR_COUNT):
            bid = self._c.create_rectangle(0, 0, 0, 0,
                                            fill=self._color, outline=self._color,
                                            state=tk.HIDDEN, tags="wave")
            self._bars.append(bid)

    def show(self, color: str):
        self._color = color
        self._visible = True
        for b in self._bars:
            self._c.itemconfig(b, fill=color, outline=color, state=tk.NORMAL)

    def hide(self):
        self._visible = False
        for b in self._bars:
            self._c.itemconfig(b, state=tk.HIDDEN)

    def set_amp(self, rms: float):
        self._amp = min(rms * 12.0, 1.0)
        for i in range(BAR_COUNT):
            cf = 1.0 - abs(i - BAR_COUNT / 2.0) / (BAR_COUNT / 2.0) * 0.35
            n = random.uniform(0.6, 1.4)
            self._targets[i] = BAR_MIN_H + (BAR_MAX_H - BAR_MIN_H) * self._amp * cf * n

    def tick(self, cx: int, cy: int):
        if not self._visible:
            return
        if self._amp < 0.02:
            self._phase += 0.08
            for i in range(BAR_COUNT):
                s = (math.sin(self._phase + i / BAR_COUNT * math.pi * 2) + 1) / 2
                self._targets[i] = BAR_MIN_H + (BAR_MAX_H * 0.35 - BAR_MIN_H) * s
        for i in range(BAR_COUNT):
            self._heights[i] += (self._targets[i] - self._heights[i]) * 0.4
        
        total = BAR_COUNT * BAR_W + (BAR_COUNT - 1) * BAR_GAP
        x0 = cx - total // 2
        for i, bid in enumerate(self._bars):
            h = max(BAR_MIN_H, self._heights[i])
            x = x0 + i * (BAR_W + BAR_GAP)
            self._c.coords(bid, x, cy - h / 2, x + BAR_W, cy + h / 2)


# ══════════════════════════════════════════════════════════════════════════════
class PillOverlay:
    def __init__(self):
        self._q: queue.Queue = queue.Queue()
        self._t = threading.Thread(target=self._run, daemon=True, name="PillOverlay")
        self._t.start()

    # ── Public API (thread-safe) ───────────────────────────────────────────────
    def set_state(self, state: str, persona: str = "", error: str = ""):
        self._q.put(("state", state, persona, error))

    def set_amplitude(self, rms: float):
        self._q.put(("amp", rms))

    def destroy(self):
        self._q.put(("quit",))

    # ── Tkinter thread ─────────────────────────────────────────────────────────
    def _run(self):
        try:
            self._root = tk.Tk()
            self._root.withdraw()
            self._state = "hidden"
            self._persona = ""
            self._error = ""
            self._width = PILL_W_REC
            self._target_width = PILL_W_REC
            self._rec_start: Optional[float] = None
            self._timer_id: Optional[str] = None
            self._spinner_id: Optional[str] = None
            self._spinner_step = 0
            self._autohide_id: Optional[str] = None
            self._wave: Optional[WaveformAnimator] = None
            self._setup_win()
            self._build()
            self._poll()
            self._root.mainloop()
        except Exception as e:
            logger.error(f"PillOverlay crashed: {e}", exc_info=True)

    def _setup_win(self):
        self._win = tk.Toplevel(self._root)
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        self._win.attributes("-alpha", 0.0)
        self._win.resizable(False, False)
        self._win.configure(bg=TRANS_KEY)

        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()

        from storage.config_manager import config_manager
        saved_x = config_manager.get("pill_x")
        saved_y = config_manager.get("pill_y")
        if saved_x is not None and saved_y is not None:
            x, y = int(saved_x), int(saved_y)
        else:
            x = (sw - PILL_W_REC) // 2
            y = sh - PILL_H - BOTTOM_OFFSET

        self._win.geometry(f"{PILL_W_REC}x{PILL_H}+{x}+{y}")
        self._drag_x = 0
        self._drag_y = 0

        # Windows transparency and no-focus
        sys = platform.system()
        if sys == "Windows":
            try:
                import ctypes
                try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
                except: pass
                # Set transparency key
                self._win.attributes("-transparentcolor", TRANS_KEY)
                
                hwnd = ctypes.windll.user32.GetParent(self._win.winfo_id())
                style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
                # WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_LAYERED
                ctypes.windll.user32.SetWindowLongW(hwnd, -20,
                    style | 0x08000000 | 0x00000080 | 0x00000020)
            except Exception as e:
                logger.warning(f"Win no-focus/transparency: {e}")

        self._win.withdraw()

    def _build(self):
        self._cv = tk.Canvas(self._win, width=PILL_W_REC, height=PILL_H,
                              bg=TRANS_KEY, highlightthickness=0, bd=0)
        self._cv.pack(fill=tk.BOTH, expand=True)

        # Pill background (tags="bg")
        self._draw_pill()

        # Waveform
        self._wave = WaveformAnimator(self._cv, COLOR_REC)

        # Spinner dots
        self._dots: list[int] = []
        for i in range(3):
            d = self._cv.create_oval(0, 0, 0, 0,
                                      fill=COLOR_FMT, outline="", state=tk.HIDDEN, tags="dots")
            self._dots.append(d)

        # Done icon
        self._icon_id = self._cv.create_text(
            0, 0, text="", anchor="center",
            fill=COLOR_OK, font=FONT_ICON, tags="icon")

        # Right-side text
        self._text_id = self._cv.create_text(
            0, 0, text="", anchor="w",
            fill=COLOR_TEXT, font=FONT, tags="text")

        self._anim()

        self._cv.bind("<ButtonPress-1>", self._drag_start)
        self._cv.bind("<B1-Motion>", self._drag_move)
        self._cv.bind("<ButtonRelease-1>", self._drag_end)

    def _draw_pill(self):
        self._cv.delete("bg")
        r, w, h = CORNER_R, int(self._width), PILL_H
        pts = []
        # Left half-circle
        for a in range(90, 271, 5):
            rad = math.radians(a)
            pts += [r + r*math.cos(rad), r + r*math.sin(rad)]
        # Right half-circle
        for a in range(270, 451, 5):
            rad = math.radians(a)
            pts += [w-r + r*math.cos(rad), r + r*math.sin(rad)]
        
        self._cv.create_polygon(pts, fill=BG_COLOR, outline="#333336", width=1, tags="bg")

    # ── Queue ──────────────────────────────────────────────────────────────────
    def _poll(self):
        try:
            while True:
                msg = self._q.get_nowait()
                k = msg[0]
                if k == "state":
                    self._do_state(msg[1], msg[2], msg[3])
                elif k == "amp":
                    if self._wave and self._state in ("recording", "transcribing"):
                        self._wave.set_amp(msg[1])
                elif k == "quit":
                    self._do_destroy(); return
        except queue.Empty:
            pass
        self._root.after(16, self._poll)

    # ── State machine ──────────────────────────────────────────────────────────
    def _do_state(self, state: str, persona: str, error: str):
        if self._autohide_id:
            self._root.after_cancel(self._autohide_id)
            self._autohide_id = None
        
        prev = self._state
        self._state = state
        self._persona = persona
        self._error = error
        self._stop_timer()
        self._stop_spinner()

        if state == "recording":
            self._target_width = PILL_W_REC
            self._rec_start = time.monotonic()
            self._cv.itemconfig(self._text_id, text=_fmt_timer(0), fill=COLOR_TEXT)
            self._cv.itemconfig(self._icon_id, text="")
            self._wave.show(COLOR_REC)
            self._hide_dots()
            if prev == "hidden":
                self._win.deiconify()
                self._fade_in()
            self._start_timer()

        elif state == "transcribing":
            self._target_width = PILL_W_REC # Keep wide for the text
            self._cv.itemconfig(self._text_id, text=t("pill.transcribing"), fill=COLOR_DIM)
            self._cv.itemconfig(self._icon_id, text="")
            self._wave.show(COLOR_TRANS)
            self._hide_dots()

        elif state == "formatting":
            self._target_width = PILL_W_SMALL
            self._cv.itemconfig(self._text_id, text="", fill=COLOR_DIM)
            self._cv.itemconfig(self._icon_id, text="")
            self._wave.hide()
            self._show_dots()
            self._start_spinner()

        elif state == "done":
            self._target_width = PILL_W_REC if error else PILL_W_SMALL
            self._wave.hide()
            self._hide_dots()
            if error:
                self._cv.itemconfig(self._icon_id, text="\u2717", fill=COLOR_ERR)
                self._cv.itemconfig(self._text_id, text=_truncate(error, 16), fill=COLOR_ERR)
            else:
                self._cv.itemconfig(self._icon_id, text="\u2713", fill=COLOR_OK)
                # For success, just show the checkmark or persona very briefly
                label = _truncate(persona) if persona else ""
                self._cv.itemconfig(self._text_id, text=label, fill=COLOR_TEXT)
            
            self._autohide_id = self._root.after(2200, self._auto_hide)

        elif state == "hidden":
            self._fade_out(cb=lambda: self._win.withdraw())

    # ── Timer ──────────────────────────────────────────────────────────────────
    def _start_timer(self):
        self._tick_timer()

    def _tick_timer(self):
        if self._state != "recording": return
        elapsed = int(time.monotonic() - (self._rec_start or time.monotonic()))
        self._cv.itemconfig(self._text_id, text=_fmt_timer(elapsed))
        self._timer_id = self._root.after(1000, self._tick_timer)

    def _stop_timer(self):
        if self._timer_id:
            self._root.after_cancel(self._timer_id)
            self._timer_id = None

    # ── Spinner ────────────────────────────────────────────────────────────────
    def _show_dots(self):
        for d in self._dots: self._cv.itemconfig(d, state=tk.NORMAL)

    def _hide_dots(self):
        for d in self._dots: self._cv.itemconfig(d, state=tk.HIDDEN)

    def _start_spinner(self):
        self._spinner_step = 0
        self._tick_spinner()

    def _tick_spinner(self):
        if self._state != "formatting": return
        for i, d in enumerate(self._dots):
            self._cv.itemconfig(d, fill=COLOR_FMT if i == self._spinner_step % 3 else "#4a3800")
        self._spinner_step += 1
        self._spinner_id = self._root.after(250, self._tick_spinner)

    def _stop_spinner(self):
        if self._spinner_id:
            self._root.after_cancel(self._spinner_id)
            self._spinner_id = None

    # ── Animation ──────────────────────────────────────────────────────────────
    def _anim(self):
        # 1. Smooth width transition
        if abs(self._width - self._target_width) > 1:
            diff = self._target_width - self._width
            self._width += diff * 0.15
            # Center the window relative to its previous center
            cx = self._win.winfo_x() + self._win.winfo_width() // 2
            new_x = cx - int(self._width) // 2
            self._win.geometry(f"{int(self._width)}x{PILL_H}+{new_x}+{self._win.winfo_y()}")
            self._cv.config(width=int(self._width))
            self._draw_pill()

        # 2. Update element positions based on current width
        mid_x = self._width / 2
        mid_y = PILL_H / 2

        if self._state in ("recording", "transcribing"):
            # Waveform left of center, text right of center
            self._wave.tick(mid_x - 30, mid_y)
            self._cv.coords(self._text_id, mid_x + 30, mid_y)
            self._cv.itemconfig(self._text_id, anchor="w")
        elif self._state == "formatting":
            # Dots centered
            for i, d in enumerate(self._dots):
                dx = mid_x - 16 + i * 16
                self._cv.coords(d, dx-5, mid_y-5, dx+5, mid_y+5)
        elif self._state == "done":
            # Icon centered or icon+text
            if self._cv.itemcget(self._text_id, "text"):
                self._cv.coords(self._icon_id, mid_x - 40, mid_y)
                self._cv.coords(self._text_id, mid_x - 10, mid_y)
                self._cv.itemconfig(self._text_id, anchor="w")
            else:
                self._cv.coords(self._icon_id, mid_x, mid_y)

        self._root.after(20, self._anim)

    # ── Fade ───────────────────────────────────────────────────────────────────
    def _fade_in(self, ms: int = 200):
        steps = 10
        for i in range(steps + 1):
            a = (i / steps) * PILL_ALPHA
            self._root.after(i * (ms // steps), lambda v=a: self._win.attributes("-alpha", v) if self._win.winfo_exists() else None)

    def _fade_out(self, ms: int = 250, cb=None):
        steps = 10
        for i in range(steps + 1):
            a = PILL_ALPHA * (1 - i / steps)
            delay = i * (ms // steps)
            if i == steps:
                if cb: self._root.after(delay, cb)
            else:
                self._root.after(delay, lambda v=a: self._win.attributes("-alpha", v) if self._win.winfo_exists() else None)

    def _auto_hide(self):
        self._autohide_id = None
        self._fade_out(cb=lambda: (setattr(self, "_state", "hidden"), self._win.withdraw() if self._win.winfo_exists() else None))

    # ── Drag to move ───────────────────────────────────────────────────────────
    def _drag_start(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _drag_move(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self._win.winfo_x() + dx
        y = self._win.winfo_y() + dy
        self._win.geometry(f"+{x}+{y}")

    def _drag_end(self, event):
        try:
            from storage.config_manager import config_manager
            config_manager.set("pill_x", self._win.winfo_x())
            config_manager.set("pill_y", self._win.winfo_y())
        except Exception:
            pass

    # ── Destroy ────────────────────────────────────────────────────────────────
    def _do_destroy(self):
        self._stop_timer()
        self._stop_spinner()
        try:
            self._root.quit()
            self._root.destroy()
        except: pass
