from __future__ import annotations
import json, os, re, sys, time, subprocess
from pathlib import Path
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

ROOT=Path(__file__).resolve().parents[1]; DRIVE=Path(ROOT.anchor); PORT=8765; URL=f"http://127.0.0.1:{PORT}"
KAYOCK=DRIVE/'Kayock-Browser-2.5.3-rc.1-Portable.exe'; LOGS=ROOT/'Logs'; LOG=LOGS/'web_gui.log'
ENGINE=ROOT/'Engine'/'llama-server.exe'; CHAT_HEALTH='http://127.0.0.1:8080/health'; CHAT_API='http://127.0.0.1:8080/v1/chat/completions'
COMFY=ROOT/'ComfyUI'; COMFY_MAIN=COMFY/'main.py'; LIB=ROOT/'Library'; PROJECTS=ROOT/'Projects'
PROF={
 'fox':('Agent Fox','Mission Control','Practical help. Local first.','You are Agent Fox, a helpful local AI assistant inside FOXAI. Be direct, practical, and helpful.'),
 'asimov':('Professor Asimov','Artificial Minds','An intelligent machine earns trust by revealing its reasoning.','You are Professor Asimov inside FOXAI. Specialize in AI systems, software architecture, safe automation, and transparent reasoning.'),
 'sagan':('Professor Sagan','Scientific Curiosity','Extraordinary claims require extraordinary evidence.','You are Professor Sagan inside FOXAI. Specialize in science, evidence, skepticism, cosmology, and clear explanations.'),
 'kayock':('Professor Kayock','Practical Engineering','Wonder is a tool. Build with it.','You are Professor Kayock inside FOXAI. Specialize in troubleshooting, Windows repair, Linux, networking, local AI workstations, and step-by-step engineering.'),
 'roddenberry':('Professor Roddenberry','Optimistic Futures','Technology reaches its highest purpose when it enlarges humanity.','You are Professor Roddenberry inside FOXAI. Specialize in hopeful futures, ethical technology, design, storytelling, and human-centered systems.'),
 'deadpool':('Professor Deadpool','Meta Creativity',"The best stories know they're being told.",'You are Professor Deadpool inside FOXAI. Specialize in creative brainstorming, comedy, comics, characters, and bold ideas while still being useful.')}
prof='fox'; active_project=None; chat_model=None; chat_process=None
messages=[{'role':'system','content':PROF[prof][3]}]
FOLDERS={'root':ROOT,'models':ROOT/'Models','chat_models':ROOT/'Models'/'Chat','comfy_output':COMFY/'output','library':LIB,'projects':PROJECTS,'prompts':ROOT/'Prompts','logs':LOGS,'config':ROOT/'Config'}

def log(s): LOGS.mkdir(exist_ok=True); LOG.open('a',encoding='utf-8').write(f"[{datetime.now():%F %T}] {s}\n")
def now(): return datetime.now().isoformat(timespec='seconds')
def jread(p,d):
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else d
    except Exception: return d
def jwrite(p,d): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(d,indent=2),encoding='utf-8')
def slug(n): return (re.sub(r'[^A-Za-z0-9 _.-]','',n).strip().replace(' ','_')[:80] or 'New_Project')
def ppath(name):
    c=(PROJECTS/slug(name)).resolve()
    try: c.relative_to(PROJECTS.resolve()); return c
    except Exception: return None
def active_prof(): return PROF.get(prof,PROF['fox'])
def reset_msgs():
    global messages; messages=[{'role':'system','content':active_prof()[3]}]
def timeline(project,event):
    p=ppath(project); 
    if not p: return
    arr=jread(p/'timeline.json',[]); arr.append({'time':now(),'event':event}); jwrite(p/'timeline.json',arr[-500:])
def ensure_mission(project):
    p=ppath(project); p.mkdir(parents=True,exist_ok=True)
    m=jread(p/'mission.json',None)
    if not m:
        m={'project':p.name,'created':now(),'last_opened':now(),'active_professor':prof,'active_professor_name':active_prof()[0],'active_model':chat_model,'active_model_name':Path(chat_model).name if chat_model else None,'current_task':'Getting started','notes_file':'FOXAI_PROJECT_NOTES.md'}
        jwrite(p/'mission.json',m); timeline(p.name,'Mission memory initialized')
    return m
def save_state(event=None):
    if not active_project: return {'ok':False,'message':'No active project selected.'}
    p=ppath(active_project); m=ensure_mission(active_project)
    m.update({'last_opened':now(),'active_professor':prof,'active_professor_name':active_prof()[0],'active_model':chat_model,'active_model_name':Path(chat_model).name if chat_model else None})
    jwrite(p/'mission.json',m)
    if event: timeline(active_project,event)
    return {'ok':True,'message':'Mission state saved.','mission':m}
def tasks(): return jread(ppath(active_project)/'tasks.json',[]) if active_project else []
def save_tasks(t): jwrite(ppath(active_project)/'tasks.json',t)
def models():
    bases=[ROOT/'Models'/'Chat',ROOT/'Models',ROOT/'models',ROOT/'Engine']; out=[]; seen=set()
    for b in bases:
        if b.exists():
            for p in b.rglob('*.gguf'):
                k=str(p.resolve()).lower()
                if k not in seen: seen.add(k); out.append(p)
    return sorted(out,key=lambda p:p.name.lower())
def check(url):
    try:
        import urllib.request; urllib.request.urlopen(url,timeout=1.5).read(32); return True
    except Exception: return False
