const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('kayockAPI', {
  onDownloadUpdate: (callback) => ipcRenderer.on('kayock-download-update', (_event, payload) => callback(payload)),
  onSecurityEvent: (callback) => ipcRenderer.on('kayock-security-event', (_event, payload) => callback(payload)),
  onDiagnosticEvent: (callback) => ipcRenderer.on('kayock-diagnostic-event', (_event, payload) => callback(payload)),
  showItemInFolder: (filePath) => ipcRenderer.invoke('kayock-show-item', filePath),
  openPath: (filePath) => ipcRenderer.invoke('kayock-open-path', filePath),
  chooseDownloadFolder: () => ipcRenderer.invoke('kayock-choose-download-folder'),
  setDownloadFolder: (folder) => ipcRenderer.invoke('kayock-set-download-folder', folder),
  downloadAction: (payload) => ipcRenderer.invoke('kayock-download-action', payload),
  startDownload: (url) => ipcRenderer.invoke('kayock-start-download', url),
  openExternal: (url) => ipcRenderer.invoke('kayock-open-external', url),
  toggleFullscreen: () => ipcRenderer.invoke('kayock-toggle-fullscreen'),
  setFullscreen: (value) => ipcRenderer.invoke('kayock-set-fullscreen', value),
  onFullscreenChanged: (callback) => ipcRenderer.on('kayock-fullscreen-changed', (_event, value) => callback(value)),
  onOpenUrlInTab: (callback) => ipcRenderer.on('kayock-open-url-in-tab', (_event, payload) => callback(payload)),
  onZoomShortcut: (callback) => ipcRenderer.on('kayock-zoom-shortcut', (_event, payload) => callback(payload)),
  onClearTemporaryTrust: (callback) => ipcRenderer.on('kayock-clear-temporary-trust', () => callback()),
  setWebviewZoom: (webContentsId, factor, url) => ipcRenderer.invoke('kayock-set-webview-zoom', { webContentsId, factor, url }),
  addAllowOnceMain: (host) => ipcRenderer.invoke('kayock-allow-once-add', host),
  clearAllowOnceMain: (reason) => ipcRenderer.invoke('kayock-clear-allow-once-main', reason)
});
