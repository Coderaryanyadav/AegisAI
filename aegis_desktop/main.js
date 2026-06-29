const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const net = require('net');
const serve = require('electron-serve');
const serveStatic = serve({ directory: 'out' });

let mainWindow;
let splashWindow;
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

// startStaticServer removed in favor of electron-serve
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
      path: '/api/health',
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

function startBackend(port) {
  log(`Starting FastAPI backend process on port ${port}...`);
  
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
    pythonArgs = ['--port', port.toString()];
  } else {
    const venvBin = process.platform === 'win32' ? 'Scripts' : 'bin';
    const venvPath = path.join(cwd, 'venv', venvBin, process.platform === 'win32' ? 'python.exe' : 'python');
    if (fs.existsSync(venvPath)) {
      pythonExecutable = venvPath;
    }
    pythonArgs = ['-m', 'aegis_backend.main', '--port', port.toString()];
  }

  // Validate path boundaries for security
  const resolvedPath = path.resolve(pythonExecutable);
  if (!app.isPackaged && !resolvedPath.startsWith(path.resolve(cwd))) {
    log(`Security Warning: Python executable path resolves outside of sandbox: ${resolvedPath}`);
  }

  log(`Spawning backend: ${pythonExecutable} ${pythonArgs.join(' ')}`);

  try {
    backendProcess = spawn(pythonExecutable, pythonArgs, {
      cwd: cwd,
      env: { 
        ...process.env, 
        PORT: port.toString(), 
        PYTHONUNBUFFERED: '1',
        AEGIS_CORS_ORIGINS: `http://localhost:${staticServerPort},http://127.0.0.1:${staticServerPort}`
      }
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

function createSplash() {
  splashWindow = new BrowserWindow({
    width: 400,
    height: 300,
    transparent: false,
    backgroundColor: '#09090b',
    frame: false,
    alwaysOnTop: true,
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });
  splashWindow.loadFile(path.join(__dirname, 'splash.html'));
  splashWindow.once('ready-to-show', () => {
    splashWindow.show();
  });
  splashWindow.on('closed', () => {
    splashWindow = null;
  });
}

function createWindow(backendPort) {
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
      sandbox: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  mainWindow.setBackgroundColor('#09090b');

  const isDev = !app.isPackaged && process.env.NODE_ENV !== 'production';
  
  if (isDev) {
    log(`Loading local dev server: http://localhost:3000?backend_port=${backendPort}`);
    mainWindow.loadURL(`http://localhost:3000?backend_port=${backendPort}`);
    mainWindow.webContents.openDevTools();
  } else {
    log(`Loading production static build with backend port ${backendPort}`);
    serveStatic(mainWindow).then(() => {
      mainWindow.loadURL(`app://-?backend_port=${backendPort}`);
    });
  }

  mainWindow.once('ready-to-show', () => {
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
    }
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  createSplash();
  // First, find a free port for FastAPI backend
  getFreePort(8000, (freeBackendPort) => {
    const backendPort = freeBackendPort;
    
    // Start FastAPI Python backend on dynamic port
    startBackend(backendPort);

    // Wait 15 seconds max for Python backend
    checkBackend(backendPort, 15000, (backErr) => {
      if (backErr) {
        log(`Backend startup check failed on port ${backendPort}: ${backErr.message}`);
      } else {
        log(`Backend is active on port ${backendPort}. Launching UI.`);
      }
      createWindow(backendPort);
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