def post(url,payload,timeout=300):
    import urllib.request
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read().decode(errors='replace'))
def launch(cmd,cwd): return subprocess.Popen(cmd,cwd=str(cwd),creationflags=subprocess.CREATE_NEW_CONSOLE if os.name=='nt' else 0)
def pycmd():
    for p in [ROOT/'env'/'python'/'python.exe',ROOT/'python'/'python.exe',ROOT/'ComfyUI'/'python_embeded'/'python.exe']:
        if p.exists(): return [str(p)]
    return [sys.executable]
def openurl(u): subprocess.Popen([str(KAYOCK),u],cwd=str(DRIVE)) if KAYOCK.exists() else __import__('webbrowser').open(u)
def metric():
    try:
        import psutil; m=psutil.virtual_memory(); return {'cpu_percent':round(psutil.cpu_percent(interval=.1),1),'ram_total_gb':round(m.total/2**30,1),'ram_used_gb':round((m.total-m.available)/2**30,1),'ram_percent':round(m.percent,1)}
    except Exception: return {'cpu_percent':None,'ram_total_gb':None,'ram_used_gb':None,'ram_percent':None}
def human(n):
    for u in ['B','KB','MB','GB','TB']:
        if n<1024: return f'{n:.0f} {u}' if u=='B' else f'{n:.1f} {u}'
        n/=1024
    return f'{n:.1f} PB'
def safelib(rel):
    c=(LIB/unquote(rel or '').replace('\\','/').strip('/')).resolve()
    try: c.relative_to(LIB.resolve()); return c
    except Exception: return None

