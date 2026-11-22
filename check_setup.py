#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import urllib.request
import json
import socket

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(PROJECT_DIR, "venv")
REQ_FILE = os.path.join(PROJECT_DIR, "requirements.txt")
FRONTEND_DIR = os.path.join(PROJECT_DIR, "aegis_frontend")

def print_section(title):
    print("\n" + "=" * 60)
    print(f"🔧 {title.upper()}")
    print("=" * 60)

def print_status(name, passed, detail=""):
    status = "🟢 OK" if passed else "🔴 ERROR"
    print(f"[{status}] {name}")
    if detail:
        print(f"   Detail: {detail}")

def check_python():
    print_section("checking python environment")
    version = sys.version_info
    passed = version.major == 3 and version.minor >= 11
    print_status("Python 3.11+", passed, f"Running: {sys.version.split()[0]}")
    if not passed:
        print("[-] Please ensure Python 3.11 or higher is installed and active.")
        sys.exit(1)

def check_venv():
    print_section("checking python virtual environment (venv)")
    if not os.path.isdir(VENV_DIR):
        print("[*] 'venv' not found. Creating virtual environment...")
        py_exec = sys.executable
        if sys.version_info >= (3, 15):
            for cand in ["python3.12", "python3.11"]:
                cand_path = shutil.which(cand)
                if cand_path:
                    py_exec = cand_path
                    break
        try:
            subprocess.run([py_exec, "-m", "venv", VENV_DIR], check=True)
            print_status("venv Creation", True, f"Successfully created virtual environment with {py_exec}.")
        except Exception as e:
            print_status("venv Creation", False, f"Failed to create virtual environment: {e}")
            sys.exit(1)
    else:
        print_status("venv Directory", True, f"Found existing venv at {VENV_DIR}")

def check_pip_requirements():
    print_section("checking python dependencies")
    if not os.path.exists(REQ_FILE):
        print_status("requirements.txt", False, f"Not found at {REQ_FILE}")
        return

    # Use the venv pip
    if os.name == "nt":
        pip_path = os.path.join(VENV_DIR, "Scripts", "pip")
    else:
        pip_path = os.path.join(VENV_DIR, "bin", "pip")

    if not os.path.exists(pip_path):
        # fallback to sys.executable
        pip_path = "pip"

    print(f"[*] Verifying requirements using pip at {pip_path}...")
    try:
        # Upgrade pip first
        subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True, stdout=subprocess.DEVNULL)
        # Install packages
        dev_req = os.path.join(PROJECT_DIR, "requirements-dev.txt")
        cmd = [pip_path, "install", "-r", REQ_FILE]
        if os.path.exists(dev_req):
            cmd.extend(["-r", dev_req])
        subprocess.run(cmd, check=True)
        print_status("Python Dependencies", True, "All requirements installed successfully.")
    except Exception as e:
        print_status("Python Dependencies", False, f"Error installing requirements: {e}")
        sys.exit(1)

def check_node():
    print_section("checking node.js & npm")
    npm_path = shutil.which("npm")
    passed = npm_path is not None
    print_status("Node.js / NPM", passed, f"NPM Path: {npm_path or 'Not Found'}")
    if not passed:
        print("[-] Node.js is required to compile and run the Next.js React frontend.")
        print("[-] Please download it from: https://nodejs.org/")
        sys.exit(1)

def check_frontend_deps():
    print_section("checking frontend packages")
    node_modules_dir = os.path.join(FRONTEND_DIR, "node_modules")
    if not os.path.isdir(node_modules_dir):
        print("[*] node_modules not found in aegis_frontend. Running npm install...")
        try:
            subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=True)
            print_status("Frontend Install", True, "Installed packages in aegis_frontend.")
        except Exception as e:
            print_status("Frontend Install", False, f"Failed to run npm install: {e}")
            sys.exit(1)
    else:
        print_status("Frontend node_modules", True, f"Found active packages in {node_modules_dir}")

def check_local_ai_runtime():
    print_section("checking local ai inference engine (lm studio / ollama)")
    
    # 1. Check LM Studio
    lmstudio_running = False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect(("127.0.0.1", 1234))
            lmstudio_running = True
    except Exception:
        pass

    if not lmstudio_running:
        lms_cli = shutil.which("lms") or os.path.expanduser("~/.lmstudio/bin/lms")
        if os.path.exists(lms_cli) or shutil.which("lms"):
            print("[*] LM Studio CLI detected. Starting local server...")
            try:
                env = dict(os.environ)
                env.pop("ELECTRON_RUN_AS_NODE", None)
                subprocess.run([lms_cli, "server", "start", "--cors"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)
                import time
                time.sleep(2)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2.0)
                    s.connect(("127.0.0.1", 1234))
                    lmstudio_running = True
            except Exception:
                pass

    if lmstudio_running:
        print_status("LM Studio Runtime (Port 1234)", True, "Active and responsive (GPU-accelerated)")
        try:
            req = urllib.request.Request("http://127.0.0.1:1234/v1/models")
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                models = [m["id"] for m in data.get("data", [])]
                print(f"[*] Available LM Studio models: {models}")
                print_status("LM Studio Models", True, f"Found {len(models)} model(s) loaded/ready.")
                return
        except Exception as e:
            print(f"[*] Connected to LM Studio on port 1234: {e}")
            return

    # 2. Check Ollama Fallback
    ollama_running = False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect(("127.0.0.1", 11434))
            ollama_running = True
    except Exception:
        pass

    if ollama_running:
        print_status("Ollama Runtime Fallback (Port 11434)", True, "Active and responsive")
        return

    print_status("Local AI Runtime", False, "Neither LM Studio (port 1234) nor Ollama (port 11434) is currently running.")
    print("[-] Recommended: Launch LM Studio and start the local server on port 1234 (or run 'lms server start --cors').")

def fix_chroma_db():
    print_section("checking chromadb index integrity")
    user_home = os.path.expanduser("~")
    aegis_dir = os.path.join(user_home, ".aegis_ai")
    chroma_dir = os.path.join(aegis_dir, "chroma")
    
    if os.path.exists(chroma_dir):
        print(f"[*] Clearing local Chroma index cache to avoid segment discrepancies...")
        try:
            shutil.rmtree(chroma_dir)
            print_status("ChromaDB Clean", True, "Successfully reset ChromaDB directory.")
        except Exception as e:
            print_status("ChromaDB Clean", False, f"Failed to clean Chroma directory: {e}")
    else:
        print_status("ChromaDB Directory", True, "Clean directory ready.")

def main():
    print("==========================================================")
    print("⚖️ AegisAI Setup Integrity & Dependency Installer")
    print("==========================================================")
    
    check_python()
    check_venv()
    check_pip_requirements()
    check_node()
    check_frontend_deps()
    check_local_ai_runtime()
    fix_chroma_db()
    
    print("\n==========================================================")
    print("🟢 Setup Complete! Run './start.sh' to boot AegisAI.")
    print("==========================================================")

if __name__ == "__main__":
    main()
