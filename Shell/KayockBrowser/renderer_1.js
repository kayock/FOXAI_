const address = document.getElementById('address');
const navForm = document.getElementById('navForm');
const home = document.getElementById('home');
const homeSearch = document.getElementById('homeSearch');
const homeQuery = document.getElementById('homeQuery');
const tabsEl = document.getElementById('tabs');
const webviewsEl = document.getElementById('webviews');
const shieldPanel = document.getElementById('shieldPanel');
const bookmarksPanel = document.getElementById('bookmarksPanel');
const historyPanel = document.getElementById('historyPanel');
const downloadsPanel = document.getElementById('downloadsPanel');
const settingsPanel = document.getElementById('settingsPanel');
const aboutPanel = document.getElementById('aboutPanel');
const diagnosticsPanel = document.getElementById('diagnosticsPanel');
const workshopPanel = document.getElementById('workshopPanel');
const hunterPanel = document.getElementById('hunterPanel');
const tracksList = document.getElementById('tracksList');
const currentHuntName = document.getElementById('currentHuntName');
const currentHuntMeta = document.getElementById('currentHuntMeta');
const diagnosticsList = document.getElementById('diagnosticsList');
const hunterToast = document.getElementById('hunterToast');
const securityEvents = document.getElementById('securityEvents');
const bookmarksList = document.getElementById('bookmarksList');
const historyList = document.getElementById('historyList');
const downloadsList = document.getElementById('downloadsList');
const siteStatus = document.getElementById('siteStatus');
const shieldBtn = document.getElementById('shieldBtn');
const trustSiteBtn = document.getElementById('trustSiteBtn');
const blockSiteBtn = document.getElementById('blockSiteBtn');
const allowOnceBtn = document.getElementById('allowOnceBtn');
const shieldMode = document.getElementById('shieldMode');
const javascriptStatus = document.getElementById('javascriptStatus');
const shieldDomain = document.getElementById('shieldDomain');
const trustedList = document.getElementById('trustedList');
const shieldAdvice = document.getElementById('shieldAdvice');
const starvedBanner = document.getElementById('starvedBanner');
const bannerTrust = document.getElementById('bannerTrust');
const bannerOnce = document.getElementById('bannerOnce');
const bannerOpenShield = document.getElementById('bannerOpenShield');
const zoomOutBtn = document.getElementById('zoomOut');
const zoomInBtn = document.getElementById('zoomIn');
const zoomDisplay = document.getElementById('zoomDisplay');

// Kayock 2.4: default to compact icon rail. Users may pin it open.
if (localStorage.getItem('kayockHunterPinned') === 'true') document.body.classList.add('hunterPinned');

let tabs = [];
let activeTabId = null;
let nextTabId = 1;
let saveTimer = null;

const defaultSettings = { searchEngine: 'duckduckgo', restoreSession: true, openHomeNewTab: true, downloadFolder: '', defaultZoom: 1, uiSize: 'large', uiFont: 'legible', spellcheckUS: true, largeMenus: true, reduceMotion: false };
// Kayock 2.1.2: Allow Once is intentionally session-only.
// It never gets written to localStorage or exported in Vault backups.
const allowOnceSites = new Set();
const panels = () => [shieldPanel, bookmarksPanel, historyPanel, downloadsPanel, settingsPanel, diagnosticsPanel, aboutPanel, workshopPanel].filter(Boolean);
const defaultShield = { mode: 'balanced', trustedSites: [], blockedSites: [], events: [] };

function getSettings() {
  try { return { ...defaultSettings, ...JSON.parse(localStorage.getItem('kayockSettings') || '{}') }; }
  catch { return defaultSettings; }
}
function saveSettingsObject(settings) { localStorage.setItem('kayockSettings', JSON.stringify(settings)); applyAppearanceSettings(); }
function applyAppearanceSettings() {
  const s = getSettings();
  const uiSize = s.uiSize || 'large';
  const uiFont = s.uiFont || 'legible';
  document.body.dataset.uiSize = uiSize;
  document.body.dataset.uiFont = uiFont;
  document.documentElement.dataset.uiSize = uiSize;
  document.documentElement.dataset.uiFont = uiFont;
  document.body.classList.toggle('largeMenus', !!s.largeMenus);
  document.body.classList.toggle('reduceMotion', !!s.reduceMotion);
  document.body.classList.toggle('spellcheckUS', s.spellcheckUS !== false);

  const fontMap = {
    default: "Georgia, 'Times New Roman', serif",
    legible: "'Atkinson Hyperlegible', Verdana, Arial, sans-serif",
    verdana: "Verdana, Geneva, sans-serif",
    dyslexic: "'OpenDyslexic', 'Comic Sans MS', Verdana, Arial, sans-serif",
    system: "'Segoe UI', Arial, sans-serif"
  };
  const sizeMap = { normal: 1, large: 1.12, extra: 1.28 };
  const fontFamily = fontMap[uiFont] || fontMap.legible;
  const scale = sizeMap[uiSize] || 1.12;
  let style = document.getElementById('kayockAccessibilityStyle');
  if (!style) {
    style = document.createElement('style');
    style.id = 'kayockAccessibilityStyle';
    document.head.appendChild(style);
  }
  style.textContent = `
    html, body, body *:not(code):not(pre) { font-family: ${fontFamily} !important; }
    button, input, textarea, select, .tab, .brand, .sidePanel, .panelTitle, .quickLinks, .toolbar { font-family: ${fontFamily} !important; }
    body { font-size: ${Math.round(15 * scale)}px !important; }
    .topbar button, .topbar input, .sidePanel button, .sidePanel input, .sidePanel select { font-size: ${Math.round(14 * scale)}px !important; }
    .tab { font-size: ${Math.round(13 * scale)}px !important; min-height: ${Math.round(28 * scale)}px !important; }
    .name { font-size: ${Math.round(25 * scale)}px !important; }
    .tagline { font-size: ${Math.round(11 * scale)}px !important; }
    .sidePanel { font-size: ${Math.round(14 * scale)}px !important; width: ${Math.round(350 * Math.min(scale, 1.18))}px !important; }
    #address { font-size: ${Math.round(14 * scale)}px !important; }
  `;
}
function openAccessibilitySettings() {
  showSettingsPanel();
  setTimeout(() => document.getElementById('uiSize')?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 60);
}

function getShield() {
  try { return { ...defaultShield, ...JSON.parse(localStorage.getItem('kayockShield') || '{}') }; }
  catch { return { ...defaultShield }; }
}
function saveShield(shield) {
  const safeShield = {
    ...shield,
    trustedSites: [...new Set(shield.trustedSites || [])],
    blockedSites: [...new Set(shield.blockedSites || [])]
  };
  delete safeShield.allowOnce;
  localStorage.setItem('kayockShield', JSON.stringify(safeShield));
  renderShieldPanel();
}

