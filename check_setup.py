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
        try:
            subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
            print_status("venv Creation", True, "Successfully created virtual environment.")
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
        subprocess.run([pip_path, "install", "-r", REQ_FILE], check=True)
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

def check_ollama():
    print_section("checking ollama offline service")
    ollama_cli = shutil.which("ollama")
    print_status("Ollama CLI", ollama_cli is not None, f"Ollama Path: {ollama_cli or 'Not Found'}")
    
    # Try connecting to Ollama
    ollama_running = False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect(("127.0.0.1", 11434))
            ollama_running = True
    except Exception:
        pass

    if not ollama_running:
        print("[!] Ollama service is NOT running on port 11434.")
        if sys.platform == "darwin":
            print("[*] Attempting to launch Ollama desktop application...")
            try:
                subprocess.run(["open", "-a", "Ollama"])
                print("[*] Waiting for Ollama service to boot up...")
                import time
                for _ in range(10):
                    time.sleep(2)
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.settimeout(1.0)
                            s.connect(("127.0.0.1", 11434))
                            ollama_running = True
                            break
                    except Exception:
                        pass
            except Exception as e:
                print(f"[!] Failed to auto-launch Ollama: {e}")

    print_status("Ollama Running", ollama_running)
    if not ollama_running:
        print("[-] Please start the Ollama desktop app or service manually and re-run.")
        sys.exit(1)

    # Check and pull lightweight models
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            models = [m["name"] for m in data.get("models", [])]
            print(f"[*] Available local models: {models}")
            
            # We want to make sure a fast model like 'llama3.2' is available
            target_model = "llama3.2:latest"
            # If any of the existing models is llama3.2 (text-only), we're good
            has_fast_model = any(("llama3.2" in m and "vision" not in m) or "qwen2.5:3b" in m or "qwen2.5:1.5b" in m for m in models)
            
            if not has_fast_model:
                print(f"[!] No lightweight text model detected. Pulling '{target_model}' for rapid local execution...")
                pull_payload = json.dumps({"name": "llama3.2", "stream": False}).encode('utf-8')
                pull_req = urllib.request.Request(
                    "http://127.0.0.1:11434/api/pull", 
                    data=pull_payload, 
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(pull_req, timeout=600) as pull_response:
                    print_status("Model Pull", True, f"Successfully pulled model: {target_model}")
            else:
                print_status("Lightweight Local Model Check", True, "Suitable fast model found.")
    except Exception as e:
        print_status("Ollama Model Check", False, f"Failed to retrieve/pull models: {e}")

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
    check_ollama()
    fix_chroma_db()
    
    print("\n==========================================================")
    print("🟢 Setup Complete! Run './start.sh' to boot AegisAI.")
    print("==========================================================")

if __name__ == "__main__":
    main()