HTML=r"""<!doctype html>
<html>
<head>
<meta charset=utf-8>
<title>FOXAI Command Bridge</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>
:root{
  --bg:#070811;--bg2:#0d0f1a;--panel:#121420;--panel2:#181b2a;--panel3:#202436;
  --text:#f4f1ff;--muted:#aeb2c8;--purple:#8f5cff;--purple2:#b18cff;
  --cyan:#23d7ff;--green:#42ff9e;--orange:#ff9f43;--blue:#3ba7ff;
  --magenta:#ff5ccf;--gold:#ffd166;--red:#ff4d6d;--line:rgba(143,92,255,.32)
}
*{box-sizing:border-box}
body{
  margin:0;color:var(--text);font-family:Segoe UI,system-ui,sans-serif;
  background:
    radial-gradient(circle at 14% 5%,rgba(143,92,255,.28),transparent 32%),
    radial-gradient(circle at 86% 9%,rgba(35,215,255,.12),transparent 28%),
    linear-gradient(135deg,#04050b,var(--bg2) 55%,#05060b);
}
.app{display:grid;grid-template-columns:292px 1fr;min-height:100vh}
aside{
  border-right:1px solid var(--line);padding:22px;background:rgba(0,0,0,.28);
  position:sticky;top:0;height:100vh;overflow:auto;backdrop-filter:blur(12px)
}
main{padding:24px;max-width:1540px;width:100%;overflow:hidden}
.logo{
  width:92px;height:92px;border:1px solid var(--line);border-radius:26px;
  display:grid;place-items:center;color:var(--purple2);font-size:42px;font-weight:900;
  box-shadow:0 0 34px rgba(143,92,255,.15);background:rgba(143,92,255,.08)
}
h1{color:var(--purple2);margin:16px 0 4px;font-size:32px;letter-spacing:.04em}
.sub,.small{color:var(--muted);font-size:13px}.muted{color:var(--muted)}
.nav{
  display:block;width:100%;text-align:left;margin:7px 0;padding:12px 13px;border:1px solid rgba(255,255,255,.08);
  border-radius:15px;background:rgba(255,255,255,.035);color:var(--text);font-weight:850;cursor:pointer
}
.nav.active,.nav:hover{background:rgba(143,92,255,.18);border-color:rgba(143,92,255,.55)}
.nav[data-accent=cyan].active,.nav[data-accent=cyan]:hover{background:rgba(35,215,255,.13);border-color:rgba(35,215,255,.5)}
.nav[data-accent=orange].active,.nav[data-accent=orange]:hover{background:rgba(255,159,67,.13);border-color:rgba(255,159,67,.5)}
.nav[data-accent=blue].active,.nav[data-accent=blue]:hover{background:rgba(59,167,255,.13);border-color:rgba(59,167,255,.5)}
.nav[data-accent=magenta].active,.nav[data-accent=magenta]:hover{background:rgba(255,92,207,.13);border-color:rgba(255,92,207,.5)}
.hero,.card,.ops{
  border:1px solid rgba(255,255,255,.08);background:linear-gradient(180deg,rgba(18,20,32,.92),rgba(24,27,42,.94));
  border-radius:24px;padding:18px;margin-bottom:16px;box-shadow:0 0 32px rgba(0,0,0,.2)
}
.hero{border-color:var(--line);box-shadow:0 0 38px rgba(143,92,255,.14)}
.hero h2{font-size:clamp(34px,4vw,56px);line-height:1;margin:0 0 10px;color:#fff;text-shadow:0 0 20px rgba(143,92,255,.22)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:16px}.wide{grid-column:1/-1}
button,select{
  border:1px solid rgba(143,92,255,.55);background:rgba(143,92,255,.22);color:#fff;
  border-radius:13px;padding:10px 13px;margin:5px 5px 0 0;font-weight:850;cursor:pointer
}
button:hover{background:rgba(143,92,255,.34)}
select,input,textarea{
  width:100%;background:#0b0d17;color:var(--text);border:1px solid #332a55;border-radius:14px;padding:12px
}
textarea{min-height:92px;resize:vertical}.status{white-space:pre-wrap;font-family:Consolas,monospace;font-size:13px;color:#dfe1ff}
.page{display:none}.page.active{display:block}
.pill{display:inline-block;border:1px solid rgba(143,92,255,.36);border-radius:999px;padding:7px 10px;margin:4px;color:var(--muted)}
.ok{color:var(--green)}.warn{color:var(--gold)}.bad{color:var(--red)}.path{font-family:Consolas,monospace;color:var(--gold);overflow-wrap:anywhere}
.row{display:grid;grid-template-columns:96px 1fr;gap:8px;border-bottom:1px solid rgba(255,255,255,.07);padding:6px 0;font-family:Consolas,monospace;font-size:13px}.lab{color:var(--muted)}
.meter{height:10px;border:1px solid #332a55;border-radius:999px;overflow:hidden}.fill{height:100%;background:linear-gradient(90deg,var(--purple),var(--cyan))}
.prof{min-height:210px}.prof h3{color:var(--purple2)}.activeProf{border-color:rgba(255,209,102,.7);box-shadow:0 0 28px rgba(255,209,102,.12)}
#chatLog{height:390px;overflow:auto;background:#080a12;border:1px solid #332a55;border-radius:16px;padding:14px}
.user{color:#bfefff}.fox{color:#d8ffe0}.sys{color:var(--gold)}
.pulse{display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--green);box-shadow:0 0 14px var(--green);animation:p 1.2s infinite}@keyframes p{50%{opacity:.3}}
table{width:100%;border-collapse:collapse;font-family:Consolas,monospace;font-size:13px}td,th{border-bottom:1px solid rgba(255,255,255,.08);padding:9px;text-align:left}.link{background:transparent;border:0;color:var(--cyan);padding:0}
.done{text-decoration:line-through;color:var(--muted)}.tl{border-left:3px solid var(--purple);padding:8px 0 8px 12px;margin:8px 0;background:rgba(143,92,255,.08);border-radius:0 12px 12px 0}.time{color:var(--gold);font-family:Consolas,monospace;font-size:12px}
#toast{position:fixed;right:20px;bottom:20px;background:#111423;border:1px solid var(--line);padding:12px 16px;border-radius:14px;display:none;max-width:520px;z-index:5}
.command-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.metric{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:16px}.metric .label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em}.metric .value{font-size:28px;font-weight:900;margin-top:8px;color:var(--purple2)}
.dept-card{position:relative;overflow:hidden}.dept-card:before{content:"";position:absolute;left:0;top:0;bottom:0;width:5px;background:var(--purple)}.dept-card[data-accent=orange]:before{background:var(--orange)}.dept-card[data-accent=blue]:before{background:var(--blue)}.dept-card[data-accent=cyan]:before{background:var(--cyan)}.dept-card[data-accent=magenta]:before{background:var(--magenta)}.dept-card[data-accent=red]:before{background:var(--red)}.dept-card[data-accent=gold]:before{background:var(--gold)}
.command-bar{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}.status-badge{float:right;border:1px solid rgba(66,255,158,.45);color:var(--green);background:rgba(66,255,158,.08);border-radius:999px;padding:7px 11px;font-weight:900;font-size:12px}
@media(max-width:1100px){.command-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.app{grid-template-columns:1fr}aside{position:relative;height:auto}}
@media(max-width:620px){.command-grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class=app>
<aside>
  <div class=logo>F</div><h1>FOXAI</h1><div class=sub>Command Bridge · Orion X</div>
  <button class="nav active" onclick="pg('dash',this)">🚀 Command Bridge</button>
  <button class=nav onclick="pg('projects',this)">🗂 Projects</button>
  <button class=nav onclick="pg('memory',this)">🧭 Mission Memory</button>
  <button class=nav onclick="pg('mission',this)">💬 Mission Console</button>
  <button class=nav data-accent=cyan onclick="pg('academy',this)">🎓 Academy</button>
  <button class=nav data-accent=magenta onclick="pg('promptsmith',this)">✍ PromptSmith</button>
  <button class=nav data-accent=magenta onclick="pg('creative',this)">🎨 Creative Studio</button>
  <button class=nav data-accent=blue onclick="pg('library',this)">📚 Iron Library</button>
  <button class=nav data-accent=orange onclick="pg('repair',this)">🛠 Repair Bay</button>
  <button class=nav onclick="pg('logs',this)">📜 Logs</button>
  <button class=nav onclick="pg('settings',this)">⚙ Settings</button>
  <div class=ops>
    <div class=row><div class=lab>Operator</div><div>Eric Fox</div></div>
    <div class=row><div class=lab>Professor</div><div id=ap>Agent Fox</div></div>
    <div class=row><div class=lab>Project</div><div id=apro>None</div></div>
    <div class=row><div class=lab>Mission</div><div id=ms>READY</div></div>
    <div class=row><div class=lab>Model</div><div id=am>None</div></div>
    <div class=row><div class=lab>Runtime</div><div id=rt>Checking</div></div>
  </div>
  <div id=quick></div>
  <div class=ops><div class=row><div class=lab>CPU</div><div id=cpu>?</div></div><div class=row><div class=lab>RAM</div><div id=ram>?</div></div><div class=meter><div id=ramm class=fill></div></div></div>
</aside>
<main>
<section id=dash class="page active">
  <div class=hero>
    <span id=kernelBadge class=status-badge>INITIALIZING</span>
    <h2>Welcome back, Commander.</h2>
    <p class=muted>FOXAI Command OS · Ultimate Edifier Platform · graphite/purple bridge identity online.</p>
    <div class=command-bar>
      <button onclick="refresh()">Refresh Status</button>
      <button onclick="go('mission')">Open Mission Console</button>
      <button onclick="go('promptsmith')">Open PromptSmith</button>
      <button onclick="go('repair')">Repair Bay</button>
    </div>
  </div>
  <div class=command-grid>
    <div class=metric><div class=label>Departments</div><div id=bfDepartments class=value>—</div></div>
    <div class=metric><div class=label>Online</div><div id=bfOnline class=value>—</div></div>
    <div class=metric><div class=label>Runtime Packages</div><div id=bfPackages class=value>—</div></div>
    <div class=metric><div class=label>Captain's Log</div><div id=bfLog class=value>—</div></div>
  </div>
  <div class=grid style="margin-top:16px">
    <div class="card wide"><h3>Department Cards</h3><div id=deptCards class=grid></div></div>
    <div class=card><h3>Latest Mission</h3><div id=latestMission class=status>No recent mission.</div></div>
    <div class=card><h3>Latest Event</h3><div id=latestEvent class=status>Awaiting event.</div></div>
    <div class="card wide"><h3>Captain's Log</h3><div id=bridgeLog class=status>Loading bridge feed...</div></div>
  </div>
</section>

<section id=projects class=page><div class=hero><h2>Project Workspace</h2><p class=muted>Create and resume local workspaces.</p></div><div class=grid><div class=card><h3>New Project</h3><input id=newProject placeholder="Project name"><button onclick="createProject()">Create</button></div><div class=card><h3>Projects Folder</h3><button onclick="api('/api/open/projects')">Open Folder</button><button onclick="loadProjects()">Refresh</button></div><div class="card wide"><h3>Available Projects</h3><div id=plist class=status>Loading...</div></div><div class="card wide"><h3>Project Notes</h3><div class=small>Active: <span id=pnoteTitle class=path>None</span></div><textarea id=pnote></textarea><button onclick="saveNote()">Save Note</button><button onclick="askProject()">Ask Agent About Project</button></div></div></section>
<section id=memory class=page><div class=hero><h2>Mission Memory</h2><p class=muted>Project state, tasks, and timeline persist on the USB.</p></div><div class=grid><div class="card wide"><h3>Mission State</h3><div id=memstate class=status>No active mission.</div><button onclick="resumeMission()">Resume Mission</button><button onclick="api('/api/memory/save');loadMemory()">Save Current State</button></div><div class=card><h3>Add Task</h3><input id=task placeholder="Task"><button onclick="addTask()">Add</button></div><div class="card wide"><h3>Tasks</h3><div id=tasks class=status>No tasks.</div></div><div class="card wide"><h3>Timeline</h3><div id=timeline class=status>No timeline.</div></div></div></section>
<section id=mission class=page><div class=hero><h2>Mission Console</h2><p class=muted>Talk to the active professor using your local GGUF model.</p></div><div class="card wide"><h3><span id=pulse></span> <span id=mtitle>Agent Fox</span></h3><select id=model><option>Loading...</option></select><br><button onclick="startChat()">Start Chat Engine</button><button onclick="api('/api/chat/stop')">Stop Chat Engine</button><button onclick="api('/api/chat/reset');chat.innerHTML='Mission console reset.\n'">Reset</button><div id=chatLog class=status>Mission console ready.\n</div><textarea id=input placeholder="Ask the active professor..." onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send()}" ></textarea><button onclick="send()">Send</button></div></section>
<section id=academy class=page><div class=hero><h2>Academy</h2><p class=muted>Professors are prompt profiles and future specialist agents.</p></div><div id=profgrid class=grid></div></section>
<section id=promptsmith class=page><div class=hero><h2>PromptSmith</h2><p class=muted>Forge, test, save, and improve prompts. Browser-extension integration point.</p></div><div class=grid><div class=card><h3>Prompt Draft</h3><textarea id=psDraft placeholder="Write or paste a prompt to refine..."></textarea><button onclick="psPolish()">Polish Prompt</button><button onclick="psSend()">Send to Mission Console</button></div><div class=card><h3>PromptSmith Notes</h3><div class=status id=psOut>PromptSmith is ready. This is the first-class workspace for the extension to target.</div></div></div></section>
<section id=creative class=page><div class=hero><h2>Creative Studio</h2><p class=muted>ComfyUI remains the image engine. Novel Forge belongs here next.</p></div><div class=grid><div class=card><h3>ComfyUI</h3><button onclick="api('/api/launch/comfy')">Launch</button><button onclick="api('/api/open-url/comfy')">Open</button></div><div class=card><h3>Gallery</h3><button onclick="api('/api/open/comfy_output')">Open Output</button></div><div class=card><h3>Novel Forge</h3><p class=muted>Planned story OS: codex, continuity, timeline, relationship graph, canon tracking.</p><button onclick="go('promptsmith')">Start With PromptSmith</button></div></div></section>
<section id=library class=page><div class=hero><h2>Iron Library</h2><p class=muted>Browse local reference files.</p></div><div class="card wide"><h3>Library Browser</h3><div id=libpath class="small path">Library</div><button onclick="libUp()">Up</button><button onclick="loadLib('')">Root</button><button onclick="api('/api/open/library')">Explorer</button><div id=liblist class=status>Loading...</div></div></section>
<section id=repair class=page><div class=hero><h2>Repair Bay</h2><p class=muted>Diagnostics first. Automated repair later.</p></div><div class=grid><div class=card><h3>Diagnostics</h3><button onclick="refresh()">Refresh Status</button></div><div class=card><h3>Config</h3><button onclick="api('/api/open/config')">Open Config</button></div></div></section>
<section id=logs class=page><div class=hero><h2>Logs</h2></div><div class=card><button onclick="api('/api/open/logs')">Open Logs</button><div id=status2 class=status></div></div></section>
<section id=settings class=page><div class=hero><h2>Settings</h2></div><div class=card><div id=paths class=status></div><button onclick="api('/api/open-url/github')">Open GitHub</button></div></section>
</main></div><div id=toast></div>

<script>
let activeProject=null, curLib='', missionData=null; const chat=document.getElementById('chatLog');
function q(id){return document.getElementById(id)}function toast(s){q('toast').textContent=s;q('toast').style.display='block';setTimeout(()=>q('toast').style.display='none',4200)}
function pg(id,b){document.querySelectorAll('.page').forEach(x=>x.classList.remove('active'));q(id).classList.add('active');document.querySelectorAll('.nav').forEach(x=>x.classList.remove('active'));if(b)b.classList.add('active'); if(id==='projects')loadProjects(); if(id==='memory')loadMemory(); if(id==='library')loadLib(curLib)}
function go(id){const map={dash:0,projects:1,memory:2,mission:3,academy:4,promptsmith:5,creative:6,library:7,repair:8,logs:9,settings:10};pg(id,document.querySelectorAll('.nav')[map[id]])}
async function api(u,opt){try{let r=await fetch(u,opt);let d=await r.json();toast(d.message||JSON.stringify(d));refresh();return d}catch(e){toast('Request failed: '+e)}}
function esc(s){return String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]))}function js(s){return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'")}
function logline(c,w,m){chat.innerHTML+=`<span class=${c}>[${w}]</span> ${esc(m)}\n\n`;chat.scrollTop=chat.scrollHeight}function think(on){q('pulse').innerHTML=on?'<span class=pulse></span>':'';q('ms').textContent=on?'THINKING':'READY'}
async function loadBridgeFeed(){try{let d=await (await fetch('/api/bridge/feed')).json();renderBridgeFeed(d)}catch(e){}}
function renderBridgeFeed(d){
 if(!d||!d.ok){q('kernelBadge').textContent='BRIDGE FEED WAITING';return}
 q('kernelBadge').textContent=(d.kernel&&d.kernel.status)||'ONLINE';
 let s=d.summary||{}; q('bfDepartments').textContent=s.department_count??'—'; q('bfOnline').textContent=s.departments_online??'—'; q('bfPackages').textContent=s.runtime_packages??'—'; q('bfLog').textContent=s.captains_log_entries??'—';
 q('latestMission').textContent=s.latest_mission||'No recent mission.'; q('latestEvent').textContent=s.latest_event||'Awaiting event.';
 let cards=d.department_cards||[]; q('deptCards').innerHTML=cards.map(c=>`<div class="card dept-card" data-accent="${esc(c.accent||'purple')}"><h3>${esc(c.title||c.id)}</h3><div class=small>${esc(c.officer||'Unassigned')}</div><p class="${c.ok?'ok':'warn'}">${esc(c.status||'UNKNOWN')}</p><div class=small>Services: ${(c.services||[]).length} · Tools: ${Object.keys(c.tools||{}).length}</div></div>`).join('')||'<div class=card>No department cards yet.</div>';
 let entries=((d.captains_log||{}).entries||[]).slice(-7).reverse(); q('bridgeLog').innerHTML=entries.map(e=>`${esc(e.timestamp||'')} — ${esc(e.source||'FOXAI')}\n[${esc(e.severity||'info')}] ${esc(e.message||'')}`).join('\n\n')||'No Captain\\'s Log entries yet.';
}
async function loadModels(){let d=await (await fetch('/api/models')).json();q('model').innerHTML=d.models.length?d.models.map(m=>`<option value="${esc(m.path)}">${esc(m.name)}</option>`).join(''):'<option>No GGUF models found</option>'}
async function loadProf(){let d=await (await fetch('/api/professors')).json();q('profgrid').innerHTML=Object.entries(d.professors).map(([k,p])=>`<div class="card prof ${k===d.active?'activeProf':''}"><h3>${esc(p.name)}</h3><div class=warn>${esc(p.college)}</div><p class=small><i>"${esc(p.motto)}"</i></p><button onclick="setProf('${k}')">${k===d.active?'Active':'Activate'}</button><button onclick="setProf('${k}').then(()=>go('mission'))">Use in Mission</button></div>`).join('')}
async function setProf(k){let d=await api('/api/professor/set',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:k})}); if(d?.ok){logline('sys','ACADEMY',d.message);loadProf();loadMemory()}}
async function startChat(){let d=await api('/api/chat/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:q('model').value})}); logline(d?.ok?'sys':'bad','SYSTEM',d?.message||'start failed');loadMemory()}
async function send(){let text=q('input').value.trim();if(!text)return;q('input').value='';logline('user','ERIC',text);think(true);try{let d=await (await fetch('/api/chat/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text})})).json();d.ok?logline('fox',q('ap').textContent.toUpperCase(),d.answer):logline('bad','ERROR',d.message)}catch(e){logline('bad','ERROR',String(e))}think(false);loadMemory();refresh()}
async function loadProjects(){let d=await (await fetch('/api/projects/list')).json();q('plist').innerHTML='<div class=grid>'+d.projects.map(p=>`<div class="card project"><h3>🗂 ${esc(p.name)}</h3><p class=small>Files: ${p.files} | Updated: ${esc(p.modified)}</p><button onclick="selectProject('${js(p.name)}')">Select</button><button onclick="api('/api/projects/open?name=${encodeURIComponent(p.name)}')">Open Folder</button></div>`).join('')+'</div>'}
async function createProject(){let name=q('newProject').value.trim();if(!name)return toast('Enter a project name.');let d=await api('/api/projects/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});if(d?.ok){q('newProject').value='';loadProjects();selectProject(d.name)}}
async function selectProject(name){let d=await (await fetch('/api/projects/select',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})})).json();toast(d.message);if(d.ok){activeProject=d.name;q('apro').textContent=d.name;q('pnoteTitle').textContent=d.name;q('pnote').value=d.note||'';loadMemory();refresh()}}
async function saveNote(){if(!activeProject)return toast('Select a project first.');await api('/api/projects/save-note',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:activeProject,note:q('pnote').value})});loadMemory()}
function askProject(){if(!activeProject)return toast('Select a project first.');go('mission');q('input').value=`We are working on project "${activeProject}". Here are my current notes:\n\n${q('pnote').value}\n\nWhat should I do next?`}
async function loadMemory(){let d=await (await fetch('/api/memory/current')).json();missionData=d;if(!d.ok){q('memstate').textContent=d.message;q('tasks').textContent='No tasks.';q('timeline').textContent='No timeline.';return}let m=d.mission;let state=`Project: ${m.project}\nCurrent task: ${m.current_task||'None'}\nProfessor: ${m.active_professor_name}\nModel: ${m.active_model_name||'None'}\nCreated: ${m.created}\nLast opened: ${m.last_opened}\nEvents: ${d.timeline.length}\nTasks: ${d.tasks.length}`;q('memstate').textContent=state;q('tasks').innerHTML=d.tasks.length?d.tasks.map((t,i)=>`<div><input type=checkbox ${t.done?'checked':''} onchange="toggleTask(${i},this.checked)"> <span class="${t.done?'done':''}">${esc(t.text)}</span></div>`).join(''):'No tasks yet.';q('timeline').innerHTML=d.timeline.slice().reverse().slice(0,35).map(e=>`<div class=tl><div class=time>${esc(e.time)}</div>${esc(e.event)}</div>`).join('')||'No timeline yet.'}
async function addTask(){let text=q('task').value.trim();if(!text)return toast('Enter a task.');await api('/api/memory/task/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});q('task').value='';loadMemory()}
async function toggleTask(index,done){await api('/api/memory/task/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({index,done})});loadMemory()}
function resumeMission(){if(!missionData?.ok){toast('Select a project first.');go('projects');return}let m=missionData.mission;go('mission');q('input').value=`Resume mission "${m.project}". Current task: ${m.current_task||'None'}. Active professor: ${m.active_professor_name}. What should we do next?`;toast('Mission context loaded.')}
async function loadLib(rel=''){curLib=rel;let d=await (await fetch('/api/library/list?path='+encodeURIComponent(rel))).json();q('libpath').textContent=d.display_path||'Library';if(!d.ok){q('liblist').textContent=d.message;return}q('liblist').innerHTML='<table><tr><th>Name</th><th>Type</th><th>Size</th><th>Action</th></tr>'+d.items.map(it=>`<tr><td>${it.is_dir?'📁':'📄'} ${esc(it.name)}</td><td>${it.is_dir?'folder':it.ext}</td><td>${it.size}</td><td>${it.is_dir?`<button class=link onclick="loadLib('${js(it.rel_path)}')">Open</button>`:`<button class=link onclick="api('/api/library/open?path=${encodeURIComponent(it.rel_path)}')">Open File</button>`}</td></tr>`).join('')+'</table>'}
function libUp(){let a=curLib.split(/[\\/]/).filter(Boolean);a.pop();loadLib(a.join('/'))}
function psPolish(){let v=q('psDraft').value.trim();q('psOut').textContent=v?`PromptSmith draft prepared:\n\n${v}\n\nNext step: route this to the active professor for critique, expansion, or model-specific formatting.`:'Add a draft prompt first.'}
function psSend(){let v=q('psDraft').value.trim();if(!v)return toast('Add a prompt first.');go('mission');q('input').value=`PromptSmith request:\n\nPlease improve this prompt, make it clearer, and explain why the revised version is better:\n\n${v}`}
async function refresh(){let s=await (await fetch('/api/status')).json();let lines=[`Root: ${s.root}`,`Kayock Browser: ${s.kayock_browser_found?'found':'missing'}`,`Engine: ${s.engine_found?'found':'missing'}`,`Chat online: ${s.chat_online?'yes':'no'}`,`Active project: ${s.active_project||'None'}`,`Projects: ${s.projects}`,`ComfyUI: ${s.comfy_online?'online':'offline'}`,`Chat models: ${s.chat_models}`,`Library items: ${s.library_items}`,`PDFs: ${s.library_pdfs}`];q('status2').textContent=lines.join('\n');q('paths').textContent=`Root: ${s.root}\nDrive: ${s.drive_root}\nBrowser: ${s.kayock_browser}\nEngine: ${s.engine}\nProjects: ${s.projects_root}`;q('am').textContent=s.chat_model_name||'None';q('ap').textContent=s.active_professor_name||'Agent Fox';q('mtitle').textContent=s.active_professor_name||'Agent Fox';q('apro').textContent=s.active_project||'None';q('rt').textContent=s.chat_online?'ONLINE':'OFFLINE';q('cpu').textContent=s.cpu_percent!==null?`${s.cpu_percent}%`:'n/a';q('ram').textContent=s.ram_used_gb!==null?`${s.ram_used_gb}/${s.ram_total_gb} GB (${s.ram_percent}%)`:'n/a';q('ramm').style.width=s.ram_percent!==null?`${s.ram_percent}%`:'0%';q('quick').innerHTML=`<span class="pill ${s.engine_found?'ok':'bad'}">Engine ${s.engine_found?'Found':'Missing'}</span><br><span class="pill ${s.chat_online?'ok':'warn'}">Chat ${s.chat_online?'Online':'Offline'}</span><br><span class="pill ${s.comfy_online?'ok':'warn'}">ComfyUI ${s.comfy_online?'Online':'Offline'}</span>`;loadBridgeFeed()}
loadModels();loadProf();loadProjects();loadMemory();refresh();setInterval(refresh,8000)
</script>
</body></html>"""