function getHost(url) { try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return ''; } }
function isInternal(url) { return !url || url.startsWith('kayock://'); }
function shouldAllowJavascript(url) {
  if (isInternal(url)) return true;
  const host = getHost(url);
  const s = getShield();
  if ((s.blockedSites || []).includes(host)) return false;
  if (allowOnceSites.has(host)) return true;
  if ((s.trustedSites || []).includes(host)) return true;
  if (s.mode === 'compatibility') return true;
  return false; // Balanced and Hunter Mode both start with JavaScript blocked for unknown sites.
}
function shieldLabel(url) {
  if (isInternal(url)) return 'Kayock internal page';
  const host = getHost(url);
  const s = getShield();
  if ((s.trustedSites || []).includes(host)) return 'Trusted · scripts allowed';
  if (allowOnceSites.has(host)) return 'Allowed once · scripts allowed';
  if ((s.blockedSites || []).includes(host)) return 'Blocked site · scripts blocked';
  if (s.mode === 'compatibility') return 'Compatibility mode · scripts allowed';
  return 'Unknown site · scripts blocked';
}
function updateShieldIndicator() {
  const tab = activeTab();
  const url = tab?.url || 'kayock://home';
  const allowed = shouldAllowJavascript(url);
  const internal = isInternal(url);
  document.body.classList.toggle('shieldBlocked', !allowed && !internal);
  document.body.classList.toggle('shieldTrusted', allowed && !internal);
  if (shieldBtn) shieldBtn.textContent = allowed || internal ? '◉ Shield' : '◉ Shield 🔴';
  if (siteStatus) siteStatus.textContent = `Current site: ${tab?.title || 'Kayock'} · ${shieldLabel(url)}`;
  if (starvedBanner) starvedBanner.classList.toggle('hidden', allowed || internal);
}

function searchUrl(query) {
  const engine = getSettings().searchEngine;
  if (engine === 'google') return `https://www.google.com/search?q=${encodeURIComponent(query)}`;
  if (engine === 'bing') return `https://www.bing.com/search?q=${encodeURIComponent(query)}`;
  return `https://duckduckgo.com/?q=${encodeURIComponent(query)}`;
}
function normalizeInput(text) {
  const value = text.trim();
  if (!value || value === 'kayock://home') return 'kayock://home';
  if (value === 'kayock://history' || value === 'kayock://tracks') return 'kayock://history';
  if (value === 'kayock://downloads' || value === 'kayock://trophies') return 'kayock://downloads';
  if (value === 'kayock://settings') return 'kayock://settings';
  if (value === 'kayock://about') return 'kayock://about';
  if (value === 'kayock://diagnostics') return 'kayock://diagnostics';
  if (value === 'kayock://shield') return 'kayock://shield';
  const looksLikeUrl = value.includes('.') && !value.includes(' ');
  if (value.startsWith('http://') || value.startsWith('https://')) return value;
  if (looksLikeUrl) return `https://${value}`;
  return searchUrl(value);
}
function makeTitle(url) {
  if (url === 'kayock://home') return 'Kayock Home';
  if (url === 'kayock://history') return 'Tracks';
  if (url === 'kayock://downloads') return 'Trophy Room';
  if (url === 'kayock://settings') return 'Settings';
  if (url === 'kayock://about') return 'About Kayock';
  if (url === 'kayock://diagnostics') return 'Hunter Diagnostics';
  if (url === 'kayock://shield') return 'Hunter Shield';
  try { return new URL(url).hostname.replace('www.', ''); } catch { return 'New Hunt'; }
}

function looksLikeDirectDownload(url) {
  return /\/resolve\//i.test(url)
    || /[?&]download=1/i.test(url)
    || /\.(gguf|safetensors|bin|zip|7z|rar|tar|gz|iso|exe|msi|pdf|mp4|mp3)(\?|#|$)/i.test(url);
}
function startDirectDownload(url) {
  const clean = String(url || '').trim();
  if (!/^https?:\/\//i.test(clean)) {
    alert('Kayock can only acquire http/https links right now.');
    return;
  }
  window.kayockAPI?.startDownload?.(clean).then(result => {
    if (!result?.ok) alert('Acquire failed: ' + (result?.error || 'unknown error'));
    else showDownloadsPanel();
  });
}


function getZoomMap() { try { return JSON.parse(localStorage.getItem('kayockSiteZoom') || '{}'); } catch { return {}; } }
function saveZoomMap(map) { localStorage.setItem('kayockSiteZoom', JSON.stringify(map)); }
function zoomKeyFor(url) { return isInternal(url) ? 'kayock://internal' : (getHost(url) || 'default'); }
function clampZoom(value) { return Math.min(2.5, Math.max(0.75, Number(value) || 1)); }
function getCurrentZoomFactor(url = activeTab()?.url || 'kayock://home') {
  const map = getZoomMap();
  const key = zoomKeyFor(url);
  return clampZoom(map[key] || getSettings().defaultZoom || 1);
}
function zoomLevelFromFactor(factor) { return Math.log(clampZoom(factor)) / Math.log(1.2); }
function applyZoomToTab(tab = activeTab()) {
  if (!tab) return;
  const factor = getCurrentZoomFactor(tab.url);
  if (zoomDisplay) zoomDisplay.textContent = `${Math.round(factor * 100)}%`;
  const wv = tab.webview;
  if (!wv || isInternal(tab.url)) return;

  // Kayock 2.1.2: prefer native Electron zoom via main-process IPC.
  // The previous CSS injection fallback worked for stubborn pages but could break
  // viewport layouts and cost CPU on media-heavy pages.
  try {
    const id = typeof wv.getWebContentsId === 'function' ? wv.getWebContentsId() : 0;
    if (id && window.kayockAPI?.setWebviewZoom) {
      window.kayockAPI.setWebviewZoom(id, factor, tab.url).then(result => {
        if (!result?.ok) addDiagnostic({ type: 'zoom-error', message: result?.error || 'Zoom IPC failed', url: tab.url });
      }).catch(err => addDiagnostic({ type: 'zoom-error', message: err.message, url: tab.url }));
    }
  } catch (err) {
    addDiagnostic({ type: 'zoom-error', message: err.message, url: tab.url });
  }

  try { if (typeof wv.setZoomFactor === 'function') wv.setZoomFactor(factor); } catch {}
  try { if (typeof wv.setZoomLevel === 'function') wv.setZoomLevel(zoomLevelFromFactor(factor)); } catch {}
}
function setZoomForCurrent(factor) {
  const tab = activeTab(); if (!tab) return;
  const map = getZoomMap();
  map[zoomKeyFor(tab.url)] = clampZoom(factor);
  saveZoomMap(map);
  applyZoomToTab(tab);
}
function stepZoom(delta) {
  const current = getCurrentZoomFactor();
  const steps = [0.75, 0.9, 1, 1.1, 1.25, 1.5, 1.75, 2, 2.5];
  let idx = steps.findIndex(v => Math.abs(v - current) < 0.01);
  if (idx === -1) idx = steps.findIndex(v => v > current) - 1;
  if (idx < 0) idx = 2;
  setZoomForCurrent(steps[Math.min(steps.length - 1, Math.max(0, idx + delta))]);
}
function resetZoomForCurrent() { setZoomForCurrent(getSettings().defaultZoom || 1); }

function activeTab() { return tabs.find(t => t.id === activeTabId); }
function hidePanels() { panels().forEach(p => p.classList.add('hidden')); }
function showOnlyPanel(panel) { panels().forEach(p => p.classList.toggle('hidden', p !== panel)); }
function enhancePanels() {
  panels().forEach(panel => {
    if (panel.dataset.enhanced === 'true') return;
    const h2 = panel.querySelector('h2');
    if (!h2) return;
    const title = h2.textContent;
    h2.classList.add('panelTitle');
    h2.innerHTML = `<span>${escapeHtml(title)}</span><button class="panelClose" title="Close panel" aria-label="Close panel">×</button>`;
    h2.querySelector('.panelClose').addEventListener('click', (e) => { e.stopPropagation(); hidePanels(); });
    panel.dataset.enhanced = 'true';
  });
}
function updateJournal() {
  const shield = getShield();
  const set = (id, value) => { const el = document.getElementById(id); if (el) el.textContent = value; };
  set('journalShield', `${(shield.mode || 'balanced')} / active`);
  set('journalTrusted', String((shield.trustedSites || []).length));
  set('journalMarks', String(getBookmarks().length));
  set('journalTracks', String(getHistory().length));
  set('journalTrophies', String(getDownloads().length));
}
function showHome(show) { home.classList.toggle('hidden', !show); }
function saveSessionSoon() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    const session = tabs.map(t => ({ url: t.url, title: t.title }));
    localStorage.setItem('kayockSession', JSON.stringify({ activeTabId, tabs: session, currentTrackId }));
    syncCurrentTrackFromOpenTabs();
  }, 150);
}
function restoreSession() {
  if (!getSettings().restoreSession) return false;
  try {
    const saved = JSON.parse(localStorage.getItem('kayockSession') || 'null');
    if (!saved?.tabs?.length) return false;
    saved.tabs.slice(0, 12).forEach(t => createTab(t.url || 'kayock://home', false));
    setActiveTab(tabs[0]?.id);
    return true;
  } catch { return false; }
}


