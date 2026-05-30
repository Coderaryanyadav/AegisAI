import os
import sys
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

    # Launch ourselves with --backend flag
    return subprocess.Popen(
        [sys.executable, __file__, "--backend"] if not getattr(sys, 'frozen', False) else [sys.executable, "--backend"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        startupinfo=startupinfo
    )

def start_frontend():
    """Launch the Streamlit frontend process silently."""
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE

    # Launch ourselves with --frontend flag
    return subprocess.Popen(
        [sys.executable, __file__, "--frontend"] if not getattr(sys, 'frozen', False) else [sys.executable, "--frontend"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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