class Handler(BaseHTTPRequestHandler):
    def body(self):
        n=int(self.headers.get('Content-Length','0') or 0); return json.loads(self.rfile.read(n).decode(errors='replace')) if n else {}
    def sendit(self,b,ct='text/html; charset=utf-8'):
        self.send_response(200); self.send_header('Content-Type',ct); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(b)
    def js(self,d): self.sendit(json.dumps(d,indent=2).encode(),'application/json; charset=utf-8')
    def do_GET(self):
        global active_project
        u=urlparse(self.path); path=u.path; qs=parse_qs(u.query)
        if path=='/': self.sendit(HTML.encode()); return
        if path=='/api/status': self.js(status()); return
        if path=='/api/models': self.js({'models':[{'name':p.name,'path':str(p)} for p in models()]}); return
        if path=='/api/professors': self.js({'active':prof,'professors':{k:{'name':v[0],'college':v[1],'motto':v[2]} for k,v in PROF.items()}}); return
        if path=='/api/memory/current': self.js(mission_current()); return
        if path=='/api/projects/list': self.js(list_projects()); return
        if path=='/api/projects/open':
            p=ppath(qs.get('name',[''])[0])
            if not p or not p.exists(): self.js({'ok':False,'message':'Project not found.'}); return
            os.startfile(str(p)); timeline(p.name,'Project folder opened'); self.js({'ok':True,'message':f'Opened {p.name}'}); return
        if path=='/api/library/list': self.js(list_lib(qs.get('path',[''])[0])); return
        if path=='/api/library/open':
            p=safelib(qs.get('path',[''])[0])
            if not p or not p.exists() or p.is_dir(): self.js({'ok':False,'message':'Invalid file.'}); return
            os.startfile(str(p));
            if active_project: timeline(active_project,f'Library file opened: {p.name}')
            self.js({'ok':True,'message':f'Opened {p.name}'}); return
        if path=='/api/chat/stop': self.js(stop_chat()); return
        if path=='/api/chat/reset': reset_msgs(); save_state('Conversation reset'); self.js({'ok':True,'message':'Conversation reset.'}); return
        if path=='/api/launch/comfy':
            if not COMFY_MAIN.exists(): self.js({'ok':False,'message':'ComfyUI main.py not found.'}); return
            if check('http://127.0.0.1:8188'): self.js({'ok':True,'message':'ComfyUI is already online.'}); return
            launch(pycmd()+[str(COMFY_MAIN),'--cpu'],COMFY); timeline(active_project,'ComfyUI launched') if active_project else None; self.js({'ok':True,'message':'Launched ComfyUI.'}); return
        if path=='/api/open-url/comfy': openurl('http://127.0.0.1:8188'); self.js({'ok':True,'message':'Opened ComfyUI.'}); return
        if path=='/api/open-url/github': openurl('https://github.com/kayock/FOXAI_'); self.js({'ok':True,'message':'Opened GitHub.'}); return
        if path.startswith('/api/open/'):
            f=FOLDERS.get(path.split('/')[-1])
            if not f: self.js({'ok':False,'message':'Unknown folder.'}); return
            f.mkdir(parents=True,exist_ok=True); os.startfile(str(f)); self.js({'ok':True,'message':f'Opened {f}'}); return
        self.send_response(404); self.end_headers()
    def do_POST(self):
        global prof, active_project, chat_model, chat_process
        path=urlparse(self.path).path; d=self.body()
        if path=='/api/memory/save': self.js(save_state('Mission state manually saved')); return
        if path=='/api/memory/task/add':
            if not active_project: self.js({'ok':False,'message':'Select a project first.'}); return
            t=tasks(); txt=d.get('text','').strip(); t.append({'text':txt,'done':False,'created':now()}); save_tasks(t); timeline(active_project,f'Task added: {txt}'); self.js({'ok':True,'message':'Task added.'}); return
        if path=='/api/memory/task/toggle':
            if not active_project: self.js({'ok':False,'message':'Select a project first.'}); return
            t=tasks(); i=int(d.get('index',-1));
            if i<0 or i>=len(t): self.js({'ok':False,'message':'Task not found.'}); return
            t[i]['done']=bool(d.get('done')); t[i]['updated']=now(); save_tasks(t); timeline(active_project,('Task completed: ' if t[i]['done'] else 'Task reopened: ')+t[i]['text']); self.js({'ok':True,'message':'Task updated.'}); return
        if path=='/api/projects/create': self.js(create_project(d.get('name',''))); return
        if path=='/api/projects/select': self.js(select_project(d.get('name',''))); return
        if path=='/api/projects/save-note': self.js(save_note(d.get('name',''),d.get('note',''))); return
        if path=='/api/professor/set': self.js(set_prof(d.get('key',''))); return
        if path=='/api/chat/start': self.js(start_chat(d.get('model',''))); return
        if path=='/api/chat/send':
            text=(d.get('message') or '').strip()
            if not text: self.js({'ok':False,'message':'Empty message.'}); return
            if not check(CHAT_HEALTH): self.js({'ok':False,'message':'Chat engine is offline. Start Chat Engine first.'}); return
            messages.append({'role':'user','content':text}); timeline(active_project,'Message sent to Mission Console') if active_project else None
            try:
                r=post(CHAT_API,{'model':'local-model','messages':messages,'temperature':0.7,'max_tokens':768,'stream':False}); ans=r['choices'][0]['message']['content'].strip(); messages.append({'role':'assistant','content':ans}); save_state('Agent response received'); self.js({'ok':True,'answer':ans}); return
            except Exception as e: self.js({'ok':False,'message':f'Chat request failed: {e}'}); return
        self.send_response(404); self.end_headers()
    def log_message(self,*a): return