const defaultTrackId = 'base-camp';
let currentTrackId = localStorage.getItem('kayockCurrentTrack') || defaultTrackId;
function getTracks() {
  try {
    const saved = JSON.parse(localStorage.getItem('kayockTracks') || '[]');
    const list = Array.isArray(saved) ? saved : [];
    if (!list.some(t => t.id === defaultTrackId)) list.unshift({ id: defaultTrackId, name: 'Base Camp', icon: '🦅', color: 'gold', tabs: [], created: new Date().toISOString(), updated: new Date().toISOString() });
    return list;
  } catch {
    return [{ id: defaultTrackId, name: 'Base Camp', icon: '🦅', color: 'gold', tabs: [], created: new Date().toISOString(), updated: new Date().toISOString() }];
  }
}
function saveTracks(items) { localStorage.setItem('kayockTracks', JSON.stringify(items)); renderTracks(); updateCampfire(); }
function currentTrack() { return getTracks().find(t => t.id === currentTrackId) || getTracks()[0]; }
function tabSnapshot(tab) { return { url: tab.url, title: tab.title || makeTitle(tab.url), pinned: !!tab.pinned, saved: new Date().toISOString() }; }
function syncCurrentTrackFromOpenTabs() {
  const tracks = getTracks();
  const idx = tracks.findIndex(t => t.id === currentTrackId);
  if (idx === -1) return;
  tracks[idx].tabs = tabs.map(tabSnapshot);
  tracks[idx].updated = new Date().toISOString();
  localStorage.setItem('kayockTracks', JSON.stringify(tracks));
  updateCampfire();
}
function createTrack(name) {
  const clean = String(name || '').trim() || `New Hunt ${getTracks().length + 1}`;
  const track = { id: 'track-' + Date.now(), name: clean, icon: '📂', color: 'gold', tabs: [], created: new Date().toISOString(), updated: new Date().toISOString() };
  const tracks = getTracks(); tracks.unshift(track); saveTracks(tracks); switchTrack(track.id, false); showHunterToast(`Created Track: ${clean}`, 'Tracks');
}
function switchTrack(id, restoreTabs = true) {
  syncCurrentTrackFromOpenTabs();
  currentTrackId = id || defaultTrackId;
  localStorage.setItem('kayockCurrentTrack', currentTrackId);
  const track = currentTrack();
  if (restoreTabs) {
    for (const t of [...tabs]) t.webview?.remove?.();
    tabs = []; activeTabId = null;
    const savedTabs = (track.tabs || []).length ? track.tabs : [{ url: 'kayock://home', title: 'Kayock Home' }];
    savedTabs.slice(0, 24).forEach(t => createTab(t.url || 'kayock://home', false));
    setActiveTab(tabs[0]?.id);
  }
  renderTracks(); updateCampfire(); saveSessionSoon();
}
function moveTabToTrack(tabId, trackId) {
  const tab = tabs.find(t => t.id === tabId);
  if (!tab) return;
  const tracks = getTracks();
  const target = tracks.find(t => t.id === trackId);
  if (!target) return;
  target.tabs = (target.tabs || []).filter(x => x.url !== tab.url);
  target.tabs.unshift(tabSnapshot(tab));
  target.updated = new Date().toISOString();
  saveTracks(tracks);
  showHunterToast(`Moved tab to ${target.name}`, 'Tracks');
}
function updateCampfire() {
  const track = currentTrack();
  if (currentHuntName) currentHuntName.textContent = track?.name || 'Base Camp';
  if (currentHuntMeta) currentHuntMeta.textContent = `${tabs.length} open tab${tabs.length === 1 ? '' : 's'}`;
}
function renameTrack(trackId) {
  const tracks = getTracks();
  const idx = tracks.findIndex(t => t.id === trackId);
  if (idx === -1) return;
  const next = prompt('Rename Track:', tracks[idx].name);
  if (!next || !next.trim()) return;
  tracks[idx].name = next.trim();
  tracks[idx].updated = new Date().toISOString();
  saveTracks(tracks);
  showHunterToast(`Renamed Track: ${tracks[idx].name}`, 'Tracks');
}
function deleteTrack(trackId) {
  if (trackId === defaultTrackId) { showHunterToast('Base Camp cannot be deleted.', 'Tracks'); return; }
  const tracks = getTracks();
  const track = tracks.find(t => t.id === trackId);
  if (!track) return;
  if (!confirm(`Delete Track "${track.name}"? Saved tabs in this Track will be removed from the workspace list.`)) return;
  const remaining = tracks.filter(t => t.id !== trackId);
  saveTracks(remaining);
  if (currentTrackId === trackId) switchTrack(defaultTrackId, true);
  showHunterToast(`Deleted Track: ${track.name}`, 'Tracks');
}
function renderTracks() {
  if (!tracksList) return;
  const tracks = getTracks();
  tracksList.innerHTML = '';
  for (const track of tracks) {
    const card = document.createElement('div');
    card.className = 'trackCard' + (track.id === currentTrackId ? ' active' : '');
    card.dataset.trackId = track.id;
    const count = (track.id === currentTrackId ? tabs.length : (track.tabs || []).length);
    card.innerHTML = `<div class="trackMain"><strong>${escapeHtml(track.icon || '📂')} ${escapeHtml(track.name)}</strong><span>${count} tab${count === 1 ? '' : 's'} · ${track.id === currentTrackId ? 'Active' : 'Sleeping'}</span></div><div class="trackActions"><button data-action="open">Resume</button><button data-action="save">Save</button><button data-action="rename">Rename</button><button data-action="delete">Delete</button></div>`;
    card.addEventListener('dragover', e => { e.preventDefault(); card.classList.add('dropReady'); });
    card.addEventListener('dragleave', () => card.classList.remove('dropReady'));
    card.addEventListener('drop', e => { e.preventDefault(); card.classList.remove('dropReady'); const tabId = Number(e.dataTransfer.getData('text/kayock-tab-id')); if (tabId) moveTabToTrack(tabId, track.id); });
    card.querySelector('[data-action="open"]').addEventListener('click', () => switchTrack(track.id, true));
    card.querySelector('[data-action="save"]').addEventListener('click', () => { currentTrackId = track.id; localStorage.setItem('kayockCurrentTrack', currentTrackId); syncCurrentTrackFromOpenTabs(); renderTracks(); showHunterToast(`Saved open tabs to ${track.name}`, 'Tracks'); });
    card.querySelector('[data-action="rename"]').addEventListener('click', () => renameTrack(track.id));
    card.querySelector('[data-action="delete"]').addEventListener('click', () => deleteTrack(track.id));
    tracksList.appendChild(card);
  }
}


