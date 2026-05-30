import sys
import os
import PyInstaller.__main__

def compile_app():
    # Base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define hidden imports that are dynamically loaded and missed by PyInstaller
    hidden_imports = [
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.wsproto_impl",
        "uvicorn.lifespan.on",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "streamlit.web.bootstrap",
        "streamlit.runtime.scriptrunner.magic_funcs",
        "sqlalchemy.sql.default_comparator",
        "chromadb.api.segment",
        "chromadb.telemetry.opentelemetry"
    ]
    
    import streamlit
    streamlit_dir = os.path.dirname(streamlit.__file__)
    streamlit_static = os.path.join(streamlit_dir, "static")
    
    # Data assets to pack (uses target delimiter for OS)
    separator = ";" if sys.platform == "win32" else ":"
    data_files = [
        f"legal_ai{separator}legal_ai",
        f"{streamlit_static}{separator}streamlit/static"
    ]
    
    # Arguments list for PyInstaller compiler
    args = [
        "desktop_app.py",
        "--name=AegisLegalAI",
        "--windowed",  # Headless native window, no terminal console
        "--copy-metadata=streamlit",
        "--clean",
        "--noconfirm"
    ]
    
    for hi in hidden_imports:
        args.append(f"--hidden-import={hi}")
        
    for df in data_files:
        args.append(f"--add-data={df}")
        
    print(f"[*] Starting PyInstaller compilation...")
    PyInstaller.__main__.run(args)
    print("[*] Compilation completed. Standalone binaries saved to: ./dist/")

if __name__ == "__main__":
    compile_app()
