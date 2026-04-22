import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from storage.config_manager import config_manager
from storage.keyring_manager import keyring_manager

logger = logging.getLogger("yapclean.settings_server")

def create_app():
    # Determine the absolute path to the UI build directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    static_folder = os.path.join(base_dir, "web", "out")
    
    app = Flask(__name__, static_folder=static_folder, static_url_path="")
    CORS(app)

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/<path:path>")
    def serve_static(path):
        if os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        elif os.path.exists(os.path.join(app.static_folder, path + ".html")):
            return send_from_directory(app.static_folder, path + ".html")
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"ok": True})

    @app.route("/api/config", methods=["GET"])
    def get_config():
        data = {
            "active_preset_id": config_manager.get("current_mode", "General User"),
            "hotkey": config_manager.get("hotkey", "ctrl+alt"),
            "hotkey_mode": config_manager.get("hotkey_mode", "hold"),
            "dictation_language": config_manager.get("dictation_language", "Russian"),
            "stt_provider": config_manager.get("stt_provider", "groq"),
            "llm_provider": config_manager.get("llm_provider", "groq"),
            "microphone": config_manager.get("input_device", "Default"),
            "bypass_llm": config_manager.get("bypass_llm", False),
            "translate_to_layout": config_manager.get("translate_to_layout", False),
            "launch_at_startup": config_manager.get("autostart", False),
            "show_overlay": config_manager.get("show_pill_overlay", True),
            "ui_language": config_manager.get("ui_language", "en"),
            "notion": {
                "enabled": config_manager.get("enable_notion", False),
                "database_id": config_manager.get("notion_database_id", ""),
                "trigger_word": config_manager.get("notion_trigger_word", "")
            }
        }
        return jsonify(data)

    @app.route("/api/config", methods=["POST"])
    def post_config():
        data = request.json
        if not data:
            return jsonify({"ok": False}), 400
        
        # Map frontend keys to config manager keys
        mapping = {
            "active_preset_id": "current_mode",
            "hotkey": "hotkey",
            "hotkey_mode": "hotkey_mode",
            "dictation_language": "dictation_language",
            "stt_provider": "stt_provider",
            "llm_provider": "llm_provider",
            "microphone": "input_device",
            "bypass_llm": "bypass_llm",
            "translate_to_layout": "translate_to_layout",
            "launch_at_startup": "autostart",
            "show_overlay": "show_pill_overlay",
            "ui_language": "ui_language",
        }

        for frontend_key, backend_key in mapping.items():
            if frontend_key in data:
                config_manager.set(backend_key, data[frontend_key])
                
        if "notion" in data:
            notion = data["notion"]
            if "enabled" in notion:
                config_manager.set("enable_notion", notion["enabled"])
            if "database_id" in notion:
                config_manager.set("notion_database_id", notion["database_id"])
            if "trigger_word" in notion:
                config_manager.set("notion_trigger_word", notion["trigger_word"])

        # Handle autostart separately if needed
        if "launch_at_startup" in data:
            from app_platform.autostart import enable_autostart, disable_autostart
            if data["launch_at_startup"]:
                enable_autostart()
            else:
                disable_autostart()

        return jsonify({"ok": True})

    @app.route("/api/keys", methods=["GET"])
    def get_keys():
        providers = ["groq", "deepgram", "openai", "notion"]
        res = {}
        for p in providers:
            # Our backend key logic might differ slightly per provider
            storage_key = p + "_api_key" if p != "groq" else "api_key"
            val = keyring_manager.get(storage_key)
            res[p] = {"has_key": bool(val and len(val.strip()) > 0)}
        return jsonify(res)

    @app.route("/api/keys", methods=["POST"])
    def post_keys():
        data = request.json
        if not data or "provider" not in data:
            return jsonify({"ok": False}), 400
            
        provider = data["provider"]
        value = data.get("value")
        
        storage_key = provider + "_api_key" if provider != "groq" else "api_key"
        
        if value is None or len(value.strip()) == 0:
            keyring_manager.delete(storage_key)
        else:
            keyring_manager.save(storage_key, value.strip())
            
        return jsonify({"ok": True})

    @app.route("/api/mics", methods=["GET"])
    def get_mics():
        mics_list = [{"id": "Default", "label": "Default"}]
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            for d in devices:
                if d["max_input_channels"] > 0:
                    name = d["name"]
                    if name != "Default":
                        mics_list.append({"id": name, "label": name})
        except Exception as e:
            logger.error(f"Failed to query mics: {e}")
            
        return jsonify({
            "current_id": config_manager.get("input_device", "Default"),
            "list": mics_list
        })

    @app.route("/api/presets", methods=["GET"])
    def get_presets():
        from config import get_presets as get_all_presets
        presets_dict = get_all_presets()
        res = []
        for k, v in presets_dict.items():
            res.append({
                "id": k,
                "label": k,
                "system_prompt": v,
                "builtin": True # Simplification for now
            })
        return jsonify(res)

    @app.route("/api/presets", methods=["POST"])
    def post_presets():
        data = request.json
        if not isinstance(data, list):
            return jsonify({"ok": False}), 400
            
        presets_dict = {}
        for p in data:
            if "id" in p and "system_prompt" in p:
                presets_dict[p["id"]] = p["system_prompt"]
                
        if presets_dict:
            config_manager.set("presets", presets_dict)
        return jsonify({"ok": True})

    @app.route("/api/app-rules", methods=["GET"])
    def get_app_rules():
        bindings = config_manager.get("app_bindings", {})
        res = []
        import uuid
        for process, preset in bindings.items():
            res.append({
                "id": str(uuid.uuid4()),
                "process": process,
                "preset_id": preset
            })
        return jsonify(res)

    @app.route("/api/app-rules", methods=["POST"])
    def post_app_rules():
        data = request.json
        if not isinstance(data, list):
            return jsonify({"ok": False}), 400
            
        bindings = {}
        for rule in data:
            if "process" in rule and "preset_id" in rule:
                bindings[rule["process"]] = rule["preset_id"]
                
        config_manager.set("app_bindings", bindings)
        return jsonify({"ok": True})

    return app

def run_server(port=0):
    app = create_app()
    if port == 0:
        import socket
        sock = socket.socket()
        sock.bind(('', 0))
        port = sock.getsockname()[1]
        sock.close()
    
    # Disable werkzeug logging to keep console clean
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