function applyHunterWritingStyles(tab) {
  const wv = tab?.webview;
  if (!wv || isInternal(tab.url)) return;
  const settings = getSettings();
  if (settings.spellcheckUS === false) return;
  const css = `
    ::spelling-error {
      text-decoration-line: underline;
      text-decoration-style: wavy;
      text-decoration-thickness: 2px;
      text-decoration-color: #ff3355;
      background-color: rgba(255, 51, 85, 0.20);
      border-radius: 3px;
    }
    ::grammar-error {
      text-decoration-line: underline;
      text-decoration-style: wavy;
      text-decoration-thickness: 2px;
      text-decoration-color: #ffb000;
      background-color: rgba(255, 176, 0, 0.18);
      border-radius: 3px;
    }
    textarea, input[type='text'], input[type='search'], input[type='email'], input:not([type]), [contenteditable='true'] {
      caret-color: #ffdf8b;
    }
  `;
  try {
    if (typeof wv.insertCSS === 'function') wv.insertCSS(css).catch?.(() => {});
  } catch (err) {
    addDiagnostic({ type: 'hunter-writing-css-error', message: err.message, url: tab.url });
  }
}

function createWebviewForTab(tab, url) {
  const webview = document.createElement('webview');
  webview.className = 'webview hidden';
  // Popups are routed into Kayock tabs by main-process handlers; do not grant raw popup power here.
  webview.setAttribute('allowfullscreen', '');
  webview.setAttribute('spellcheck', 'true');
  webview.setAttribute('lang', 'en-US');
  const allowJs = shouldAllowJavascript(url);
  webview.setAttribute('webpreferences', `contextIsolation=yes, nodeIntegration=no, spellcheck=yes, webSecurity=yes, allowRunningInsecureContent=no, javascript=${allowJs ? 'yes' : 'no'}`);
  if (!isInternal(url)) webview.src = url;

  webview.addEventListener('did-attach', () => { applyZoomToTab(tab); applyHunterWritingStyles(tab); });
  webview.addEventListener('dom-ready', () => { applyZoomToTab(tab); applyHunterWritingStyles(tab); });
  webview.addEventListener('did-start-loading', () => document.body.classList.add('loading'));
  webview.addEventListener('did-stop-loading', () => { document.body.classList.remove('loading'); updateShieldIndicator(); applyZoomToTab(tab); applyHunterWritingStyles(tab); });
  webview.addEventListener('did-navigate', (event) => updateTabUrl(tab.id, event.url, true));
  webview.addEventListener('did-navigate-in-page', (event) => updateTabUrl(tab.id, event.url, true));
  webview.addEventListener('page-title-updated', (event) => {
    const t = tabs.find(x => x.id === tab.id);
    if (!t) return;
    t.title = event.title || makeTitle(t.url);
    renderTabs(); saveSessionSoon();
    if (tab.id === activeTabId) document.title = `${t.title} — Kayock`;
  });
  webview.addEventListener('did-fail-load', () => {
    const t = tabs.find(x => x.id === tab.id);
    if (!t) return;
    t.title = 'Load failed'; renderTabs();
  });

  webview.addEventListener('enter-html-full-screen', () => { document.body.classList.add('webviewFullscreen'); window.kayockAPI?.setFullscreen?.(true); });
  webview.addEventListener('leave-html-full-screen', () => { document.body.classList.remove('webviewFullscreen'); window.kayockAPI?.setFullscreen?.(false); });
  applyZoomToTab(tab);

  // v1.2 Compatibility: catch common generated download links/popups.
  // Hugging Face and GitHub often use /resolve/ or redirect URLs for large files.
  webview.addEventListener('new-window', (event) => {
    const targetUrl = event.url || '';
    if (looksLikeDirectDownload(targetUrl)) {
      event.preventDefault?.();
      startDirectDownload(targetUrl);
      return;
    }
    if (targetUrl) {
      event.preventDefault?.();
      createTab(targetUrl, true);
    }
  });
  webview.addEventListener('will-navigate', (event) => {
    const targetUrl = event.url || '';
    if (looksLikeDirectDownload(targetUrl)) {
      event.preventDefault?.();
      startDirectDownload(targetUrl);
    }
  });
  // v1.2.1 Compatibility Hotfix: removed page script injection.
  // Downloads are now handled through Electron navigation/window/download events and the right-click menu.
  return webview;
}
function replaceWebview(tab, url) {
  const old = tab.webview;
  const webview = createWebviewForTab(tab, url);
  tab.webview = webview;
  webviewsEl.appendChild(webview);
  if (old) old.remove();
  webview.classList.toggle('hidden', tab.id !== activeTabId || isInternal(url));
}
function createTab(startUrl = null, makeActive = true) {
  const settings = getSettings();
  const url = startUrl || (settings.openHomeNewTab ? 'kayock://home' : 'https://duckduckgo.com');
  const id = nextTabId++;
  const tab = { id, url, title: makeTitle(url), webview: null };
  tabs.push(tab);
  replaceWebview(tab, url);
  if (makeActive) setActiveTab(id); else renderTabs();
  saveSessionSoon();
  return tab;
}
function closeTab(id) {
  const idx = tabs.findIndex(t => t.id === id);
  if (idx === -1) return;
  const wasActive = activeTabId === id;
  tabs[idx].webview.remove(); tabs.splice(idx, 1);
  if (!tabs.length) { createTab('kayock://home'); return; }
  if (wasActive) setActiveTab(tabs[Math.max(0, idx - 1)].id);
  renderTabs(); saveSessionSoon();
}
function setActiveTab(id) {
  activeTabId = id;
  const tab = activeTab();
  if (!tab) return;
  tabs.forEach(t => t.webview.classList.toggle('hidden', t.id !== id || isInternal(t.url)));
  showHome(isInternal(tab.url));
  address.value = tab.url;
  document.title = `${tab.title} — Kayock`;
  renderTabs(); renderShieldPanel(); updateShieldIndicator(); applyZoomToTab(tab); saveSessionSoon();
}
function updateTabUrl(id, url, addTrack = false) {
  const tab = tabs.find(t => t.id === id);
  if (!tab) return;
  tab.url = url; tab.title = makeTitle(url);
  if (addTrack && !isInternal(url)) addHistory(tab.title, url);
  if (id === activeTabId) { address.value = url; renderShieldPanel(); updateShieldIndicator(); applyZoomToTab(tab); }
  renderTabs(); saveSessionSoon();
}
function loadTarget(text) {
  const url = normalizeInput(text);
  const tab = activeTab() || createTab('kayock://home');
  tab.url = url; tab.title = makeTitle(url);
  if (url === 'kayock://history') { showHistoryPanel(); showHome(true); tab.webview.classList.add('hidden'); }
  else if (url === 'kayock://downloads') { showDownloadsPanel(); showHome(true); tab.webview.classList.add('hidden'); }
  else if (url === 'kayock://settings') { showSettingsPanel(); showHome(true); tab.webview.classList.add('hidden'); }
  else if (url === 'kayock://shield') { showShieldPanel(); showHome(true); tab.webview.classList.add('hidden'); }
  else if (url === 'kayock://about') { showAboutPanel(); showHome(true); tab.webview.classList.add('hidden'); }
  else if (url === 'kayock://diagnostics') { showDiagnosticsPanel(); showHome(true); tab.webview.classList.add('hidden'); }
  else if (isInternal(url)) { hidePanels(); showHome(true); tab.webview.classList.add('hidden'); }
  else { hidePanels(); showHome(false); replaceWebview(tab, url); addHistory(tab.title, url); }
  address.value = url;
  document.title = `${tab.title} — Kayock`;
  renderTabs(); renderShieldPanel(); updateShieldIndicator(); saveSessionSoon();
}
function reloadCurrentWithShield() {
  const tab = activeTab();
  if (!tab || isInternal(tab.url)) return;
  replaceWebview(tab, tab.url);
  renderShieldPanel(); updateShieldIndicator(); saveSessionSoon();
}
function renderTabs() {
  tabsEl.innerHTML = '';
  for (const tab of tabs) {
    const btn = document.createElement('button');
    btn.className = 'tab' + (tab.id === activeTabId ? ' active' : '');
    btn.title = tab.url;
    btn.draggable = true;
    const lock = !shouldAllowJavascript(tab.url) && !isInternal(tab.url) ? ' 🔴' : '';
    btn.innerHTML = `<span>${escapeHtml(tab.title)}${lock}</span><b title="Close">×</b>`;
    btn.addEventListener('click', () => setActiveTab(tab.id));
    btn.addEventListener('dragstart', (e) => { e.dataTransfer.setData('text/kayock-tab-id', String(tab.id)); e.dataTransfer.effectAllowed = 'move'; document.body.classList.add('draggingTab'); });
    btn.addEventListener('dragend', () => document.body.classList.remove('draggingTab'));
    btn.addEventListener('contextmenu', (e) => { e.preventDefault(); const names = getTracks().map(t => t.name).join('\n'); const choice = prompt(`Move this tab to Track:\n${names}\n\nType an existing Track name or a new one:`, currentTrack()?.name || 'Base Camp'); if (!choice) return; let track = getTracks().find(t => t.name.toLowerCase() === choice.trim().toLowerCase()); if (!track) { createTrack(choice); track = currentTrack(); } moveTabToTrack(tab.id, track.id); });
    btn.addEventListener('auxclick', (e) => { if (e.button === 1) closeTab(tab.id); });
    btn.querySelector('b').addEventListener('click', (e) => { e.stopPropagation(); closeTab(tab.id); });
    tabsEl.appendChild(btn);
  }
}
function escapeHtml(text) { return String(text).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

function getBookmarks() { try { return JSON.parse(localStorage.getItem('kayockBookmarks') || '[]'); } catch { return []; } }
function saveBookmarks(bookmarks) { localStorage.setItem('kayockBookmarks', JSON.stringify(bookmarks)); renderBookmarks(); }
function addCurrentBookmark() {
  const tab = activeTab(); if (!tab || isInternal(tab.url)) return;
  const bookmarks = getBookmarks();
  if (!bookmarks.some(b => b.url === tab.url)) {
    bookmarks.unshift({ title: tab.title || makeTitle(tab.url), url: tab.url, added: new Date().toISOString() }); saveBookmarks(bookmarks);
  }
  showBookmarksPanel();
}
function removeBookmark(url) { saveBookmarks(getBookmarks().filter(b => b.url !== url)); }
function renderBookmarks() {
  const bookmarks = getBookmarks(); bookmarksList.innerHTML = '';
  if (!bookmarks.length) { bookmarksList.innerHTML = '<div class="note">No Hunter Marks yet. Visit a page and click ★.</div>'; return; }
  for (const item of bookmarks) {
    const row = document.createElement('div'); row.className = 'bookmarkItem';
    row.innerHTML = `<div class="openItem"><div class="bookmarkTitle">${escapeHtml(item.title)}</div><div class="bookmarkUrl">${escapeHtml(item.url)}</div></div><button title="Remove">×</button>`;
    row.querySelector('.openItem').addEventListener('click', () => loadTarget(item.url));
    row.querySelector('button').addEventListener('click', () => removeBookmark(item.url)); bookmarksList.appendChild(row);
  }
}
function getHistory() { try { return JSON.parse(localStorage.getItem('kayockHistory') || '[]'); } catch { return []; } }
function saveHistory(items) { localStorage.setItem('kayockHistory', JSON.stringify(items.slice(0, 250))); renderHistory(); }
function addHistory(title, url) {
  if (!url || isInternal(url)) return;
  const items = getHistory().filter(x => x.url !== url);
  items.unshift({ title: title || makeTitle(url), url, visited: new Date().toISOString() }); saveHistory(items);
}
function renderHistory() {
  const items = getHistory(); historyList.innerHTML = '';
  if (!items.length) { historyList.innerHTML = '<div class="note">No tracks yet. Browse a page and Kayock will remember it.</div>'; return; }
  for (const item of items) {
    const row = document.createElement('div'); row.className = 'bookmarkItem'; const when = new Date(item.visited).toLocaleString();
    row.innerHTML = `<div class="openItem"><div class="bookmarkTitle">${escapeHtml(item.title)}</div><div class="bookmarkUrl">${escapeHtml(item.url)}</div><div class="visited">${escapeHtml(when)}</div></div>`;
    row.querySelector('.openItem').addEventListener('click', () => loadTarget(item.url)); historyList.appendChild(row);
  }
}

function getDownloads() { try { return JSON.parse(localStorage.getItem('kayockDownloads') || '[]'); } catch { return []; } }
function saveDownloads(items) { localStorage.setItem('kayockDownloads', JSON.stringify(items.slice(0, 150))); renderDownloads(); updateJournal(); }
function upsertDownload(update) {
  const items = getDownloads(); const idx = items.findIndex(x => x.id === update.id);
  const merged = idx >= 0 ? { ...items[idx], ...update } : update;
  if (idx >= 0) items[idx] = merged; else items.unshift(merged);
  saveDownloads(items);
  document.body.classList.toggle('downloading', items.some(x => ['progressing','started'].includes(x.state)));
  if (['started'].includes(merged.state)) showHunterToast(`Acquiring ${merged.filename || 'file'}...`, 'Trophy Room');
  if (['completed'].includes(merged.state)) showHunterToast(`${merged.filename || 'File'} acquired.`, 'Trophy Room');
  if (['interrupted','cancelled'].includes(merged.state)) { showHunterToast(`${merged.filename || 'Download'} ${merged.state}.`, 'Trophy Room'); showDownloadsPanel(); }
}
function downloadPercent(item) {
  if (!item.totalBytes) return 0;
  return Math.max(0, Math.min(100, Math.round(((item.receivedBytes || 0) / item.totalBytes) * 100)));
}
function downloadEta(item) {
  const speed = item.speedBytesPerSec || 0;
  const remaining = Math.max(0, (item.totalBytes || 0) - (item.receivedBytes || 0));
  if (!speed || !remaining) return '';
  const seconds = Math.ceil(remaining / speed);
  if (seconds < 60) return `${seconds}s left`;
  if (seconds < 3600) return `${Math.ceil(seconds / 60)}m left`;
  return `${Math.ceil(seconds / 3600)}h left`;
}
function stateLabel(state) {
  if (state === 'completed') return 'Captured';
  if (state === 'progressing') return 'Downloading';
  if (state === 'interrupted') return 'Interrupted';
  if (state === 'cancelled') return 'Cancelled';
  return state || 'Starting';
}
function renderDownloads() {
  const items = getDownloads(); downloadsList.innerHTML = '';
  if (!items.length) { downloadsList.innerHTML = '<div class="note">No trophies captured yet. Download a file and Kayock will track progress, speed, ETA, retry, pause, and resume.</div>'; return; }
  for (const item of items) {
    const row = document.createElement('div'); row.className = 'downloadItem';
    const percent = downloadPercent(item);
    const total = item.totalBytes ? ` / ${formatBytes(item.totalBytes)}` : '';
    const speed = item.speedBytesPerSec ? `${formatBytes(item.speedBytesPerSec)}/s` : '';
    const eta = downloadEta(item);
    const meta = [stateLabel(item.state), `${formatBytes(item.receivedBytes || 0)}${total}`, speed, eta].filter(Boolean).join(' · ');
    const active = ['progressing','started'].includes(item.state);
    const paused = item.state === 'interrupted' || item.paused;
    row.innerHTML = `
      <div class="downloadTop">
        <div class="openItem">
          <div class="bookmarkTitle">${escapeHtml(item.filename || 'Download')}</div>
          <div class="bookmarkUrl">${escapeHtml(meta)}</div>
          <div class="visited">${escapeHtml(item.path || item.url || '')}</div>
        </div>
      </div>
      <div class="progressBar"><span style="width:${percent}%"></span></div>
      <div class="downloadActions">
        <button data-action="open">Open</button>
        <button data-action="folder">Folder</button>
        ${active && !item.paused ? '<button data-action="pause">Pause</button>' : ''}
        ${active && item.paused ? '<button data-action="resume">Resume</button>' : ''}
        ${active ? '<button data-action="cancel">Cancel</button>' : ''}
        ${['interrupted','cancelled'].includes(item.state) ? '<button data-action="retry">Retry</button>' : ''}
        <button data-action="copy">Copy URL</button>
      </div>`;
    row.querySelector('[data-action="open"]')?.addEventListener('click', () => item.path && window.kayockAPI?.openPath(item.path));
    row.querySelector('[data-action="folder"]')?.addEventListener('click', () => item.path && window.kayockAPI?.showItemInFolder(item.path));
    row.querySelector('[data-action="pause"]')?.addEventListener('click', () => window.kayockAPI?.downloadAction({ id: item.id, action: 'pause' }));
    row.querySelector('[data-action="resume"]')?.addEventListener('click', () => window.kayockAPI?.downloadAction({ id: item.id, action: 'resume' }));
    row.querySelector('[data-action="cancel"]')?.addEventListener('click', () => window.kayockAPI?.downloadAction({ id: item.id, action: 'cancel' }));
    row.querySelector('[data-action="retry"]')?.addEventListener('click', () => item.url && window.kayockAPI?.downloadAction({ action: 'retry', url: item.url }));
    row.querySelector('[data-action="copy"]')?.addEventListener('click', () => navigator.clipboard?.writeText(item.url || item.path || ''));
    downloadsList.appendChild(row);
  }
}
function formatBytes(bytes) { if (!bytes) return '0 B'; const units = ['B','KB','MB','GB','TB']; let n = bytes, i = 0; while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; } return `${n.toFixed(i ? 1 : 0)} ${units[i]}`; }