def list_projects():
    PROJECTS.mkdir(parents=True,exist_ok=True); arr=[]
    for p in sorted([x for x in PROJECTS.iterdir() if x.is_dir()],key=lambda x:x.name.lower()):
        arr.append({'name':p.name,'files':sum(1 for _ in p.rglob('*') if _.is_file()),'modified':datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y-%m-%d %H:%M')})
    return {'ok':True,'projects':arr}
def create_project(name):
    global active_project
    p=ppath(name)
    if not p: return {'ok':False,'message':'Invalid project name.'}
    p.mkdir(parents=True,exist_ok=True); note=p/'FOXAI_PROJECT_NOTES.md'
    if not note.exists(): note.write_text(f'# {p.name}\n\nCreated: {datetime.now():%Y-%m-%d %H:%M}\n\n## Notes\n\n',encoding='utf-8')
    active_project=p.name; ensure_mission(active_project); timeline(active_project,'Project created'); save_state('Project selected'); return {'ok':True,'message':f'Project ready: {p.name}','name':p.name}
def select_project(name):
    global active_project,prof,chat_model
    p=ppath(name)
    if not p or not p.exists(): return {'ok':False,'message':'Project not found.'}
    active_project=p.name; m=ensure_mission(active_project)
    if m.get('active_professor') in PROF: prof=m['active_professor']; reset_msgs()
    if m.get('active_model'): chat_model=m.get('active_model')
    m['last_opened']=now(); jwrite(p/'mission.json',m); timeline(active_project,'Project opened')
    note=p/'FOXAI_PROJECT_NOTES.md'; return {'ok':True,'message':f'Selected project: {p.name}','name':p.name,'note':note.read_text(encoding='utf-8',errors='replace') if note.exists() else ''}
def save_note(name,note):
    p=ppath(name)
    if not p or not p.exists(): return {'ok':False,'message':'Project not found.'}
    (p/'FOXAI_PROJECT_NOTES.md').write_text(note,encoding='utf-8'); timeline(p.name,'Project notes saved') if active_project==p.name else None; return {'ok':True,'message':f'Saved notes for {p.name}.'}
def mission_current():
    if not active_project: return {'ok':False,'message':'No active project selected.'}
    return {'ok':True,'mission':ensure_mission(active_project),'timeline':jread(ppath(active_project)/'timeline.json',[]),'tasks':tasks()}
def set_prof(k):
    global prof
    if k not in PROF: return {'ok':False,'message':'Unknown professor.'}
    prof=k; reset_msgs(); save_state(f'Professor changed to {active_prof()[0]}'); return {'ok':True,'message':f'{active_prof()[0]} is now active. Conversation reset.'}
def start_chat(model_path):
    global chat_model,chat_process
    m=Path(model_path); allowed={str(p.resolve()).lower():p for p in models()}; key=str(m.resolve()).lower() if m.exists() else ''
    if key not in allowed: return {'ok':False,'message':'Selected model is not inside FOXAI Models.'}
    if not ENGINE.exists(): return {'ok':False,'message':f'Missing engine: {ENGINE}'}
    if check(CHAT_HEALTH): chat_model=str(m); save_state(f'Chat model selected: {m.name}'); return {'ok':True,'message':f'Chat engine online with {m.name}'}
    chat_model=str(m); chat_process=launch([str(ENGINE),'--model',str(m),'--host','127.0.0.1','--port','8080','--ctx-size','4096','--threads','8'],ROOT)
    for _ in range(60):
        if check(CHAT_HEALTH): save_state(f'Chat engine started with {m.name}'); return {'ok':True,'message':f'Chat engine online with {m.name}'}
        time.sleep(1)
    return {'ok':False,'message':'Chat engine started but did not answer within 60 seconds.'}
def stop_chat():
    global chat_process
    if chat_process and chat_process.poll() is None: chat_process.terminate(); chat_process=None; save_state('Chat engine stopped'); return {'ok':True,'message':'Stopped chat engine launched by web console.'}
    return {'ok':True,'message':'No web-console-launched chat engine to stop.'}
def list_lib(rel):
    LIB.mkdir(parents=True,exist_ok=True); p=safelib(rel)
    if not p or not p.exists() or not p.is_dir(): return {'ok':False,'message':'Invalid library path.','items':[]}
    items=[]
    for x in sorted(p.iterdir(),key=lambda y:(not y.is_dir(),y.name.lower())):
        try: items.append({'name':x.name,'rel_path':str(x.relative_to(LIB)).replace('\\','/'),'is_dir':x.is_dir(),'ext':x.suffix.lower(),'size':'' if x.is_dir() else human(x.stat().st_size)})
        except Exception: pass
    return {'ok':True,'display_path':'Library' if p==LIB.resolve() else 'Library/'+str(p.relative_to(LIB)).replace('\\','/'),'items':items}
def status():
    PROJECTS.mkdir(exist_ok=True); LIB.mkdir(exist_ok=True); d={'root':str(ROOT),'drive_root':str(DRIVE),'kayock_browser':str(KAYOCK),'kayock_browser_found':KAYOCK.exists(),'engine':str(ENGINE),'engine_found':ENGINE.exists(),'chat_online':check(CHAT_HEALTH),'chat_model':chat_model,'chat_model_name':Path(chat_model).name if chat_model else None,'active_project':active_project,'projects':len([p for p in PROJECTS.iterdir() if p.is_dir()]),'projects_root':str(PROJECTS),'active_professor_name':active_prof()[0],'comfy_exists':COMFY_MAIN.exists(),'comfy_online':check('http://127.0.0.1:8188'),'chat_models':len(models()),'library_items':len(list(LIB.rglob('*'))) if LIB.exists() else 0,'library_pdfs':len(list(LIB.rglob('*.pdf'))) if LIB.exists() else 0}
    d.update(metric()); return d

def main():
    LOGS.mkdir(exist_ok=True); PROJECTS.mkdir(exist_ok=True); log(f'Starting FOXAI Web Console at {URL}'); ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
if __name__=='__main__': main()
