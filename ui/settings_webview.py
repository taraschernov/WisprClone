import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import threading
import webview
import time
import socket
from utils.logger import get_logger
from ui.settings_server import create_app

logger = get_logger("yapclean.settings_webview")

def get_free_port():
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

def run_flask_app(app, port):
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

def open_settings():
    # 1. Start Flask API
    port = get_free_port()
    app = create_app()
    server_thread = threading.Thread(target=run_flask_app, args=(app, port), daemon=True)
    server_thread.start()
    
    # 2. Wait a little bit for the server to start
    time.sleep(0.5)
    
    # 3. Create Webview window
    url = f"http://127.0.0.1:{port}"
    logger.info(f"Opening settings webview at {url}")
    
    window = webview.create_window(
        title="YapClean Settings",
        url=url,
        width=800,
        height=600,
        resizable=True,
    )
    
    webview.start(debug=False)
    
if __name__ == "__main__":
    open_settings()
