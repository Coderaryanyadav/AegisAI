const { contextBridge, ipcRenderer } = require('electron');

const VALID_CHANNELS = [
  'get-system-info',
  'check-backend-port'
];

contextBridge.exposeInMainWorld('aegisElectron', {
  isOffline: true,
  version: '1.0.0',
  send: (channel, data) => {
    if (VALID_CHANNELS.includes(channel)) {
      ipcRenderer.send(channel, data);
    }
  },
  receive: (channel, func) => {
    if (VALID_CHANNELS.includes(channel)) {
      ipcRenderer.on(channel, (event, ...args) => func(...args));
    }
  },
  invoke: async (channel, data) => {
    if (VALID_CHANNELS.includes(channel)) {
      return await ipcRenderer.invoke(channel, data);
    }
    throw new Error(`Unauthorized IPC channel: ${channel}`);
  }
});
