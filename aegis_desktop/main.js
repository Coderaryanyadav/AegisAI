const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const net = require('net');

let mainWindow;
let backendProcess = null;
let staticServerPort = 3000;

const USER_HOME = require('os').homedir();
const AEGIS_DIR = path.join(USER_HOME, '.aegis_ai');
const LOG_DIR = path.join(AEGIS_DIR, 'logs');

if (!fs.existsSync(LOG_DIR)) {
  fs.mkdirSync(LOG_DIR, { recursive: true });
}

const logFile = fs.createWriteStream(path.join(LOG_DIR, 'electron_backend.log'), { flags: 'a' });

function log(msg) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${msg}`);
  logFile.write(`[${timestamp}] ${msg}\n`);
}

// Function to find an available port dynamically
function getFreePort(startPort, callback) {
  const server = net.createServer();
  server.unref();
  server.on('error', () => {
    getFreePort(startPort + 1, callback);
  });
  server.listen(startPort, '127.0.0.1', () => {
    const port = server.address().port;
    server.close(() => {
      callback(port);
    });
  });
}

// Minimal static HTTP server to resolve Next.js asset paths correctly
function startStaticServer(port, callback) {
  const server = http.createServer((req, res) => {
    let safePath = decodeURIComponent(req.url.split('?')[0]);
    if (safePath === '/') {
      safePath = '/index.html';
    }

    const filePath = path.join(__dirname, 'out', safePath);
    const ext = path.extname(filePath).toLowerCase();
    
    const mimeTypes = {
      '.html': 'text/html',
      '.css': 'text/css',
      '.js': 'text/javascript',
      '.json': 'application/json',
      '.png': 'image/png',
      '.jpg': 'image/jpeg',
      '.gif': 'image/gif',
      '.svg': 'image/svg+xml',
      '.ico': 'image/x-icon'
    };

    const contentType = mimeTypes[ext] || 'application/octet-stream';

    fs.readFile(filePath, (err, content) => {
      if (err) {
        if (err.code === 'ENOENT') {
          // If page has trailing slash redirect or router fallback
          const alternativePath = filePath + (filePath.endsWith('/') ? 'index.html' : '/index.html');
          fs.readFile(alternativePath, (altErr, altContent) => {
            if (altErr) {
              res.writeHead(404, { 'Content-Type': 'text/plain' });
              res.end('404 Not Found');
            } else {
              res.writeHead(200, { 'Content-Type': 'text/html' });
              res.end(altContent, 'utf-8');
            }
          });
        } else {
          res.writeHead(500, { 'Content-Type': 'text/plain' });
          res.end(`Server Error: ${err.code}`);
        }
      } else {
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(content, 'utf-8');
      }
    });
  });

  server.listen(port, '127.0.0.1', () => {
    log(`Static web server running on http://127.0.0.1:${port}`);
    callback(null);
  });

  server.on('error', (err) => {
    callback(err);
  });
}

// Function to check if backend server is responsive
function checkBackend(port, timeoutMs, callback) {
  const startTime = Date.now();
  const check = () => {
    if (Date.now() - startTime > timeoutMs) {
      callback(new Error('Backend timeout'));
      return;
    }
    
    const req = http.request({
      host: '127.0.0.1',
      port: port,
      path: '/api/helper/ipc-bns?act=ipc&section=302',
      method: 'GET',
      timeout: 500
    }, (res) => {
      if (res.statusCode === 200) {
        callback(null);
      } else {
        setTimeout(check, 500);
      }
    });

    req.on('error', () => {
      setTimeout(check, 500);
    });

    req.end();
  };
  check();
}

function startBackend() {
  log('Starting FastAPI backend process...');
  
  let pythonExecutable = 'python3';
  let pythonArgs = [];
  let cwd = path.join(__dirname, '..');

  if (app.isPackaged) {
    const platform = process.platform;
    if (platform === 'win32') {
      pythonExecutable = path.join(process.resourcesPath, 'aegis_backend', 'aegis_backend.exe');
    } else {
      pythonExecutable = path.join(process.resourcesPath, 'aegis_backend', 'aegis_backend');
    }
    cwd = process.resourcesPath;
  } else {
    const venvBin = process.platform === 'win32' ? 'Scripts' : 'bin';
    const venvPath = path.join(cwd, 'venv', venvBin, process.platform === 'win32' ? 'python.exe' : 'python');
    if (fs.existsSync(venvPath)) {
      pythonExecutable = venvPath;
    }
    pythonArgs = ['-m', 'aegis_backend.main'];
  }

  log(`Spawning backend: ${pythonExecutable} ${pythonArgs.join(' ')}`);

  try {
    backendProcess = spawn(pythonExecutable, pythonArgs, {
      cwd: cwd,
      env: { ...process.env, PYTHONUNBUFFERED: '1' }
    });

    backendProcess.stdout.on('data', (data) => {
      log(`[Backend STDOUT]: ${data.toString().trim()}`);
    });

    backendProcess.stderr.on('data', (data) => {
      log(`[Backend STDERR]: ${data.toString().trim()}`);
    });

    backendProcess.on('close', (code) => {
      log(`Backend process exited with code ${code}`);
    });
  } catch (err) {
    log(`Failed to spawn backend process: ${err}`);
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    title: 'AegisAI Offline Legal Suite',
    width: 1366,
    height: 900,
    minWidth: 1024,
    minHeight: 768,
    frame: true,
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  mainWindow.setBackgroundColor('#09090b');

  const isDev = !app.isPackaged && process.env.NODE_ENV !== 'production';
  
  if (isDev) {
    log('Loading local dev server: http://localhost:3000');
    mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools();
  } else {
    log(`Loading production static build on port ${staticServerPort}`);
    mainWindow.loadURL(`http://127.0.0.1:${staticServerPort}`);
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  // First, find a free port for static Next.js assets
  getFreePort(3000, (freePort) => {
    staticServerPort = freePort;
    
    // Start local static server
    startStaticServer(staticServerPort, (err) => {
      if (err) {
        log(`Failed to start static server: ${err.message}`);
      }
      
      // Start FastAPI Python backend
      startBackend();

      // Wait 15 seconds max for Python backend
      checkBackend(8000, 15000, (backErr) => {
        if (backErr) {
          log(`Backend startup check failed: ${backErr.message}`);
        } else {
          log('Backend is active on port 8000. Launching UI.');
        }
        createWindow();
      });
    });
  });
});

app.on('window-all-closed', () => {
  log('All windows closed. Terminating processes.');
  if (backendProcess) {
    log('Terminating FastAPI backend child process...');
    backendProcess.kill('SIGINT');
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});
