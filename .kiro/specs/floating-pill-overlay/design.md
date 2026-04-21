# YapClean Floating Pill Overlay — Design Document

## 1. Overview

A frameless, always-on-top floating window that appears at the bottom-center of the screen during voice dictation. Implemented as a pure tkinter `Toplevel` window with a Canvas-drawn pill shape and animated waveform bars. No external GUI dependencies beyond what is already in the project.

---

## 2. Architecture

```
main.py (App)
    │
    ├── PillOverlay (ui/pill_overlay.py)
    │       ├── set_state(state)          ← called by App and Pipeline
    │       ├── set_amplitude(rms)        ← called by AudioManager callback
    │       └── _AnimationLoop (thread)
    │
    ├── AudioManager  ──amplitude_callback──► PillOverlay.set_amplitude()
    │
    └── Pipeline  ──set_state('formatting')──► PillOverlay
                  ──set_state('done', persona)──► PillOverlay
```

### State Machine

```
hidden ──[hotkey press]──► recording
recording ──[hotkey release]──► transcribing
transcribing ──[STT done]──► formatting
formatting ──[LLM done]──► done
done ──[1.5s timeout]──► hidden (fade-out)

Any state ──[error]──► done(error) ──► hidden
```

---

## 3. Module: `ui/pill_overlay.py`

### 3.1 Class: `PillOverlay`

```python
class PillOverlay:
    """
    Floating pill-shaped overlay widget.
    Runs its own tkinter Toplevel in a dedicated daemon thread.
    Communicates with main thread via thread-safe queue.
    """

    def __init__(self):
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def set_state(self, state: str, persona: str = "", error: str = "") -> None:
        """Thread-safe. Called from any thread."""
        self._queue.put(("state", state, persona, error))

    def set_amplitude(self, rms: float) -> None:
        """Thread-safe. Called from AudioManager callback thread."""
        self._queue.put(("amplitude", rms))

    def destroy(self) -> None:
        self._queue.put(("quit",))
```

### 3.2 Window Setup

```python
def _setup_window(self, root: tk.Tk):
    self._win = tk.Toplevel(root)
    self._win.overrideredirect(True)          # no title bar
    self._win.attributes('-topmost', True)    # always on top
    self._win.attributes('-alpha', 0.0)       # start invisible

    # Platform-specific: prevent focus steal
    import platform
    if platform.system() == "Windows":
        import ctypes
        hwnd = ctypes.windll.user32.GetParent(self._win.winfo_id())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
        # WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TRANSPARENT
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x08000000 | 0x00000080 | 0x00000020)
    elif platform.system() == "Darwin":
        self._win.attributes('-type', 'utility')  # macOS: no dock icon
    elif platform.system() == "Linux":
        try:
            self._win.attributes('-type', 'dock')
        except Exception:
            pass  # some WMs don't support this
```

### 3.3 Visual Design

**Pill dimensions:** 380 × 56 px  
**Corner radius:** 28 px (full pill)  
**Background:** `#1C1C1E` (dark, like Spokenly)  
**Font:** System default, 13px

**Layout (left to right):**
```
[ app_icon? ] [ app_name ]  [ waveform bars ]  [ timer / status text ]
   8px pad      ~80px          ~160px                ~80px        8px pad
```

**State colors:**
| State | Accent color | Waveform color |
|-------|-------------|----------------|
| recording | `#7C3AED` (purple) | `#A78BFA` |
| transcribing | `#2563EB` (blue) | `#60A5FA` |
| formatting | `#D97706` (amber) | `#FCD34D` |
| done (ok) | `#059669` (green) | — |
| done (error) | `#DC2626` (red) | — |

### 3.4 Waveform Animation

```python
BAR_COUNT = 12
BAR_WIDTH = 4
BAR_GAP = 3
BAR_MAX_HEIGHT = 28
BAR_MIN_HEIGHT = 4

class WaveformAnimator:
    def __init__(self, canvas, x_center, y_center, color):
        self._bars = []          # canvas rectangle IDs
        self._heights = [BAR_MIN_HEIGHT] * BAR_COUNT
        self._target_heights = [BAR_MIN_HEIGHT] * BAR_COUNT
        self._amplitude = 0.0

    def update_amplitude(self, rms: float):
        """Called at ~30fps. rms in [0.0, 1.0]."""
        self._amplitude = min(rms * 8, 1.0)  # scale up
        # Generate target heights: center bars taller, edges shorter
        for i in range(BAR_COUNT):
            center_factor = 1.0 - abs(i - BAR_COUNT/2) / (BAR_COUNT/2) * 0.4
            noise = random.uniform(0.7, 1.3)
            h = BAR_MIN_HEIGHT + (BAR_MAX_HEIGHT - BAR_MIN_HEIGHT) * self._amplitude * center_factor * noise
            self._target_heights[i] = h

    def tick(self):
        """Smooth interpolation toward target heights."""
        for i in range(BAR_COUNT):
            self._heights[i] += (self._target_heights[i] - self._heights[i]) * 0.3
        self._redraw()
```

