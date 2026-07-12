from pathlib import Path
import shutil
import datetime
import json

ROOT = Path(__file__).resolve().parents[2]
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "Backups" / f"feature002_before_bridge_app_{STAMP}"

PACKAGE_JSON = '{\n  "name": "kayocktheos-bridge",\n  "version": "0.1.0",\n  "description": "KayocktheOS Bridge application",\n  "main": "main.js",\n  "scripts": {\n    "start": "electron .",\n    "dev": "electron ."\n  },\n  "author": "KayocktheOS",\n  "license": "UNLICENSED",\n  "devDependencies": {\n    "electron": "^31.0.0"\n  }\n}'
MAIN_JS = "const { app, BrowserWindow, shell } = require('electron');\nconst path = require('path');\n\nfunction createWindow() {\n  const win = new BrowserWindow({\n    width: 1280,\n    height: 840,\n    minWidth: 1000,\n    minHeight: 700,\n    title: 'KayocktheOS Bridge',\n    backgroundColor: '#071007',\n    webPreferences: {\n      preload: path.join(__dirname, 'preload.js'),\n      contextIsolation: true,\n      nodeIntegration: false,\n      sandbox: false\n    }\n  });\n\n  win.loadFile(path.join(__dirname, 'index.html'));\n\n  win.webContents.setWindowOpenHandler(({ url }) => {\n    shell.openExternal(url);\n    return { action: 'deny' };\n  });\n}\n\napp.whenReady().then(() => {\n  createWindow();\n  app.on('activate', () => {\n    if (BrowserWindow.getAllWindows().length === 0) createWindow();\n  });\n});\n\napp.on('window-all-closed', () => {\n  if (process.platform !== 'darwin') app.quit();\n});\n"
PRELOAD_JS = "const { contextBridge } = require('electron');\n\ncontextBridge.exposeInMainWorld('kayockBridge', {\n  apiBase: 'http://127.0.0.1:8844'\n});\n"
INDEX_HTML = '<!doctype html>\n<html lang="en">\n<head>\n  <meta charset="utf-8" />\n  <meta\n    http-equiv="Content-Security-Policy"\n    content="default-src \'self\'; connect-src \'self\' http://127.0.0.1:8844; img-src \'self\' data: file:; style-src \'self\' \'unsafe-inline\'; script-src \'self\';"\n  />\n  <meta name="viewport" content="width=device-width, initial-scale=1" />\n  <title>KayocktheOS Bridge</title>\n  <link rel="stylesheet" href="style.css" />\n</head>\n<body>\n  <div class="app">\n    <aside class="sidebar">\n      <div class="brand">\n        <div class="sigil">K</div>\n        <div>\n          <h1>KayocktheOS</h1>\n          <p>Living Knowledge Workshop</p>\n        </div>\n      </div>\n\n      <nav>\n        <button class="nav active" data-room="home">🏠 Home</button>\n        <button class="nav" data-room="academy">🎓 Academy</button>\n        <button class="nav" data-room="workshop">🔧 Workshop</button>\n        <button class="nav" data-room="library">📚 Library</button>\n        <button class="nav" data-room="observatory">🔍 Observatory</button>\n        <button class="nav" data-room="foundry">🏛 Foundry</button>\n      </nav>\n\n      <div class="sidebarStatus">\n        <div><span id="apiDot" class="dot wait"></span> Core API</div>\n        <div><span id="runtimeDot" class="dot wait"></span> Runtime</div>\n        <div><span id="foxaiDot" class="dot wait"></span> FOXAI</div>\n      </div>\n    </aside>\n\n    <main class="main">\n      <header class="topbar">\n        <div>\n          <p class="eyebrow">Bridge OS</p>\n          <h2 id="roomTitle">Home</h2>\n        </div>\n        <div class="operator">\n          <span id="operatorName">Operator</span>\n          <small id="versionLabel">Loading...</small>\n        </div>\n      </header>\n\n      <section id="home" class="room active">\n        <div class="hero">\n          <div>\n            <p class="eyebrow">Welcome back</p>\n            <h3 id="heroGreeting">Opening the Workshop...</h3>\n            <p id="academyGreeting">The Academy is open. Today\'s lesson awaits.</p>\n          </div>\n          <div id="overallStatus" class="statusPill wait">Checking</div>\n        </div>\n\n        <div class="grid three">\n          <article class="card">\n            <h4>System Health</h4>\n            <div id="healthList" class="list smallList"></div>\n          </article>\n          <article class="card">\n            <h4>FOXAI</h4>\n            <div id="foxaiSummary" class="bigNumbers"></div>\n          </article>\n          <article class="card">\n            <h4>Local Chat</h4>\n            <div id="chatSummary" class="smallList"></div>\n          </article>\n        </div>\n\n        <article class="card chatCard">\n          <h4>Ask the Academy</h4>\n          <div id="chatLog" class="chatLog">\n            <div class="message system">Local chat is ready when the model runtime is online.</div>\n          </div>\n          <form id="chatForm" class="chatForm">\n            <input id="chatInput" placeholder="Ask the Academy..." />\n            <button type="submit">Ask</button>\n          </form>\n        </article>\n      </section>\n\n      <section id="academy" class="room">\n        <div class="grid two">\n          <article class="card wide">\n            <h4>Hall of Professors</h4>\n            <div id="professorGrid" class="professorGrid"></div>\n          </article>\n        </div>\n      </section>\n\n      <section id="workshop" class="room">\n        <div class="grid two">\n          <article class="card">\n            <h4>Capabilities</h4>\n            <div id="capabilityList" class="list"></div>\n          </article>\n          <article class="card">\n            <h4>Creative Studio</h4>\n            <p>Image generation and ComfyUI integration will appear here as FOXAI capabilities come online.</p>\n          </article>\n        </div>\n      </section>\n\n      <section id="library" class="room">\n        <article class="card">\n          <h4>Iron Library</h4>\n          <p>Books, manuals, comics, notes, and documents will be indexed here.</p>\n          <div id="librarySummary" class="smallList"></div>\n        </article>\n      </section>\n\n      <section id="observatory" class="room">\n        <div class="grid two">\n          <article class="card">\n            <h4>Host Computer</h4>\n            <div id="systemSummary" class="smallList"></div>\n          </article>\n          <article class="card">\n            <h4>Events</h4>\n            <div id="eventList" class="smallList"></div>\n          </article>\n        </div>\n      </section>\n\n      <section id="foundry" class="room">\n        <div class="grid two">\n          <article class="card">\n            <h4>Release Readiness</h4>\n            <div id="releaseSummary" class="smallList"></div>\n          </article>\n          <article class="card">\n            <h4>Workshop Wall</h4>\n            <div id="workshopWall" class="smallList"></div>\n          </article>\n        </div>\n      </section>\n    </main>\n  </div>\n\n  <script src="renderer.js"></script>\n</body>\n</html>\n'
STYLE_CSS = ':root {\n  color-scheme: dark;\n  --bg: #050805;\n  --panel: #0d1a0d;\n  --panel2: #122412;\n  --text: #ddffdf;\n  --muted: #95d795;\n  --accent: #00ff66;\n  --warn: #ffd166;\n  --bad: #ff5c5c;\n  --border: rgba(0,255,102,.22);\n}\n\n* { box-sizing: border-box; }\n\nbody {\n  margin: 0;\n  background: radial-gradient(circle at top, #123312, var(--bg) 55%);\n  color: var(--text);\n  font-family: "Segoe UI", Arial, sans-serif;\n}\n\n.app {\n  display: grid;\n  grid-template-columns: 280px 1fr;\n  height: 100vh;\n}\n\n.sidebar {\n  border-right: 1px solid var(--border);\n  background: rgba(5,12,5,.88);\n  padding: 22px;\n  display: flex;\n  flex-direction: column;\n  gap: 22px;\n}\n\n.brand {\n  display: flex;\n  gap: 14px;\n  align-items: center;\n}\n\n.sigil {\n  width: 48px;\n  height: 48px;\n  border: 1px solid var(--accent);\n  border-radius: 14px;\n  display: grid;\n  place-items: center;\n  color: var(--accent);\n  font-weight: 900;\n  font-size: 24px;\n  box-shadow: 0 0 24px rgba(0,255,102,.12);\n}\n\n.brand h1 { margin: 0; font-size: 20px; }\n.brand p { margin: 3px 0 0; color: var(--muted); font-size: 12px; }\n\nnav { display: grid; gap: 8px; }\n\n.nav {\n  background: transparent;\n  color: var(--text);\n  border: 1px solid rgba(149,215,149,.14);\n  border-radius: 12px;\n  padding: 12px;\n  text-align: left;\n  cursor: pointer;\n  font-size: 15px;\n}\n\n.nav:hover, .nav.active {\n  border-color: var(--accent);\n  background: rgba(0,255,102,.08);\n}\n\n.sidebarStatus {\n  margin-top: auto;\n  display: grid;\n  gap: 10px;\n  color: var(--muted);\n  font-size: 14px;\n}\n\n.dot {\n  display: inline-block;\n  width: 10px;\n  height: 10px;\n  border-radius: 99px;\n  margin-right: 8px;\n}\n.dot.ok { background: var(--accent); box-shadow: 0 0 8px var(--accent); }\n.dot.wait { background: var(--warn); box-shadow: 0 0 8px var(--warn); }\n.dot.bad { background: var(--bad); box-shadow: 0 0 8px var(--bad); }\n\n.main {\n  padding: 24px;\n  overflow: auto;\n}\n\n.topbar {\n  display: flex;\n  justify-content: space-between;\n  align-items: center;\n  margin-bottom: 22px;\n}\n\n.eyebrow {\n  text-transform: uppercase;\n  letter-spacing: .14em;\n  color: var(--muted);\n  font-size: 12px;\n  margin: 0 0 4px;\n}\n\n.topbar h2 {\n  margin: 0;\n  font-size: 36px;\n}\n\n.operator {\n  text-align: right;\n  color: var(--accent);\n}\n.operator small {\n  display: block;\n  color: var(--muted);\n}\n\n.room { display: none; }\n.room.active { display: block; }\n\n.hero {\n  border: 1px solid var(--border);\n  border-radius: 24px;\n  padding: 28px;\n  background: linear-gradient(135deg, rgba(18,36,18,.95), rgba(5,10,5,.92));\n  display: flex;\n  justify-content: space-between;\n  align-items: center;\n  margin-bottom: 18px;\n}\n\n.hero h3 {\n  font-size: 42px;\n  margin: 8px 0;\n}\n\n.statusPill {\n  border: 1px solid var(--warn);\n  color: var(--warn);\n  border-radius: 999px;\n  padding: 12px 18px;\n  font-weight: 900;\n}\n.statusPill.ok { color: var(--accent); border-color: var(--accent); }\n.statusPill.bad { color: var(--bad); border-color: var(--bad); }\n\n.grid {\n  display: grid;\n  gap: 18px;\n}\n.grid.two { grid-template-columns: repeat(2, minmax(280px, 1fr)); }\n.grid.three { grid-template-columns: repeat(3, minmax(220px, 1fr)); }\n\n.card {\n  background: rgba(13,26,13,.86);\n  border: 1px solid rgba(149,215,149,.16);\n  border-radius: 18px;\n  padding: 20px;\n}\n\n.card h4 {\n  margin: 0 0 14px;\n  color: var(--accent);\n  font-size: 20px;\n}\n\n.wide { grid-column: 1 / -1; }\n\n.list, .smallList {\n  display: grid;\n  gap: 8px;\n}\n\n.item {\n  padding: 9px 10px;\n  border-radius: 10px;\n  background: rgba(0,0,0,.22);\n  border-left: 4px solid var(--warn);\n}\n\n.item.ok { border-left-color: var(--accent); }\n.item.bad { border-left-color: var(--bad); }\n\n.item strong { display: block; }\n.item span { color: var(--muted); font-size: 13px; }\n\n.bigNumbers {\n  display: grid;\n  gap: 10px;\n}\n.num {\n  display: flex;\n  justify-content: space-between;\n  padding: 9px 0;\n  border-bottom: 1px solid rgba(149,215,149,.1);\n}\n.num strong { color: var(--accent); }\n\n.professorGrid {\n  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));\n  gap: 14px;\n}\n.professor {\n  background: rgba(0,0,0,.18);\n  border: 1px solid rgba(149,215,149,.14);\n  border-radius: 14px;\n  padding: 16px;\n}\n.professor h5 { margin: 0 0 8px; font-size: 17px; color: var(--accent); }\n.professor p { color: var(--muted); }\n\n.chatCard { margin-top: 18px; }\n\n.chatLog {\n  height: 230px;\n  overflow: auto;\n  display: grid;\n  gap: 10px;\n  align-content: start;\n  padding: 12px;\n  background: rgba(0,0,0,.22);\n  border-radius: 14px;\n  margin-bottom: 12px;\n}\n\n.message {\n  padding: 10px 12px;\n  border-radius: 12px;\n  background: rgba(255,255,255,.06);\n}\n.message.user { border-left: 4px solid var(--warn); }\n.message.assistant { border-left: 4px solid var(--accent); }\n.message.system { border-left: 4px solid var(--muted); color: var(--muted); }\n\n.chatForm {\n  display: grid;\n  grid-template-columns: 1fr 110px;\n  gap: 10px;\n}\n\n.chatForm input {\n  background: rgba(0,0,0,.35);\n  color: var(--text);\n  border: 1px solid rgba(149,215,149,.2);\n  border-radius: 12px;\n  padding: 13px;\n}\n\n.chatForm button {\n  background: rgba(0,255,102,.14);\n  color: var(--accent);\n  border: 1px solid var(--accent);\n  border-radius: 12px;\n  cursor: pointer;\n  font-weight: 800;\n}\n\n@media (max-width: 980px) {\n  .app { grid-template-columns: 1fr; }\n  .sidebar { position: relative; }\n  .grid.two, .grid.three { grid-template-columns: 1fr; }\n}\n'
RENDERER_JS = 'const API = window.kayockBridge?.apiBase || \'http://127.0.0.1:8844\';\n\nconst state = {\n  status: null,\n  academy: null,\n  foxai: null,\n  runtime: null,\n  localChat: null,\n  release: null,\n  bridge: null\n};\n\nfunction $(id) { return document.getElementById(id); }\n\nfunction setDot(id, status) {\n  const el = $(id);\n  if (!el) return;\n  el.className = \'dot \' + (status ? \'ok\' : \'bad\');\n}\n\nfunction item(label, value, status = \'wait\') {\n  return `<div class="item ${status}"><strong>${escapeHtml(label)}</strong><span>${escapeHtml(value ?? \'\')}</span></div>`;\n}\n\nfunction escapeHtml(value) {\n  return String(value ?? \'\').replace(/[&<>"\']/g, ch => ({\n    \'&\': \'&amp;\', \'<\': \'&lt;\', \'>\': \'&gt;\', \'"\': \'&quot;\', "\'": \'&#39;\'\n  }[ch]));\n}\n\nasync function fetchJson(path) {\n  const res = await fetch(API + path, { cache: \'no-store\' });\n  if (!res.ok) throw new Error(`${path} ${res.status}`);\n  return await res.json();\n}\n\nasync function refresh() {\n  try {\n    const [status, academy, foxai, runtime, localChat, release, bridge] = await Promise.allSettled([\n      fetchJson(\'/api/status\'),\n      fetchJson(\'/api/academy\'),\n      fetchJson(\'/api/foxai\'),\n      fetchJson(\'/api/runtime\'),\n      fetchJson(\'/api/local-chat\'),\n      fetchJson(\'/api/release-check\'),\n      fetchJson(\'/api/bridge\')\n    ]);\n\n    state.status = status.status === \'fulfilled\' ? status.value : null;\n    state.academy = academy.status === \'fulfilled\' ? academy.value : null;\n    state.foxai = foxai.status === \'fulfilled\' ? foxai.value : null;\n    state.runtime = runtime.status === \'fulfilled\' ? runtime.value : null;\n    state.localChat = localChat.status === \'fulfilled\' ? localChat.value : null;\n    state.release = release.status === \'fulfilled\' ? release.value : null;\n    state.bridge = bridge.status === \'fulfilled\' ? bridge.value : null;\n\n    render();\n  } catch (err) {\n    setDot(\'apiDot\', false);\n    $(\'overallStatus\').textContent = \'Core Offline\';\n    $(\'overallStatus\').className = \'statusPill bad\';\n  }\n}\n\nfunction render() {\n  const apiOnline = !!state.status;\n  setDot(\'apiDot\', apiOnline);\n  setDot(\'runtimeDot\', !!state.runtime?.online);\n  setDot(\'foxaiDot\', !!state.foxai?.exists);\n\n  const project = state.status?.project || {};\n  const operator = state.status?.operator || {};\n  $(\'operatorName\').textContent = operator.display_name || \'Operator\';\n  $(\'versionLabel\').textContent = `${project.name || \'KayocktheOS\'} ${project.version || \'\'}`;\n  $(\'heroGreeting\').textContent = `Good day, ${operator.display_name || \'Operator\'}.`;\n  $(\'academyGreeting\').textContent = state.academy?.startup_greeting || \'The Academy is open. Today’s lesson awaits.\';\n\n  const good = apiOnline && state.foxai?.exists;\n  $(\'overallStatus\').textContent = good ? \'Workshop Online\' : \'Needs Attention\';\n  $(\'overallStatus\').className = \'statusPill \' + (good ? \'ok\' : \'wait\');\n\n  renderHealth();\n  renderFoxai();\n  renderChatSummary();\n  renderAcademy();\n  renderCapabilities();\n  renderSystem();\n  renderEvents();\n  renderRelease();\n  renderWorkshopWall();\n  renderLibrary();\n}\n\nfunction renderHealth() {\n  const health = state.status?.health || [];\n  $(\'healthList\').innerHTML = health.slice(0, 8).map(h =>\n    item(h.label, `${h.status} — ${h.path}`, h.status === \'OK\' ? \'ok\' : \'bad\')\n  ).join(\'\') || item(\'Core API\', \'No data yet\', \'bad\');\n}\n\nfunction renderFoxai() {\n  const s = state.foxai?.summary || {};\n  $(\'foxaiSummary\').innerHTML = `\n    <div class="num"><span>Chat Models</span><strong>${s.llm_models ?? \'--\'}</strong></div>\n    <div class="num"><span>Image Models</span><strong>${s.image_models ?? \'--\'}</strong></div>\n    <div class="num"><span>Workflows</span><strong>${s.workflows ?? \'--\'}</strong></div>\n    <div class="num"><span>Total Assets</span><strong>${s.total_assets ?? \'--\'}</strong></div>\n  `;\n}\n\nfunction renderChatSummary() {\n  const rt = state.runtime || {};\n  const lc = state.localChat || {};\n  $(\'chatSummary\').innerHTML = [\n    item(\'Runtime\', rt.online ? \'Online\' : \'Offline\', rt.online ? \'ok\' : \'bad\'),\n    item(\'Selected Model\', lc.selected_model || \'Not selected\', lc.selected_model ? \'ok\' : \'wait\'),\n    item(\'Launch Helper\', lc.launch_helper || \'Missing\', lc.launch_helper ? \'ok\' : \'wait\')\n  ].join(\'\');\n}\n\nfunction renderAcademy() {\n  const colleges = state.academy?.colleges || [];\n  $(\'professorGrid\').innerHTML = colleges.map(c => `\n    <div class="professor">\n      <h5>${escapeHtml(c.professor || c.name)}</h5>\n      <p><strong>${escapeHtml(c.name)}</strong></p>\n      <p>“${escapeHtml(c.motto || \'\')}”</p>\n      <p>${escapeHtml((c.domains || []).join(\' · \'))}</p>\n    </div>\n  `).join(\'\') || \'<p>No Academy data yet.</p>\';\n}\n\nfunction capabilityScore(name) {\n  const llms = state.foxai?.assets?.llms || [];\n  const images = state.foxai?.assets?.image_models || [];\n  if (name === \'conversation\') return llms.length;\n  if (name === \'programming\') return llms.filter(m => (m.capabilities || []).includes(\'coding\')).length;\n  if (name === \'reasoning\') return llms.filter(m => (m.capabilities || []).includes(\'reasoning\')).length;\n  if (name === \'vision\') return llms.filter(m => (m.capabilities || []).includes(\'vision\')).length;\n  if (name === \'image_generation\') return images.length;\n  return 0;\n}\n\nfunction renderCapabilities() {\n  const caps = [\n    [\'Conversation\', \'conversation\'],\n    [\'Programming\', \'programming\'],\n    [\'Reasoning\', \'reasoning\'],\n    [\'Vision\', \'vision\'],\n    [\'Image Creation\', \'image_generation\']\n  ];\n  $(\'capabilityList\').innerHTML = caps.map(([label, key]) => {\n    const score = capabilityScore(key);\n    return item(label, score ? `${score} asset(s) available` : \'Not available yet\', score ? \'ok\' : \'wait\');\n  }).join(\'\');\n}\n\nfunction renderSystem() {\n  const sys = state.status?.system || {};\n  const cpu = sys.cpu || {};\n  const mem = sys.memory || {};\n  const disk = sys.disk || {};\n  $(\'systemSummary\').innerHTML = [\n    item(\'OS\', sys.os?.platform || \'Unknown\', sys.os ? \'ok\' : \'wait\'),\n    item(\'CPU\', cpu.name || \'Unknown\', cpu.name ? \'ok\' : \'wait\'),\n    item(\'RAM\', mem.total_gb ? `${mem.total_gb} GB` : \'Unknown\', mem.total_gb ? \'ok\' : \'wait\'),\n    item(\'Disk Free\', disk.free_gb ? `${disk.free_gb} GB free` : \'Unknown\', disk.free_gb ? \'ok\' : \'wait\')\n  ].join(\'\');\n}\n\nfunction renderEvents() {\n  const events = state.status?.events || state.bridge?.events || [];\n  $(\'eventList\').innerHTML = events.slice(-8).reverse().map(e =>\n    item(e.type || \'event\', e.message || e.timestamp || \'\', \'ok\')\n  ).join(\'\') || item(\'Events\', \'No events yet\', \'wait\');\n}\n\nfunction renderRelease() {\n  const r = state.release || {};\n  $(\'releaseSummary\').innerHTML = [\n    item(\'Ship Ready\', r.ship_ready ? \'YES\' : \'NO / Unknown\', r.ship_ready ? \'ok\' : \'wait\'),\n    item(\'Version\', r.version || \'Unknown\', r.version ? \'ok\' : \'wait\'),\n    item(\'Warnings\', r.summary?.warnings ?? \'Unknown\', \'wait\')\n  ].join(\'\');\n}\n\nfunction renderWorkshopWall() {\n  $(\'workshopWall\').innerHTML = [\n    item(\'Architecture Law #1\', \'Build complete, integrated features—not isolated components.\', \'ok\'),\n    item(\'Architecture Law #2\', \'Capabilities are discovered, never hardcoded.\', \'ok\'),\n    item(\'Architecture Law #3\', \'The interface teaches, assists, and builds.\', \'ok\'),\n    item(\'Feature 001\', \'Local Chat in progress.\', \'wait\')\n  ].join(\'\');\n}\n\nfunction renderLibrary() {\n  const files = state.status?.system?.assets?.knowledge_files;\n  $(\'librarySummary\').innerHTML = [\n    item(\'Knowledge Files\', files ?? \'Unknown\', files ? \'ok\' : \'wait\'),\n    item(\'Next\', \'Iron Library indexing is a future complete feature.\', \'wait\')\n  ].join(\'\');\n}\n\nasync function sendChat(prompt) {\n  addMessage(\'user\', prompt);\n  addMessage(\'system\', \'Sending to local AI Gateway...\');\n  try {\n    const res = await fetch(API + \'/api/chat\', {\n      method: \'POST\',\n      headers: { \'Content-Type\': \'application/json\' },\n      body: JSON.stringify({ prompt })\n    });\n    const data = await res.json();\n    const text = data.response || data.message || data.error || JSON.stringify(data).slice(0, 1000);\n    addMessage(data.ok ? \'assistant\' : \'system\', text);\n  } catch (err) {\n    addMessage(\'system\', \'Chat failed: \' + err.message);\n  }\n}\n\nfunction addMessage(role, text) {\n  const log = $(\'chatLog\');\n  const div = document.createElement(\'div\');\n  div.className = \'message \' + role;\n  div.textContent = text;\n  log.appendChild(div);\n  log.scrollTop = log.scrollHeight;\n}\n\ndocument.querySelectorAll(\'.nav\').forEach(btn => {\n  btn.addEventListener(\'click\', () => {\n    document.querySelectorAll(\'.nav\').forEach(b => b.classList.remove(\'active\'));\n    document.querySelectorAll(\'.room\').forEach(r => r.classList.remove(\'active\'));\n    btn.classList.add(\'active\');\n    const room = btn.dataset.room;\n    document.getElementById(room)?.classList.add(\'active\');\n    $(\'roomTitle\').textContent = btn.textContent.replace(/[^\\w\\s]/g, \'\').trim();\n  });\n});\n\n$(\'chatForm\').addEventListener(\'submit\', (e) => {\n  e.preventDefault();\n  const input = $(\'chatInput\');\n  const prompt = input.value.trim();\n  if (!prompt) return;\n  input.value = \'\';\n  sendChat(prompt);\n});\n\nrefresh();\nsetInterval(refresh, 5000);\n'

