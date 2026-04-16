import customtkinter as ctk
import webbrowser
import os
import sys
import winreg
import json
from config_manager import config_manager

class SettingsApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Настройки WisprClone")
        width = 560
        height = 700
        
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
        self.tabview = ctk.CTkTabview(self, width=540, height=620)
        self.tabview.pack(padx=10, pady=(10, 0), fill="both", expand=True)
        
        self.tab_general = self.tabview.add("Основные")
        self.tab_profiles = self.tabview.add("Профили LLM")
        self.tab_system = self.tabview.add("System Prompt")

        self.setup_general_tab()
        self.setup_profiles_tab()
        self.setup_system_tab()

        # Save Button at the Bottom
        self.save_btn = ctk.CTkButton(self, text="Сохранить всё и Закрыть", command=self.save_and_close, font=ctk.CTkFont(weight="bold"), height=40)
        self.save_btn.pack(pady=10)

    def setup_general_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_general, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Title
        title = ctk.CTkLabel(scroll, text="Конфигурация", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(pady=10)

        # API Keys Section
        group_api = ctk.CTkFrame(scroll)
        group_api.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(group_api, text="Groq API Key (для LLM):", anchor="w").pack(fill="x", padx=10, pady=(5,0))
        self.api_entry = ctk.CTkEntry(group_api, placeholder_text="gsk_...", show="*", font=ctk.CTkFont(size=13))
        self.api_entry.pack(fill="x", padx=10, pady=5)
        self.api_entry.insert(0, config_manager.get("api_key") or "")

        ctk.CTkLabel(group_api, text="Deepgram API Key (для STT):", anchor="w").pack(fill="x", padx=10, pady=(5,0))
        self.deepgram_entry = ctk.CTkEntry(group_api, placeholder_text="...", show="*", font=ctk.CTkFont(size=13))
        self.deepgram_entry.pack(fill="x", padx=10, pady=5)
        self.deepgram_entry.insert(0, config_manager.get("deepgram_api_key") or "")

        # Mode Selection
        from config import get_current_mode, get_presets
        ctk.CTkLabel(scroll, text="Активный режим LLM (Preset):", anchor="w", font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=20, pady=(15,0))
        self.mode_var = ctk.StringVar(value=get_current_mode())
        self.mode_dropdown = ctk.CTkOptionMenu(scroll, variable=self.mode_var, values=list(get_presets().keys()))
        self.mode_dropdown.pack(fill="x", padx=20, pady=5)

        # Hotkey & Language
        group_inputs = ctk.CTkFrame(scroll)
        group_inputs.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(group_inputs, text="Горячая клавиша:", anchor="w").pack(fill="x", padx=10, pady=(5,0))
        self.hotkey_var = ctk.StringVar(value=config_manager.get("hotkey") or "ctrl+alt")
        ctk.CTkOptionMenu(group_inputs, variable=self.hotkey_var, values=["ctrl+shift", "alt+shift", "f8", "f9", "right ctrl", "ctrl+alt", "caps lock"]).pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(group_inputs, text="Язык вашей речи:", anchor="w").pack(fill="x", padx=10, pady=(5,0))
        self.lang_var = ctk.StringVar(value=config_manager.get("dictation_language") or "Russian")
        ctk.CTkOptionMenu(group_inputs, variable=self.lang_var, values=["Russian", "English", "Ukrainian", "German", "French", "Spanish"]).pack(fill="x", padx=10, pady=5)

        # Checkboxes
        self.translate_var = ctk.BooleanVar(value=config_manager.get("translate_to_layout"))
        ctk.CTkCheckBox(scroll, text="Переводить на язык раскладки", variable=self.translate_var).pack(anchor="w", padx=20, pady=5)

        self.autostart_var = ctk.BooleanVar(value=config_manager.get("autostart"))
        ctk.CTkCheckBox(scroll, text="Запускать при старте Windows", variable=self.autostart_var).pack(anchor="w", padx=20, pady=5)

        # Notion
        group_notion = ctk.CTkFrame(scroll)
        group_notion.pack(fill="x", padx=10, pady=10)
        self.enable_notion_var = ctk.BooleanVar(value=config_manager.get("enable_notion"))
        ctk.CTkCheckBox(group_notion, text="Интеграция с Notion", variable=self.enable_notion_var, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)
        
        self.notion_api_entry = ctk.CTkEntry(group_notion, placeholder_text="Notion API Key", show="*")
        self.notion_api_entry.pack(fill="x", padx=10, pady=2)
        self.notion_api_entry.insert(0, config_manager.get("notion_api_key") or "")
        
        self.notion_db_entry = ctk.CTkEntry(group_notion, placeholder_text="Notion Database ID")
        self.notion_db_entry.pack(fill="x", padx=10, pady=2)
        self.notion_db_entry.insert(0, config_manager.get("notion_database_id") or "")

        self.notion_trigger_entry = ctk.CTkEntry(group_notion, placeholder_text="Триггер-слово (заметка)")
        self.notion_trigger_entry.pack(fill="x", padx=10, pady=2)
        self.notion_trigger_entry.insert(0, config_manager.get("notion_trigger_word") or "")

    def setup_profiles_tab(self):
        from config import get_presets
        self.presets_data = get_presets()
        
        label = ctk.CTkLabel(self.tab_profiles, text="Настройка Пресетов (Modes)", font=ctk.CTkFont(size=16, weight="bold"))
        label.pack(pady=10)

        self.edit_mode_var = ctk.StringVar(value=list(self.presets_data.keys())[0])
        self.edit_mode_dropdown = ctk.CTkOptionMenu(self.tab_profiles, variable=self.edit_mode_var, values=list(self.presets_data.keys()), command=self.update_preset_editor)
        self.edit_mode_dropdown.pack(fill="x", padx=20, pady=5)

        self.preset_textbox = ctk.CTkTextbox(self.tab_profiles, width=500, height=400, font=ctk.CTkFont(size=13))
        self.preset_textbox.pack(padx=20, pady=10, fill="both", expand=True)
        
        self.update_preset_editor(self.edit_mode_var.get())

        btn_group = ctk.CTkFrame(self.tab_profiles, fg_color="transparent")
        btn_group.pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(btn_group, text="Сбросить выбранный", command=self.reset_preset).pack(side="left", padx=5)
        ctk.CTkButton(btn_group, text="Добавить новый", command=self.add_new_preset).pack(side="right", padx=5)

    def setup_system_tab(self):
        from config import get_system_prompt
        label = ctk.CTkLabel(self.tab_system, text="Глобальный системный промпт (Role)", font=ctk.CTkFont(size=16, weight="bold"))
        label.pack(pady=10)
        
        self.system_prompt_text = ctk.CTkTextbox(self.tab_system, width=500, height=500, font=ctk.CTkFont(size=12))
        self.system_prompt_text.pack(padx=20, pady=10, fill="both", expand=True)
        self.system_prompt_text.insert("1.0", get_system_prompt())

    def update_preset_editor(self, selected):
        # Save current before switching? No, let's just update view.
        self.preset_textbox.delete("1.0", "end")
        self.preset_textbox.insert("1.0", self.presets_data.get(selected, ""))

    def add_new_preset(self):
        dialog = ctk.CTkInputDialog(text="Введите название нового режима:", title="Новый пресет")
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

        config_manager.set("api_key", self.api_entry.get().strip())
        config_manager.set("deepgram_api_key", self.deepgram_entry.get().strip())
        config_manager.set("hotkey", self.hotkey_var.get().strip())
        config_manager.set("autostart", self.autostart_var.get())
        config_manager.set("translate_to_layout", self.translate_var.get())
        config_manager.set("dictation_language", self.lang_var.get())
        config_manager.set("enable_notion", self.enable_notion_var.get())
        config_manager.set("notion_api_key", self.notion_api_entry.get().strip())
        config_manager.set("notion_database_id", self.notion_db_entry.get().strip())
        config_manager.set("notion_trigger_word", self.notion_trigger_entry.get().strip().lower())
        
        config_manager.set("current_mode", self.mode_var.get())
        config_manager.set("presets", self.presets_data)
        config_manager.set("custom_system_prompt", self.system_prompt_text.get("1.0", "end-1c"))

        self.set_autostart(self.autostart_var.get())
        self.destroy()

    def set_autostart(self, enable):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "WisprClone"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            if enable:
                exe_path = f'"{sys.executable}"' if getattr(sys, 'frozen', False) else f'"{sys.executable}" "{os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))}"'
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try: winreg.DeleteValue(key, app_name)
                except FileNotFoundError: pass
            winreg.CloseKey(key)
        except Exception: pass

def open_settings():
    app = SettingsApp()
    app.mainloop()

if __name__ == "__main__":
    open_settings()