**Idle animation (when amplitude = 0):** slow sine wave across bars, period ~2s.

### 3.5 Spinner Animation (formatting state)

Three dots pulsing in sequence (like iOS loading indicator):
```
● ○ ○  →  ○ ● ○  →  ○ ○ ●  →  ● ○ ○
```
Each dot: 8px circle, period 600ms.

### 3.6 Positioning

```python
def _get_position(self) -> tuple[int, int]:
    """Bottom-center of primary monitor, 60px from bottom."""
    screen_w = self._win.winfo_screenwidth()
    screen_h = self._win.winfo_screenheight()
    pill_w, pill_h = 380, 56
    x = (screen_w - pill_w) // 2
    y = screen_h - pill_h - 60
    return x, y
```

### 3.7 Fade In/Out

```python
def _fade_in(self, duration_ms=150):
    steps = 10
    for i in range(steps + 1):
        alpha = i / steps
        self._win.after(i * (duration_ms // steps),
                        lambda a=alpha: self._win.attributes('-alpha', a))

def _fade_out(self, duration_ms=250, callback=None):
    steps = 10
    for i in range(steps + 1):
        alpha = 1.0 - i / steps
        delay = i * (duration_ms // steps)
        if i == steps and callback:
            self._win.after(delay, callback)
        else:
            self._win.after(delay, lambda a=alpha: self._win.attributes('-alpha', a))
```

---

## 4. Integration Points

### 4.1 AudioManager — amplitude callback

```python
# audio_manager.py
class AudioManager:
    def __init__(self):
        ...
        self.amplitude_callback = None  # set by App

    def callback(self, indata, frames, time, status):
        if self.recording:
            self.audio_data.append(indata.copy())
            if self.amplitude_callback:
                rms = float(np.sqrt(np.mean(np.square(indata))))
                self.amplitude_callback(rms)
```

### 4.2 main.py — App wiring

```python
class App:
    def __init__(self):
        ...
        self.pill = PillOverlay() if config_manager.get("show_pill_overlay", True) else None
        if self.pill:
            self.audio.amplitude_callback = self.pill.set_amplitude

    def on_hotkey_press(self):
        ...
        if self.pill: self.pill.set_state("recording")

    def on_hotkey_release(self):
        ...
        if self.pill: self.pill.set_state("transcribing")
```

### 4.3 Pipeline — formatting and done states

```python
# core/pipeline.py
class Pipeline:
    def __init__(self, injector, app_awareness=None, persona_router=None, pill=None):
        self.pill = pill
        ...

    def process(self, audio_path, target_language=None):
        ...
        # Before LLM call:
        if self.pill: self.pill.set_state("formatting")

        # After inject:
        if self.pill: self.pill.set_state("done", persona=persona)

        # On error:
        except Exception as e:
            if self.pill: self.pill.set_state("done", error=str(e))
```

### 4.4 Settings UI

```python
# settings_ui.py — in setup_general_tab()
self.pill_overlay_var = ctk.BooleanVar(value=config_manager.get("show_pill_overlay", True))
ctk.CTkCheckBox(scroll, text=t("settings.pill_overlay"), variable=self.pill_overlay_var)

# in save_and_close():
config_manager.set("show_pill_overlay", self.pill_overlay_var.get())
```

---

## 5. i18n Keys to Add

```json
{
  "pill.transcribing": "Transcribing...",
  "pill.formatting": "Formatting...",
  "pill.done": "Done",
  "pill.error": "Error",
  "settings.pill_overlay": "Show floating overlay widget"
}
```

Russian:
```json
{
  "pill.transcribing": "Транскрибирование...",
  "pill.formatting": "Форматирование...",
  "pill.done": "Готово",
  "pill.error": "Ошибка",
  "settings.pill_overlay": "Показывать плавающий виджет"
}
```

---

## 6. Thread Safety

- `PillOverlay` runs its own `tk.Tk()` mainloop in a daemon thread
- All external calls go through `queue.Queue` — no direct tkinter calls from other threads
- The animation loop uses `root.after(33, tick)` — runs in the tkinter thread
- `set_state()` and `set_amplitude()` are the only public methods — both queue-based

---

## 7. Platform Notes

| Feature | Windows | macOS | Linux |
|---------|---------|-------|-------|
| No focus steal | `WS_EX_NOACTIVATE` via ctypes | `-type utility` | `-type dock` |
| Always on top | `-topmost True` | `-topmost True` | `-topmost True` |
| No title bar | `overrideredirect(True)` | `overrideredirect(True)` | `overrideredirect(True)` |
| Click-through | `WS_EX_TRANSPARENT` via ctypes | Not needed (small widget) | Not needed |
| DPI scaling | `ctypes.windll.shcore.SetProcessDpiAwareness(2)` | Auto | Auto |