def info(msg):
    print(f"[Feature 002 Bridge App] {msg}")

def write_text(rel, content):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def copy_item(src_rel):
    src = ROOT / src_rel
    if not src.exists():
        return
    dst = BACKUP_DIR / src_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)

def backup_project():
    info("Creating safety backup...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for item in ["manifest.yaml","Bridge","System","Forge","Foundry","Docs","00_START_HERE"]:
        copy_item(item)
    info(f"Backup created: {BACKUP_DIR}")

def install_bridge_app():
    write_text("Bridge/package.json", PACKAGE_JSON)
    write_text("Bridge/main.js", MAIN_JS)
    write_text("Bridge/preload.js", PRELOAD_JS)
    write_text("Bridge/index.html", INDEX_HTML)
    write_text("Bridge/style.css", STYLE_CSS)
    write_text("Bridge/renderer.js", RENDERER_JS)

    write_text("Start_Bridge.bat", """@echo off
title KayocktheOS Bridge
color 0A
cd /d "%~dp0Bridge"

if not exist node_modules (
  echo Installing Bridge dependencies...
  npm install
)

npm start
pause
""")

    write_text("Bridge/README.md", """# KayocktheOS Bridge

Feature 002 starter Bridge application.

## Run

From the KayocktheOS root:

```bat
Start_Bridge.bat
```

The Core API should already be running from:

```bat
Start_KayocktheOS.bat
```
""")
    info("Bridge app starter installed.")

def update_manifest():
    path = ROOT / "manifest.yaml"
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if text:
        if "feature_002_bridge_app: enabled" not in text:
            text += "\n  feature_002_bridge_app: enabled\n" if "features:" in text else "\nfeatures:\n  feature_002_bridge_app: enabled\n"
        path.write_text(text, encoding="utf-8")

def create_docs():
    write_text("Docs/FEATURE_002_BRIDGE_APP.md", """# Feature 002 - Bridge Application

The Bridge is the front door of KayocktheOS.

## Run

1. Start Core:

```bat
Start_KayocktheOS.bat
```

2. Start Bridge:

```bat
Start_Bridge.bat
```

## Rooms

- Home
- Academy
- Workshop
- Library
- Observatory
- Foundry

## Design rule

The Bridge is not a launcher. It is the operating environment.
""")
    write_text("Forge/Decisions/0018_feature_002_bridge_app.md", """# Decision 0018 - Feature 002 Bridge App

The Bridge becomes the center of KayocktheOS.

The browser becomes one tool/room, not the identity of the whole system.
""")
    write_text("Foundry/Releases/feature002_bridge_app_notes.md", "# Feature 002 - Bridge App\n\nAdds native Electron Bridge starter.\n")

def update_changelog():
    path = ROOT / "00_START_HERE/CHANGELOG.md"
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    block = "\n\n## Feature 002 - Bridge Application\n\n- Added `Bridge/` Electron app starter.\n- Added `Start_Bridge.bat`.\n- Bridge displays Home, Academy, Workshop, Library, Observatory, and Foundry rooms.\n- Bridge reads live data from Core API endpoints.\n"
    if "Feature 002 - Bridge Application" not in old:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(old.rstrip() + block, encoding="utf-8")

def main():
    info(f"Project root: {ROOT}")
    backup_project()
    install_bridge_app()
    update_manifest()
    create_docs()
    update_changelog()
    info("Feature 002 Bridge Application starter installed.")
    info("Run Start_KayocktheOS.bat first, then Start_Bridge.bat.")

if __name__ == "__main__":
    main()
