const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('kayockBridge', {
  apiBase: 'http://127.0.0.1:8844'
});
