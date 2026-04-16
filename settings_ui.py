import customtkinter as ctk
import webbrowser
import os
import sys
import winreg
from config_manager import config_manager

class SettingsApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Настройки WisprClone")
        self.geometry("450x550")
        self.resizable(False, False)
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Title
        self.title_label = ctk.CTkLabel(self, text="Настройки WisprClone", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=(15, 5))

        # Instructions Frame
        self.inst_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.inst_frame.pack(fill="x", padx=20, pady=5)

        self.step1 = ctk.CTkLabel(self.inst_frame, text="1. Получите бесплатный API ключ:", anchor="w")
        self.step1.pack(fill="x")

        self.link = ctk.CTkLabel(self.inst_frame, text="➡️ Открыть console.groq.com", text_color="#1f6aa5", cursor="hand2", font=ctk.CTkFont(underline=True))
        self.link.pack(fill="x", pady=2)
        self.link.bind("<Button-1>", lambda e: webbrowser.open("https://console.groq.com/keys"))

        self.step2 = ctk.CTkLabel(self.inst_frame, text="2. Вставьте ваш ключ сюда:", anchor="w", font=ctk.CTkFont(size=14))
        self.step2.pack(fill="x", pady=(10, 0))

        # API Key Input
        self.api_entry = ctk.CTkEntry(self, placeholder_text="gsk_xxxxxxxxxxxxxxxxxxxxxx", show="*", width=410, font=ctk.CTkFont(size=14))
        self.api_entry.pack(padx=20, pady=5)
        self.api_entry.insert(0, config_manager.get("api_key") or "")

        # Notion Integration Label
        self.notion_label = ctk.CTkLabel(self, text="Интеграция с Notion (Опционально):", anchor="w", font=ctk.CTkFont(size=14, weight="bold"))
        self.notion_label.pack(fill="x", padx=20, pady=(15, 0))

        # Notion API Key Input
        self.notion_api_entry = ctk.CTkEntry(self, placeholder_text="secret_xxxxxxxxxxxxxxxxxx (Notion API Key)", show="*", width=410, font=ctk.CTkFont(size=14))
        self.notion_api_entry.pack(padx=20, pady=5)
        self.notion_api_entry.insert(0, config_manager.get("notion_api_key") or "")

        # Notion Database ID Input
        self.notion_db_entry = ctk.CTkEntry(self, placeholder_text="xxxxxxxxxxxxxxxxxxxxxxxx (Database ID)", width=410, font=ctk.CTkFont(size=14))
        self.notion_db_entry.pack(padx=20, pady=5)
        self.notion_db_entry.insert(0, config_manager.get("notion_database_id") or "")

        # Hotkey Input
        self.hotkey_label = ctk.CTkLabel(self, text="Комбинация клавиш (удерживать для записи):", anchor="w", font=ctk.CTkFont(size=14))
        self.hotkey_label.pack(fill="x", padx=20, pady=(15, 0))

        self.hotkey_var = ctk.StringVar(value=config_manager.get("hotkey") or "ctrl+shift")
        self.hotkey_dropdown = ctk.CTkOptionMenu(
            self, 
            variable=self.hotkey_var,
            font=ctk.CTkFont(size=14),
            width=410,
            values=["ctrl+shift", "alt+shift", "f8", "f9", "right ctrl", "ctrl+alt"]
        )
        self.hotkey_dropdown.pack(padx=20, pady=5)

        # Autostart Checkbox
        self.autostart_var = ctk.BooleanVar(value=config_manager.get("autostart"))
        self.autostart_checkbox = ctk.CTkCheckBox(self, text="Запускать вместе с Windows", variable=self.autostart_var)
        self.autostart_checkbox.pack(anchor="w", padx=20, pady=(15, 10))

        # Save Button
        self.save_btn = ctk.CTkButton(self, text="Сохранить и Закрыть", command=self.save_and_close, font=ctk.CTkFont(weight="bold"))
        self.save_btn.pack(pady=10)

    def set_autostart(self, enable):
        """Creates or removes windows registry key for autostart"""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "WisprClone"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            if enable:
                # If running as script, use pythonw path. If frozen, use sys.executable
                if getattr(sys, 'frozen', False):
                    exe_path = f'"{sys.executable}"'
                else:
                    exe_path = f'"{sys.executable}" "{os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))}"'
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Failed to toggle autostart: {e}")

    def save_and_close(self):
        api_key = self.api_entry.get().strip()
        hotkey = self.hotkey_var.get().strip()
        autostart = self.autostart_var.get()
        notion_api = self.notion_api_entry.get().strip()
        notion_db = self.notion_db_entry.get().strip()

        config_manager.set("api_key", api_key)
        config_manager.set("hotkey", hotkey)
        config_manager.set("autostart", autostart)
        config_manager.set("notion_api_key", notion_api)
        config_manager.set("notion_database_id", notion_db)

        self.set_autostart(autostart)
        
        # Notify user (e.g., visual feedback)
        self.save_btn.configure(text="Сохранено!", fg_color="green")
        self.after(500, self.destroy)

def open_settings():
    app = SettingsApp()
    app.eval('tk::PlaceWindow . center')
    app.mainloop()

if __name__ == "__main__":
    open_settings()
