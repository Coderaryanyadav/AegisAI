const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('aegisElectron', {
  isOffline: true,
  version: '1.0.0'
});