function getSecurityEvents() { try { return JSON.parse(localStorage.getItem('kayockSecurityEvents') || '[]'); } catch { return []; } }
function saveSecurityEvents(items) { localStorage.setItem('kayockSecurityEvents', JSON.stringify(items.slice(0, 40))); renderSecurityEvents(); }
function addSecurityEvent(event) {
  const items = getSecurityEvents();
  items.unshift({ ...event, at: event.at || new Date().toISOString() });
  saveSecurityEvents(items);
}
function renderSecurityEvents() {
  if (!securityEvents) return;
  const items = getSecurityEvents();
  if (!items.length) { securityEvents.innerHTML = '<div class="note">No blocked permission requests yet.</div>'; return; }
  securityEvents.innerHTML = '';
  for (const item of items.slice(0, 8)) {
    const row = document.createElement('div'); row.className = 'trustedItem';
    const when = new Date(item.at).toLocaleTimeString();
    row.innerHTML = `<span>${escapeHtml(item.permission || item.type)}<br><small>${escapeHtml(when)} · ${escapeHtml(item.origin || '')}</small></span>`;
    securityEvents.appendChild(row);
  }
}



function showHunterToast(message, title = 'Hunter') {
  if (!hunterToast) return;
  hunterToast.innerHTML = `<strong>${escapeHtml(title)}</strong><br>${escapeHtml(message || '')}`;
  hunterToast.classList.remove('hidden');
  clearTimeout(showHunterToast.timer);
  showHunterToast.timer = setTimeout(() => hunterToast.classList.add('hidden'), 5000);
}

