import sys
import os
import subprocess
import shutil

def run_command(cmd, cwd=None):
    print(f"[*] Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"[!] Command failed with exit code: {result.returncode}")
        sys.exit(result.returncode)

def compile_app():
    # Resolve base_dir to the project root (one level up from packaging/)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Compile Python Backend using PyInstaller
    print("\n==============================================")
    print("[*] STEP 1: Compiling FastAPI Python Backend")
    print("==============================================\n")
    
    pyinstaller_bin = os.path.join(base_dir, "venv", "bin", "pyinstaller")
    if not os.path.exists(pyinstaller_bin):
        pyinstaller_bin = "pyinstaller" # fallback to system path
        
    hidden_imports = [
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.wsproto_impl",
        "uvicorn.lifespan.on",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "sqlalchemy.sql.default_comparator",
        "chromadb.api.segment",
        "chromadb.api.rust",
        "chromadb.telemetry.opentelemetry",
        "chromadb.telemetry.product.posthog",
        "chromadb.db.impl.sqlite",
        "chromadb.migrations",
        "chromadb.migrations.embeddings",
        "sentence_transformers",
        "pdfplumber",
        "pypdf",
        "email_validator",
        "bcrypt",
        "cryptography",
        "fitz",
        "pytesseract"
    ]
    
    args = [
        pyinstaller_bin,
        "--name=aegis_backend",
        "--onedir",
        "--clean",
        "--noconfirm",
        "--paths=.",
        "aegis_backend/main.py"
    ]
    
    # Add model_bundle folder as packaged data
    sep = ";" if sys.platform == "win32" else ":"
    args.append(f"--add-data=aegis_backend/model_bundle{sep}aegis_backend/model_bundle")
    
    for hi in hidden_imports:
        args.append(f"--hidden-import={hi}")
        
    run_command(args, cwd=base_dir)
    print("[*] Python backend compiled successfully under ./dist/aegis_backend/")

    # Copy Next.js static build to aegis_desktop/out
    desktop_out_dir = os.path.join(base_dir, "aegis_desktop", "out")
    frontend_out_dir = os.path.join(base_dir, "aegis_frontend", "out")
    print(f"[*] Copying static pages from {frontend_out_dir} to {desktop_out_dir}...")
    if os.path.exists(desktop_out_dir):
        shutil.rmtree(desktop_out_dir)
    shutil.copytree(frontend_out_dir, desktop_out_dir)

    # 2. Package Electron App using electron-builder
    print("\n==============================================")
    print("[*] STEP 2: Packaging Desktop App Bundle via Electron")
    print("==============================================\n")
    
    # Run npm run dist inside aegis_desktop
    npm_cmd = ["npm", "run", "dist"]
    if sys.platform == "win32":
        npm_cmd = ["npm.cmd", "run", "dist"]
        
    run_command(npm_cmd, cwd=os.path.join(base_dir, "aegis_desktop"))
    
    print("\n==============================================")
    print("[*] SUCCESS: AegisAI Standalone Desktop App Built!")
    print("[*] Final installers are saved in: ./dist_desktop/")
    print("==============================================\n")

if __name__ == "__main__":
    compile_app()
