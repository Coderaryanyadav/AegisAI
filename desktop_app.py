import os
import sys
import warnings

# Force Streamlit to run headlessly without ever opening a browser window
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
# Also force global development mode to false via env variable as an extra layer
os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"

# Suppress all deprecation and runtime warnings globally
warnings.simplefilter("ignore")

# Define user-writable paths for logs and debug info
USER_HOME = os.path.expanduser("~")
LOG_DIR = os.path.join(USER_HOME, ".aegis_legal_ai", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

backend_log_path = os.path.join(LOG_DIR, "backend_server.log")
frontend_log_path = os.path.join(LOG_DIR, "frontend_server.log")
debug_paths_path = os.path.join(LOG_DIR, "debug_paths.txt")

# Ensure absolute imports work in both developer and compiled standalone mode
if hasattr(sys, '_MEIPASS'):
    sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import subprocess
import time
import socket
import webview

def wait_for_port(port: int, timeout: float = 15.0) -> bool:
    """Check if local port is active and accepting TCP connections."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.connect(("127.0.0.1", port))
                return True
        except socket.error:
            time.sleep(0.5)
    return False

def get_resource_path(relative_path: str) -> str:
    """Resolve resource path for bundled files in PyInstaller mode."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), relative_path))

def start_backend():
    """Launch the FastAPI Uvicorn backend process silently."""
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE

    # Redirect to log files to capture debugging tracebacks safely in user home directory
    log_f = open(backend_log_path, "w")
    return subprocess.Popen(
        [sys.executable, __file__, "--backend"] if not getattr(sys, 'frozen', False) else [sys.executable, "--backend"],
        stdout=log_f,
        stderr=log_f,
        startupinfo=startupinfo
    )

def start_frontend():
    """Launch the Streamlit frontend process silently."""
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE

    # Redirect to log files to capture debugging tracebacks safely in user home directory
    log_f = open(frontend_log_path, "w")
    return subprocess.Popen(
        [sys.executable, __file__, "--frontend"] if not getattr(sys, 'frozen', False) else [sys.executable, "--frontend"],
        stdout=log_f,
        stderr=log_f,
        startupinfo=startupinfo
    )

# Routing flags for self-invocation under compiled bundler
if __name__ == "__main__":
    if "--backend" in sys.argv:
        # Run FastAPI Backend programmatically
        import uvicorn
        from legal_ai.main import app
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")
        sys.exit(0)

    elif "--frontend" in sys.argv:
        # Force Streamlit to run in production mode to mount static asset routes
        from streamlit import config
        config.set_option("global.developmentMode", False)

        # Monkeypatch Streamlit static folder resolution for PyInstaller zip-package environment
        import streamlit.file_util as streamlit_file_util
        streamlit_file_util.get_static_dir = lambda: get_resource_path(os.path.join("streamlit", "static"))

        # Debug paths
        try:
            with open(debug_paths_path, "w") as debug_f:
                debug_f.write(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'None')}\n")
                debug_f.write(f"get_static_dir(): {streamlit_file_util.get_static_dir()}\n")
                debug_f.write(f"exists: {os.path.exists(streamlit_file_util.get_static_dir())}\n")
        except Exception as debug_e:
            pass

        # Force Streamlit to run headlessly without ever opening a browser window
        config.set_option("server.headless", True)
        config.set_option("browser.gatherUsageStats", False)
        config.set_option("server.port", 8501)
        
        # Run Streamlit Frontend programmatically
        import streamlit.web.bootstrap as bootstrap
        frontend_path = get_resource_path(os.path.join("legal_ai", "app", "frontend.py"))
        
        # Configure Streamlit programmatic environment settings
        bootstrap.run(
            frontend_path, 
            "streamlit run", 
            [], 
            flag_options={
                "server.port": 8501,
                "server.headless": True,
                "browser.gatherUsageStats": False,
                "global.developmentMode": False
            }
        )
        sys.exit(0)

    else:
        # Main desktop GUI process
        backend_proc = start_backend()
        frontend_proc = start_frontend()

        # Wait until Streamlit frontend port is active
        ready = wait_for_port(8501, timeout=20.0)
        if not ready:
            print("[!] Fail to start background web server in time.")
            backend_proc.terminate()
            frontend_proc.terminate()
            sys.exit(1)

        try:
            # Open PyWebView Desktop window
            webview.create_window(
                title="Aegis Legal AI Suite",
                url="http://127.0.0.1:8501",
                width=1280,
                height=850,
                resizable=True,
                confirm_close=True
            )
            webview.start()
        finally:
            # Ensure background processes are cleaned up on window close
            backend_proc.terminate()
            frontend_proc.terminate()
            
            # Wait for them to exit
            backend_proc.wait()
            frontend_proc.wait()
            sys.exit(0)