function getDiagnostics() { try { return JSON.parse(localStorage.getItem('kayockDiagnostics') || '[]'); } catch { return []; } }
function saveDiagnostics(items) { localStorage.setItem('kayockDiagnostics', JSON.stringify(items.slice(0, 80))); renderDiagnostics(); updateJournal(); }
function addDiagnostic(event) {
  const items = getDiagnostics();
  items.unshift({ ...event, at: event.at || new Date().toISOString() });
  saveDiagnostics(items);
}
function renderDiagnostics() {
  if (!diagnosticsList) return;
  const items = getDiagnostics();
  if (!items.length) { diagnosticsList.innerHTML = '<div class="note">No diagnostic events yet. That is good.</div>'; return; }
  diagnosticsList.innerHTML = '';
  for (const item of items.slice(0, 20)) {
    const row = document.createElement('div'); row.className = 'trustedItem';
    const when = new Date(item.at).toLocaleTimeString();
    row.innerHTML = `<span>${escapeHtml(item.type || 'event')}<br><small>${escapeHtml(when)} · ${escapeHtml(item.message || item.url || '')}</small></span>`;
    diagnosticsList.appendChild(row);
  }
}
function showDiagnosticsPanel() { renderDiagnostics(); showOnlyPanel(diagnosticsPanel); }
function showWorkshopPanel() { showOnlyPanel(workshopPanel); }

function renderShieldPanel() {
  const tab = activeTab(); const url = tab?.url || 'kayock://home'; const host = getHost(url); const s = getShield(); const allowed = shouldAllowJavascript(url);
  if (shieldMode) shieldMode.value = s.mode || 'balanced';
  if (shieldDomain) shieldDomain.textContent = host || 'Kayock internal page';
  if (javascriptStatus) javascriptStatus.textContent = allowed ? 'Allowed' : 'Blocked';
  if (shieldAdvice) shieldAdvice.textContent = isInternal(url) ? 'Kayock page safe' : (allowed ? 'Fed / scripts allowed' : 'Starved / scripts blocked');
  renderSecurityEvents();
  if (trustedList) {
    const trusted = s.trustedSites || [];
    trustedList.innerHTML = trusted.length ? trusted.map(h => `<div class="trustedItem"><span>${escapeHtml(h)}</span><button data-host="${escapeHtml(h)}">Remove</button></div>`).join('') : '<div class="note">No trusted sites yet.</div>';
    trustedList.querySelectorAll('button').forEach(btn => btn.addEventListener('click', () => { const sh = getShield(); sh.trustedSites = (sh.trustedSites || []).filter(x => x !== btn.dataset.host); saveShield(sh); reloadCurrentWithShield(); }));
  }
}
function showShieldPanel() { renderShieldPanel(); showOnlyPanel(shieldPanel); updateShieldIndicator(); }
function trustCurrentSite() {
  const tab = activeTab(); if (!tab || isInternal(tab.url)) return; const host = getHost(tab.url); const s = getShield();
  s.trustedSites = [...new Set([...(s.trustedSites || []), host])]; s.blockedSites = (s.blockedSites || []).filter(h => h !== host); allowOnceSites.delete(host); saveShield(s); reloadCurrentWithShield();
}
function blockCurrentSite() {
  const tab = activeTab(); if (!tab || isInternal(tab.url)) return; const host = getHost(tab.url); const s = getShield();
  s.blockedSites = [...new Set([...(s.blockedSites || []), host])]; s.trustedSites = (s.trustedSites || []).filter(h => h !== host); allowOnceSites.delete(host); saveShield(s); reloadCurrentWithShield();
}
function allowOnceCurrentSite() {
  const tab = activeTab(); if (!tab || isInternal(tab.url)) return; const host = getHost(tab.url); const s = getShield();
  allowOnceSites.add(host);
  window.kayockAPI?.addAllowOnceMain?.(host);
  s.blockedSites = (s.blockedSites || []).filter(h => h !== host);
  saveShield(s);
  addDiagnostic({ type: 'allow-once-added', message: `Temporary trust added for this session: ${host}` });
  reloadCurrentWithShield();
}
function clearAllowOnceSession(reason = 'shutdown') {
  const count = allowOnceSites.size;
  allowOnceSites.clear();
  window.kayockAPI?.clearAllowOnceMain?.(reason);
  addDiagnostic({ type: 'temporary-trust-cleared', message: `Cleared ${count} Allow Once site(s) during ${reason}.` });
  updateShieldIndicator();
}

