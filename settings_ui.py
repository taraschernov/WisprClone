import customtkinter as ctk
import webbrowser
import os
import sys
import json
from storage.config_manager import config_manager
from storage.keyring_manager import keyring_manager
from i18n.translator import t, init_translator


def _bind_paste(entry: ctk.CTkEntry) -> None:
    """Fix Ctrl+V paste for masked CTkEntry fields (show='*') on Windows."""
    def _paste(event=None):
        try:
            text = entry.clipboard_get()
            entry._entry.delete(0, "end")
            entry._entry.insert(0, text.strip())
        except Exception:
            pass
        return "break"
    entry._entry.bind("<<Paste>>", _paste)
    entry._entry.bind("<Control-v>", _paste)
    entry._entry.bind("<Control-V>", _paste)


def _make_secret_row(parent, placeholder: str, initial_value: str = "") -> ctk.CTkEntry:
    """
    Create a password entry row with a show/hide toggle button.
    Returns the CTkEntry widget.
    """
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=10, pady=5)
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


class SettingsApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        init_translator(config_manager.get("ui_language", "en"))

        self.title(t("settings.title"))
        width = 580
        height = 720

        # Center the window
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.resizable(True, True)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Tabview
        self.tabview = ctk.CTkTabview(self, width=560, height=640)
        self.tabview.pack(padx=10, pady=(10, 0), fill="both", expand=True)

        self.tab_general = self.tabview.add(t("settings.tab.general"))
        self.tab_profiles = self.tabview.add(t("settings.tab.profiles"))
        self.tab_system = self.tabview.add(t("settings.tab.system_prompt"))
        self.tab_app_rules = self.tabview.add(t("settings.tab.app_rules"))

        self.setup_general_tab()
        self.setup_profiles_tab()
        self.setup_system_tab()
        self.setup_app_rules_tab()

        # Save Button at the Bottom
        self.save_btn = ctk.CTkButton(
            self,
            text=t("settings.save_close"),
            command=self.save_and_close,
            font=ctk.CTkFont(weight="bold"),
            height=40,
        )
        self.save_btn.pack(pady=10)

    def setup_general_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_general, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Title
        title = ctk.CTkLabel(
            scroll,
            text=t("settings.section.configuration"),
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.pack(pady=10)

        # API Keys Section
        group_api = ctk.CTkFrame(scroll)
        group_api.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(group_api, text=t("settings.groq_api_key"), anchor="w").pack(
            fill="x", padx=10, pady=(5, 0)
        )
        self.api_entry = _make_secret_row(group_api, "gsk_...", keyring_manager.get("api_key"))

        ctk.CTkLabel(group_api, text=t("settings.deepgram_api_key"), anchor="w").pack(
            fill="x", padx=10, pady=(5, 0)
        )
        self.deepgram_entry = _make_secret_row(group_api, "...", keyring_manager.get("deepgram_api_key"))

        ctk.CTkLabel(group_api, text=t("settings.openai_api_key"), anchor="w").pack(
            fill="x", padx=10, pady=(5, 0)
        )
        self.openai_entry = _make_secret_row(group_api, "sk-...", keyring_manager.get("openai_api_key"))

        # Mode Selection
        from config import get_current_mode, get_presets

        ctk.CTkLabel(
            scroll,
            text=t("settings.active_mode"),
            anchor="w",
            font=ctk.CTkFont(weight="bold"),
        ).pack(fill="x", padx=20, pady=(15, 0))
        self.mode_var = ctk.StringVar(value=get_current_mode())
        self.mode_dropdown = ctk.CTkOptionMenu(
            scroll, variable=self.mode_var, values=list(get_presets().keys())
        )
        self.mode_dropdown.pack(fill="x", padx=20, pady=5)

        # Hotkey, Hotkey Mode & Language
        group_inputs = ctk.CTkFrame(scroll)
        group_inputs.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(group_inputs, text=t("settings.hotkey"), anchor="w").pack(
            fill="x", padx=10, pady=(5, 0)
        )
        self.hotkey_var = ctk.StringVar(
            value=config_manager.get("hotkey") or "ctrl+alt"
        )
        import platform as _platform
        _hotkey_values = [
            "ctrl+shift", "alt+shift", "f8", "f9",
            "right ctrl", "ctrl+alt", "caps lock",
        ]
        if _platform.system() == "Darwin":
            _hotkey_values += ["right cmd", "ctrl+space", "fn"]
        ctk.CTkOptionMenu(
            group_inputs,
            variable=self.hotkey_var,
            values=_hotkey_values,
        ).pack(fill="x", padx=10, pady=5)

        # 14.6 Hotkey mode selector
        ctk.CTkLabel(group_inputs, text=t("settings.hotkey_mode"), anchor="w").pack(
            fill="x", padx=10, pady=(5, 0)
        )
        _hold_label = t("settings.hotkey_mode.hold")
        _toggle_label = t("settings.hotkey_mode.toggle")
        _stored_mode = config_manager.get("hotkey_mode", "hold")
        _display_mode = _toggle_label if _stored_mode == "toggle" else _hold_label
        self.hotkey_mode_var = ctk.StringVar(value=_display_mode)
        ctk.CTkOptionMenu(
            group_inputs,
            variable=self.hotkey_mode_var,
            values=[_hold_label, _toggle_label],
        ).pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            group_inputs, text=t("settings.dictation_language"), anchor="w"
        ).pack(fill="x", padx=10, pady=(5, 0))
        self.lang_var = ctk.StringVar(
            value=config_manager.get("dictation_language") or "Russian"
        )
        ctk.CTkOptionMenu(
            group_inputs,
            variable=self.lang_var,
            values=["Russian", "English", "Ukrainian", "German", "French", "Spanish"],
        ).pack(fill="x", padx=10, pady=5)

        # 14.3 STT provider selector
        ctk.CTkLabel(scroll, text=t("settings.stt_provider"), anchor="w").pack(
            fill="x", padx=20, pady=(10, 0)
        )
        self.stt_provider_var = ctk.StringVar(
            value=config_manager.get("stt_provider", "groq")
        )
        ctk.CTkOptionMenu(
            scroll,
            variable=self.stt_provider_var,
            values=["groq", "deepgram", "openai", "local"],
        ).pack(fill="x", padx=20, pady=5)

        # 14.4 LLM provider selector
        ctk.CTkLabel(scroll, text=t("settings.llm_provider"), anchor="w").pack(
            fill="x", padx=20, pady=(5, 0)
        )
        self.llm_provider_var = ctk.StringVar(
            value=config_manager.get("llm_provider", "groq")
        )
        ctk.CTkOptionMenu(
            scroll,
            variable=self.llm_provider_var,
            values=["groq", "openai", "ollama"],
        ).pack(fill="x", padx=20, pady=5)

        # 14.2 Microphone device selector
        ctk.CTkLabel(scroll, text=t("settings.microphone"), anchor="w").pack(
            fill="x", padx=20, pady=(5, 0)
        )
        input_devices = self._get_input_devices()
        self.mic_var = ctk.StringVar(
            value=config_manager.get("input_device", "Default")
        )
        ctk.CTkOptionMenu(
            scroll, variable=self.mic_var, values=input_devices
        ).pack(fill="x", padx=20, pady=5)

        # Checkboxes
        # 14.5 Bypass LLM checkbox
        self.bypass_llm_var = ctk.BooleanVar(
            value=config_manager.get("bypass_llm", False)
        )
        ctk.CTkCheckBox(
            scroll, text=t("settings.bypass_llm"), variable=self.bypass_llm_var
        ).pack(anchor="w", padx=20, pady=5)

        self.translate_var = ctk.BooleanVar(
            value=config_manager.get("translate_to_layout")
        )
        ctk.CTkCheckBox(
            scroll,
            text=t("settings.translate_to_layout"),
            variable=self.translate_var,
        ).pack(anchor="w", padx=20, pady=5)

        self.autostart_var = ctk.BooleanVar(value=config_manager.get("autostart"))
        ctk.CTkCheckBox(
            scroll, text=t("settings.autostart"), variable=self.autostart_var
        ).pack(anchor="w", padx=20, pady=5)

        # Notion
        group_notion = ctk.CTkFrame(scroll)
        group_notion.pack(fill="x", padx=10, pady=10)
        self.enable_notion_var = ctk.BooleanVar(
            value=config_manager.get("enable_notion")
        )
        ctk.CTkCheckBox(
            group_notion,
            text=t("settings.notion.title"),
            variable=self.enable_notion_var,
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=10, pady=5)

        ctk.CTkLabel(group_notion, text=t("settings.notion.api_key"), anchor="w").pack(
            fill="x", padx=10, pady=(5, 0)
        )
        self.notion_api_entry = _make_secret_row(group_notion, t("settings.notion.api_key"), keyring_manager.get("notion_api_key"))

        self.notion_db_entry = ctk.CTkEntry(
            group_notion, placeholder_text=t("settings.notion.database_id")
        )
        self.notion_db_entry.pack(fill="x", padx=10, pady=2)
        self.notion_db_entry.insert(0, config_manager.get("notion_database_id") or "")

        self.notion_trigger_entry = ctk.CTkEntry(
            group_notion, placeholder_text=t("settings.notion.trigger_word")
        )
        self.notion_trigger_entry.pack(fill="x", padx=10, pady=2)
        self.notion_trigger_entry.insert(
            0, config_manager.get("notion_trigger_word") or ""
        )

        # 14.8 Interface Language selector
        group_lang = ctk.CTkFrame(scroll)
        group_lang.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(group_lang, text=t("settings.ui_language"), anchor="w").pack(
            fill="x", padx=10, pady=(5, 0)
        )
        self.ui_language_var = ctk.StringVar(
            value=config_manager.get("ui_language", "en")
        )
        ctk.CTkOptionMenu(
            group_lang, variable=self.ui_language_var, values=["en", "ru"]
        ).pack(fill="x", padx=10, pady=5)

    def _get_input_devices(self):
        """Query sounddevice for input devices; fallback to ['Default'] on error."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            names = ["Default"] + [
                d["name"] for d in devices if d["max_input_channels"] > 0
            ]
            return names
        except Exception:
            return ["Default"]

    # 14.1 App Rules tab
    def setup_app_rules_tab(self):
        ctk.CTkLabel(
            self.tab_app_rules,
            text=t("settings.app_rules.title"),
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=10, padx=10, anchor="w")

        self._rules_scroll = ctk.CTkScrollableFrame(self.tab_app_rules)
        self._rules_scroll.pack(fill="both", expand=True, padx=10, pady=5)

        self._app_rule_rows = []

        existing = config_manager.get("app_bindings", {})
        for proc, persona in existing.items():
            self._add_rule_row(proc, persona)

        ctk.CTkButton(
            self.tab_app_rules,
            text=t("settings.app_rules.add"),
            command=lambda: self._add_rule_row("", "General User"),
        ).pack(pady=5)

    def _add_rule_row(self, process: str, persona: str):
        row_frame = ctk.CTkFrame(self._rules_scroll, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)

        proc_var = ctk.StringVar(value=process)
        persona_var = ctk.StringVar(value=persona or "General User")

        ctk.CTkEntry(
            row_frame,
            textvariable=proc_var,
            placeholder_text="process name",
            width=160,
        ).pack(side="left", padx=5)
        ctk.CTkOptionMenu(
            row_frame, variable=persona_var, values=PERSONAS, width=200
        ).pack(side="left", padx=5)

        row_data = {"process": proc_var, "persona": persona_var, "frame": row_frame}
        self._app_rule_rows.append(row_data)

        def delete_row():
            row_frame.destroy()
            self._app_rule_rows.remove(row_data)

        ctk.CTkButton(
            row_frame,
            text=t("settings.app_rules.delete"),
            command=delete_row,
            width=70,
            fg_color="red",
        ).pack(side="left", padx=5)

    def setup_profiles_tab(self):
        from config import get_presets

        self.presets_data = get_presets()

        label = ctk.CTkLabel(
            self.tab_profiles,
            text=t("settings.profiles.title"),
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        label.pack(pady=10)

        self.edit_mode_var = ctk.StringVar(value=list(self.presets_data.keys())[0])
        self.edit_mode_dropdown = ctk.CTkOptionMenu(
            self.tab_profiles,
            variable=self.edit_mode_var,
            values=list(self.presets_data.keys()),
            command=self.update_preset_editor,
        )
        self.edit_mode_dropdown.pack(fill="x", padx=20, pady=5)

        self.preset_textbox = ctk.CTkTextbox(
            self.tab_profiles, width=500, height=400, font=ctk.CTkFont(size=13)
        )
        self.preset_textbox.pack(padx=20, pady=10, fill="both", expand=True)

        self.update_preset_editor(self.edit_mode_var.get())

        btn_group = ctk.CTkFrame(self.tab_profiles, fg_color="transparent")
        btn_group.pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(
            btn_group, text=t("settings.profiles.reset"), command=self.reset_preset
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            btn_group, text=t("settings.profiles.add"), command=self.add_new_preset
        ).pack(side="right", padx=5)

    def setup_system_tab(self):
        from config import get_system_prompt

        label = ctk.CTkLabel(
            self.tab_system,
            text=t("settings.system_prompt.title"),
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        label.pack(pady=10)

        self.system_prompt_text = ctk.CTkTextbox(
            self.tab_system, width=500, height=500, font=ctk.CTkFont(size=12)
        )
        self.system_prompt_text.pack(padx=20, pady=10, fill="both", expand=True)
        self.system_prompt_text.insert("1.0", get_system_prompt())

    def update_preset_editor(self, selected):
        self.preset_textbox.delete("1.0", "end")
        self.preset_textbox.insert("1.0", self.presets_data.get(selected, ""))

    def add_new_preset(self):
        dialog = ctk.CTkInputDialog(
            text=t("settings.profiles.new_dialog_text"),
            title=t("settings.profiles.new_dialog_title"),
        )
        name = dialog.get_input()
        if name and name not in self.presets_data:
            self.presets_data[name] = "New instructions here..."
            self.edit_mode_dropdown.configure(values=list(self.presets_data.keys()))
            self.edit_mode_var.set(name)
            self.update_preset_editor(name)

    def reset_preset(self):
        from config import DEFAULT_PRESETS

        curr = self.edit_mode_var.get()
        if curr in DEFAULT_PRESETS:
            self.presets_data[curr] = DEFAULT_PRESETS[curr]
            self.update_preset_editor(curr)

    def save_and_close(self):
        # Update current preset content in dict before saving
        curr_preset = self.edit_mode_var.get()
        self.presets_data[curr_preset] = self.preset_textbox.get("1.0", "end-1c")

        # 14.7 Save API keys to keyring (never to config.json)
        keyring_manager.save("api_key", self.api_entry.get().strip())
        keyring_manager.save("deepgram_api_key", self.deepgram_entry.get().strip())
        keyring_manager.save("openai_api_key", self.openai_entry.get().strip())
        keyring_manager.save("notion_api_key", self.notion_api_entry.get().strip())

        # Save non-sensitive settings to config.json
        config_manager.set("hotkey", self.hotkey_var.get().strip())

        # 14.6 Save hotkey mode — map display label back to "hold"/"toggle"
        _toggle_label = t("settings.hotkey_mode.toggle")
        hotkey_mode_value = (
            "toggle"
            if self.hotkey_mode_var.get() == _toggle_label
            else "hold"
        )
        config_manager.set("hotkey_mode", hotkey_mode_value)

        # 14.3 / 14.4 Save provider selections
        config_manager.set("stt_provider", self.stt_provider_var.get())
        config_manager.set("llm_provider", self.llm_provider_var.get())

        # 14.5 Save bypass LLM
        config_manager.set("bypass_llm", self.bypass_llm_var.get())

        # 14.2 Save microphone selection
        config_manager.set("input_device", self.mic_var.get())

        config_manager.set("autostart", self.autostart_var.get())
        config_manager.set("translate_to_layout", self.translate_var.get())
        config_manager.set("dictation_language", self.lang_var.get())
        config_manager.set("enable_notion", self.enable_notion_var.get())
        config_manager.set("notion_database_id", self.notion_db_entry.get().strip())
        config_manager.set(
            "notion_trigger_word", self.notion_trigger_entry.get().strip().lower()
        )
        config_manager.set("current_mode", self.mode_var.get())
        config_manager.set("presets", self.presets_data)
        config_manager.set(
            "custom_system_prompt", self.system_prompt_text.get("1.0", "end-1c")
        )

        # 14.1 Save app rules
        bindings = {}
        for row in self._app_rule_rows:
            proc = row["process"].get().strip().lower()
            persona = row["persona"].get()
            if proc:
                bindings[proc] = persona
        config_manager.set("app_bindings", bindings)

        # 14.8 Save and apply UI language
        new_locale = self.ui_language_var.get()
        config_manager.set("ui_language", new_locale)
        init_translator(new_locale)

        self.set_autostart(self.autostart_var.get())
        self.destroy()

    def set_autostart(self, enable):
        from app_platform.autostart import enable_autostart, disable_autostart

        if enable:
            enable_autostart()
        else:
            disable_autostart()


def open_settings():
    app = SettingsApp()
    app.mainloop()


if __name__ == "__main__":
    open_settings()
