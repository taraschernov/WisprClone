import customtkinter as ctk
from storage.config_manager import config_manager
from storage.keyring_manager import keyring_manager
from i18n.translator import t, init_translator
from utils.logger import get_logger

logger = get_logger("yapclean.onboarding")

PERSONAS = [
    "General User",
    "IT Specialist / Developer",
    "Manager / Entrepreneur",
    "Writer / Blogger / Marketer",
    "Medical / Legal / Researcher",
    "Support Specialist",
    "HR / Recruiter",
    "Teacher / Trainer",
]


class OnboardingWizard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(t("onboarding.title"))
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._step = 1
        self._mode = ctk.StringVar(value="byok")
        self._frames = {}

        self._build_header()
        self._build_step1()
        self._build_step2_byok()
        self._build_step2_local()
        self._build_step2_pro()
        self._build_step3()
        self._build_footer()
        self._show_step(1)

        w, h = 500, 560
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build_header(self):
        ctk.CTkLabel(self, text=t("onboarding.title"),
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 5))
        ctk.CTkLabel(self, text=t("onboarding.subtitle"),
                     font=ctk.CTkFont(size=13), text_color="gray").pack(pady=(0, 10))
        self._step_label = ctk.CTkLabel(self, text="Step 1 / 3",
                                         font=ctk.CTkFont(size=12), text_color="gray")
        self._step_label.pack()

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=20, pady=15)
        self._back_btn = ctk.CTkButton(footer, text=t("onboarding.btn.back"),
                                        command=self._go_back, width=100)
        self._back_btn.pack(side="left")
        self._next_btn = ctk.CTkButton(footer, text=t("onboarding.btn.next"),
                                        command=self._go_next, width=100)
        self._next_btn.pack(side="right")

    def _build_step1(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(frame, text=t("onboarding.step1.title"),
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(10, 15))

        lang_frame = ctk.CTkFrame(frame)
        lang_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(lang_frame, text="Interface language / Язык интерфейса:",
                     anchor="w").pack(fill="x", padx=10, pady=(5, 0))
        self._lang_var = ctk.StringVar(value=config_manager.get("ui_language", "en"))
        ctk.CTkOptionMenu(lang_frame, variable=self._lang_var, values=["en", "ru"],
                           command=lambda v: init_translator(v)).pack(fill="x", padx=10, pady=5)

        mode_frame = ctk.CTkFrame(frame)
        mode_frame.pack(fill="x", padx=20, pady=10)
        for mode, key in [("byok", "onboarding.step1.byok"),
                           ("local", "onboarding.step1.local"),
                           ("pro", "onboarding.step1.pro")]:
            ctk.CTkRadioButton(mode_frame, text=t(key), variable=self._mode,
                                value=mode).pack(anchor="w", padx=15, pady=5)
        self._frames["step1"] = frame

    def _build_step2_byok(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(frame, text=t("onboarding.step2.byok.title"),
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(10, 15))
        ctk.CTkLabel(frame, text=t("settings.groq_api_key"), anchor="w").pack(fill="x", padx=20)
        self._groq_entry = _make_secret_row(frame, "gsk_...", keyring_manager.get("api_key"))
        ctk.CTkLabel(frame, text=t("settings.deepgram_api_key"), anchor="w").pack(fill="x", padx=20)
        self._deepgram_entry = _make_secret_row(frame, "...", keyring_manager.get("deepgram_api_key"))
        ctk.CTkLabel(frame, text=t("settings.openai_api_key"), anchor="w").pack(fill="x", padx=20)
        self._openai_entry = _make_secret_row(frame, "sk-...", keyring_manager.get("openai_api_key"))
        self._frames["step2_byok"] = frame

    def _build_step2_local(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(frame, text=t("onboarding.step2.local.title"),
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(10, 15))
        ctk.CTkLabel(frame, text="Model size:", anchor="w").pack(fill="x", padx=20)
        self._model_size_var = ctk.StringVar(value=config_manager.get("local_model_size", "base"))
        ctk.CTkOptionMenu(frame, variable=self._model_size_var,
                           values=["tiny", "base", "small", "medium"]).pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(frame, text="Larger models are more accurate but slower.",
                     text_color="gray", font=ctk.CTkFont(size=11)).pack(padx=20)
        self._frames["step2_local"] = frame

    def _build_step2_pro(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(frame, text="YapClean Pro",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(10, 15))
        ctk.CTkLabel(frame, text="Coming soon at yapclean.tech",
                     font=ctk.CTkFont(size=13), text_color="gray").pack(pady=10)
        ctk.CTkLabel(frame, text="For now, use BYOK mode with your own API keys.",
                     text_color="gray", font=ctk.CTkFont(size=11), wraplength=400).pack(padx=20)
        self._frames["step2_pro"] = frame

    def _build_step3(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(frame, text=t("onboarding.step3.title"),
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(10, 15))
        ctk.CTkLabel(frame, text=t("onboarding.step3.hotkey"), anchor="w").pack(fill="x", padx=20)
        self._hotkey_var = ctk.StringVar(value=config_manager.get("hotkey", "ctrl+alt+space"))
        ctk.CTkOptionMenu(frame, variable=self._hotkey_var,
                           values=["ctrl+alt+space", "ctrl+shift", "alt+shift", "f8", "f9", "caps lock"]
                           ).pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(frame, text=t("onboarding.step3.persona"), anchor="w").pack(fill="x", padx=20)
        self._persona_var = ctk.StringVar(value=config_manager.get("active_persona", "General User"))
        ctk.CTkOptionMenu(frame, variable=self._persona_var, values=PERSONAS).pack(fill="x", padx=20, pady=5)
        self._frames["step3"] = frame

    def _show_step(self, step: int):
        for f in self._frames.values():
            f.pack_forget()
        self._step = step
        self._step_label.configure(text=f"Step {step} / 3")
        self._back_btn.configure(state="normal" if step > 1 else "disabled")
        if step == 1:
            self._frames["step1"].pack(fill="both", expand=True, padx=10)
            self._next_btn.configure(text=t("onboarding.btn.next"), command=self._go_next)
        elif step == 2:
            self._frames[f"step2_{self._mode.get()}"].pack(fill="both", expand=True, padx=10)
            self._next_btn.configure(text=t("onboarding.btn.next"), command=self._go_next)
        elif step == 3:
            self._frames["step3"].pack(fill="both", expand=True, padx=10)
            self._next_btn.configure(text=t("onboarding.btn.finish"), command=self._finish)

    def _go_next(self):
        if self._step == 1:
            config_manager.set("ui_language", self._lang_var.get())
            config_manager.set("app_mode", self._mode.get())
            self._show_step(2)
        elif self._step == 2:
            self._save_step2()
            self._show_step(3)

    def _go_back(self):
        if self._step > 1:
            self._show_step(self._step - 1)

    def _save_step2(self):
        mode = self._mode.get()
        if mode == "byok":
            if self._groq_entry.get().strip():
                keyring_manager.save("api_key", self._groq_entry.get().strip())
            if self._deepgram_entry.get().strip():
                keyring_manager.save("deepgram_api_key", self._deepgram_entry.get().strip())
            if self._openai_entry.get().strip():
                keyring_manager.save("openai_api_key", self._openai_entry.get().strip())
        elif mode == "local":
            config_manager.set("local_model_size", self._model_size_var.get())
            config_manager.set("stt_provider", "local")
            config_manager.set("llm_provider", "ollama")

    def _finish(self):
        config_manager.set("hotkey", self._hotkey_var.get())
        config_manager.set("active_persona", self._persona_var.get())
        config_manager.set("onboarding_complete", True)
        logger.info("Onboarding complete.")
        self.destroy()


def _bind_paste(entry: ctk.CTkEntry) -> None:
    """Fix Ctrl+V paste for masked CTkEntry fields (show='*') on Windows."""
    def _paste(event=None):
        try:
            text = entry.clipboard_get()
            # Replace entire content with pasted text
            entry._entry.delete(0, "end")
            entry._entry.insert(0, text.strip())
        except Exception:
            pass
        return "break"  # prevent default handler from running
    # Bind both the virtual event and the key combo
    entry._entry.bind("<<Paste>>", _paste)
    entry._entry.bind("<Control-v>", _paste)
    entry._entry.bind("<Control-V>", _paste)


def _make_secret_row(parent, placeholder: str, initial_value: str = "") -> ctk.CTkEntry:
    """Password entry with show/hide toggle button. Ctrl+V works correctly."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=20, pady=5)
    row.columnconfigure(0, weight=1)

    entry = ctk.CTkEntry(row, placeholder_text=placeholder, show="*",
                         font=ctk.CTkFont(size=13))
    entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
    if initial_value:
        entry.insert(0, initial_value)

    _bind_paste(entry)

    visible = [False]

    def toggle():
        visible[0] = not visible[0]
        entry.configure(show="" if visible[0] else "*")
        btn.configure(text="🙈" if visible[0] else "👁")

    btn = ctk.CTkButton(row, text="👁", width=36, command=toggle,
                        fg_color="transparent", hover_color="#444",
                        font=ctk.CTkFont(size=14))
    btn.grid(row=0, column=1)
    return entry


def run_onboarding():
    app = OnboardingWizard()
    app.mainloop()