function showBookmarksPanel() { renderBookmarks(); showOnlyPanel(bookmarksPanel); }
function showHistoryPanel() { renderTracks(); renderHistory(); showOnlyPanel(historyPanel); }
function showDownloadsPanel() { renderDownloads(); showOnlyPanel(downloadsPanel); }
function showSettingsPanel() { loadSettingsUI(); showOnlyPanel(settingsPanel); }
function showAboutPanel() { updateJournal(); showOnlyPanel(aboutPanel); }

function loadSettingsUI() {
  const s = getSettings(); document.getElementById('searchEngine').value = s.searchEngine;
  document.getElementById('restoreSession').checked = !!s.restoreSession; document.getElementById('openHomeNewTab').checked = !!s.openHomeNewTab;
  const dz = document.getElementById('defaultZoom'); if (dz) dz.value = String(s.defaultZoom || 1);
  const uiSize = document.getElementById('uiSize'); if (uiSize) uiSize.value = s.uiSize || 'large';
  const uiFont = document.getElementById('uiFont'); if (uiFont) uiFont.value = s.uiFont || 'legible';
  const spellcheckUS = document.getElementById('spellcheckUS'); if (spellcheckUS) spellcheckUS.checked = s.spellcheckUS !== false;
  const largeMenus = document.getElementById('largeMenus'); if (largeMenus) largeMenus.checked = !!s.largeMenus;
  const reduceMotion = document.getElementById('reduceMotion'); if (reduceMotion) reduceMotion.checked = !!s.reduceMotion;
  const folder = document.getElementById('downloadFolder'); if (folder) folder.textContent = s.downloadFolder || 'Default Windows Downloads folder';
  document.getElementById('settingsSaved').classList.add('hidden');
}

function updateSettingsFromControls({ quiet = false } = {}) {
  const current = getSettings();
  const dz = document.getElementById('defaultZoom');
  const settings = {
    ...current,
    searchEngine: document.getElementById('searchEngine')?.value || current.searchEngine,
    restoreSession: !!document.getElementById('restoreSession')?.checked,
    openHomeNewTab: !!document.getElementById('openHomeNewTab')?.checked,
    defaultZoom: Number(dz?.value || 1),
    uiSize: document.getElementById('uiSize')?.value || 'large',
    uiFont: document.getElementById('uiFont')?.value || 'legible',
    spellcheckUS: !!document.getElementById('spellcheckUS')?.checked,
    largeMenus: !!document.getElementById('largeMenus')?.checked,
    reduceMotion: !!document.getElementById('reduceMotion')?.checked
  };
  saveSettingsObject(settings);
  window.kayockAPI?.setDownloadFolder(settings.downloadFolder || '');
  if (!quiet) showSettingsMessage('Settings saved.');
  return settings;
}

function saveSettingsFromUI() {
  updateSettingsFromControls({ quiet: false });
}
async function chooseDownloadFolder() {
  const folder = await window.kayockAPI?.chooseDownloadFolder?.();
  if (!folder) return;
  const s = getSettings(); s.downloadFolder = folder; saveSettingsObject(s);
  await window.kayockAPI?.setDownloadFolder(folder);
  loadSettingsUI(); showSettingsMessage('Download folder saved.');
}



