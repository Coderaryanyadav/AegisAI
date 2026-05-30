# ⚖️ Aegis Legal AI

Aegis Legal AI is a **production-quality, self-hosted, and fully offline RAG assistant** designed for law firms. Built with absolute privacy and confidentiality in mind, Aegis ensures that sensitive client files, evidence, court orders, and contracts never leave the local hardware.

The application runs entirely within an air-gapped environment, utilizing a local **Ollama** inference engine and local embeddings to power contract audits, document searches, and draft generation.

---

## ⚡ Key Features

* **🔒 Zero-Cloud Confidentiality**: Run entirely on local hardware with zero external API calls. 
* **📁 AES-256 Storage at Rest**: Case files (PDF/TXT) are dynamically encrypted using AES-256 (Fernet cipher) on the filesystem immediately upon upload.
* **💬 Citation-Aware RAG Chat**: Retrieve semantic answers scoped to specific case files. Every response includes precise document page citations (e.g., `[Contract.pdf, Page 12]`).
* **🔍 Contract Risk Auditor**: Automated clause extraction (Termination, Governing Law, Indemnity), critical liability detection (High/Medium/Low), and compliance gap identification.
* **✍️ Context-Grounded Legal Draftsman**: Generate drafts of notices, filings, or contracts using your local files as references.
* **📋 Security Compliance Log**: A tamper-resistant, relational audit trail logging every user login, file upload, search query, and deletion with timestamp, IP, and details.
* **👑 Dynamic Role-Based Access Control**: Simple multi-user permission layers (`Admin`, `Lawyer`, `Auditor`).

---

## 🏗️ System Architecture

```mermaid
graph TD
    UI[Streamlit Desktop client] -->|HTTP / JSON / JWT| API[FastAPI Backend Server]
    API -->|Auth / Metadata / Log Actions| DB[(SQLite Database)]
    API -->|AES-256 Cipher| EncryptedFS[Encrypted Local Storage]
    
    subgraph Local Ingestion & Pipeline
        API -->|Page-by-page Extract| Ingestor[PDF/TXT Ingestor]
        Ingestor -->|Sentence delimiters| Chunker[Recursive Chunker]
        Chunker -->|Local Embeddings| VDB[(Chroma Vector DB)]
    end
    
    subgraph Local Inference Engine
        API -->|Semantic Retrieval Context| RAG[RAG Orchestrator]
        RAG -->|Prompt Pipeline| LLM[Ollama Local LLM]
    end
```

---

## 🛠️ Technology Stack

* **Frontend**: Streamlit (Premium customized Dark/Glassmorphic SaaS theme)
* **Backend**: FastAPI (Python)
* **Database**: SQLite (ORM via SQLAlchemy)
* **Vector DB**: ChromaDB (Running locally in persistent client mode)
* **Embeddings**: Local HuggingFace sentence-transformers (`all-MiniLM-L6-v2`)
* **Local Inference**: Ollama (`qwen3:8b` or `llama3:latest`)
* **Security & Auth**: PyJWT (token access) + Bcrypt (native password hashing) + Cryptography (AES-256 Fernet)

---

## 🚀 Getting Started

### Prerequisites

1. **Python**: Python 3.11+ (Fully tested and compliant on Python 3.14.5)
2. **Ollama**: Download and install [Ollama](https://ollama.com/) locally.
3. **Local LLM Model**: Pull a model of choice. We recommend `qwen3:8b`:
   ```bash
   ollama pull qwen3:8b
   ```

### Quick Startup (Recommended)

Aegis Legal AI is equipped with **self-bootstrapping startup scripts** for both Windows and macOS/Linux. These scripts automatically verify your Python installation, create a virtual environment (`venv`), install/upgrade dependencies, and perform port collision checks before starting the services.

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Coderaryanyadav/AegisAI.git
   cd AegisAI
   ```

2. **Launch the Application**:
   * **macOS / Linux**:
     ```bash
     chmod +x start.sh
     ./start.sh
     ```
   * **Windows**:
     Double-click `start.bat` or run it in Command Prompt:
     ```cmd
     start.bat
     ```

The script will launch:
* 🌐 **FastAPI Server**: `http://127.0.0.1:8000` (Swagger docs at `/docs`)
* ⚖️ **Streamlit Client**: `http://127.0.0.1:8501`

*Aegis automatically generates a secure Fernet encryption key and writes it to `.env` on first startup if not specified.*

### Alternative Manual Installation
If you prefer to set up the environment manually:
1. `python3 -m venv venv`
2. `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
3. `pip install -r requirements.txt`
4. Run Backend: `uvicorn legal_ai.main:app --port 8000`
5. Run Frontend: `streamlit run legal_ai/app/frontend.py`

### Default Sign-In Credentials
* **Email**: `admin@legalai.local`
* **Password**: `adminpassword123`

---

## 🧪 Running Unit Tests

We maintain strict verification logic for database operations, hashing, encryption, and semantic indexing. Run them using pytest:

```bash
python3 -m pytest
```

---

## 🔍 Troubleshooting & FAQ

### 1. `Ollama service is not running` or `Model qwen3:8b not found`
- **Solution**: Make sure you have downloaded the Ollama app from [ollama.com](https://ollama.com) and that the application is running (you should see the Ollama icon in your taskbar/menubar).
- To pull the recommended model, open a terminal window and run:
  ```bash
  ollama pull qwen3:8b
  ```
- If you run a different model (e.g. `llama3`), Aegis will dynamically fall back to it, but `qwen3:8b` is highly recommended for structured legal drafting.

### 2. `Port 8000` or `Port 8501` already in use
- **Solution**: This happens if another service (or a previous session of Aegis) is already running on those ports.
- On **macOS/Linux**, find and terminate the process:
  ```bash
  lsof -i :8000
  kill -9 <PID>
  ```
- On **Windows**, terminate any uvicorn or python server tasks:
  ```cmd
  taskkill /F /IM python.exe
  ```

### 3. Database is locked / Resetting database
- Aegis stores document metadata, users, and audit trails in a local SQLite file: `data/legal_ai.db`.
- If you ever need to reset the system database or start fresh, simply delete the `data/legal_ai.db` file. Aegis will automatically recreate a fresh database and seed the default administrator account on the next startup.

### 4. Binary package errors during `pip install` (e.g. greenlet, bcrypt)
- **Solution**: Ensure your Python installation is up to date, and you have development build tools installed.
- On **macOS**, ensure Xcode Command Line Tools are installed:
  ```bash
  xcode-select --install
  ```
- On **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt-get install python3-dev build-essential
  ```