function showSettingsMessage(message) {
  const el = document.getElementById('settingsSaved');
  if (!el) return;
  el.textContent = message;
  el.classList.remove('hidden');
}
function exportVault() {
  const keys = ['kayockBookmarks','kayockHistory','kayockDownloads','kayockSettings','kayockShield','kayockSecurityEvents','kayockSession'];
  const vault = { app: 'Kayock Browser', version: '2.5.1-rc.1', exportedAt: new Date().toISOString(), data: {} };
  for (const key of keys) vault.data[key] = localStorage.getItem(key);
  const blob = new Blob([JSON.stringify(vault, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `kayock-vault-${new Date().toISOString().slice(0,10)}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  showSettingsMessage('Vault exported. Keep that file safe.');
}
function importVaultFile(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const vault = JSON.parse(reader.result);
      if (!vault || !vault.data) throw new Error('Not a Kayock Vault file');
      for (const [key, value] of Object.entries(vault.data)) {
        if (key.startsWith('kayock') && typeof value === 'string') localStorage.setItem(key, value);
      }
      renderBookmarks(); renderHistory(); renderTracks(); renderDownloads(); renderShieldPanel(); renderDiagnostics(); updateCampfire();
      showSettingsMessage('Vault imported. Restart Kayock to restore saved tabs.');
    } catch (err) {
      showSettingsMessage('Import failed: not a valid Kayock Vault file.');
    }
  };
  reader.readAsText(file);
}
function privacyReset() {
  const ok = confirm('Privacy Reset clears Marks, Tracks, Trophies, sessions, Shield trust decisions, and events on this copy of Kayock. Continue?');
  if (!ok) return;
  ['kayockBookmarks','kayockHistory','kayockDownloads','kayockSettings','kayockShield','kayockSecurityEvents','kayockSession'].forEach(key => localStorage.removeItem(key));
  renderBookmarks(); renderHistory(); renderTracks(); renderDownloads(); renderShieldPanel(); renderDiagnostics(); updateCampfire();
  showSettingsMessage('Privacy Reset complete. Restart Kayock for a clean session.');
}


navForm.addEventListener('submit', (event) => { event.preventDefault(); loadTarget(address.value); });
homeSearch.addEventListener('submit', (event) => { event.preventDefault(); loadTarget(homeQuery.value); });
document.getElementById('newTab').addEventListener('click', () => createTab());
document.getElementById('newTabTop')?.addEventListener('click', () => createTab());
document.getElementById('homeBtn').addEventListener('click', () => loadTarget('kayock://home'));
shieldBtn.addEventListener('click', showShieldPanel);
document.getElementById('bookmarksBtn').addEventListener('click', showBookmarksPanel);
document.getElementById('historyBtn').addEventListener('click', showHistoryPanel);
document.getElementById('downloadsBtn').addEventListener('click', showDownloadsPanel);
document.getElementById('accessibilityBtn')?.addEventListener('click', openAccessibilitySettings);
document.getElementById('settingsBtn').addEventListener('click', showSettingsPanel);
document.getElementById('diagnosticsBtn')?.addEventListener('click', showDiagnosticsPanel);
document.getElementById('workshopBtn')?.addEventListener('click', showWorkshopPanel);
document.getElementById('aboutBtn').addEventListener('click', showAboutPanel);
document.getElementById('bookmarkBtn').addEventListener('click', addCurrentBookmark);
document.getElementById('clearHistory').addEventListener('click', () => saveHistory([]));
document.getElementById('clearDownloads').addEventListener('click', () => saveDownloads([]));
document.getElementById('startDirectDownload')?.addEventListener('click', () => startDirectDownload(document.getElementById('directDownloadUrl')?.value || ''));
document.getElementById('createTrackBtn')?.addEventListener('click', () => createTrack(document.getElementById('newTrackName')?.value || ''));
document.getElementById('newTrackName')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') createTrack(e.target.value); });
document.getElementById('hunterCollapse')?.addEventListener('click', () => {
  const pinned = document.body.classList.toggle('hunterPinned');
  localStorage.setItem('kayockHunterPinned', String(pinned));
  showHunterToast(pinned ? 'Hunter Panel pinned open' : 'Hunter Panel set to icon rail', 'Sidebar');
});
document.getElementById('brandToggle')?.addEventListener('click', () => document.body.classList.toggle('brandCollapsed'));
document.getElementById('directDownloadUrl')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') startDirectDownload(e.target.value); });
document.getElementById('saveSettings').addEventListener('click', saveSettingsFromUI);
['uiSize','uiFont','spellcheckUS','largeMenus','reduceMotion','defaultZoom'].forEach(id => {
  const el = document.getElementById(id);
  if (el) el.addEventListener('change', () => updateSettingsFromControls({ quiet: true }));
});
document.getElementById('chooseDownloadFolder')?.addEventListener('click', chooseDownloadFolder);
document.getElementById('exportVault')?.addEventListener('click', exportVault);
document.getElementById('importVault')?.addEventListener('click', () => document.getElementById('vaultImportFile')?.click());
document.getElementById('vaultImportFile')?.addEventListener('change', (e) => importVaultFile(e.target.files?.[0]));
document.getElementById('privacyReset')?.addEventListener('click', privacyReset);
zoomOutBtn?.addEventListener('click', () => stepZoom(-1));
zoomInBtn?.addEventListener('click', () => stepZoom(1));
zoomDisplay?.addEventListener('click', () => resetZoomForCurrent());
document.getElementById('clearDiagnostics')?.addEventListener('click', () => saveDiagnostics([]));
document.getElementById('openCurrentExternal')?.addEventListener('click', () => { const t = activeTab(); if (t?.url && !isInternal(t.url)) window.kayockAPI?.openExternal?.(t.url); });
trustSiteBtn.addEventListener('click', trustCurrentSite);
blockSiteBtn.addEventListener('click', blockCurrentSite);
allowOnceBtn.addEventListener('click', allowOnceCurrentSite);
if (bannerTrust) bannerTrust.addEventListener('click', trustCurrentSite);
if (bannerOnce) bannerOnce.addEventListener('click', allowOnceCurrentSite);
if (bannerOpenShield) bannerOpenShield.addEventListener('click', showShieldPanel);
shieldMode.addEventListener('change', () => { const s = getShield(); s.mode = shieldMode.value; saveShield(s); reloadCurrentWithShield(); });


// v1.0 Daily Driver Alpha panel behavior: visible X buttons, ESC to close, and click outside to dismiss.
enhancePanels();
document.addEventListener('mousedown', (event) => {
  const openPanel = panels().find(p => !p.classList.contains('hidden'));
  if (!openPanel) return;
  const clickedPanel = event.target.closest('.sidePanel');
  const clickedPanelButton = event.target.closest('#bookmarksBtn,#historyBtn,#downloadsBtn,#accessibilityBtn,#settingsBtn,#diagnosticsBtn,#aboutBtn,#shieldBtn,#workshopBtn,#bannerOpenShield,.hunterPanel');
  if (!clickedPanel && !clickedPanelButton) hidePanels();
});

document.querySelectorAll('.quickLinks button').forEach(btn => btn.addEventListener('click', () => loadTarget(btn.dataset.url)));
document.getElementById('back').addEventListener('click', () => { const t = activeTab(); if (t?.webview?.canGoBack()) t.webview.goBack(); });
document.getElementById('forward').addEventListener('click', () => { const t = activeTab(); if (t?.webview?.canGoForward()) t.webview.goForward(); });
document.getElementById('reload').addEventListener('click', () => { const t = activeTab(); if (t?.url && !isInternal(t.url)) reloadCurrentWithShield(); });

// Eagle Eye: attempt Ctrl + mouse wheel zoom when the wheel event reaches the shell.
document.addEventListener('wheel', (event) => {
  if (!event.ctrlKey) return;
  event.preventDefault();
  stepZoom(event.deltaY < 0 ? 1 : -1);
}, { passive: false });

document.addEventListener('keydown', (event) => {
  if (event.key === 'F11') { event.preventDefault(); window.kayockAPI?.toggleFullscreen?.(); return; }
  if (event.key === 'Escape') { document.body.classList.remove('webviewFullscreen'); window.kayockAPI?.setFullscreen?.(false); hidePanels(); return; }
  if (!event.ctrlKey) return; const key = event.key.toLowerCase();
  if (key === 't') { event.preventDefault(); createTab(); }
  if (key === 'w') { event.preventDefault(); closeTab(activeTabId); }
  if (key === 'l') { event.preventDefault(); address.focus(); address.select(); }
  if (key === 'h' && event.shiftKey) { event.preventDefault(); showDiagnosticsPanel(); return; }
  if (key === 'h') { event.preventDefault(); showHistoryPanel(); }
  if (key === 'j') { event.preventDefault(); showDownloadsPanel(); }
  if (key === 'd') { event.preventDefault(); addCurrentBookmark(); }
  if (key === ',') { event.preventDefault(); showSettingsPanel(); }
  if (key === 'u') { event.preventDefault(); showShieldPanel(); }
  if (key === '=' || key === '+') { event.preventDefault(); stepZoom(1); }
  if (key === '-' || key === '_') { event.preventDefault(); stepZoom(-1); }
  if (key === '0') { event.preventDefault(); resetZoomForCurrent(); }
});

window.kayockAPI?.onFullscreenChanged?.((value) => document.body.classList.toggle('webviewFullscreen', !!value));
window.kayockAPI?.onOpenUrlInTab?.((payload) => { if (payload?.url) createTab(payload.url, payload.active !== false); });
window.addEventListener('beforeunload', () => clearAllowOnceSession('window shutdown'));
window.kayockAPI?.onClearTemporaryTrust?.(() => clearAllowOnceSession('app shutdown'));

window.kayockAPI?.onZoomShortcut?.((payload) => {
  const key = String(payload?.key || '').toLowerCase();
  if (key === '0') resetZoomForCurrent();
  else if (key === '-' || key === '_') stepZoom(-1);
  else stepZoom(1);
});

window.kayockAPI?.setDownloadFolder(getSettings().downloadFolder || '');
window.kayockAPI?.onDownloadUpdate((payload) => upsertDownload(payload));
window.kayockAPI?.onSecurityEvent((payload) => addSecurityEvent(payload));
window.kayockAPI?.onDiagnosticEvent?.((payload) => {
  addDiagnostic(payload);
  if (['duplicate-warning','download-started','download-error','media-hunter','media-hunter-error','toast'].includes(payload?.type)) {
    showHunterToast(payload.message || payload.type, payload.title || 'Media Hunter');
  }
});
function scheduleKayockIdle(fn, timeout = 700) {
  if (typeof window.requestIdleCallback === 'function') window.requestIdleCallback(fn, { timeout });
  else setTimeout(fn, 0);
}
function hydrateKayockPanelsAfterStart() {
  // 2.5.1 performance pass: show the browser first, then warm up panels quietly.
  scheduleKayockIdle(() => { renderTracks(); updateCampfire(); }, 120);
  scheduleKayockIdle(() => renderBookmarks(), 250);
  scheduleKayockIdle(() => renderHistory(), 350);
  scheduleKayockIdle(() => renderDownloads(), 450);
  scheduleKayockIdle(() => renderShieldPanel(), 550);
  scheduleKayockIdle(() => renderDiagnostics(), 650);
}

applyAppearanceSettings();
updateCampfire();
if (!restoreSession()) createTab();
applyZoomToTab();
hydrateKayockPanelsAfterStart();
