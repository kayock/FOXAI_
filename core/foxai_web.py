from __future__ import annotations
import shutil
import platform
import importlib.util
import json
import hashlib
import re, os, re, sys, time, subprocess, shutil, py_compile
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
FOLDERS={'root':ROOT,'models':ROOT/'Models','chat_models':ROOT/'Models'/'Chat','comfy_output':COMFY/'output','library':LIB,'projects':PROJECTS,'prompts':ROOT/'Prompts','novel_forge':ROOT/'NovelForge','novel_exports':ROOT/'NovelForge'/'Exports','logs':LOGS,'config':ROOT/'Config','reports':ROOT/'Reports','repair_reports':ROOT/'Reports'/'RepairActions','repair_ops_dashboard':ROOT/'Reports'/'RepairActions'/'OperationsDashboard','repair_action_details':ROOT/'Reports'/'RepairActions'/'ActionDetails','repair_tickets':ROOT/'Reports'/'RepairActions'/'Tickets','repair_ticket_details':ROOT/'Reports'/'RepairActions'/'TicketDetails','repair_ticket_bridges':ROOT/'Reports'/'RepairActions'/'TicketBridges','repair_session_reports':ROOT/'Reports'/'RepairActions'/'SessionReports','repair_milestone_freeze':ROOT/'Reports'/'RepairActions'/'MilestoneFreeze','command_center_reports':ROOT/'Reports'/'CommandCenter','command_center_detail_reports':ROOT/'Reports'/'CommandCenter'/'Details','command_center_card_reports':ROOT/'Reports'/'CommandCenter'/'DashboardCards','command_center_archive_reports':ROOT/'Reports'/'CommandCenter'/'Archive','command_center_milestone_freeze':ROOT/'Reports'/'CommandCenter'/'MilestoneFreeze','kayock_writer_reports':ROOT/'Reports'/'KayockWriter','kayock_writer_foundation_reports':ROOT/'Reports'/'KayockWriter'/'Foundation','kayock_writer_story_forge_reports':ROOT/'Reports'/'KayockWriter'/'StoryForge','kayock_writer_manifest_preview_reports':ROOT/'Reports'/'KayockWriter'/'ManifestPreview','kayock_writer_create_gate_reports':ROOT/'Reports'/'KayockWriter'/'CreateProjectGate','env_reports':ROOT/'Reports'/'Environment','portable_reports':ROOT/'Reports'/'PortableReadiness','model_reports':ROOT/'Reports'/'Models','build_reports':ROOT/'Reports'/'BuildVerification','scan_reports':ROOT/'Reports'/'Scans','manifest_backups':ROOT/'Backups'/'Manifests','file_backups':ROOT/'Backups'/'GeneratedFiles','restore_staging':ROOT/'Reports'/'Backups'/'RestoreStaging','staging_inventory':ROOT/'Reports'/'Backups'/'StagingInventory','final_checklist':ROOT/'Reports'/'Backups'/'FinalChecklist','restore_live_backups':ROOT/'Backups'/'RestoreLiveTargets','restore_reports':ROOT/'Reports'/'Backups'/'RestoreActions','restore_audit':ROOT/'Reports'/'Backups'/'RestoreAudit','rollback_previews':ROOT/'Reports'/'Backups'/'RollbackPreviews','rollback_live_backups':ROOT/'Backups'/'RollbackLiveTargets','rollback_reports':ROOT/'Reports'/'Backups'/'RollbackActions','rollback_audit':ROOT/'Reports'/'Backups'/'RollbackAudit','recovery_timeline':ROOT/'Reports'/'Backups'/'RecoveryTimeline','extensions':ROOT/'Extensions','modules':ROOT/'Modules'}
OPSBRIDGE_OUTBOX=ROOT/'OpsBridge'/'outbox'; BRIDGE_FEED_FILE=OPSBRIDGE_OUTBOX/'bridge_feed.json'; BUILDER_REPORT_FILE=OPSBRIDGE_OUTBOX/'builder_report.json'

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

HTML=r"""<!doctype html><html><head><meta charset=utf-8><title>Kayock Command OS</title><meta name=viewport content="width=device-width,initial-scale=1"><style>
:root{
--a:#8f5cff;--ah:#7c4de6;--p2:#b18cff;--w:#ffd166;--t:#f4f1ff;--m:#aeb2c8;--l:#2a2142;--b:#070811;--panel:#121420;--panel2:#181b2a;--r:#ff4d6d;--c:#23d7ff;--g:#42ff9e;--orange:#ff9f43;--blue:#3ba7ff;--mag:#ff5ccf}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(circle at 12% 8%,#8f5cff33,transparent 28%),radial-gradient(circle at 88% 12%,#23d7ff16,transparent 26%),linear-gradient(135deg,#04050b,#0d0f1a 58%,#05060b);color:var(--t);font-family:Segoe UI,system-ui,sans-serif}
.app{display:grid;grid-template-columns:285px 1fr;min-height:100vh}
aside{border-right:1px solid #8f5cff35;padding:18px 16px;background:#0007;position:sticky;top:0;height:100vh;overflow:auto;backdrop-filter:blur(10px)}
main{padding:24px}
.logo{width:76px;height:76px;border:1px solid #8f5cff66;border-radius:22px;display:grid;place-items:center;color:var(--p2);font-size:36px;font-weight:900;box-shadow:0 0 28px #8f5cff22;background:#8f5cff10}
h1{color:var(--p2);margin:14px 0 3px;font-size:28px;letter-spacing:.04em}
.sub,.small{color:var(--m);font-size:13px}
.nav{display:block;width:100%;text-align:left;margin:6px 0;padding:10px 11px;border:1px solid #8f5cff2c;border-radius:13px;background:#ffffff06;color:var(--t);font-weight:800;transition:.15s ease}
.nav.active,.nav:hover{background:#8f5cff24;border-color:#8f5cff6c;transform:translateX(2px)}
.nav.command{background:#8f5cff22;border-color:#8f5cff80;color:#fff;box-shadow:0 0 18px #8f5cff18}
.navbreak{height:1px;background:#8f5cff26;margin:12px 0}
.hero,.card,.ops{border:1px solid #8f5cff30;background:linear-gradient(180deg,#121420e6,#181b2ae8);border-radius:22px;padding:18px;margin-bottom:16px;box-shadow:0 0 28px #00000033}
.hero{background:radial-gradient(circle at top left,#8f5cff22,transparent 35%),linear-gradient(180deg,#121420,#181b2a)}
.hero h2{font-size:42px;margin:0 0 8px;letter-spacing:-.03em}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:16px}
.wide{grid-column:1/-1}
button,select{border:1px solid #8f5cff66;background:#8f5cff;color:#fff;border-radius:12px;padding:10px 13px;margin:5px 5px 0 0;font-weight:800}
button:hover{background:var(--ah)}
select,input,textarea{width:100%;background:#0b0d17;color:var(--t);border:1px solid #332a55;border-radius:14px;padding:12px}
textarea{min-height:92px;resize:vertical}
.status{white-space:pre-wrap;font-family:Consolas,monospace;font-size:13px;color:#e7dcff}
.page{display:none}.page.active{display:block}
.pill{display:inline-block;border:1px solid #8f5cff38;border-radius:999px;padding:7px 10px;margin:4px;color:var(--m)}
.ok{color:var(--g)}.warn{color:var(--w)}.bad{color:var(--r)}
.path{font-family:Consolas,monospace;color:var(--w);overflow-wrap:anywhere}
.row{display:grid;grid-template-columns:82px 1fr;gap:8px;border-bottom:1px solid #8f5cff18;padding:5px 0;font-family:Consolas,monospace;font-size:12px}
.lab{color:var(--m)}
.meter{height:10px;border:1px solid #332a55;border-radius:999px;overflow:hidden;background:#090b14}
.fill{height:100%;background:linear-gradient(90deg,var(--a),var(--c))}
.prof{min-height:210px}
.prof h3{color:var(--p2)}
.activeProf{border-color:#ffd16688;box-shadow:0 0 28px #ffd16618}
#chatLog{height:390px;overflow:auto;background:#080a12;border:1px solid #332a55;border-radius:16px;padding:14px}
.user{color:#bfefff}.fox{color:#efe9ff}.sys{color:var(--w)}
.pulse{display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--g);box-shadow:0 0 14px var(--g);animation:p 1.2s infinite}@keyframes p{50%{opacity:.3}}
table{width:100%;border-collapse:collapse;font-family:Consolas,monospace;font-size:13px}
td,th{border-bottom:1px solid #8f5cff18;padding:9px;text-align:left}
.link{background:transparent;border:0;color:var(--c);padding:0}.done{text-decoration:line-through;color:var(--m)}
.tl{border-left:3px solid var(--a);padding:8px 0 8px 12px;margin:8px 0;background:#8f5cff0d;border-radius:0 12px 12px 0}
.time{color:var(--w);font-family:Consolas,monospace;font-size:12px}
#toast{position:fixed;right:20px;bottom:20px;background:#121420;border:1px solid #8f5cff55;padding:12px 16px;border-radius:14px;display:none;max-width:520px;box-shadow:0 0 28px #0008}
.fleetcard{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:18px;padding:14px;min-height:112px;position:relative;overflow:hidden}
.fleetcard:before{content:'';position:absolute;inset:0 0 auto 0;height:3px;background:linear-gradient(90deg,var(--a),transparent)}
.fleetcard .depticon{font-size:24px;margin-bottom:8px}
.fleetcard.online{border-color:#42ff9e55}.fleetcard.staged{border-color:#ffd16644}.fleetcard.missing{border-color:#ff4d6d55}
.fleetcard h4{margin:0 0 8px;color:var(--p2)}
.fleetstatus{font-family:Consolas,monospace;font-size:12px;color:var(--m)}
.livegrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.livebox{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px}
.livebox .label{color:var(--m);font-size:12px}.livebox .value{font-size:24px;font-weight:900;color:#fff;margin-top:4px}
.eventbox{border-left:3px solid var(--w);padding:10px 0 10px 12px;margin-top:12px;background:#ffd1660b;border-radius:0 12px 12px 0}.promptitem{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px;margin:8px 0}.promptitem h4{margin:0 0 6px;color:var(--p2)}.promptpreview{color:var(--m);font-family:Consolas,monospace;font-size:12px;white-space:pre-wrap}.prompttag{display:inline-block;border:1px solid #8f5cff45;border-radius:999px;padding:3px 8px;margin:3px 4px 6px 0;color:var(--p2);font-size:12px}.promptactions button{padding:8px 10px;font-size:13px}
@media(max-width:900px){.app{grid-template-columns:1fr}aside{position:relative;height:auto}}

.libresult{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px;margin:8px 0}.libresult h4{margin:0 0 5px;color:var(--p2)}.libmeta{color:var(--m);font-family:Consolas,monospace;font-size:12px}.libbadge{display:inline-block;border:1px solid #8f5cff45;border-radius:999px;padding:3px 8px;margin:3px 4px 6px 0;color:var(--p2);font-size:12px}.previewbox{background:#070913;border:1px solid #8f5cff30;border-radius:16px;padding:14px;max-height:520px;overflow:auto;white-space:pre-wrap;font-family:Consolas,monospace;font-size:13px}.previewhead{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:10px}.copypath{color:var(--c);font-family:Consolas,monospace;font-size:12px;overflow-wrap:anywhere}.indexresult{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px;margin:8px 0}.indexresult h4{margin:0 0 5px;color:var(--p2)}.indexsnippet{background:#070913;border:1px solid #8f5cff22;border-radius:12px;padding:10px;margin-top:8px;color:#e7dcff;font-family:Consolas,monospace;font-size:12px;white-space:pre-wrap}.indexscore{color:var(--w);font-family:Consolas,monospace;font-size:12px}.askhint{color:var(--w);font-size:12px;margin-top:6px}.nfitem{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px;margin:8px 0}.nfitem h4{margin:0 0 6px;color:var(--p2)}.nftag{display:inline-block;border:1px solid #8f5cff45;border-radius:999px;padding:3px 8px;margin:3px 4px 6px 0;color:var(--p2);font-size:12px}.nfpreview{color:var(--m);font-family:Consolas,monospace;font-size:12px;white-space:pre-wrap}.nfcount{display:inline-block;border:1px solid #8f5cff45;border-radius:999px;padding:4px 9px;margin:3px;color:var(--p2);font-size:12px}.nfactions button{padding:8px 10px;font-size:13px}.tmevent{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px;margin:8px 0}.tmevent h4{margin:0 0 6px;color:var(--p2)}.tmtag{display:inline-block;border:1px solid #8f5cff45;border-radius:999px;padding:3px 8px;margin:3px 4px 6px 0;color:var(--p2);font-size:12px}.tmdetails{color:var(--m);white-space:pre-wrap;font-family:Consolas,monospace;font-size:12px}.tmactions button{padding:8px 10px;font-size:13px}.charcard{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px;margin:8px 0}.charcard h4{margin:0 0 6px;color:var(--p2)}.chartag{display:inline-block;border:1px solid #8f5cff45;border-radius:999px;padding:3px 8px;margin:3px 4px 6px 0;color:var(--p2);font-size:12px}.chardetails{color:var(--m);white-space:pre-wrap;font-family:Consolas,monospace;font-size:12px}.charactions button{padding:8px 10px;font-size:13px}.mysterycard{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px;margin:8px 0}.mysterycard h4{margin:0 0 6px;color:var(--p2)}.mystag{display:inline-block;border:1px solid #8f5cff45;border-radius:999px;padding:3px 8px;margin:3px 4px 6px 0;color:var(--p2);font-size:12px}.mystatus-unresolved{border-color:#ffd16666;color:#ffd166}.mystatus-solved{border-color:#42ff9e66;color:#42ff9e}.mystatus-red{border-color:#ff4d6d66;color:#ff4d6d}.mysdetails{color:var(--m);white-space:pre-wrap;font-family:Consolas,monospace;font-size:12px}.mysactions button{padding:8px 10px;font-size:13px}.loccard,.artcard{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px;margin:8px 0}.loccard h4,.artcard h4{margin:0 0 6px;color:var(--p2)}.loctag,.arttag{display:inline-block;border:1px solid #8f5cff45;border-radius:999px;padding:3px 8px;margin:3px 4px 6px 0;color:var(--p2);font-size:12px}.locdetails,.artdetails{color:var(--m);white-space:pre-wrap;font-family:Consolas,monospace;font-size:12px}.locactions button,.artactions button{padding:8px 10px;font-size:13px}.codexdash{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:10px 0}.codexbox{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px}.codexbox .label{color:var(--m);font-size:12px}.codexbox .value{font-size:24px;font-weight:900;color:#fff;margin-top:4px}.readiness{border-left:3px solid var(--w);padding:10px 0 10px 12px;margin-top:12px;background:#ffd1660b;border-radius:0 12px 12px 0}.scenecard{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px;margin:8px 0}.scenecard h4{margin:0 0 6px;color:var(--p2)}.scenetag{display:inline-block;border:1px solid #8f5cff45;border-radius:999px;padding:3px 8px;margin:3px 4px 6px 0;color:var(--p2);font-size:12px}.scenedetails{color:var(--m);white-space:pre-wrap;font-family:Consolas,monospace;font-size:12px}.sceneactions button{padding:8px 10px;font-size:13px}.extcard{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px;margin:8px 0}.extcard h4{margin:0 0 6px;color:var(--p2)}.exttag{display:inline-block;border:1px solid #8f5cff45;border-radius:999px;padding:3px 8px;margin:3px 4px 6px 0;color:var(--p2);font-size:12px}.extmeta{color:var(--m);white-space:pre-wrap;font-family:Consolas,monospace;font-size:12px}.extactions button{padding:8px 10px;font-size:13px}.disabledmod{opacity:.55}.repairbox{background:#050713;border:1px solid #8f5cff45;border-radius:14px;padding:12px;white-space:pre-wrap;overflow:auto;max-height:380px;color:#eae7ff;font-family:Consolas,monospace;font-size:12px}.moddash{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:10px 0}.modbox{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px}.modbox .label{color:var(--m);font-size:12px}.modbox .value{font-size:24px;font-weight:900;color:#fff;margin-top:4px}.modhint{border-left:3px solid var(--w);padding:10px 0 10px 12px;margin-top:12px;background:#ffd1660b;border-radius:0 12px 12px 0}.modok{border-left-color:var(--ok)!important;background:#00e6860a}.modwarn{border-left-color:var(--bad)!important;background:#ff4d6d0b}.scanbox{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:10px 0}.scanmetric{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px}.scanmetric .label{color:var(--m);font-size:12px}.scanmetric .value{font-size:24px;font-weight:900;color:#fff;margin-top:4px}.scanlist{background:#050713;border:1px solid #8f5cff45;border-radius:14px;padding:12px;white-space:pre-wrap;overflow:auto;max-height:420px;color:#eae7ff;font-family:Consolas,monospace;font-size:12px}.docstatusgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:10px 0}.docstat{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px}.docstat .label{color:var(--m);font-size:12px}.docstat .value{font-size:24px;font-weight:900;color:#fff;margin-top:4px}.docrow{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:14px;padding:10px;margin:8px 0}.docrow.good{border-left:3px solid var(--ok)}.docrow.bad{border-left:3px solid var(--bad)}.buildgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:10px 0}.buildmetric{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px}.buildmetric .label{color:var(--m);font-size:12px}.buildmetric .value{font-size:24px;font-weight:900;color:#fff;margin-top:4px}.checkrow{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:14px;padding:10px;margin:8px 0}.checkrow.pass{border-left:3px solid var(--ok)}.checkrow.fail{border-left:3px solid var(--bad)}.envgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:10px 0}.envmetric{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px}.envmetric .label{color:var(--m);font-size:12px}.envmetric .value{font-size:24px;font-weight:900;color:#fff;margin-top:4px}.envrow{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:14px;padding:10px;margin:8px 0}.envrow.pass{border-left:3px solid var(--ok)}.envrow.fail{border-left:3px solid var(--bad)}.envrow.optional{border-left:3px solid var(--w)}.portablegrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:12px;margin:10px 0}.portablemetric{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px}.portablemetric .label{color:var(--m);font-size:12px}.portablemetric .value{font-size:24px;font-weight:900;color:#fff;margin-top:4px}.portrow{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:14px;padding:10px;margin:8px 0}.portrow.pass{border-left:3px solid var(--ok)}.portrow.warn{border-left:3px solid var(--w)}.portrow.fail{border-left:3px solid var(--bad)}.modelgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:12px;margin:10px 0}.modelmetric{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px}.modelmetric .label{color:var(--m);font-size:12px}.modelmetric .value{font-size:24px;font-weight:900;color:#fff;margin-top:4px}.modelrow{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:14px;padding:10px;margin:8px 0}.modelrow.safe{border-left:3px solid var(--ok)}.modelrow.info{border-left:3px solid var(--m)}.modelrow.review{border-left:3px solid var(--w)}.modelrow.warn{border-left:3px solid var(--bad)}.repairrow{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:14px;padding:12px;margin:10px 0}.repairrow.available{border-left:3px solid var(--ok)}.repairrow.blocked{border-left:3px solid var(--bad)}.repairrow .repairtitle{font-weight:900;color:#fff}.repairrow .risk{color:var(--m);font-size:12px}.repairrow button{margin-top:8px}.historygrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:10px 0}.historymetric{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px}.historymetric .label{color:var(--m);font-size:12px}.historymetric .value{font-size:24px;font-weight:900;color:#fff;margin-top:4px}.histrow{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:14px;padding:10px;margin:8px 0}.histrow.ok{border-left:3px solid var(--ok)}.histrow.fail{border-left:3px solid var(--bad)}.histrow.info{border-left:3px solid var(--m)}.verifybadge{display:inline-block;border-radius:999px;padding:3px 8px;font-size:11px;font-weight:900;margin-left:6px}.verifybadge.pass{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.verifybadge.fail{background:#ff5d5d22;color:#ffb0b0;border:1px solid #ff5d5d55}.verifybadge.none{background:#ffffff12;color:#c9bfdc;border:1px solid #ffffff22}.checkline{font-size:12px;color:#d8d0e8;margin-left:10px}.backupbadge{display:inline-block;border-radius:999px;padding:3px 8px;font-size:11px;font-weight:900;margin-left:6px}.backupbadge.assoc{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.backupbadge.old{background:#ffffff12;color:#c9bfdc;border:1px solid #ffffff22}.vaultpath{font-size:12px;color:#d8d0e8;word-break:break-all}.vaultmetric{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:16px;padding:12px}.vaultmetric .label{color:var(--m);font-size:12px}.vaultmetric .value{font-size:24px;font-weight:900;color:#fff;margin-top:4px}.timestampnote{font-size:12px;color:#c9bfdc;border-left:3px solid #8f5cff77;padding-left:8px;margin-top:6px}.riskbadge{display:inline-block;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:900}.riskbadge.low{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.riskbadge.medium{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.riskbadge.blocked{background:#ff5d5d22;color:#ffb0b0;border:1px solid #ff5d5d55}.diffbox{white-space:pre-wrap;font-family:ui-monospace,Consolas,monospace}.gatebadge{display:inline-block;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:900;margin-left:6px}.gatebadge.pass{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.gatebadge.warn{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.gatebadge.block{background:#ff5d5d22;color:#ffb0b0;border:1px solid #ff5d5d55}.gatebadge.info{background:#8f5cff22;color:#e2d4ff;border:1px solid #8f5cff55}.phrasebox{font-family:ui-monospace,Consolas,monospace;font-size:16px;border:1px solid #8f5cff55;background:#00000033;border-radius:14px;padding:12px;color:#fff}.packagebadge{display:inline-block;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:900;margin-left:6px}.packagebadge.ok{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.packagebadge.problem{background:#ff5d5d22;color:#ffb0b0;border:1px solid #ff5d5d55}.packagefile{font-size:12px;color:#d8d0e8;word-break:break-all;margin-left:8px}.finalbadge{display:inline-block;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:900;margin-left:6px}.finalbadge.pass{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.finalbadge.warn{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.finalbadge.block{background:#ff5d5d22;color:#ffb0b0;border:1px solid #ff5d5d55}.finalphrase{font-family:ui-monospace,Consolas,monospace;font-size:15px;border:1px solid #8f5cff55;background:#00000033;border-radius:14px;padding:12px;color:#fff}.auditbadge{display:inline-block;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:900;margin-left:6px}.auditbadge.intact{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.auditbadge.attention{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.hashline{font-family:ui-monospace,Consolas,monospace;font-size:12px;word-break:break-all;color:#d8d0e8}.rollbackbadge{display:inline-block;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:900;margin-left:6px}.rollbackbadge.pass{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.rollbackbadge.warn{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.rollbackbadge.block{background:#ff5d5d22;color:#ffb0b0;border:1px solid #ff5d5d55}.rollbackphrase{font-family:ui-monospace,Consolas,monospace;font-size:15px;border:1px solid #8f5cff55;background:#00000033;border-radius:14px;padding:12px;color:#fff}.rbauditbadge{display:inline-block;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:900;margin-left:6px}.rbauditbadge.intact{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.rbauditbadge.attention{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.rbauditHash{font-family:ui-monospace,Consolas,monospace;font-size:12px;word-break:break-all;color:#d8d0e8}.tlbadge{display:inline-block;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:900;margin-left:6px}.tlbadge.intact{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.tlbadge.attention{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.tlbadge.evidence{background:#8f5cff22;color:#d8c7ff;border:1px solid #8f5cff55}.tlbadge.superseded_by_rollback{background:#66c7ff22;color:#b9e8ff;border:1px solid #66c7ff55}.tlbadge.other{background:#ffffff12;color:#ddd;border:1px solid #ffffff22}.timelineHash{font-family:ui-monospace,Consolas,monospace;font-size:12px;word-break:break-all;color:#d8d0e8}.timelineEvent{border-left:3px solid #8f5cff;padding-left:12px}.recoveryHealthBadge{display:inline-block;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:900;margin-bottom:8px}.recoveryHealthBadge.healthy{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.recoveryHealthBadge.warn{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.recoveryMiniGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-top:10px}.recoveryMini{border:1px solid #ffffff18;border-radius:14px;padding:10px;background:#00000022}.recoveryMini .label{font-size:11px;color:#aaa}.recoveryMini .value{font-size:18px;font-weight:900;color:#fff}.recoveryPath{font-size:12px;color:#cfc7df;word-break:break-all;margin-top:8px}.repairShopBadge{display:inline-block;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:900;margin-bottom:8px}.repairShopBadge.healthy{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.repairShopBadge.warn{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.repairShopGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-top:10px}.repairShopMetric{border:1px solid #ffffff18;border-radius:14px;padding:10px;background:#00000022}.repairShopMetric .label{font-size:11px;color:#aaa}.repairShopMetric .value{font-size:18px;font-weight:900;color:#fff}.repairShopPath{font-size:12px;color:#cfc7df;word-break:break-all;margin-top:8px}.actionPill{display:inline-block;border-radius:999px;padding:3px 9px;font-size:11px;font-weight:900;margin-left:6px}.actionPill.available{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.actionPill.blocked{background:#ffffff12;color:#aaa;border:1px solid #ffffff22}.detailBadge{display:inline-block;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:900;margin-bottom:8px}.detailBadge.verified{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.detailBadge.legacy_ok{background:#66c7ff22;color:#b9e8ff;border:1px solid #66c7ff55}.detailBadge.failed{background:#ff5d5d22;color:#ffb0b0;border:1px solid #ff5d5d55}.detailBadge.attention{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.detailGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-top:10px}.detailMetric{border:1px solid #ffffff18;border-radius:14px;padding:10px;background:#00000022}.detailMetric .label{font-size:11px;color:#aaa}.detailMetric .value{font-size:16px;font-weight:900;color:#fff}.detailHash{font-family:ui-monospace,Consolas,monospace;font-size:12px;word-break:break-all;color:#d8d0e8}.repairCardBadge{display:inline-block;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:900;margin-bottom:8px}.repairCardBadge.healthy{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.repairCardBadge.warn{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.repairCardGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:10px;margin-top:10px}.repairCardMetric{border:1px solid #ffffff18;border-radius:14px;padding:10px;background:#00000022}.repairCardMetric .label{font-size:11px;color:#aaa}.repairCardMetric .value{font-size:18px;font-weight:900;color:#fff}.repairCardPath{font-size:12px;color:#cfc7df;word-break:break-all;margin-top:8px}.ticketBadge{display:inline-block;border-radius:999px;padding:4px 10px;font-size:11px;font-weight:900;margin-right:6px}.ticketBadge.critical{background:#ff336622;color:#ffb0c4;border:1px solid #ff336655}.ticketBadge.high{background:#ff5d5d22;color:#ffb0b0;border:1px solid #ff5d5d55}.ticketBadge.medium{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.ticketBadge.low{background:#66c7ff22;color:#b9e8ff;border:1px solid #66c7ff55}.ticketBadge.info{background:#ffffff12;color:#d8d0e8;border:1px solid #ffffff24}.ticketBadge.healthy{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.ticketGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:10px;margin-top:10px}.ticketMetric{border:1px solid #ffffff18;border-radius:14px;padding:10px;background:#00000022}.ticketMetric .label{font-size:11px;color:#aaa}.ticketMetric .value{font-size:18px;font-weight:900;color:#fff}.ticketRow{border:1px solid #8f5cff2f;background:#ffffff05;border-radius:14px;padding:10px;margin:8px 0}.ticketRow.critical,.ticketRow.high{border-left:3px solid var(--bad)}.ticketRow.medium,.ticketRow.low{border-left:3px solid var(--w)}.ticketRow.healthy{border-left:3px solid var(--ok)}.ticketPath{font-size:12px;color:#cfc7df;word-break:break-all;margin-top:6px}.ticketDetailBadge{display:inline-block;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:900;margin-bottom:8px}.ticketDetailBadge.healthy{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.ticketDetailBadge.available_action{background:#66c7ff22;color:#b9e8ff;border:1px solid #66c7ff55}.ticketDetailBadge.informational{background:#ffffff12;color:#d8d0e8;border:1px solid #ffffff22}.ticketDetailBadge.needs_attention,.ticketDetailBadge.open{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.ticketDetailGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:10px;margin-top:10px}.ticketDetailMetric{border:1px solid #ffffff18;border-radius:14px;padding:10px;background:#00000022}.ticketDetailMetric .label{font-size:11px;color:#aaa}.ticketDetailMetric .value{font-size:17px;font-weight:900;color:#fff}.ticketDetailPath{font-size:12px;color:#cfc7df;word-break:break-all;margin-top:8px}.bridgeBadge{display:inline-block;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:900;margin-bottom:8px}.bridgeBadge.ready{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.bridgeBadge.info{background:#66c7ff22;color:#b9e8ff;border:1px solid #66c7ff55}.bridgeBadge.warn{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.bridgeGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:10px}.bridgeMetric{border:1px solid #ffffff18;border-radius:14px;padding:10px;background:#00000022}.bridgeMetric .label{font-size:11px;color:#aaa}.bridgeMetric .value{font-size:16px;font-weight:900;color:#fff}.repairrow.recommended{border-color:#36d399aa!important;box-shadow:0 0 0 1px #36d39955 inset}.recommendTag{display:inline-block;border-radius:999px;padding:4px 10px;background:#36d39922;color:#7fffd4;border:1px solid #36d39955;font-size:11px;font-weight:900;margin-bottom:8px}.sessionBadge{display:inline-block;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:900;margin-bottom:8px}.sessionBadge.healthy{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.sessionBadge.warn{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.sessionGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-top:10px}.sessionMetric{border:1px solid #ffffff18;border-radius:14px;padding:10px;background:#00000022}.sessionMetric .label{font-size:11px;color:#aaa}.sessionMetric .value{font-size:18px;font-weight:900;color:#fff}.sessionPath{font-size:12px;color:#cfc7df;word-break:break-all;margin-top:8px}.freezeBadge{display:inline-block;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:900;margin-bottom:8px}.freezeBadge.healthy{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.freezeBadge.warn{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.freezeGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-top:10px}.freezeMetric{border:1px solid #ffffff18;border-radius:14px;padding:10px;background:#00000022}.freezeMetric .label{font-size:11px;color:#aaa}.freezeMetric .value{font-size:18px;font-weight:900;color:#fff}.freezePath{font-size:12px;color:#cfc7df;word-break:break-all;margin-top:8px}.ccBadge{display:inline-block;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:900;margin-bottom:8px}.ccBadge.clear{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.ccBadge.advisory{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.ccBadge.bad{background:#ff557722;color:#ff9aaa;border:1px solid #ff557755}.ccGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-top:10px}.ccMetric{border:1px solid #ffffff18;border-radius:14px;padding:10px;background:#00000022}.ccMetric .label{font-size:11px;color:#aaa}.ccMetric .value{font-size:18px;font-weight:900;color:#fff}.ccPath{font-size:12px;color:#cfc7df;word-break:break-all;margin-top:8px}.foundationCard{border:1px solid #ffffff18;border-radius:16px;padding:12px;margin:10px 0;background:#00000022}.foundationCard.clear{border-color:#36d39955}.foundationCard.advisory{border-color:#ffcc6655}.foundationCard.needs_attention{border-color:#ff557755}.cmdDetailBadge{display:inline-block;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:900;margin-bottom:8px}.cmdDetailBadge.clear{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.cmdDetailBadge.advisory{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.cmdDetailBadge.bad{background:#ff557722;color:#ff9aaa;border:1px solid #ff557755}.cmdMetric{border:1px solid #ffffff18;border-radius:14px;padding:10px;margin:8px 0;background:#00000022}.cmdMetric .k{font-size:12px;color:#aaa}.cmdMetric .v{font-weight:800;color:#fff;word-break:break-word}.cmdPath{font-size:12px;color:#cfc7df;word-break:break-all;margin-top:6px}.ccDashBadge{display:inline-block;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:900;margin-bottom:8px}.ccDashBadge.clear{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.ccDashBadge.advisory{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.ccDashBadge.bad{background:#ff557722;color:#ff9aaa;border:1px solid #ff557755}.ccDashGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-top:10px}.ccDashMetric{border:1px solid #ffffff18;border-radius:14px;padding:10px;background:#00000022}.ccDashMetric .label{font-size:11px;color:#aaa}.ccDashMetric .value{font-size:18px;font-weight:900;color:#fff}.ccDashLine{font-size:12px;color:#cfc7df;word-break:break-word;margin-top:8px}.archiveBadge{display:inline-block;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:900;margin-bottom:8px}.archiveBadge.clear{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.archiveBadge.advisory{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.archiveBadge.bad{background:#ff557722;color:#ff9aaa;border:1px solid #ff557755}.archiveGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-top:10px}.archiveMetric{border:1px solid #ffffff18;border-radius:14px;padding:10px;background:#00000022}.archiveMetric .label{font-size:11px;color:#aaa}.archiveMetric .value{font-size:18px;font-weight:900;color:#fff}.archivePath{font-size:12px;color:#cfc7df;word-break:break-all;margin-top:8px}.cmdFreezeBadge{display:inline-block;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:900;margin-bottom:8px}.cmdFreezeBadge.clear{background:#36d39922;color:#7fffd4;border:1px solid #36d39955}.cmdFreezeBadge.advisory{background:#ffcc6622;color:#ffd99a;border:1px solid #ffcc6655}.cmdFreezeBadge.bad{background:#ff557722;color:#ff9aaa;border:1px solid #ff557755}.cmdFreezeGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-top:10px}.cmdFreezeMetric{border:1px solid #ffffff18;border-radius:14px;padding:10px;background:#00000022}.cmdFreezeMetric .label{font-size:11px;color:#aaa}.cmdFreezeMetric .value{font-size:18px;font-weight:900;color:#fff}.cmdFreezePath{font-size:12px;color:#cfc7df;word-break:break-all;margin-top:8px}.writerBadge{display:inline-block;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:900;margin-bottom:8px;background:#a855f722;color:#e9d5ff;border:1px solid #a855f755}.writerGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-top:10px}.writerMetric{border:1px solid #ffffff18;border-radius:14px;padding:10px;background:#00000022}.writerMetric .label{font-size:11px;color:#aaa}.writerMetric .value{font-size:18px;font-weight:900;color:#fff}.writerPath{font-size:12px;color:#cfc7df;word-break:break-all;margin-top:8px}.writerModule{border:1px solid #a855f733;border-radius:16px;padding:12px;margin:10px 0;background:#14001f33}.storyBadge{display:inline-block;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:900;margin-bottom:8px;background:#8b5cf622;color:#ddd6fe;border:1px solid #8b5cf655}.storyGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-top:10px}.storyMetric{border:1px solid #ffffff18;border-radius:14px;padding:10px;background:#00000022}.storyMetric .label{font-size:11px;color:#aaa}.storyMetric .value{font-size:18px;font-weight:900;color:#fff}.storyPath{font-size:12px;color:#cfc7df;word-break:break-all;margin-top:8px}.storyCard{border:1px solid #8b5cf633;border-radius:16px;padding:12px;margin:10px 0;background:#16002433}.manifestBadge{display:inline-block;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:900;margin-bottom:8px;background:#7c3aed22;color:#ddd6fe;border:1px solid #7c3aed55}.manifestGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-top:10px}.manifestMetric{border:1px solid #ffffff18;border-radius:14px;padding:10px;background:#00000022}.manifestMetric .label{font-size:11px;color:#aaa}.manifestMetric .value{font-size:18px;font-weight:900;color:#fff}.manifestPath{font-size:12px;color:#cfc7df;word-break:break-all;margin-top:8px}.manifestCard{border:1px solid #7c3aed33;border-radius:16px;padding:12px;margin:10px 0;background:#12002033}.gateBadge{display:inline-block;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:900;margin-bottom:8px;background:#6d28d922;color:#ddd6fe;border:1px solid #6d28d955}.gateGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-top:10px}.gateMetric{border:1px solid #ffffff18;border-radius:14px;padding:10px;background:#00000022}.gateMetric .label{font-size:11px;color:#aaa}.gateMetric .value{font-size:18px;font-weight:900;color:#fff}.gatePath{font-size:12px;color:#cfc7df;word-break:break-all;margin-top:8px}.gateCard{border:1px solid #6d28d933;border-radius:16px;padding:12px;margin:10px 0;background:#12002033}</style></head><body><div class=app><aside><div class=logo>K</div><h1>KAYOCK</h1><div class=sub>Command OS · FOXAI Core</div><button class="nav command active" onclick="pg('dash',this)">🚀 Command Bridge</button><button class=nav onclick="pg('commandcenter',this)">🛰️ Command Center</button><button class=nav onclick="pg('commanddetail',this)">🔎 Command Detail</button><button class=nav onclick="pg('commandarchive',this)">🗄️ Command Archive</button><button class=nav onclick="pg('commandfreeze',this)">🧊 Command Freeze</button><button class=nav onclick="pg('kayockwriter',this)">✍️ Kayock Writer</button><button class=nav onclick="pg('storyforge',this)">📚 Story Forge</button><button class=nav onclick="pg('storymanifest',this)">🧾 Story Manifest</button><button class=nav onclick="pg('projectgate',this)">🚪 Project Gate</button><div class=navbreak></div><button class=nav onclick="pg('academy',this)">🎓 Academy</button><button class=nav onclick="pg('novelforge',this)">📖 Novel Forge</button><button class=nav onclick="pg('prompts',this)">✍️ PromptSmith</button><button class=nav onclick="pg('creative',this)">🎨 Creative Studio</button><button class=nav onclick="pg('library',this)">📚 Iron Library</button><button class=nav onclick="pg('mission',this)">🤖 Artificial Minds</button><button class=nav onclick="pg('projects',this)">🗂 Projects</button><button class=nav onclick="pg('memory',this)">🧭 Mission Memory</button><button class=nav onclick="pg('repair',this)">🔧 Repair Bay</button><button class=nav onclick="pg('extensions',this)">🧩 Extensions</button><button class=nav onclick="pg('scanbridge',this)">📡 Scan Bridge</button><button class=nav onclick="pg('projectgen',this)">🧾 Project Docs</button><button class=nav onclick="pg('buildverify',this)">🧪 Build Verify</button><button class=nav onclick="pg('envverify',this)">🧰 Env Verify</button><button class=nav onclick="pg('portable',this)">🧳 Portable Ready</button><button class=nav onclick="pg('modelcheck',this)">🧬 Model Check</button><button class=nav onclick="pg('repairactions',this)">🛠️ Repair Actions</button><button class=nav onclick="pg('repairhistory',this)">📜 Repair History</button><button class=nav onclick="pg('repairops',this)">🏪 Repair Shop</button><button class=nav onclick="pg('repairdetail',this)">🔎 Action Detail</button><button class=nav onclick="pg('repairtickets',this)">🎫 Repair Tickets</button><button class=nav onclick="pg('repairticketdetail',this)">📋 Ticket Detail</button><button class=nav onclick="pg('ticketbridge',this)">🔗 Ticket Bridge</button><button class=nav onclick="pg('repairsession',this)">🧾 Shop Session</button><button class=nav onclick="pg('repairfreeze',this)">🧊 Milestone Freeze</button><button class=nav onclick="pg('backupvault',this)">🗄️ Backup Vault</button><button class=nav onclick="pg('restorepreview',this)">🧭 Restore Preview</button><button class=nav onclick="pg('restoregate',this)">🚧 Restore Gate</button><button class=nav onclick="pg('restorestaging',this)">📦 Restore Staging</button><button class=nav onclick="pg('stagingpackages',this)">🧾 Staging Packages</button><button class=nav onclick="pg('restorefinal',this)">✅ Restore Final Check</button><button class=nav onclick="pg('restoreaction',this)">♻️ Restore Action</button><button class=nav onclick="pg('restoreaudit',this)">🧪 Restore Audit</button><button class=nav onclick="pg('rollbackpreview',this)">↩️ Rollback Preview</button><button class=nav onclick="pg('rollbackaction',this)">⏪ Rollback Action</button><button class=nav onclick="pg('rollbackaudit',this)">🧾 Rollback Audit</button><button class=nav onclick="pg('recoverytimeline',this)">🕰️ Recovery Timeline</button><div class=navbreak></div><button class=nav onclick="pg('logs',this)">📜 Captain's Log</button><button class=nav onclick="pg('settings',this)">⚙ Settings</button><div class=ops><div class=row><div class=lab>Operator</div><div>Eric Fox</div></div><div class=row><div class=lab>Professor</div><div id=ap>Agent Fox</div></div><div class=row><div class=lab>Project</div><div id=apro>None</div></div><div class=row><div class=lab>Mission</div><div id=ms>READY</div></div><div class=row><div class=lab>Model</div><div id=am>None</div></div><div class=row><div class=lab>Runtime</div><div id=rt>Checking</div></div></div><div id=quick></div><div class=ops><div class=row><div class=lab>CPU</div><div id=cpu>?</div></div><div class=row><div class=lab>RAM</div><div id=ram>?</div></div><div class=meter><div id=ramm class=fill></div></div></div></aside><main>
<section id=dash class="page active"><div class=hero><h2>Welcome back, Commander.</h2><p>Kayock Command OS is online. FOXAI Core, Mission Memory, and the Bridge are standing by.</p></div><div class=grid>
<div class="card wide" id=commandCenterDashCard><h3>🛰️ Command Center</h3><div id=commandCenterDashStatus class=status>Command Center dashboard not loaded yet.</div><div id=commandCenterDashBody class=status>Loading foundation health...</div><button onclick="loadCommandCenterDashboard(false)">Refresh Command Center</button><button onclick="loadCommandCenterDashboard(true)">Export Card Report</button><button onclick="go('commandcenter')">Open Command Center</button><button onclick="go('commanddetail')">Open Command Detail</button><button onclick="sendCommandCenterDashboardToMission()">Send to Mission</button></div>
<div class=card><h3>Resume Mission</h3><div id=resume class=status>No active mission.</div><button onclick="goMemory()">Open Mission Memory</button><button onclick="resumeMission()">Resume in Console</button></div><div class=card><h3>Projects</h3><button onclick="go('projects')">Open Projects</button></div><div class=card><h3>Artificial Minds</h3><button onclick="go('mission')">Open Mission Console</button></div><div class=card><h3>PromptSmith</h3><button onclick="go('prompts')">Open PromptSmith</button></div><div class=card><h3>Novel Forge</h3><button onclick="go('novelforge')">Open Novel Forge</button></div><div class="card wide"><h3>Live Command Bridge</h3><div id=bridgeLive class=status>Loading Bridge Feed...</div></div><div class="card wide"><h3>Recovery Foundation</h3><div id=recoveryDashCard class=status>Loading recovery health...</div><button onclick="loadRecoveryDashboard()">Refresh Recovery Health</button><button onclick="go('recoverytimeline')">Open Recovery Timeline</button><button onclick="sendRecoveryDashboardToMission()">Send Recovery Health to Mission</button></div><div class="card wide"><h3>Repair Shop</h3><div id=repairShopDashCard class=status>Loading Repair Shop health...</div><button onclick="loadRepairShopDashboardCard()">Refresh Repair Shop</button><button onclick="go('repairops')">Open Repair Shop</button><button onclick="go('repairdetail')">Open Action Detail</button><button onclick="sendRepairShopDashboardCardToMission()">Send Repair Shop Health to Mission</button></div><div class="card wide"><h3>Department Fleet</h3><div id=deptcards class=grid>Loading departments...</div></div><div class="card wide"><h3>Status</h3><div id=status class=status>Loading...</div></div></div></section>
<section id=projects class=page><div class=hero><h2>Project Workspace</h2><p>Create and resume local workspaces.</p></div><div class=grid><div class=card><h3>New Project</h3><input id=newProject placeholder="Project name"><button onclick="createProject()">Create</button></div><div class=card><h3>Projects Folder</h3><button onclick="api('/api/open/projects')">Open Folder</button><button onclick="loadProjects()">Refresh</button></div><div class="card wide"><h3>Available Projects</h3><div id=plist class=status>Loading...</div></div><div class="card wide"><h3>Project Notes</h3><div class=small>Active: <span id=pnoteTitle class=path>None</span></div><textarea id=pnote></textarea><button onclick="saveNote()">Save Note</button><button onclick="askProject()">Ask Agent About Project</button></div></div></section>
<section id=memory class=page><div class=hero><h2>Mission Memory</h2><p>Project state, tasks, and timeline persist on the USB.</p></div><div class=grid><div class="card wide"><h3>Mission State</h3><div id=memstate class=status>No active mission.</div><button onclick="resumeMission()">Resume Mission</button><button onclick="api('/api/memory/save');loadMemory()">Save Current State</button></div><div class=card><h3>Add Task</h3><input id=task placeholder="Task"><button onclick="addTask()">Add</button></div><div class="card wide"><h3>Tasks</h3><div id=tasks class=status>No tasks.</div></div><div class="card wide"><h3>Timeline</h3><div id=timeline class=status>No timeline.</div></div></div></section>
<section id=mission class=page><div class=hero><h2>Artificial Minds</h2><p>Talk to the active professor using your local GGUF model.</p></div><div class="card wide"><h3><span id=pulse></span> <span id=mtitle>Agent Fox</span></h3><select id=model><option>Loading...</option></select><br><button onclick="startChat()">Start Chat Engine</button><button onclick="api('/api/chat/stop')">Stop Chat Engine</button><button onclick="api('/api/chat/reset');chat.innerHTML='Mission console reset.\n'">Reset</button><div id=chatLog class=status>Mission console ready.\n</div><textarea id=input placeholder="Ask the active professor..." onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send()}" ></textarea><button onclick="send()">Send</button></div></section>

<section id=commandcenter class=page><div class=hero><h2>Command Center Foundation</h2><p>One command screen for the major Kayock Command OS foundations: Repair Shop, Recovery, Build, Environment, Portable readiness, Models, Scan Bridge, Project Docs, and Extensions.</p></div><div class=grid><div class="card wide"><h3>Command Center Controls</h3><button onclick="loadCommandCenter(false)">Load Command Center</button><button onclick="loadCommandCenter(true)">Export Command Center Report</button><button onclick="api('/api/open/command_center_reports')">Open Command Center Reports</button><button onclick="go('repairfreeze')">Open Repair Shop Freeze</button><button onclick="go('recoverytimeline')">Open Recovery Timeline</button><button onclick="sendCommandCenterToMission()">Send Command Center to Mission</button><div id=commandCenterStatus class=status>No Command Center report loaded yet.</div></div><div class="card wide"><h3>Foundation Summary</h3><div id=commandCenterSummary class=status>No summary yet.</div></div><div class="card wide"><h3>Foundation Health</h3><div id=commandCenterFoundations class=scanlist>No foundation data loaded yet.</div></div><div class="card wide"><h3>Attention</h3><div id=commandCenterAttention class=scanlist>No attention items loaded yet.</div></div><div class="card wide"><h3>Advisories</h3><div id=commandCenterAdvisories class=scanlist>No advisories loaded yet.</div></div><div class="card wide"><h3>Recommended Next</h3><div id=commandCenterNext class=scanlist>No recommendations loaded yet.</div></div><div class="card wide"><h3>Safety Contract</h3><div id=commandCenterSafety class=status>No safety contract loaded yet.</div></div></div></section>


<section id=commanddetail class=page><div class=hero><h2>Command Center Detail Viewer</h2><p>Inspect one foundation from the Command Center board: metrics, status, advisory reason, source page, source endpoint, related paths, and safety contract.</p></div><div class=grid><div class="card wide"><h3>Detail Controls</h3><button onclick="loadCommandDetailList()">Load Foundation List</button><select id=commandDetailSelect><option value="env_verify">env_verify</option></select><button onclick="loadCommandDetail(false)">Load Detail</button><button onclick="loadCommandDetail(true)">Export Detail</button><button onclick="openCommandDetailRelatedPage()">Open Related Page</button><button onclick="api('/api/open/command_center_detail_reports')">Open Detail Reports</button><button onclick="sendCommandDetailToMission()">Send Detail to Mission</button><div id=commandDetailStatus class=status>No foundation detail loaded yet.</div></div><div class="card wide"><h3>Foundation Detail</h3><div id=commandDetailSummary class=status>No detail yet.</div></div><div class="card wide"><h3>Metrics</h3><div id=commandDetailMetrics class=scanlist>No metrics loaded yet.</div></div><div class="card wide"><h3>Advisory / Attention</h3><div id=commandDetailSignal class=scanlist>No advisory or attention loaded yet.</div></div><div class="card wide"><h3>Related Paths</h3><div id=commandDetailPaths class=scanlist>No related paths loaded yet.</div></div><div class="card wide"><h3>Detail Checks</h3><div id=commandDetailChecks class=scanlist>No checks loaded yet.</div></div><div class="card wide"><h3>Safety Contract</h3><div id=commandDetailSafety class=status>No safety contract loaded yet.</div></div></div></section>


<section id=commandarchive class=page><div class=hero><h2>Command Center History / Archive</h2><p>Browse prior Command Center reports, dashboard-card reports, and foundation-detail reports. This is the memory shelf for Command Center health over time.</p></div><div class=grid><div class="card wide"><h3>Archive Controls</h3><button onclick="loadCommandArchive(false)">Load Archive</button><button onclick="loadCommandArchive(true)">Export Archive Report</button><button onclick="api('/api/open/command_center_archive_reports')">Open Archive Reports</button><button onclick="api('/api/open/command_center_reports')">Open Foundation Reports</button><button onclick="api('/api/open/command_center_detail_reports')">Open Detail Reports</button><button onclick="api('/api/open/command_center_card_reports')">Open Card Reports</button><button onclick="sendCommandArchiveToMission()">Send Archive to Mission</button><div id=commandArchiveStatus class=status>No archive loaded yet.</div></div><div class="card wide"><h3>Archive Summary</h3><div id=commandArchiveSummary class=status>No summary yet.</div></div><div class="card wide"><h3>Health Trend</h3><div id=commandArchiveTrend class=scanlist>No trend loaded yet.</div></div><div class="card wide"><h3>Report Timeline</h3><div id=commandArchiveTimeline class=scanlist>No timeline loaded yet.</div></div><div class="card wide"><h3>Latest Reports</h3><div id=commandArchiveLatest class=scanlist>No latest report data loaded yet.</div></div><div class="card wide"><h3>Safety Contract</h3><div id=commandArchiveSafety class=status>No safety contract loaded yet.</div></div></div></section>


<section id=commandfreeze class=page><div class=hero><h2>Command Center Milestone Freeze</h2><p>Formal freeze report for the v10.10.x Command Center foundation: proven modules, advisories, safety contract, and readiness to move to the next milestone.</p></div><div class=grid><div class="card wide"><h3>Freeze Controls</h3><button onclick="loadCommandFreeze(false)">Load Freeze</button><button onclick="loadCommandFreeze(true)">Export Freeze Report</button><button onclick="api('/api/open/command_center_milestone_freeze')">Open Freeze Reports</button><button onclick="go('commandcenter')">Open Command Center</button><button onclick="go('commandarchive')">Open Command Archive</button><button onclick="sendCommandFreezeToMission()">Send Freeze to Mission</button><div id=commandFreezeStatus class=status>No Command Center freeze loaded yet.</div></div><div class="card wide"><h3>Freeze Summary</h3><div id=commandFreezeSummary class=status>No summary yet.</div></div><div class="card wide"><h3>Proven Modules</h3><div id=commandFreezeModules class=scanlist>No modules loaded yet.</div></div><div class="card wide"><h3>Advisories</h3><div id=commandFreezeAdvisories class=scanlist>No advisories loaded yet.</div></div><div class="card wide"><h3>Recommendations</h3><div id=commandFreezeRecommendations class=scanlist>No recommendations loaded yet.</div></div><div class="card wide"><h3>Problems / Review Items</h3><div id=commandFreezeProblems class=scanlist>No review items loaded yet.</div></div><div class="card wide"><h3>Safety Contract</h3><div id=commandFreezeSafety class=status>No safety contract loaded yet.</div></div></div></section>


<section id=kayockwriter class=page><div class=hero><h2>Kayock Writer Foundation</h2><p>The new creative writing department: Story Forge, Poetry Studio, Codex, Timeline, Continuity, Mystery Tracker, and Story Bible Export. This foundation report is read-only and does not migrate or modify story files.</p></div><div class=grid><div class="card wide"><h3>Foundation Controls</h3><button onclick="loadKayockWriter(false)">Load Writer Foundation</button><button onclick="loadKayockWriter(true)">Export Foundation Report</button><button onclick="api('/api/open/kayock_writer_foundation_reports')">Open Writer Foundation Reports</button><button onclick="sendKayockWriterToMission()">Send Writer Foundation to Mission</button><div id=kayockWriterStatus class=status>No Kayock Writer foundation report loaded yet.</div></div><div class="card wide"><h3>Foundation Summary</h3><div id=kayockWriterSummary class=status>No summary yet.</div></div><div class="card wide"><h3>Module Plan</h3><div id=kayockWriterModules class=scanlist>No modules loaded yet.</div></div><div class="card wide"><h3>Naming Decisions</h3><div id=kayockWriterNames class=scanlist>No naming decisions loaded yet.</div></div><div class="card wide"><h3>Flagship Universe</h3><div id=kayockWriterFlagship class=status>No flagship universe loaded yet.</div></div><div class="card wide"><h3>Path Checks</h3><div id=kayockWriterPaths class=scanlist>No path checks loaded yet.</div></div><div class="card wide"><h3>Recommendations</h3><div id=kayockWriterRecommendations class=scanlist>No recommendations loaded yet.</div></div><div class="card wide"><h3>Safety Contract</h3><div id=kayockWriterSafety class=status>No safety contract loaded yet.</div></div></div></section>

<section id=storyforge class=page><div class=hero><h2>Story Forge Shell</h2><p>The first Kayock Writer working module: story projects, chapter planning, scene planning, and Slipping into Darkness as the flagship demo universe. This shell is read-only.</p></div><div class=grid><div class="card wide"><h3>Story Forge Controls</h3><button onclick="loadStoryForge(false)">Load Story Forge Shell</button><button onclick="loadStoryForge(true)">Export Shell Report</button><button onclick="api('/api/open/kayock_writer_story_forge_reports')">Open Story Forge Reports</button><button onclick="go('kayockwriter')">Open Kayock Writer</button><button onclick="sendStoryForgeToMission()">Send Story Forge to Mission</button><div id=storyForgeStatus class=status>No Story Forge shell loaded yet.</div></div><div class="card wide"><h3>Shell Summary</h3><div id=storyForgeSummary class=status>No summary yet.</div></div><div class="card wide"><h3>Flagship Story</h3><div id=storyForgeFlagship class=status>No flagship loaded yet.</div></div><div class="card wide"><h3>Project Candidates</h3><div id=storyForgeProjects class=scanlist>No project candidates loaded yet.</div></div><div class="card wide"><h3>Shell Sections</h3><div id=storyForgeSections class=scanlist>No shell sections loaded yet.</div></div><div class="card wide"><h3>Future Actions</h3><div id=storyForgeActions class=scanlist>No future actions loaded yet.</div></div><div class="card wide"><h3>Checks</h3><div id=storyForgeChecks class=scanlist>No checks loaded yet.</div></div><div class="card wide"><h3>Safety Contract</h3><div id=storyForgeSafety class=status>No safety contract loaded yet.</div></div></div></section>


<section id=storymanifest class=page><div class=hero><h2>Story Project Manifest Preview</h2><p>Preview the proposed Kayock Writer project manifest before anything is created. This page scans legacy NovelForge read-only and lists exact future writes behind an approval gate.</p></div><div class=grid><div class="card wide"><h3>Manifest Preview Controls</h3><button onclick="loadStoryManifest(false)">Load Manifest Preview</button><button onclick="loadStoryManifest(true)">Export Manifest Preview</button><button onclick="api('/api/open/kayock_writer_manifest_preview_reports')">Open Manifest Preview Reports</button><button onclick="go('storyforge')">Open Story Forge</button><button onclick="sendStoryManifestToMission()">Send Manifest Preview to Mission</button><div id=storyManifestStatus class=status>No manifest preview loaded yet.</div></div><div class="card wide"><h3>Preview Summary</h3><div id=storyManifestSummary class=status>No summary yet.</div></div><div class="card wide"><h3>Proposed Manifest</h3><div id=storyManifestBody class=status>No manifest loaded yet.</div></div><div class="card wide"><h3>Legacy Sources Detected</h3><div id=storyManifestLegacy class=scanlist>No legacy sources loaded yet.</div></div><div class="card wide"><h3>Proposed Folders</h3><div id=storyManifestFolders class=scanlist>No proposed folders loaded yet.</div></div><div class="card wide"><h3>Future Writes / Approval Gate</h3><div id=storyManifestWrites class=scanlist>No future writes loaded yet.</div></div><div class="card wide"><h3>Checks</h3><div id=storyManifestChecks class=scanlist>No checks loaded yet.</div></div><div class="card wide"><h3>Safety Contract</h3><div id=storyManifestSafety class=status>No safety contract loaded yet.</div></div></div></section>


<section id=projectgate class=page><div class=hero><h2>Create Project Approval Gate</h2><p>Final pre-flight gate before any Kayock Writer project skeleton is created. This page verifies target paths, overwrite risk, copy-only legacy import, and the exact approval phrase. It does not create anything.</p></div><div class=grid><div class="card wide"><h3>Gate Controls</h3><input id=projectGatePhrase placeholder="Optional test phrase; creation still disabled in this build"><button onclick="loadProjectGate(false)">Load Gate</button><button onclick="loadProjectGate(true)">Export Gate Report</button><button onclick="api('/api/open/kayock_writer_create_gate_reports')">Open Gate Reports</button><button onclick="go('storymanifest')">Open Manifest Preview</button><button onclick="sendProjectGateToMission()">Send Gate to Mission</button><div id=projectGateStatus class=status>No project gate loaded yet.</div></div><div class="card wide"><h3>Gate Summary</h3><div id=projectGateSummary class=status>No summary yet.</div></div><div class="card wide"><h3>Approval Gate</h3><div id=projectGateApproval class=status>No approval gate loaded yet.</div></div><div class="card wide"><h3>Proposed Writes</h3><div id=projectGateWrites class=scanlist>No proposed writes loaded yet.</div></div><div class="card wide"><h3>Overwrite Risks</h3><div id=projectGateRisks class=scanlist>No risk scan loaded yet.</div></div><div class="card wide"><h3>Legacy Copy-Only Sources</h3><div id=projectGateLegacy class=scanlist>No legacy files loaded yet.</div></div><div class="card wide"><h3>Checks</h3><div id=projectGateChecks class=scanlist>No checks loaded yet.</div></div><div class="card wide"><h3>Safety Contract</h3><div id=projectGateSafety class=status>No safety contract loaded yet.</div></div></div></section>

<section id=academy class=page><div class=hero><h2>Academy</h2><p>Professors are prompt profiles.</p></div><div id=profgrid class=grid></div></section>

<section id=novelforge class=page><div class=hero><h2>Novel Forge</h2><p>Story operating system workspace. Build the Codex first: universes, characters, locations, artifacts, timelines, mysteries, and notes.</p></div><div class="card wide"><h3>Codex Dashboard</h3><div id=nfDashboard class=status>Loading Codex dashboard...</div><div id=nfExportStatus class=status></div><div class=previewhead><button onclick="updateCodexDashboard()">Refresh Dashboard</button><button onclick="checkNovelContinuity()">Check Continuity</button><button onclick="checkCharacterArcs()">Check Character Arcs</button><button onclick="checkMysteryPayoff()">Check Mystery Payoff</button><button onclick="checkWorldbuilding()">Check Worldbuilding</button><button onclick="checkArtifactRules()">Check Artifact Rules</button><button onclick="sendCompleteStoryBible()">Send Complete Story Bible</button><button onclick="exportStoryBible()">Export Story Bible</button><button onclick="api('/api/open/novel_exports')">Open Export Folder</button></div></div><div class=grid><div class="card wide"><h3>Codex Editor</h3><div class=previewhead><button onclick="loadSlippingTemplate()">Load Slipping into Darkness Template</button><button onclick="updateNovelCounts()">Update Counts</button><span id=nfCounts class=small>Counts: 0 characters · 0 locations · 0 artifacts · 0 timeline · 0 mysteries</span></div><div class=small>Universe Name</div><input id=nfUniverse placeholder="Example: Slipping into Darkness" oninput="updateNovelCounts()"><div class=small>Premise</div><textarea id=nfPremise placeholder="What is this universe about?" oninput="updateNovelCounts()"></textarea><div class=grid><div><div class=small>Characters - one per line</div><textarea id=nfCharacters placeholder="Anthony / Whisper - protagonist, psychic vampire hunter...&#10;Kayock - first vampire, ancient protector..." oninput="syncCharactersFromText();updateNovelCounts()"></textarea></div><div><div class=small>Locations - one per line</div><textarea id=nfLocations placeholder="Pueblo tunnels&#10;Olmec pyramid&#10;Kayock's lair" oninput="updateNovelCounts()"></textarea></div></div><div class="card wide"><h3>Character Manager</h3><p class=small>Structured character cards save back into the Characters text box as portable Codex lines.</p><div class=grid><div><div class=small>Name</div><input id=nfCharName placeholder="Anthony / Whisper"></div><div><div class=small>Role / Archetype</div><input id=nfCharRole placeholder="Protagonist, mentor, antagonist, ancient protector"></div><div><div class=small>Status / Alignment</div><input id=nfCharStatus placeholder="Alive, turned, dead, unknown, ally, enemy"></div></div><div class=small>Details</div><textarea id=nfCharDetails placeholder="Core motivation, powers, wound, secret, relationship to prophecy, and canon facts."></textarea><div class=small>Tags / Connections</div><input id=nfCharTags placeholder="Anthony, Kayock, prophecy, Book 1, psychic, vampire"><button onclick="addCharacterCard()">Add Character</button><button onclick="sortCharacterCards()">Sort Characters</button><button onclick="restoreSlippingCharacters()">Restore Slipping Characters</button><button onclick="upgradeSimpleCharacterCards()">Upgrade Simple Cards</button><button onclick="checkCharacterArcs()">Check Character Arcs</button><button onclick="syncCharactersFromText();renderCharacterCards()">Refresh From Text</button><div id=nfCharacterCards class=status>No character cards yet.</div></div><div class="card wide"><h3>Location Manager</h3><p class=small>Track places, secrets, related characters, and mystery connections. Saves back into the Locations text box as portable Codex lines.</p><div class=grid><div><div class=small>Location Name</div><input id=nfLocName placeholder="Pueblo tunnels"></div><div><div class=small>Type</div><input id=nfLocType placeholder="City, lair, ancient ruin, prison, sanctuary"></div><div><div class=small>Related Characters</div><input id=nfLocCharacters placeholder="Anthony, Kayock, Jokaya"></div></div><div class=small>Description</div><textarea id=nfLocDescription placeholder="What is this place, what does it feel like, and why does it matter?"></textarea><div class=small>Secrets</div><textarea id=nfLocSecrets placeholder="Hidden history, secret rooms, lies, buried threats, reader-reveal timing..."></textarea><div class=small>Related Mysteries</div><input id=nfLocMysteries placeholder="Crystal skulls, Croatoan escape, prophecy misunderstanding"><button onclick="addLocationCard()">Add Location</button><button onclick="sortLocationCards()">Sort Locations</button><button onclick="restoreSlippingLocations()">Restore Slipping Locations</button><button onclick="checkWorldbuilding()">Check Worldbuilding</button><button onclick="syncLocationsFromText();renderLocationCards()">Refresh From Text</button><div id=nfLocationCards class=status>No location cards yet.</div></div><div class=grid><div><div class=small>Artifacts - one per line</div><textarea id=nfArtifacts placeholder="Crystal skulls&#10;Silver cross&#10;Ancient blood vats" oninput="syncArtifactsFromText();updateNovelCounts()"></textarea></div><div><div class=small>Timeline Events - one per line</div><textarea id=nfTimeline placeholder="Book 1: Anthony learns the prophecy...&#10;Kayock dies..." oninput="syncTimelineFromText();updateNovelCounts()"></textarea></div></div><div class="card wide"><h3>Artifact Manager</h3><p class=small>Track artifacts, powers, rules, limits, history, and payoff connections. Saves back into the Artifacts text box as portable Codex lines.</p><div class=grid><div><div class=small>Artifact Name</div><input id=nfArtName placeholder="Crystal skulls"></div><div><div class=small>Type</div><input id=nfArtType placeholder="Relic, weapon, prophecy key, vessel, record"></div><div><div class=small>Related Characters</div><input id=nfArtCharacters placeholder="Anthony, Kayock, Thoth"></div></div><div class=small>Power / Function</div><textarea id=nfArtFunction placeholder="What does this artifact do, reveal, unlock, or threaten?"></textarea><div class=small>History</div><textarea id=nfArtHistory placeholder="Where did it come from, who used it, who lied about it?"></textarea><div class=small>Rules / Limits</div><textarea id=nfArtRules placeholder="Costs, limits, dangers, requirements, failure states..."></textarea><div class=small>Related Mysteries</div><input id=nfArtMysteries placeholder="Crystal skull contents, prophecy misunderstanding, Croatoan escape"><button onclick="addArtifactCard()">Add Artifact</button><button onclick="sortArtifactCards()">Sort Artifacts</button><button onclick="restoreSlippingArtifacts()">Restore Slipping Artifacts</button><button onclick="checkArtifactRules()">Check Artifact Rules</button><button onclick="syncArtifactsFromText();renderArtifactCards()">Refresh From Text</button><div id=nfArtifactCards class=status>No artifact cards yet.</div></div><div class="card wide"><h3>Timeline Manager</h3><p class=small>Structured timeline events are saved back into the Timeline text box, so the Codex stays portable.</p><div class=grid><div><div class=small>Book / Era</div><input id=nfEventEra placeholder="Book 1, Book 2, Ancient Egypt, Modern Pueblo"></div><div><div class=small>Event Title</div><input id=nfEventTitle placeholder="Anthony learns the prophecy"></div></div><div class=small>Event Details</div><textarea id=nfEventDetails placeholder="What happens, why it matters, and what canon facts this creates."></textarea><div class=small>Tags / Characters / Clues</div><input id=nfEventTags placeholder="Anthony, Kayock, prophecy, crystal skulls"><button onclick="addTimelineEvent()">Add Event</button><button onclick="sortTimelineEvents()">Sort Timeline</button><button onclick="sendTimelineManager()">Send Timeline to Mission Console</button><button onclick="syncTimelineFromText();renderTimelineEvents()">Refresh From Text</button><div id=nfTimelineList class=status>No timeline events yet.</div></div><div class=small>Mysteries / Unresolved Threads - one per line</div><textarea id=nfMysteries placeholder="What happened to the ex?&#10;How did Croatoan escape?" oninput="syncMysteriesFromText();updateNovelCounts()"></textarea><div class="card wide"><h3>Mystery Tracker</h3><p class=small>Track unresolved threads, planted clues, reveals, red herrings, and payoffs. Saves back into the Mysteries text box as portable Codex lines.</p><div class=grid><div><div class=small>Mystery Title</div><input id=nfMysteryTitle placeholder="What exactly did Anthony’s ex become?"></div><div><div class=small>Status</div><select id=nfMysteryStatus><option>Unresolved</option><option>Clue planted</option><option>Partially revealed</option><option>Solved</option><option>Red herring</option></select></div><div><div class=small>Related Characters</div><input id=nfMysteryCharacters placeholder="Anthony, ex, Jokaya, Chee"></div></div><div class=small>Details</div><textarea id=nfMysteryDetails placeholder="What is the mystery, why does it matter, and what question should the reader be asking?"></textarea><div class=small>Clues</div><textarea id=nfMysteryClues placeholder="Clue 1...&#10;Clue 2..."></textarea><div class=small>Payoff Plan</div><textarea id=nfMysteryPayoff placeholder="How and when should this mystery pay off?"></textarea><button onclick="addMysteryCard()">Add Mystery</button><button onclick="sortMysteryCards()">Sort Mysteries</button><button onclick="restoreSlippingMysteries()">Restore Slipping Mysteries</button><button onclick="checkMysteryPayoff()">Check Mystery Payoff</button><button onclick="syncMysteriesFromText();renderMysteryCards()">Refresh From Text</button><div id=nfMysteryCards class=status>No mysteries yet.</div></div><div class="card wide"><h3>Scene Builder</h3><p class=small>Create scene briefs from the Codex. Save them as portable scene lines and send them to the active professor for drafting or continuity checks.</p><div class=grid><div><div class=small>Scene Title</div><input id=nfSceneTitle placeholder="Anthony enters Kayock’s lair"></div><div><div class=small>POV Character</div><input id=nfScenePOV placeholder="Anthony / Whisper"></div><div><div class=small>Location</div><input id=nfSceneLocation placeholder="Kayock’s lair"></div></div><div class=small>Characters Present</div><input id=nfSceneCharacters placeholder="Anthony, Chee, Kayock legacy"><div class=small>Scene Purpose</div><textarea id=nfScenePurpose placeholder="What must this scene accomplish for plot, character, theme, or mystery?"></textarea><div class=small>Conflict</div><textarea id=nfSceneConflict placeholder="What pressure, danger, argument, revelation, or choice drives the scene?"></textarea><div class=small>Outcome</div><textarea id=nfSceneOutcome placeholder="What changes by the end of the scene? What new canon is created?"></textarea><div class=small>Canon Notes</div><textarea id=nfSceneCanon placeholder="Rules, clues, continuity constraints, foreshadowing, author-only notes..."></textarea><button onclick="addSceneCard()">Add Scene</button><button onclick="sortSceneCards()">Sort Scenes</button><button onclick="restoreStarterScenes()">Restore Starter Scenes</button><button onclick="checkScenePlan()">Check Scene Plan</button><button onclick="syncScenesFromText();renderSceneCards()">Refresh From Text</button><div id=nfSceneCards class=status>No scenes yet.</div></div><div class=small>Scenes - portable storage lines</div><textarea id=nfScenes placeholder="Scene cards save here automatically." oninput="syncScenesFromText();updateNovelCounts()"></textarea><div class=small>Notes</div><textarea id=nfNotes placeholder="Author notes, tone, themes, rules, contradictions to resolve..." oninput="updateNovelCounts()"></textarea><button onclick="saveNovelForge()">Save Universe</button><button onclick="sendNovelForgeContext()">Send Full Codex</button><button onclick="checkNovelContinuity()">Check Continuity</button><button onclick="buildNextStoryArc()">Build Next Arc</button><select id=nfSection><option value=full>Full Codex</option><option value=premise>Premise</option><option value=characters>Characters</option><option value=locations>Locations</option><option value=artifacts>Artifacts</option><option value=timeline>Timeline</option><option value=mysteries>Mysteries</option><option value=notes>Notes</option></select><button onclick="sendNovelForgeSection()">Send Section</button><button onclick="clearNovelForge()">New Universe</button><button onclick="api('/api/open/novel_forge')">Open Novel Forge Folder</button><div id=nfStatus class=status></div></div><div class="card wide"><h3>Saved Universes</h3><button onclick="loadNovelForgeList()">Refresh</button><div id=nfList class=status>Loading universes...</div></div><div class=card><h3>Continuity Engine</h3><div class=status>Ready:
Check contradictions
Timeline logic
Character conflicts
Canon risks
Setup/payoff gaps</div><button onclick="checkNovelContinuity()">Run Continuity Check</button></div><div class=card><h3>Next Engines</h3><div class=status>Continuity Check
Timeline Manager
Relationship Graph
Canon Tracker
Reader vs Author Knowledge</div></div><div class=card><h3>Flagship Demo</h3><div class=status>Slipping into Darkness is the ideal first test universe for Novel Forge.</div></div></div></section>

<section id=prompts class=page><div class=hero><h2>PromptSmith</h2><p>Build, organize, save, search, and send prompts into the Mission Console. Stored locally in the FOXAI Prompts folder.</p></div><div class=grid><div class="card wide"><h3>Prompt Workshop</h3><div class=grid><div><div class=small>Title</div><input id=promptTitle placeholder="Example: Novel Forge Continuity Check"></div><div><div class=small>Category</div><select id=promptCategory><option>General</option><option>Coding</option><option>Novel Forge</option><option>Repair Bay</option><option>Creative Studio</option><option>Academy</option><option>System</option></select></div><div><div class=small>Prompt Type</div><select id=promptType><option>User Prompt</option><option>System Prompt</option><option>Agent Instruction</option><option>Template</option><option>Checklist</option></select></div></div><div class=small>Notes</div><textarea id=promptNotes placeholder="What this prompt is for, what model it works best with, or how to use it."></textarea><div class=small>Prompt</div><textarea id=promptDraft placeholder="Draft a prompt here..."></textarea><button onclick="savePromptSmith()">Save Prompt</button><button onclick="copyPromptSmith()">Copy Prompt</button><button onclick="sendPromptSmith()">Send to Mission Console</button><button onclick="sendPromptSmithWithContext()">Send with Context</button><button onclick="clearPromptSmith()">New Prompt</button><button onclick="api('/api/open/prompts')">Open Prompts Folder</button><div id=promptSaveStatus class=status></div></div><div class="card wide"><h3>Saved Prompts</h3><div class=grid><div><div class=small>Search</div><input id=promptSearch placeholder="Search title, category, notes, prompt..." oninput="renderPromptList()"></div><div><div class=small>Filter Category</div><select id=promptFilter onchange="renderPromptList()"><option>All</option><option>General</option><option>Coding</option><option>Novel Forge</option><option>Repair Bay</option><option>Creative Studio</option><option>Academy</option><option>System</option></select></div></div><button onclick="loadPrompts()">Refresh</button><div id=promptList class=status>Loading prompts...</div></div><div class=card><h3>PromptSmith Pipeline</h3><div class=status>Draft
Test
Compare Models
Optimize
Save
Deploy</div></div><div class=card><h3>Extension Hook</h3><div class=status>Import endpoint ready:
POST /api/prompts/import

Payload:
title, category, prompt_type, notes, prompt</div></div></div></section>

<section id=creative class=page><div class=hero><h2>Creative Studio</h2><p>ComfyUI remains the image engine.</p></div><div class=grid><div class=card><h3>ComfyUI</h3><button onclick="api('/api/launch/comfy')">Launch</button><button onclick="api('/api/open-url/comfy')">Open</button></div><div class=card><h3>Gallery</h3><button onclick="api('/api/open/comfy_output')">Open Output</button></div></div></section>
<section id=library class=page><div class=hero><h2>Iron Library</h2><p>Browse and search local reference files. Search is filename/folder based for speed and USB safety.</p></div><div class="card wide"><h3>Library Search</h3><div class=grid><div><div class=small>Search</div><input id=libSearch placeholder="Search filenames, folders, extensions..." onkeydown="if(event.key==='Enter'){searchLib()}"></div><div><div class=small>Type</div><select id=libType><option value=all>All</option><option value=folder>Folders</option><option value=pdf>PDF</option><option value=text>Text / Markdown</option><option value=doc>Documents</option><option value=image>Images</option><option value=code>Code</option><option value=audio>Audio</option><option value=video>Video</option></select></div></div><button onclick="searchLib()">Search Library</button><button onclick="q('libSearch').value='';q('libType').value='all';searchLib()">Show All</button><div class=small>Optional question for the active professor</div><textarea id=libAskQuestion placeholder="Example: Summarize this file, find risks, extract action items, explain what matters, or connect it to my current project."></textarea><div id=libSearchStatus class=status></div><div id=libResults class=status></div></div><div class="card wide"><h3>Preview</h3><div id=libPreview class=status>Select a readable file to preview.</div></div><div class="card wide"><h3>Full Text Index</h3><p class=small>Manual lightweight index for text, markdown, logs, code, JSON, and config files. PDFs/ePubs come later.</p><button onclick="buildIronIndex()">Build / Refresh Index</button><button onclick="loadIronIndexStatus()">Index Status</button><div id=ironIndexStatus class=status>Index status unknown.</div><div class=grid><div><div class=small>Indexed Text Search</div><input id=ironIndexSearch placeholder="Search inside indexed readable files..." onkeydown="if(event.key==='Enter'){searchIronIndex()}"></div></div><button onclick="searchIronIndex()">Search Index</button><div id=ironIndexResults class=status></div></div><div class="card wide"><h3>Library Browser</h3><div id=libpath class="small path">Library</div><button onclick="libUp()">Up</button><button onclick="loadLib('')">Root</button><button onclick="api('/api/open/library')">Explorer</button><div id=liblist class=status>Loading...</div></div></section>
<section id=repair class=page><div class=hero><h2>Repair Bay</h2><p>Diagnostics first. Automated repair only when approved.</p></div><div class=grid><div class=card><h3>Diagnostics</h3><button onclick="refresh()">Refresh Status</button></div><div class=card><h3>Config</h3><button onclick="api('/api/open/config')">Open Config</button></div></div></section>

<section id=extensions class=page><div class=hero><h2>Extension Manager</h2><p>Discover, validate, enable, and disable Kayock modules. This is the shell for the future .kmod ecosystem.</p></div><div class=grid><div class="card wide"><h3>Module Status Dashboard</h3><div id=extDashboard class=status>Loading module dashboard...</div><div class=previewhead><button onclick="loadExtensions()">Refresh</button><button onclick="validateExtensions()">Validate</button><button onclick="exportExtensionReport()">Export Report</button><button onclick="api('/api/open/manifest_backups')">Open Backups</button></div></div><div class="card wide"><h3>Module Control</h3><button onclick="loadExtensions()">Refresh Modules</button><button onclick="validateExtensions()">Validate Manifests</button><button onclick="createSampleExtension()">Create Sample Extension</button><button onclick="exportExtensionReport()">Export Extension Report</button><button onclick="api('/api/open/extensions')">Open Extensions Folder</button><button onclick="api('/api/open/modules')">Open Modules Folder</button><button onclick="api('/api/open/reports')">Open Reports Folder</button><button onclick="api('/api/open/manifest_backups')">Open Manifest Backups</button><div id=extSummary class=status>Loading extensions...</div></div><div class="card wide"><h3>Installed Modules</h3><div id=extList class=status>Loading...</div></div><div class="card wide"><h3>Manifest Repair Helper</h3><p class=small>Safe helper: generates suggested manifest text. Apply Fix backs up the original file before writing.</p><div id=extRepair class=status>Validate manifests, then click Suggest Fix on a problem.</div></div><div class=card><h3>Future .kmod Flow</h3><div class=status>Discover
Validate manifest
Check dependencies
Enable / disable
Import / export
Package verification
Safe update center handoff</div></div><div class=card><h3>Manifest Minimum</h3><div class=status>{
  "id": "my-module",
  "name": "My Module",
  "version": "0.1.0",
  "description": "...",
  "enabled": true
}</div></div></div></section>


<section id=scanbridge class=page><div class=hero><h2>Folder Scan Bridge</h2><p>Read-only folder scanner. Kayock scans allowed FOXAI folders, creates a safe report, then the Mission Console can send that report to the local model.</p></div><div class=grid><div class="card wide"><h3>Scan Control</h3><div class=grid><div><div class=small>Folder / Path / Key</div><input id=scanPath placeholder="extensions, modules, reports, or Z:\FOXAI\Departments\Engineering"></div><div><div class=small>Max Files</div><input id=scanMaxFiles value="3000"></div><div><div class=small>Large File Skip Bytes</div><input id=scanMaxBytes value="1048576"></div></div><button onclick="scanFolder(false)">Scan Folder</button><button onclick="scanFolder(true)">Scan + Export Report</button><button onclick="api('/api/open/scan_reports')">Open Scan Reports</button><button onclick="sendLastScanToMission()">Send Last Scan to Mission</button><div id=scanStatus class=status>No scan yet.</div></div><div class="card wide"><h3>Scan Report Reader</h3><p class=small>Load a saved scan report, preview its contents, and send the report summary/content to Mission Console.</p><div class=grid><div><div class=small>Report Path</div><input id=scanReportPath placeholder="Z:\FOXAI\Reports\Scans\Folder_Scan_....json or .md"></div><div><div class=small>Preview Character Limit</div><input id=scanReportMax value="120000"></div></div><button onclick="loadScanReport()">Load Report</button><button onclick="useLastScanReportPath()">Use Last Exported Report</button><button onclick="sendLoadedScanReportToMission()">Send Loaded Report to Mission</button><div id=scanReportStatus class=status>No saved report loaded yet.</div><div id=scanReportPreview class=scanlist>No preview yet.</div></div><div class="card wide"><h3>Scan Results</h3><div id=scanResults class=status>No results yet.</div></div><div class=card><h3>Allowed Safety Model</h3><div class=status>Read-only scan
FOXAI root only
No direct AI drive roaming
Backend creates report first
Model receives summary/report path</div></div><div class=card><h3>Ignored Folders</h3><div class=status>node_modules
.git
env / venv / .venv
__pycache__
dist / build
cache folders</div></div></div></section>


<section id=projectgen class=page><div class=hero><h2>Project Manifest + README Generator</h2><p>Generate safe project documentation from discovered modules and scan reports. Preview first, then write with backup.</p></div><div class=grid><div class="card wide"><h3>Documentation Status</h3><div id=docsStatus class=status>Documentation status not checked yet.</div><div class=previewhead><button onclick="refreshProjectDocsStatus()">Refresh Docs Status</button><button onclick="loadRootManifestFile()">Load Root Manifest</button><button onclick="loadDepartmentReadmeFile()">Load Engineering README</button><button onclick="sendDocsStatusToMission()">Send Docs Status to Mission</button></div></div><div class="card wide"><h3>Root Project Manifest</h3><p class=small>Creates a root <code>Z:\FOXAI\manifest.json</code> that describes Kayock Command OS, modules, safety principles, and scan summary.</p><button onclick="previewRootManifest()">Preview Root Manifest</button><button onclick="applyRootManifest()">Write Root Manifest</button><button onclick="api('/api/open/file_backups')">Open Generated File Backups</button><div id=rootManifestStatus class=status>No preview yet.</div></div><div class="card wide"><h3>Department README</h3><p class=small>Creates a README for a department from its manifest, services, tools, and ownership metadata.</p><div class=grid><div><div class=small>Department Key</div><input id=readmeDeptKey value="engineering"></div></div><button onclick="previewDepartmentReadme()">Preview Department README</button><button onclick="applyDepartmentReadme()">Write Department README</button><div id=readmeStatus class=status>No README preview yet.</div></div><div class="card wide"><h3>Preview</h3><div id=generatedPreview class=scanlist>No generated content yet.</div><button onclick="sendGeneratedPreviewToMission()">Send Preview to Mission Console</button></div><div class=card><h3>Safety Model</h3><div class=status>Preview before write
Backup existing files
FOXAI-root-only targets
JSON / Markdown generation
No silent overwrites</div></div></div></section>


<section id=buildverify class=page><div class=hero><h2>Build Verification Lite</h2><p>Report-only verification. Checks manifests, docs, expected paths, scan summaries, and Python compile status without modifying project files.</p></div><div class=grid><div class="card wide"><h3>Verification Control</h3><button onclick="runBuildVerification()">Run Build Verification</button><button onclick="api('/api/open/build_reports')">Open Build Reports</button><button onclick="sendBuildVerificationToMission()">Send Verification to Mission</button><div id=buildStatus class=status>No build verification run yet.</div></div><div class="card wide"><h3>Verification Dashboard</h3><div id=buildDashboard class=status>No results yet.</div></div><div class="card wide"><h3>Verification Details</h3><div id=buildDetails class=scanlist>No details yet.</div></div><div class=card><h3>Safety Model</h3><div class=status>Report-only
No package installs
No repair actions
No code edits
Python compile check only
Export report before model review</div></div></div></section>


<section id=envverify class=page><div class=hero><h2>Environment + Dependency Verification</h2><p>Report-only environment check. Verifies Python runtime, optional Repair Bay imports, Node/npm presence, key folders, models, BAT files, and report paths.</p></div><div class=grid><div class="card wide"><h3>Environment Control</h3><button onclick="runEnvVerification()">Run Environment Verification</button><button onclick="api('/api/open/env_reports')">Open Environment Reports</button><button onclick="sendEnvVerificationToMission()">Send Environment Report to Mission</button><div id=envStatus class=status>No environment verification run yet.</div></div><div class="card wide"><h3>Environment Dashboard</h3><div id=envDashboard class=status>No results yet.</div></div><div class="card wide"><h3>Verification Details</h3><div id=envDetails class=scanlist>No details yet.</div></div><div class=card><h3>Safety Model</h3><div class=status>Report-only
No package installs
No dependency updates
No repairs
No code edits
Optional missing tools are not failures yet</div></div></div></section>


<section id=portable class=page><div class=hero><h2>Runtime Lock + Portable Readiness</h2><p>Checks whether Kayock is actually running from the portable FOXAI runtime and identifies what still blocks USB workstation readiness.</p></div><div class=grid><div class="card wide"><h3>Portable Readiness Control</h3><button onclick="runPortableReadiness()">Run Portable Readiness</button><button onclick="api('/api/open/portable_reports')">Open Portable Reports</button><button onclick="sendPortableReadinessToMission()">Send Readiness to Mission</button><div id=portableStatus class=status>No portable readiness report run yet.</div></div><div class="card wide"><h3>Portable Dashboard</h3><div id=portableDashboard class=status>No results yet.</div></div><div class="card wide"><h3>Blockers + Warnings</h3><div id=portableBlockers class=scanlist>No blockers/warnings yet.</div></div><div class="card wide"><h3>Check Details</h3><div id=portableDetails class=scanlist>No details yet.</div></div><div class=card><h3>Safety Model</h3><div class=status>Report-only
No installs
No repairs
No model deletion
No folder cleanup
Use this before approved Repair Bay actions</div></div></div></section>


<section id=modelcheck class=page><div class=hero><h2>Model Duplicate Truth Check</h2><p>Separates true duplicate GGUF files from Windows folder casing aliases. Generates a cleanup plan without deleting or moving anything.</p></div><div class=grid><div class="card wide"><h3>Model Check Control</h3><button onclick="runModelDuplicateTruth()">Run Model Duplicate Truth Check</button><button onclick="api('/api/open/model_reports')">Open Model Reports</button><button onclick="sendModelDuplicateTruthToMission()">Send Cleanup Plan to Mission</button><div id=modelTruthStatus class=status>No model duplicate truth check run yet.</div></div><div class="card wide"><h3>Model Storage Dashboard</h3><div id=modelTruthDashboard class=status>No results yet.</div></div><div class="card wide"><h3>Cleanup Plan</h3><div id=modelCleanupPlan class=scanlist>No cleanup plan yet.</div></div><div class="card wide"><h3>Duplicate / Alias Details</h3><div id=modelTruthDetails class=scanlist>No details yet.</div></div><div class=card><h3>Safety Model</h3><div class=status>Report-only
No deletion
No moving files
No model cleanup action
No path rewrite
Planner before action</div></div></div></section>


<section id=repairactions class=page><div class=hero><h2>User-Approved Repair Bay Actions</h2><p>Low-risk action mode. Build a plan first, then apply one confirmed action at a time with logs and backups.</p></div><div class=grid><div class="card wide"><h3>Action Control</h3><button onclick="buildRepairActionPlan()">Build Repair Action Plan</button><button onclick="api('/api/open/repair_reports')">Open Repair Logs</button><button onclick="sendRepairActionPlanToMission()">Send Plan to Mission</button><div id=repairActionStatus class=status>No repair action plan built yet.</div></div><div class="card wide"><h3>Action Plan</h3><div id=repairActionPlan class=scanlist>No plan yet.</div></div><div class="card wide"><h3>Last Action Result</h3><div id=repairActionResult class=scanlist>No action applied yet.</div></div><div class=card><h3>Safety Model</h3><div class=status>Preview first
One action at a time
Browser confirmation
Backend confirmation token
Backup before overwrite
Repair log for every action
No model deletion
No dependency installs</div></div></div></section>


<section id=repairhistory class=page><div class=hero><h2>Repair Bay Action History</h2><p>Audit trail for user-approved Repair Bay actions. Review logs, targets, backups, success/failure counts, and post-action verification before expanding repair powers.</p></div><div class=grid><div class="card wide"><h3>History Control</h3><div class=grid><div><div class=small>Action Filter</div><input id=repairHistoryFilter placeholder="optional, e.g. readme or manifest"></div><div><div class=small>Limit</div><input id=repairHistoryLimit value="200"></div></div><button onclick="loadRepairHistory(false)">Load History</button><button onclick="loadRepairHistory(true)">Export History Summary</button><button onclick="api('/api/open/repair_reports')">Open Repair Logs</button><button onclick="sendRepairHistoryToMission()">Send History to Mission</button><div id=repairHistoryStatus class=status>No repair history loaded yet.</div></div><div class="card wide"><h3>History Dashboard</h3><div id=repairHistoryDashboard class=status>No results yet.</div></div><div class="card wide"><h3>By Action Type</h3><div id=repairHistoryByAction class=scanlist>No action summary yet.</div></div><div class="card wide"><h3>Action Logs</h3><div id=repairHistoryLogs class=scanlist>No logs yet.</div></div><div class=card><h3>Safety Model</h3><div class=status>Read-only history viewer
No repairs
No deletes
No installs
No file changes except optional history export</div></div></div></section>



<section id=restorepreview class=page><div class=hero><h2>Restore Preview Planner</h2><p>Preview-only rollback planning. Compare a selected backup against its current target before any restore power exists.</p></div><div class=grid><div class="card wide"><h3>Preview Control</h3><div class=grid><div><div class=small>Select Backup</div><select id=restoreBackupSelect onchange="q('restoreBackupPath').value=this.value"></select></div><div><div class=small>Or Backup Path</div><input id=restoreBackupPath placeholder="Z:\FOXAI\Backups\GeneratedFiles\..."></div></div><button onclick="loadRestoreBackupList()">Load Backup List</button><button onclick="previewRestore(false)">Preview Selected Backup</button><button onclick="previewRestore(true)">Export Restore Preview</button><button onclick="sendRestorePreviewToMission()">Send Preview to Mission</button><div id=restorePreviewStatus class=status>No restore preview loaded yet.</div></div><div class="card wide"><h3>Preview Dashboard</h3><div id=restorePreviewDashboard class=status>No comparison yet.</div></div><div class="card wide"><h3>Backup vs Current Target</h3><div id=restorePreviewCompare class=scanlist>No comparison yet.</div></div><div class="card wide"><h3>Text Diff / Preview</h3><pre id=restorePreviewDiff class=log>No diff preview yet.</pre></div><div class=card><h3>Safety Lock</h3><div class=status>Preview only
No restore button
No overwrite
No copy-back
No delete
No install
No model cleanup</div></div></div></section>



<section id=restorestaging class=page><div class=hero><h2>Restore Staging Copy</h2><p>Copies a selected backup into a staging package only. It does not restore, overwrite, or touch the live target.</p></div><div class=grid><div class="card wide"><h3>Staging Control</h3><div class=grid><div><div class=small>Select Backup</div><select id=restoreStagingSelect onchange="q('restoreStagingPath').value=this.value"></select></div><div><div class=small>Or Backup Path</div><input id=restoreStagingPath placeholder="Z:\FOXAI\Backups\GeneratedFiles\..."></div></div><div class=small>Confirmation</div><input id=restoreStagingConfirm placeholder="Type STAGE to create staging copy only"><button onclick="loadRestoreStagingList()">Load Backup List</button><button onclick="stageRestoreCopy()">Stage Backup Copy</button><button onclick="sendRestoreStagingToMission()">Send Staging Result to Mission</button><div id=restoreStagingStatus class=status>No staging action run yet.</div></div><div class="card wide"><h3>Staging Result</h3><div id=restoreStagingResult class=status>No staged copy yet.</div></div><div class="card wide"><h3>Verification Checks</h3><div id=restoreStagingChecks class=scanlist>No verification yet.</div></div><div class=card><h3>Safety Lock</h3><div class=status>Staging copy only
No restore to original location
No live target overwrite
No copy-back
No delete
No install
No model cleanup
User confirmation required
Repair action log required
Verification required</div></div></div></section>



<section id=restorefinal class=page><div class=hero><h2>Restore Final Checklist</h2><p>Final proof wall before any future restore feature. This remains checklist-only and cannot restore files.</p></div><div class=grid><div class="card wide"><h3>Final Checklist Control</h3><div class=grid><div><div class=small>Select Staging Package</div><select id=restoreFinalSelect onchange="q('restoreFinalPath').value=this.value"></select></div><div><div class=small>Or Stage Folder / Package File Path</div><input id=restoreFinalPath placeholder="Z:\FOXAI\Reports\Backups\RestoreStaging\Stage_..."></div></div><button onclick="loadRestoreFinalList()">Load Staging Packages</button><button onclick="runRestoreFinal(false)">Run Final Checklist</button><button onclick="runRestoreFinal(true)">Export Final Checklist</button><button onclick="api('/api/open/final_checklist')">Open Final Checklist Reports</button><button onclick="sendRestoreFinalToMission()">Send Final Checklist to Mission</button><div id=restoreFinalStatus class=status>No final checklist run yet.</div></div><div class="card wide"><h3>Final Dashboard</h3><div id=restoreFinalDashboard class=status>No final result yet.</div></div><div class="card wide"><h3>Final Checks</h3><div id=restoreFinalChecks class=scanlist>No checks yet.</div></div><div class="card wide"><h3>Final Confirmation Phrase</h3><div id=restoreFinalPhrase class=status>No phrase generated yet.</div></div><div class=card><h3>Safety Lock</h3><div class=status>Final check only
No restore button
No restore endpoint
No overwrite
No copy-back
No delete
No install
No model cleanup</div></div></div></section>



<section id=restoreaudit class=page><div class=hero><h2>Post-Restore Audit Viewer</h2><p>Read-only audit view for completed restore actions, live-target backups, verification reports, and current target hash state.</p></div><div class=grid><div class="card wide"><h3>Audit Control</h3><div class=grid><div><div class=small>Filter</div><input id=restoreAuditFilter placeholder="optional: README, target, backup"></div><div><div class=small>Limit</div><input id=restoreAuditLimit value="1000"></div></div><button onclick="loadRestoreAudit(false)">Load Restore Audit</button><button onclick="loadRestoreAudit(true)">Export Restore Audit</button><button onclick="api('/api/open/restore_reports')">Open Restore Reports</button><button onclick="api('/api/open/restore_live_backups')">Open Live Target Backups</button><button onclick="api('/api/open/restore_audit')">Open Audit Exports</button><button onclick="sendRestoreAuditToMission()">Send Audit to Mission</button><div id=restoreAuditStatus class=status>No restore audit loaded yet.</div></div><div class="card wide"><h3>Audit Dashboard</h3><div id=restoreAuditDashboard class=status>No results yet.</div></div><div class="card wide"><h3>Actions by Status</h3><div id=restoreAuditStatusList class=scanlist>No status summary yet.</div></div><div class="card wide"><h3>Actions by Target</h3><div id=restoreAuditTargetList class=scanlist>No target summary yet.</div></div><div class="card wide"><h3>Restore Actions</h3><div id=restoreAuditList class=scanlist>No restore actions loaded yet.</div></div><div class=card><h3>Safety Model</h3><div class=status>Read-only audit viewer
No restore
No overwrite
No copy-back
No delete
No install
No model cleanup
Only optional audit export</div></div></div></section>



<section id=rollbackaction class=page><div class=hero><h2>Single-File Rollback Action</h2><p>Live rollback action. Narrow scope: one pre-restore backup, original target only, current target backed up before overwrite, exact phrase required.</p></div><div class=grid><div class="card wide"><h3>Rollback Control</h3><div class=grid><div><div class=small>Select Restore Action</div><select id=rollbackActionSelect onchange="q('rollbackActionPath').value=this.value"></select></div><div><div class=small>Or Restore Report / Live Backup / Target Path</div><input id=rollbackActionPath placeholder="Z:\FOXAI\Reports\Backups\RestoreActions\Single_File_Restore_...json"></div></div><button onclick="loadRollbackActionList()">Load Restore Actions</button><button onclick="preflightRollbackAction()">Run Rollback Preflight</button><div class=small>Exact Rollback Confirmation Phrase</div><input id=rollbackActionConfirm placeholder="Run preflight, then paste exact rollback phrase"><button onclick="runSingleFileRollback()">ROLLBACK SINGLE FILE</button><button onclick="sendRollbackActionToMission()">Send Rollback Result to Mission</button><div id=rollbackActionStatus class=status>No rollback action run yet.</div></div><div class="card wide"><h3>Preflight / Result</h3><pre id=rollbackActionResult class=log>No result yet.</pre></div><div class="card wide"><h3>Rollback Verification</h3><div id=rollbackActionChecks class=scanlist>No verification yet.</div></div><div class=card><h3>Scope Lock</h3><div class=status>Single file only
From pre-restore backup only
Original target only
Current target backup required before rollback
Exact confirmation phrase required
No folder rollback
No delete
No install
No model cleanup</div></div></div></section>



<section id=recoverytimeline class=page><div class=hero><h2>Recovery Timeline Viewer</h2><p>Read-only chain map for backup, staging, restore, restore audit, rollback, and rollback audit history.</p></div><div class=grid><div class="card wide"><h3>Timeline Control</h3><div class=grid><div><div class=small>Filter</div><input id=recoveryTimelineFilter placeholder="optional: README, target, backup"></div><div><div class=small>Limit</div><input id=recoveryTimelineLimit value="1000"></div></div><button onclick="loadRecoveryTimeline(false)">Load Recovery Timeline</button><button onclick="loadRecoveryTimeline(true)">Export Recovery Timeline</button><button onclick="api('/api/open/recovery_timeline')">Open Timeline Exports</button><button onclick="sendRecoveryTimelineToMission()">Send Timeline to Mission</button><div id=recoveryTimelineStatus class=status>No recovery timeline loaded yet.</div></div><div class="card wide"><h3>Timeline Dashboard</h3><div id=recoveryTimelineDashboard class=status>No results yet.</div></div><div class="card wide"><h3>Recovery Chains by Target</h3><div id=recoveryTimelineChains class=scanlist>No chains yet.</div></div><div class="card wide"><h3>Event Types</h3><div id=recoveryTimelineKinds class=scanlist>No event type summary yet.</div></div><div class="card wide"><h3>Timeline Events</h3><div id=recoveryTimelineEvents class=scanlist>No timeline events loaded yet.</div></div><div class=card><h3>Safety Model</h3><div class=status>Read-only timeline
No restore
No rollback
No overwrite
No copy-back
No delete
No install
No model cleanup
Only optional timeline export</div></div></div></section>

<section id=rollbackaudit class=page><div class=hero><h2>Rollback Audit Viewer</h2><p>Read-only audit view for completed rollback actions, pre-rollback backups, verification reports, and current target hash state.</p></div><div class=grid><div class="card wide"><h3>Audit Control</h3><div class=grid><div><div class=small>Filter</div><input id=rollbackAuditFilter placeholder="optional: README, target, backup"></div><div><div class=small>Limit</div><input id=rollbackAuditLimit value="1000"></div></div><button onclick="loadRollbackAudit(false)">Load Rollback Audit</button><button onclick="loadRollbackAudit(true)">Export Rollback Audit</button><button onclick="api('/api/open/rollback_reports')">Open Rollback Reports</button><button onclick="api('/api/open/rollback_live_backups')">Open Pre-Rollback Backups</button><button onclick="api('/api/open/rollback_audit')">Open Rollback Audit Exports</button><button onclick="sendRollbackAuditToMission()">Send Audit to Mission</button><div id=rollbackAuditStatus class=status>No rollback audit loaded yet.</div></div><div class="card wide"><h3>Audit Dashboard</h3><div id=rollbackAuditDashboard class=status>No results yet.</div></div><div class="card wide"><h3>Actions by Status</h3><div id=rollbackAuditStatusList class=scanlist>No status summary yet.</div></div><div class="card wide"><h3>Actions by Target</h3><div id=rollbackAuditTargetList class=scanlist>No target summary yet.</div></div><div class="card wide"><h3>Rollback Actions</h3><div id=rollbackAuditList class=scanlist>No rollback actions loaded yet.</div></div><div class=card><h3>Safety Model</h3><div class=status>Read-only audit viewer
No rollback
No restore
No overwrite
No copy-back
No delete
No install
No model cleanup
Only optional audit export</div></div></div></section>

<section id=rollbackpreview class=page><div class=hero><h2>Rollback Preview From Pre-Restore Backup</h2><p>Preview reversing a completed single-file restore using the pre-restore live backup. Preview only: no rollback action exists in this build.</p></div><div class=grid><div class="card wide"><h3>Rollback Preview Control</h3><div class=grid><div><div class=small>Select Restore Action</div><select id=rollbackPreviewSelect onchange="q('rollbackPreviewPath').value=this.value"></select></div><div><div class=small>Or Restore Report / Live Backup / Target Path</div><input id=rollbackPreviewPath placeholder="Z:\FOXAI\Reports\Backups\RestoreActions\Single_File_Restore_...json"></div></div><button onclick="loadRollbackPreviewActions()">Load Restore Actions</button><button onclick="runRollbackPreview(false)">Run Rollback Preview</button><button onclick="runRollbackPreview(true)">Export Rollback Preview</button><button onclick="api('/api/open/rollback_previews')">Open Rollback Preview Reports</button><button onclick="sendRollbackPreviewToMission()">Send Rollback Preview to Mission</button><div id=rollbackPreviewStatus class=status>No rollback preview run yet.</div></div><div class="card wide"><h3>Preview Dashboard</h3><div id=rollbackPreviewDashboard class=status>No preview yet.</div></div><div class="card wide"><h3>Preview Checks</h3><div id=rollbackPreviewChecks class=scanlist>No checks yet.</div></div><div class="card wide"><h3>Diff Preview</h3><pre id=rollbackPreviewDiff class=log>No diff preview yet.</pre></div><div class="card wide"><h3>Future Rollback Phrase</h3><div id=rollbackPreviewPhrase class=status>No phrase yet.</div></div><div class=card><h3>Safety Lock</h3><div class=status>Preview only
No rollback button
No rollback endpoint
No overwrite
No copy-back
No delete
No install
No model cleanup</div></div></div></section>

<section id=restoreaction class=page><div class=hero><h2>Single-File Restore Action</h2><p>First live restore action. Narrow scope: one staged file, original target only, live target backed up before overwrite, exact phrase required.</p></div><div class=grid><div class="card wide"><h3>Restore Control</h3><div class=grid><div><div class=small>Select Staging Package</div><select id=restoreActionSelect onchange="q('restoreActionPath').value=this.value"></select></div><div><div class=small>Or Stage Folder Path</div><input id=restoreActionPath placeholder="Z:\FOXAI\Reports\Backups\RestoreStaging\Stage_..."></div></div><button onclick="loadRestoreActionList()">Load Staging Packages</button><button onclick="preflightRestoreAction()">Run Restore Preflight</button><div class=small>Exact Confirmation Phrase</div><input id=restoreActionConfirm placeholder="Run preflight, then paste exact restore phrase"><button onclick="runSingleFileRestore()">RESTORE SINGLE FILE</button><button onclick="sendRestoreActionToMission()">Send Restore Result to Mission</button><div id=restoreActionStatus class=status>No restore action run yet.</div></div><div class="card wide"><h3>Preflight / Result</h3><pre id=restoreActionResult class=log>No result yet.</pre></div><div class="card wide"><h3>Restore Verification</h3><div id=restoreActionChecks class=scanlist>No verification yet.</div></div><div class=card><h3>Scope Lock</h3><div class=status>Single file only
From staging package only
Original target only
Pre-restore live backup required
Exact confirmation phrase required
No folder restore
No delete
No install
No model cleanup</div></div></div></section>

<section id=stagingpackages class=page><div class=hero><h2>Staging Package Viewer</h2><p>Read-only audit view for restore staging packages. Review staged copies, metadata, verification, and target-untouched proof.</p></div><div class=grid><div class="card wide"><h3>Package Control</h3><div class=grid><div><div class=small>Filter</div><input id=stagingPackageFilter placeholder="optional: README, manifest, risk, target"></div><div><div class=small>Limit</div><input id=stagingPackageLimit value="500"></div></div><button onclick="loadStagingPackages(false)">Load Staging Packages</button><button onclick="loadStagingPackages(true)">Export Staging Inventory</button><button onclick="api('/api/open/restore_staging')">Open Staging Folder</button><button onclick="api('/api/open/staging_inventory')">Open Inventory Reports</button><button onclick="sendStagingPackagesToMission()">Send Staging Inventory to Mission</button><div id=stagingPackageStatus class=status>No staging package inventory loaded yet.</div></div><div class="card wide"><h3>Package Dashboard</h3><div id=stagingPackageDashboard class=status>No results yet.</div></div><div class="card wide"><h3>Packages by Status</h3><div id=stagingPackageStatusList class=scanlist>No status summary yet.</div></div><div class="card wide"><h3>Packages by Preview Risk</h3><div id=stagingPackageRiskList class=scanlist>No risk summary yet.</div></div><div class="card wide"><h3>Staging Packages</h3><div id=stagingPackageList class=scanlist>No packages loaded yet.</div></div><div class=card><h3>Safety Model</h3><div class=status>Read-only package viewer
No restore
No overwrite
No copy-back
No delete
No install
No model cleanup
Only optional inventory export</div></div></div></section>

<section id=restoregate class=page><div class=hero><h2>Restore Readiness Gate</h2><p>Preview-only eligibility checklist for future restore. The restore lock remains active.</p></div><div class=grid><div class="card wide"><h3>Gate Control</h3><div class=grid><div><div class=small>Select Backup</div><select id=restoreGateSelect onchange="q('restoreGatePath').value=this.value"></select></div><div><div class=small>Or Backup Path</div><input id=restoreGatePath placeholder="Z:\FOXAI\Backups\GeneratedFiles\..."></div></div><button onclick="loadRestoreGateList()">Load Backup List</button><button onclick="runRestoreGate(false)">Run Readiness Gate</button><button onclick="runRestoreGate(true)">Export Readiness Report</button><button onclick="sendRestoreGateToMission()">Send Gate Report to Mission</button><div id=restoreGateStatus class=status>No restore gate run yet.</div></div><div class="card wide"><h3>Gate Dashboard</h3><div id=restoreGateDashboard class=status>No gate results yet.</div></div><div class="card wide"><h3>Gate Checks</h3><div id=restoreGateChecks class=scanlist>No gate checks yet.</div></div><div class="card wide"><h3>Future Confirmation Phrase</h3><div id=restoreGatePhrase class=status>No phrase generated yet.</div></div><div class=card><h3>Safety Lock</h3><div class=status>Restore remains blocked
No restore button
No restore endpoint
No overwrite
No copy-back
No delete
No install
No model cleanup</div></div></div></section>


<section id=repairops class=page><div class=hero><h2>Repair Shop Operations Dashboard</h2><p>One command view for RepairActions history, verified results, safe actions, generated backups, and Recovery Foundation health.</p></div><div class=grid><div class="card wide"><h3>Repair Shop Control</h3><button onclick="loadRepairOps(false)">Load Repair Shop</button><button onclick="loadRepairOps(true)">Export Repair Shop Report</button><button onclick="api('/api/open/repair_reports')">Open RepairActions</button><button onclick="api('/api/open/repair_ops_dashboard')">Open Repair Shop Reports</button><button onclick="api('/api/open/file_backups')">Open Generated Backups</button><button onclick="go('repairactions')">Open Safe Actions</button><button onclick="go('repairhistory')">Open Repair History</button><button onclick="go('backupvault')">Open Backup Vault</button><button onclick="go('recoverytimeline')">Open Recovery Timeline</button><button onclick="sendRepairOpsToMission()">Send Repair Shop to Mission</button><div id=repairOpsStatus class=status>No Repair Shop report loaded yet.</div></div><div class="card wide"><h3>Operations Dashboard</h3><div id=repairOpsDashboard class=status>No dashboard yet.</div></div><div class="card wide"><h3>Safe Actions</h3><div id=repairOpsActions class=scanlist>No action plan loaded yet.</div></div><div class="card wide"><h3>Action Types</h3><div id=repairOpsByAction class=scanlist>No action history loaded yet.</div></div><div class="card wide"><h3>Recent Repair Logs</h3><div id=repairOpsRecent class=scanlist>No recent logs loaded yet.</div></div><div class="card wide"><h3>Backup + Recovery Coupling</h3><div id=repairOpsBackupRecovery class=status>No backup/recovery summary yet.</div></div><div class=card><h3>Safety Model</h3><div class=status>Read-only operations dashboard
No repair action
No restore
No rollback
No overwrite
No copy-back
No delete
No install
No model cleanup
Only optional dashboard export</div></div></div></section>


<section id=repairdetail class=page><div class=hero><h2>Repair Action Detail Viewer</h2><p>Read-only drill-down for one RepairActions log: verification checks, target, backup, related reports, and safety state.</p></div><div class=grid><div class="card wide"><h3>Detail Control</h3><div class=grid><div><div class=small>Select Repair Log</div><select id=repairDetailSelect onchange="q('repairDetailPath').value=this.value"></select></div><div><div class=small>Or Log Path / Action Search</div><input id=repairDetailPath placeholder="Z:\FOXAI\Reports\RepairActions\Repair_Action_...json"></div></div><button onclick="loadRepairDetailList()">Load Repair Logs</button><button onclick="loadRepairDetail(false)">Load Detail</button><button onclick="loadRepairDetail(true)">Export Detail</button><button onclick="api('/api/open/repair_action_details')">Open Detail Reports</button><button onclick="sendRepairDetailToMission()">Send Detail to Mission</button><div id=repairDetailStatus class=status>No repair action detail loaded yet.</div></div><div class="card wide"><h3>Action Summary</h3><div id=repairDetailSummary class=status>No summary yet.</div></div><div class="card wide"><h3>Verification Checks</h3><div id=repairDetailVerification class=scanlist>No verification yet.</div></div><div class="card wide"><h3>Target + Backup</h3><div id=repairDetailFiles class=status>No file state yet.</div></div><div class="card wide"><h3>Related Paths</h3><div id=repairDetailRelated class=scanlist>No related paths yet.</div></div><div class="card wide"><h3>Detail Safety Checks</h3><div id=repairDetailChecks class=scanlist>No detail checks yet.</div></div><div class=card><h3>Safety Model</h3><div class=status>Read-only detail viewer
No repair action
No restore
No rollback
No overwrite
No copy-back
No delete
No install
No model cleanup
Only optional detail export</div></div></div></section>

<section id=repairtickets class=page><div class=hero><h2>Repair Ticket Queue</h2><p>Read-only triage board for Build Verify, Env Verify, Portable Ready, Model Check, Scan Bridge, RepairActions, Backup Vault, and Recovery Foundation.</p></div><div class=grid><div class="card wide"><h3>Ticket Queue Control</h3><button onclick="loadRepairTickets(false)">Load Ticket Queue</button><button onclick="loadRepairTickets(true)">Export Ticket Queue</button><button onclick="api('/api/open/repair_tickets')">Open Ticket Reports</button><button onclick="go('repairops')">Open Repair Shop</button><button onclick="go('repairactions')">Open Safe Actions</button><button onclick="go('repairticketdetail')">Open Ticket Detail</button><button onclick="go('buildverify')">Open Build Verify</button><button onclick="go('envverify')">Open Env Verify</button><button onclick="go('portableready')">Open Portable Ready</button><button onclick="go('modelcheck')">Open Model Check</button><button onclick="sendRepairTicketsToMission()">Send Tickets to Mission</button><div id=repairTicketStatus class=status>No ticket queue loaded yet.</div></div><div class="card wide"><h3>Ticket Dashboard</h3><div id=repairTicketDashboard class=status>No dashboard yet.</div></div><div class="card wide"><h3>Active Tickets</h3><div id=repairTicketActive class=scanlist>No active tickets loaded yet.</div></div><div class="card wide"><h3>Available Action Tickets</h3><div id=repairTicketActions class=scanlist>No action tickets loaded yet.</div></div><div class="card wide"><h3>Informational / Historical Tickets</h3><div id=repairTicketInfo class=scanlist>No informational tickets loaded yet.</div></div><div class="card wide"><h3>Healthy Checks</h3><div id=repairTicketHealthy class=scanlist>No healthy checks loaded yet.</div></div><div class=card><h3>Safety Model</h3><div class=status>Read-only ticket queue
No repair action
No restore
No rollback
No overwrite
No copy-back
No delete
No install
No model cleanup
Only optional ticket export</div></div></div></section>


<section id=repairticketdetail class=page><div class=hero><h2>Repair Ticket Detail Viewer</h2><p>Read-only inspection clipboard for one Repair Ticket: evidence, source, suggested action, safe action match, and related report paths.</p></div><div class=grid><div class="card wide"><h3>Ticket Detail Control</h3><div class=grid><div><div class=small>Select Ticket</div><select id=repairTicketDetailSelect onchange="q('repairTicketDetailQuery').value=this.value"></select></div><div><div class=small>Or Ticket ID / Search</div><input id=repairTicketDetailQuery placeholder="optional_repair_tools_missing"></div></div><button onclick="loadRepairTicketDetailList()">Load Ticket List</button><button onclick="loadRepairTicketDetail(false)">Load Ticket Detail</button><button onclick="loadRepairTicketDetail(true)">Export Ticket Detail</button><button onclick="api('/api/open/repair_ticket_details')">Open Ticket Detail Reports</button><button onclick="go('repairtickets')">Open Ticket Queue</button><button onclick="go('repairactions')">Open Safe Actions</button><button onclick="sendRepairTicketDetailToMission()">Send Ticket Detail to Mission</button><div id=repairTicketDetailStatus class=status>No ticket detail loaded yet.</div></div><div class="card wide"><h3>Ticket Summary</h3><div id=repairTicketDetailSummary class=status>No summary yet.</div></div><div class="card wide"><h3>Evidence</h3><div id=repairTicketDetailEvidence class=scanlist>No evidence yet.</div></div><div class="card wide"><h3>Suggested / Safe Action</h3><div id=repairTicketDetailAction class=status>No action match yet.</div></div><div class="card wide"><h3>Related Paths</h3><div id=repairTicketDetailRelated class=scanlist>No related paths yet.</div></div><div class="card wide"><h3>Detail Checks</h3><div id=repairTicketDetailChecks class=scanlist>No detail checks yet.</div></div><div class=card><h3>Safety Model</h3><div class=status>Read-only ticket detail viewer
No repair action
No restore
No rollback
No overwrite
No copy-back
No delete
No install
No model cleanup
Only optional ticket detail export</div></div></div></section>


<section id=ticketbridge class=page><div class=hero><h2>Ticket-to-Approved-Action Bridge</h2><p>Read-only bridge from a Repair Ticket to its matching safe action. It prepares context, but still requires manual approval in Repair Actions.</p></div><div class=grid><div class="card wide"><h3>Bridge Control</h3><div class=grid><div><div class=small>Select Ticket</div><select id=ticketBridgeSelect onchange="q('ticketBridgeQuery').value=this.value"></select></div><div><div class=small>Or Ticket ID / Search</div><input id=ticketBridgeQuery placeholder="optional_repair_tools_missing"></div></div><button onclick="loadTicketBridgeList()">Load Ticket List</button><button onclick="loadTicketBridge(false)">Load Bridge</button><button onclick="loadTicketBridge(true)">Export Bridge Report</button><button onclick="api('/api/open/repair_ticket_bridges')">Open Bridge Reports</button><button onclick="go('repairticketdetail')">Open Ticket Detail</button><button onclick="bridgeOpenRepairActions()">Open Repair Actions with Context</button><button onclick="sendTicketBridgeToMission()">Send Bridge to Mission</button><div id=ticketBridgeStatus class=status>No bridge loaded yet.</div></div><div class="card wide"><h3>Bridge Summary</h3><div id=ticketBridgeSummary class=status>No summary yet.</div></div><div class="card wide"><h3>Matching Safe Action</h3><div id=ticketBridgeAction class=status>No action match yet.</div></div><div class="card wide"><h3>Manual Next Steps</h3><div id=ticketBridgeSteps class=scanlist>No steps yet.</div></div><div class="card wide"><h3>Bridge Checks</h3><div id=ticketBridgeChecks class=scanlist>No checks yet.</div></div><div class="card wide"><h3>Related Paths</h3><div id=ticketBridgeRelated class=scanlist>No paths yet.</div></div><div class=card><h3>Safety Model</h3><div class=status>Read-only ticket/action bridge
No repair action
No restore
No rollback
No overwrite
No copy-back
No delete
No install
No model cleanup
Only optional bridge export</div></div></div></section>


<section id=repairsession class=page><div class=hero><h2>Repair Shop Session Report</h2><p>Chief Engineering end-of-shift summary: Repair Shop health, tickets, backups, Recovery Foundation, recent actions, and recommended next steps.</p></div><div class=grid><div class="card wide"><h3>Session Controls</h3><button onclick="loadRepairSession(false)">Load Session Report</button><button onclick="loadRepairSession(true)">Export Session Report</button><button onclick="api('/api/open/repair_session_reports')">Open Session Reports</button><button onclick="go('repairops')">Open Repair Shop</button><button onclick="go('repairtickets')">Open Ticket Queue</button><button onclick="go('ticketbridge')">Open Ticket Bridge</button><button onclick="sendRepairSessionToMission()">Send Session to Mission</button><div id=repairSessionStatus class=status>No session report loaded yet.</div></div><div class="card wide"><h3>Chief Engineering Summary</h3><div id=repairSessionSummary class=status>No summary yet.</div></div><div class="card wide"><h3>What Changed This Session</h3><div id=repairSessionChanged class=scanlist>No recent changes loaded yet.</div></div><div class="card wide"><h3>Active Tickets</h3><div id=repairSessionTickets class=scanlist>No tickets loaded yet.</div></div><div class="card wide"><h3>Recommended Next</h3><div id=repairSessionNext class=scanlist>No recommendations loaded yet.</div></div><div class="card wide"><h3>Safe To Ignore / Historical</h3><div id=repairSessionIgnore class=scanlist>No historical items loaded yet.</div></div><div class=card><h3>Safety Model</h3><div class=status>Read-only session report
No repair action
No restore
No rollback
No overwrite
No copy-back
No delete
No install
No model cleanup
Only optional session export</div></div></div></section>


<section id=repairfreeze class=page><div class=hero><h2>Repair Shop Milestone Freeze</h2><p>Formal freeze report for the v10.9.x Repair Shop foundation: proven modules, safety contract, recommendations, and readiness to move to the next milestone.</p></div><div class=grid><div class="card wide"><h3>Freeze Controls</h3><button onclick="loadRepairFreeze(false)">Load Milestone Freeze</button><button onclick="loadRepairFreeze(true)">Export Milestone Freeze</button><button onclick="api('/api/open/repair_milestone_freeze')">Open Freeze Reports</button><button onclick="go('repairsession')">Open Session Report</button><button onclick="go('repairops')">Open Repair Shop</button><button onclick="sendRepairFreezeToMission()">Send Freeze to Mission</button><div id=repairFreezeStatus class=status>No milestone freeze loaded yet.</div></div><div class="card wide"><h3>Freeze Summary</h3><div id=repairFreezeSummary class=status>No summary yet.</div></div><div class="card wide"><h3>Proven Modules</h3><div id=repairFreezeModules class=scanlist>No modules loaded yet.</div></div><div class="card wide"><h3>Recommendations</h3><div id=repairFreezeRecommendations class=scanlist>No recommendations loaded yet.</div></div><div class="card wide"><h3>Safety Contract</h3><div id=repairFreezeSafety class=status>No safety contract loaded yet.</div></div><div class="card wide"><h3>Problems / Review Items</h3><div id=repairFreezeProblems class=scanlist>No review items loaded yet.</div></div></div></section>

<section id=backupvault class=page><div class=hero><h2>Backup Vault Viewer</h2><p>Rollback visibility for generated-file backups. Read-only inventory before stronger Repair Bay powers. Windows Date modified may reflect original file metadata, so this page separates file-modified time from action-created time.</p></div><div class=grid><div class="card wide"><h3>Backup Vault Control</h3><div class=grid><div><div class=small>Filter</div><input id=backupVaultFilter placeholder="optional: manifest, README, dependency, action name"></div><div><div class=small>Limit</div><input id=backupVaultLimit value="500"></div></div><button onclick="loadBackupVault(false)">Load Backup Vault</button><button onclick="loadBackupVault(true)">Export Backup Inventory</button><button onclick="api('/api/open/file_backups')">Open Backup Folder</button><button onclick="sendBackupVaultToMission()">Send Backup Inventory to Mission</button><div id=backupVaultStatus class=status>No backup vault inventory loaded yet.</div></div><div class="card wide"><h3>Backup Dashboard</h3><div id=backupVaultDashboard class=status>No results yet.</div></div><div class="card wide"><h3>Backups by Type</h3><div id=backupVaultTypes class=scanlist>No type summary yet.</div></div><div class="card wide"><h3>Backups by Repair Action</h3><div id=backupVaultActions class=scanlist>No action summary yet.</div></div><div class="card wide"><h3>Backup Files</h3><div id=backupVaultFiles class=scanlist>No backup files loaded yet.</div></div><div class=card><h3>Safety Model</h3><div class=status>Read-only backup viewer
No restore yet
No deletes
No installs
No model cleanup
Only optional inventory export</div></div></div></section>

<section id=logs class=page><div class=hero><h2>Logs</h2></div><div class=card><button onclick="api('/api/open/logs')">Open Logs</button><div id=status2 class=status></div></div></section>
<section id=settings class=page><div class=hero><h2>Settings</h2></div><div class=card><div id=paths class=status></div><button onclick="api('/api/open-url/github')">Open GitHub</button></div></section>
</main></div><div id=toast></div><script>
let activeProject=null, curLib='', missionData=null; const chat=document.getElementById('chatLog');
function q(id){return document.getElementById(id)}function toast(s){q('toast').textContent=s;q('toast').style.display='block';setTimeout(()=>q('toast').style.display='none',4200)}
function pg(id,b){if(id==='dash')setTimeout(()=>loadRecoveryDashboard(),0); if(id==='commandcenter')setTimeout(()=>loadCommandCenter(false),0); if(id==='commanddetail')setTimeout(()=>loadCommandDetailList(),0); if(id==='commandarchive')setTimeout(()=>loadCommandArchive(false),0); if(id==='commandfreeze')setTimeout(()=>loadCommandFreeze(false),0); if(id==='kayockwriter')setTimeout(()=>loadKayockWriter(false),0); if(id==='storyforge')setTimeout(()=>loadStoryForge(false),0); if(id==='storymanifest')setTimeout(()=>loadStoryManifest(false),0); if(id==='projectgate')setTimeout(()=>loadProjectGate(false),0);document.querySelectorAll('.page').forEach(x=>x.classList.remove('active'));q(id).classList.add('active');document.querySelectorAll('.nav').forEach(x=>x.classList.remove('active'));if(b)b.classList.add('active'); if(id==='projects')loadProjects(); if(id==='memory')loadMemory(); if(id==='library'){loadLib(curLib);loadIronIndexStatus(); if(q('libResults')&&!q('libResults').innerHTML.trim())searchLib()} if(id==='novelforge'){loadNovelForgeList();setTimeout(updateCodexDashboard,0)} if(id==='prompts')loadPrompts(); if(id==='extensions')loadExtensions(); if(id==='scanbridge'&&!q('scanPath').value)q('scanPath').value='Departments'; if(id==='projectgen')setTimeout(refreshProjectDocsStatus,0); if(id==='repairhistory')setTimeout(()=>loadRepairHistory(false),0); if(id==='repairops')setTimeout(()=>loadRepairOps(false),0); if(id==='repairdetail')setTimeout(()=>loadRepairDetailList(),0); if(id==='repairtickets')setTimeout(()=>loadRepairTickets(false),0); if(id==='repairticketdetail')setTimeout(()=>loadRepairTicketDetailList(),0); if(id==='ticketbridge')setTimeout(()=>loadTicketBridgeList(),0); if(id==='repairsession')setTimeout(()=>loadRepairSession(false),0); if(id==='repairfreeze')setTimeout(()=>loadRepairFreeze(false),0); if(id==='backupvault')setTimeout(()=>loadBackupVault(false),0); if(id==='restorepreview')setTimeout(()=>loadRestoreBackupList(),0); if(id==='restoregate')setTimeout(()=>loadRestoreGateList(),0); if(id==='restorestaging')setTimeout(()=>loadRestoreStagingList(),0); if(id==='stagingpackages')setTimeout(()=>loadStagingPackages(false),0); if(id==='restorefinal')setTimeout(()=>loadRestoreFinalList(),0); if(id==='restoreaction')setTimeout(()=>loadRestoreActionList(),0); if(id==='restoreaudit')setTimeout(()=>loadRestoreAudit(false),0); if(id==='rollbackpreview')setTimeout(()=>loadRollbackPreviewActions(),0); if(id==='rollbackaction')setTimeout(()=>loadRollbackActionList(),0); if(id==='rollbackaudit')setTimeout(()=>loadRollbackAudit(false),0); if(id==='recoverytimeline')setTimeout(()=>loadRecoveryTimeline(false),0)}
function go(id){let b=[...document.querySelectorAll('.nav')].find(x=>x.getAttribute('onclick')?.includes("'"+id+"'"));pg(id,b)}function goMemory(){go('memory')}
async function api(u,opt){try{let r=await fetch(u,opt);let d=await r.json();toast(d.message||JSON.stringify(d));refresh();return d}catch(e){toast('Request failed: '+e)}}function esc(s){return String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]))}function js(s){return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'")}
function logline(c,w,m){chat.innerHTML+=`<span class=${c}>[${w}]</span> ${esc(m)}\n\n`;chat.scrollTop=chat.scrollHeight}function think(on){q('pulse').innerHTML=on?'<span class=pulse></span>':'';q('ms').textContent=on?'THINKING':'READY'}
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
async function loadMemory(){let d=await (await fetch('/api/memory/current')).json();missionData=d;if(!d.ok){q('memstate').textContent=d.message;q('resume').textContent='No active mission.';q('tasks').textContent='No tasks.';q('timeline').textContent='No timeline.';return}let m=d.mission;let state=`Project: ${m.project}\nCurrent task: ${m.current_task||'None'}\nProfessor: ${m.active_professor_name}\nModel: ${m.active_model_name||'None'}\nCreated: ${m.created}\nLast opened: ${m.last_opened}\nEvents: ${d.timeline.length}\nTasks: ${d.tasks.length}`;q('memstate').textContent=state;q('resume').textContent=state;q('tasks').innerHTML=d.tasks.length?d.tasks.map((t,i)=>`<div><input type=checkbox ${t.done?'checked':''} onchange="toggleTask(${i},this.checked)"> <span class="${t.done?'done':''}">${esc(t.text)}</span></div>`).join(''):'No tasks yet.';q('timeline').innerHTML=d.timeline.slice().reverse().slice(0,35).map(e=>`<div class=tl><div class=time>${esc(e.time)}</div>${esc(e.event)}</div>`).join('')||'No timeline yet.'}
async function addTask(){let text=q('task').value.trim();if(!text)return toast('Enter a task.');await api('/api/memory/task/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});q('task').value='';loadMemory()}
async function toggleTask(index,done){await api('/api/memory/task/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({index,done})});loadMemory()}
function resumeMission(){if(!missionData?.ok){toast('Select a project first.');go('projects');return}let m=missionData.mission;go('mission');q('input').value=`Resume mission "${m.project}". Current task: ${m.current_task||'None'}. Active professor: ${m.active_professor_name}. What should we do next?`;toast('Mission context loaded.')}




function libraryQuestion(){
    return (q('libAskQuestion')?.value||'').trim()||'Analyze this Iron Library file. Tell me what matters, what I should do next, and any risks or useful connections.';
}
async function askProfessorAboutLib(rel){
    try{
        let d=await (await fetch('/api/library/preview?path='+encodeURIComponent(rel)+'&limit=9000')).json();
        go('mission');
        if(d.ok){
            q('input').value=`Iron Library request for the active professor.

Question:
${libraryQuestion()}

File:
Library/${d.rel_path}

Type: ${d.ext}
Size: ${d.size}
Modified: ${d.modified}

Preview:
${d.content}`;
        }else{
            q('input').value=`Iron Library request for the active professor.

Question:
${libraryQuestion()}

File:
Library/${rel}

Preview unavailable:
${d.message||'This file type is not previewable yet. Use the file path and available metadata only.'}`;
        }
        toast('Library question sent to Mission Console input.');
    }catch(e){
        go('mission');
        q('input').value=`Iron Library request for the active professor.

Question:
${libraryQuestion()}

File:
Library/${rel}

Note: Preview failed: ${e}`;
        toast('Library path sent with preview error.');
    }
}

async function loadIronIndexStatus(){
    if(!q('ironIndexStatus'))return;
    try{
        let d=await (await fetch('/api/library/index/status')).json();
        q('ironIndexStatus').textContent=d.index_found?`Index built: ${d.built}\nItems: ${d.items}\nScanned: ${d.scanned}\nSkipped: ${d.skipped}\nIndex: ${d.index_file}`:'No Iron Library index found yet.';
    }catch(e){q('ironIndexStatus').textContent='Index status failed: '+e}
}
async function buildIronIndex(){
    if(!q('ironIndexStatus'))return;
    q('ironIndexStatus').textContent='Building Iron Library index... this may take a moment.';
    try{
        let d=await (await fetch('/api/library/index/build?max_files=2000')).json();
        q('ironIndexStatus').textContent=`${d.message}\nBuilt: ${d.built}\nScanned: ${d.scanned}\nSkipped: ${d.skipped}\nIndex: ${d.index_file}`;
        toast(d.message||'Index built.');
    }catch(e){q('ironIndexStatus').textContent='Index build failed: '+e}
}
async function searchIronIndex(){
    if(!q('ironIndexResults'))return;
    let term=q('ironIndexSearch')?.value||'';
    if(!term.trim()){toast('Enter an indexed text search term.');return}
    q('ironIndexResults').textContent='Searching index...';
    try{
        let d=await (await fetch('/api/library/index/search?q='+encodeURIComponent(term)+'&limit=100')).json();
        if(!d.ok){q('ironIndexResults').textContent=d.message||'Index search unavailable.';return}
        if(!d.results?.length){q('ironIndexResults').innerHTML=`No indexed matches for "${esc(term)}".`;return}
        q('ironIndexResults').innerHTML=`<div class=time>Index built: ${esc(d.built||'unknown')} • Results: ${d.count}</div>`+d.results.map(it=>{
            let icon=({'.md':'📝','.txt':'📝','.log':'📜','.json':'{}','.py':'🐍','.js':'🟨','.html':'🌐','.css':'🎨'}[it.ext]||'📄');
            return `<div class=indexresult><h4>${icon} ${esc(it.name)}</h4><span class=libbadge>${esc(it.ext||'file')}</span><span class=libbadge>${esc(it.size||'')}</span><span class=indexscore>score ${esc(it.score)}</span><div class=libmeta>${esc(it.rel_path)}<br>Modified: ${esc(it.modified||'')}</div><button onclick="previewLib('${js(it.rel_path)}')">Preview</button><button onclick="askProfessorAboutLib('${js(it.rel_path)}')">Ask Professor</button><button onclick="api('/api/library/open?path=${encodeURIComponent(it.rel_path)}')">Open File</button><button onclick="copyLibPath('${js(it.rel_path)}')">Copy Path</button><button onclick="sendLibPath('${js(it.rel_path)}')">Send Path</button><button onclick="sendLibPreview('${js(it.rel_path)}')">Send Preview</button><div class=indexsnippet>${esc(it.snippet||'')}</div></div>`
        }).join('');
    }catch(e){q('ironIndexResults').textContent='Index search failed: '+e}
}

async function previewLib(rel){
    if(!q('libPreview'))return;
    q('libPreview').textContent='Loading preview...';
    try{
        let d=await (await fetch('/api/library/preview?path='+encodeURIComponent(rel)+'&limit=16000')).json();
        if(!d.ok){
            q('libPreview').innerHTML=`<div class=warn>${esc(d.message||'Preview unavailable.')}</div><br><div class=copypath>${esc(rel)}</div><button onclick="api('/api/library/open?path=${encodeURIComponent(rel)}')">Open File</button><button onclick="askProfessorAboutLib('${js(rel)}')">Ask Professor</button><button onclick="copyLibPath('${js(rel)}')">Copy Path</button><button onclick="sendLibPath('${js(rel)}')">Send Path</button>`;
            return;
        }
        let trunc=d.truncated?`\n\n--- Preview truncated at 16,000 characters. Open the file for full content. ---`:'';
        q('libPreview').innerHTML=`<div class=previewhead><button onclick="api('/api/library/open?path=${encodeURIComponent(d.rel_path)}')">Open File</button><button onclick="askProfessorAboutLib('${js(d.rel_path)}')">Ask Professor</button><button onclick="copyLibPath('${js(d.rel_path)}')">Copy Path</button><button onclick="sendLibPath('${js(d.rel_path)}')">Send Path</button><button onclick="sendLibPreview('${js(d.rel_path)}')">Send Preview</button></div><div class=copypath>${esc(d.rel_path)} • ${esc(d.size)} • ${esc(d.modified)}</div><div class=previewbox>${esc(d.content+trunc)}</div>`;
    }catch(e){
        q('libPreview').textContent='Preview failed: '+e;
    }
}
function copyLibPath(rel){
    navigator.clipboard?.writeText('Library/'+rel);
    toast('Library path copied.');
}
function sendLibPath(rel){
    go('mission');
    q('input').value=`Please help me with this Iron Library file:\nLibrary/${rel}`;
    toast('Library path sent to Mission Console input.');
}
async function sendLibPreview(rel){
    try{
        let d=await (await fetch('/api/library/preview?path='+encodeURIComponent(rel)+'&limit=8000')).json();
        go('mission');
        if(d.ok){
            q('input').value=`Please help me analyze this Iron Library file.\n\nPath: Library/${d.rel_path}\nType: ${d.ext}\nSize: ${d.size}\n\nPreview:\n${d.content}`;
        }else{
            q('input').value=`Please help me with this Iron Library file:\nLibrary/${rel}\n\nNote: ${d.message||'Preview unavailable.'}`;
        }
        toast('Library preview sent to Mission Console input.');
    }catch(e){toast('Could not send preview: '+e)}
}

async function searchLib(){
    if(!q('libResults'))return;
    let term=q('libSearch')?.value||'';
    let type=q('libType')?.value||'all';
    q('libSearchStatus').textContent='Searching Iron Library...';
    try{
        let d=await (await fetch('/api/library/search?q='+encodeURIComponent(term)+'&type='+encodeURIComponent(type)+'&limit=250')).json();
        q('libSearchStatus').textContent=`Found ${d.count} result(s). Scanned ${d.scanned} item(s).`;
        if(!d.results?.length){
            q('libResults').innerHTML='No matching library items.';
            return;
        }
        q('libResults').innerHTML=d.results.map(it=>{
            let icon=it.is_dir?'📁':({'.pdf':'📕','.md':'📝','.txt':'📝','.docx':'📄','.doc':'📄','.png':'🖼️','.jpg':'🖼️','.jpeg':'🖼️','.webp':'🖼️','.py':'🐍','.js':'🟨','.html':'🌐','.css':'🎨'}[it.ext]||'📄');
            let action=it.is_dir?`<button onclick="loadLib('${js(it.rel_path)}');go('library')">Open Folder</button><button onclick="copyLibPath('${js(it.rel_path)}')">Copy Path</button><button onclick="sendLibPath('${js(it.rel_path)}')">Send Path</button>`:`<button onclick="previewLib('${js(it.rel_path)}')">Preview</button><button onclick="askProfessorAboutLib('${js(it.rel_path)}')">Ask Professor</button><button onclick="api('/api/library/open?path=${encodeURIComponent(it.rel_path)}')">Open File</button><button onclick="copyLibPath('${js(it.rel_path)}')">Copy Path</button><button onclick="sendLibPath('${js(it.rel_path)}')">Send Path</button>`;
            return `<div class=libresult><h4>${icon} ${esc(it.name)}</h4><span class=libbadge>${esc(it.ext||'file')}</span><span class=libbadge>${esc(it.size||'folder')}</span><div class=libmeta>${esc(it.rel_path)}<br>Modified: ${esc(it.modified||'')}</div>${action}</div>`
        }).join('');
    }catch(e){
        q('libSearchStatus').textContent='Library search failed: '+e;
    }
}

async function loadLib(rel=''){curLib=rel;let d=await (await fetch('/api/library/list?path='+encodeURIComponent(rel))).json();q('libpath').textContent=d.display_path||'Library';if(!d.ok){q('liblist').textContent=d.message;return}q('liblist').innerHTML='<table><tr><th>Name</th><th>Type</th><th>Size</th><th>Action</th></tr>'+d.items.map(it=>`<tr><td>${it.is_dir?'📁':'📄'} ${esc(it.name)}</td><td>${it.is_dir?'folder':it.ext}</td><td>${it.size}</td><td>${it.is_dir?`<button class=link onclick="loadLib('${js(it.rel_path)}')">Open</button>`:`<button class=link onclick="previewLib('${js(it.rel_path)}')">Preview</button> <button class=link onclick="askProfessorAboutLib('${js(it.rel_path)}')">Ask Professor</button> <button class=link onclick="api('/api/library/open?path=${encodeURIComponent(it.rel_path)}')">Open File</button>`}</td></tr>`).join('')+'</table>'}
function libUp(){let a=curLib.split(/[\\/]/).filter(Boolean);a.pop();loadLib(a.join('/'))}




let activeUniverseName=null;





let nfSceneCards=[];
function starterSceneLines(){
    return [
        'Book 1: Prophecy Discovery | Anthony / Whisper | Pueblo tunnels | Anthony, Chee | Anthony learns the prophecy is not just vampire politics but a possible end to the blood curse. | Anthony distrusts the source and fears being used. | Anthony accepts that Kayock’s legacy is now his problem. | Plant prophecy rules; keep reader knowledge limited.',
        'Book 1: Kayock Falls | Anthony / Whisper | Kayock’s lair | Anthony, Kayock, Jokaya | Kayock’s death transfers emotional and mythic weight to Anthony. | Jokaya proves she can kill even the first vampire. | Anthony inherits the mission without understanding all of it. | Define how Kayock can die and what remains active.',
        'Book 1: The Ex Revealed | Anthony / Whisper | Modern Pueblo | Anthony, ex, Jokaya shadow | Personal stakes collide with vampire prophecy. | Anthony learns his ex has been turned but not what she has become. | Book 2 hook is created. | Tie her transformation to Jokaya experiments or prophecy misunderstanding.',
        'Book 2: Olmec Clue Site | Anthony / Whisper | Olmec pyramid | Anthony, Croatoan clues, Thoth records | Anthony follows evidence toward Croatoan and the crystal skull mystery. | The clues suggest an escape that should have been impossible. | Croatoan becomes an active future threat. | Use claw marks, broken pedestal, mismatched glyphs, ancient blood.'
    ];
}
function parseSceneLine(line){
    let raw=String(line||'').trim();
    if(!raw)return null;
    let parts=raw.split('|').map(x=>x.trim());
    if(parts.length>=8)return {title:parts[0],pov:parts[1],location:parts[2],characters:parts[3],purpose:parts[4],conflict:parts[5],outcome:parts[6],canon:parts.slice(7).join(' | ')};
    return {title:raw,pov:'',location:'',characters:'',purpose:'',conflict:'',outcome:'',canon:''};
}
function sceneCardToLine(sc){
    return `${(sc.title||'Untitled Scene').trim()} | ${(sc.pov||'').trim()} | ${(sc.location||'').trim()} | ${(sc.characters||'').trim()} | ${(sc.purpose||'').replace(/\r?\n/g,' ').trim()} | ${(sc.conflict||'').replace(/\r?\n/g,' ').trim()} | ${(sc.outcome||'').replace(/\r?\n/g,' ').trim()} | ${(sc.canon||'').replace(/\r?\n/g,' ').trim()}`;
}
function syncScenesFromText(){
    if(!q('nfScenes'))return;
    nfSceneCards=(q('nfScenes').value||'').split(/\r?\n/).map(parseSceneLine).filter(Boolean);
}
function syncScenesToText(){
    if(!q('nfScenes'))return;
    q('nfScenes').value=nfSceneCards.map(sceneCardToLine).join('\n');
    updateNovelCounts();
}
function renderSceneCards(){
    if(!q('nfSceneCards'))return;
    syncScenesToText();
    if(!nfSceneCards.length){q('nfSceneCards').innerHTML='No scenes yet.';return}
    q('nfSceneCards').innerHTML=nfSceneCards.map((sc,i)=>`<div class=scenecard><h4>🎬 ${esc(sc.title||'Untitled Scene')}</h4><span class=scenetag>POV: ${esc(sc.pov||'unknown')}</span><span class=scenetag>${esc(sc.location||'no location')}</span><span class=scenetag>${esc(sc.characters||'no characters')}</span><div class=scenedetails><b>Purpose:</b> ${esc(sc.purpose||'None')}\n<b>Conflict:</b> ${esc(sc.conflict||'None')}\n<b>Outcome:</b> ${esc(sc.outcome||'None')}\n<b>Canon:</b> ${esc(sc.canon||'None')}</div><div class=sceneactions><button onclick="editSceneCard(${i})">Edit</button><button onclick="moveSceneCard(${i},-1)">Up</button><button onclick="moveSceneCard(${i},1)">Down</button><button onclick="deleteSceneCard(${i})">Delete</button><button onclick="sendSceneBrief(${i})">Send Brief</button><button onclick="generateSceneDraft(${i})">Generate Draft</button></div></div>`).join('');
}
function addSceneCard(){
    let title=q('nfSceneTitle').value.trim();
    if(!title){toast('Enter a scene title before adding.');return}
    nfSceneCards.push({title,pov:q('nfScenePOV').value.trim(),location:q('nfSceneLocation').value.trim(),characters:q('nfSceneCharacters').value.trim(),purpose:q('nfScenePurpose').value.trim(),conflict:q('nfSceneConflict').value.trim(),outcome:q('nfSceneOutcome').value.trim(),canon:q('nfSceneCanon').value.trim()});
    ['nfSceneTitle','nfScenePOV','nfSceneLocation','nfSceneCharacters','nfScenePurpose','nfSceneConflict','nfSceneOutcome','nfSceneCanon'].forEach(id=>q(id).value='');
    renderSceneCards();
    toast('Scene added.');
}
function editSceneCard(i){
    let sc=nfSceneCards[i]; if(!sc)return;
    q('nfSceneTitle').value=sc.title||''; q('nfScenePOV').value=sc.pov||''; q('nfSceneLocation').value=sc.location||''; q('nfSceneCharacters').value=sc.characters||''; q('nfScenePurpose').value=sc.purpose||''; q('nfSceneConflict').value=sc.conflict||''; q('nfSceneOutcome').value=sc.outcome||''; q('nfSceneCanon').value=sc.canon||'';
    nfSceneCards.splice(i,1); renderSceneCards(); toast('Scene loaded for editing.');
}
function moveSceneCard(i,delta){let j=i+delta;if(j<0||j>=nfSceneCards.length)return;[nfSceneCards[i],nfSceneCards[j]]=[nfSceneCards[j],nfSceneCards[i]];renderSceneCards();}
function deleteSceneCard(i){nfSceneCards.splice(i,1);renderSceneCards();}
function sortSceneCards(){nfSceneCards.sort((a,b)=>String(a.title||'').localeCompare(String(b.title||'')));renderSceneCards();toast('Scenes sorted.');}
function restoreStarterScenes(){q('nfScenes').value=starterSceneLines().join('\n');syncScenesFromText();renderSceneCards();updateNovelCounts();toast('Starter scenes restored.');}
function sceneCardsText(){
    syncScenesFromText();
    return nfSceneCards.map((sc,i)=>`${i+1}. ${sc.title||'Untitled Scene'}\nPOV: ${sc.pov||'Unknown'}\nLocation: ${sc.location||'Unknown'}\nCharacters: ${sc.characters||'None'}\nPurpose: ${sc.purpose||'None'}\nConflict: ${sc.conflict||'None'}\nOutcome: ${sc.outcome||'None'}\nCanon Notes: ${sc.canon||'None'}`).join('\n\n')||'No scenes.';
}
function sceneBrief(sc){
    return `Scene Brief

Universe: ${q('nfUniverse').value||'Untitled Universe'}
Scene: ${sc.title||'Untitled Scene'}
POV: ${sc.pov||'Unknown'}
Location: ${sc.location||'Unknown'}
Characters Present: ${sc.characters||'None'}

Purpose:
${sc.purpose||'None'}

Conflict:
${sc.conflict||'None'}

Outcome:
${sc.outcome||'None'}

Canon Notes:
${sc.canon||'None'}`;
}
function sendSceneBrief(i){
    let sc=nfSceneCards[i]; if(!sc)return;
    go('mission');
    q('input').value=`You are helping with a Novel Forge scene.

${sceneBrief(sc)}

Please improve this scene brief, identify continuity risks, and suggest beats that make the scene stronger.`;
    toast('Scene brief sent to Mission Console input.');
}
function generateSceneDraft(i){
    let sc=nfSceneCards[i]; if(!sc)return;
    go('mission');
    q('input').value=`You are Novel Forge's scene drafting engine.

Draft this scene using the scene brief and Codex context. Preserve canon, respect character motivations, and avoid resolving mysteries too early.

Return:
1. Scene draft
2. Continuity notes
3. Foreshadowing opportunities
4. Revision suggestions

${sceneBrief(sc)}

Codex Context:
${completeStoryBibleText()}`;
    toast('Scene draft request sent to Mission Console input.');
}
function checkScenePlan(){
    syncScenesToText();
    go('mission');
    q('input').value=`You are Novel Forge's scene planning engine.

Analyze these scenes for weak purpose, missing conflict, unclear outcome, continuity risks, pacing gaps, and missing setup/payoff.

Return your answer in this exact structure:

1. Scene Plan Summary
2. Strongest Scenes
3. Weakest Scenes
4. Missing Conflict
5. Missing Outcomes
6. Continuity Risks
7. Better Scene Order
8. Recommended New Scenes
9. Best Next Scene to Draft

Universe: ${q('nfUniverse').value||'Untitled Universe'}

Scenes:
${sceneCardsText()}

Story Bible:
${completeStoryBibleText()}`;
    toast('Scene plan check sent to Mission Console input.');
}

let nfLocationCards=[];
function slippingLocationLines(){
    return [
        'Pueblo tunnels | Urban underworld / hidden lair network | Dark underground routes tied to local danger, hidden vampire movement, and possible Baal lore. | Hidden entrances, old chambers, blood traces, things older than the city. | Anthony, Baal, Jokaya | Baal threat, hidden vampire movement',
        'Olmec pyramid | Ancient ruin / clue site | A major Book 2 investigation site tied to Croatoan, crystal skulls, and evidence of ancient escape. | Claw marks, broken pedestal, mismatched glyphs, ancient blood, priest journal fragment. | Anthony, Croatoan, Thoth | Croatoan escape, crystal skulls',
        'Mayan prison | Ancient prison | Prison site connected to Croatoan’s defeat, confinement, and eventual mystery escape. | Prison mechanism may be spiritual, blood-based, or prophecy-linked. | Croatoan, Jokaya, Kayock | How did Croatoan escape?',
        'Kayock’s lair | Protector stronghold / archive | Kayock’s base containing old records, blood vats, hidden technology, and possibly his legacy plan. | Computer, records, blood vats, prophecy materials, author-only secrets. | Kayock, Anthony | Kayock legacy, bloodless future',
        'Roanoke | Lost colony / origin clue | Historical site connected to Croatoan, disappearance, and vampire mythology. | The name Croatoan may be clue, warning, or trap. | Croatoan, Kayock | Roanoke mystery',
        'Vatican | Religious archive / power center | Potential repository of prophecy records, hunter history, and dangerous theological secrets. | Records may conflict with vampire versions of history. | Anthony, Father Grandier, St. Michael | prophecy misunderstanding',
        'Desert where Kayock meets Jesus | Sacred encounter site | Location of Kayock’s transformative meeting with Jesus and the moral root of the protector mission. | What Jesus told Kayock should be revealed carefully. | Kayock, Jesus, Anthony | What did Kayock learn from Jesus?'
    ];
}
function parseLocationLine(line){
    let raw=String(line||'').trim();
    if(!raw)return null;
    let parts=raw.split('|').map(x=>x.trim());
    if(parts.length>=6)return {name:parts[0],type:parts[1],description:parts[2],secrets:parts[3],characters:parts[4],mysteries:parts.slice(5).join(' | ')};
    return {name:raw,type:'',description:'',secrets:'',characters:'',mysteries:''};
}
function locationCardToLine(loc){
    return `${(loc.name||'Unnamed Location').trim()} | ${(loc.type||'').trim()} | ${(loc.description||'').replace(/\r?\n/g,' ').trim()} | ${(loc.secrets||'').replace(/\r?\n/g,' ').trim()} | ${(loc.characters||'').trim()} | ${(loc.mysteries||'').trim()}`;
}
function syncLocationsFromText(){
    if(!q('nfLocations'))return;
    nfLocationCards=(q('nfLocations').value||'').split(/\r?\n/).map(parseLocationLine).filter(Boolean);
}
function syncLocationsToText(){
    q('nfLocations').value=nfLocationCards.map(locationCardToLine).join('\n');
    updateNovelCounts();
}
function renderLocationCards(){
    if(!q('nfLocationCards'))return;
    syncLocationsToText();
    if(!nfLocationCards.length){q('nfLocationCards').innerHTML='No location cards yet.';return}
    q('nfLocationCards').innerHTML=nfLocationCards.map((loc,i)=>`<div class=loccard><h4>📍 ${esc(loc.name||'Unnamed Location')}</h4><span class=loctag>${esc(loc.type||'type unknown')}</span><span class=loctag>${esc(loc.characters||'no characters')}</span><span class=loctag>${esc(loc.mysteries||'no mysteries')}</span><div class=locdetails><b>Description:</b> ${esc(loc.description||'None')}\n<b>Secrets:</b> ${esc(loc.secrets||'None')}</div><div class=locactions><button onclick="editLocationCard(${i})">Edit</button><button onclick="moveLocationCard(${i},-1)">Up</button><button onclick="moveLocationCard(${i},1)">Down</button><button onclick="deleteLocationCard(${i})">Delete</button><button onclick="sendLocationCard(${i})">Send</button></div></div>`).join('');
}
function addLocationCard(){
    let name=q('nfLocName').value.trim();
    if(!name){toast('Enter a location name before adding.');return}
    nfLocationCards.push({name,type:q('nfLocType').value.trim(),description:q('nfLocDescription').value.trim(),secrets:q('nfLocSecrets').value.trim(),characters:q('nfLocCharacters').value.trim(),mysteries:q('nfLocMysteries').value.trim()});
    ['nfLocName','nfLocType','nfLocDescription','nfLocSecrets','nfLocCharacters','nfLocMysteries'].forEach(id=>q(id).value='');
    renderLocationCards();
    toast('Location added.');
}
function editLocationCard(i){
    let loc=nfLocationCards[i]; if(!loc)return;
    q('nfLocName').value=loc.name||''; q('nfLocType').value=loc.type||''; q('nfLocDescription').value=loc.description||''; q('nfLocSecrets').value=loc.secrets||''; q('nfLocCharacters').value=loc.characters||''; q('nfLocMysteries').value=loc.mysteries||'';
    nfLocationCards.splice(i,1); renderLocationCards(); toast('Location loaded for editing.');
}
function moveLocationCard(i,delta){let j=i+delta;if(j<0||j>=nfLocationCards.length)return;[nfLocationCards[i],nfLocationCards[j]]=[nfLocationCards[j],nfLocationCards[i]];renderLocationCards();}
function deleteLocationCard(i){nfLocationCards.splice(i,1);renderLocationCards();}
function sortLocationCards(){nfLocationCards.sort((a,b)=>String(a.name||'').localeCompare(String(b.name||'')));renderLocationCards();toast('Locations sorted.');}
function restoreSlippingLocations(){q('nfLocations').value=slippingLocationLines().join('\n');syncLocationsFromText();renderLocationCards();updateNovelCounts();updateCodexDashboard();
    toast('Slipping locations restored.');}
function locationCardsText(){syncLocationsFromText();return nfLocationCards.map((loc,i)=>`${i+1}. ${loc.name||'Unnamed Location'}\nType: ${loc.type||'Unknown'}\nDescription: ${loc.description||'None'}\nSecrets: ${loc.secrets||'None'}\nCharacters: ${loc.characters||'None'}\nMysteries: ${loc.mysteries||'None'}`).join('\n\n')||'No locations.'}
function sendLocationCard(i){
    let loc=nfLocationCards[i]; if(!loc)return;
    go('mission');
    q('input').value=`You are helping with a Novel Forge location.

Universe: ${q('nfUniverse').value||'Untitled Universe'}
Location: ${loc.name||'Unnamed Location'}
Type: ${loc.type||'Unknown'}
Description: ${loc.description||'None'}
Secrets: ${loc.secrets||'None'}
Related Characters: ${loc.characters||'None'}
Related Mysteries: ${loc.mysteries||'None'}

Please strengthen this location, identify story uses, reveal timing, continuity risks, and sensory details.`;
    toast('Location sent to Mission Console input.');
}
function checkWorldbuilding(){
    syncLocationsToText();
    go('mission');
    q('input').value=`You are Novel Forge's worldbuilding logic engine.

Analyze these locations for unclear geography, weak atmosphere, missing secrets, cultural/mythological risks, underused settings, and continuity problems.

Return your answer in this exact structure:

1. Worldbuilding Summary
2. Strongest Locations
3. Weakest / Least Defined Locations
4. Geography or Timeline Problems
5. Secret / Reveal Opportunities
6. Cultural or Mythology Handling Risks
7. Location-Character Connections
8. Recommended Improvements
9. Best Next Location Scene

Universe: ${q('nfUniverse').value||'Untitled Universe'}

Premise:
${q('nfPremise').value||'None'}

Locations:
${locationCardsText()}

Characters:
${characterCardsText()}

Mysteries:
${mysteryCardsText()}`;
    toast('Worldbuilding check sent to Mission Console input.');
}

let nfArtifactCards=[];
function slippingArtifactLines(){
    return [
        'Crystal skulls | Prophecy vessel / memory prison | May contain prophecy fragments, ancient vampire memories, imprisoned beings, or bloodline records. | Connected to Olmec/Mayan clues, Croatoan, Thoth, and old vampire knowledge. | Should require interpretation, have consequences, and avoid becoming an unlimited answer machine. | Anthony, Croatoan, Thoth, Kayock | What do the crystal skulls contain?',
        'Silver cross | Sacred weapon / personal proof | Burns Chee and proves spiritual rules matter; may connect Anthony to faith, curse, or hunter traditions. | Used in Anthony’s origin and Chee’s injury. | Must have consistent rules for why it works on some beings and not others. | Anthony, Chee | Anthony turning, vampire rules',
        'Ancient blood vats | Survival technology / moral horror | Provide cloned or stored blood alternative; tie into Kayock’s goal of ending predatory blood need. | Found in Kayock’s lair or later protector systems. | Need rules for supply, purity, consent, corruption, and who controls them. | Kayock, Anthony | bloodless future',
        'Prophecy records | Ancient text / contested truth | Records the prophecy but may be mistranslated or politically manipulated. | Tied to Thoth, Vatican, Kayock, and hunter priest traditions. | Must clearly separate true prophecy from interpretations. | Anthony, Kayock, Thoth, Yactazini | prophecy misunderstanding',
        'Clawed pedestal | Physical clue / missing artifact site | Evidence that something escaped, was removed, or transformed at the Olmec site. | Supports Croatoan escape and crystal skull mystery. | Should point to a specific event, not just atmosphere. | Croatoan, Anthony | Croatoan escape',
        'Priest journal fragment | Witness record / incomplete clue | A damaged account from a priest or hunter who saw part of the ancient event. | Reveals partial truth while preserving mystery. | Fragment should mislead or omit enough to keep tension. | Yactazini, Anthony | prophecy, Croatoan escape'
    ];
}
function parseArtifactLine(line){
    let raw=String(line||'').trim();
    if(!raw)return null;
    let parts=raw.split('|').map(x=>x.trim());
    if(parts.length>=7)return {name:parts[0],type:parts[1],functionText:parts[2],history:parts[3],rules:parts[4],characters:parts[5],mysteries:parts.slice(6).join(' | ')};
    return {name:raw,type:'',functionText:'',history:'',rules:'',characters:'',mysteries:''};
}
function artifactCardToLine(art){
    return `${(art.name||'Unnamed Artifact').trim()} | ${(art.type||'').trim()} | ${(art.functionText||'').replace(/\r?\n/g,' ').trim()} | ${(art.history||'').replace(/\r?\n/g,' ').trim()} | ${(art.rules||'').replace(/\r?\n/g,' ').trim()} | ${(art.characters||'').trim()} | ${(art.mysteries||'').trim()}`;
}
function syncArtifactsFromText(){if(!q('nfArtifacts'))return;nfArtifactCards=(q('nfArtifacts').value||'').split(/\r?\n/).map(parseArtifactLine).filter(Boolean);}
function syncArtifactsToText(){q('nfArtifacts').value=nfArtifactCards.map(artifactCardToLine).join('\n');updateNovelCounts();}
function renderArtifactCards(){
    if(!q('nfArtifactCards'))return;
    syncArtifactsToText();
    if(!nfArtifactCards.length){q('nfArtifactCards').innerHTML='No artifact cards yet.';return}
    q('nfArtifactCards').innerHTML=nfArtifactCards.map((art,i)=>`<div class=artcard><h4>🔮 ${esc(art.name||'Unnamed Artifact')}</h4><span class=arttag>${esc(art.type||'type unknown')}</span><span class=arttag>${esc(art.characters||'no characters')}</span><span class=arttag>${esc(art.mysteries||'no mysteries')}</span><div class=artdetails><b>Function:</b> ${esc(art.functionText||'None')}\n<b>History:</b> ${esc(art.history||'None')}\n<b>Rules:</b> ${esc(art.rules||'None')}</div><div class=artactions><button onclick="editArtifactCard(${i})">Edit</button><button onclick="moveArtifactCard(${i},-1)">Up</button><button onclick="moveArtifactCard(${i},1)">Down</button><button onclick="deleteArtifactCard(${i})">Delete</button><button onclick="sendArtifactCard(${i})">Send</button></div></div>`).join('');
}
function addArtifactCard(){
    let name=q('nfArtName').value.trim();
    if(!name){toast('Enter an artifact name before adding.');return}
    nfArtifactCards.push({name,type:q('nfArtType').value.trim(),functionText:q('nfArtFunction').value.trim(),history:q('nfArtHistory').value.trim(),rules:q('nfArtRules').value.trim(),characters:q('nfArtCharacters').value.trim(),mysteries:q('nfArtMysteries').value.trim()});
    ['nfArtName','nfArtType','nfArtFunction','nfArtHistory','nfArtRules','nfArtCharacters','nfArtMysteries'].forEach(id=>q(id).value='');
    renderArtifactCards();
    toast('Artifact added.');
}
function editArtifactCard(i){
    let art=nfArtifactCards[i]; if(!art)return;
    q('nfArtName').value=art.name||''; q('nfArtType').value=art.type||''; q('nfArtFunction').value=art.functionText||''; q('nfArtHistory').value=art.history||''; q('nfArtRules').value=art.rules||''; q('nfArtCharacters').value=art.characters||''; q('nfArtMysteries').value=art.mysteries||'';
    nfArtifactCards.splice(i,1); renderArtifactCards(); toast('Artifact loaded for editing.');
}
function moveArtifactCard(i,delta){let j=i+delta;if(j<0||j>=nfArtifactCards.length)return;[nfArtifactCards[i],nfArtifactCards[j]]=[nfArtifactCards[j],nfArtifactCards[i]];renderArtifactCards();}
function deleteArtifactCard(i){nfArtifactCards.splice(i,1);renderArtifactCards();}
function sortArtifactCards(){nfArtifactCards.sort((a,b)=>String(a.name||'').localeCompare(String(b.name||'')));renderArtifactCards();toast('Artifacts sorted.');}
function restoreSlippingArtifacts(){q('nfArtifacts').value=slippingArtifactLines().join('\n');syncArtifactsFromText();renderArtifactCards();updateNovelCounts();updateCodexDashboard();
    toast('Slipping artifacts restored.');}
function artifactCardsText(){syncArtifactsFromText();return nfArtifactCards.map((art,i)=>`${i+1}. ${art.name||'Unnamed Artifact'}\nType: ${art.type||'Unknown'}\nFunction: ${art.functionText||'None'}\nHistory: ${art.history||'None'}\nRules / Limits: ${art.rules||'None'}\nCharacters: ${art.characters||'None'}\nMysteries: ${art.mysteries||'None'}`).join('\n\n')||'No artifacts.'}
function sendArtifactCard(i){
    let art=nfArtifactCards[i]; if(!art)return;
    go('mission');
    q('input').value=`You are helping with a Novel Forge artifact.

Universe: ${q('nfUniverse').value||'Untitled Universe'}
Artifact: ${art.name||'Unnamed Artifact'}
Type: ${art.type||'Unknown'}
Power / Function: ${art.functionText||'None'}
History: ${art.history||'None'}
Rules / Limits: ${art.rules||'None'}
Related Characters: ${art.characters||'None'}
Related Mysteries: ${art.mysteries||'None'}

Please strengthen this artifact, define clear rules, identify continuity risks, and suggest how it should affect the story.`;
    toast('Artifact sent to Mission Console input.');
}
function checkArtifactRules(){
    syncArtifactsToText();
    go('mission');
    q('input').value=`You are Novel Forge's artifact rules engine.

Analyze these artifacts for unclear powers, inconsistent rules, overpowered mechanics, missing costs, weak history, and payoff opportunities.

Return your answer in this exact structure:

1. Artifact System Summary
2. Strongest Artifacts
3. Weakest / Least Defined Artifacts
4. Rule Inconsistencies
5. Power Creep Risks
6. Missing Costs or Limits
7. Mystery / Plot Payoff Opportunities
8. Recommended Fixes
9. Best Next Artifact Scene

Universe: ${q('nfUniverse').value||'Untitled Universe'}

Premise:
${q('nfPremise').value||'None'}

Artifacts:
${artifactCardsText()}

Characters:
${characterCardsText()}

Mysteries:
${mysteryCardsText()}`;
    toast('Artifact rules check sent to Mission Console input.');
}

let nfMysteryCards=[];
function slippingMysteryLines(){
    return [
        'What exactly did Anthony’s ex become? | Unresolved | Anthony, ex, Jokaya, Chee | Anthony learns she has been turned, but not what she has become or who controls her. | Book 1 ending reveal; signs of a transformation that does not fit normal vampire rules. | Book 2 should make the hunt personal while tying her fate to Jokaya’s experiments or prophecy misunderstanding.',
        'How did Croatoan escape? | Unresolved | Croatoan, Jokaya, Kayock | Croatoan was imprisoned but later evidence suggests he escaped or was released. | Olmec pyramid clues; claw marks; broken pedestal; mismatched glyphs; priest journal fragment. | Reveal whether escape was deliberate, betrayal-driven, or part of a larger prophecy mechanism.',
        'What do the crystal skulls truly contain? | Clue planted | Croatoan, Thoth, Kayock, Anthony | The skulls may contain more than records; they might preserve memories, imprisoned vampires, prophecy fragments, or ancient blood power. | Claw marks, ancient blood residue, murals shifting from small to giant figures. | Pay off as a key to understanding Croatoan, the prophecy, or the bloodless future.',
        'What parts of the prophecy are misunderstood? | Unresolved | Anthony, Kayock, Jesus, Thoth | The prophecy may not mean killing vampires; it may mean ending their need for blood or transforming the curse. | Kayock’s meeting with Jesus; prophecy records; Anthony’s psychic nature. | Reveal that the prophecy has been interpreted through fear, power, or vampire politics.',
        'What did Kayock learn from Jesus? | Unresolved | Kayock, Jesus, Anthony | Kayock’s desert encounter should explain why he became a protector and what he believed about ending blood need. | Desert meeting; protector legacy; Kayock’s refusal to behave like other vampires. | Pay off as the spiritual/moral core of Kayock’s mission and Anthony’s inheritance.'
    ];
}
function parseMysteryLine(line){
    let raw=String(line||'').trim();
    if(!raw)return null;
    let parts=raw.split('|').map(x=>x.trim());
    if(parts.length>=6)return {title:parts[0],status:parts[1],characters:parts[2],details:parts[3],clues:parts[4],payoff:parts.slice(5).join(' | ')};
    return {title:raw,status:'Unresolved',characters:'',details:'',clues:'',payoff:''};
}
function mysteryCardToLine(my){
    let title=(my.title||'Untitled Mystery').trim();
    let status=(my.status||'Unresolved').trim();
    let characters=(my.characters||'').trim();
    let details=(my.details||'').replace(/\r?\n/g,' ').trim();
    let clues=(my.clues||'').replace(/\r?\n/g,'; ').trim();
    let payoff=(my.payoff||'').replace(/\r?\n/g,' ').trim();
    return `${title} | ${status} | ${characters} | ${details} | ${clues} | ${payoff}`;
}
function syncMysteriesFromText(){
    if(!q('nfMysteries'))return;
    nfMysteryCards=(q('nfMysteries').value||'').split(/\r?\n/).map(parseMysteryLine).filter(Boolean);
}
function syncMysteriesToText(){
    q('nfMysteries').value=nfMysteryCards.map(mysteryCardToLine).join('\n');
    updateNovelCounts();
}
function mysteryBadgeClass(status){
    let s=String(status||'').toLowerCase();
    if(s.includes('solved'))return 'mystatus-solved';
    if(s.includes('red'))return 'mystatus-red';
    return 'mystatus-unresolved';
}
function renderMysteryCards(){
    if(!q('nfMysteryCards'))return;
    syncMysteriesToText();
    syncScenesToText();
    if(!nfMysteryCards.length){
        q('nfMysteryCards').innerHTML='No mysteries yet.';
        return;
    }
    q('nfMysteryCards').innerHTML=nfMysteryCards.map((my,i)=>`<div class=mysterycard><h4>🧩 ${esc(my.title||'Untitled Mystery')}</h4><span class="mystag ${mysteryBadgeClass(my.status)}">${esc(my.status||'Unresolved')}</span><span class=mystag>${esc(my.characters||'no characters')}</span><div class=mysdetails><b>Details:</b> ${esc(my.details||'None')}\n<b>Clues:</b> ${esc(my.clues||'None')}\n<b>Payoff:</b> ${esc(my.payoff||'None')}</div><div class=mysactions><button onclick="editMysteryCard(${i})">Edit</button><button onclick="moveMysteryCard(${i},-1)">Up</button><button onclick="moveMysteryCard(${i},1)">Down</button><button onclick="deleteMysteryCard(${i})">Delete</button><button onclick="sendMysteryCard(${i})">Send</button></div></div>`).join('');
}
function addMysteryCard(){
    let title=q('nfMysteryTitle').value.trim();
    if(!title){toast('Enter a mystery title before adding.');return}
    let my={
        title:title,
        status:q('nfMysteryStatus').value||'Unresolved',
        characters:q('nfMysteryCharacters').value.trim(),
        details:q('nfMysteryDetails').value.trim(),
        clues:q('nfMysteryClues').value.trim(),
        payoff:q('nfMysteryPayoff').value.trim()
    };
    nfMysteryCards.push(my);
    ['nfMysteryTitle','nfMysteryCharacters','nfMysteryDetails','nfMysteryClues','nfMysteryPayoff'].forEach(id=>q(id).value='');
    q('nfMysteryStatus').value='Unresolved';
    renderMysteryCards();
    toast('Mystery added.');
}
function editMysteryCard(i){
    let my=nfMysteryCards[i]; if(!my)return;
    q('nfMysteryTitle').value=my.title||'';
    q('nfMysteryStatus').value=my.status||'Unresolved';
    q('nfMysteryCharacters').value=my.characters||'';
    q('nfMysteryDetails').value=my.details||'';
    q('nfMysteryClues').value=my.clues||'';
    q('nfMysteryPayoff').value=my.payoff||'';
    nfMysteryCards.splice(i,1);
    renderMysteryCards();
    toast('Mystery loaded for editing. Update fields and Add Mystery when ready.');
}
function moveMysteryCard(i,delta){
    let j=i+delta;
    if(j<0||j>=nfMysteryCards.length)return;
    [nfMysteryCards[i],nfMysteryCards[j]]=[nfMysteryCards[j],nfMysteryCards[i]];
    renderMysteryCards();
}
function deleteMysteryCard(i){
    nfMysteryCards.splice(i,1);
    renderMysteryCards();
}
function sortMysteryCards(){
    const order={'Unresolved':0,'Clue planted':1,'Partially revealed':2,'Red herring':3,'Solved':4};
    nfMysteryCards.sort((a,b)=>(order[a.status]??9)-(order[b.status]??9)||String(a.title||'').localeCompare(String(b.title||'')));
    renderMysteryCards();
    toast('Mysteries sorted.');
}
function restoreSlippingMysteries(){
    q('nfMysteries').value=slippingMysteryLines().join('\n');
    syncMysteriesFromText();
    renderMysteryCards();
    updateNovelCounts();
    updateCodexDashboard();
    toast('Slipping into Darkness mysteries restored.');
}
function mysteryCardsText(){
    syncMysteriesFromText();
    return nfMysteryCards.map((my,i)=>`${i+1}. ${my.title||'Untitled Mystery'}\nStatus: ${my.status||'Unresolved'}\nCharacters: ${my.characters||'None'}\nDetails: ${my.details||'None'}\nClues: ${my.clues||'None'}\nPayoff Plan: ${my.payoff||'None'}`).join('\n\n')||'No mysteries.';
}
function sendMysteryCard(i){
    let my=nfMysteryCards[i]; if(!my)return;
    go('mission');
    q('input').value=`You are helping with a Novel Forge mystery thread.

Universe: ${q('nfUniverse').value||'Untitled Universe'}
Mystery: ${my.title||'Untitled Mystery'}
Status: ${my.status||'Unresolved'}
Related Characters: ${my.characters||'None'}
Details: ${my.details||'None'}
Clues: ${my.clues||'None'}
Payoff Plan: ${my.payoff||'None'}

Please strengthen this mystery, suggest clues, identify payoff risks, and connect it to the larger story arc.`;
    toast('Mystery sent to Mission Console input.');
}
function checkMysteryPayoff(){
    syncMysteriesToText();
    syncScenesToText();
    go('mission');
    q('input').value=`You are Novel Forge's mystery payoff engine.

Analyze these mystery threads for weak setup, missing clues, unresolved promises, premature reveals, red herring risks, and payoff opportunities.

Return your answer in this exact structure:

1. Mystery System Summary
2. Strongest Mystery Threads
3. Weakest / Vaguest Mysteries
4. Missing Clues
5. Payoff Risks
6. Red Herring Opportunities
7. Character Connections
8. Recommended Reveal Order
9. Best Next Mystery Scene

Universe: ${q('nfUniverse').value||'Untitled Universe'}

Premise:
${q('nfPremise').value||'None'}

Characters:
${characterCardsText()}

Timeline:
${timelineManagerText()}

Mysteries:
${mysteryCardsText()}`;
    toast('Mystery payoff check sent to Mission Console input.');
}

let nfCharacterCards=[];

function slippingCharacterLines(){
    return [
        'Anthony / Whisper | Protagonist / Psychic Hunter | Alive / Cursed | Main hero with psychic and telepathic gifts, drawn into a vampire prophecy that may end the need for blood. | Anthony, Whisper, prophecy, Book 1, psychic',
        'Kayock | First Vampire / Ancient Protector | Dead / Legacy Active | Ancient hunter and first vampire, later protector figure; his death at Jokaya’s hands becomes a central wound in Book 1. | Kayock, first vampire, Jesus, prophecy, protector',
        'Jokaya | Antagonist / Ancient Queen | Active Threat | Ancient Native queen and powerful vampire antagonist who kills Kayock and forces Anthony into the center of the prophecy. | Jokaya, queen, Book 1, antagonist',
        'Chee | Mysterious Vampire / Survivor Figure | Unknown / Ambiguous | Chinese vampire connected to Anthony’s turning, survival, and the unclear boundary between hunter and vampire. | Chee, turning, survival, Anthony',
        'Croatoan | Imp Vampire / Escaped Threat | Imprisoned Then Escaped | Child or legacy of Kayock tied to Roanoke, ancient prisons, and the mystery of escape in Book 2. | Croatoan, Roanoke, prison, Book 2',
        'Ishtar | Ancient Vampire Power Figure | Unknown | Ancient power figure in the vampire mythology; needs clearer motive and relation to prophecy. | Ishtar, ancient vampire, mythology',
        'Thoth | Ancient Knowledge Figure | Unknown | Knowledge-linked ancient figure who may connect prophecy records, skulls, and hidden vampire history. | Thoth, knowledge, prophecy, records',
        'Baal | Demonic / Vampiric Threat | Threat / To Be Clarified | Ancient demonic or vampiric threat; should be reconciled carefully with vampire rules and Pueblo tunnel lore. | Baal, demon, vampire, threat',
        'Beowulf | Protector Champion | Legacy / Mythic Ally | Champion figure connected to protector mythology and possible vampire-hunter lineage. | Beowulf, protector, champion',
        'Yactazini | First Hunter Priest | Ancient Legacy | First hunter priest, likely tied to early anti-vampire traditions and prophecy interpretation. | Yactazini, hunter, priest, ancient'
    ];
}
function restoreSlippingCharacters(){
    q('nfCharacters').value=slippingCharacterLines().join('\n');
    syncCharactersFromText();
    renderCharacterCards();
    updateNovelCounts();
    updateCodexDashboard();
    toast('Slipping into Darkness character cards restored.');
}

function parseCharacterLine(line){
    let raw=String(line||'').trim();
    if(!raw)return null;
    let parts=raw.split('|').map(x=>x.trim());
    if(parts.length>=5)return {name:parts[0],role:parts[1],status:parts[2],details:parts[3],tags:parts.slice(4).join(' | ')};
    let m=raw.match(/^(.+?)\s+-\s+(.*)$/);
    if(m)return {name:m[1].trim(),role:m[2].trim(),status:'',details:'',tags:''};
    return {name:raw,role:'',status:'',details:'',tags:''};
}
function characterCardToLine(ch){
    let name=(ch.name||'Unnamed Character').trim();
    let role=(ch.role||'').trim();
    let status=(ch.status||'').trim();
    let details=(ch.details||'').replace(/\r?\n/g,' ').trim();
    let tags=(ch.tags||'').trim();
    return `${name} | ${role} | ${status} | ${details} | ${tags}`;
}
function syncCharactersFromText(){
    if(!q('nfCharacters'))return;
    nfCharacterCards=(q('nfCharacters').value||'').split(/\r?\n/).map(parseCharacterLine).filter(Boolean);
}
function syncCharactersToText(){
    q('nfCharacters').value=nfCharacterCards.map(characterCardToLine).join('\n');
    updateNovelCounts();
}
function renderCharacterCards(){
    if(!q('nfCharacterCards'))return;
    syncCharactersToText();
    if(!nfCharacterCards.length){
        q('nfCharacterCards').innerHTML='No character cards yet.';
        return;
    }
    q('nfCharacterCards').innerHTML=nfCharacterCards.map((ch,i)=>`<div class=charcard><h4>🧍 ${esc(ch.name||'Unnamed Character')}</h4><span class=chartag>${esc(ch.role||'role unknown')}</span><span class=chartag>${esc(ch.status||'status unknown')}</span><span class=chartag>${esc(ch.tags||'no tags')}</span><div class=chardetails>${esc(ch.details||'')}</div><div class=charactions><button onclick="editCharacterCard(${i})">Edit</button><button onclick="moveCharacterCard(${i},-1)">Up</button><button onclick="moveCharacterCard(${i},1)">Down</button><button onclick="deleteCharacterCard(${i})">Delete</button><button onclick="sendCharacterCard(${i})">Send</button></div></div>`).join('');
}
function addCharacterCard(){
    let name=q('nfCharName').value.trim();
    if(!name){
        toast('Enter a character name before adding a character.');
        return;
    }
    let ch={
        name:name,
        role:q('nfCharRole').value.trim(),
        status:q('nfCharStatus').value.trim(),
        details:q('nfCharDetails').value.trim(),
        tags:q('nfCharTags').value.trim()
    };
    nfCharacterCards.push(ch);
    ['nfCharName','nfCharRole','nfCharStatus','nfCharDetails','nfCharTags'].forEach(id=>q(id).value='');
    renderCharacterCards();
    toast('Character added.');
}
function editCharacterCard(i){
    let ch=nfCharacterCards[i]; if(!ch)return;
    q('nfCharName').value=ch.name||'';
    q('nfCharRole').value=ch.role||'';
    q('nfCharStatus').value=ch.status||'';
    q('nfCharDetails').value=ch.details||'';
    q('nfCharTags').value=ch.tags||'';
    nfCharacterCards.splice(i,1);
    renderCharacterCards();
    toast('Character loaded for editing. Update fields and Add Character when ready.');
}
function moveCharacterCard(i,delta){
    let j=i+delta;
    if(j<0||j>=nfCharacterCards.length)return;
    [nfCharacterCards[i],nfCharacterCards[j]]=[nfCharacterCards[j],nfCharacterCards[i]];
    renderCharacterCards();
}
function deleteCharacterCard(i){
    nfCharacterCards.splice(i,1);
    renderCharacterCards();
}
function sortCharacterCards(){
    nfCharacterCards.sort((a,b)=>String(a.name||'').localeCompare(String(b.name||'')));
    renderCharacterCards();
    toast('Characters sorted.');
}
function characterCardsText(){
    syncCharactersFromText();
    return nfCharacterCards.map((ch,i)=>`${i+1}. ${ch.name||'Unnamed Character'}\nRole: ${ch.role||'Unknown'}\nStatus: ${ch.status||'Unknown'}\nDetails: ${ch.details||'None'}\nTags: ${ch.tags||'None'}`).join('\n\n')||'No character cards.';
}
function sendCharacterCard(i){
    let ch=nfCharacterCards[i]; if(!ch)return;
    go('mission');
    q('input').value=`You are helping with a Novel Forge character.

Universe: ${q('nfUniverse').value||'Untitled Universe'}
Character: ${ch.name||'Unnamed Character'}
Role: ${ch.role||'Unknown'}
Status: ${ch.status||'Unknown'}
Details: ${ch.details||'None'}
Tags: ${ch.tags||'None'}

Please develop this character, identify continuity implications, strengthen motivation, and suggest how they should affect the plot.`;
    toast('Character sent to Mission Console input.');
}

function upgradeSimpleCharacterCards(){
    syncCharactersFromText();
    if(!nfCharacterCards.length){restoreSlippingCharacters();return;}
    const known={
        'Anthony / Whisper':{role:'Protagonist / Psychic Hunter',status:'Alive / Cursed',details:'Main hero with psychic and telepathic gifts, drawn into a vampire prophecy that may end the need for blood.',tags:'Anthony, Whisper, prophecy, Book 1, psychic'},
        'Kayock':{role:'First Vampire / Ancient Protector',status:'Dead / Legacy Active',details:'Ancient hunter and first vampire, later protector figure; his death at Jokaya’s hands becomes a central wound in Book 1.',tags:'Kayock, first vampire, Jesus, prophecy, protector'},
        'Jokaya':{role:'Antagonist / Ancient Queen',status:'Active Threat',details:'Ancient Native queen and powerful vampire antagonist who kills Kayock and forces Anthony into the center of the prophecy.',tags:'Jokaya, queen, Book 1, antagonist'},
        'Chee':{role:'Mysterious Vampire / Survivor Figure',status:'Unknown / Ambiguous',details:'Chinese vampire connected to Anthony’s turning, survival, and the unclear boundary between hunter and vampire.',tags:'Chee, turning, survival, Anthony'},
        'Croatoan':{role:'Imp Vampire / Escaped Threat',status:'Imprisoned Then Escaped',details:'Child or legacy of Kayock tied to Roanoke, ancient prisons, and the mystery of escape in Book 2.',tags:'Croatoan, Roanoke, prison, Book 2'},
        'Ishtar':{role:'Ancient Vampire Power Figure',status:'Unknown',details:'Ancient power figure in the vampire mythology; needs clearer motive and relation to prophecy.',tags:'Ishtar, ancient vampire, mythology'},
        'Thoth':{role:'Ancient Knowledge Figure',status:'Unknown',details:'Knowledge-linked ancient figure who may connect prophecy records, skulls, and hidden vampire history.',tags:'Thoth, knowledge, prophecy, records'},
        'Baal':{role:'Demonic / Vampiric Threat',status:'Threat / To Be Clarified',details:'Ancient demonic or vampiric threat; should be reconciled carefully with vampire rules and Pueblo tunnel lore.',tags:'Baal, demon, vampire, threat'},
        'Beowulf':{role:'Protector Champion',status:'Legacy / Mythic Ally',details:'Champion figure connected to protector mythology and possible vampire-hunter lineage.',tags:'Beowulf, protector, champion'},
        'Yactazini':{role:'First Hunter Priest',status:'Ancient Legacy',details:'First hunter priest, likely tied to early anti-vampire traditions and prophecy interpretation.',tags:'Yactazini, hunter, priest, ancient'}
    };
    nfCharacterCards=nfCharacterCards.map(ch=>{
        let key=Object.keys(known).find(k=>String(ch.name||'').toLowerCase()===k.toLowerCase());
        if(!key)return ch;
        let k=known[key];
        return {
            name:ch.name||key,
            role:(ch.role&&ch.role!=='')?ch.role:k.role,
            status:(ch.status&&ch.status!=='')?ch.status:k.status,
            details:(ch.details&&ch.details!=='')?ch.details:k.details,
            tags:(ch.tags&&ch.tags!=='')?ch.tags:k.tags
        };
    });
    renderCharacterCards();
    toast('Simple character cards upgraded.');
}

function checkCharacterArcs(){
    syncCharactersToText();
    go('mission');
    q('input').value=`You are Novel Forge's character arc engine.

Analyze these character cards for unclear motivations, missing relationships, weak arcs, contradictions, underused characters, and opportunities for stronger emotional payoff.

Return your answer in this exact structure:

1. Character Arc Summary
2. Strongest Characters
3. Weakest / Least Defined Characters
4. Motivation Problems
5. Relationship Opportunities
6. Character Continuity Risks
7. Suggested Arc Improvements
8. Best Next Character Scene

Universe: ${q('nfUniverse').value||'Untitled Universe'}

Premise:
${q('nfPremise').value||'None'}

Characters:
${characterCardsText()}

Timeline:
${timelineManagerText()}

Mysteries:
${q('nfMysteries').value||'None'}`;
    toast('Character arc check sent to Mission Console input.');
}

let nfTimelineEvents=[];
function parseTimelineLine(line){
    let raw=String(line||'').trim();
    if(!raw)return null;
    let parts=raw.split('|').map(x=>x.trim());
    if(parts.length>=4)return {era:parts[0],title:parts[1],details:parts[2],tags:parts.slice(3).join(' | ')};
    let m=raw.match(/^([^:]+):\s*(.*)$/);
    if(m)return {era:m[1].trim(),title:m[2].trim(),details:'',tags:''};
    return {era:'Unsorted',title:raw,details:'',tags:''};
}
function timelineEventToLine(ev){
    let era=(ev.era||'Unsorted').trim();
    let title=(ev.title||'Untitled Event').trim();
    let details=(ev.details||'').replace(/\r?\n/g,' ').trim();
    let tags=(ev.tags||'').trim();
    return `${era} | ${title} | ${details} | ${tags}`;
}
function syncTimelineFromText(){
    if(!q('nfTimeline'))return;
    nfTimelineEvents=(q('nfTimeline').value||'').split(/\r?\n/).map(parseTimelineLine).filter(Boolean);
}
function syncTimelineToText(){
    q('nfTimeline').value=nfTimelineEvents.map(timelineEventToLine).join('\n');
    updateNovelCounts();
}
function renderTimelineEvents(){
    if(!q('nfTimelineList'))return;
    syncTimelineToText();
    if(!nfTimelineEvents.length){
        q('nfTimelineList').innerHTML='No timeline events yet.';
        return;
    }
    q('nfTimelineList').innerHTML=nfTimelineEvents.map((ev,i)=>`<div class=tmevent><h4>${esc(ev.era||'Unsorted')} — ${esc(ev.title||'Untitled Event')}</h4><span class=tmtag>${esc(ev.tags||'no tags')}</span><div class=tmdetails>${esc(ev.details||'')}</div><div class=tmactions><button onclick="editTimelineEvent(${i})">Edit</button><button onclick="moveTimelineEvent(${i},-1)">Up</button><button onclick="moveTimelineEvent(${i},1)">Down</button><button onclick="deleteTimelineEvent(${i})">Delete</button><button onclick="sendSingleTimelineEvent(${i})">Send</button></div></div>`).join('');
}
function addTimelineEvent(){
    let ev={
        era:q('nfEventEra').value.trim()||'Unsorted',
        title:q('nfEventTitle').value.trim()||'Untitled Event',
        details:q('nfEventDetails').value.trim(),
        tags:q('nfEventTags').value.trim()
    };
    nfTimelineEvents.push(ev);
    ['nfEventEra','nfEventTitle','nfEventDetails','nfEventTags'].forEach(id=>q(id).value='');
    renderTimelineEvents();
    toast('Timeline event added.');
}
function editTimelineEvent(i){
    let ev=nfTimelineEvents[i]; if(!ev)return;
    q('nfEventEra').value=ev.era||'';
    q('nfEventTitle').value=ev.title||'';
    q('nfEventDetails').value=ev.details||'';
    q('nfEventTags').value=ev.tags||'';
    nfTimelineEvents.splice(i,1);
    renderTimelineEvents();
    toast('Event loaded for editing. Update fields and Add Event when ready.');
}
function moveTimelineEvent(i,delta){
    let j=i+delta;
    if(j<0||j>=nfTimelineEvents.length)return;
    [nfTimelineEvents[i],nfTimelineEvents[j]]=[nfTimelineEvents[j],nfTimelineEvents[i]];
    renderTimelineEvents();
}
function deleteTimelineEvent(i){
    nfTimelineEvents.splice(i,1);
    renderTimelineEvents();
}
function sortTimelineEvents(){
    nfTimelineEvents.sort((a,b)=>String(a.era||'').localeCompare(String(b.era||''))||String(a.title||'').localeCompare(String(b.title||'')));
    renderTimelineEvents();
    toast('Timeline sorted.');
}
function timelineManagerText(){
    syncTimelineFromText();
    return nfTimelineEvents.map((ev,i)=>`${i+1}. [${ev.era||'Unsorted'}] ${ev.title||'Untitled Event'}\nDetails: ${ev.details||'None'}\nTags: ${ev.tags||'None'}`).join('\n\n')||'No timeline events.';
}
function sendTimelineManager(){
    go('mission');
    q('input').value=`You are helping with Novel Forge timeline management.

Universe: ${q('nfUniverse').value||'Untitled Universe'}

Please review this timeline for order, continuity, missing causality, contradictions, and next-step story opportunities.

Timeline:
${timelineManagerText()}`;
    toast('Timeline sent to Mission Console input.');
}
function sendSingleTimelineEvent(i){
    let ev=nfTimelineEvents[i]; if(!ev)return;
    go('mission');
    q('input').value=`You are helping with a Novel Forge timeline event.

Universe: ${q('nfUniverse').value||'Untitled Universe'}
Era/Book: ${ev.era||'Unsorted'}
Event: ${ev.title||'Untitled Event'}
Details: ${ev.details||'None'}
Tags: ${ev.tags||'None'}

Please help develop this event, identify continuity implications, and suggest what should happen before or after it.`;
    toast('Timeline event sent to Mission Console input.');
}

function nfLines(id){return (q(id)?.value||'').split(/\r?\n/).map(x=>x.trim()).filter(Boolean)}
function updateNovelCounts(){
    if(!q('nfCounts'))return;
    let c=nfLines('nfCharacters').length,l=nfLines('nfLocations').length,a=nfLines('nfArtifacts').length,t=nfLines('nfTimeline').length,m=nfLines('nfMysteries').length;
    q('nfCounts').innerHTML=`<span class=nfcount>${c} characters</span><span class=nfcount>${l} locations</span><span class=nfcount>${a} artifacts</span><span class=nfcount>${t} timeline</span><span class=nfcount>${m} mysteries</span>`;
    if(q('nfDashboard'))setTimeout(updateCodexDashboard,0);
}
async function loadNovelForgeList(){
    if(!q('nfList'))return;
    try{
        let d=await (await fetch('/api/novelforge/list')).json();
        if(!d.universes?.length){
            q('nfList').innerHTML='No saved universes yet.';
            return;
        }
        q('nfList').innerHTML=d.universes.map(u=>`<div class=nfitem><h4>📖 ${esc(u.universe)}</h4><span class=nftag>${u.characters} characters</span><span class=nftag>${u.locations} locations</span><span class=nftag>${u.artifacts} artifacts</span><span class=nftag>${u.timeline} timeline</span><span class=nftag>${u.mysteries} mysteries</span><div class=time>${esc(u.modified)}</div><div class=nfpreview>${esc(u.premise||'')}</div><div class=nfactions><button onclick="openNovelForge('${js(u.name)}')">Load</button><button onclick="duplicateNovelForge('${js(u.name)}')">Duplicate</button><button onclick="renameNovelForge('${js(u.name)}')">Rename</button><button onclick="deleteNovelForge('${js(u.name)}')">Delete</button></div></div>`).join('');
    }catch(e){
        q('nfList').textContent='Novel Forge list unavailable: '+e;
    }
}
async function openNovelForge(name){
    let d=await (await fetch('/api/novelforge/read?name='+encodeURIComponent(name))).json();
    if(!d.ok){toast(d.message||'Universe not found.');return}
    activeUniverseName=d.file_name||name;
    q('nfUniverse').value=d.universe||'';
    q('nfPremise').value=d.premise||'';
    q('nfCharacters').value=(d.characters||[]).join('\n');syncCharactersFromText();renderCharacterCards();
    q('nfLocations').value=(d.locations||[]).join('\n');syncLocationsFromText();renderLocationCards();
    q('nfArtifacts').value=(d.artifacts||[]).join('\n');syncArtifactsFromText();renderArtifactCards();
    q('nfTimeline').value=(d.timeline||[]).join('\n');syncTimelineFromText();renderTimelineEvents();
    q('nfMysteries').value=(d.mysteries||[]).join('\n');syncMysteriesFromText();renderMysteryCards();q('nfScenes').value=(d.scenes||[]).join('\n');syncScenesFromText();renderSceneCards();
    q('nfNotes').value=d.notes||'';
    q('nfStatus').textContent=`Loaded universe: ${d.universe||name}`;
    updateNovelCounts();
    updateCodexDashboard();
    toast('Universe loaded.');
}
async function saveNovelForge(){
    syncCharactersToText();
    syncLocationsToText();
    syncArtifactsToText();
    syncTimelineToText();
    syncMysteriesToText();
    let payload={
        universe:q('nfUniverse').value.trim()||'Untitled Universe',
        premise:q('nfPremise').value,
        characters:q('nfCharacters').value,
        locations:q('nfLocations').value,
        artifacts:q('nfArtifacts').value,
        timeline:q('nfTimeline').value,
        mysteries:q('nfMysteries').value,
        scenes:q('nfScenes').value,
        notes:q('nfNotes').value
    };
    let d=await api('/api/novelforge/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(d?.ok){
        activeUniverseName=d.name;
        q('nfStatus').textContent=d.message;
        updateNovelCounts();
        updateCodexDashboard();
        loadNovelForgeList();
    }
}
async function duplicateNovelForge(name){
    let new_title=prompt('Duplicate universe as:', name+' Copy');
    if(!new_title)return;
    let d=await api('/api/novelforge/duplicate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,new_title})});
    if(d?.ok)loadNovelForgeList();
}
async function renameNovelForge(name){
    let new_title=prompt('Rename universe to:', name);
    if(!new_title)return;
    let d=await api('/api/novelforge/rename',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,new_title})});
    if(d?.ok)loadNovelForgeList();
}
async function deleteNovelForge(name){
    if(!confirm('Delete this Novel Forge universe?'))return;
    let d=await api('/api/novelforge/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
    if(d?.ok){
        if(activeUniverseName===name)clearNovelForge();
        loadNovelForgeList();
    }
}
function novelForgeContext(){
    syncCharactersToText();
    syncLocationsToText();
    syncArtifactsToText();
    syncTimelineToText();
    syncMysteriesToText();
    return `Novel Forge Codex Context

Universe:
${q('nfUniverse').value||'Untitled Universe'}

Premise:
${q('nfPremise').value||'None'}

Characters:
${q('nfCharacters').value||'None'}

Locations:
${q('nfLocations').value||'None'}

Artifacts:
${q('nfArtifacts').value||'None'}

Timeline:
${q('nfTimeline').value||'None'}

Mysteries / Unresolved Threads:
${q('nfMysteries').value||'None'}

Scenes:
${q('nfScenes')?.value||'None'}

Notes:
${q('nfNotes').value||'None'}`;
}
function novelForgeSectionText(section){
    const map={
        premise:['Premise',q('nfPremise').value],
        characters:['Characters',characterCardsText()],
        locations:['Locations',locationCardsText()],
        artifacts:['Artifacts',artifactCardsText()],
        timeline:['Timeline',timelineManagerText()],
        mysteries:['Mysteries / Unresolved Threads',mysteryCardsText()],
        notes:['Notes',q('nfNotes').value]
    };
    if(section==='full')return novelForgeContext();
    let item=map[section]||['Codex',novelForgeContext()];
    return `Novel Forge Section

Universe: ${q('nfUniverse').value||'Untitled Universe'}
Section: ${item[0]}

${item[1]||'None'}`;
}


function codexCounts(){
    return {
        universe:(q('nfUniverse')?.value||'Untitled Universe').trim()||'Untitled Universe',
        characters:nfLines('nfCharacters').length,
        locations:nfLines('nfLocations').length,
        artifacts:nfLines('nfArtifacts').length,
        timeline:nfLines('nfTimeline').length,
        mysteries:nfLines('nfMysteries').length,
        scenes:nfLines('nfScenes').length,
        notes:(q('nfNotes')?.value||'').trim().length
    };
}
function codexReadiness(c){
    let issues=[];
    if(!q('nfPremise')?.value.trim())issues.push('Premise missing');
    if(c.characters<3)issues.push('Few characters');
    if(c.locations<2)issues.push('Few locations');
    if(c.artifacts<1)issues.push('No artifacts');
    if(c.timeline<3)issues.push('Short timeline');
    if(c.mysteries<1)issues.push('No mystery threads');
    if(c.scenes<1)issues.push('No scene briefs');
    if(!issues.length)return 'Codex has enough structure for continuity, arc, and scene planning.';
    return 'Needs attention: '+issues.join(', ');
}
function updateCodexDashboard(){
    if(!q('nfDashboard'))return;
    try{
        syncCharactersToText();
        syncLocationsToText();
        syncArtifactsToText();
        syncTimelineToText();
        syncMysteriesToText();
    }catch(e){}
    let c=codexCounts();
    q('nfDashboard').innerHTML=`<div class=codexdash>
        <div class=codexbox><div class=label>Universe</div><div class=value>${esc(c.universe)}</div></div>
        <div class=codexbox><div class=label>Characters</div><div class=value>${c.characters}</div></div>
        <div class=codexbox><div class=label>Locations</div><div class=value>${c.locations}</div></div>
        <div class=codexbox><div class=label>Artifacts</div><div class=value>${c.artifacts}</div></div>
        <div class=codexbox><div class=label>Timeline</div><div class=value>${c.timeline}</div></div>
        <div class=codexbox><div class=label>Mysteries</div><div class=value>${c.mysteries}</div></div>
        <div class=codexbox><div class=label>Scenes</div><div class=value>${c.scenes}</div></div>
    </div><div class=readiness><div class=time>Story Readiness</div>${esc(codexReadiness(c))}</div>`;
}
function completeStoryBibleText(){
    return `Novel Forge Complete Story Bible

${novelForgeContext()}

Structured Character Cards:
${characterCardsText()}

Structured Locations:
${locationCardsText()}

Structured Artifacts:
${artifactCardsText()}

Structured Timeline:
${timelineManagerText()}

Structured Mysteries:
${mysteryCardsText()}

Structured Scenes:
${sceneCardsText()}`;
}

function storyBiblePayload(){
    syncCharactersToText();
    syncLocationsToText();
    syncArtifactsToText();
    syncTimelineToText();
    syncMysteriesToText();
    let c=codexCounts();
    return {
        universe:c.universe,
        summary:{
            characters:c.characters,
            locations:c.locations,
            artifacts:c.artifacts,
            timeline:c.timeline,
            mysteries:c.mysteries,
            readiness:codexReadiness(c)
        },
        codex:{
            premise:q('nfPremise').value||'',
            characters:q('nfCharacters').value||'',
            locations:q('nfLocations').value||'',
            artifacts:q('nfArtifacts').value||'',
            timeline:q('nfTimeline').value||'',
            mysteries:q('nfMysteries').value||'',
            notes:q('nfNotes').value||'',
            scenes:q('nfScenes')?.value||''
        },
        story_bible:completeStoryBibleText()
    };
}
async function exportStoryBible(){
    if(q('nfExportStatus'))q('nfExportStatus').textContent='Exporting Story Bible...';
    let d=await api('/api/novelforge/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(storyBiblePayload())});
    if(d?.ok){
        if(q('nfExportStatus'))q('nfExportStatus').innerHTML=`${esc(d.message)}
Markdown: ${esc(d.markdown)}
Text: ${esc(d.text)}
JSON: ${esc(d.json)}

<button onclick="sendExportedBiblePath('${js(d.markdown)}')">Send Markdown Path to Mission Console</button>`;
        toast('Story Bible exported.');
    }
}
function sendExportedBiblePath(path){
    go('mission');
    q('input').value=`Please help me with this exported Novel Forge Story Bible:
${path}

Use it as the current story reference.`;
    toast('Exported Story Bible path sent to Mission Console.');
}

function sendCompleteStoryBible(){
    go('mission');
    q('input').value=`You are helping with a full Novel Forge story bible.

Use the complete story bible below to help plan, check continuity, develop arcs, organize canon, and suggest the best next writing step.

Please respond in this structure:

1. Story Bible Summary
2. Strongest Existing Elements
3. Weakest / Least Developed Elements
4. Biggest Continuity Risks
5. Best Development Opportunities
6. Recommended Next Build Step
7. Recommended Next Writing Step

${completeStoryBibleText()}`;
    toast('Complete Story Bible sent to Mission Console input.');
}

function checkNovelContinuity(){
    syncTimelineToText();
    go('mission');
    q('input').value=`You are Novel Forge's continuity engine.

Analyze this Codex for story continuity, canon problems, timeline logic, missing causes, character contradictions, unresolved setup/payoff issues, and risks to reader clarity.

Return your answer in this exact structure:

1. Continuity Pass Summary
2. Major Contradictions
3. Timeline Problems
4. Character Logic Problems
5. Missing Causes / Weak Motivations
6. Unresolved Mystery Setup
7. Canon Risks
8. Suggested Fixes
9. Best Next Writing Step

Codex:
${novelForgeContext()}`;
    toast('Continuity check sent to Mission Console input.');
}
function buildNextStoryArc(){
    syncTimelineToText();
    go('mission');
    q('input').value=`You are Novel Forge's story-arc planner.

Using this Codex, propose the next story arc while preserving canon and honoring unresolved mysteries.

Return your answer in this exact structure:

1. Recommended Next Arc
2. Why This Arc Fits
3. Required Setup
4. Key Scenes
5. Character Changes
6. Mystery Payoff / New Mystery
7. Timeline Placement
8. Continuity Risks
9. First Scene Draft Seed

Codex:
${novelForgeContext()}`;
    toast('Next arc request sent to Mission Console input.');
}

function sendNovelForgeContext(){
    go('mission');
    q('input').value=`You are helping with a Novel Forge universe. Use this codex context to help me plan, check continuity, suggest next steps, or develop the story.

${novelForgeContext()}`;
    toast('Novel Forge Codex sent to Mission Console input.');
}
function sendNovelForgeSection(){
    let section=q('nfSection')?.value||'full';
    go('mission');
    q('input').value=`You are helping with Novel Forge. Use this selected codex section to help me develop, improve, or check continuity.

${novelForgeSectionText(section)}`;
    toast('Novel Forge section sent to Mission Console input.');
}
function clearNovelForge(){
    activeUniverseName=null;
    ['nfUniverse','nfPremise','nfCharacters','nfLocations','nfArtifacts','nfTimeline','nfMysteries','nfScenes','nfNotes'].forEach(id=>q(id).value='');
    q('nfStatus').textContent='New universe.';
    nfCharacterCards=[];renderCharacterCards();
    nfLocationCards=[];renderLocationCards();
    nfArtifactCards=[];renderArtifactCards();
    nfTimelineEvents=[];renderTimelineEvents();
    nfMysteryCards=[];renderMysteryCards();
    nfSceneCards=[];renderSceneCards();
    updateNovelCounts();
}
function loadSlippingTemplate(){
    q('nfUniverse').value='Slipping into Darkness';
    q('nfPremise').value='An ancient vampire mythology universe centered on Kayock, the first vampire and ancient protector, and Anthony / Whisper, a psychic hunter drawn into a prophecy that could end the need for blood.';
    q('nfCharacters').value=slippingCharacterLines().join('\n');
    q('nfLocations').value=slippingLocationLines().join('\n');
    q('nfArtifacts').value=slippingArtifactLines().join('\n');
    q('nfTimeline').value=[
        'Book 1: Anthony learns the prophecy',
        'Book 1: Kayock dies at Jokaya’s hands',
        'Book 1: Anthony stops Jokaya',
        'Book 1: Anthony learns his ex has been turned',
        'Book 2: Hunt the ex and learn who she has become',
        'Book 2: Discover Jokaya’s sanctuary',
        'Book 2: Follow clues to Olmec pyramids',
        'Book 2: Learn Croatoan escaped'
    ].join('\n');
    q('nfMysteries').value=slippingMysteryLines().join('\n');
    q('nfNotes').value='Flagship Novel Forge demonstration universe. Track canon carefully. Separate author knowledge from reader knowledge in future versions.';
    syncCharactersFromText();renderCharacterCards();syncLocationsFromText();renderLocationCards();syncArtifactsFromText();renderArtifactCards();syncTimelineFromText();renderTimelineEvents();syncMysteriesFromText();renderMysteryCards();q('nfScenes').value=starterSceneLines().join('\n');syncScenesFromText();renderSceneCards();updateNovelCounts();
    updateCodexDashboard();
    toast('Slipping into Darkness template loaded.');
}

let activePromptName=null;
let promptCache=[];
async function loadPrompts(){
    try{
        let d=await (await fetch('/api/prompts/list')).json();
        promptCache=d.prompts||[];
        renderPromptList();
    }catch(e){
        if(q('promptList'))q('promptList').textContent='Prompt list unavailable: '+e;
    }
}
function renderPromptList(){
    if(!q('promptList'))return;
    let term=(q('promptSearch')?.value||'').toLowerCase();
    let cat=(q('promptFilter')?.value||'All');
    let items=promptCache.filter(p=>{
        let hay=[p.title,p.category,p.prompt_type,p.notes,p.preview].join(' ').toLowerCase();
        return (!term||hay.includes(term))&&(cat==='All'||p.category===cat);
    });
    if(!items.length){q('promptList').innerHTML='No matching prompts.';return}
    q('promptList').innerHTML=items.map(p=>`<div class=promptitem><h4>${esc(p.title)}</h4><span class=prompttag>${esc(p.category||'General')}</span><span class=prompttag>${esc(p.prompt_type||'User Prompt')}</span><div class=time>${esc(p.modified)}</div><div class=promptpreview>${esc(p.preview||'')}</div><div class=promptactions><button onclick="openPromptSmith('${js(p.name)}')">Load</button><button onclick="duplicatePromptSmith('${js(p.name)}')">Duplicate</button><button onclick="renamePromptSmith('${js(p.name)}')">Rename</button><button onclick="deletePromptSmith('${js(p.name)}')">Delete</button></div></div>`).join('');
}
async function openPromptSmith(name){
    let d=await (await fetch('/api/prompts/read?name='+encodeURIComponent(name))).json();
    if(!d.ok){toast(d.message||'Prompt not found.');return}
    activePromptName=d.name;
    q('promptTitle').value=d.title||d.name||'';
    q('promptCategory').value=d.category||'General';
    q('promptType').value=d.prompt_type||'User Prompt';
    q('promptNotes').value=d.notes||'';
    q('promptDraft').value=d.prompt||d.body||'';
    q('promptSaveStatus').textContent=`Loaded: ${d.title||d.name}`;
    toast('Prompt loaded.');
}
async function savePromptSmith(){
    let title=q('promptTitle').value.trim()||'Untitled Prompt';
    let category=q('promptCategory').value||'General';
    let prompt_type=q('promptType').value||'User Prompt';
    let notes=q('promptNotes').value;
    let prompt=q('promptDraft').value;
    let d=await api('/api/prompts/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,category,prompt_type,notes,prompt})});
    if(d?.ok){
        activePromptName=d.name;
        q('promptSaveStatus').textContent=d.message;
        loadPrompts();
    }
}
async function duplicatePromptSmith(name){
    let new_title=prompt('Duplicate prompt as:', name+' Copy');
    if(!new_title)return;
    let d=await api('/api/prompts/duplicate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,new_title})});
    if(d?.ok)loadPrompts();
}
async function renamePromptSmith(name){
    let new_title=prompt('Rename prompt to:', name);
    if(!new_title)return;
    let d=await api('/api/prompts/rename',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,new_title})});
    if(d?.ok)loadPrompts();
}
async function deletePromptSmith(name){
    if(!confirm('Delete this saved prompt?'))return;
    let d=await api('/api/prompts/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
    if(d?.ok){
        if(activePromptName===name)clearPromptSmith();
        loadPrompts();
    }
}
function copyPromptSmith(){
    let text=q('promptDraft').value;
    navigator.clipboard?.writeText(text);
    toast('Prompt copied.');
}
function promptSmithContext(){
    return `PromptSmith Context
Title: ${q('promptTitle').value||'Untitled'}
Category: ${q('promptCategory').value||'General'}
Type: ${q('promptType').value||'User Prompt'}
Notes: ${q('promptNotes').value||'None'}

Prompt:
${q('promptDraft').value}`;
}
function sendPromptSmith(){
    let text=q('promptDraft').value.trim();
    if(!text){toast('Prompt is empty.');return}
    go('mission');
    q('input').value=text;
    toast('Prompt sent to Mission Console input.');
}
function sendPromptSmithWithContext(){
    let text=q('promptDraft').value.trim();
    if(!text){toast('Prompt is empty.');return}
    go('mission');
    q('input').value=promptSmithContext();
    toast('Prompt with context sent to Mission Console input.');
}
function clearPromptSmith(){
    activePromptName=null;
    q('promptTitle').value='';
    q('promptCategory').value='General';
    q('promptType').value='User Prompt';
    q('promptNotes').value='';
    q('promptDraft').value='';
    q('promptSaveStatus').textContent='New prompt.';
}



async function exportExtensionReport(){
    let d=await api('/api/extensions/report');
    if(d?.ok){
        q('extSummary').textContent=`${d.message}
Modules: ${d.summary.count}
Enabled: ${d.summary.enabled}
Valid: ${d.summary.valid}
Problems: ${d.summary.problems}
Markdown: ${d.markdown}
JSON: ${d.json}`;
        q('extRepair').innerHTML=`<b>Report exported.</b>
<div class=repairbox>Markdown: ${esc(d.markdown)}
JSON: ${esc(d.json)}
Folder: ${esc(d.folder)}</div>
<button onclick="sendExtensionReportPath('${js(d.markdown)}')">Send Report Path to Mission Console</button>`;
        window.extLastReport=d.markdown;
        loadExtensions();
        toast('Extension report exported.');
    }
}
function sendExtensionReportPath(path){
    go('mission');
    q('input').value=`Please review this Kayock Extension Report and recommend fixes or architecture improvements:

${path}`;
    toast('Extension report path sent to Mission Console input.');
}
async function suggestManifestFix(key,manifest){
    let d=await api('/api/extensions/repair_suggest',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key,manifest})});
    if(d?.ok){
        window.extLastManifest=d.manifest;
        window.extLastSuggested=d.suggested;
        q('extRepair').innerHTML=`<b>${esc(d.message)}</b>
<div class=small>Manifest: ${esc(d.manifest)}</div>
<div class=small>Suggested replacement text:</div>
<div class=repairbox>${esc(d.suggested)}</div>
<button onclick="copyManifestSuggestion(window.extLastSuggested)">Copy Suggested Manifest</button>
<button onclick="applyManifestFix(window.extLastManifest,window.extLastSuggested)">Apply Suggested Fix</button>
<button onclick="sendManifestSuggestionToMission(window.extLastManifest,window.extLastSuggested)">Send Suggestion to Mission Console</button>`;
        toast('Manifest suggestion generated.');
    }else if(d?.message){
        q('extRepair').textContent=d.message;
    }
}


function extOfficerText(officer){
    if(!officer)return '';
    if(typeof officer==='string')return officer;
    if(typeof officer==='object'){
        let parts=[];
        if(officer.name)parts.push(officer.name);
        if(officer.callsign)parts.push(`"${officer.callsign}"`);
        if(officer.role)parts.push(`— ${officer.role}`);
        return parts.join(' ')||JSON.stringify(officer);
    }
    return String(officer);
}
function extDashboardFromData(d){
    if(!q('extDashboard')||!d)return;
    let items=d.items||[];
    let total=items.length;
    let enabled=items.filter(x=>x.enabled).length;
    let disabled=total-enabled;
    let valid=items.filter(x=>x.status==='VALID').length;
    let problems=items.filter(x=>x.status!=='VALID'||(x.missing&&x.missing.length)).length;
    let departments=items.filter(x=>String(x.kind||'').toLowerCase()==='department').length;
    let extensions=items.filter(x=>String(x.kind||'').toLowerCase()==='extension').length;
    let systems=items.filter(x=>String(x.kind||'').toLowerCase()==='system').length;
    let hint=problems?`Needs attention: ${problems} manifest problem(s). Use Validate, Suggest Fix, then Apply Suggested Fix if the suggestion looks right.`:'All discovered module manifests look valid.';
    let hintClass=problems?'modhint modwarn':'modhint modok';
    q('extDashboard').innerHTML=`<div class=moddash>
        <div class=modbox><div class=label>Total Modules</div><div class=value>${total}</div></div>
        <div class=modbox><div class=label>Enabled</div><div class=value>${enabled}</div></div>
        <div class=modbox><div class=label>Disabled</div><div class=value>${disabled}</div></div>
        <div class=modbox><div class=label>Valid</div><div class=value>${valid}</div></div>
        <div class=modbox><div class=label>Problems</div><div class=value>${problems}</div></div>
        <div class=modbox><div class=label>Departments</div><div class=value>${departments}</div></div>
        <div class=modbox><div class=label>Extensions</div><div class=value>${extensions}</div></div>
        <div class=modbox><div class=label>System</div><div class=value>${systems}</div></div>
    </div><div class="${hintClass}"><div class=time>Module Readiness</div>${esc(hint)}${window.extLastReport?`<br><br>Last report: ${esc(window.extLastReport)}`:''}</div>`;
}

async function applyManifestFix(manifest,suggested){
    let ok=confirm('Apply this manifest repair now? A backup will be created first.');
    if(!ok)return;
    q('extRepair').textContent='Applying manifest repair safely...';
    let d=await api('/api/extensions/apply_repair',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({manifest,suggested})});
    if(d?.ok){
        q('extRepair').innerHTML=`<b>${esc(d.message)}</b>
<div class=repairbox>Manifest: ${esc(d.manifest)}
Backup: ${esc(d.backup)}

Before:
Status: ${esc(d.before.status)}
Version: ${esc(d.before.version)}
Missing: ${esc((d.before.missing||[]).join(', ')||'None')}

After:
Status: ${esc(d.after.status)}
Version: ${esc(d.after.version)}
Missing: ${esc((d.after.missing||[]).join(', ')||'None')}

Validation:
Checked: ${esc(d.validation.checked)}
Valid: ${esc(d.validation.valid)}
Problems: ${esc((d.validation.problems||[]).length)}</div>
<button onclick="loadExtensions()">Refresh Modules</button>
<button onclick="validateExtensions()">Validate Again</button>
<button onclick="exportExtensionReport()">Export New Report</button>`;
        toast('Manifest repair applied safely.');
        loadExtensions();
    }else{
        q('extRepair').textContent=d?.message||'Manifest repair failed.';
    }
}

function copyManifestSuggestion(txt){
    navigator.clipboard.writeText(txt);
    toast('Suggested manifest copied.');
}
function sendManifestSuggestionToMission(manifest,suggested){
    go('mission');
    q('input').value=`Please review this Kayock manifest repair suggestion before I apply it manually.

Manifest:
${manifest}

Suggested manifest:
${suggested}

Check if this is safe and whether any fields should be changed.`;
    toast('Manifest repair suggestion sent to Mission Console input.');
}


let lastScanReport=null;






















let lastRecoveryDashboard=null;
async function loadRecoveryDashboard(){
    if(!q('recoveryDashCard'))return;
    q('recoveryDashCard').textContent='Loading recovery health...';
    let d=await api('/api/backups/recovery_dashboard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});
    if(!d?.ok){
        q('recoveryDashCard').textContent=d?.message||'Recovery dashboard unavailable.';
        return;
    }
    lastRecoveryDashboard=d;
    let s=d.summary||{};
    let cls=d.healthy?'healthy':'warn';
    q('recoveryDashCard').innerHTML=`<div class="recoveryHealthBadge ${cls}">Recovery Foundation: ${esc(d.health_label||'UNKNOWN')}</div>
<div>Current chain: <b>${esc(d.current_chain||'unknown')}</b></div>
<div class=recoveryMiniGrid>
  <div class=recoveryMini><div class=label>Restore Actions</div><div class=value>${s.restore_actions||0}</div></div>
  <div class=recoveryMini><div class=label>Rollback Actions</div><div class=value>${s.rollback_actions||0}</div></div>
  <div class=recoveryMini><div class=label>Attention</div><div class=value>${s.attention_events||0}</div></div>
  <div class=recoveryMini><div class=label>Errors</div><div class=value>${s.errors||0}</div></div>
  <div class=recoveryMini><div class=label>Superseded</div><div class=value>${s.superseded_events||0}</div></div>
  <div class=recoveryMini><div class=label>Events</div><div class=value>${s.events||0}</div></div>
</div>
<div class=recoveryPath>Latest: ${esc(s.latest_event||'none')} ${s.latest_created?('• '+esc(s.latest_created)) : ''}</div>
<div class=recoveryPath>Restore audit OK: ${s.restore_audit_ok} • Rollback audit OK: ${s.rollback_audit_ok}</div>`;
}
function sendRecoveryDashboardToMission(){
    if(!lastRecoveryDashboard){
        toast('Load recovery health first.');
        return;
    }
    let s=lastRecoveryDashboard.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Recovery Foundation dashboard summary.

Health:
${lastRecoveryDashboard.health_label}

Current chain:
${lastRecoveryDashboard.current_chain}

Summary:
Events: ${s.events}
Targets/chains: ${s.targets}
Restore actions: ${s.restore_actions}
Rollback actions: ${s.rollback_actions}
Backup/staging events: ${s.backup_events}
Evidence reports: ${s.evidence_reports}
Intact events: ${s.intact_events}
Superseded-by-rollback events: ${s.superseded_events}
Attention events: ${s.attention_events}
Errors: ${s.errors}
Latest event: ${s.latest_event}
Latest created: ${s.latest_created}
Restore audit OK: ${s.restore_audit_ok}
Rollback audit OK: ${s.rollback_audit_ok}

Chains:
${(lastRecoveryDashboard.chains||[]).map(c=>`${c.target}
Events: ${c.event_count}
Restores: ${c.restore_actions}
Rollbacks: ${c.rollback_actions}
Backups: ${c.backup_events}
Evidence: ${c.evidence_reports}
Intact: ${c.intact_events}
Superseded: ${c.superseded_events||0}
Attention: ${c.attention_events}
Latest: ${c.latest_created}`).join('\n\n')}

Safety:
Read-only dashboard.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether Recovery Foundation should be marked healthy
2. Whether the Command Bridge card is accurate
3. Whether v10.8.x can be frozen as the Recovery Foundation milestone
4. Whether the next build should move to a new milestone area.`;
    toast('Recovery dashboard sent to Mission Console.');
}

let lastRecoveryTimeline=null;
function timelineBadge(status){
    status=(status||'other').toLowerCase();
    let cls=(status==='intact'||status==='attention'||status==='evidence'||status==='superseded_by_rollback')?status:'other';
    return `<span class="tlbadge ${cls}">${esc(status.toUpperCase())}</span>`;
}
async function loadRecoveryTimeline(doExport=false){
    let query=q('recoveryTimelineFilter').value||'';
    let limit=parseInt(q('recoveryTimelineLimit').value||'1000');
    q('recoveryTimelineStatus').textContent='Loading recovery timeline...';
    let d=await api('/api/backups/recovery_timeline',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,limit,export:doExport})});
    if(!d?.ok){
        q('recoveryTimelineStatus').textContent=d?.message||'Could not load recovery timeline.';
        return;
    }
    lastRecoveryTimeline=d;
    let s=d.summary||{};
    q('recoveryTimelineStatus').textContent=`Recovery timeline loaded.
Events: ${s.events||0}
Targets/chains: ${s.targets||0}
Restore actions: ${s.restore_actions||0}
Rollback actions: ${s.rollback_actions||0}
Backup/staging events: ${s.backup_events||0}
Evidence reports: ${s.evidence_reports||0}
Intact events: ${s.intact_events||0}
Attention events: ${s.attention_events||0}
Superseded-by-rollback events: ${s.superseded_events||0}
Errors: ${s.errors||0}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('recoveryTimelineDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Events</div><div class=value>${s.events||0}</div></div>
        <div class=vaultmetric><div class=label>Chains</div><div class=value>${s.targets||0}</div></div>
        <div class=vaultmetric><div class=label>Restores</div><div class=value>${s.restore_actions||0}</div></div>
        <div class=vaultmetric><div class=label>Rollbacks</div><div class=value>${s.rollback_actions||0}</div></div>
        <div class=vaultmetric><div class=label>Backups</div><div class=value>${s.backup_events||0}</div></div>
        <div class=vaultmetric><div class=label>Evidence</div><div class=value>${s.evidence_reports||0}</div></div>
        <div class=vaultmetric><div class=label>Attention</div><div class=value>${s.attention_events||0}</div></div>
        <div class=vaultmetric><div class=label>Superseded</div><div class=value>${s.superseded_events||0}</div></div>
        <div class=vaultmetric><div class=label>Errors</div><div class=value>${s.errors||0}</div></div>
    </div><div class=status>Latest event: ${esc(s.latest_event||'none')} | ${esc(s.latest_created||'')}</div>`;
    q('recoveryTimelineChains').innerHTML=(d.chains||[]).map(c=>`<div class="histrow ${c.attention_events?'info':'ok'}"><b>${esc(c.target)}</b>
<div>Events: ${c.event_count} | Restores: ${c.restore_actions} | Rollbacks: ${c.rollback_actions} | Backups: ${c.backup_events} | Evidence: ${c.evidence_reports}</div>
<div>Intact: ${c.intact_events} | Superseded: ${c.superseded_events||0} | Attention: ${c.attention_events} | Latest: ${esc(c.latest_created||'')}</div>
</div>`).join('')||'No recovery chains found.';
    q('recoveryTimelineKinds').innerHTML=(d.kind_counts||[]).map(k=>`<div class="histrow info"><b>${esc(k.kind)}</b><div>Count: ${k.count}</div></div>`).join('')||'No event type summary.';
    q('recoveryTimelineEvents').innerHTML=(d.events||[]).map(e=>{
        let h=e.hashes||{};
        let p=e.paths||{};
        let failed=(e.checks||[]).filter(c=>!c.ok);
        return `<div class="histrow timelineEvent ${e.status==='intact'?'ok':'info'}"><b>${esc(e.created||'unknown time')} — ${esc(e.kind)} — ${esc(e.title)}</b>${timelineBadge(e.status)}
<div>${esc(e.summary||'')}</div>
<div class=vaultpath>Target: ${esc(e.target||'')}</div>
<div class=vaultpath>Source: ${esc(e.source||'')}</div>
${Object.keys(p).map(k=>`<div class=vaultpath>${esc(k)}: ${esc(p[k]||'')}</div>`).join('')}
${Object.keys(h).map(k=>`<div class=timelineHash>${esc(k)}: ${esc(h[k]||'')}</div>`).join('')}
<details><summary>Checks: ${(e.checks||[]).length} | Failed: ${failed.map(c=>c.id).join(', ')||'none'}</summary>${(e.checks||[]).map(c=>`<div class=packagefile>${c.ok?'PASS':'FAIL'} — ${esc(c.id)} — ${esc(c.message)} — ${esc(c.path||'')}</div>`).join('')}</details>
</div>`;
    }).join('')||'No timeline events found.';
    toast('Recovery timeline loaded.');
}
function sendRecoveryTimelineToMission(){
    if(!lastRecoveryTimeline){
        toast('Load recovery timeline first.');
        return;
    }
    let s=lastRecoveryTimeline.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Recovery Timeline.

This is a read-only timeline review. No restore or rollback action is requested.

Summary:
Events: ${s.events}
Targets/chains: ${s.targets}
Restore actions: ${s.restore_actions}
Rollback actions: ${s.rollback_actions}
Backup/staging events: ${s.backup_events}
Evidence reports: ${s.evidence_reports}
Intact events: ${s.intact_events}
Attention events: ${s.attention_events}
Superseded-by-rollback events: ${s.superseded_events||0}
Errors: ${s.errors}
Latest event: ${s.latest_event}
Latest created: ${s.latest_created}

Exported Timeline:
${lastRecoveryTimeline.exported?.markdown||'No exported timeline path'}

Chains:
${(lastRecoveryTimeline.chains||[]).map(c=>`${c.target}
Events: ${c.event_count}
Restores: ${c.restore_actions}
Rollbacks: ${c.rollback_actions}
Backups: ${c.backup_events}
Evidence: ${c.evidence_reports}
Intact: ${c.intact_events}
Superseded: ${c.superseded_events||0}
Attention: ${c.attention_events}
Latest: ${c.latest_created}`).join('\n\n')}

Events:
${(lastRecoveryTimeline.events||[]).map(e=>`${e.created} — ${e.kind} — ${e.title}
Status: ${e.status}
Target: ${e.target}
Summary: ${e.summary}
Source: ${e.source}
Paths: ${JSON.stringify(e.paths||{})}
Hashes: ${JSON.stringify(e.hashes||{})}`).join('\n\n')}

Safety:
Read-only timeline.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the recovery chain is complete and understandable
2. Whether restore and rollback actions remain auditable together
3. Whether any attention or error item should block future recovery actions
4. Whether the next build should add a Recovery Dashboard summary card on Command Bridge
5. Whether we should freeze v10.8.x as the Recovery Foundation milestone.`;
    toast('Recovery timeline sent to Mission Console.');
}

let lastRollbackAudit=null;
function rollbackAuditBadge(status){
    status=(status||'attention').toLowerCase();
    return `<span class="rbauditbadge ${status}">${esc(status.toUpperCase())}</span>`;
}
async function loadRollbackAudit(doExport=false){
    let query=q('rollbackAuditFilter').value||'';
    let limit=parseInt(q('rollbackAuditLimit').value||'1000');
    q('rollbackAuditStatus').textContent='Loading rollback audit...';
    let d=await api('/api/backups/rollback_audit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,limit,export:doExport})});
    if(!d?.ok){
        q('rollbackAuditStatus').textContent=d?.message||'Could not load rollback audit.';
        return;
    }
    lastRollbackAudit=d;
    let s=d.summary||{};
    q('rollbackAuditStatus').textContent=`Rollback audit loaded.
Actions: ${s.actions||0}
Intact: ${s.intact||0}
Attention: ${s.attention||0}
Verified: ${s.verified||0}
Rollback sources present: ${s.rollback_sources_present||0}
Rollback source hashes intact: ${s.rollback_source_hashes_intact||0}
Pre-rollback backups present: ${s.pre_rollback_backups_present||0}
Targets still rolled back: ${s.targets_still_rolled_back||0}
Errors: ${s.errors||0}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('rollbackAuditDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Actions</div><div class=value>${s.actions||0}</div></div>
        <div class=vaultmetric><div class=label>Intact</div><div class=value>${s.intact||0}</div></div>
        <div class=vaultmetric><div class=label>Attention</div><div class=value>${s.attention||0}</div></div>
        <div class=vaultmetric><div class=label>Verified</div><div class=value>${s.verified||0}</div></div>
        <div class=vaultmetric><div class=label>Sources</div><div class=value>${s.rollback_sources_present||0}</div></div>
        <div class=vaultmetric><div class=label>Source Hash OK</div><div class=value>${s.rollback_source_hashes_intact||0}</div></div>
        <div class=vaultmetric><div class=label>Targets Rolled Back</div><div class=value>${s.targets_still_rolled_back||0}</div></div>
        <div class=vaultmetric><div class=label>Errors</div><div class=value>${s.errors||0}</div></div>
    </div><div class=status>Latest action: ${esc(s.latest_action||'none')} | ${esc(s.latest_created||'')}</div>`;
    q('rollbackAuditStatusList').innerHTML=(d.by_status||[]).map(x=>`<div class="histrow info"><b>${esc(x.status)}</b><div>Count: ${x.count}</div></div>`).join('')||'No status summary.';
    q('rollbackAuditTargetList').innerHTML=(d.by_target||[]).map(x=>`<div class="histrow info"><b>${esc(x.target)}</b><div>Count: ${x.count} | Intact: ${x.intact} | Attention: ${x.attention}</div></div>`).join('')||'No target summary.';
    q('rollbackAuditList').innerHTML=(d.actions||[]).map(a=>`<div class="histrow ${a.status==='intact'?'ok':'info'}"><b>${esc(a.name)}</b>${rollbackAuditBadge(a.status)}
<div>Created: ${esc(a.created||'')} | Verification: ${a.verification_ok} (${a.verification_passed}/${a.verification_checked})</div>
<div>Target still matches rollback hash: ${a.target_current_matches_rollback_hash} | Rollback source hash intact: ${a.rollback_source_backup_hash_intact}</div>
<div class=vaultpath>Target: ${esc(a.target||'')}</div>
<div class=vaultpath>Rollback source backup: ${esc(a.rollback_source_backup||'')}</div>
<div class=vaultpath>Pre-rollback current target backup: ${esc(a.pre_rollback_current_target_backup||'')}</div>
<div class=vaultpath>Original restore action: ${esc(a.restore_action||'')}</div>
<div class=vaultpath>Rollback report: ${esc(a.rollback_report_markdown||a.rollback_report_json||'')}</div>
<div class=vaultpath>Repair log: ${esc(a.repair_action_log_markdown||a.repair_action_log_json||'')}</div>
<div class=rbauditHash>target_before_rollback: ${esc((a.hashes||{}).target_before_rollback||'')}</div>
<div class=rbauditHash>pre_rollback_backup: ${esc((a.hashes||{}).pre_rollback_current_target_backup||'')}</div>
<div class=rbauditHash>rollback_source: ${esc((a.hashes||{}).rollback_source_backup||'')}</div>
<div class=rbauditHash>target_after_rollback: ${esc((a.hashes||{}).target_after_rollback||'')}</div>
<div class=rbauditHash>target_current: ${esc(a.target_current_hash||'')}</div>
<details><summary>Checks (${(a.checks||[]).length}) / Failed: ${(a.failed_checks||[]).join(', ')||'none'}</summary>${(a.checks||[]).map(c=>`<div class=packagefile>${c.ok?'PASS':'FAIL'} — ${esc(c.id)} — ${esc(c.message)} — ${esc(c.path||'')}</div>`).join('')}</details>
</div>`).join('')||'No rollback actions found.';
    toast('Rollback audit loaded.');
}
function sendRollbackAuditToMission(){
    if(!lastRollbackAudit){
        toast('Load rollback audit first.');
        return;
    }
    let s=lastRollbackAudit.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Rollback Audit Inventory.

This is a read-only audit review. No rollback or restore action is requested.

Summary:
Actions: ${s.actions}
Intact: ${s.intact}
Attention: ${s.attention}
Verified: ${s.verified}
Rollback sources present: ${s.rollback_sources_present}
Rollback source hashes intact: ${s.rollback_source_hashes_intact}
Pre-rollback backups present: ${s.pre_rollback_backups_present}
Pre-rollback backup hashes intact: ${s.pre_rollback_backup_hashes_intact}
Targets still rolled back: ${s.targets_still_rolled_back}
Restore action reports present: ${s.restore_action_reports_present}
Repair logs present: ${s.repair_logs_present}
Errors: ${s.errors}
Latest action: ${s.latest_action}
Latest created: ${s.latest_created}

Exported Audit:
${lastRollbackAudit.exported?.markdown||'No exported rollback audit path'}

Actions:
${(lastRollbackAudit.actions||[]).map(a=>`${a.status.toUpperCase()} — ${a.name}
Created: ${a.created}
Original restore action: ${a.restore_action}
Target: ${a.target}
Rollback source backup: ${a.rollback_source_backup}
Pre-rollback current target backup: ${a.pre_rollback_current_target_backup}
Verification OK: ${a.verification_ok}
Verification message: ${a.verification_message}
Target still matches rollback hash: ${a.target_current_matches_rollback_hash}
Rollback source hash intact: ${a.rollback_source_backup_hash_intact}
Pre-rollback backup hash intact: ${a.pre_rollback_current_target_backup_hash_intact}
Target before rollback: ${(a.hashes||{}).target_before_rollback}
Pre-rollback backup: ${(a.hashes||{}).pre_rollback_current_target_backup}
Rollback source: ${(a.hashes||{}).rollback_source_backup}
Target after rollback: ${(a.hashes||{}).target_after_rollback}
Target current: ${a.target_current_hash}
Failed checks: ${(a.failed_checks||[]).join(', ')||'none'}
Rollback report: ${a.rollback_report_markdown||a.rollback_report_json}
Repair log: ${a.repair_action_log_markdown||a.repair_action_log_json}`).join('\n\n')}

Safety:
Read-only viewer.
No rollback.
No restore.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the completed rollback action remains auditable
2. Whether the rollback source backup is intact
3. Whether the pre-rollback backup is intact
4. Whether the target still matches the rollback result
5. Whether any attention item should block future rollback/restore actions.`;
    toast('Rollback audit sent to Mission Console.');
}

let lastRollbackAction=null;
let lastRollbackPreflight=null;
async function loadRollbackActionList(){
    q('rollbackActionStatus').textContent='Loading restore actions...';
    let d=await api('/api/backups/restore_audit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});
    if(!d?.ok){
        q('rollbackActionStatus').textContent=d?.message||'Could not load restore actions.';
        return;
    }
    let sel=q('rollbackActionSelect');
    sel.innerHTML=(d.actions||[]).map(a=>`<option value="${esc(a.restore_report_json||a.pre_restore_live_backup||a.name)}">${esc(a.name)} → ${esc(a.target||'unknown target')}</option>`).join('');
    if((d.actions||[]).length){
        q('rollbackActionPath').value=d.actions[0].restore_report_json||d.actions[0].pre_restore_live_backup||d.actions[0].name;
    }
    q('rollbackActionStatus').textContent=`Loaded ${d.actions?.length||0} restore action(s). Run rollback preflight first.`;
}
async function preflightRollbackAction(){
    let path=q('rollbackActionPath').value||q('rollbackActionSelect').value||'';
    if(!path){
        q('rollbackActionStatus').textContent='Select a restore action first.';
        return;
    }
    q('rollbackActionStatus').textContent='Running rollback preflight...';
    let d=await api('/api/backups/rollback_preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action_report:path,export:true})});
    lastRollbackPreflight=d;
    q('rollbackActionResult').textContent=JSON.stringify(d,null,2);
    if(!d?.ok){
        q('rollbackActionStatus').textContent=d?.message||'Rollback preflight failed.';
        return;
    }
    q('rollbackActionConfirm').value='';
    q('rollbackActionConfirm').placeholder=d.future_rollback_phrase||'Exact rollback phrase unavailable';
    let s=d.summary||{};
    q('rollbackActionStatus').textContent=`Rollback preflight complete.
Candidate status: ${s.candidate_status}
Hard blocks excluding rollback lock: ${s.hard_blocks}
Would overwrite: ${s.would_overwrite}
Future rollback phrase required:
${d.future_rollback_phrase}`;
    q('rollbackActionChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.status==='pass'?'ok':(c.status==='block'?'fail':'info')}"><b>${esc(c.id)}</b>${rollbackBadge(c.status)}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.detail||'')}</div></div>`).join('');
    toast('Rollback preflight complete.');
}
async function runSingleFileRollback(){
    let path=q('rollbackActionPath').value||q('rollbackActionSelect').value||'';
    let confirm=q('rollbackActionConfirm').value||'';
    if(!path){
        q('rollbackActionStatus').textContent='Select a restore action first.';
        return;
    }
    if(!lastRollbackPreflight || (lastRollbackPreflight.summary||{}).restore_action!==((lastRollbackPreflight.restore_action||{}).name||'')){
        // Keep this lenient; backend re-runs the preview.
    }
    if(!lastRollbackPreflight){
        q('rollbackActionStatus').textContent='Run rollback preflight first.';
        return;
    }
    if(confirm!==lastRollbackPreflight.future_rollback_phrase){
        q('rollbackActionStatus').textContent='Exact rollback phrase does not match the preflight phrase.';
        return;
    }
    if(!window.confirm('This will overwrite the original target with the pre-restore backup after backing up the current target. Continue?')){
        q('rollbackActionStatus').textContent='Rollback cancelled.';
        return;
    }
    if(!window.confirm('Final confirmation: run the live single-file rollback action now?')){
        q('rollbackActionStatus').textContent='Rollback cancelled at final confirmation.';
        return;
    }
    q('rollbackActionStatus').textContent='Running single-file rollback...';
    let d=await api('/api/backups/single_file_rollback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action_report:path,confirm})});
    lastRollbackAction=d;
    q('rollbackActionResult').textContent=JSON.stringify(d,null,2);
    let v=d?.verification||{};
    q('rollbackActionChecks').innerHTML=(v.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id)}</b>${rollbackBadge(c.ok?'pass':'block')}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.path||'')}</div></div>`).join('')||'No verification checks.';
    if(d?.ok){
        q('rollbackActionStatus').textContent=`Single-file rollback complete and verified.
Target: ${d.target}
Pre-rollback current-target backup: ${d.pre_rollback_current_target_backup}
Report: ${d.exported?.markdown||''}
Repair log: ${d.repair_action_log?.markdown||''}`;
        toast('Single-file rollback complete and verified.');
    }else{
        q('rollbackActionStatus').textContent=d?.message||'Rollback failed or was blocked.';
        toast('Rollback failed or blocked.');
    }
}
function sendRollbackActionToMission(){
    if(!lastRollbackAction){
        toast('Run a rollback action first.');
        return;
    }
    go('mission');
    let v=lastRollbackAction.verification||{};
    let h=lastRollbackAction.hashes||{};
    q('input').value=`Please review this Kayock Single-File Rollback Action result.

This was a narrow rollback action from the pre-restore live backup.

Result:
OK: ${lastRollbackAction.ok}
Message: ${lastRollbackAction.message}
Target: ${lastRollbackAction.target}
Rollback source backup: ${lastRollbackAction.rollback_source_backup}
Pre-rollback current target backup: ${lastRollbackAction.pre_rollback_current_target_backup}
Original restore action: ${lastRollbackAction.restore_action}
Confirmation phrase: ${lastRollbackAction.confirmation_phrase}

Hashes:
Target before rollback: ${h.target_before_rollback}
Pre-rollback current target backup: ${h.pre_rollback_current_target_backup}
Rollback source backup: ${h.rollback_source_backup}
Recorded old target: ${h.recorded_old_target}
Recorded live backup: ${h.recorded_live_backup}
Target after rollback: ${h.target_after_rollback}

Verification:
${v.message||''}
${(v.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message} ${c.path||''}`).join('\n')}

Reports:
Rollback report: ${lastRollbackAction.exported?.markdown||''}
RepairActions log: ${lastRollbackAction.repair_action_log?.markdown||''}

Safety:
Single file only.
From pre-restore backup only.
Original target only.
Current target backed up before rollback.
Exact confirmation phrase required.
No folder rollback.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether rollback was successful
2. Whether the pre-rollback backup makes re-restore safe
3. Whether post-rollback hash verification is sufficient
4. Whether the rollback action should stay limited to generated files
5. Whether to build a rollback audit viewer next.`;
    toast('Rollback result sent to Mission Console.');
}

let lastRollbackPreview=null;
async function loadRollbackPreviewActions(){
    q('rollbackPreviewStatus').textContent='Loading restore actions...';
    let d=await api('/api/backups/restore_audit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});
    if(!d?.ok){
        q('rollbackPreviewStatus').textContent=d?.message||'Could not load restore actions.';
        return;
    }
    let sel=q('rollbackPreviewSelect');
    sel.innerHTML=(d.actions||[]).map(a=>`<option value="${esc(a.restore_report_json||a.pre_restore_live_backup||a.name)}">${esc(a.name)} → ${esc(a.target||'unknown target')}</option>`).join('');
    if((d.actions||[]).length){
        q('rollbackPreviewPath').value=d.actions[0].restore_report_json||d.actions[0].pre_restore_live_backup||d.actions[0].name;
    }
    q('rollbackPreviewStatus').textContent=`Loaded ${d.actions?.length||0} restore action(s). Select one and run rollback preview.`;
}
function rollbackBadge(status){
    status=(status||'block').toLowerCase();
    return `<span class="rollbackbadge ${status}">${esc(status.toUpperCase())}</span>`;
}
async function runRollbackPreview(doExport=false){
    let path=q('rollbackPreviewPath').value||q('rollbackPreviewSelect').value||'';
    if(!path){
        q('rollbackPreviewStatus').textContent='Select a restore action first.';
        return;
    }
    q('rollbackPreviewStatus').textContent='Running rollback preview...';
    let d=await api('/api/backups/rollback_preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action_report:path,export:doExport})});
    if(!d?.ok){
        q('rollbackPreviewStatus').textContent=d?.message||'Rollback preview failed.';
        return;
    }
    lastRollbackPreview=d;
    let s=d.summary||{};
    q('rollbackPreviewStatus').textContent=`Rollback preview complete.
Candidate status: ${s.candidate_status}
Checks: ${s.checks}
Passed: ${s.pass}
Warnings: ${s.warn}
Blocks: ${s.block}
Hard blocks excluding rollback lock: ${s.hard_blocks}
Rollback allowed now: ${s.rollback_allowed_now}
Would overwrite: ${s.would_overwrite}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('rollbackPreviewDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Candidate</div><div class=value>${esc((s.candidate_status||'').replaceAll('_',' '))}</div></div>
        <div class=vaultmetric><div class=label>Passed</div><div class=value>${s.pass||0}</div></div>
        <div class=vaultmetric><div class=label>Warnings</div><div class=value>${s.warn||0}</div></div>
        <div class=vaultmetric><div class=label>Blocks</div><div class=value>${s.block||0}</div></div>
        <div class=vaultmetric><div class=label>Hard Blocks</div><div class=value>${s.hard_blocks||0}</div></div>
        <div class=vaultmetric><div class=label>Would Overwrite</div><div class=value>${s.would_overwrite?'YES':'NO'}</div></div>
        <div class=vaultmetric><div class=label>Same Hash</div><div class=value>${s.same_hash?'YES':'NO'}</div></div>
        <div class=vaultmetric><div class=label>Text Diff</div><div class=value>${s.text_preview_available?'YES':'NO'}</div></div>
    </div><div class=status>Rollback remains intentionally unavailable in this build. Preview only.</div>`;
    q('rollbackPreviewChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.status==='pass'?'ok':(c.status==='block'?'fail':'info')}"><b>${esc(c.id)}</b>${rollbackBadge(c.status)}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.detail||'')}</div></div>`).join('')||'No checks.';
    q('rollbackPreviewDiff').textContent=(d.comparison||{}).diff_preview||'No diff preview.';
    q('rollbackPreviewPhrase').innerHTML=`<div class=rollbackphrase>${esc(d.future_rollback_phrase||'')}</div><div class=small>This phrase does not unlock rollback in this build. Actual rollback is still unavailable.</div>`;
    toast('Rollback preview complete.');
}
function sendRollbackPreviewToMission(){
    if(!lastRollbackPreview){
        toast('Run rollback preview first.');
        return;
    }
    let s=lastRollbackPreview.summary||{};
    let b=lastRollbackPreview.rollback_source_backup||{};
    let t=lastRollbackPreview.target||{};
    go('mission');
    q('input').value=`Please review this Kayock Rollback Preview.

No rollback action is requested or possible in this build.

Summary:
Candidate status: ${s.candidate_status}
Checks: ${s.checks}
Passed: ${s.pass}
Warnings: ${s.warn}
Blocks: ${s.block}
Hard blocks excluding intentional rollback lock: ${s.hard_blocks}
Rollback allowed now: ${s.rollback_allowed_now}
Restore action: ${s.restore_action}
Target: ${s.target}
Pre-restore backup: ${s.pre_restore_backup}
Same hash: ${s.same_hash}
Would overwrite: ${s.would_overwrite}
Text diff available: ${s.text_preview_available}

Future rollback phrase:
${lastRollbackPreview.future_rollback_phrase}

Hashes:
Pre-restore backup: ${b.sha256}
Recorded live backup: ${b.recorded_live_backup_sha256}
Recorded old target: ${b.recorded_old_target_sha256}
Current target: ${t.sha256_now}
Recorded restored target: ${t.recorded_restored_sha256}

Checks:
${(lastRollbackPreview.checks||[]).map(c=>`${c.status.toUpperCase()} — ${c.id}: ${c.message} ${c.detail||''}`).join('\n')}

Diff Preview:
${(lastRollbackPreview.comparison||{}).diff_preview||'No diff preview'}

Exported Report:
${lastRollbackPreview.exported?.markdown||'No exported rollback preview path'}

Safety:
Preview only.
No rollback button.
No rollback endpoint.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the pre-restore backup is a valid future rollback source
2. Whether current target state is safe to rollback from
3. Whether any warning should become a hard block
4. Whether the rollback phrase is strong enough
5. Whether the next build should still be preview-only or can safely introduce a single-file rollback action.`;
    toast('Rollback preview sent to Mission Console.');
}

let lastRestoreAudit=null;
function auditBadge(status){
    status=(status||'attention').toLowerCase();
    return `<span class="auditbadge ${status}">${esc(status.toUpperCase())}</span>`;
}
async function loadRestoreAudit(doExport=false){
    let query=q('restoreAuditFilter').value||'';
    let limit=parseInt(q('restoreAuditLimit').value||'1000');
    q('restoreAuditStatus').textContent='Loading post-restore audit...';
    let d=await api('/api/backups/restore_audit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,limit,export:doExport})});
    if(!d?.ok){
        q('restoreAuditStatus').textContent=d?.message||'Could not load restore audit.';
        return;
    }
    lastRestoreAudit=d;
    let s=d.summary||{};
    q('restoreAuditStatus').textContent=`Restore audit loaded.
Actions: ${s.actions||0}
Intact: ${s.intact||0}
Attention: ${s.attention||0}
Verified: ${s.verified||0}
Live backups present: ${s.live_backups_present||0}
Live backup hashes intact: ${s.live_backup_hashes_intact||0}
Targets still restored: ${s.targets_still_restored||0}
Errors: ${s.errors||0}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('restoreAuditDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Actions</div><div class=value>${s.actions||0}</div></div>
        <div class=vaultmetric><div class=label>Intact</div><div class=value>${s.intact||0}</div></div>
        <div class=vaultmetric><div class=label>Attention</div><div class=value>${s.attention||0}</div></div>
        <div class=vaultmetric><div class=label>Verified</div><div class=value>${s.verified||0}</div></div>
        <div class=vaultmetric><div class=label>Live Backups</div><div class=value>${s.live_backups_present||0}</div></div>
        <div class=vaultmetric><div class=label>Backup Hash OK</div><div class=value>${s.live_backup_hashes_intact||0}</div></div>
        <div class=vaultmetric><div class=label>Targets Restored</div><div class=value>${s.targets_still_restored||0}</div></div>
        <div class=vaultmetric><div class=label>Errors</div><div class=value>${s.errors||0}</div></div>
    </div><div class=status>Latest action: ${esc(s.latest_action||'none')} | ${esc(s.latest_created||'')}</div>`;
    q('restoreAuditStatusList').innerHTML=(d.by_status||[]).map(x=>`<div class="histrow info"><b>${esc(x.status)}</b><div>Count: ${x.count}</div></div>`).join('')||'No status summary.';
    q('restoreAuditTargetList').innerHTML=(d.by_target||[]).map(x=>`<div class="histrow info"><b>${esc(x.target)}</b><div>Count: ${x.count} | Intact: ${x.intact} | Attention: ${x.attention}</div></div>`).join('')||'No target summary.';
    q('restoreAuditList').innerHTML=(d.actions||[]).map(a=>`<div class="histrow ${a.status==='intact'?'ok':'info'}"><b>${esc(a.name)}</b>${auditBadge(a.status)}
<div>Created: ${esc(a.created||'')} | Verification: ${a.verification_ok} (${a.verification_passed}/${a.verification_checked})</div>
<div>Target still matches restored hash: ${a.target_current_matches_restored_hash} | Live backup hash intact: ${a.pre_restore_live_backup_hash_intact}</div>
<div class=vaultpath>Target: ${esc(a.target||'')}</div>
<div class=vaultpath>Pre-restore live backup: ${esc(a.pre_restore_live_backup||'')}</div>
<div class=vaultpath>Staged copy: ${esc(a.staged_copy||'')}</div>
<div class=vaultpath>Source backup: ${esc(a.source_backup||'')}</div>
<div class=vaultpath>Restore report: ${esc(a.restore_report_markdown||a.restore_report_json||'')}</div>
<div class=vaultpath>Repair log: ${esc(a.repair_action_log_markdown||a.repair_action_log_json||'')}</div>
<div class=hashline>target_before: ${esc((a.hashes||{}).target_before||'')}</div>
<div class=hashline>live_backup: ${esc((a.hashes||{}).live_backup||'')}</div>
<div class=hashline>staged_copy: ${esc((a.hashes||{}).staged_copy||'')}</div>
<div class=hashline>target_after: ${esc((a.hashes||{}).target_after||'')}</div>
<div class=hashline>target_current: ${esc(a.target_current_hash||'')}</div>
<details><summary>Checks (${(a.checks||[]).length}) / Failed: ${(a.failed_checks||[]).join(', ')||'none'}</summary>${(a.checks||[]).map(c=>`<div class=packagefile>${c.ok?'PASS':'FAIL'} — ${esc(c.id)} — ${esc(c.message)} — ${esc(c.path||'')}</div>`).join('')}</details>
</div>`).join('')||'No restore actions found.';
    toast('Restore audit loaded.');
}
function sendRestoreAuditToMission(){
    if(!lastRestoreAudit){
        toast('Load restore audit first.');
        return;
    }
    let s=lastRestoreAudit.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Post-Restore Audit Inventory.

This is a read-only audit review. No restore action is requested.

Summary:
Actions: ${s.actions}
Intact: ${s.intact}
Attention: ${s.attention}
Verified: ${s.verified}
Live backups present: ${s.live_backups_present}
Live backup hashes intact: ${s.live_backup_hashes_intact}
Staged copy hashes intact: ${s.staged_copy_hashes_intact}
Targets still restored: ${s.targets_still_restored}
Repair logs present: ${s.repair_logs_present}
Errors: ${s.errors}
Latest action: ${s.latest_action}
Latest created: ${s.latest_created}

Exported Audit:
${lastRestoreAudit.exported?.markdown||'No exported audit path'}

Actions:
${(lastRestoreAudit.actions||[]).map(a=>`${a.status.toUpperCase()} — ${a.name}
Created: ${a.created}
Target: ${a.target}
Pre-restore live backup: ${a.pre_restore_live_backup}
Staged copy: ${a.staged_copy}
Source backup: ${a.source_backup}
Verification OK: ${a.verification_ok}
Verification message: ${a.verification_message}
Target still matches restored hash: ${a.target_current_matches_restored_hash}
Live backup hash intact: ${a.pre_restore_live_backup_hash_intact}
Target before: ${(a.hashes||{}).target_before}
Live backup: ${(a.hashes||{}).live_backup}
Staged copy: ${(a.hashes||{}).staged_copy}
Target after: ${(a.hashes||{}).target_after}
Target current: ${a.target_current_hash}
Failed checks: ${(a.failed_checks||[]).join(', ')||'none'}
Restore report: ${a.restore_report_markdown||a.restore_report_json}
Repair log: ${a.repair_action_log_markdown||a.repair_action_log_json}`).join('\n\n')}

Safety:
Read-only viewer.
No restore.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the completed restore action remains auditable
2. Whether the live backup is intact
3. Whether the restored target still matches the restored hash
4. Whether any attention item should block future restores
5. Whether the next build should add a rollback-from-pre-restore-backup preview only.`;
    toast('Restore audit sent to Mission Console.');
}

let lastRestoreAction=null;
let lastRestorePreflight=null;
async function loadRestoreActionList(){
    q('restoreActionStatus').textContent='Loading staging packages...';
    let d=await api('/api/backups/staging_packages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});
    if(!d?.ok){
        q('restoreActionStatus').textContent=d?.message||'Could not load staging packages.';
        return;
    }
    let sel=q('restoreActionSelect');
    sel.innerHTML=(d.packages||[]).map(p=>`<option value="${esc(p.stage_dir)}">${esc(p.name)} → ${esc(p.future_target||'unknown target')}</option>`).join('');
    if((d.packages||[]).length){
        q('restoreActionPath').value=d.packages[0].stage_dir;
    }
    q('restoreActionStatus').textContent=`Loaded ${d.packages?.length||0} staging package(s). Run preflight before restore.`;
}
async function preflightRestoreAction(){
    let path=q('restoreActionPath').value||q('restoreActionSelect').value||'';
    if(!path){
        q('restoreActionStatus').textContent='Select a staging package first.';
        return;
    }
    q('restoreActionStatus').textContent='Running restore preflight...';
    let d=await api('/api/backups/restore_final_check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({stage_dir:path,export:true})});
    lastRestorePreflight=d;
    q('restoreActionResult').textContent=JSON.stringify(d,null,2);
    if(!d?.ok){
        q('restoreActionStatus').textContent=d?.message||'Preflight failed.';
        return;
    }
    q('restoreActionConfirm').value='';
    q('restoreActionConfirm').placeholder=d.future_restore_phrase||'Exact restore phrase unavailable';
    let s=d.summary||{};
    q('restoreActionStatus').textContent=`Preflight complete.
Final status: ${s.final_status}
Hard blocks excluding restore lock: ${s.hard_blocks}
Future restore phrase required:
${d.future_restore_phrase}`;
    q('restoreActionChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.status==='pass'?'ok':(c.status==='block'?'fail':'info')}"><b>${esc(c.id)}</b>${finalBadge(c.status)}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.detail||'')}</div></div>`).join('');
    toast('Restore preflight complete.');
}
async function runSingleFileRestore(){
    let path=q('restoreActionPath').value||q('restoreActionSelect').value||'';
    let confirm=q('restoreActionConfirm').value||'';
    if(!path){
        q('restoreActionStatus').textContent='Select a staging package first.';
        return;
    }
    if(!lastRestorePreflight || (lastRestorePreflight.summary||{}).stage_dir!==path){
        q('restoreActionStatus').textContent='Run restore preflight for this package first.';
        return;
    }
    if(confirm!==lastRestorePreflight.future_restore_phrase){
        q('restoreActionStatus').textContent='Exact confirmation phrase does not match the preflight phrase.';
        return;
    }
    let msg='This will overwrite the original target with the staged file after creating a live-target backup. Continue?';
    if(!window.confirm(msg)){
        q('restoreActionStatus').textContent='Restore cancelled.';
        return;
    }
    if(!window.confirm('Final confirmation: this is the first real single-file restore action. Proceed?')){
        q('restoreActionStatus').textContent='Restore cancelled at final confirmation.';
        return;
    }
    q('restoreActionStatus').textContent='Running single-file restore...';
    let d=await api('/api/backups/single_file_restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({stage_dir:path,confirm})});
    lastRestoreAction=d;
    q('restoreActionResult').textContent=JSON.stringify(d,null,2);
    let v=d?.verification||{};
    q('restoreActionChecks').innerHTML=(v.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id)}</b>${finalBadge(c.ok?'pass':'block')}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.path||'')}</div></div>`).join('')||'No verification checks.';
    if(d?.ok){
        q('restoreActionStatus').textContent=`Single-file restore complete and verified.
Target: ${d.target}
Pre-restore live backup: ${d.pre_restore_live_backup}
Report: ${d.exported?.markdown||''}
Repair log: ${d.repair_action_log?.markdown||''}`;
        toast('Single-file restore complete and verified.');
    }else{
        q('restoreActionStatus').textContent=d?.message||'Restore failed or was blocked.';
        toast('Restore failed or blocked.');
    }
}
function sendRestoreActionToMission(){
    if(!lastRestoreAction){
        toast('Run a restore action first.');
        return;
    }
    go('mission');
    let v=lastRestoreAction.verification||{};
    let h=lastRestoreAction.hashes||{};
    q('input').value=`Please review this Kayock Single-File Restore Action result.

This was the first narrow restore action.

Result:
OK: ${lastRestoreAction.ok}
Message: ${lastRestoreAction.message}
Target: ${lastRestoreAction.target}
Staged copy: ${lastRestoreAction.staged_copy}
Source backup: ${lastRestoreAction.source_backup}
Pre-restore live backup: ${lastRestoreAction.pre_restore_live_backup}
Confirmation phrase: ${lastRestoreAction.confirmation_phrase}

Hashes:
Target before: ${h.target_before}
Live backup: ${h.live_backup}
Staged copy: ${h.staged_copy}
Source backup: ${h.source_backup}
Target after: ${h.target_after}

Verification:
${v.message||''}
${(v.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message} ${c.path||''}`).join('\n')}

Reports:
Restore report: ${lastRestoreAction.exported?.markdown||''}
RepairActions log: ${lastRestoreAction.repair_action_log?.markdown||''}

Safety:
Single file only.
From staging package only.
Original target only.
Pre-restore live backup required.
Exact confirmation phrase required.
No folder restore.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the restore was successful
2. Whether the live backup makes rollback safe
3. Whether the post-restore hash verification is sufficient
4. Whether the restore action should stay limited to generated files
5. Whether to build a post-restore audit viewer next.`;
    toast('Restore action result sent to Mission Console.');
}

let lastRestoreFinal=null;
async function loadRestoreFinalList(){
    q('restoreFinalStatus').textContent='Loading staging package list...';
    let d=await api('/api/backups/staging_packages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});
    if(!d?.ok){
        q('restoreFinalStatus').textContent=d?.message||'Could not load staging packages.';
        return;
    }
    let sel=q('restoreFinalSelect');
    sel.innerHTML=(d.packages||[]).map(p=>`<option value="${esc(p.stage_dir)}">${esc(p.name)} → ${esc(p.future_target||'unknown target')}</option>`).join('');
    if((d.packages||[]).length){
        q('restoreFinalPath').value=d.packages[0].stage_dir;
    }
    q('restoreFinalStatus').textContent=`Loaded ${d.packages?.length||0} staging package(s). Select one and run final checklist.`;
}
function finalBadge(status){
    status=(status||'block').toLowerCase();
    return `<span class="finalbadge ${status}">${esc(status.toUpperCase())}</span>`;
}
async function runRestoreFinal(doExport=false){
    let path=q('restoreFinalPath').value||q('restoreFinalSelect').value||'';
    if(!path){
        q('restoreFinalStatus').textContent='Select a staging package first.';
        return;
    }
    q('restoreFinalStatus').textContent='Running final restore checklist...';
    let d=await api('/api/backups/restore_final_check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({stage_dir:path,export:doExport})});
    if(!d?.ok){
        q('restoreFinalStatus').textContent=d?.message||'Final checklist failed.';
        return;
    }
    lastRestoreFinal=d;
    let s=d.summary||{};
    q('restoreFinalStatus').textContent=`Final checklist complete.
Final status: ${s.final_status}
Checks: ${s.checks}
Passed: ${s.pass}
Warnings: ${s.warn}
Blocks: ${s.block}
Hard blocks excluding restore lock: ${s.hard_blocks}
Restore allowed now: ${s.restore_allowed_now}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('restoreFinalDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Final Status</div><div class=value>${esc((s.final_status||'').replaceAll('_',' '))}</div></div>
        <div class=vaultmetric><div class=label>Passed</div><div class=value>${s.pass||0}</div></div>
        <div class=vaultmetric><div class=label>Warnings</div><div class=value>${s.warn||0}</div></div>
        <div class=vaultmetric><div class=label>Blocks</div><div class=value>${s.block||0}</div></div>
        <div class=vaultmetric><div class=label>Hard Blocks</div><div class=value>${s.hard_blocks||0}</div></div>
        <div class=vaultmetric><div class=label>Restore Allowed</div><div class=value>${s.restore_allowed_now?'YES':'NO'}</div></div>
        <div class=vaultmetric><div class=label>Risk</div><div class=value>${esc(s.preview_risk||'')}</div></div>
        <div class=vaultmetric><div class=label>Target Unchanged</div><div class=value>${s.target_unchanged_since_staging?'YES':'NO'}</div></div>
    </div><div class=status>Restore remains intentionally unavailable. This is final checklist only.</div>`;
    q('restoreFinalChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.status==='pass'?'ok':(c.status==='block'?'fail':'info')}"><b>${esc(c.id)}</b>${finalBadge(c.status)}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.detail||'')}</div></div>`).join('')||'No checks.';
    q('restoreFinalPhrase').innerHTML=`<div class=finalphrase>${esc(d.final_confirmation_phrase||'')}</div><div class=small>This phrase does not unlock restore in this build. Actual restore is still unavailable.</div>`;
    toast('Final checklist complete.');
}
function sendRestoreFinalToMission(){
    if(!lastRestoreFinal){
        toast('Run final checklist first.');
        return;
    }
    let s=lastRestoreFinal.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Restore Final Checklist.

No restore action is requested or possible in this build.

Summary:
Final status: ${s.final_status}
Checks: ${s.checks}
Passed: ${s.pass}
Warnings: ${s.warn}
Blocks: ${s.block}
Hard blocks excluding intentional restore lock: ${s.hard_blocks}
Restore allowed now: ${s.restore_allowed_now}
Stage package: ${s.stage_package}
Stage folder: ${s.stage_dir}
Staged copy: ${s.staged_copy}
Source backup: ${s.source_backup}
Future target: ${s.future_target}
Preview risk: ${s.preview_risk}
Candidate status: ${s.candidate_status}
Target unchanged since staging: ${s.target_unchanged_since_staging}
Read errors: ${s.read_errors}

Final confirmation phrase:
${lastRestoreFinal.final_confirmation_phrase}

Checks:
${(lastRestoreFinal.checks||[]).map(c=>`${c.status.toUpperCase()} — ${c.id}: ${c.message} ${c.detail||''}`).join('\n')}

Hashes:
Source backup: ${(lastRestoreFinal.hashes||{}).source_backup_sha256}
Staged copy: ${(lastRestoreFinal.hashes||{}).staged_copy_sha256}
Target after staging: ${(lastRestoreFinal.hashes||{}).target_sha256_after_staging}
Target now: ${(lastRestoreFinal.hashes||{}).target_sha256_now}

Exported Report:
${lastRestoreFinal.exported?.markdown||'No exported final checklist path'}

Safety:
Final check only.
No restore button.
No restore endpoint.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please decide:
1. Whether the final proof wall is sufficient
2. Whether any warning should block future restore
3. Whether the final confirmation phrase is strong enough
4. Whether restore should remain blocked
5. Whether the next version should still be preview-only or can safely introduce an actual restore action.`;
    toast('Final checklist sent to Mission Console.');
}

let lastStagingPackages=null;
function packageBadge(ok){
    return ok?'<span class="packagebadge ok">PACKAGE OK</span>':'<span class="packagebadge problem">CHECK PACKAGE</span>';
}
async function loadStagingPackages(doExport=false){
    let query=q('stagingPackageFilter').value||'';
    let limit=parseInt(q('stagingPackageLimit').value||'500');
    q('stagingPackageStatus').textContent='Loading staging packages...';
    let d=await api('/api/backups/staging_packages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,limit,export:doExport})});
    if(!d?.ok){
        q('stagingPackageStatus').textContent=d?.message||'Could not load staging packages.';
        return;
    }
    lastStagingPackages=d;
    let s=d.summary||{};
    q('stagingPackageStatus').textContent=`Staging packages loaded.
Packages: ${s.packages||0}
OK: ${s.ok||0}
Problems: ${s.problems||0}
Verified: ${s.verified||0}
Live target untouched: ${s.live_target_untouched||0}
Restore allowed now: ${s.restore_allowed_now||0}
Files: ${s.files||0}
Total size: ${fmtBytes(s.bytes||0)}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('stagingPackageDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Packages</div><div class=value>${s.packages||0}</div></div>
        <div class=vaultmetric><div class=label>OK</div><div class=value>${s.ok||0}</div></div>
        <div class=vaultmetric><div class=label>Problems</div><div class=value>${s.problems||0}</div></div>
        <div class=vaultmetric><div class=label>Verified</div><div class=value>${s.verified||0}</div></div>
        <div class=vaultmetric><div class=label>Untouched</div><div class=value>${s.live_target_untouched||0}</div></div>
        <div class=vaultmetric><div class=label>Restore Allowed</div><div class=value>${s.restore_allowed_now||0}</div></div>
        <div class=vaultmetric><div class=label>Files</div><div class=value>${s.files||0}</div></div>
        <div class=vaultmetric><div class=label>Total Size</div><div class=value>${fmtBytes(s.bytes||0)}</div></div>
    </div><div class=status>Latest package: ${esc(s.latest_package||'none')} | ${esc(s.latest_created||'')}</div>`;
    q('stagingPackageStatusList').innerHTML=(d.by_status||[]).map(x=>`<div class="histrow info"><b>${esc(x.status)}</b><div>Count: ${x.count} | Size: ${fmtBytes(x.bytes)}</div></div>`).join('')||'No status summary.';
    q('stagingPackageRiskList').innerHTML=(d.by_risk||[]).map(x=>`<div class="histrow info"><b>${esc(x.risk)}</b><div>Count: ${x.count} | Size: ${fmtBytes(x.bytes)}</div></div>`).join('')||'No risk summary.';
    q('stagingPackageList').innerHTML=(d.packages||[]).map(p=>`<div class="histrow ${p.ok?'ok':'fail'}"><b>${esc(p.name)}</b>${packageBadge(p.ok)}
<div>Created: ${esc(p.created||'')} | Risk: ${esc(p.preview_risk||'')} | Candidate: ${esc(p.candidate_status||'')}</div>
<div>Verification: ${p.verification_ok} (${p.verification_passed}/${p.verification_checked}) | Live target untouched: ${p.live_target_untouched}</div>
<div>Restore allowed now: ${p.restore_allowed_now}</div>
<div class=vaultpath>Stage folder: ${esc(p.stage_dir||'')}</div>
<div class=vaultpath>Staged copy: ${esc(p.staged_copy||'')}</div>
<div class=vaultpath>Source backup: ${esc(p.source_backup||'')}</div>
<div class=vaultpath>Future target: ${esc(p.future_target||'')}</div>
<div class=small>Future phrase: ${esc(p.future_confirmation_phrase||'')}</div>
<div class=vaultpath>Metadata: ${esc(p.metadata||'')}</div>
<div class=vaultpath>Report: ${esc(p.markdown||'')}</div>
<div class=vaultpath>Repair log: ${esc(p.repair_action_log_markdown||p.repair_action_log_json||'')}</div>
<div class=small>Missing required: ${(p.missing_required||[]).map(esc).join(', ')||'none'}</div>
<details><summary>Included files (${p.file_count||0})</summary>${(p.files||[]).map(f=>`<div class=packagefile>${esc(f.name)} — ${fmtBytes(f.size)} — ${esc(f.path)}</div>`).join('')}</details>
</div>`).join('')||'No staging packages found.';
    toast('Staging packages loaded.');
}
function sendStagingPackagesToMission(){
    if(!lastStagingPackages){
        toast('Load staging packages first.');
        return;
    }
    let s=lastStagingPackages.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Staging Package Inventory.

This is a read-only audit review. No restore action is requested.

Summary:
Packages: ${s.packages}
OK: ${s.ok}
Problems: ${s.problems}
Verified: ${s.verified}
Live target untouched: ${s.live_target_untouched}
Restore allowed now: ${s.restore_allowed_now}
Files: ${s.files}
Total size: ${fmtBytes(s.bytes)}
Scan errors: ${s.scan_errors}
Latest package: ${s.latest_package}
Latest created: ${s.latest_created}

Exported Inventory:
${lastStagingPackages.exported?.markdown||'No exported inventory path'}

Packages:
${(lastStagingPackages.packages||[]).map(p=>`${p.ok?'OK':'PROBLEM'} — ${p.name}
Stage folder: ${p.stage_dir}
Staged copy: ${p.staged_copy}
Source backup: ${p.source_backup}
Future target: ${p.future_target}
Verification OK: ${p.verification_ok}
Verification message: ${p.verification_message}
Live target untouched: ${p.live_target_untouched}
Restore allowed now: ${p.restore_allowed_now}
Candidate status: ${p.candidate_status}
Risk: ${p.preview_risk}
Future phrase: ${p.future_confirmation_phrase}
Missing required: ${(p.missing_required||[]).join(', ')||'none'}
Repair log: ${p.repair_action_log_markdown||p.repair_action_log_json||''}`).join('\n\n')}

Safety:
Read-only viewer.
No restore.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether staging package audit visibility is sufficient
2. Whether any package looks incomplete
3. Whether live-target-untouched proof is visible enough
4. What final metadata is needed before actual restore
5. Whether restore should remain blocked for now.`;
    toast('Staging inventory sent to Mission Console.');
}

let lastRestoreStaging=null;
async function loadRestoreStagingList(){
    q('restoreStagingStatus').textContent='Loading Backup Vault list...';
    let d=await api('/api/backups/vault',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});
    if(!d?.ok){
        q('restoreStagingStatus').textContent=d?.message||'Could not load backup list.';
        return;
    }
    let sel=q('restoreStagingSelect');
    sel.innerHTML=(d.backups||[]).map(b=>`<option value="${esc(b.path)}">${esc(b.name)} → ${esc(b.original_target||'unknown target')}</option>`).join('');
    if((d.backups||[]).length){
        q('restoreStagingPath').value=d.backups[0].path;
    }
    q('restoreStagingStatus').textContent=`Loaded ${d.backups?.length||0} backup(s). Type STAGE before staging.`;
}
async function stageRestoreCopy(){
    let path=q('restoreStagingPath').value||q('restoreStagingSelect').value||'';
    let confirm=q('restoreStagingConfirm').value||'';
    if(!path){
        q('restoreStagingStatus').textContent='Select or paste a backup path first.';
        return;
    }
    if(confirm.trim().toUpperCase()!=='STAGE'){
        q('restoreStagingStatus').textContent='Type STAGE to confirm staging-only copy.';
        return;
    }
    if(!window.confirm('Create a staging copy only? This will NOT restore or overwrite the live target.')){
        q('restoreStagingStatus').textContent='Staging cancelled.';
        return;
    }
    q('restoreStagingStatus').textContent='Creating staging copy...';
    let d=await api('/api/backups/restore_staging',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({backup_path:path,confirm})});
    lastRestoreStaging=d;
    if(!d?.ok){
        q('restoreStagingStatus').textContent=d?.message||'Staging copy failed or was blocked.';
    }else{
        q('restoreStagingStatus').textContent=`Staging copy complete.
Stage folder: ${d.stage_dir}
Staged copy: ${d.staged_copy}
Metadata: ${d.metadata}
Markdown: ${d.markdown}
Restore allowed now: ${d.restore_allowed_now}`;
    }
    q('restoreStagingResult').textContent=JSON.stringify(d,null,2);
    let v=d?.verification||{};
    q('restoreStagingChecks').innerHTML=(v.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id)}</b>${gateBadge(c.ok?'pass':'block')}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.path||'')}</div></div>`).join('')||'No verification checks.';
    toast(d?.ok?'Restore staging copy complete.':'Restore staging blocked or failed.');
}
function sendRestoreStagingToMission(){
    if(!lastRestoreStaging){
        toast('Run staging copy first.');
        return;
    }
    go('mission');
    let v=lastRestoreStaging.verification||{};
    q('input').value=`Please review this Kayock Restore Staging Copy result.

No restore action was performed. This is staging only.

Summary:
OK: ${lastRestoreStaging.ok}
Message: ${lastRestoreStaging.message}
Stage folder: ${lastRestoreStaging.stage_dir}
Staged copy: ${lastRestoreStaging.staged_copy}
Metadata: ${lastRestoreStaging.metadata}
Markdown report: ${lastRestoreStaging.markdown}
Readiness JSON: ${lastRestoreStaging.readiness}
Preview JSON: ${lastRestoreStaging.preview}
Restore allowed now: ${lastRestoreStaging.restore_allowed_now}

Verification:
${v.message||''}
${(v.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message} ${c.path||''}`).join('\n')}

Safety:
No restore to original location.
No live target overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the staging package is trustworthy
2. Whether the live target remained untouched
3. Whether the staged copy hash/size proof is enough
4. Whether a future restore feature still needs another gate
5. Whether restore should remain blocked for now.`;
    toast('Restore staging result sent to Mission Console.');
}

let lastRestoreGate=null;
async function loadRestoreGateList(){
    q('restoreGateStatus').textContent='Loading Backup Vault list...';
    let d=await api('/api/backups/vault',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});
    if(!d?.ok){
        q('restoreGateStatus').textContent=d?.message||'Could not load backup list.';
        return;
    }
    let sel=q('restoreGateSelect');
    sel.innerHTML=(d.backups||[]).map(b=>`<option value="${esc(b.path)}">${esc(b.name)} → ${esc(b.original_target||'unknown target')}</option>`).join('');
    if((d.backups||[]).length){
        q('restoreGatePath').value=d.backups[0].path;
    }
    q('restoreGateStatus').textContent=`Loaded ${d.backups?.length||0} backup(s). Select one and run the gate.`;
}
function gateBadge(status){
    status=(status||'info').toLowerCase();
    return `<span class="gatebadge ${status}">${esc(status.toUpperCase())}</span>`;
}
async function runRestoreGate(doExport=false){
    let path=q('restoreGatePath').value||q('restoreGateSelect').value||'';
    if(!path){
        q('restoreGateStatus').textContent='Select or paste a backup path first.';
        return;
    }
    q('restoreGateStatus').textContent='Running restore readiness gate...';
    let d=await api('/api/backups/restore_readiness',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({backup_path:path,export:doExport})});
    if(!d?.ok){
        q('restoreGateStatus').textContent=d?.message||'Restore readiness gate failed.';
        return;
    }
    lastRestoreGate=d;
    let s=d.summary||{};
    q('restoreGateStatus').textContent=`Restore readiness gate complete.
Candidate status: ${s.candidate_status}
Gates: ${s.gates}
Passed: ${s.pass}
Warnings: ${s.warn}
Blocks: ${s.block}
Hard blocks excluding restore lock: ${s.hard_blocks}
Restore allowed now: ${s.restore_allowed_now}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('restoreGateDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Candidate</div><div class=value>${esc((s.candidate_status||'').replaceAll('_',' '))}</div></div>
        <div class=vaultmetric><div class=label>Passed</div><div class=value>${s.pass||0}</div></div>
        <div class=vaultmetric><div class=label>Warnings</div><div class=value>${s.warn||0}</div></div>
        <div class=vaultmetric><div class=label>Blocks</div><div class=value>${s.block||0}</div></div>
        <div class=vaultmetric><div class=label>Hard Blocks</div><div class=value>${s.hard_blocks||0}</div></div>
        <div class=vaultmetric><div class=label>Risk</div><div class=value>${esc(s.preview_risk||'')}</div></div>
        <div class=vaultmetric><div class=label>Target Exists</div><div class=value>${s.target_exists?'YES':'NO'}</div></div>
        <div class=vaultmetric><div class=label>Same Hash</div><div class=value>${s.same_hash?'YES':'NO'}</div></div>
    </div><div class=status>Restore remains intentionally blocked in this build. This gate is advisory only.</div>`;
    q('restoreGateChecks').innerHTML=(d.gates||[]).map(g=>`<div class="histrow ${g.status==='pass'?'ok':(g.status==='block'?'fail':'info')}"><b>${esc(g.id)}</b>${gateBadge(g.status)}<div>${esc(g.message||'')}</div><div class=vaultpath>${esc(g.detail||'')}</div></div>`).join('')||'No gate checks.';
    q('restoreGatePhrase').innerHTML=`<div class=phrasebox>${esc(d.future_confirmation_phrase||'')}</div><div class=small>This phrase is for a possible future restore build only. It does not unlock restore in this build.</div>`;
    toast('Restore readiness gate complete.');
}
function sendRestoreGateToMission(){
    if(!lastRestoreGate){
        toast('Run the restore gate first.');
        return;
    }
    let s=lastRestoreGate.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Restore Readiness Gate report.

No restore action is requested. Restore remains intentionally blocked.

Summary:
Candidate status: ${s.candidate_status}
Gates: ${s.gates}
Passed: ${s.pass}
Warnings: ${s.warn}
Blocks: ${s.block}
Hard blocks excluding intentional restore lock: ${s.hard_blocks}
Restore allowed now: ${s.restore_allowed_now}
Backup: ${s.backup}
Target: ${s.target}
Preview risk: ${s.preview_risk}
Same hash: ${s.same_hash}
Target exists: ${s.target_exists}
Target inside FOXAI root: ${s.target_inside_root}

Future confirmation phrase:
${lastRestoreGate.future_confirmation_phrase}

Gate Checks:
${(lastRestoreGate.gates||[]).map(g=>`${g.status.toUpperCase()} — ${g.id}: ${g.message} ${g.detail||''}`).join('\n')}

Exported Report:
${lastRestoreGate.exported?.markdown||'No exported readiness report path'}

Please decide:
1. Whether this backup is a valid future restore candidate
2. Whether any warning should become a hard block
3. Whether the future confirmation phrase is strong enough
4. Whether restore should remain blocked
5. What metadata is still missing before actual restore power.`;
    toast('Restore gate report sent to Mission Console.');
}

let lastRestorePreview=null;
async function loadRestoreBackupList(){
    q('restorePreviewStatus').textContent='Loading Backup Vault list...';
    let d=await api('/api/backups/vault',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});
    if(!d?.ok){
        q('restorePreviewStatus').textContent=d?.message||'Could not load backup list.';
        return;
    }
    let sel=q('restoreBackupSelect');
    sel.innerHTML=(d.backups||[]).map(b=>`<option value="${esc(b.path)}">${esc(b.name)} → ${esc(b.original_target||'unknown target')}</option>`).join('');
    if((d.backups||[]).length){
        q('restoreBackupPath').value=d.backups[0].path;
    }
    q('restorePreviewStatus').textContent=`Loaded ${d.backups?.length||0} backup(s). Select one and preview.`;
}
function restoreRiskBadge(r){
    r=(r||'low').toLowerCase();
    return `<span class="riskbadge ${r}">${esc(r.toUpperCase())}</span>`;
}
async function previewRestore(doExport=false){
    let path=q('restoreBackupPath').value||q('restoreBackupSelect').value||'';
    if(!path){
        q('restorePreviewStatus').textContent='Select or paste a backup path first.';
        return;
    }
    q('restorePreviewStatus').textContent='Generating restore preview...';
    let d=await api('/api/backups/restore_preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({backup_path:path,export:doExport})});
    if(!d?.ok){
        q('restorePreviewStatus').textContent=d?.message||'Restore preview failed.';
        return;
    }
    lastRestorePreview=d;
    let s=d.summary||{};
    q('restorePreviewStatus').textContent=`Restore preview generated.
Risk: ${s.risk}
Backup: ${s.backup}
Target: ${s.target||'unknown'}
Target exists: ${s.target_exists}
Same hash: ${s.same_hash}
Would overwrite: ${s.would_overwrite}
Would create: ${s.would_create}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('restorePreviewDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Risk</div><div class=value>${restoreRiskBadge(s.risk)}</div></div>
        <div class=vaultmetric><div class=label>Target Exists</div><div class=value>${s.target_exists?'YES':'NO'}</div></div>
        <div class=vaultmetric><div class=label>Same Hash</div><div class=value>${s.same_hash?'YES':'NO'}</div></div>
        <div class=vaultmetric><div class=label>Would Overwrite</div><div class=value>${s.would_overwrite?'YES':'NO'}</div></div>
        <div class=vaultmetric><div class=label>Backup Size</div><div class=value>${fmtBytes(s.backup_size)}</div></div>
        <div class=vaultmetric><div class=label>Target Size</div><div class=value>${fmtBytes(s.target_size)}</div></div>
        <div class=vaultmetric><div class=label>Problems</div><div class=value>${s.problems||0}</div></div>
        <div class=vaultmetric><div class=label>Warnings</div><div class=value>${s.warnings||0}</div></div>
    </div><div class=status>Safety: preview only. No restore operation exists in this build.</div>`;
    let b=d.backup||{}, t=d.target||{}, c=d.comparison||{};
    q('restorePreviewCompare').innerHTML=`<div class="histrow info"><b>Backup</b>
<div class=vaultpath>${esc(b.path||'')}</div>
<div>Type: ${esc(b.type||'')} | Size: ${fmtBytes(b.size)}</div>
<div class=small>SHA256: ${esc(b.sha256||'')}</div>
<div class=small>File-modified time: ${esc(b.file_modified_time||'')}</div>
<div class=small>Created by action: ${esc(b.created_by_action||'')}</div>
<div class=small>Action-created time: ${esc(b.action_created||'')}</div>
<div class=vaultpath>Repair log: ${esc(b.repair_log||'')}</div></div>
<div class="histrow ${t.exists?'ok':'fail'}"><b>Current Target</b>
<div class=vaultpath>${esc(t.path||'unknown')}</div>
<div>Exists: ${t.exists} | Inside FOXAI root: ${t.inside_root}</div>
<div>Size: ${fmtBytes(t.size)}</div>
<div class=small>SHA256: ${esc(t.sha256||'')}</div>
<div class=small>File-modified time: ${esc(t.file_modified_time||'')}</div></div>
<div class="histrow info"><b>Comparison</b>
<div>Same hash: ${c.same_hash}</div>
<div>Size delta if restored: ${fmtBytes(c.size_delta_if_restored)}</div>
<div>Text preview available: ${c.text_preview_available}</div>
<div>Diff truncated: ${c.diff_truncated}</div>
<div class=small>${esc(c.readable_reason||'')}</div></div>
${(d.problems||[]).length?`<div class="histrow fail"><b>Problems</b>${d.problems.map(p=>`<div>❌ ${esc(p)}</div>`).join('')}</div>`:''}
${(d.warnings||[]).length?`<div class="histrow info"><b>Warnings</b>${d.warnings.map(w=>`<div>⚠️ ${esc(w)}</div>`).join('')}</div>`:''}`;
    q('restorePreviewDiff').textContent=(c.diff_preview||'No diff preview available.');
    toast('Restore preview generated.');
}
function sendRestorePreviewToMission(){
    if(!lastRestorePreview){
        toast('Generate a restore preview first.');
        return;
    }
    let s=lastRestorePreview.summary||{}, b=lastRestorePreview.backup||{}, t=lastRestorePreview.target||{}, c=lastRestorePreview.comparison||{};
    go('mission');
    q('input').value=`Please review this Kayock Restore Preview Plan.

No restore action is requested. This is preview-only.

Safety:
No restore button exists.
No overwrite was performed.
No copy-back was performed.
No delete was performed.
No install was performed.
No model cleanup was performed.

Summary:
Risk: ${s.risk}
Backup: ${s.backup}
Target: ${s.target}
Target exists: ${s.target_exists}
Target inside FOXAI root: ${s.target_inside_root}
Same hash: ${s.same_hash}
Would overwrite: ${s.would_overwrite}
Would create: ${s.would_create}
Backup size: ${fmtBytes(s.backup_size)}
Target size: ${fmtBytes(s.target_size)}

Backup:
Name: ${b.name}
Type: ${b.type}
SHA256: ${b.sha256}
Created by action: ${b.created_by_action}
Action-created time: ${b.action_created}
Verified state: ${b.verified_state}
Repair log: ${b.repair_log}

Target:
Path: ${t.path}
Exists: ${t.exists}
SHA256: ${t.sha256}
File-modified time: ${t.file_modified_time}

Problems:
${(lastRestorePreview.problems||[]).join('\n')||'none'}

Warnings:
${(lastRestorePreview.warnings||[]).join('\n')||'none'}

Exported Preview:
${lastRestorePreview.exported?.markdown||'No exported preview path'}

Please determine:
1. Whether this backup is a valid restore candidate
2. Whether the risk level is appropriate
3. Whether the diff/hash metadata is enough
4. What confirmation phrase should be required in a future restore build
5. Whether an actual restore action should remain blocked for now.`;
    toast('Restore preview sent to Mission Console.');
}

let lastBackupVault=null;
function fmtBytes(n){
    n=Number(n||0);
    if(n<1024)return n+' B';
    if(n<1024*1024)return (n/1024).toFixed(1)+' KB';
    if(n<1024*1024*1024)return (n/1024/1024).toFixed(1)+' MB';
    return (n/1024/1024/1024).toFixed(2)+' GB';
}
function assocBadge(b){
    return b.associated?'<span class="backupbadge assoc">ACTION LINKED</span>':'<span class="backupbadge old">OLDER/UNLINKED</span>';
}
async function loadBackupVault(doExport=false){
    let query=q('backupVaultFilter').value||'';
    let limit=parseInt(q('backupVaultLimit').value||'500');
    q('backupVaultStatus').textContent='Loading backup vault...';
    let d=await api('/api/backups/vault',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,limit,export:doExport})});
    if(!d?.ok){
        q('backupVaultStatus').textContent=d?.message||'Could not load backup vault.';
        return;
    }
    lastBackupVault=d;
    let s=d.summary||{};
    q('backupVaultStatus').textContent=`Backup vault loaded.
Backups: ${s.backups||0}
Associated with repair actions: ${s.associated||0}
Older/unassociated: ${s.unassociated||0}
Verified action backups: ${s.verified||0}
Total size: ${fmtBytes(s.bytes||0)}
Latest: ${s.latest_backup||'none'}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('backupVaultDashboard').innerHTML=`<div class=historygrid>
        <div class=vaultmetric><div class=label>Backups</div><div class=value>${s.backups||0}</div></div>
        <div class=vaultmetric><div class=label>Total Size</div><div class=value>${fmtBytes(s.bytes||0)}</div></div>
        <div class=vaultmetric><div class=label>Linked</div><div class=value>${s.associated||0}</div></div>
        <div class=vaultmetric><div class=label>Older</div><div class=value>${s.unassociated||0}</div></div>
        <div class=vaultmetric><div class=label>Verified</div><div class=value>${s.verified||0}</div></div>
        <div class=vaultmetric><div class=label>Types</div><div class=value>${s.types||0}</div></div>
        <div class=vaultmetric><div class=label>Actions</div><div class=value>${s.actions||0}</div></div>
        <div class=vaultmetric><div class=label>Errors</div><div class=value>${(s.scan_errors||0)+(s.log_errors||0)}</div></div>
    </div><div class=status>Latest backup: ${esc(s.latest_backup||'none')}<br>File-modified time: ${esc(s.latest_file_modified_time||s.latest_modified||'')}<br>Filename timestamp: ${esc(s.latest_backup_filename_time||'')}<br>Action-created time: ${esc(s.latest_action_created||'')}<br>${esc(s.timestamp_note||'File modified time may not equal backup creation time.')}</div>`;
    q('backupVaultTypes').innerHTML=(d.by_type||[]).map(t=>`<div class="histrow info"><b>${esc(t.type)}</b><div>Count: ${t.count} | Size: ${fmtBytes(t.bytes)}</div></div>`).join('')||'No type summary.';
    q('backupVaultActions').innerHTML=(d.by_action||[]).map(a=>`<div class="histrow info"><b>${esc(a.action_id)}</b><div>Count: ${a.count} | Size: ${fmtBytes(a.bytes)}</div><div>Verified: ${a.verified||0} | Older/unverified: ${a.unverified||0}</div></div>`).join('')||'No action summary.';
    q('backupVaultFiles').innerHTML=(d.backups||[]).map(b=>`<div class="histrow ${b.associated?'ok':'info'}"><b>${esc(b.name)}</b>${assocBadge(b)}
<div>Type: ${esc(b.type)} | Size: ${fmtBytes(b.size)}</div><div class=small>File-modified time: ${esc(b.file_modified_time||b.modified||'')}</div><div class=small>Filename timestamp: ${esc(b.backup_filename_time||'')}</div><div class=small>Action-created time: ${esc(b.action_created||'')}</div><div class=small>${esc(b.timestamp_note||'')}</div>
<div class=vaultpath>Backup: ${esc(b.path||'')}</div>
<div class=vaultpath>Original target: ${esc(b.original_target||'unknown')}</div>
<div class=small>Created by: ${esc(b.action_id||'unknown/older backup')} | Verified state: ${esc(b.verified_state||'')}</div>
<div class=vaultpath>Repair log: ${esc(b.log_markdown||b.log_json||'')}</div></div>`).join('')||'No backup files found.';
    toast('Backup vault loaded.');
}
function sendBackupVaultToMission(){
    if(!lastBackupVault){
        toast('Load backup vault first.');
        return;
    }
    let s=lastBackupVault.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Backup Vault inventory.

This is a read-only rollback visibility review. No restore action is requested.

Summary:
Backups: ${s.backups}
Total size: ${fmtBytes(s.bytes)}
Associated with repair actions: ${s.associated}
Older/unassociated backups: ${s.unassociated}
Verified action backups: ${s.verified}
Backup types: ${s.types}
Repair action types: ${s.actions}
Scan errors: ${s.scan_errors}
Log errors: ${s.log_errors}
Latest backup: ${s.latest_backup}
Latest file-modified time: ${s.latest_file_modified_time||s.latest_modified}\nLatest filename timestamp: ${s.latest_backup_filename_time||''}\nLatest action-created time: ${s.latest_action_created||''}\nTimestamp note: ${s.timestamp_note||'File modified time may not equal backup creation time.'}

Exported Inventory:
${lastBackupVault.exported?.markdown||'No exported inventory path'}

By Type:
${(lastBackupVault.by_type||[]).map(t=>`${t.type}: count=${t.count}, size=${fmtBytes(t.bytes)}`).join('\n')}

By Repair Action:
${(lastBackupVault.by_action||[]).map(a=>`${a.action_id}: count=${a.count}, size=${fmtBytes(a.bytes)}, verified=${a.verified||0}, unverified=${a.unverified||0}`).join('\n')}

Recent Backups:
${(lastBackupVault.backups||[]).slice(0,25).map(b=>`${b.name}
Type: ${b.type}
Size: ${fmtBytes(b.size)}
File-modified time: ${b.file_modified_time||b.modified}\nFilename timestamp: ${b.backup_filename_time||''}\nAction-created time: ${b.action_created||''}
Original target: ${b.original_target||'unknown'}
Created by action: ${b.action_id||'unknown/older backup'}
Verified state: ${b.verified_state}
Backup path: ${b.path}
Repair log: ${b.log_markdown||b.log_json||''}`).join('\n\n')}

Please identify:
1. Whether rollback visibility is sufficient
2. Whether backups are being created in the right place
3. Whether any backup looks suspicious or unlinked
4. What metadata should be added before a restore feature exists
5. Whether it is safe to build a preview-only restore planner next.`;
    toast('Backup inventory sent to Mission Console.');
}


















let lastProjectGate=null;
async function loadProjectGate(doExport=false){
    if(!q('projectGateStatus'))return;
    q('projectGateStatus').textContent='Loading Create Project Approval Gate...';
    let phrase=q('projectGatePhrase')?.value||'';
    let d=await api('/api/writer/create_project_gate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:'slipping_into_darkness',approval_phrase:phrase,export:doExport})});
    if(!d?.ok){
        q('projectGateStatus').textContent=d?.message||'Could not load project gate.';
        return;
    }
    lastProjectGate=d;
    let s=d.summary||{};
    q('projectGateStatus').innerHTML=`<span class=gateBadge>${esc(d.health_label||'UNKNOWN')}</span>`;
    q('projectGateSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div>
    <div class=gateGrid>
      <div class=gateMetric><div class=label>Safe Later</div><div class=value>${s.safe_to_create_later?'YES':'NO'}</div></div>
      <div class=gateMetric><div class=label>Creates Now</div><div class=value>${s.creation_enabled_in_this_build?'YES':'NO'}</div></div>
      <div class=gateMetric><div class=label>Writes</div><div class=value>${s.proposed_writes||0}</div></div>
      <div class=gateMetric><div class=label>Overwrite Risks</div><div class=value>${s.overwrite_risks||0}</div></div>
      <div class=gateMetric><div class=label>Legacy Files</div><div class=value>${s.legacy_files_detected||0}</div></div>
      <div class=gateMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div>
    </div>
    <div class=gatePath>Project root: ${esc(s.proposed_project_root||'')}</div>
    <div class=gatePath>Manifest target: ${esc(s.manifest_target||'')}</div>
    ${d.exported?`<div class=gatePath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    let g=d.approval_gate||{};
    q('projectGateApproval').textContent=`Required phrase:
${g.required_phrase||''}

Typed phrase present: ${g.typed_phrase_present}
Typed phrase matches: ${g.typed_phrase_matches}
Creation enabled in this build: ${g.creation_enabled_in_this_build}

Reason:
${g.reason_creation_disabled||''}

Preview required: ${g.preview_required}
Backup required before write: ${g.backup_required_before_write}
Copy, not move, for legacy sources: ${g.copy_not_move_for_legacy_sources}
No delete allowed: ${g.no_delete_allowed}
No overwrite without backup: ${g.no_overwrite_without_backup}
No automatic migration: ${g.no_automatic_migration}`;
    q('projectGateWrites').innerHTML=(d.proposed_writes||[]).map(w=>`<div class="gateCard"><b>${esc(w.id||'write')}</b><div>${esc(w.action||'')} | Kind: ${esc(w.kind||'')}</div><div>Target exists: ${w.target_exists} | Would overwrite: ${w.would_overwrite} | Executes now: ${w.will_execute_in_this_build}</div><div class=gatePath>${esc(w.target||'')}</div>${w.source?`<div class=gatePath>Source: ${esc(w.source)}</div>`:''}</div>`).join('')||'No proposed writes.';
    q('projectGateRisks').innerHTML=(d.overwrite_risks||[]).length?(d.overwrite_risks||[]).map(r=>`<div class="histrow fail"><b>Overwrite risk</b><div class=gatePath>${esc(r.target||'')}</div></div>`).join(''):'<div class="histrow ok"><b>No overwrite risks detected.</b><div>Project creation may be safe in a later approved-action build.</div></div>';
    q('projectGateLegacy').innerHTML=(d.legacy_files||[]).map(f=>`<div class="histrow info"><b>${esc(f.name||'')}</b><div>${esc(f.suffix||'')} | ${f.size||0} bytes | ${esc(f.modified||'')}</div><div class=gatePath>${esc(f.path||'')}</div></div>`).join('')||'No legacy files detected.';
    q('projectGateChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('projectGateSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Create Project Approval Gate loaded.');
}
function sendProjectGateToMission(){
    if(!lastProjectGate){toast('Load Project Gate first.');return;}
    let d=lastProjectGate, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Create Project Approval Gate.

Milestone:
${d.milestone}
Health: ${d.health_label}
Gate ready: ${d.gate_ready}
Safe to create later: ${d.safe_to_create_later}

Summary:
Project: ${s.title}
Project ID: ${s.project_id}
Creation enabled in this build: ${s.creation_enabled_in_this_build}
Required phrase: ${s.required_phrase}
Typed phrase present: ${s.typed_phrase_present}
Typed phrase matches: ${s.typed_phrase_matches}
Legacy files detected: ${s.legacy_files_detected}
Proposed writes: ${s.proposed_writes}
Required writes: ${s.required_writes}
Optional copy writes: ${s.optional_copy_writes}
Overwrite risks: ${s.overwrite_risks}
Parent missing expected: ${s.parent_missing_expected}
Checks passed: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}
Proposed project root: ${s.proposed_project_root}
Manifest target: ${s.manifest_target}

Approval gate:
${JSON.stringify(d.approval_gate,null,2)}

Legacy import policy:
${JSON.stringify(d.legacy_import_policy,null,2)}

Proposed writes:
${(d.proposed_writes||[]).map(w=>`${w.id}: ${w.action}; target=${w.target}; exists=${w.target_exists}; overwrite=${w.would_overwrite}; executes_now=${w.will_execute_in_this_build}`).join('\n')}

Overwrite risks:
${(d.overwrite_risks||[]).length ? (d.overwrite_risks||[]).map(r=>r.target).join('\n') : 'None.'}

Checks:
${(d.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}

Export:
${d.exported?.markdown||'No exported gate report'}

Safety:
Gate preview only.
Read-only legacy scan.
No project creation.
No story-file mutation.
No legacy migration.
No rename performed.
No overwrite.
No delete.
No install.
No model cleanup.
Future writes require preview and approval.

Please determine:
1. Whether v10.11.3 should be marked stable/proven
2. Whether the next build should be Create Project Approved Action
3. Whether it is safe for the future action to create the folder skeleton only after exact phrase approval.`;
    toast('Project Gate sent to Mission Console.');
}

let lastStoryManifest=null;
async function loadStoryManifest(doExport=false){
    if(!q('storyManifestStatus'))return;
    q('storyManifestStatus').textContent='Loading Story Project Manifest Preview...';
    let d=await api('/api/writer/manifest_preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:'slipping_into_darkness',export:doExport})});
    if(!d?.ok){
        q('storyManifestStatus').textContent=d?.message||'Could not load manifest preview.';
        return;
    }
    lastStoryManifest=d;
    let s=d.summary||{};
    q('storyManifestStatus').innerHTML=`<span class=manifestBadge>${esc(d.health_label||'UNKNOWN')}</span>`;
    q('storyManifestSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div>
    <div class=manifestGrid>
      <div class=manifestMetric><div class=label>Legacy Files</div><div class=value>${s.legacy_files_detected||0}</div></div>
      <div class=manifestMetric><div class=label>Folders</div><div class=value>${s.proposed_folders||0}</div></div>
      <div class=manifestMetric><div class=label>Writes Enabled</div><div class=value>${s.future_writes_enabled_now||0}/${s.future_writes||0}</div></div>
      <div class=manifestMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div>
      <div class=manifestMetric><div class=label>Problems</div><div class=value>${s.problems||0}</div></div>
      <div class=manifestMetric><div class=label>Ready</div><div class=value>${s.preview_ready?'YES':'NO'}</div></div>
    </div>
    <div class=manifestPath>Project root: ${esc(s.proposed_project_root||'')}</div>
    <div class=manifestPath>Manifest target: ${esc(s.manifest_target||'')}</div>
    ${d.exported?`<div class=manifestPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    let mp=d.manifest_preview||{};
    q('storyManifestBody').innerHTML=`<pre>${esc(JSON.stringify(mp,null,2))}</pre>`;
    q('storyManifestLegacy').innerHTML=(d.legacy_candidates||[]).filter(f=>f.exists).map(f=>`<div class="manifestCard"><b>${esc(f.name||'')}</b><div>${esc(f.suffix||'')} | ${f.size||0} bytes | ${esc(f.modified||'')}</div><div class=manifestPath>${esc(f.path||'')}</div></div>`).join('')||'No legacy sources detected.';
    q('storyManifestFolders').innerHTML=(d.proposed_folders||[]).map(f=>`<div class="histrow info"><b>${esc(f.id||'folder')}</b><div class=manifestPath>${esc(f.path||'')}</div><div>${esc(f.purpose||'')}</div></div>`).join('')||'No proposed folders.';
    let gate=d.approval_gate||{};
    q('storyManifestWrites').innerHTML=`<div class="histrow info"><b>Approval Gate</b><div>Required phrase: ${esc(gate.required_phrase||'')}</div><div>Preview required: ${gate.preview_required} | Backup required: ${gate.backup_required_before_write} | No automatic migration: ${gate.no_automatic_migration}</div></div>`+(d.future_writes||[]).map(w=>`<div class="histrow info"><b>${esc(w.id||'write')}</b><div>Action: ${esc(w.action||'')} | Enabled now: ${w.enabled_now} | Requires approval: ${w.requires_user_approval}</div><div class=manifestPath>Target: ${esc(w.target||'')}</div></div>`).join('');
    q('storyManifestChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('storyManifestSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Story Project Manifest Preview loaded.');
}
function sendStoryManifestToMission(){
    if(!lastStoryManifest){toast('Load manifest preview first.');return;}
    let d=lastStoryManifest, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Story Project Manifest Preview.

Milestone:
${d.milestone}
Health: ${d.health_label}
Preview ready: ${d.preview_ready}

Summary:
Project: ${s.title}
Project ID: ${s.project_id}
Legacy files detected: ${s.legacy_files_detected}
Legacy JSON/Markdown/Text: ${s.legacy_json}/${s.legacy_markdown}/${s.legacy_text}
Proposed folders: ${s.proposed_folders}
Future writes enabled now: ${s.future_writes_enabled_now}/${s.future_writes}
Checks passed: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}
Proposed project root: ${s.proposed_project_root}
Manifest target: ${s.manifest_target}

Proposed manifest:
${JSON.stringify(d.manifest_preview,null,2)}

Legacy sources:
${(d.legacy_candidates||[]).filter(f=>f.exists).map(f=>`${f.suffix} — ${f.path} — ${f.size} bytes`).join('\n')}

Proposed folders:
${(d.proposed_folders||[]).map(f=>`${f.id}: ${f.path} — ${f.purpose}`).join('\n')}

Future writes:
${(d.future_writes||[]).map(w=>`${w.id}: enabled_now=${w.enabled_now}; action=${w.action}; target=${w.target}; approval=${w.requires_user_approval}`).join('\n')}

Approval gate:
${JSON.stringify(d.approval_gate,null,2)}

Checks:
${(d.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}

Export:
${d.exported?.markdown||'No exported manifest preview report'}

Safety:
Preview only.
Read-only legacy scan.
No project creation.
No story-file mutation.
No legacy migration.
No rename performed.
No overwrite.
No delete.
No install.
No model cleanup.
Future writes require preview and approval.

Please determine:
1. Whether v10.11.2 should be marked stable/proven
2. Whether the next build should be Create Project Approval Gate
3. Whether the proposed manifest/folder structure is safe.`;
    toast('Story manifest preview sent to Mission Console.');
}

let lastStoryForge=null;
async function loadStoryForge(doExport=false){
    if(!q('storyForgeStatus'))return;
    q('storyForgeStatus').textContent='Loading Story Forge shell...';
    let d=await api('/api/writer/story_forge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({export:doExport,limit:80})});
    if(!d?.ok){
        q('storyForgeStatus').textContent=d?.message||'Could not load Story Forge shell.';
        return;
    }
    lastStoryForge=d;
    let s=d.summary||{};
    q('storyForgeStatus').innerHTML=`<span class=storyBadge>${esc(d.health_label||'UNKNOWN')}</span>`;
    q('storyForgeSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div>
    <div class=storyGrid>
      <div class=storyMetric><div class=label>Sections</div><div class=value>${s.sections||0}</div></div>
      <div class=storyMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div>
      <div class=storyMetric><div class=label>Problems</div><div class=value>${s.problems||0}</div></div>
      <div class=storyMetric><div class=label>Project Roots</div><div class=value>${s.existing_project_roots||0}/${s.project_roots_checked||0}</div></div>
      <div class=storyMetric><div class=label>Future Actions</div><div class=value>${s.future_actions_available_now||0}/${s.future_actions||0}</div></div>
      <div class=storyMetric><div class=label>Ready</div><div class=value>${s.foundation_ready?'YES':'NO'}</div></div>
    </div>
    <div class=storyPath>Flagship universe: ${esc(s.flagship_universe||'')}</div>
    <div class=storyPath>Legacy NovelForge exists: ${s.legacy_novel_forge_exists}</div>
    ${d.exported?`<div class=storyPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    let f=d.flagship||{};
    q('storyForgeFlagship').textContent=`${f.title||''}
Status: ${f.status||''}

Book 1:
${f.book_1||''}

Book 2:
${f.book_2||''}

Story Forge use:
${(f.story_forge_use||[]).join('\\n')}`;
    q('storyForgeProjects').innerHTML=(d.project_candidates||[]).map(p=>`<div class="storyCard"><b>${esc(p.title||'')}</b><div>Role: ${esc(p.role||'')} | Exists: ${p.exists} | Kind: ${esc(p.kind||'')}</div><div class=storyPath>${esc(p.path||'')}</div><div>Files: ${p.counts?.total||0} | MD: ${p.counts?.markdown||0} | JSON: ${p.counts?.json||0} | TXT: ${p.counts?.text||0}</div>${(p.children||[]).length?`<div class=storyPath>Children: ${(p.children||[]).map(c=>esc(c.name)+' ('+(c.counts?.total||0)+' files)').join(', ')}</div>`:''}</div>`).join('')||'No project candidates.';
    q('storyForgeSections').innerHTML=(d.shell_sections||[]).map(x=>`<div class="histrow info"><b>${esc(x.title||'')}</b><div>ID: ${esc(x.id||'')} | Status: ${esc(x.status||'')}</div><div>${esc(x.purpose||'')}</div></div>`).join('')||'No sections.';
    q('storyForgeActions').innerHTML=(d.future_actions||[]).map(a=>`<div class="histrow info"><b>${esc(a.title||'')}</b><div>ID: ${esc(a.id||'')} | Available now: ${a.available_now} | Requires approval: ${a.requires_user_approval}</div><div class=storyPath>Writes: ${esc(a.writes||'')}</div></div>`).join('')||'No future actions.';
    q('storyForgeChecks').innerHTML=(d.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div></div>`).join('')||'No checks.';
    q('storyForgeSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Story Forge shell loaded.');
}
function sendStoryForgeToMission(){
    if(!lastStoryForge){toast('Load Story Forge first.');return;}
    let d=lastStoryForge, s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Writer Story Forge Shell report.

Milestone:
${d.milestone}
Health: ${d.health_label}
Shell ready: ${d.shell_ready}

Summary:
Sections: ${s.sections}
Checks passed: ${s.checks_passed}/${s.checks}
Problems: ${s.problems}
Project roots checked: ${s.project_roots_checked}
Existing project roots: ${s.existing_project_roots}
Legacy NovelForge exists: ${s.legacy_novel_forge_exists}
Future actions available now: ${s.future_actions_available_now}/${s.future_actions}
Flagship universe: ${s.flagship_universe}

Flagship:
${d.flagship?.title}
Book 1: ${d.flagship?.book_1}
Book 2: ${d.flagship?.book_2}

Project candidates:
${(d.project_candidates||[]).map(p=>`${p.id}: ${p.path} — exists=${p.exists} — files=${p.counts?.total||0}`).join('\n')}

Shell sections:
${(d.shell_sections||[]).map(x=>`${x.id}: ${x.status} — ${x.purpose}`).join('\n')}

Future actions:
${(d.future_actions||[]).map(a=>`${a.id}: available_now=${a.available_now}; requires approval=${a.requires_user_approval}; writes=${a.writes}`).join('\n')}

Checks:
${(d.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}

Export:
${d.exported?.markdown||'No exported Story Forge shell report'}

Safety:
Read-only Story Forge shell.
No story-file mutation.
No project creation.
No legacy migration.
No rename performed.
No overwrite.
No delete.
No install.
No model cleanup.
Future writes require preview and approval.

Please determine:
1. Whether v10.11.1 should be marked stable/proven
2. Whether Story Project Manifest Preview should be the next build
3. Whether legacy NovelForge should remain read-only until an approved migration tool exists.`;
    toast('Story Forge sent to Mission Console.');
}

let lastKayockWriter=null;
async function loadKayockWriter(doExport=false){
    if(!q('kayockWriterStatus'))return;
    q('kayockWriterStatus').textContent='Loading Kayock Writer foundation...';
    let d=await api('/api/writer/foundation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({export:doExport})});
    if(!d?.ok){q('kayockWriterStatus').textContent=d?.message||'Could not load Kayock Writer foundation.';return;}
    lastKayockWriter=d; let s=d.summary||{};
    q('kayockWriterStatus').innerHTML=`<span class=writerBadge>${esc(d.health_label||'UNKNOWN')}</span>`;
    q('kayockWriterSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b></div><div class=writerGrid><div class=writerMetric><div class=label>Modules</div><div class=value>${s.modules||0}</div></div><div class=writerMetric><div class=label>Checks</div><div class=value>${s.checks_passed||0}/${s.checks||0}</div></div><div class=writerMetric><div class=label>Problems</div><div class=value>${s.problems||0}</div></div><div class=writerMetric><div class=label>Paths</div><div class=value>${s.existing_paths||0}/${s.path_checks||0}</div></div><div class=writerMetric><div class=label>Decisions</div><div class=value>${s.naming_decisions||0}</div></div><div class=writerMetric><div class=label>Ready</div><div class=value>${s.foundation_ready?'YES':'NO'}</div></div></div><div class=writerPath>Flagship universe: ${esc(s.flagship_universe||'')}</div><div class=writerPath>Read only: ${s.read_only} • Report only: ${s.report_only}</div>${d.exported?`<div class=writerPath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('kayockWriterModules').innerHTML=(d.module_plan||[]).map(m=>`<div class=writerModule><b>${esc(m.name||'')}</b><div>ID: ${esc(m.id||'')} | Status: ${esc(m.status||'')}</div><div>${esc(m.purpose||'')}</div><div class=writerPath>Future writes: ${esc(m.future_writes||'')}</div></div>`).join('')||'No modules.';
    q('kayockWriterNames').innerHTML=(d.naming_decisions||[]).map(n=>`<div class="histrow ok"><b>${esc(n.decision||'')}</b><div>ID: ${esc(n.id||'')} | Status: ${esc(n.status||'')}</div><div>${esc(n.notes||'')}</div></div>`).join('')||'No naming decisions.';
    let f=d.flagship_universe||{}; q('kayockWriterFlagship').textContent=`${f.title||''}\nStatus: ${f.status||''}\n\nBook 1:\n${f.book_1||''}\n\nBook 2:\n${f.book_2||''}\n\nUse:\n${f.use||''}`;
    q('kayockWriterPaths').innerHTML=(d.path_checks||[]).map(p=>`<div class="histrow ${p.exists?'ok':'info'}"><b>${esc(p.key||'path')}</b><div class=writerPath>${esc(p.path||'')}</div><div>Exists: ${p.exists} | Kind: ${esc(p.kind||'')} | Modified: ${esc(p.modified||'')}</div></div>`).join('')||'No path checks.';
    q('kayockWriterRecommendations').innerHTML=(d.recommendations||[]).map(r=>`<div class="histrow info"><b>${esc(r.title||'')}</b><div>ID: ${esc(r.id||'')} | Risk: ${esc(r.risk||'')} | Auto apply: ${r.auto_apply}</div><div>${esc(r.recommendation||'')}</div></div>`).join('')||'No recommendations.';
    q('kayockWriterSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Kayock Writer foundation loaded.');
}
function sendKayockWriterToMission(){
    if(!lastKayockWriter){toast('Load Kayock Writer foundation first.');return;}
    let d=lastKayockWriter; let s=d.summary||{}; go('mission');
    q('input').value=`Please review this Kayock Writer Foundation report.\n\nMilestone:\n${d.milestone}\n\nHealth:\n${d.health_label}\n\nSummary:\nModules: ${s.modules}\nChecks passed: ${s.checks_passed}/${s.checks}\nProblems: ${s.problems}\nNaming decisions: ${s.naming_decisions}\nExisting paths: ${s.existing_paths}/${s.path_checks}\nFlagship universe: ${s.flagship_universe}\nFoundation ready: ${s.foundation_ready}\nRead only: ${s.read_only}\nReport only: ${s.report_only}\n\nModule plan:\n${(d.module_plan||[]).map(m=>`${m.id} — ${m.name}: ${m.purpose}`).join('\n')}\n\nNaming decisions:\n${(d.naming_decisions||[]).map(n=>`${n.id}: ${n.status} — ${n.decision}`).join('\n')}\n\nFlagship universe:\n${d.flagship_universe?.title}\nBook 1: ${d.flagship_universe?.book_1}\nBook 2: ${d.flagship_universe?.book_2}\n\nPath checks:\n${(d.path_checks||[]).map(p=>`${p.key}: ${p.path} — exists=${p.exists} — kind=${p.kind}`).join('\n')}\n\nRecommendations:\n${(d.recommendations||[]).map(r=>`${r.id}: ${r.recommendation} — auto apply=${r.auto_apply}`).join('\n')}\n\nExport:\n${d.exported?.markdown||'No exported Kayock Writer foundation report'}\n\nSafety:\nRead-only Kayock Writer foundation report.\nNo story-file mutation.\nNo rename performed.\nNo migration performed.\nNo overwrite.\nNo delete.\nNo install.\nNo model cleanup.\nFuture writes require explicit user approval.\n\nPlease determine:\n1. Whether v10.11.0 should be marked stable/proven\n2. Whether Kayock Writer should replace Novel Forge as the public department name\n3. Whether Story Forge should be the next build\n4. Whether Poetry Studio should follow after Story Forge.`;
    toast('Kayock Writer foundation sent to Mission Console.');
}

let lastCommandFreeze=null;
async function loadCommandFreeze(doExport=false){
    if(!q('commandFreezeStatus'))return;
    q('commandFreezeStatus').textContent='Loading Command Center milestone freeze...';
    let d=await api('/api/command_center/milestone_freeze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:300,export:doExport})});
    if(!d?.ok){
        q('commandFreezeStatus').textContent=d?.message||'Could not load Command Center milestone freeze.';
        return;
    }
    lastCommandFreeze=d;
    let s=d.summary||{};
    let cls=d.freeze_ready?(s.advisory?'advisory':'clear'):'bad';
    q('commandFreezeStatus').innerHTML=`<span class="cmdFreezeBadge ${cls}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('commandFreezeSummary').innerHTML=`<div><b>${esc(d.milestone||'')}</b> • ${esc(d.version_range||'')}</div>
    <div class=cmdFreezeGrid>
      <div class=cmdFreezeMetric><div class=label>Modules Proven</div><div class=value>${s.modules_complete_proven||0}/${s.modules||0}</div></div>
      <div class=cmdFreezeMetric><div class=label>Score</div><div class=value>${s.score||0}</div></div>
      <div class=cmdFreezeMetric><div class=label>Foundations</div><div class=value>${s.foundations||0}</div></div>
      <div class=cmdFreezeMetric><div class=label>Clear</div><div class=value>${s.clear||0}</div></div>
      <div class=cmdFreezeMetric><div class=label>Advisory</div><div class=value>${s.advisory||0}</div></div>
      <div class=cmdFreezeMetric><div class=label>Attention</div><div class=value>${s.needs_attention||0}</div></div>
      <div class=cmdFreezeMetric><div class=label>Archive Reports</div><div class=value>${s.archive_reports||0}</div></div>
      <div class=cmdFreezeMetric><div class=label>Archive Errors</div><div class=value>${s.archive_errors||0}</div></div>
    </div>
    <div class=cmdFreezePath>Command Center: ${esc(s.command_center_health||'')}</div>
    <div class=cmdFreezePath>Dashboard card: ${esc(s.dashboard_card_health||'')}</div>
    <div class=cmdFreezePath>Archive: ${esc(s.archive_health||'')}</div>
    <div class=cmdFreezePath>Repair Shop: ${esc(s.repair_shop_foundation||'')} • Recovery: ${esc(s.recovery_foundation||'')}</div>
    <div class=cmdFreezePath>Latest repair action: ${esc(s.latest_repair_action||'none')} • Latest recovery: ${esc(s.latest_recovery_event||'none')}</div>
    ${d.exported?`<div class=cmdFreezePath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('commandFreezeModules').innerHTML=(d.modules||[]).map(m=>`<div class="histrow ${m.status==='complete_proven'?'ok':'fail'}"><b>${esc(m.version||'')} — ${esc(m.name||'')}</b>${verifyBadge(m.status==='complete_proven'?'passed':'failed')}
<div>Status: ${esc(m.status||'')} | Health: ${esc(m.health||'')}</div>
<div>${esc(m.proof||'')}</div>
<div class=vaultpath>Page: ${esc(m.page||'')} | Endpoint: ${esc(m.endpoint||'')}</div></div>`).join('')||'No modules.';
    q('commandFreezeAdvisories').innerHTML=(d.advisories||[]).map(a=>`<div class="histrow info"><b>${esc(a.title||'')}</b><div>ID: ${esc(a.id||'')}</div><div>${esc(a.summary||'')}</div><div class=vaultpath>${esc(a.recommended_action||'')} | Safe to ignore: ${a.safe_to_ignore}</div></div>`).join('')||'<div class="histrow ok"><b>No advisories.</b><div>All Command Center foundations are fully clear.</div></div>';
    q('commandFreezeRecommendations').innerHTML=(d.recommendations||[]).map(r=>`<div class="histrow info"><b>${esc(r.title||'')}</b><div>ID: ${esc(r.id||'')} | Status: ${esc(r.status||'')} | Risk: ${esc(r.risk||'')} | Auto apply: ${r.auto_apply}</div><div>${esc(r.recommendation||'')}</div></div>`).join('')||'No recommendations.';
    q('commandFreezeProblems').innerHTML=(d.problems||[]).map(p=>`<div class="histrow fail"><b>${esc(p.source||'review')}</b><div>${esc(p.message||'')}</div></div>`).join('')||'<div class="histrow ok"><b>No problems.</b><div>Command Center milestone is ready to freeze.</div></div>';
    q('commandFreezeSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Command Center milestone freeze loaded.');
}
function sendCommandFreezeToMission(){
    if(!lastCommandFreeze){
        toast('Load Command Center freeze first.');
        return;
    }
    let d=lastCommandFreeze;
    let s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Command Center Milestone Freeze.

Milestone:
${d.milestone}
Version range: ${d.version_range}
Health: ${d.health_label}
Freeze ready: ${d.freeze_ready}

Summary:
Modules proven: ${s.modules_complete_proven}/${s.modules}
Modules need review: ${s.modules_need_review}
Command Center health: ${s.command_center_health}
Dashboard card health: ${s.dashboard_card_health}
Archive health: ${s.archive_health}
Score: ${s.score}
Foundations: ${s.foundations}
Clear/advisory/attention: ${s.clear}/${s.advisory}/${s.needs_attention}
Command ready: ${s.command_ready}
Archive reports: ${s.archive_reports}
Archive errors: ${s.archive_errors}
Trend attention reports: ${s.trend_attention_reports}
Repair Shop Foundation: ${s.repair_shop_foundation}
Recovery Foundation: ${s.recovery_foundation}
Latest repair action: ${s.latest_repair_action}
Latest recovery event: ${s.latest_recovery_event}

Modules:
${(d.modules||[]).map(m=>`${m.version} — ${m.name} — ${m.status} — ${m.proof}`).join('\n')}

Advisories:
${(d.advisories||[]).length ? (d.advisories||[]).map(a=>`${a.id}: ${a.summary} — ${a.recommended_action}`).join('\n') : 'None.'}

Problems:
${(d.problems||[]).length ? (d.problems||[]).map(p=>`${p.source}: ${p.message}`).join('\n') : 'None.'}

Recommendations:
${(d.recommendations||[]).map(r=>`${r.id}: ${r.status} — ${r.recommendation} — auto apply=${r.auto_apply}`).join('\n')}

Export:
${d.exported?.markdown||'No exported Command Center freeze report'}

Safety:
Scan first. Report second. Ask before action.
Read-only milestone freeze report.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether v10.10.x Command Center Foundation should be frozen
2. Whether advisories are safe to carry as optional maintenance
3. Whether v10.10.4 should be marked stable/proven
4. What the next foundation milestone should be.`;
    toast('Command Center freeze sent to Mission Console.');
}

let lastCommandArchive=null;
async function loadCommandArchive(doExport=false){
    if(!q('commandArchiveStatus'))return;
    q('commandArchiveStatus').textContent='Loading Command Center archive...';
    let d=await api('/api/command_center/archive',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:200,export:doExport})});
    if(!d?.ok){
        q('commandArchiveStatus').textContent=d?.message||'Could not load Command Center archive.';
        return;
    }
    lastCommandArchive=d;
    let s=d.summary||{};
    let cls=s.latest_needs_attention?'bad':(s.latest_advisory?'advisory':'clear');
    q('commandArchiveStatus').innerHTML=`<span class="archiveBadge ${cls}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('commandArchiveSummary').innerHTML=`<div class=archiveGrid>
      <div class=archiveMetric><div class=label>Reports</div><div class=value>${s.reports||0}</div></div>
      <div class=archiveMetric><div class=label>Foundation</div><div class=value>${s.foundation_reports||0}</div></div>
      <div class=archiveMetric><div class=label>Cards</div><div class=value>${s.dashboard_card_reports||0}</div></div>
      <div class=archiveMetric><div class=label>Details</div><div class=value>${s.detail_reports||0}</div></div>
      <div class=archiveMetric><div class=label>Latest Score</div><div class=value>${s.latest_score||0}</div></div>
      <div class=archiveMetric><div class=label>Errors</div><div class=value>${s.errors||0}</div></div>
    </div>
    <div class=archivePath>Latest foundation: ${esc(s.latest_foundation_report||'none')} — ${esc(s.latest_foundation_health||'')}</div>
    <div class=archivePath>Latest dashboard: ${esc(s.latest_dashboard_report||'none')} — ${esc(s.latest_dashboard_health||'')}</div>
    <div class=archivePath>Latest detail: ${esc(s.latest_detail_report||'none')} — ${esc(s.latest_detail_foundation||'')}</div>
    <div class=archivePath>Latest repair action: ${esc(s.latest_repair_action||'none')} • Latest recovery: ${esc(s.latest_recovery_event||'none')}</div>
    ${d.exported?`<div class=archivePath>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    q('commandArchiveTrend').innerHTML=(d.trend||[]).slice().reverse().map(t=>`<div class="histrow ${t.needs_attention?'fail':(t.advisory?'info':'ok')}"><b>${esc(t.created||'')}</b><div>${esc(t.type||'')} — ${esc(t.health_label||'')}</div><div>Score: ${t.score||0} | Clear/advisory/attention: ${t.clear||0}/${t.advisory||0}/${t.needs_attention||0} | Ready: ${t.command_ready}</div></div>`).join('')||'No trend data yet.';
    q('commandArchiveTimeline').innerHTML=(d.timeline||[]).slice(0,80).map(t=>`<div class="histrow info"><b>${esc(t.created||'')} — ${esc(t.type||'')}</b><div>${esc(t.name||'')}</div><div>${esc(t.health_label||'')} ${t.foundation_id?('• '+esc(t.foundation_id)+' '+esc(t.foundation_status||'')):''}</div><div class=vaultpath>${esc(t.path||'')}</div></div>`).join('')||'No archived reports yet.';
    let latest=[];
    if(d.latest_foundation?.name)latest.push(`<div class="histrow ok"><b>Latest Foundation Report</b><div>${esc(d.latest_foundation.name)} — ${esc(d.latest_foundation.health_label||'')}</div><div class=vaultpath>${esc(d.latest_foundation.path||'')}</div></div>`);
    if(d.latest_dashboard?.name)latest.push(`<div class="histrow ok"><b>Latest Dashboard Card Report</b><div>${esc(d.latest_dashboard.name)} — ${esc(d.latest_dashboard.health_label||'')}</div><div class=vaultpath>${esc(d.latest_dashboard.path||'')}</div></div>`);
    if(d.latest_detail?.name)latest.push(`<div class="histrow ok"><b>Latest Detail Report</b><div>${esc(d.latest_detail.name)} — ${esc(d.latest_detail.foundation_id||'')}</div><div class=vaultpath>${esc(d.latest_detail.path||'')}</div></div>`);
    (d.errors||[]).forEach(e=>latest.push(`<div class="histrow fail"><b>Archive Error</b><div>${esc(JSON.stringify(e))}</div></div>`));
    q('commandArchiveLatest').innerHTML=latest.join('')||'No latest report data.';
    q('commandArchiveSafety').textContent=Object.entries(d.safety||{}).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Command Center archive loaded.');
}
function sendCommandArchiveToMission(){
    if(!lastCommandArchive){
        toast('Load Command Center archive first.');
        return;
    }
    let d=lastCommandArchive;
    let s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Command Center History / Archive report.

Health:
${d.health_label}

Summary:
Reports: ${s.reports}
Foundation reports: ${s.foundation_reports}
Dashboard card reports: ${s.dashboard_card_reports}
Detail reports: ${s.detail_reports}
Errors: ${s.errors}
Latest score: ${s.latest_score}
Latest clear/advisory/attention: ${s.latest_clear}/${s.latest_advisory}/${s.latest_needs_attention}
Latest command ready: ${s.latest_command_ready}
Trend clear reports: ${s.trend_clear_reports}
Trend advisory reports: ${s.trend_advisory_reports}
Trend attention reports: ${s.trend_attention_reports}
Latest repair action: ${s.latest_repair_action}
Latest recovery event: ${s.latest_recovery_event}

Trend:
${(d.trend||[]).map(t=>`${t.created} — ${t.type} — ${t.health_label} — score=${t.score} — clear/advisory/attention=${t.clear}/${t.advisory}/${t.needs_attention}`).join('\n')}

Timeline:
${(d.timeline||[]).slice(0,30).map(t=>`${t.created} — ${t.type} — ${t.name} — ${t.health_label} — ${t.path}`).join('\n')}

Errors:
${(d.errors||[]).length ? (d.errors||[]).map(e=>JSON.stringify(e)).join('\n') : 'None.'}

Export:
${d.exported?.markdown||'No exported archive report'}

Safety:
Read-only archive viewer.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the Command Center archive is healthy
2. Whether v10.10.3 should be marked stable/proven
3. Whether the next build should freeze the Command Center milestone.`;
    toast('Command Center archive sent to Mission Console.');
}

let lastCommandCenterDashboard=null;
async function loadCommandCenterDashboard(doExport=false){
    if(!q('commandCenterDashStatus'))return;
    q('commandCenterDashStatus').textContent='Loading Command Center dashboard card...';
    let d=await api('/api/command_center/dashboard_card',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:300,export:doExport})});
    if(!d?.ok){
        q('commandCenterDashStatus').textContent=d?.message||'Could not load Command Center dashboard card.';
        return;
    }
    lastCommandCenterDashboard=d;
    let cls=d.card_state==='clear'?'clear':(d.card_state==='advisory'?'advisory':'bad');
    q('commandCenterDashStatus').innerHTML=`<span class="ccDashBadge ${cls}">${esc(d.health_label||'UNKNOWN')}</span>`;
    q('commandCenterDashBody').innerHTML=`<div class=ccDashGrid>
      <div class=ccDashMetric><div class=label>Score</div><div class=value>${d.score||0}</div></div>
      <div class=ccDashMetric><div class=label>Foundations</div><div class=value>${d.foundations_total||0}</div></div>
      <div class=ccDashMetric><div class=label>Clear</div><div class=value>${d.foundations_clear||0}</div></div>
      <div class=ccDashMetric><div class=label>Advisory</div><div class=value>${d.foundations_advisory||0}</div></div>
      <div class=ccDashMetric><div class=label>Attention</div><div class=value>${d.foundations_needs_attention||0}</div></div>
      <div class=ccDashMetric><div class=label>Ready</div><div class=value>${d.command_ready?'YES':'NO'}</div></div>
    </div>
    <div class=ccDashLine>Repair Shop: ${esc(d.repair_shop_foundation||'')}</div>
    <div class=ccDashLine>Recovery: ${esc(d.recovery_foundation||'')}</div>
    <div class=ccDashLine>Latest repair action: ${esc(d.latest_repair_action||'none')}</div>
    <div class=ccDashLine>Latest recovery event: ${esc(d.latest_recovery_event||'none')}</div>
    ${d.primary_advisory?.title?`<div class=ccDashLine>Advisory: ${esc(d.primary_advisory.title)} — ${esc(d.primary_advisory.summary||'')}</div>`:''}
    ${d.primary_attention?.title?`<div class=ccDashLine>Attention: ${esc(d.primary_attention.title)} — ${esc(d.primary_attention.summary||'')}</div>`:''}
    ${d.exported?`<div class=ccDashLine>Export: ${esc(d.exported.markdown||'')}</div>`:''}`;
    toast('Command Center dashboard card loaded.');
}
function sendCommandCenterDashboardToMission(){
    if(!lastCommandCenterDashboard){
        toast('Refresh Command Center dashboard first.');
        return;
    }
    let d=lastCommandCenterDashboard;
    go('mission');
    q('input').value=`Please review this Kayock Command Center Dashboard Card.

Health:
${d.health_label}

Command ready: ${d.command_ready}
Fully clear: ${d.fully_clear}
Score: ${d.score}

Foundations:
Total: ${d.foundations_total}
Clear: ${d.foundations_clear}
Advisory: ${d.foundations_advisory}
Needs attention: ${d.foundations_needs_attention}

Repair Shop Foundation:
${d.repair_shop_foundation}

Recovery Foundation:
${d.recovery_foundation}

Latest repair action:
${d.latest_repair_action}

Latest recovery event:
${d.latest_recovery_event}

Advisories:
${(d.advisories||[]).length ? (d.advisories||[]).map(a=>`${a.id}: ${a.summary} — ${a.recommended_action}`).join('\n') : 'None.'}

Attention:
${(d.attention||[]).length ? (d.attention||[]).map(a=>`${a.id}: ${a.summary} — ${a.recommended_action}`).join('\n') : 'None.'}

Foundation list:
${(d.foundations||[]).map(f=>`${f.status} — ${f.title}: ${f.summary}`).join('\n')}

Recommendations:
${(d.recommendations||[]).map(r=>`${r.id}: ${r.recommendation} — auto apply=${r.auto_apply}`).join('\n')}

Export:
${d.exported?.markdown||'No exported dashboard card report'}

Safety:
Read-only dashboard card.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether this dashboard card reflects Command Center correctly
2. Whether v10.10.2 should be marked stable/proven
3. Whether the next build should add a Command Center history/archive view.`;
    toast('Command Center dashboard sent to Mission Console.');
}

let lastCommandDetail=null;
async function loadCommandDetailList(){
    let sel=q('commandDetailSelect');
    if(!sel)return;
    q('commandDetailStatus').textContent='Loading foundation list...';
    let d=await api('/api/command_center/foundation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:300})});
    if(!d?.ok){
        q('commandDetailStatus').textContent=d?.message||'Could not load Command Center foundations.';
        return;
    }
    sel.innerHTML=(d.foundations||[]).map(f=>`<option value="${esc(f.id||'')}">${esc(f.id||'')} — ${esc(f.status||'')} — ${esc(f.title||'')}</option>`).join('');
    q('commandDetailStatus').textContent=`Foundation list loaded: ${(d.foundations||[]).length}`;
    toast('Foundation list loaded.');
}
async function loadCommandDetail(doExport=false){
    let sel=q('commandDetailSelect');
    let id=sel?.value||'env_verify';
    q('commandDetailStatus').textContent='Loading foundation detail...';
    let d=await api('/api/command_center/detail',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({foundation_id:id,limit:300,export:doExport})});
    if(!d?.ok){
        q('commandDetailStatus').textContent=d?.message||'Could not load foundation detail.';
        return;
    }
    lastCommandDetail=d;
    q('commandDetailStatus').textContent=`Detail loaded.
Foundation: ${d.foundation_title}
Status: ${d.foundation_status}
Health: ${d.foundation_health}
Detail OK: ${d.detail_ok}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    let cls=d.foundation_status==='clear'?'clear':(d.foundation_status==='advisory'?'advisory':'bad');
    q('commandDetailSummary').innerHTML=`<span class="cmdDetailBadge ${cls}">${esc(d.health_label||'UNKNOWN')}</span>
<div><b>${esc(d.foundation_title||'')}</b> <span class=muted>(${esc(d.foundation_id||'')})</span></div>
<div>Status: ${esc(d.foundation_status||'')} | Health: ${esc(d.foundation_health||'')}</div>
<div>${esc(d.foundation_summary||'')}</div>
<div class=cmdPath>Source: ${esc(d.foundation_source||'')}</div>
<div class=cmdPath>Page: ${esc(d.foundation_page||'')} | Endpoint: ${esc(d.foundation_endpoint||'')}</div>
<div class=cmdPath>Recommended action: ${esc(d.recommended_action||'')}</div>`;
    q('commandDetailMetrics').innerHTML=Object.entries(d.metrics||{}).map(([k,v])=>`<div class=cmdMetric><div class=k>${esc(k)}</div><div class=v>${esc(typeof v==='object'?JSON.stringify(v):String(v))}</div></div>`).join('')||'No metrics.';
    let sig=[];
    (d.matching_attention||[]).forEach(a=>sig.push(`<div class="histrow fail"><b>Attention</b><div>${esc(a.summary||'')}</div><div class=vaultpath>${esc(a.recommended_action||'')}</div></div>`));
    (d.matching_advisory||[]).forEach(a=>sig.push(`<div class="histrow info"><b>Advisory</b><div>${esc(a.summary||'')}</div><div class=vaultpath>${esc(a.recommended_action||'')}</div></div>`));
    (d.recommended_next||[]).forEach(r=>sig.push(`<div class="histrow info"><b>${esc(r.title||'')}</b><div>${esc(r.recommendation||'')}</div><div class=vaultpath>Risk: ${esc(r.risk||'')} | Auto apply: ${r.auto_apply}</div></div>`));
    q('commandDetailSignal').innerHTML=sig.join('')||'<div class="histrow ok"><b>No advisory or attention.</b><div>This foundation is clear.</div></div>';
    q('commandDetailPaths').innerHTML=(d.related_paths||[]).map(p=>`<div class="histrow ${p.exists===false?'fail':'ok'}"><b>${esc(p.key||'path')}</b><div class=vaultpath>${esc(p.path||'')}</div><div>Kind: ${esc(p.kind||'')} | Exists: ${p.exists===undefined?'n/a':p.exists} | Size: ${p.size??''} | Modified: ${esc(p.modified||'')}</div></div>`).join('')||'No related paths.';
    q('commandDetailChecks').innerHTML=(d.detail_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b><div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.path||'')}</div></div>`).join('')||'No checks.';
    let sc=d.safety||{};
    q('commandDetailSafety').textContent=Object.entries(sc).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Foundation detail loaded.');
}
function openCommandDetailRelatedPage(){
    if(!lastCommandDetail){
        toast('Load foundation detail first.');
        return;
    }
    if(lastCommandDetail.foundation_page){
        go(lastCommandDetail.foundation_page);
    }else{
        toast('No related page declared.');
    }
}
function sendCommandDetailToMission(){
    if(!lastCommandDetail){
        toast('Load foundation detail first.');
        return;
    }
    let d=lastCommandDetail;
    go('mission');
    q('input').value=`Please review this Kayock Command Center foundation detail.

Foundation:
${d.foundation_title}
ID: ${d.foundation_id}
Status: ${d.foundation_status}
Health: ${d.foundation_health}
Detail OK: ${d.detail_ok}

Summary:
${d.foundation_summary}

Source:
${d.foundation_source}
Page: ${d.foundation_page}
Endpoint: ${d.foundation_endpoint}

Recommended action:
${d.recommended_action}

Metrics:
${Object.entries(d.metrics||{}).map(([k,v])=>`${k}: ${typeof v==='object'?JSON.stringify(v):v}`).join('\n')}

Attention:
${(d.matching_attention||[]).length ? (d.matching_attention||[]).map(a=>`${a.id}: ${a.summary} — ${a.recommended_action}`).join('\n') : 'None.'}

Advisory:
${(d.matching_advisory||[]).length ? (d.matching_advisory||[]).map(a=>`${a.id}: ${a.summary} — ${a.recommended_action}`).join('\n') : 'None.'}

Recommended next:
${(d.recommended_next||[]).map(r=>`${r.id}: ${r.recommendation} — auto apply=${r.auto_apply}`).join('\n')}

Detail checks:
${(d.detail_checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message}`).join('\n')}

Related paths:
${(d.related_paths||[]).map(p=>`${p.key}: ${p.path} — exists=${p.exists}`).join('\n')}

Export:
${d.exported?.markdown||'No exported detail report'}

Safety:
Read-only foundation detail.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether this foundation is clear, advisory, or needs attention
2. Whether the recommendation is safe
3. Whether v10.10.1 should be marked stable/proven.`;
    toast('Command Center detail sent to Mission Console.');
}

let lastCommandCenter=null;
async function loadCommandCenter(doExport=false){
    if(!q('commandCenterStatus'))return;
    q('commandCenterStatus').textContent='Loading Command Center foundation report...';
    let d=await api('/api/command_center/foundation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:300,export:doExport})});
    if(!d?.ok){
        q('commandCenterStatus').textContent=d?.message||'Could not load Command Center.';
        return;
    }
    lastCommandCenter=d;
    let s=d.summary||{};
    q('commandCenterStatus').textContent=`Command Center loaded.
Health: ${d.health_label}
Command ready: ${d.command_ready}
Foundations: ${s.foundations}
Clear/advisory/attention: ${s.clear}/${s.advisory}/${s.needs_attention}
Score: ${s.score}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    let badgeClass=d.fully_clear?'clear':(d.command_ready?'advisory':'bad');
    q('commandCenterSummary').innerHTML=`<span class="ccBadge ${badgeClass}">${esc(d.health_label||'UNKNOWN')}</span>
<div><b>${esc(d.milestone||'')}</b></div>
<div class=ccGrid>
  <div class=ccMetric><div class=label>Score</div><div class=value>${s.score||0}</div></div>
  <div class=ccMetric><div class=label>Foundations</div><div class=value>${s.foundations||0}</div></div>
  <div class=ccMetric><div class=label>Clear</div><div class=value>${s.clear||0}</div></div>
  <div class=ccMetric><div class=label>Advisory</div><div class=value>${s.advisory||0}</div></div>
  <div class=ccMetric><div class=label>Attention</div><div class=value>${s.needs_attention||0}</div></div>
  <div class=ccMetric><div class=label>Portable</div><div class=value>${s.portable_score||0}</div></div>
  <div class=ccMetric><div class=label>Env Optional</div><div class=value>${s.env_optional_missing||0}</div></div>
  <div class=ccMetric><div class=label>Model Dupes</div><div class=value>${s.true_model_duplicate_groups||0}</div></div>
</div>
<div class=ccPath>Repair Shop: ${esc(s.repair_shop_foundation||'')}</div>
<div class=ccPath>Recovery: ${esc(s.recovery_foundation||'')} • Latest: ${esc(s.latest_recovery_event||'')}</div>
<div class=ccPath>Latest repair action: ${esc(s.latest_repair_action||'none')}</div>`;
    q('commandCenterFoundations').innerHTML=(d.foundations||[]).map(f=>{
        let cls=f.status==='clear'?'clear':(f.status==='advisory'?'advisory':'needs_attention');
        let badge=f.status==='clear'?'passed':(f.status==='advisory'?'not_recorded':'failed');
        return `<div class="foundationCard ${cls}"><b>${esc(f.title||'')}</b>${verifyBadge(badge)}
<div>Status: ${esc(f.status||'')} | Health: ${esc(f.health||'')}</div>
<div>${esc(f.summary||'')}</div>
<div class=vaultpath>Source: ${esc(f.source||'')} | Page: ${esc(f.page||'')} | Endpoint: ${esc(f.endpoint||'')}</div>
<div class=vaultpath>Recommended: ${esc(f.recommended_action||'')}</div></div>`;
    }).join('')||'No foundations loaded.';
    q('commandCenterAttention').innerHTML=(d.attention||[]).map(a=>`<div class="histrow fail"><b>${esc(a.title||'')}</b><div>${esc(a.summary||'')}</div><div class=vaultpath>${esc(a.recommended_action||'')}</div></div>`).join('')||'<div class="histrow ok"><b>No attention items.</b><div>Command Center has no failing foundations.</div></div>';
    q('commandCenterAdvisories').innerHTML=(d.advisories||[]).map(a=>`<div class="histrow info"><b>${esc(a.title||'')}</b><div>${esc(a.summary||'')}</div><div class=vaultpath>${esc(a.recommended_action||'')}</div></div>`).join('')||'<div class="histrow ok"><b>No advisories.</b><div>All foundations are fully clear.</div></div>';
    q('commandCenterNext').innerHTML=(d.recommendations||[]).map(r=>`<div class="histrow info"><b>${esc(r.title||'')}</b><div>ID: ${esc(r.id||'')} | Risk: ${esc(r.risk||'')} | Auto apply: ${r.auto_apply}</div><div>${esc(r.recommendation||'')}</div></div>`).join('')||'No recommendations.';
    let sc=d.safety_contract||{};
    q('commandCenterSafety').textContent=Object.entries(sc).map(([k,v])=>`${k}: ${v}`).join('\n');
    toast('Command Center loaded.');
}
function sendCommandCenterToMission(){
    if(!lastCommandCenter){
        toast('Load Command Center first.');
        return;
    }
    let d=lastCommandCenter;
    let s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Command Center Foundation report.

Milestone:
${d.milestone}

Health:
${d.health_label}

Command ready: ${d.command_ready}
Fully clear: ${d.fully_clear}
Score: ${s.score}

Summary:
Foundations: ${s.foundations}
Clear: ${s.clear}
Advisory: ${s.advisory}
Needs attention: ${s.needs_attention}
Repair Shop Foundation: ${s.repair_shop_foundation}
Recovery Foundation: ${s.recovery_foundation}
Build Verify problems: ${s.build_verify_problems}
Env required problems: ${s.env_required_problems}
Env optional missing: ${s.env_optional_missing}
Portable score: ${s.portable_score}
Portable blockers/warnings: ${s.portable_blockers}/${s.portable_warnings}
True model duplicate groups: ${s.true_model_duplicate_groups}
Scan Bridge status: ${s.scan_bridge_status}
Project Docs problems: ${s.project_docs_problems}
Extension problems: ${s.extension_problems}
Latest repair action: ${s.latest_repair_action}
Latest recovery event: ${s.latest_recovery_event}

Foundations:
${(d.foundations||[]).map(f=>`${f.status} — ${f.title}: ${f.summary} — recommended=${f.recommended_action}`).join('\n')}

Attention:
${(d.attention||[]).length ? (d.attention||[]).map(a=>`${a.id}: ${a.summary}`).join('\n') : 'None.'}

Advisories:
${(d.advisories||[]).length ? (d.advisories||[]).map(a=>`${a.id}: ${a.summary}`).join('\n') : 'None.'}

Recommendations:
${(d.recommendations||[]).map(r=>`${r.id}: ${r.recommendation} — auto apply=${r.auto_apply}`).join('\n')}

Export:
${d.exported?.markdown||'No exported Command Center report'}

Safety:
Scan first. Report second. Ask before action.
Read-only Command Center.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether v10.10.0 should be marked stable/proven
2. Whether Command Center is ready for normal work
3. Which advisories are safe to ignore
4. What the next foundation milestone should be.`;
    toast('Command Center sent to Mission Console.');
}

let lastRepairFreeze=null;
async function loadRepairFreeze(doExport=false){
    if(!q('repairFreezeStatus'))return;
    q('repairFreezeStatus').textContent='Loading Repair Shop milestone freeze...';
    let d=await api('/api/repair/milestone_freeze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:300,export:doExport})});
    if(!d?.ok){
        q('repairFreezeStatus').textContent=d?.message||'Could not load milestone freeze.';
        return;
    }
    lastRepairFreeze=d;
    let s=d.summary||{};
    q('repairFreezeStatus').textContent=`Milestone freeze loaded.
Health: ${d.health_label}
Freeze ready: ${d.freeze_ready}
Modules proven: ${s.modules_complete_proven}/${s.modules}
Repair failures: ${s.repair_failed}
Verification failures: ${s.verification_failed}
Open tickets: ${s.open_tickets}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('repairFreezeSummary').innerHTML=`<span class="freezeBadge ${d.freeze_ready?'healthy':'warn'}">${esc(d.health_label||'UNKNOWN')}</span>
<div><b>${esc(d.milestone||'')}</b> • ${esc(d.version_range||'')}</div>
<div class=freezeGrid>
  <div class=freezeMetric><div class=label>Modules Proven</div><div class=value>${s.modules_complete_proven||0}/${s.modules||0}</div></div>
  <div class=freezeMetric><div class=label>Repair Failed</div><div class=value>${s.repair_failed||0}</div></div>
  <div class=freezeMetric><div class=label>Verify Failed</div><div class=value>${s.verification_failed||0}</div></div>
  <div class=freezeMetric><div class=label>Open Tickets</div><div class=value>${s.open_tickets||0}</div></div>
  <div class=freezeMetric><div class=label>Critical/High/Med</div><div class=value>${s.critical||0}/${s.high||0}/${s.medium||0}</div></div>
  <div class=freezeMetric><div class=label>Backups</div><div class=value>${s.generated_backups||0}</div></div>
  <div class=freezeMetric><div class=label>Recovery</div><div class=value>${esc(s.recovery_chain||'')}</div></div>
  <div class=freezeMetric><div class=label>Active Tickets</div><div class=value>${s.active_tickets||0}</div></div>
</div>
<div class=freezePath>Repair Shop: ${esc(s.repair_shop_health||'')} • Session: ${esc(s.session_health||'')}</div>
<div class=freezePath>Recovery: ${esc(s.recovery_health||'')} • Latest: ${esc(s.latest_recovery_event||'')}</div>
<div class=freezePath>Latest action: ${esc(s.latest_action||'none')} ${s.latest_action_created?('• '+esc(s.latest_action_created)) : ''}</div>`;
    q('repairFreezeModules').innerHTML=(d.milestone_modules||[]).map(m=>`<div class="histrow ${m.status==='complete_proven'?'ok':'fail'}"><b>${esc(m.version||'')} — ${esc(m.name||'')}</b>${verifyBadge(m.status==='complete_proven'?'passed':'failed')}
<div>Status: ${esc(m.status||'')}</div>
<div>${esc(m.proof||'')}</div>
<div class=vaultpath>Endpoint: ${esc(m.endpoint||'')} | Page: ${esc(m.page||'')}</div></div>`).join('')||'No modules.';
    q('repairFreezeRecommendations').innerHTML=(d.recommendations||[]).map(r=>`<div class="histrow info"><b>${esc(r.title||'')}</b>
<div>ID: ${esc(r.id||'')} | Status: ${esc(r.status||'')} | Risk: ${esc(r.risk||'')}</div>
<div>${esc(r.recommendation||'')}</div></div>`).join('')||'No recommendations.';
    let sc=d.safety_contract||{};
    q('repairFreezeSafety').textContent=Object.entries(sc).map(([k,v])=>`${k}: ${v}`).join('\n');
    q('repairFreezeProblems').innerHTML=(d.problems||[]).map(p=>`<div class="histrow fail"><b>${esc(p.source||'review')}</b><div>${esc(p.message||'')}</div></div>`).join('')||'<div class="histrow ok"><b>No problems.</b><div>Milestone is ready to freeze.</div></div>';
    toast('Repair Shop milestone freeze loaded.');
}
function sendRepairFreezeToMission(){
    if(!lastRepairFreeze){
        toast('Load milestone freeze first.');
        return;
    }
    let d=lastRepairFreeze;
    let s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Repair Shop Milestone Freeze.

Milestone:
${d.milestone}
Version range: ${d.version_range}
Health: ${d.health_label}
Freeze ready: ${d.freeze_ready}

Summary:
Modules proven: ${s.modules_complete_proven}/${s.modules}
Modules need review: ${s.modules_need_review}
Repair Shop health: ${s.repair_shop_health}
Session health: ${s.session_health}
Ticket Queue health: ${s.ticket_queue_health}
Verified Action health: ${s.verified_action_health}
Recovery health: ${s.recovery_health}
Recovery chain: ${s.recovery_chain}
Repair logs: ${s.repair_logs}
Repair failed: ${s.repair_failed}
Verification failed: ${s.verification_failed}
Open tickets: ${s.open_tickets}
Critical/high/medium: ${s.critical}/${s.high}/${s.medium}
Active tickets: ${s.active_tickets}
Available action tickets: ${s.available_action_tickets}
Informational tickets: ${s.informational_tickets}
Healthy tickets: ${s.healthy_tickets}
Generated backups: ${s.generated_backups}
Verified backups: ${s.verified_backups}
Backup errors: ${s.backup_errors}
Latest action: ${s.latest_action}
Latest recovery event: ${s.latest_recovery_event}

Proven modules:
${(d.milestone_modules||[]).map(m=>`${m.version} — ${m.name} — ${m.status} — ${m.proof}`).join('\n')}

Recommendations:
${(d.recommendations||[]).map(r=>`${r.id}: ${r.status} — ${r.recommendation}`).join('\n')}

Problems:
${(d.problems||[]).length ? (d.problems||[]).map(p=>`${p.source}: ${p.message}`).join('\n') : 'None.'}

Safety contract:
Scan first. Report second. Ask before action.
Read-only freeze report.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Export:
${d.exported?.markdown||'No exported freeze report'}

Please determine:
1. Whether v10.9.x Repair Shop Foundation should be frozen
2. Whether the safety contract is sufficient
3. Whether legacy logs can remain historical
4. What the next milestone should be.`;
    toast('Repair Shop freeze sent to Mission Console.');
}

let lastRepairSession=null;
async function loadRepairSession(doExport=false){
    if(!q('repairSessionStatus'))return;
    q('repairSessionStatus').textContent='Loading Repair Shop session report...';
    let d=await api('/api/repair/session_report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:300,export:doExport})});
    if(!d?.ok){
        q('repairSessionStatus').textContent=d?.message||'Could not load session report.';
        return;
    }
    lastRepairSession=d;
    let s=d.summary||{};
    q('repairSessionStatus').textContent=`Session loaded.
Health: ${d.health_label}
Repair Shop: ${s.repair_shop_health}
Ticket Queue: ${s.ticket_queue_health}
Active tickets: ${s.active_tickets}
Open tickets: ${s.open_tickets}
Latest action: ${s.latest_action}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('repairSessionSummary').innerHTML=`<span class="sessionBadge ${d.healthy?'healthy':'warn'}">${esc(d.health_label||'UNKNOWN')}</span>
<div class=sessionGrid>
  <div class=sessionMetric><div class=label>Repair Logs</div><div class=value>${s.repair_logs||0}</div></div>
  <div class=sessionMetric><div class=label>Repair Failed</div><div class=value>${s.repair_failed||0}</div></div>
  <div class=sessionMetric><div class=label>Verify Failed</div><div class=value>${s.verification_failed||0}</div></div>
  <div class=sessionMetric><div class=label>Active Tickets</div><div class=value>${s.active_tickets||0}</div></div>
  <div class=sessionMetric><div class=label>Open Tickets</div><div class=value>${s.open_tickets||0}</div></div>
  <div class=sessionMetric><div class=label>Backups</div><div class=value>${s.generated_backups||0}</div></div>
  <div class=sessionMetric><div class=label>Legacy Logs</div><div class=value>${s.legacy_logs_without_verification||0}</div></div>
  <div class=sessionMetric><div class=label>Recovery</div><div class=value>${esc(s.recovery_chain||'')}</div></div>
</div>
<div class=sessionPath>Repair Shop: ${esc(s.repair_shop_health||'')} • Ticket Queue: ${esc(s.ticket_queue_health||'')}</div>
<div class=sessionPath>Recovery: ${esc(s.recovery_health||'')} • Latest recovery: ${esc(s.latest_recovery_event||'')}</div>
<div class=sessionPath>Latest action: ${esc(s.latest_action||'none')} ${s.latest_action_created?('• '+esc(s.latest_action_created)) : ''}</div>`;
    q('repairSessionChanged').innerHTML=(d.what_changed_this_session||[]).map(x=>`<div class="histrow ${x.ok?'ok':'fail'}"><b>${esc(x.created||'')} — ${esc(x.title||'')}</b>${verifyBadge(x.verified_state||'')}
<div>${esc(x.summary||'')}</div>
<div class=vaultpath>Target: ${esc(x.target||'')}</div>
<div class=vaultpath>Backup: ${esc(x.backup||'')}</div>
<div class=vaultpath>Log: ${esc(x.log||'')}</div></div>`).join('')||'No recent changes.';
    q('repairSessionTickets').innerHTML=(d.active_tickets||[]).map(t=>`<div class="ticket ${esc(t.severity||'info')}"><b>${esc(t.title||'')}</b>
<div>Source: ${esc(t.source||'')} | Severity: ${esc(t.severity||'')} | Status: ${esc(t.status||'')}</div>
<div>${esc(t.summary||'')}</div>
<div class=vaultpath>Suggested: ${esc(t.suggested_action||'')}</div>
<div class=vaultpath>Safe action: ${esc(t.safe_action_id||'none')}</div></div>`).join('')||'No active tickets.';
    q('repairSessionNext').innerHTML=(d.recommended_next||[]).map(r=>`<div class="histrow info"><b>${esc(r.title||'')}</b>
<div>Ticket: ${esc(r.ticket_id||'')} | Severity: ${esc(r.severity||'')}</div>
<div>${esc(r.recommendation||'')}</div>
<div class=vaultpath>Safe action: ${esc(r.safe_action_id||'none')} | Manual approval required: ${r.manual_approval_required} | Auto apply: ${r.auto_apply}</div></div>`).join('')||'No recommendations.';
    q('repairSessionIgnore').innerHTML=(d.safe_to_ignore||[]).map(r=>`<div class="histrow ok"><b>${esc(r.title||'')}</b>
<div>${esc(r.reason||'')}</div>
<div class=vaultpath>${esc(r.suggested_action||'')}</div></div>`).join('')||'No historical items.';
    toast('Repair Shop session report loaded.');
}
function sendRepairSessionToMission(){
    if(!lastRepairSession){
        toast('Load session report first.');
        return;
    }
    let d=lastRepairSession;
    let s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Repair Shop Session Report.

Health:
${d.health_label}

Summary:
Repair Shop health: ${s.repair_shop_health}
Ticket Queue health: ${s.ticket_queue_health}
Verified Action health: ${s.verified_action_health}
Recovery health: ${s.recovery_health}
Recovery chain: ${s.recovery_chain}
Repair logs: ${s.repair_logs}
Repair OK: ${s.repair_ok}
Repair failed: ${s.repair_failed}
Verification passed: ${s.verification_passed}
Verification failed: ${s.verification_failed}
Legacy logs without verification: ${s.legacy_logs_without_verification}
Tickets: ${s.tickets}
Active tickets: ${s.active_tickets}
Open tickets: ${s.open_tickets}
Available-action tickets: ${s.available_action_tickets}
Informational tickets: ${s.informational_tickets}
Healthy tickets: ${s.healthy_tickets}
Critical/high/medium: ${s.critical}/${s.high}/${s.medium}
Generated backups: ${s.generated_backups}
Verified backups: ${s.verified_backups}
Unassociated backups: ${s.unassociated_backups}
Backup errors: ${s.backup_errors}
Latest action: ${s.latest_action}
Latest action created: ${s.latest_action_created}
Latest backup: ${s.latest_backup}
Latest recovery event: ${s.latest_recovery_event}

What changed this session:
${(d.what_changed_this_session||[]).map(x=>`${x.created} — ${x.title} — ok=${x.ok} — verified=${x.verified_state} — ${x.summary} — target=${x.target} — backup=${x.backup}`).join('\n')}

Active tickets:
${(d.active_tickets||[]).map(t=>`${t.severity} — ${t.id}: ${t.summary} — suggested=${t.suggested_action} — safe_action=${t.safe_action_id||'none'}`).join('\n')}

Recommended next:
${(d.recommended_next||[]).map(r=>`${r.ticket_id}: ${r.recommendation} — manual approval required=${r.manual_approval_required} — auto apply=${r.auto_apply}`).join('\n')}

Safe to ignore/historical:
${(d.safe_to_ignore||[]).map(r=>`${r.ticket_id}: ${r.reason}`).join('\n')}

Export:
${d.exported?.markdown||'No exported session report'}

Safety:
Read-only session report.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether this session should be marked healthy
2. What should be safely ignored
3. What, if anything, should be recommended next
4. Whether v10.9.6 should be marked stable
5. Whether the next build should freeze Repair Shop or add a session archive viewer.`;
    toast('Repair Shop session sent to Mission Console.');
}

let lastTicketBridge=null;
let recommendedRepairActionId='';
function bridgeBadge(status,label){
    status=(status||'').toLowerCase();
    let cls=status==='ready_for_manual_approval'?'ready':(status==='informational_only'?'info':'warn');
    return `<span class="bridgeBadge ${cls}">${esc(label||status||'UNKNOWN')}</span>`;
}
async function loadTicketBridgeList(){
    q('ticketBridgeStatus').textContent='Loading ticket list for bridge...';
    let d=await api('/api/repair/ticket_queue',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({include_healthy:true,limit:500})});
    if(!d?.ok){q('ticketBridgeStatus').textContent=d?.message||'Could not load ticket queue.';return;}
    let all=d.tickets||[];
    q('ticketBridgeSelect').innerHTML=all.map(t=>`<option value="${esc(t.id||'')}">${esc((t.severity||'').toUpperCase())} — ${esc(t.id||'')} — ${esc(t.title||'')}</option>`).join('');
    if(all.length)q('ticketBridgeQuery').value=all[0].id||'';
    q('ticketBridgeStatus').textContent=`Loaded ${all.length} ticket(s) for bridge.`;
}
async function loadTicketBridge(doExport=false){
    let id=q('ticketBridgeQuery').value||q('ticketBridgeSelect').value||'';
    q('ticketBridgeStatus').textContent='Loading Ticket-to-Approved-Action Bridge...';
    let d=await api('/api/repair/ticket_action_bridge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ticket_id:id,query:id,export:doExport})});
    if(!d?.ok){q('ticketBridgeStatus').textContent=d?.message||'Could not load bridge.';return;}
    lastTicketBridge=d;
    recommendedRepairActionId=d.safe_action_id||'';
    q('ticketBridgeStatus').textContent=`Bridge loaded.
Ticket: ${d.ticket_id}
Bridge status: ${d.bridge_status}
Safe action: ${d.safe_action_id||'none'}
Available: ${d.safe_action_available}
Requires confirmation: ${d.safe_action_requires_confirmation}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    let a=d.matching_safe_action||{};
    q('ticketBridgeSummary').innerHTML=`${bridgeBadge(d.bridge_status,d.bridge_label)}
<div><b>${esc(d.ticket_title||'Ticket')}</b></div>
<div>Source: ${esc(d.ticket_source||'')} • Severity: <b>${esc(d.ticket_severity||'')}</b> • Ticket status: <b>${esc(d.ticket_status||'')}</b></div>
<div>${esc(d.ticket_summary||'')}</div>
<div class=bridgeGrid>
  <div class=bridgeMetric><div class=label>Safe Action</div><div class=value>${esc(d.safe_action_id||'none')}</div></div>
  <div class=bridgeMetric><div class=label>Available</div><div class=value>${d.safe_action_available}</div></div>
  <div class=bridgeMetric><div class=label>Confirmation</div><div class=value>${d.safe_action_requires_confirmation}</div></div>
  <div class=bridgeMetric><div class=label>Detail OK</div><div class=value>${d.detail_ok}</div></div>
</div>
<div class=vaultpath>${esc(d.message||'')}</div>`;
    q('ticketBridgeAction').innerHTML=a.id?`<div class=histrow ${a.available?'ok':'info'}><b>${esc(a.title||a.id)}</b><div>ID: <code>${esc(a.id)}</code> | Risk: ${esc(a.risk||'')}</div><div>${esc(a.description||'')}</div><div>Available: ${a.available} | Requires confirmation: ${a.requires_confirmation}</div><div class=vaultpath>Reason: ${esc(a.reason||'')}</div><div class=vaultpath>Writes: ${(a.writes||[]).map(w=>esc(w)).join(' | ')||'none'}</div></div>`:'No matching safe action for this ticket.';
    q('ticketBridgeSteps').innerHTML=(d.manual_next_steps||[]).map((s,i)=>`<div class="histrow info"><b>Step ${i+1}</b><div>${esc(s)}</div></div>`).join('')||'No steps.';
    q('ticketBridgeChecks').innerHTML=(d.detail_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b>${verifyBadge(c.ok?'passed':'failed')}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.path||'')}</div></div>`).join('')||'No checks.';
    q('ticketBridgeRelated').innerHTML=(d.related_paths||[]).map(r=>`<div class="histrow ${r.exists||r.kind==='internal'?'ok':'info'}"><b>${esc(r.key||'path')}</b><div>Kind: ${esc(r.kind||'')} • Exists: ${r.exists}</div><div class=vaultpath>${esc(r.path||'')}</div></div>`).join('')||'No related paths.';
    toast('Ticket bridge loaded.');
}
function bridgeOpenRepairActions(){
    if(lastTicketBridge)recommendedRepairActionId=lastTicketBridge.safe_action_id||'';
    go('repairactions');
    setTimeout(()=>buildRepairActionPlan(),120);
    if(recommendedRepairActionId)toast('Repair Actions opened. Recommended action: '+recommendedRepairActionId+' — manual approval still required.');
    else toast('Repair Actions opened. This ticket has no mapped safe action.');
}
function sendTicketBridgeToMission(){
    if(!lastTicketBridge){toast('Load bridge first.');return;}
    let d=lastTicketBridge;
    let a=d.matching_safe_action||{};
    go('mission');
    q('input').value=`Please review this Kayock Ticket-to-Approved-Action Bridge.

Bridge:
${d.bridge_label}
Status: ${d.bridge_status}
Message: ${d.message}

Ticket:
ID: ${d.ticket_id}
Title: ${d.ticket_title}
Source: ${d.ticket_source}
Severity: ${d.ticket_severity}
Status: ${d.ticket_status}
Summary: ${d.ticket_summary}

Evidence:
${(d.evidence||[]).map(e=>'- '+e).join('\n')}

Suggested action:
${d.suggested_action}

Matching safe action:
ID: ${a.id||'none'}
Title: ${a.title||''}
Available: ${a.available}
Requires confirmation: ${a.requires_confirmation}
Risk: ${a.risk||''}
Reason: ${a.reason||''}
Writes:
${(a.writes||[]).map(w=>'- '+w).join('\n')||'- none'}

Manual next steps:
${(d.manual_next_steps||[]).map((s,i)=>`${i+1}. ${s}`).join('\n')}

Bridge checks:
${(d.detail_checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message} ${c.path||''}`).join('\n')}

Export:
${d.exported?.markdown||'No exported bridge report'}

Safety:
Read-only bridge.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether this ticket is correctly mapped to the safe action
2. Whether manual approval guardrails are sufficient
3. Whether v10.9.5 should be marked stable
4. Whether the next build should be Repair Shop Session Report.`;
    toast('Ticket bridge sent to Mission Console.');
}

let lastRepairTicketDetail=null;
function ticketDetailBadge(status){
    status=(status||'open').toLowerCase();
    let cls=['healthy','available_action','informational','needs_attention','open'].includes(status)?status:'open';
    return `<span class="ticketDetailBadge ${cls}">${esc(status.toUpperCase())}</span>`;
}
async function loadRepairTicketDetailList(){
    if(!q('repairTicketDetailStatus'))return;
    q('repairTicketDetailStatus').textContent='Loading ticket list...';
    let d=await api('/api/repair/ticket_queue',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:500,include_healthy:true})});
    if(!d?.ok){q('repairTicketDetailStatus').textContent=d?.message||'Could not load tickets.';return;}
    let all=[...(d.active_tickets||[]),...(d.healthy_tickets||[])];
    q('repairTicketDetailSelect').innerHTML=all.map(t=>`<option value="${esc(t.id||'')}">${esc((t.severity||'').toUpperCase())} — ${esc(t.id||'')} — ${esc(t.title||'')}</option>`).join('');
    if(all.length) q('repairTicketDetailQuery').value=all[0].id||'';
    q('repairTicketDetailStatus').textContent=`Loaded ${all.length} ticket(s) for detail inspection.`;
}
async function loadRepairTicketDetail(doExport=false){
    let id=q('repairTicketDetailQuery').value||q('repairTicketDetailSelect').value||'';
    q('repairTicketDetailStatus').textContent='Loading ticket detail...';
    let d=await api('/api/repair/ticket_detail',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ticket_id:id,query:id,export:doExport})});
    if(!d?.ok){q('repairTicketDetailStatus').textContent=d?.message||'Could not load ticket detail.';return;}
    lastRepairTicketDetail=d;
    let t=d.ticket||{};
    q('repairTicketDetailStatus').textContent=`Ticket detail loaded.
Ticket: ${d.ticket_id}
Status: ${d.status}
Severity: ${d.ticket_severity}
Source: ${d.ticket_source}
Detail OK: ${d.detail_ok}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('repairTicketDetailSummary').innerHTML=`${ticketDetailBadge(d.status)}
<div><b>${esc(d.ticket_title||'Ticket')}</b></div>
<div>Source: ${esc(d.ticket_source||'')} • Severity: <b>${esc(d.ticket_severity||'')}</b> • Ticket status: <b>${esc(d.ticket_status||'')}</b></div>
<div>${esc(d.ticket_summary||'')}</div>
<div class=ticketDetailGrid>
  <div class=ticketDetailMetric><div class=label>Queue Tickets</div><div class=value>${(d.queue_summary||{}).tickets||0}</div></div>
  <div class=ticketDetailMetric><div class=label>Active</div><div class=value>${(d.queue_summary||{}).active_tickets||0}</div></div>
  <div class=ticketDetailMetric><div class=label>Open</div><div class=value>${(d.queue_summary||{}).open_tickets||0}</div></div>
  <div class=ticketDetailMetric><div class=label>Errors</div><div class=value>${(d.queue_summary||{}).errors||0}</div></div>
</div>
<div class=ticketDetailPath>Source folder: ${esc(d.source_folder||'')}</div>`;
    q('repairTicketDetailEvidence').innerHTML=(d.evidence||[]).map(e=>`<div class="histrow info"><b>Evidence</b><div>${esc(e)}</div></div>`).join('')||'No evidence listed.';
    let a=d.matching_safe_action||null;
    q('repairTicketDetailAction').innerHTML=`<div><b>Suggested action</b></div><div>${esc(d.suggested_action||'None')}</div>
<div class=ticketDetailPath>Safe action ID: ${esc(d.safe_action_id||'none')}</div>
${a?`<h4>Matching Safe Action</h4><div><b>${esc(a.title||'')}</b></div><div>Available: ${a.available} • Requires confirmation: ${a.requires_confirmation} • Risk: ${esc(a.risk||'')}</div><div>${esc(a.description||'')}</div><div class=ticketDetailPath>Reason: ${esc(a.reason||'')}</div><div class=ticketDetailPath>Writes: ${(a.writes||[]).map(w=>esc(w)).join(' | ')||'none'}</div>`:'<div class=ticketDetailPath>No matching safe action required or linked.</div>'}`;
    q('repairTicketDetailRelated').innerHTML=(d.related_paths||[]).map(r=>`<div class="histrow ${r.exists?'ok':'info'}"><b>${esc(r.key||'path')}</b><div>Kind: ${esc(r.kind||'')} • Exists: ${r.exists} ${r.size?('• Size: '+r.size):''}</div><div class=ticketDetailPath>${esc(r.path||'')}</div></div>`).join('')||'No related paths.';
    q('repairTicketDetailChecks').innerHTML=(d.detail_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b>${verifyBadge(c.ok?'passed':'failed')}<div>${esc(c.message||'')}</div><div class=ticketDetailPath>${esc(c.path||'')}</div></div>`).join('')||'No detail checks.';
    toast('Repair ticket detail loaded.');
}
function sendRepairTicketDetailToMission(){
    if(!lastRepairTicketDetail){toast('Load a ticket detail first.');return;}
    let d=lastRepairTicketDetail;
    let a=d.matching_safe_action||{};
    go('mission');
    q('input').value=`Please review this Kayock Repair Ticket Detail.

Ticket:
ID: ${d.ticket_id}
Title: ${d.ticket_title}
Source: ${d.ticket_source}
Severity: ${d.ticket_severity}
Ticket status: ${d.ticket_status}
Detail status: ${d.status}
Summary: ${d.ticket_summary}

Evidence:
${(d.evidence||[]).map(e=>`- ${e}`).join('\n')}

Suggested action:
${d.suggested_action}

Safe action:
ID: ${d.safe_action_id||'none'}
Matched: ${!!d.matching_safe_action}
Available: ${d.safe_action_available}
Requires confirmation: ${d.safe_action_requires_confirmation}
Title: ${a.title||''}
Reason: ${a.reason||''}
Writes: ${(a.writes||[]).join(', ')||'none'}

Queue summary:
Tickets: ${(d.queue_summary||{}).tickets}
Active: ${(d.queue_summary||{}).active_tickets}
Open: ${(d.queue_summary||{}).open_tickets}
Errors: ${(d.queue_summary||{}).errors}

Related paths:
${(d.related_paths||[]).map(r=>`${r.key}: exists=${r.exists}, kind=${r.kind}, path=${r.path}`).join('\n')}

Detail checks:
${(d.detail_checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message} ${c.path||''}`).join('\n')}

Export:
${d.exported?.markdown||'No exported ticket detail'}

Safety:
Read-only ticket detail viewer.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether this ticket is real work, informational, or healthy
2. Whether its suggested action is safe
3. Whether the linked safe action should remain manual-only
4. Whether this ticket can be dismissed, left historical, or tracked
5. Whether v10.9.4 should be marked stable.`;
    toast('Repair ticket detail sent to Mission Console.');
}

let lastRepairTickets=null;
function ticketBadge(sev){
    sev=(sev||'info').toLowerCase();
    let cls=['critical','high','medium','low','info','healthy'].includes(sev)?sev:'info';
    return `<span class="ticketBadge ${cls}">${esc(sev.toUpperCase())}</span>`;
}
function ticketRow(t){
    return `<div class="ticketRow ${esc(t.severity||'info')}">${ticketBadge(t.severity)}<b>${esc(t.title||'Ticket')}</b>
<div>Source: ${esc(t.source||'')} • Status: <b>${esc(t.status||'')}</b> • Risk: ${esc(t.risk||'')}</div>
<div>${esc(t.summary||'')}</div>
<div class=ticketPath>Suggested: ${esc(t.suggested_action||'None')}</div>
${t.safe_action_id?`<div class=ticketPath>Safe action ID: ${esc(t.safe_action_id)}</div>`:''}
${(t.evidence||[]).length?`<div class=ticketPath>Evidence: ${(t.evidence||[]).map(e=>esc(e)).join(' | ')}</div>`:''}</div>`;
}
async function loadRepairTickets(doExport=false){
    if(!q('repairTicketStatus'))return;
    q('repairTicketStatus').textContent='Loading Repair Ticket Queue...';
    let d=await api('/api/repair/ticket_queue',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:500,export:doExport,include_healthy:true})});
    if(!d?.ok){q('repairTicketStatus').textContent=d?.message||'Could not load ticket queue.';return;}
    lastRepairTickets=d;
    let s=d.summary||{};
    q('repairTicketStatus').textContent=`Repair Ticket Queue loaded.
Health: ${d.health_label}
Tickets: ${s.tickets}
Active: ${s.active_tickets}
Open: ${s.open_tickets}
Available actions: ${s.available_action_tickets}
Informational: ${s.informational_tickets}
Errors: ${s.errors}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('repairTicketDashboard').innerHTML=`<span class="ticketBadge ${d.healthy?'healthy':'medium'}">${esc(d.health_label||'UNKNOWN')}</span>
<div class=ticketGrid>
  <div class=ticketMetric><div class=label>Tickets</div><div class=value>${s.tickets||0}</div></div>
  <div class=ticketMetric><div class=label>Active</div><div class=value>${s.active_tickets||0}</div></div>
  <div class=ticketMetric><div class=label>Open</div><div class=value>${s.open_tickets||0}</div></div>
  <div class=ticketMetric><div class=label>Available</div><div class=value>${s.available_action_tickets||0}</div></div>
  <div class=ticketMetric><div class=label>Info</div><div class=value>${s.informational_tickets||0}</div></div>
  <div class=ticketMetric><div class=label>Errors</div><div class=value>${s.errors||0}</div></div>
</div>
<div class=ticketPath>Repair Shop: ${esc(s.repair_shop_health||'')} • Recovery: ${esc(s.recovery_health||'')}</div>
<div class=ticketPath>Latest action: ${esc(s.latest_repair_action||'')} • Latest recovery: ${esc(s.latest_recovery_event||'')}</div>`;
    q('repairTicketActive').innerHTML=(d.active_tickets||[]).map(ticketRow).join('')||'No active tickets.';
    q('repairTicketActions').innerHTML=(d.available_action_tickets||[]).map(ticketRow).join('')||'No available action tickets.';
    q('repairTicketInfo').innerHTML=(d.informational_tickets||[]).map(ticketRow).join('')||'No informational tickets.';
    q('repairTicketHealthy').innerHTML=(d.healthy_tickets||[]).map(ticketRow).join('')||'No healthy checks listed.';
    toast('Repair Ticket Queue loaded.');
}
function sendRepairTicketsToMission(){
    if(!lastRepairTickets){toast('Load ticket queue first.');return;}
    let d=lastRepairTickets;
    let s=d.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Repair Ticket Queue.

Health:
${d.health_label}

Summary:
Tickets: ${s.tickets}
Active tickets: ${s.active_tickets}
Open tickets: ${s.open_tickets}
Available action tickets: ${s.available_action_tickets}
Informational tickets: ${s.informational_tickets}
Healthy tickets: ${s.healthy_tickets}
Critical: ${s.critical}
High: ${s.high}
Medium: ${s.medium}
Low: ${s.low}
Info: ${s.info}
Healthy: ${s.healthy}
Errors: ${s.errors}
Repair Shop health: ${s.repair_shop_health}
Recovery health: ${s.recovery_health}
Latest repair action: ${s.latest_repair_action}
Latest recovery event: ${s.latest_recovery_event}

Active Tickets:
${(d.active_tickets||[]).map(t=>`${t.severity}/${t.status} — ${t.source} — ${t.title} — ${t.summary} — Suggested: ${t.suggested_action||'None'} — Safe action: ${t.safe_action_id||''}`).join('\n')}

Available Action Tickets:
${(d.available_action_tickets||[]).map(t=>`${t.id}: ${t.title} — ${t.suggested_action} — ${t.safe_action_id||''}`).join('\n')}

Informational Tickets:
${(d.informational_tickets||[]).map(t=>`${t.id}: ${t.title} — ${t.summary}`).join('\n')}

Source states:
${Object.entries(d.sources||{}).map(([k,v])=>`${k}: ${v}`).join('\n')}

Export:
${d.exported?.markdown||'No exported ticket report'}

Safety:
Read-only ticket queue.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the ticket queue is accurate
2. Which tickets are informational only
3. Whether any available action should remain user-approved only
4. Whether v10.9.3 should be marked stable
5. Whether the next build should be a Ticket Detail Viewer.`;
    toast('Repair Ticket Queue sent to Mission Console.');
}

let lastRepairShopCard=null;
async function loadRepairShopDashboardCard(){
    if(!q('repairShopDashCard'))return;
    q('repairShopDashCard').textContent='Loading Repair Shop health...';
    let d=await api('/api/repair/verified_dashboard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:300})});
    if(!d?.ok){q('repairShopDashCard').textContent=d?.message||'Repair Shop health unavailable.';return;}
    lastRepairShopCard=d;
    let s=d.summary||{}, l=d.latest_action||{};
    q('repairShopDashCard').innerHTML=`<span class="repairCardBadge ${d.healthy?'healthy':'warn'}">${esc(d.health_label||'UNKNOWN')}</span>
<div>Latest action: <b>${esc(l.action_id||'none')}</b> • Verification: <b>${esc(l.verified_state||'unknown')}</b></div>
<div class=repairCardGrid>
  <div class=repairCardMetric><div class=label>Repair Logs</div><div class=value>${s.repair_logs||0}</div></div>
  <div class=repairCardMetric><div class=label>Failures</div><div class=value>${s.repair_failed||0}</div></div>
  <div class=repairCardMetric><div class=label>Verify Fail</div><div class=value>${s.verification_failed||0}</div></div>
  <div class=repairCardMetric><div class=label>Verified</div><div class=value>${s.verification_passed||0}</div></div>
  <div class=repairCardMetric><div class=label>Legacy</div><div class=value>${s.legacy_logs_without_verification||0}</div></div>
  <div class=repairCardMetric><div class=label>Safe Actions</div><div class=value>${s.safe_actions_available||0}</div></div>
</div>
<div class=repairCardPath>Created: ${esc(l.created||'')} • ${esc(l.message||'')}</div>
<div class=repairCardPath>Target: ${esc(l.target||'')}</div>
<div class=repairCardPath>Recovery: ${esc(s.recovery_health||'unknown')} • Chain: ${esc(s.recovery_chain||'unknown')}</div>`;
}
function sendRepairShopDashboardCardToMission(){
    if(!lastRepairShopCard){toast('Load Repair Shop health first.');return;}
    let d=lastRepairShopCard, s=d.summary||{}, l=d.latest_action||{};
    go('mission');
    q('input').value=`Please review this Kayock Repair Shop Command Bridge card.

Health:
${d.health_label}

Latest action:
Action ID: ${l.action_id}
Created: ${l.created}
OK: ${l.ok}
Verified state: ${l.verified_state}
Message: ${l.message}
Target: ${l.target}
Backup: ${l.backup}
Log JSON: ${l.log_json}
Log Markdown: ${l.log_markdown}

Summary:
Repair logs: ${s.repair_logs}
Repair OK: ${s.repair_ok}
Repair failures: ${s.repair_failed}
Verification passed: ${s.verification_passed}
Verification failures: ${s.verification_failed}
Legacy logs without verification: ${s.legacy_logs_without_verification}
Safe actions available: ${s.safe_actions_available}
Safe actions blocked: ${s.safe_actions_blocked}
Generated backups: ${s.generated_backups}
Backup errors: ${s.backup_errors}
Recovery health: ${s.recovery_health}
Recovery chain: ${s.recovery_chain}
Recovery attention: ${s.recovery_attention}
Recovery errors: ${s.recovery_errors}
Latest backup: ${s.latest_backup}
Latest recovery event: ${s.latest_recovery_event}

Action types:
${(d.action_types||[]).map(a=>`${a.action_id}: count ${a.count}, ok ${a.ok}, failed ${a.failed}, verified ${a.verified}, verification failed ${a.verification_failed}, legacy ${a.not_recorded}`).join('\n')}

Safety:
Read-only dashboard card.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether the Repair Shop card is accurate
2. Whether the latest verified action should be surfaced on Command Bridge
3. Whether legacy logs can remain historical
4. Whether v10.9.2 should be marked stable.`;
    toast('Repair Shop health sent to Mission Console.');
}

let lastRepairDetail=null;
function detailBadge(status){status=(status||'attention').toLowerCase();let cls=['verified','legacy_ok','failed','attention'].includes(status)?status:'attention';return `<span class="detailBadge ${cls}">${esc(status.toUpperCase())}</span>`;}
async function loadRepairDetailList(){q('repairDetailStatus').textContent='Loading RepairActions logs...';let h=await api('/api/repair/actions/history',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:1000})});if(!h?.ok){q('repairDetailStatus').textContent=h?.message||'Could not load RepairActions history.';return;}let sel=q('repairDetailSelect');sel.innerHTML=(h.logs||[]).map(l=>`<option value="${esc(l.path||'')}">${esc(l.created||'')} — ${esc(l.action_id||'unknown')} — ${esc(l.verified_state||'')}</option>`).join('');if((h.logs||[]).length){q('repairDetailPath').value=h.logs[0].path||'';}q('repairDetailStatus').textContent=`Loaded ${h.logs?.length||0} RepairActions log(s).`;}
async function loadRepairDetail(doExport=false){let path=q('repairDetailPath').value||q('repairDetailSelect').value||'';q('repairDetailStatus').textContent='Loading repair action detail...';let d=await api('/api/repair/action_detail',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path,query:path,export:doExport})});if(!d?.ok){q('repairDetailStatus').textContent=d?.message||'Could not load repair action detail.';return;}lastRepairDetail=d;let v=d.verification||{};q('repairDetailStatus').textContent=`Repair action detail loaded.
Action: ${d.action_id}
Status: ${d.status}
Action OK: ${d.action_ok}
Verified state: ${d.verified_state}
Checks: ${v.passed}/${v.checked}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;q('repairDetailSummary').innerHTML=`${detailBadge(d.status)}<div><b>${esc(d.action_id||'unknown')}</b> • ${esc(d.action_created||'')}</div><div>${esc(d.message||'')}</div><div class=detailGrid><div class=detailMetric><div class=label>Action OK</div><div class=value>${d.action_ok}</div></div><div class=detailMetric><div class=label>User Approved</div><div class=value>${d.user_approved_action}</div></div><div class=detailMetric><div class=label>Verified</div><div class=value>${d.verified_state}</div></div><div class=detailMetric><div class=label>Checks</div><div class=value>${v.passed||0}/${v.checked||0}</div></div></div><div class=vaultpath>JSON: ${esc((d.log||{}).json||'')}</div><div class=vaultpath>Markdown: ${esc((d.log||{}).markdown||'')}</div>`;q('repairDetailVerification').innerHTML=(v.checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b>${verifyBadge(c.ok?'passed':'failed')}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.path||'')}</div></div>`).join('')||`<div class="histrow info"><b>Legacy log</b><div>${esc(v.message||'No verification recorded.')}</div></div>`;let t=d.target||{},b=d.backup||{};q('repairDetailFiles').innerHTML=`<h4>Target</h4><div class=vaultpath>${esc(t.path||'')}</div><div>Exists: ${t.exists} • Inside root: ${t.inside_root} • Size: ${t.size??''} • Modified: ${esc(t.modified||'')}</div><div class=detailHash>SHA256: ${esc(t.sha256||'')}</div><h4>Backup</h4><div class=vaultpath>${esc(b.path||'')}</div><div>Exists: ${b.exists} • Inside root: ${b.inside_root} • Size: ${b.size??''} • Modified: ${esc(b.modified||'')}</div><div class=detailHash>SHA256: ${esc(b.sha256||'')}</div>`;q('repairDetailRelated').innerHTML=(d.related_paths||[]).map(r=>`<div class="histrow ${r.exists?'ok':'info'}"><b>${esc(r.key||'path')}</b><div>Kind: ${esc(r.kind||'')} • Exists: ${r.exists}</div><div class=vaultpath>${esc(r.path||'')}</div></div>`).join('')||'No related paths.';q('repairDetailChecks').innerHTML=(d.detail_checks||[]).map(c=>`<div class="histrow ${c.ok?'ok':'fail'}"><b>${esc(c.id||'check')}</b>${verifyBadge(c.ok?'passed':'failed')}<div>${esc(c.message||'')}</div><div class=vaultpath>${esc(c.path||'')}</div></div>`).join('')||'No detail checks.';toast('Repair action detail loaded.');}
function sendRepairDetailToMission(){if(!lastRepairDetail){toast('Load a detail first.');return;}let d=lastRepairDetail,v=d.verification||{},t=d.target||{},b=d.backup||{};go('mission');q('input').value=`Please review this Kayock Repair Action Detail.

Action:
${d.action_id}
Created: ${d.action_created}
Status: ${d.status}
Action OK: ${d.action_ok}
Verified state: ${d.verified_state}
Message: ${d.message}

Log:
JSON: ${(d.log||{}).json}
Markdown: ${(d.log||{}).markdown}

Target:
Path: ${t.path}
Exists: ${t.exists}
Inside root: ${t.inside_root}
Size: ${t.size}
Modified: ${t.modified}
SHA256: ${t.sha256}

Backup:
Path: ${b.path}
Exists: ${b.exists}
Inside root: ${b.inside_root}
Size: ${b.size}
Modified: ${b.modified}
SHA256: ${b.sha256}

Verification:
Recorded: ${v.recorded}
OK: ${v.ok}
Checked: ${v.checked}
Passed: ${v.passed}
Failed: ${v.failed}
Message: ${v.message}

Verification checks:
${(v.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message} ${c.path||''}`).join('\n')}

Detail checks:
${(d.detail_checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.id}: ${c.message} ${c.path||''}`).join('\n')}

Related paths:
${(d.related_paths||[]).map(r=>`${r.key}: exists=${r.exists}, kind=${r.kind}, path=${r.path}`).join('\n')}

Export:
${d.exported?.markdown||'No exported detail report'}

Safety:
Read-only detail viewer.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine whether this repair action detail is healthy and whether any legacy log needs migration.`;toast('Repair action detail sent to Mission Console.');}

let lastRepairOps=null;
function repairShopBadge(ok,label){
    return `<span class="repairShopBadge ${ok?'healthy':'warn'}">${esc(label||'UNKNOWN')}</span>`;
}
function actionPill(available){
    return `<span class="actionPill ${available?'available':'blocked'}">${available?'AVAILABLE':'BLOCKED'}</span>`;
}
async function loadRepairOps(doExport=false){
    if(!q('repairOpsStatus'))return;
    q('repairOpsStatus').textContent='Loading Repair Shop operations dashboard...';
    let d=await api('/api/repair/ops_dashboard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:300,export:doExport})});
    if(!d?.ok){
        q('repairOpsStatus').textContent=d?.message||'Could not load Repair Shop dashboard.';
        return;
    }
    lastRepairOps=d;
    let s=d.summary||{};
    q('repairOpsStatus').textContent=`Repair Shop loaded.
Health: ${d.health_label}
Repair logs: ${s.repair_logs}
OK: ${s.repair_ok}
Failed: ${s.repair_failed}
Verification passed: ${s.verification_passed}
Verification failed: ${s.verification_failed}
Available actions: ${s.available_actions}
Generated backups: ${s.generated_backups}
Recovery: ${s.recovery_health}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('repairOpsDashboard').innerHTML=`${repairShopBadge(d.healthy,d.health_label)}
<div class=repairShopGrid>
  <div class=repairShopMetric><div class=label>Repair Logs</div><div class=value>${s.repair_logs||0}</div></div>
  <div class=repairShopMetric><div class=label>OK</div><div class=value>${s.repair_ok||0}</div></div>
  <div class=repairShopMetric><div class=label>Failed</div><div class=value>${s.repair_failed||0}</div></div>
  <div class=repairShopMetric><div class=label>Verified</div><div class=value>${s.verification_passed||0}</div></div>
  <div class=repairShopMetric><div class=label>Verify Failed</div><div class=value>${s.verification_failed||0}</div></div>
  <div class=repairShopMetric><div class=label>Legacy Logs</div><div class=value>${s.legacy_logs_without_verification||0}</div></div>
  <div class=repairShopMetric><div class=label>Available Actions</div><div class=value>${s.available_actions||0}</div></div>
  <div class=repairShopMetric><div class=label>Backups</div><div class=value>${s.generated_backups||0}</div></div>
</div>
<div class=repairShopPath>Latest action: ${esc(s.latest_action||'none')} ${s.latest_action_created?('• '+esc(s.latest_action_created)) : ''}</div>
<div class=repairShopPath>Recovery: ${esc(s.recovery_health||'unknown')} • Chain: ${esc(s.recovery_chain||'unknown')}</div>`;
    q('repairOpsActions').innerHTML=(d.safe_actions||[]).map(a=>`<div class="histrow ${a.available?'ok':'info'}"><b>${esc(a.title)}</b>${actionPill(a.available)}
<div>ID: <code>${esc(a.id)}</code> | Risk: ${esc(a.risk||'')}</div>
<div>${esc(a.description||'')}</div>
<div class=vaultpath>Reason: ${esc(a.reason||'')}</div>
<div class=vaultpath>Writes: ${(a.writes||[]).map(w=>esc(w)).join(' | ')||'none'}</div>
</div>`).join('')||'No safe actions loaded.';
    q('repairOpsByAction').innerHTML=(d.history_by_action||[]).map(a=>`<div class="histrow info"><b>${esc(a.action_id||'unknown')}</b>
<div>Count: ${a.count} | OK: ${a.ok} | Failed: ${a.failed} | Verified: ${a.verified} | Verify failed: ${a.verification_failed} | Legacy: ${a.not_recorded}</div>
<div class=vaultpath>Last: ${esc(a.last_created||'')}</div></div>`).join('')||'No action types found.';
    q('repairOpsRecent').innerHTML=(d.recent_logs||[]).map(l=>`<div class="histrow ${l.ok?'ok':'fail'}"><b>${esc(l.created||'')} — ${esc(l.action_id||'unknown')}</b>${verifyBadge(l.verified_state)}
<div>${esc(l.message||'')}</div>
<div class=vaultpath>Target: ${esc(l.target||'')}</div>
<div class=vaultpath>Backup: ${esc(l.backup||'')}</div>
<div class=vaultpath>Log: ${esc(l.markdown||l.path||'')}</div></div>`).join('')||'No recent logs.';
    q('repairOpsBackupRecovery').innerHTML=`<div class=repairShopGrid>
  <div class=repairShopMetric><div class=label>Generated Backups</div><div class=value>${s.generated_backups||0}</div></div>
  <div class=repairShopMetric><div class=label>Associated</div><div class=value>${s.associated_backups||0}</div></div>
  <div class=repairShopMetric><div class=label>Verified Backups</div><div class=value>${s.verified_backups||0}</div></div>
  <div class=repairShopMetric><div class=label>Backup Errors</div><div class=value>${s.backup_errors||0}</div></div>
  <div class=repairShopMetric><div class=label>Recovery Attention</div><div class=value>${s.recovery_attention||0}</div></div>
  <div class=repairShopMetric><div class=label>Recovery Errors</div><div class=value>${s.recovery_errors||0}</div></div>
</div>
<div class=repairShopPath>Latest backup: ${esc(s.latest_backup||'none')}</div>
<div class=repairShopPath>Latest recovery event: ${esc(s.latest_recovery_event||'none')} ${s.latest_recovery_created?('• '+esc(s.latest_recovery_created)) : ''}</div>`;
    toast('Repair Shop dashboard loaded.');
}
function sendRepairOpsToMission(){
    if(!lastRepairOps){
        toast('Load Repair Shop first.');
        return;
    }
    let s=lastRepairOps.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Repair Shop Operations Dashboard.

Health:
${lastRepairOps.health_label}

Summary:
Repair logs: ${s.repair_logs}
Repair OK: ${s.repair_ok}
Repair failed: ${s.repair_failed}
User approved: ${s.user_approved}
Verification passed: ${s.verification_passed}
Verification failed: ${s.verification_failed}
Legacy logs without verification: ${s.legacy_logs_without_verification}
Available safe actions: ${s.available_actions}
Blocked safe actions: ${s.blocked_actions}
Generated backups: ${s.generated_backups}
Associated backups: ${s.associated_backups}
Verified backups: ${s.verified_backups}
Backup errors: ${s.backup_errors}
Recovery health: ${s.recovery_health}
Recovery chain: ${s.recovery_chain}
Recovery attention: ${s.recovery_attention}
Recovery errors: ${s.recovery_errors}
Latest action: ${s.latest_action}
Latest action created: ${s.latest_action_created}
Latest backup: ${s.latest_backup}
Latest recovery event: ${s.latest_recovery_event}

Safe Actions:
${(lastRepairOps.safe_actions||[]).map(a=>`${a.available?'AVAILABLE':'BLOCKED'} — ${a.id} — ${a.title} — ${a.reason}`).join('\n')}

Action Types:
${(lastRepairOps.history_by_action||[]).map(a=>`${a.action_id}: count ${a.count}, ok ${a.ok}, failed ${a.failed}, verified ${a.verified}, verification failed ${a.verification_failed}, legacy ${a.not_recorded}`).join('\n')}

Recent Logs:
${(lastRepairOps.recent_logs||[]).map(l=>`${l.created} — ${l.action_id} — ok=${l.ok} — verified=${l.verified_state} — ${l.message} — target=${l.target} — backup=${l.backup}`).join('\n')}

Export:
${lastRepairOps.exported?.markdown||'No exported Repair Shop report'}

Safety:
Read-only operations dashboard.
No repair action.
No restore.
No rollback.
No overwrite.
No copy-back.
No delete.
No install.
No model cleanup.

Please determine:
1. Whether Repair Shop should be marked healthy
2. Whether any old legacy logs need migration or can remain as historical
3. Whether safe actions should stay as currently scoped
4. Whether the next Repair Shop build should be an action detail viewer or a verified-action dashboard card.`;
    toast('Repair Shop sent to Mission Console.');
}

let lastRepairHistory=null;
function verifyBadge(state){
    if(state==='passed')return '<span class="verifybadge pass">VERIFIED</span>';
    if(state==='failed')return '<span class="verifybadge fail">VERIFY FAILED</span>';
    return '<span class="verifybadge none">OLDER LOG</span>';
}
function verificationLines(v){
    if(!v || !v.checks)return '<div class=small>Verification: not recorded in this older log.</div>';
    return `<div class=small>${esc(v.message||'')}</div>`+(v.checks||[]).map(c=>`<div class=checkline>${c.ok?'✅':'❌'} ${esc(c.id||'check')} — ${esc(c.message||'')}</div>`).join('');
}
async function loadRepairHistory(doExport=false){
    let action_filter=q('repairHistoryFilter').value||'';
    let limit=parseInt(q('repairHistoryLimit').value||'200');
    q('repairHistoryStatus').textContent='Loading repair action history...';
    let d=await api('/api/repair/actions/history',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action_filter,limit,export:doExport})});
    if(!d?.ok){
        q('repairHistoryStatus').textContent=d?.message||'Could not load repair history.';
        return;
    }
    lastRepairHistory=d;
    let s=d.summary||{};
    q('repairHistoryStatus').textContent=`Repair history loaded.
Logs: ${s.logs}
OK: ${s.ok}
Failed: ${s.failed}
User approved: ${s.user_approved}
Verification passed: ${s.verification_passed||0}
Verification failed: ${s.verification_failed||0}
Older logs without verification: ${s.verification_not_recorded||0}
Last action: ${s.last_action||'none'}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('repairHistoryDashboard').innerHTML=`<div class=historygrid>
        <div class=historymetric><div class=label>Logs</div><div class=value>${s.logs||0}</div></div>
        <div class=historymetric><div class=label>OK</div><div class=value>${s.ok||0}</div></div>
        <div class=historymetric><div class=label>Failed</div><div class=value>${s.failed||0}</div></div>
        <div class=historymetric><div class=label>Approved</div><div class=value>${s.user_approved||0}</div></div>
        <div class=historymetric><div class=label>Verified</div><div class=value>${s.verification_passed||0}</div></div>
        <div class=historymetric><div class=label>Verify Failed</div><div class=value>${s.verification_failed||0}</div></div>
        <div class=historymetric><div class=label>Older Logs</div><div class=value>${s.verification_not_recorded||0}</div></div>
        <div class=historymetric><div class=label>Errors</div><div class=value>${s.errors||0}</div></div>
    </div><div class=status>Last action: ${esc(s.last_action||'none')} | ${esc(s.last_created||'')}</div>`;
    q('repairHistoryByAction').innerHTML=(d.by_action||[]).map(a=>`<div class="histrow info"><b>${esc(a.action_id)}</b><div>Count: ${a.count} | OK: ${a.ok} | Failed: ${a.failed}</div><div>Verified: ${a.verified||0} | Verification failed: ${a.verification_failed||0} | Older logs: ${a.not_recorded||0}</div><div class=small>Last: ${esc(a.last_created||'')}</div></div>`).join('')||'No action summary yet.';
    q('repairHistoryLogs').innerHTML=(d.logs||[]).map(l=>`<div class="histrow ${l.ok?'ok':'fail'}"><b>${l.ok?'OK':'FAILED'} — ${esc(l.action_id)}</b>${verifyBadge(l.verified_state)}
<div>${esc(l.message||'')}</div>
<div class=small>Created: ${esc(l.created||'')} | Approved: ${l.user_approved_action} | Dry run: ${l.dry_run}</div>
<div class=small>Target: ${esc(l.target||'')}</div>
<div class=small>Backup: ${esc(l.backup||'')}</div>
<div class=small>Log: ${esc(l.path||'')}</div>
${verificationLines(l.verification)}</div>`).join('')||'No logs found.';
    toast('Repair history loaded.');
}
function sendRepairHistoryToMission(){
    if(!lastRepairHistory){
        toast('Load repair history first.');
        return;
    }
    let s=lastRepairHistory.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Repair Bay Action History.

This is an audit trail review. It is read-only.

Summary:
Logs: ${s.logs}
OK: ${s.ok}
Failed: ${s.failed}
Dry runs: ${s.dry_runs}
User approved: ${s.user_approved}
Action types: ${s.actions}
Parse errors: ${s.errors}
Verification passed: ${s.verification_passed||0}
Verification failed: ${s.verification_failed||0}
Older logs without verification: ${s.verification_not_recorded||0}
Last action: ${s.last_action}
Last created: ${s.last_created}

History Report:
${lastRepairHistory.exported?.markdown||'No exported history report path'}

By Action:
${(lastRepairHistory.by_action||[]).map(a=>`${a.action_id}: count=${a.count}, ok=${a.ok}, failed=${a.failed}, verified=${a.verified||0}, verification_failed=${a.verification_failed||0}, older=${a.not_recorded||0}, last=${a.last_created}`).join('\n')}

Recent Logs:
${(lastRepairHistory.logs||[]).slice(0,20).map(l=>`${l.ok?'OK':'FAILED'} — ${l.action_id}
Created: ${l.created}
Verification: ${l.verified_state}
Verification message: ${(l.verification||{}).message||'not recorded'}
Message: ${l.message}
Target: ${l.target}
Backup: ${l.backup}
Log: ${l.path}`).join('\n\n')}

Please identify:
1. Whether the Repair Bay audit trail is trustworthy
2. Any failed or suspicious actions
3. Whether backups, logs, and post-action verification are sufficient
4. What next Repair Bay action type should be added
5. Whether it is safe to expand beyond docs/manifests/folders.`;
    toast('Repair history sent to Mission Console.');
}

let lastRepairPlan=null;
let lastRepairResult=null;
async function buildRepairActionPlan(){
    q('repairActionStatus').textContent='Building repair action plan...';
    let d=await api('/api/repair/actions/plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
    if(!d?.ok){
        q('repairActionStatus').textContent=d?.message||'Could not build repair action plan.';
        return;
    }
    lastRepairPlan=d;
    let s=d.summary||{};
    q('repairActionStatus').textContent=`Repair action plan ready.
Actions: ${s.actions}
Available: ${s.available}
Blocked: ${s.blocked}
Low risk: ${s.low_risk}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('repairActionPlan').innerHTML=(d.actions||[]).map(a=>`<div class="repairrow ${a.available?'available':'blocked'} ${(recommendedRepairActionId&&a.id===recommendedRepairActionId)?'recommended':''}">${(recommendedRepairActionId&&a.id===recommendedRepairActionId)?'<div class=recommendTag>RECOMMENDED FROM TICKET — MANUAL APPROVAL STILL REQUIRED</div>':''}<div class=repairtitle>${esc(a.title)}</div>
<div class=risk>ID: ${esc(a.id)} | Risk: ${esc(a.risk)} | Available: ${a.available}</div>
<div>${esc(a.description||'')}</div>
<div class=small>${esc(a.reason||'')}</div>
<div class=small>Writes: ${(a.writes||[]).map(x=>esc(x)).join('<br>')||'none'}</div>
${a.available?`<button onclick="applyRepairAction('${esc(a.id)}')">Apply This Action</button>`:''}</div>`).join('');
    if(recommendedRepairActionId){q('repairActionStatus').textContent += `
Recommended from Ticket Bridge: ${recommendedRepairActionId}
Manual approval is still required.`;}
    toast('Repair action plan built.');
}
async function applyRepairAction(actionId){
    if(!actionId){
        toast('Missing action id.');
        return;
    }
    let ok=confirm(`Apply Repair Bay action now?\n\n${actionId}\n\nThis may write files, but will create logs/backups when needed.`);
    if(!ok)return;
    let d=await api('/api/repair/actions/apply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action_id:actionId,confirm:'YES'})});
    lastRepairResult=d;
    q('repairActionResult').textContent=JSON.stringify(d,null,2);
    let v=d?.verification||{};
    if(v.message){
        q('repairActionResult').textContent+='\n\nPOST-ACTION VERIFICATION:\n'+v.message;
    }
    if(d?.ok){
        toast('Repair action applied and verified.');
        buildRepairActionPlan();
    }else{
        toast('Repair action failed, was blocked, or verification failed.');
    }
}
function sendRepairActionPlanToMission(){
    if(!lastRepairPlan){
        toast('Build a repair action plan first.');
        return;
    }
    go('mission');
    q('input').value=`Please review this Kayock User-Approved Repair Bay Action Plan.

This is the first action mode. Actions require user confirmation and write repair logs.

Summary:
Actions: ${lastRepairPlan.summary.actions}
Available: ${lastRepairPlan.summary.available}
Blocked: ${lastRepairPlan.summary.blocked}
Low risk: ${lastRepairPlan.summary.low_risk}

Plan Report:
${lastRepairPlan.exported?.markdown||'No exported plan path'}

Safety Rules:
${(lastRepairPlan.rules||[]).map(x=>'- '+x).join('\n')}

Actions:
${(lastRepairPlan.actions||[]).map(a=>`${a.available?'AVAILABLE':'BLOCKED'} — ${a.title}
ID: ${a.id}
Risk: ${a.risk}
Reason: ${a.reason}
Writes:
${(a.writes||[]).map(x=>'- '+x).join('\n')||'- none'}
Description: ${a.description}`).join('\n\n')}

Please identify:
1. Whether these actions are safe enough for first Repair Bay action mode
2. Which action should be tested first
3. Any action that should remain blocked
4. Whether more guardrails are needed before expanding Repair Bay.`;
    toast('Repair action plan sent to Mission Console.');
}

let lastModelTruth=null;
async function runModelDuplicateTruth(){
    q('modelTruthStatus').textContent='Running model duplicate truth check...';
    let d=await api('/api/models/duplicates',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({export:true})});
    if(!d){
        q('modelTruthStatus').textContent='Model duplicate truth check failed: no response.';
        return;
    }
    lastModelTruth=d;
    let s=d.summary||{};
    q('modelTruthStatus').textContent=`Model Duplicate Truth Check complete.
Physical files: ${s.physical_model_files}
Unique model keys: ${s.unique_model_keys}
Skipped alias dirs: ${s.skipped_alias_dirs}
True duplicate groups: ${s.true_duplicate_groups}
True duplicate copies: ${s.true_duplicate_copies}
Estimated duplicate space: ${s.estimated_true_duplicate_bytes_human}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('modelTruthDashboard').innerHTML=`<div class=modelgrid>
        <div class=modelmetric><div class=label>Physical Files</div><div class=value>${s.physical_model_files||0}</div></div>
        <div class=modelmetric><div class=label>Unique Models</div><div class=value>${s.unique_model_keys||0}</div></div>
        <div class=modelmetric><div class=label>Alias Dirs</div><div class=value>${s.skipped_alias_dirs||0}</div></div>
        <div class=modelmetric><div class=label>True Dup Groups</div><div class=value>${s.true_duplicate_groups||0}</div></div>
        <div class=modelmetric><div class=label>True Dup Copies</div><div class=value>${s.true_duplicate_copies||0}</div></div>
    </div><div class=status>Estimated true duplicate space: ${esc(s.estimated_true_duplicate_bytes_human||'0 B')}</div>`;
    q('modelCleanupPlan').innerHTML=(d.cleanup_plan||[]).map(p=>`<div class="modelrow ${esc(p.priority||'info')}"><b>${esc((p.priority||'info').toUpperCase())}: ${esc(p.action||'')}</b>
<div>${esc(p.reason||'')}</div>
${p.estimated_space_recoverable_human?`<div class=small>Estimated recoverable: ${esc(p.estimated_space_recoverable_human)}</div>`:''}</div>`).join('');
    let parts=[];
    if((d.skipped_alias_dirs||[]).length){
        parts.push('<h4>Folder aliases skipped</h4>'+d.skipped_alias_dirs.map(x=>`<div class="modelrow info"><b>${esc(x.path)}</b><div class=small>Alias of: ${esc(x.alias_of||'')}</div></div>`).join(''));
    }
    if((d.true_duplicates||[]).length){
        parts.push('<h4>Confirmed duplicate candidates</h4>'+d.true_duplicates.map(g=>`<div class="modelrow review"><b>${esc(g.name)} — ${esc(g.size_human||'')}</b><div>Suggested keep: ${esc(g.kept_suggestion?.path||'')}</div><div class=small>${(g.duplicate_candidates||[]).map(c=>esc(c.path)).join('<br>')}</div></div>`).join(''));
    }else{
        parts.push('<div class="modelrow safe"><b>No confirmed duplicate files</b><div>After canonical folder and physical path detection, no true duplicate GGUF files require deletion planning.</div></div>');
    }
    q('modelTruthDetails').innerHTML=parts.join('');
    toast('Model duplicate truth check complete.');
}
function sendModelDuplicateTruthToMission(){
    if(!lastModelTruth){
        toast('Run model duplicate truth check first.');
        return;
    }
    let s=lastModelTruth.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Model Duplicate Truth Check and cleanup plan.

This was report-only. It did not delete, move, rename, or modify model files.

Summary:
Tracked model dirs: ${s.tracked_model_dirs}
Existing model dirs: ${s.existing_model_dirs}
Scanned canonical dirs: ${s.scanned_canonical_dirs}
Skipped alias dirs: ${s.skipped_alias_dirs}
Raw scan models: ${s.raw_scan_models}
Physical model files: ${s.physical_model_files}
Unique model keys: ${s.unique_model_keys}
True duplicate groups: ${s.true_duplicate_groups}
True duplicate copies: ${s.true_duplicate_copies}
Estimated duplicate space: ${s.estimated_true_duplicate_bytes_human}
Scan errors: ${s.scan_errors}

Report Path:
${lastModelTruth.exported?.markdown||'No exported markdown path'}

Cleanup Plan:
${(lastModelTruth.cleanup_plan||[]).map(p=>`${(p.priority||'info').toUpperCase()} — ${p.action}
${p.reason}
${p.estimated_space_recoverable_human?`Estimated recoverable: ${p.estimated_space_recoverable_human}`:''}`).join('\n\n')}

Please identify:
1. Whether duplicate detection is now trustworthy
2. Whether Models/models were aliases or true duplicates
3. Whether any cleanup action is safe to add later
4. What the first user-approved cleanup action should be
5. Whether Repair Bay can proceed to approved actions after this.`;
    toast('Model cleanup plan sent to Mission Console.');
}

let lastPortableReadiness=null;
async function runPortableReadiness(){
    q('portableStatus').textContent='Running runtime lock and portable readiness report...';
    let d=await api('/api/portable/readiness',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({export:true})});
    if(!d){
        q('portableStatus').textContent='Portable readiness failed: no response.';
        return;
    }
    lastPortableReadiness=d;
    let s=d.summary||{};
    q('portableStatus').textContent=`Portable Readiness complete.
Score: ${s.score}/100
Readiness: ${s.readiness}
Runtime locked: ${s.runtime_locked}
Blockers: ${s.blockers}
Warnings: ${s.warnings}
Unique GGUF models: ${s.unique_gguf_models}
Duplicate GGUF copies: ${s.duplicate_gguf_copies}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('portableDashboard').innerHTML=`<div class=portablegrid>
        <div class=portablemetric><div class=label>Score</div><div class=value>${s.score||0}</div></div>
        <div class=portablemetric><div class=label>Blockers</div><div class=value>${s.blockers||0}</div></div>
        <div class=portablemetric><div class=label>Warnings</div><div class=value>${s.warnings||0}</div></div>
        <div class=portablemetric><div class=label>Runtime Lock</div><div class=value>${s.runtime_locked?'YES':'NO'}</div></div>
        <div class=portablemetric><div class=label>Unique Models</div><div class=value>${s.unique_gguf_models||0}</div></div>
        <div class=portablemetric><div class=label>Duplicates</div><div class=value>${s.duplicate_gguf_copies||0}</div></div>
        <div class=portablemetric><div class=label>Optional Tools</div><div class=value>${s.optional_tools_available||0}/${s.optional_tools_total||0}</div></div>
    </div><div class=status>${esc(s.readiness||'')}</div>`;
    let bw=[];
    if((d.blockers||[]).length){
        bw.push('<h4>Blockers</h4>'+d.blockers.map(b=>`<div class="portrow fail"><b>${esc(b.name)}</b><div>${esc(b.message||'')}</div></div>`).join(''));
    }else{
        bw.push('<div class="portrow pass"><b>No blockers</b><div>No USB portability blockers found for current web bridge workflows.</div></div>');
    }
    if((d.warnings||[]).length){
        bw.push('<h4>Warnings</h4>'+d.warnings.map(w=>`<div class="portrow warn"><b>${esc(w.name)}</b><div>${esc(w.message||'')}</div></div>`).join(''));
    }
    q('portableBlockers').innerHTML=bw.join('');
    q('portableDetails').innerHTML=(d.checks||[]).map(c=>{
        let cls=c.ok?'pass':(c.blocker?'fail':'warn');
        let status=c.ok?'PASS':(c.blocker?'BLOCKER':'WARNING');
        return `<div class="portrow ${cls}"><b>${status} — ${esc(c.name)}</b>
<div>${esc(c.message||'')}</div>
<div class=small>Weight: ${c.weight} | Blocker: ${c.blocker} | Warning: ${c.warning}</div></div>`;
    }).join('');
    toast('Portable readiness complete.');
}
function sendPortableReadinessToMission(){
    if(!lastPortableReadiness){
        toast('Run portable readiness first.');
        return;
    }
    let s=lastPortableReadiness.summary||{};
    go('mission');
    q('input').value=`Please review this Kayock Runtime Lock + Portable Readiness report.

This was report-only. It did not install, repair, delete, or modify files.

Summary:
Portable readiness score: ${s.score}/100
Readiness: ${s.readiness}
Runtime locked: ${s.runtime_locked}
Current Python: ${s.current_python}
Expected Python: ${s.expected_python}
Blockers: ${s.blockers}
Warnings: ${s.warnings}
GGUF files: ${s.gguf_files}
Unique GGUF models: ${s.unique_gguf_models}
Duplicate GGUF copies: ${s.duplicate_gguf_copies}
Optional tools: ${s.optional_tools_available}/${s.optional_tools_total}

Report Path:
${lastPortableReadiness.exported?.markdown||'No exported markdown path'}

Checks:
${(lastPortableReadiness.checks||[]).map(c=>`${c.ok?'PASS':(c.blocker?'BLOCKER':'WARNING')} — ${c.name}
${c.message}`).join('\n\n')}

Please identify:
1. USB workstation readiness
2. Remaining portability blockers
3. Duplicate model/folder cleanup recommendations
4. Optional dependency priorities
5. Whether we are ready to begin user-approved Repair Bay actions.`;
    toast('Portable readiness sent to Mission Console.');
}

let lastEnvVerification=null;
async function runEnvVerification(){
    q('envStatus').textContent='Running report-only environment verification...';
    let d=await api('/api/env/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({export:true})});
    if(!d){
        q('envStatus').textContent='Environment verification failed: no response.';
        return;
    }
    lastEnvVerification=d;
    let s=d.summary||{};
    q('envStatus').textContent=`Environment Verification complete.
Passed: ${s.passed}/${s.checks}
Problems: ${s.problems}
Optional tools: ${s.optional_tools_available}/${s.optional_tools_total}
GGUF models: ${s.gguf_models}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('envDashboard').innerHTML=`<div class=envgrid>
        <div class=envmetric><div class=label>Checks</div><div class=value>${s.checks||0}</div></div>
        <div class=envmetric><div class=label>Passed</div><div class=value>${s.passed||0}</div></div>
        <div class=envmetric><div class=label>Problems</div><div class=value>${s.problems||0}</div></div>
        <div class=envmetric><div class=label>Optional Tools</div><div class=value>${s.optional_tools_available||0}/${s.optional_tools_total||0}</div></div>
        <div class=envmetric><div class=label>GGUF Models</div><div class=value>${s.gguf_models||0}</div></div>
    </div>`;
    q('envDetails').innerHTML=(d.checks||[]).map(c=>{
        let cls=c.ok?'pass':(c.optional?'optional':'fail');
        let status=c.ok?'PASS':(c.optional?'OPTIONAL':'FAIL');
        return `<div class="envrow ${cls}"><b>${status} — ${esc(c.name)}</b>
<div>${esc(c.message||'')}</div>
<div class=small>Severity: ${esc(c.severity||'info')} | Optional: ${c.optional}</div></div>`;
    }).join('');
    toast('Environment verification complete.');
}
function sendEnvVerificationToMission(){
    if(!lastEnvVerification){
        toast('Run environment verification first.');
        return;
    }
    go('mission');
    q('input').value=`Please review this Kayock Environment + Dependency Verification report.

This was report-only. It did not install packages, update dependencies, edit files, or run repair actions.

Summary:
Checks: ${lastEnvVerification.summary.checks}
Passed: ${lastEnvVerification.summary.passed}
Problems: ${lastEnvVerification.summary.problems}
Optional tools: ${lastEnvVerification.summary.optional_tools_available}/${lastEnvVerification.summary.optional_tools_total}
GGUF models: ${lastEnvVerification.summary.gguf_models}

Report Path:
${lastEnvVerification.exported?.markdown||'No exported markdown path'}

Checks:
${(lastEnvVerification.checks||[]).map(c=>`${c.ok?'PASS':(c.optional?'OPTIONAL':'FAIL')} — ${c.name}
${c.message}`).join('\n\n')}

Please identify:
1. Environment readiness
2. Missing optional tools worth installing later
3. Unsafe assumptions
4. Dependency risks
5. Next Repair Bay verification feature to add before approved actions.`;
    toast('Environment report sent to Mission Console.');
}

let lastBuildVerification=null;
async function runBuildVerification(){
    q('buildStatus').textContent='Running report-only build verification...';
    let d=await api('/api/build/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({export:true})});
    if(!d){
        q('buildStatus').textContent='Build verification failed: no response.';
        return;
    }
    lastBuildVerification=d;
    let s=d.summary||{};
    q('buildStatus').textContent=`Build Verification Lite complete.
Passed: ${s.passed}/${s.checks}
Problems: ${s.problems}
Python files: ${s.python_files}
${d.exported?`Markdown: ${d.exported.markdown}
JSON: ${d.exported.json}`:''}`;
    q('buildDashboard').innerHTML=`<div class=buildgrid>
        <div class=buildmetric><div class=label>Checks</div><div class=value>${s.checks||0}</div></div>
        <div class=buildmetric><div class=label>Passed</div><div class=value>${s.passed||0}</div></div>
        <div class=buildmetric><div class=label>Problems</div><div class=value>${s.problems||0}</div></div>
        <div class=buildmetric><div class=label>Python Files</div><div class=value>${s.python_files||0}</div></div>
    </div>`;
    q('buildDetails').innerHTML=(d.checks||[]).map(c=>`<div class="checkrow ${c.ok?'pass':'fail'}"><b>${c.ok?'PASS':'FAIL'} — ${esc(c.name)}</b>
<div>${esc(c.message||'')}</div>
<div class=small>Severity: ${esc(c.severity||'info')}</div></div>`).join('');
    toast('Build verification complete.');
}
function sendBuildVerificationToMission(){
    if(!lastBuildVerification){
        toast('Run build verification first.');
        return;
    }
    go('mission');
    q('input').value=`Please review this Kayock Build Verification Lite report.

This was report-only. It did not install packages, edit files, or run repair actions.

Summary:
Checks: ${lastBuildVerification.summary.checks}
Passed: ${lastBuildVerification.summary.passed}
Problems: ${lastBuildVerification.summary.problems}
Python files checked: ${lastBuildVerification.summary.python_files}

Report Path:
${lastBuildVerification.exported?.markdown||'No exported markdown path'}

Checks:
${(lastBuildVerification.checks||[]).map(c=>`${c.ok?'PASS':'FAIL'} — ${c.name}
${c.message}`).join('\n\n')}

Please identify:
1. Build readiness
2. Any unsafe assumptions
3. Missing checks
4. Next Repair Bay feature to add
5. Whether this should stay report-only or gain a user-approved action.`;
    toast('Build verification sent to Mission Console.');
}

let projectDocsStatusData=null;
async function refreshProjectDocsStatus(){
    let d=await api('/api/project_docs/status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
    if(!d?.ok){
        q('docsStatus').textContent=d?.message||'Docs status failed.';
        return;
    }
    projectDocsStatusData=d;
    let s=d.summary||{};
    q('docsStatus').innerHTML=`<div class=docstatusgrid>
        <div class=docstat><div class=label>Tracked Docs</div><div class=value>${s.docs||0}</div></div>
        <div class=docstat><div class=label>Present</div><div class=value>${s.present||0}</div></div>
        <div class=docstat><div class=label>Valid</div><div class=value>${s.valid||0}</div></div>
        <div class=docstat><div class=label>Problems</div><div class=value>${s.problems||0}</div></div>
        <div class=docstat><div class=label>Backups</div><div class=value>${s.backup_count||0}</div></div>
    </div>
    ${(d.docs||[]).map(x=>`<div class="docrow ${x.exists&&x.valid?'good':'bad'}"><b>${esc(x.label)}</b>
<div class=small>${esc(x.relative||x.path)}</div>
<div class=small>Exists: ${x.exists} | Valid: ${x.valid} | Size: ${x.size} | Modified: ${esc(x.modified||'')}</div>
<div>${esc(x.message||'')}</div></div>`).join('')}`;
    toast('Project docs status refreshed.');
}
async function loadGeneratedFileToPreview(path){
    let d=await api('/api/generated/read',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path})});
    if(d?.ok){
        generatedPreviewData={target:d.path,content:d.content,exists:true};
        q('generatedPreview').textContent=d.content||'';
        toast('Generated file loaded into preview.');
    }else{
        q('generatedPreview').textContent=d?.message||'Could not load generated file.';
    }
}
function loadRootManifestFile(){
    loadGeneratedFileToPreview('manifest.json');
}
function loadDepartmentReadmeFile(){
    loadGeneratedFileToPreview('Departments/Engineering/README.md');
}
function sendDocsStatusToMission(){
    if(!projectDocsStatusData){
        toast('Refresh docs status first.');
        return;
    }
    go('mission');
    q('input').value=`Please review this Kayock Project Docs status report.

Summary:
Tracked docs: ${projectDocsStatusData.summary.docs}
Present: ${projectDocsStatusData.summary.present}
Valid: ${projectDocsStatusData.summary.valid}
Problems: ${projectDocsStatusData.summary.problems}
Backups: ${projectDocsStatusData.summary.backup_count}

Docs:
${(projectDocsStatusData.docs||[]).map(x=>`${x.label}
Path: ${x.relative||x.path}
Exists: ${x.exists}
Valid: ${x.valid}
Size: ${x.size}
Modified: ${x.modified}
Message: ${x.message}`).join('\n\n')}

Please identify missing docs, stale docs, and the best next documentation/build step.`;
    toast('Docs status sent to Mission Console.');
}

let generatedPreviewData=null;
async function previewRootManifest(){
    try{
        let d=await api('/api/generate/root_manifest/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
        if(d?.ok){
            generatedPreviewData=d;
            q('rootManifestStatus').textContent=`Preview target: ${d.target}
Already exists: ${d.exists}`;
            q('generatedPreview').textContent=d.content||'';
            toast('Root manifest preview generated.');
        }else{
            q('rootManifestStatus').textContent=d?.message||'Preview failed.';
        }
    }catch(e){
        q('rootManifestStatus').textContent='Preview failed: '+e;
    }
}
async function applyRootManifest(){
    let ok=confirm('Write root manifest now? Existing file will be backed up first.');
    if(!ok)return;
    let d=await api('/api/generate/root_manifest/apply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});
    if(d?.ok){
        q('rootManifestStatus').textContent=`${d.message}
Target: ${d.target}
Backup: ${d.backup||'none'}
Validation problems: ${(d.validation?.problems||[]).length}`;
        refreshProjectDocsStatus();
        toast('Root manifest written safely.');
    }else{
        q('rootManifestStatus').textContent=d?.message||'Write failed.';
    }
}
async function previewDepartmentReadme(){
    let key=q('readmeDeptKey').value||'engineering';
    let d=await api('/api/generate/department_readme/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})});
    if(d?.ok){
        generatedPreviewData=d;
        q('readmeStatus').textContent=`Preview target: ${d.target}
Already exists: ${d.exists}`;
        q('generatedPreview').textContent=d.content||'';
        toast('Department README preview generated.');
    }else{
        q('readmeStatus').textContent=d?.message||'README preview failed.';
    }
}
async function applyDepartmentReadme(){
    let ok=confirm('Write department README now? Existing file will be backed up first.');
    if(!ok)return;
    let key=q('readmeDeptKey').value||'engineering';
    let d=await api('/api/generate/department_readme/apply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})});
    if(d?.ok){
        q('readmeStatus').textContent=`${d.message}
Target: ${d.target}
Backup: ${d.backup||'none'}`;
        refreshProjectDocsStatus();
        toast('Department README written safely.');
    }else{
        q('readmeStatus').textContent=d?.message||'README write failed.';
    }
}
function sendGeneratedPreviewToMission(){
    if(!generatedPreviewData){
        toast('Generate a preview first.');
        return;
    }
    go('mission');
    q('input').value=`Please review this generated Kayock project documentation before I rely on it.

Target:
${generatedPreviewData.target}

Content:
${generatedPreviewData.content}

Check:
1. Accuracy
2. Missing sections
3. Safety concerns
4. Better wording
5. Whether it should be written or revised first.`;
    toast('Generated preview sent to Mission Console.');
}

let loadedScanReport=null;
function useLastScanReportPath(){
    if(!lastScanReport?.exported){
        toast('No exported scan report yet. Use Scan + Export Report first.');
        return;
    }
    q('scanReportPath').value=lastScanReport.exported.json||lastScanReport.exported.markdown||'';
    toast('Last exported scan report path loaded.');
}
async function loadScanReport(){
    let path=q('scanReportPath').value.trim();
    if(!path){
        toast('Enter a report path first.');
        return;
    }
    q('scanReportStatus').textContent='Loading scan report...';
    let d=await api('/api/scan/read_report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path,max_read:parseInt(q('scanReportMax').value||'120000')})});
    if(!d?.ok){
        q('scanReportStatus').textContent=d?.message||'Could not load report.';
        return;
    }
    loadedScanReport=d;
    let s=d.summary||{};
    let counts=s.counts||{};
    q('scanReportStatus').textContent=`Loaded: ${d.relative}
Size: ${d.size} bytes
Kind: ${d.kind}
Truncated: ${d.truncated}
Target: ${s.target||'n/a'}
Files: ${counts.files??'n/a'}
Folders: ${counts.folders??'n/a'}
Manifests: ${counts.manifests??s.manifests??'n/a'}
Errors: ${counts.errors??s.errors??'n/a'}`;
    q('scanReportPreview').textContent=d.content||'No content.';
    toast('Scan report loaded.');
}
function loadedScanReportMissionText(){
    if(!loadedScanReport)return '';
    let s=loadedScanReport.summary||{};
    let counts=s.counts||{};
    return `Kayock Loaded Scan Report

Path:
${loadedScanReport.path}

Relative:
${loadedScanReport.relative}

Created:
${s.created||'Unknown'}

Target:
${s.target||'Unknown'}

Counts:
Files: ${counts.files??'Unknown'}
Folders: ${counts.folders??'Unknown'}
Manifests: ${counts.manifests??'Unknown'}
Python: ${counts.python??'Unknown'}
JSON: ${counts.json??'Unknown'}
Markdown: ${counts.markdown??'Unknown'}
Code: ${counts.code??'Unknown'}
Large skipped: ${counts.large_skipped??'Unknown'}
Errors: ${counts.errors??'Unknown'}

Report Preview:
${loadedScanReport.content||'No content.'}`;
}
function sendLoadedScanReportToMission(){
    if(!loadedScanReport){
        toast('Load a scan report first.');
        return;
    }
    go('mission');
    q('input').value=`Please review this loaded Kayock scan report.

Analyze:
1. Folder structure
2. Important files
3. Missing manifests
4. Repair Bay risks
5. Module ownership
6. Suggested next cleanup/build step

${loadedScanReportMissionText()}`;
    toast('Loaded scan report sent to Mission Console input.');
}

async function scanFolder(exportReport){
    let payload={
        path:q('scanPath').value||'',
        max_files:parseInt(q('scanMaxFiles').value||'3000'),
        max_bytes:parseInt(q('scanMaxBytes').value||'1048576'),
        export:!!exportReport
    };
    q('scanStatus').textContent='Scanning read-only...';
    let d=await api('/api/scan/folder',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!d?.ok){
        q('scanStatus').textContent=d?.message||'Scan failed.';
        return;
    }
    lastScanReport=d;
    let c=d.counts||{};
    q('scanStatus').textContent=`Scanned: ${d.target}
Read-only: ${d.read_only}
Files: ${c.files}
Folders: ${c.folders}
Manifests: ${c.manifests}
${d.exported?`Exported Markdown: ${d.exported.markdown}
Exported JSON: ${d.exported.json}`:''}`;
    if(d.exported&&q('scanReportPath'))q('scanReportPath').value=d.exported.json||d.exported.markdown||'';
    q('scanResults').innerHTML=`<div class=scanbox>
        <div class=scanmetric><div class=label>Files</div><div class=value>${c.files||0}</div></div>
        <div class=scanmetric><div class=label>Folders</div><div class=value>${c.folders||0}</div></div>
        <div class=scanmetric><div class=label>Manifests</div><div class=value>${c.manifests||0}</div></div>
        <div class=scanmetric><div class=label>Python</div><div class=value>${c.python||0}</div></div>
        <div class=scanmetric><div class=label>JSON</div><div class=value>${c.json||0}</div></div>
        <div class=scanmetric><div class=label>Markdown</div><div class=value>${c.markdown||0}</div></div>
        <div class=scanmetric><div class=label>Code</div><div class=value>${c.code||0}</div></div>
        <div class=scanmetric><div class=label>Large Skipped</div><div class=value>${c.large_skipped||0}</div></div>
        <div class=scanmetric><div class=label>Errors</div><div class=value>${c.errors||0}</div></div>
    </div>
    <h3>Manifests</h3><div class=scanlist>${esc((d.manifests||[]).map(x=>`${x.relative} (${x.size} bytes)`).join('\n')||'No manifests found.')}</div>
    <h3>Sample Files</h3><div class=scanlist>${esc((d.samples||[]).slice(0,100).map(x=>`[${x.kind}] ${x.relative} (${x.size} bytes)${x.large?' LARGE':''}`).join('\n')||'No sample files.')}</div>`;
    toast(exportReport?'Folder scan exported.':'Folder scan complete.');
}
function sendLastScanToMission(){
    if(!lastScanReport){
        toast('Run a scan first.');
        return;
    }
    let path=lastScanReport.exported?.markdown||lastScanReport.exported?.json||'No exported report path. Use Scan + Export Report, then Load Report for full content.';
    go('mission');
    q('input').value=`Please review this Kayock folder scan.

Target:
${lastScanReport.target}

Report Path:
${path}

Summary:
Files: ${lastScanReport.counts.files}
Folders: ${lastScanReport.counts.folders}
Manifests: ${lastScanReport.counts.manifests}
Python: ${lastScanReport.counts.python}
JSON: ${lastScanReport.counts.json}
Markdown: ${lastScanReport.counts.markdown}
Code: ${lastScanReport.counts.code}
Large skipped: ${lastScanReport.counts.large_skipped}
Errors: ${lastScanReport.counts.errors}

Manifests:
${(lastScanReport.manifests||[]).map(x=>x.relative).join('\n')||'None'}

Please identify structure, risks, missing manifests, next cleanup steps, and which department should own follow-up work.`;
    toast('Folder scan sent to Mission Console input.');
}

async function loadExtensions(){
    if(!q('extList'))return;
    try{
        let d=await (await fetch('/api/extensions/list')).json();
        q('extSummary').textContent=`Modules: ${d.count}
Enabled: ${d.enabled}
Valid: ${d.valid}
State file: ${d.state_file}`;
        extDashboardFromData(d);
        q('extList').innerHTML=(d.items||[]).map(x=>{
            let cls=x.enabled?'':'disabledmod';
            let missing=(x.missing&&x.missing.length)?`Missing: ${x.missing.join(', ')}`:'Manifest OK';
            return `<div class="extcard ${cls}"><h4>🧩 ${esc(x.name)} <span class=small>v${esc(x.version)}</span></h4><span class=exttag>${esc(x.kind||'extension')}</span><span class=exttag>${esc(x.status||'UNKNOWN')}</span><span class=exttag>${x.enabled?'ENABLED':'DISABLED'}</span><div class=extmeta>${esc(x.description||'')}\nOfficer: ${esc(extOfficerText(x.officer))}\nKey: ${esc(x.key)}\n${esc(missing)}\nManifest: ${esc(x.manifest)}\nFolder: ${esc(x.folder)}</div><div class=extactions><button onclick="toggleExtension('${js(x.key)}',${x.enabled?'false':'true'})">${x.enabled?'Disable':'Enable'}</button><button onclick="suggestManifestFix('${js(x.key)}','${js(x.manifest)}')">Suggest Fix</button><button onclick="sendExtensionToMission('${js(x.key)}')">Send to Mission</button></div></div>`
        }).join('')||'No extension manifests found yet.';
    }catch(e){
        q('extSummary').textContent='Extension list failed: '+e;
    }
}
async function toggleExtension(key,enabled){
    let d=await api('/api/extensions/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key,enabled})});
    if(d?.ok)loadExtensions();
}
async function validateExtensions(){
    let d=await api('/api/extensions/validate');
    if(d?.ok){
        q('extSummary').textContent=`${d.message}
Checked: ${d.checked}
Valid: ${d.valid}
Problems: ${d.problems.length}`;
        loadExtensions();
        if(d.problems?.length){
            q('extList').innerHTML=d.problems.map(p=>`<div class=extcard><h4>⚠ ${esc(p.name)}</h4><div class=extmeta>Key: ${esc(p.key)}\nMissing: ${esc((p.missing||[]).join(', '))}\nManifest: ${esc(p.manifest)}</div><div class=extactions><button onclick="suggestManifestFix('${js(p.key)}','${js(p.manifest)}')">Suggest Fix</button></div></div>`).join('');
        }
    }
}
async function createSampleExtension(){
    let d=await api('/api/extensions/sample');
    if(d?.ok){
        toast(d.message);
        loadExtensions();
    }
}
function sendExtensionToMission(key){
    go('mission');
    q('input').value=`Please review this Kayock extension/module and suggest any manifest, dependency, safety, or architecture improvements.

Extension key:
${key}

Focus on:
1. Manifest quality
2. Safety
3. Dependencies
4. How it should appear in the Command Bridge
5. Whether it belongs as a department, extension, or utility`;
    toast('Extension review request sent to Mission Console input.');
}

async function loadBridge(){
    try{
        let d=await (await fetch('/api/bridge/feed')).json();
        let build=(d.builder_passed!==null&&d.builder_passed!==undefined&&d.builder_total!==null&&d.builder_total!==undefined)?`${d.builder_passed}/${d.builder_total} passed`:(d.builder_ok===true?'OK':(d.builder_found?'Report found':'No report'));
        let ev=d.latest_event||{};
        let evMeta=[ev.time,ev.source,ev.severity].filter(Boolean).join(' • ');
        let msg=d.latest_event_message||ev.message||'No recent Bridge event found.';
        q('bridgeLive').innerHTML=`<div class=livegrid>
            <div class=livebox><div class=label>Kernel</div><div class=value>${esc(d.kernel_status||'UNKNOWN')}</div></div>
            <div class=livebox><div class=label>Departments</div><div class=value>${esc(d.departments_online)}/${esc(d.departments)}</div></div>
            <div class=livebox><div class=label>Runtime Packages</div><div class=value>${esc(d.runtime_packages??'—')}</div></div>
            <div class=livebox><div class=label>Builder</div><div class=value>${esc(build)}</div></div>
        </div><div class=eventbox><div class=time>${esc(evMeta||'Latest Event')}</div>${esc(msg)}</div>`;
        let cards=(d.department_cards||[]).map(x=>{
            let cls=String(x.status||'').toLowerCase();
            let badge=(['online','ok','ready','active','healthy','pass','passed'].includes(cls))?'ok':(['warn','warning','degraded','check','staged'].includes(cls)?'warn':'bad');
            let officer=x.officer?`<div class=fleetstatus>${esc(x.officer)}</div>`:'';
            let first=String(x.name||'').split(' ')[0];
            let icon=({Command:'🚀',Academy:'🎓',Engineering:'⚙️',Artificial:'🤖',Iron:'📚',Creative:'🎨',Repair:'🔧',PromptSmith:'✍️',Novel:'📖'}[first]||'◇');
            let cardcls=badge==='ok'?'online':(badge==='warn'?'staged':'missing');
            return `<div class="fleetcard ${cardcls}"><div class=depticon>${icon}</div><h4>${esc(x.name)}</h4>${officer}<div class="fleetstatus ${badge}">${esc(x.status||'UNKNOWN')}</div></div>`
        }).join('');
        q('deptcards').innerHTML=cards||'<div class=status>No department cards found yet. Refresh after running the Builder.</div>';
    }catch(e){
        if(q('bridgeLive'))q('bridgeLive').textContent='Bridge Feed unavailable: '+e;
        if(q('deptcards'))q('deptcards').textContent='Department feed unavailable.';
    }
}

async function refresh(){let s=await (await fetch('/api/status')).json();let lines=[`Root: ${s.root}`,`Kayock Browser: ${s.kayock_browser_found?'found':'missing'}`,`Engine: ${s.engine_found?'found':'missing'}`,`Chat online: ${s.chat_online?'yes':'no'}`,`Active project: ${s.active_project||'None'}`,`Projects: ${s.projects}`,`ComfyUI: ${s.comfy_online?'online':'offline'}`,`Chat models: ${s.chat_models}`,`Library items: ${s.library_items}`,`PDFs: ${s.library_pdfs}`];q('status').textContent=lines.join('\n');q('status2').textContent=lines.join('\n');q('paths').textContent=`Root: ${s.root}\nDrive: ${s.drive_root}\nBrowser: ${s.kayock_browser}\nEngine: ${s.engine}\nProjects: ${s.projects_root}`;q('am').textContent=s.chat_model_name||'None';q('ap').textContent=s.active_professor_name||'Agent Fox';q('mtitle').textContent=s.active_professor_name||'Agent Fox';q('apro').textContent=s.active_project||'None';q('rt').textContent=s.chat_online?'ONLINE':'OFFLINE';q('cpu').textContent=s.cpu_percent!==null?`${s.cpu_percent}%`:'n/a';q('ram').textContent=s.ram_used_gb!==null?`${s.ram_used_gb}/${s.ram_total_gb} GB (${s.ram_percent}%)`:'n/a';q('ramm').style.width=s.ram_percent!==null?`${s.ram_percent}%`:'0%';q('quick').innerHTML=`<span class="pill ${s.engine_found?'ok':'bad'}">Engine ${s.engine_found?'Found':'Missing'}</span><br><span class="pill ${s.chat_online?'ok':'warn'}">Chat ${s.chat_online?'Online':'Offline'}</span><br><span class="pill ${s.comfy_online?'ok':'warn'}">ComfyUI ${s.comfy_online?'Online':'Offline'}</span>`}
loadModels();loadProf();loadProjects();loadMemory();loadBridge();loadRecoveryDashboard();refresh();setInterval(refresh,8000);setInterval(loadBridge,10000)
</script></body></html>"""

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
        if path=='/api/bridge/feed': self.js(bridge_feed()); return
        if path=='/api/models': self.js({'models':[{'name':p.name,'path':str(p)} for p in models()]}); return
        if path=='/api/professors': self.js({'active':prof,'professors':{k:{'name':v[0],'college':v[1],'motto':v[2]} for k,v in PROF.items()}}); return
        if path=='/api/memory/current': self.js(mission_current()); return
        if path=='/api/projects/list': self.js(list_projects()); return
        if path=='/api/extensions/list': self.js(list_extensions()); return
        if path=='/api/extensions/validate': self.js(validate_extensions()); return
        if path=='/api/extensions/sample': self.js(create_sample_extension()); return
        if path=='/api/extensions/report': self.js(extension_report_export()); return
        if path=='/api/novelforge/list': self.js(list_universes()); return
        if path=='/api/novelforge/read': self.js(read_universe(qs.get('name',[''])[0])); return
        if path=='/api/prompts/list': self.js(list_prompts()); return
        if path=='/api/prompts/read': self.js(read_prompt(qs.get('name',[''])[0])); return
        if path=='/api/projects/open':
            p=ppath(qs.get('name',[''])[0])
            if not p or not p.exists(): self.js({'ok':False,'message':'Project not found.'}); return
            os.startfile(str(p)); timeline(p.name,'Project folder opened'); self.js({'ok':True,'message':f'Opened {p.name}'}); return
        if path=='/api/library/list': self.js(list_lib(qs.get('path',[''])[0])); return
        if path=='/api/library/search': self.js(search_library(qs.get('q',[''])[0],qs.get('type',['all'])[0],qs.get('limit',['250'])[0])); return
        if path=='/api/library/preview': self.js(preview_library_file(qs.get('path',[''])[0],qs.get('limit',['16000'])[0])); return
        if path=='/api/library/index/status': self.js(library_index_status()); return
        if path=='/api/library/index/build': self.js(build_library_index(qs.get('max_files',['2000'])[0])); return
        if path=='/api/library/index/search': self.js(search_library_index(qs.get('q',[''])[0],qs.get('limit',['100'])[0])); return
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
        if path=='/api/generate/root_manifest/preview': self.js(project_manifest_preview(d)); return
        if path=='/api/generate/department_readme/preview': self.js(department_readme_preview(d)); return
        if path=='/api/writer/create_project_gate': self.js(kayock_writer_create_project_gate_report(d)); return
        if path=='/api/writer/manifest_preview': self.js(kayock_writer_manifest_preview_report(d)); return
        if path=='/api/writer/story_forge': self.js(kayock_writer_story_forge_report(d)); return
        if path=='/api/writer/foundation': self.js(kayock_writer_foundation_report(d)); return
        if path=='/api/command_center/milestone_freeze': self.js(command_center_milestone_freeze_report(d)); return
        if path=='/api/command_center/archive': self.js(command_center_archive_report(d)); return
        if path=='/api/command_center/dashboard_card': self.js(command_center_dashboard_card_report(d)); return
        if path=='/api/command_center/detail': self.js(command_center_detail_report(d)); return
        if path=='/api/command_center/foundation': self.js(command_center_foundation_report(d)); return
        if path=='/api/repair/milestone_freeze': self.js(repair_shop_milestone_freeze_report(d)); return
        if path=='/api/repair/session_report': self.js(repair_shop_session_report(d)); return
        if path=='/api/repair/ticket_action_bridge': self.js(repair_ticket_action_bridge_report(d)); return
        if path=='/api/repair/ticket_detail': self.js(repair_ticket_detail_report(d)); return
        if path=='/api/repair/ticket_queue': self.js(repair_ticket_queue_report(d)); return
        if path=='/api/repair/verified_dashboard': self.js(verified_action_dashboard_card(d)); return
        if path=='/api/repair/action_detail': self.js(repair_action_detail_report(d)); return
        if path=='/api/repair/ops_dashboard': self.js(repair_ops_dashboard_report(d)); return
        if path=='/api/backups/recovery_dashboard': self.js(recovery_dashboard_summary(d)); return
        if path=='/api/backups/recovery_timeline': self.js(recovery_timeline_report(d)); return
        if path=='/api/backups/rollback_audit': self.js(rollback_action_audit_inventory(d)); return
        if path=='/api/backups/single_file_rollback': self.js(single_file_rollback_action(d)); return
        if path=='/api/backups/rollback_preview': self.js(rollback_preview_report(d)); return
        if path=='/api/backups/restore_audit': self.js(restore_action_audit_inventory(d)); return
        if path=='/api/backups/single_file_restore': self.js(single_file_restore_action(d)); return
        if path=='/api/backups/restore_final_check': self.js(restore_final_checklist(d)); return
        if path=='/api/backups/staging_packages': self.js(staging_package_inventory(d)); return
        if path=='/api/backups/restore_staging': self.js(restore_staging_copy(d)); return
        if path=='/api/backups/restore_readiness': self.js(restore_readiness_gate(d)); return
        if path=='/api/backups/restore_preview': self.js(restore_preview_report(d)); return
        if path=='/api/backups/vault': self.js(backup_vault_report(d)); return
        if path=='/api/repair/actions/history': self.js(repair_action_history(d)); return
        if path=='/api/repair/actions/plan': self.js(repair_action_plan(d)); return
        if path=='/api/repair/actions/apply': self.js(apply_repair_action(d)); return
        if path=='/api/models/duplicates': self.js(model_duplicate_truth_report(d)); return
        if path=='/api/portable/readiness': self.js(portable_readiness_report(d)); return
        if path=='/api/env/verify': self.js(env_dependency_verification(d)); return
        if path=='/api/build/verify': self.js(build_verification_lite(d)); return
        if path=='/api/project_docs/status': self.js(project_docs_status(d)); return
        if path=='/api/generated/read': self.js(generated_file_reader(d)); return
        if path=='/api/scan/read_report': self.js(read_scan_report(d)); return
        if path=='/api/generate/root_manifest/apply': self.js(apply_project_manifest(d)); return
        if path=='/api/generate/department_readme/apply': self.js(apply_department_readme(d)); return
        if path=='/api/scan/folder': self.js(folder_scan_bridge(d)); return
        if path=='/api/extensions/apply_repair': self.js(apply_manifest_repair(d)); return
        if path=='/api/extensions/repair_suggest': self.js(suggest_manifest_repair(d)); return
        if path=='/api/extensions/toggle': self.js(toggle_extension(d)); return
        if path=='/api/novelforge/export': self.js(export_story_bible(d)); return
        if path=='/api/novelforge/save': self.js(save_universe(d)); return
        if path=='/api/novelforge/duplicate': self.js(duplicate_universe(d)); return
        if path=='/api/novelforge/rename': self.js(rename_universe(d)); return
        if path=='/api/novelforge/delete': self.js(delete_universe(d.get('name',''))); return
        if path=='/api/prompts/save': self.js(save_prompt(d)); return
        if path=='/api/prompts/import': self.js(save_prompt(dict(d, source='PromptSmith Extension Import'))); return
        if path=='/api/prompts/duplicate': self.js(duplicate_prompt(d)); return
        if path=='/api/prompts/rename': self.js(rename_prompt(d)); return
        if path=='/api/prompts/delete': self.js(delete_prompt(d.get('name',''))); return
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



def prompt_path(name):
    base=FOLDERS['prompts']; base.mkdir(parents=True,exist_ok=True)
    safe=slug(name or 'Untitled_Prompt')
    if safe.lower().endswith('.json'): safe=safe[:-5]
    p=(base/(safe+'.json')).resolve()
    try:
        p.relative_to(base.resolve()); return p
    except Exception:
        return None

def prompt_markdown_path(name):
    base=FOLDERS['prompts']; base.mkdir(parents=True,exist_ok=True)
    safe=slug(name or 'Untitled_Prompt')
    if safe.lower().endswith('.json'): safe=safe[:-5]
    return base/(safe+'.md')

def list_prompts():
    base=FOLDERS['prompts']; base.mkdir(parents=True,exist_ok=True)
    arr=[]
    for p in sorted(base.glob('*.json'),key=lambda x:x.stat().st_mtime,reverse=True):
        d=jread(p,{})
        body=d.get('prompt','') or d.get('body','')
        arr.append({
            'name':p.stem,
            'title':d.get('title') or p.stem,
            'notes':d.get('notes',''),
            'category':d.get('category','General'),
            'prompt_type':d.get('prompt_type','User Prompt'),
            'preview':body[:220],
            'modified':datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y-%m-%d %H:%M'),
            'path':str(p)
        })
    return {'ok':True,'prompts':arr,'folder':str(base)}

def read_prompt(name):
    p=prompt_path(name)
    if not p or not p.exists():
        return {'ok':False,'message':'Prompt not found.'}
    d=jread(p,{})
    d.update({'ok':True,'name':p.stem,'path':str(p),'category':d.get('category','General'),'prompt_type':d.get('prompt_type','User Prompt')})
    return d

def save_prompt(d):
    title=(d.get('title') or 'Untitled Prompt').strip()
    prompt=(d.get('prompt') or d.get('body') or '').strip()
    notes=(d.get('notes') or '').strip()
    category=(d.get('category') or 'General').strip()
    prompt_type=(d.get('prompt_type') or d.get('type') or 'User Prompt').strip()
    if not prompt:
        return {'ok':False,'message':'Prompt body is empty.'}
    p=prompt_path(title)
    if not p:
        return {'ok':False,'message':'Invalid prompt title.'}
    old=jread(p,{}) if p.exists() else {}
    data={
        'title':title,
        'name':p.stem,
        'category':category,
        'prompt_type':prompt_type,
        'prompt':prompt,
        'notes':notes,
        'created':old.get('created',now()) if old else now(),
        'modified':now(),
        'version':'1.1',
        'source':d.get('source') or 'PromptSmith'
    }
    jwrite(p,data)
    md=prompt_markdown_path(title)
    md.write_text(f"# {title}\n\nCategory: {category}\nType: {prompt_type}\nModified: {data['modified']}\n\n## Notes\n\n{notes}\n\n## Prompt\n\n```text\n{prompt}\n```\n",encoding='utf-8')
    if active_project:
        timeline(active_project,f'PromptSmith saved prompt: {title}')
    return {'ok':True,'message':f'Saved prompt: {title}','name':p.stem,'prompt':data,'path':str(p),'markdown':str(md)}

def delete_prompt(name):
    p=prompt_path(name)
    if not p or not p.exists():
        return {'ok':False,'message':'Prompt not found.'}
    title=jread(p,{}).get('title') or p.stem
    try:
        p.unlink()
        md=prompt_markdown_path(name)
        if md.exists(): md.unlink()
    except Exception as e:
        return {'ok':False,'message':f'Delete failed: {e}'}
    if active_project:
        timeline(active_project,f'PromptSmith deleted prompt: {title}')
    return {'ok':True,'message':f'Deleted prompt: {title}'}

def duplicate_prompt(d):
    name=d.get('name','')
    p=prompt_path(name)
    if not p or not p.exists():
        return {'ok':False,'message':'Prompt not found.'}
    old=jread(p,{})
    base_title=(d.get('new_title') or (old.get('title') or p.stem)+' Copy').strip()
    new_data=dict(old)
    new_data['title']=base_title
    new_data['source']='PromptSmith Duplicate'
    return save_prompt(new_data)

def rename_prompt(d):
    name=d.get('name','')
    new_title=(d.get('new_title') or '').strip()
    if not new_title:
        return {'ok':False,'message':'New title is required.'}
    p=prompt_path(name)
    if not p or not p.exists():
        return {'ok':False,'message':'Prompt not found.'}
    data=jread(p,{})
    old_title=data.get('title') or p.stem
    data['title']=new_title
    result=save_prompt(data)
    if result.get('ok'):
        try:
            p.unlink()
            old_md=prompt_markdown_path(name)
            if old_md.exists(): old_md.unlink()
        except Exception:
            pass
        if active_project:
            timeline(active_project,f'PromptSmith renamed prompt: {old_title} -> {new_title}')
    return result


def novel_root():
    p=FOLDERS.get('novel_forge',ROOT/'NovelForge')
    p.mkdir(parents=True,exist_ok=True)
    return p

def novel_path(name):
    base=novel_root()
    safe=slug(name or 'Untitled_Universe')
    if safe.lower().endswith('.json'): safe=safe[:-5]
    p=(base/(safe+'.json')).resolve()
    try:
        p.relative_to(base.resolve()); return p
    except Exception:
        return None

def novel_md_path(name):
    base=novel_root()/'Markdown'
    base.mkdir(parents=True,exist_ok=True)
    safe=slug(name or 'Untitled_Universe')
    return base/(safe+'.md')

def list_universes():
    base=novel_root()
    arr=[]
    for p in sorted(base.glob('*.json'),key=lambda x:x.stat().st_mtime,reverse=True):
        d=jread(p,{})
        arr.append({
            'name':p.stem,
            'universe':d.get('universe') or d.get('name') or p.stem,
            'premise':(d.get('premise') or '')[:220],
            'characters':len(d.get('characters',[])) if isinstance(d.get('characters'),list) else 0,
            'locations':len(d.get('locations',[])) if isinstance(d.get('locations'),list) else 0,
            'artifacts':len(d.get('artifacts',[])) if isinstance(d.get('artifacts'),list) else 0,
            'timeline':len(d.get('timeline',[])) if isinstance(d.get('timeline'),list) else 0,
            'mysteries':len(d.get('mysteries',[])) if isinstance(d.get('mysteries'),list) else 0,
            'scenes':len(d.get('scenes',[])) if isinstance(d.get('scenes'),list) else 0,
            'modified':datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
        })
    return {'ok':True,'universes':arr,'folder':str(base)}

def read_universe(name):
    p=novel_path(name)
    if not p or not p.exists():
        return {'ok':False,'message':'Universe not found.'}
    d=jread(p,{})
    d.update({'ok':True,'file_name':p.stem,'path':str(p)})
    return d

def lines_to_list(value):
    if isinstance(value,list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [x.strip() for x in str(value or '').splitlines() if x.strip()]

def save_universe(d):
    name=(d.get('universe') or d.get('name') or 'Untitled Universe').strip()
    if not name:
        return {'ok':False,'message':'Universe name is required.'}
    p=novel_path(name)
    if not p:
        return {'ok':False,'message':'Invalid universe name.'}
    old=jread(p,{}) if p.exists() else {}
    data={
        'universe':name,
        'file_name':p.stem,
        'premise':(d.get('premise') or '').strip(),
        'characters':lines_to_list(d.get('characters','')),
        'locations':lines_to_list(d.get('locations','')),
        'artifacts':lines_to_list(d.get('artifacts','')),
        'timeline':lines_to_list(d.get('timeline','')),
        'mysteries':lines_to_list(d.get('mysteries','')),
        'scenes':lines_to_list(d.get('scenes','')),
        'notes':(d.get('notes') or '').strip(),
        'created':old.get('created',now()) if old else now(),
        'modified':now(),
        'version':'0.1',
        'source':'Novel Forge'
    }
    jwrite(p,data)
    md=novel_md_path(name)
    md.write_text(
        f"# {name}\n\n"
        f"Modified: {data['modified']}\n\n"
        f"## Premise\n\n{data['premise']}\n\n"
        f"## Characters\n\n" + "\n".join(f"- {x}" for x in data['characters']) + "\n\n"
        f"## Locations\n\n" + "\n".join(f"- {x}" for x in data['locations']) + "\n\n"
        f"## Artifacts\n\n" + "\n".join(f"- {x}" for x in data['artifacts']) + "\n\n"
        f"## Timeline\n\n" + "\n".join(f"- {x}" for x in data['timeline']) + "\n\n"
        f"## Mysteries / Unresolved Threads\n\n" + "\n".join(f"- {x}" for x in data['mysteries']) + "\n\n"
        f"## Scenes\n\n" + "\n".join(f"- {x}" for x in data.get('scenes',[])) + "\n\n"
        f"## Notes\n\n{data['notes']}\n",
        encoding='utf-8'
    )
    if active_project:
        timeline(active_project,f'Novel Forge saved universe: {name}')
    return {'ok':True,'message':f'Saved universe: {name}','universe':data,'name':p.stem,'path':str(p),'markdown':str(md)}

def duplicate_universe(d):
    name=d.get('name','')
    new_title=(d.get('new_title') or '').strip()
    p=novel_path(name)
    if not p or not p.exists():
        return {'ok':False,'message':'Universe not found.'}
    old=jread(p,{})
    if not new_title:
        new_title=(old.get('universe') or p.stem)+' Copy'
    old['universe']=new_title
    old['source']='Novel Forge Duplicate'
    return save_universe(old)

def rename_universe(d):
    name=d.get('name','')
    new_title=(d.get('new_title') or '').strip()
    if not new_title:
        return {'ok':False,'message':'New universe name is required.'}
    p=novel_path(name)
    if not p or not p.exists():
        return {'ok':False,'message':'Universe not found.'}
    old=jread(p,{})
    old_title=old.get('universe') or p.stem
    old['universe']=new_title
    result=save_universe(old)
    if result.get('ok'):
        try:
            p.unlink()
            md=novel_md_path(name)
            if md.exists(): md.unlink()
        except Exception:
            pass
        if active_project:
            timeline(active_project,f'Novel Forge renamed universe: {old_title} -> {new_title}')
    return result

def delete_universe(name):
    p=novel_path(name)
    if not p or not p.exists():
        return {'ok':False,'message':'Universe not found.'}
    title=jread(p,{}).get('universe') or p.stem
    try:
        p.unlink()
        md=novel_md_path(name)
        if md.exists(): md.unlink()
    except Exception as e:
        return {'ok':False,'message':f'Delete failed: {e}'}
    if active_project:
        timeline(active_project,f'Novel Forge deleted universe: {title}')
    return {'ok':True,'message':f'Deleted universe: {title}'}


def export_story_bible(d):
    base=FOLDERS.get('novel_exports',ROOT/'NovelForge'/'Exports')
    base.mkdir(parents=True,exist_ok=True)
    universe=(d.get('universe') or 'Untitled Universe').strip()
    safe=slug(universe)
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    prefix=f"{safe}_Story_Bible_{stamp}"
    json_path=base/(prefix+'.json')
    md_path=base/(prefix+'.md')
    txt_path=base/(prefix+'.txt')
    summary=d.get('summary') or {}
    bible=d.get('story_bible') or ''
    codex=d.get('codex') or {}
    export_data={
        'universe':universe,
        'exported':now(),
        'summary':summary,
        'codex':codex,
        'story_bible':bible,
        'source':'Novel Forge Story Bible Export',
        'version':'1.0'
    }
    jwrite(json_path,export_data)
    summary_md="\n".join([
        f"- Characters: {summary.get('characters','')}",
        f"- Locations: {summary.get('locations','')}",
        f"- Artifacts: {summary.get('artifacts','')}",
        f"- Timeline Events: {summary.get('timeline','')}",
        f"- Mysteries: {summary.get('mysteries','')}",
        f"- Readiness: {summary.get('readiness','')}",
    ])
    md_text=f"# {universe} — Story Bible\n\nExported: {export_data['exported']}\n\n## Dashboard Summary\n\n{summary_md}\n\n---\n\n{bible}\n"
    md_path.write_text(md_text,encoding='utf-8')
    txt_path.write_text(md_text.replace('# ','').replace('## ',''),encoding='utf-8')
    if active_project:
        timeline(active_project,f'Novel Forge exported story bible: {universe}')
    return {
        'ok':True,
        'message':f'Exported Story Bible for {universe}',
        'folder':str(base),
        'json':str(json_path),
        'markdown':str(md_path),
        'text':str(txt_path)
    }


def extension_roots():
    roots=[FOLDERS.get('extensions',ROOT/'Extensions'),FOLDERS.get('modules',ROOT/'Modules'),ROOT/'Departments']
    for r in roots:
        try: r.mkdir(parents=True,exist_ok=True)
        except Exception: pass
    return roots

def extension_state_file():
    p=FOLDERS.get('config',ROOT/'Config')/'extension_state.json'
    p.parent.mkdir(parents=True,exist_ok=True)
    return p

def read_extension_state():
    return jread(extension_state_file(),{})

def write_extension_state(d):
    jwrite(extension_state_file(),d)

def manifest_candidates():
    files=[]
    for root in extension_roots():
        if not root.exists(): continue
        for name in ['manifest.json','module.json','extension.json']:
            files.extend(root.glob(f'*/{name}'))
        # Allow direct loose manifests in Extensions for early testing.
        if root.name.lower() in ['extensions','modules']:
            for name in ['manifest.json','module.json','extension.json']:
                p=root/name
                if p.exists(): files.append(p)
    # Deduplicate while preserving order.
    seen=set(); out=[]
    for p in files:
        s=str(p.resolve()).lower()
        if s not in seen:
            seen.add(s); out.append(p)
    return out

def extension_key_from_path(p):
    try:
        rel=str(p.parent.relative_to(ROOT)).replace('\\','/')
    except Exception:
        rel=p.parent.name
    return slug(rel).lower()

def normalize_extension_manifest(p):
    d=jread(p,{})
    key=d.get('id') or d.get('key') or d.get('name') or extension_key_from_path(p)
    name=d.get('name') or d.get('title') or p.parent.name
    version=d.get('version') or '0.0.0'
    desc=d.get('description') or d.get('summary') or ''
    kind=d.get('type') or d.get('kind') or ('department' if 'Departments' in str(p) else 'extension')
    officer=d.get('officer') or d.get('lead') or d.get('captain') or ''
    required=['name','version']
    missing=[x for x in required if not d.get(x)]
    state=read_extension_state()
    enabled=state.get(key,{}).get('enabled',d.get('enabled',True))
    status='VALID' if not missing else 'CHECK'
    return {
        'key':key,
        'name':name,
        'version':version,
        'description':desc,
        'kind':kind,
        'officer':officer,
        'enabled':bool(enabled),
        'status':status,
        'missing':missing,
        'manifest':str(p),
        'folder':str(p.parent),
        'raw':d
    }

def list_extensions():
    items=[normalize_extension_manifest(p) for p in manifest_candidates()]
    # Built-in shell entry so the page is never empty.
    if not any(x.get('key')=='extension-manager' for x in items):
        items.insert(0,{
            'key':'extension-manager',
            'name':'Extension Manager',
            'version':'0.1-shell',
            'description':'Built-in Kayock module manager shell.',
            'kind':'system',
            'officer':'Kayock Command OS',
            'enabled':True,
            'status':'VALID',
            'missing':[],
            'manifest':'built-in',
            'folder':str(FOLDERS.get('extensions',ROOT/'Extensions')),
            'raw':{}
        })
    valid=sum(1 for x in items if x.get('status')=='VALID')
    enabled=sum(1 for x in items if x.get('enabled'))
    return {'ok':True,'count':len(items),'valid':valid,'enabled':enabled,'state_file':str(extension_state_file()),'items':items}

def toggle_extension(d):
    key=d.get('key') or ''
    enabled=bool(d.get('enabled'))
    if not key:
        return {'ok':False,'message':'Extension key required.'}
    state=read_extension_state()
    old=state.get(key,{})
    old['enabled']=enabled
    old['modified']=now()
    state[key]=old
    write_extension_state(state)
    if active_project:
        timeline(active_project,f"Extension {'enabled' if enabled else 'disabled'}: {key}")
    return {'ok':True,'message':f"{'Enabled' if enabled else 'Disabled'} extension: {key}",'key':key,'enabled':enabled}

def validate_extensions():
    data=list_extensions()
    problems=[]
    for item in data.get('items',[]):
        if item.get('missing'):
            problems.append({'key':item.get('key'),'name':item.get('name'),'missing':item.get('missing'),'manifest':item.get('manifest')})
    return {'ok':True,'checked':data.get('count',0),'valid':data.get('valid',0),'problems':problems,'message':f"Checked {data.get('count',0)} extension manifest(s); {len(problems)} problem(s)."}

def create_sample_extension():
    root=FOLDERS.get('extensions',ROOT/'Extensions')/'SampleExtension'
    root.mkdir(parents=True,exist_ok=True)
    p=root/'manifest.json'
    if not p.exists():
        jwrite(p,{
            'id':'sample-extension',
            'name':'Sample Extension',
            'version':'0.1.0',
            'type':'extension',
            'description':'Example Kayock extension manifest for future .kmod packages.',
            'officer':'Sample Officer',
            'enabled':False,
            'entry':'README.md',
            'permissions':['read-only']
        })
        (root/'README.md').write_text('# Sample Extension\n\nThis is a placeholder extension manifest for Kayock Command OS.\n',encoding='utf-8')
    return {'ok':True,'message':'Sample extension manifest ready.','folder':str(root),'manifest':str(p)}


def extension_report_export():
    reports=FOLDERS.get('reports',ROOT/'Reports')
    reports.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    data=list_extensions()
    validation=validate_extensions()
    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Extension Report',
        'summary':{
            'count':data.get('count',0),
            'enabled':data.get('enabled',0),
            'valid':data.get('valid',0),
            'problems':len(validation.get('problems',[])),
        },
        'state_file':data.get('state_file',''),
        'items':data.get('items',[]),
        'problems':validation.get('problems',[])
    }
    json_path=reports/f'Extension_Report_{stamp}.json'
    md_path=reports/f'Extension_Report_{stamp}.md'
    jwrite(json_path,report)
    lines=[
        '# Kayock Extension Report',
        '',
        f"Created: {report['created']}",
        '',
        '## Summary',
        '',
        f"- Modules: {report['summary']['count']}",
        f"- Enabled: {report['summary']['enabled']}",
        f"- Valid: {report['summary']['valid']}",
        f"- Problems: {report['summary']['problems']}",
        f"- State file: {report['state_file']}",
        '',
        '## Problems',
        ''
    ]
    if report['problems']:
        for p in report['problems']:
            lines += [
                f"### {p.get('name') or p.get('key')}",
                '',
                f"- Key: {p.get('key','')}",
                f"- Missing: {', '.join(p.get('missing',[]))}",
                f"- Manifest: {p.get('manifest','')}",
                ''
            ]
    else:
        lines += ['No manifest problems found.','']
    lines += ['## Modules','']
    for x in report['items']:
        lines += [
            f"### {x.get('name','Unnamed Module')}",
            '',
            f"- Key: {x.get('key','')}",
            f"- Version: {x.get('version','')}",
            f"- Kind: {x.get('kind','')}",
            f"- Status: {x.get('status','')}",
            f"- Enabled: {x.get('enabled')}",
            f"- Missing: {', '.join(x.get('missing',[])) if x.get('missing') else 'None'}",
            f"- Manifest: {x.get('manifest','')}",
            f"- Folder: {x.get('folder','')}",
            '',
            x.get('description','') or '',
            ''
        ]
    md_path.write_text('\n'.join(lines),encoding='utf-8')
    if active_project:
        timeline(active_project,f'Exported extension report: {md_path.name}')
    return {'ok':True,'message':'Extension report exported.','json':str(json_path),'markdown':str(md_path),'folder':str(reports),'summary':report['summary']}

def suggest_manifest_repair(d):
    manifest=d.get('manifest') or ''
    key=d.get('key') or ''
    target=None
    if manifest and manifest!='built-in':
        p=Path(manifest)
        if p.exists():
            target=p
    if target is None and key:
        for p in manifest_candidates():
            item=normalize_extension_manifest(p)
            if item.get('key')==key:
                target=p
                break
    if target is None:
        return {'ok':False,'message':'Could not find a manifest file for repair suggestion.'}

    raw=jread(target,{})
    folder_name=target.parent.name
    suggested=dict(raw)
    if not suggested.get('id'):
        suggested['id']=slug(folder_name).lower()
    if not suggested.get('name'):
        suggested['name']=folder_name.replace('_',' ').replace('-',' ').title()
    if not suggested.get('version'):
        suggested['version']='0.1.0'
    if not suggested.get('type') and not suggested.get('kind'):
        suggested['type']='department' if 'Departments' in str(target) else 'extension'
    if not suggested.get('description'):
        suggested['description']=f"{suggested.get('name','Module')} module for Kayock Command OS."
    if 'enabled' not in suggested:
        suggested['enabled']=True
    repaired=json.dumps(suggested,indent=2,ensure_ascii=False)
    return {
        'ok':True,
        'message':'Manifest repair suggestion generated.',
        'manifest':str(target),
        'folder':str(target.parent),
        'original':json.dumps(raw,indent=2,ensure_ascii=False),
        'suggested':repaired
    }


def apply_manifest_repair(d):
    manifest=d.get('manifest') or ''
    suggested_text=d.get('suggested') or ''
    key=d.get('key') or ''
    target=None

    if manifest and manifest!='built-in':
        p=Path(manifest)
        if p.exists():
            target=p

    if target is None and key:
        for p in manifest_candidates():
            item=normalize_extension_manifest(p)
            if item.get('key')==key:
                target=p
                break

    if target is None:
        return {'ok':False,'message':'Could not find manifest file to repair.'}

    if not suggested_text.strip():
        suggestion=suggest_manifest_repair({'manifest':str(target),'key':key})
        if not suggestion.get('ok'):
            return suggestion
        suggested_text=suggestion.get('suggested','')

    try:
        suggested_json=json.loads(suggested_text)
    except Exception as e:
        return {'ok':False,'message':f'Suggested manifest is not valid JSON: {e}'}

    before=normalize_extension_manifest(target)
    backup_dir=FOLDERS.get('manifest_backups',ROOT/'Backups'/'Manifests')
    backup_dir.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path=backup_dir/f"{slug(target.parent.name)}_manifest_{stamp}.json"

    try:
        shutil.copy2(target,backup_path)
    except Exception as e:
        return {'ok':False,'message':f'Could not back up manifest before repair: {e}'}

    try:
        jwrite(target,suggested_json)
    except Exception as e:
        try:
            shutil.copy2(backup_path,target)
        except Exception:
            pass
        return {'ok':False,'message':f'Could not write repaired manifest. Original was restored if possible. Error: {e}','backup':str(backup_path)}

    after=normalize_extension_manifest(target)
    validation=validate_extensions()
    if active_project:
        timeline(active_project,f'Applied safe manifest repair: {target.name} backed up to {backup_path.name}')

    return {
        'ok':True,
        'message':'Manifest repair applied safely.',
        'manifest':str(target),
        'backup':str(backup_path),
        'before':{
            'status':before.get('status'),
            'missing':before.get('missing',[]),
            'version':before.get('version')
        },
        'after':{
            'status':after.get('status'),
            'missing':after.get('missing',[]),
            'version':after.get('version')
        },
        'validation':validation
    }


SCAN_SKIP_DIRS={'.git','node_modules','env','.env','venv','.venv','__pycache__','.pytest_cache','.mypy_cache','dist','build','target','.idea','.vscode'}
SCAN_TEXT_EXTS={'.txt','.md','.json','.yaml','.yml','.toml','.ini','.cfg','.conf','.py','.js','.ts','.html','.css','.bat','.ps1','.sh','.sql','.xml','.csv','.log'}
SCAN_CODE_EXTS={'.py','.js','.ts','.html','.css','.bat','.ps1','.sh','.sql','.java','.cs','.cpp','.c','.h','.rs','.go','.php','.rb'}
SCAN_DOC_EXTS={'.md','.txt','.pdf','.doc','.docx','.rtf'}
SCAN_IMAGE_EXTS={'.png','.jpg','.jpeg','.gif','.webp','.svg','.ico'}
SCAN_AUDIO_EXTS={'.mp3','.wav','.flac','.ogg','.m4a'}
SCAN_VIDEO_EXTS={'.mp4','.mov','.avi','.mkv','.webm'}

def safe_scan_target(raw):
    raw=(raw or '').strip()
    if not raw:
        return ROOT
    if raw in FOLDERS:
        return FOLDERS[raw]
    p=Path(raw)
    if not p.is_absolute():
        p=ROOT/raw
    try:
        rp=p.resolve()
        rr=ROOT.resolve()
        if not (rp==rr or rr in rp.parents):
            raise ValueError('Scan target must be inside the FOXAI root.')
        return rp
    except Exception as e:
        raise ValueError(str(e))

def classify_scan_file(p):
    ext=p.suffix.lower()
    if p.name.lower() in {'manifest.json','module.json','extension.json'}:
        return 'manifest'
    if ext=='.py':
        return 'python'
    if ext=='.json':
        return 'json'
    if ext in {'.md','.markdown'}:
        return 'markdown'
    if ext in SCAN_TEXT_EXTS:
        return 'text'
    if ext in SCAN_CODE_EXTS:
        return 'code'
    if ext in SCAN_DOC_EXTS:
        return 'document'
    if ext in SCAN_IMAGE_EXTS:
        return 'image'
    if ext in SCAN_AUDIO_EXTS:
        return 'audio'
    if ext in SCAN_VIDEO_EXTS:
        return 'video'
    return 'other'

def folder_scan_bridge(d):
    try:
        target=safe_scan_target(d.get('path') or d.get('folder') or '')
    except Exception as e:
        return {'ok':False,'message':f'Invalid scan target: {e}'}

    max_files=int(d.get('max_files') or 3000)
    max_bytes=int(d.get('max_bytes') or 1024*1024)
    export=bool(d.get('export',False))
    target.mkdir(parents=True,exist_ok=True) if str(target).startswith(str(ROOT)) and not target.exists() else None

    counts={
        'folders':0,'files':0,'manifests':0,'python':0,'json':0,'markdown':0,'text':0,'code':0,
        'documents':0,'images':0,'audio':0,'video':0,'other':0,'large_skipped':0,'errors':0
    }
    samples=[]
    manifests=[]
    errors=[]
    skipped_dirs=[]
    total_bytes=0

    for dirpath, dirnames, filenames in os.walk(target):
        original=list(dirnames)
        dirnames[:]=[x for x in dirnames if x not in SCAN_SKIP_DIRS and not x.startswith('$')]
        for skipped in sorted(set(original)-set(dirnames)):
            skipped_dirs.append(str(Path(dirpath)/skipped))
        counts['folders']+=len(dirnames)

        for fn in filenames:
            if counts['files']>=max_files:
                break
            p=Path(dirpath)/fn
            try:
                size=p.stat().st_size
                rel=str(p.relative_to(ROOT)).replace('\\','/') if ROOT in p.resolve().parents or p.resolve()==ROOT else str(p)
                kind=classify_scan_file(p)
                counts['files']+=1
                total_bytes+=size
                if size>max_bytes:
                    counts['large_skipped']+=1
                if kind=='manifest':
                    counts['manifests']+=1
                    manifests.append({'path':str(p),'relative':rel,'size':size})
                elif kind=='python':
                    counts['python']+=1
                    counts['code']+=1
                elif kind=='json':
                    counts['json']+=1
                    counts['text']+=1
                elif kind=='markdown':
                    counts['markdown']+=1
                    counts['text']+=1
                elif kind=='text':
                    counts['text']+=1
                elif kind=='code':
                    counts['code']+=1
                elif kind=='document':
                    counts['documents']+=1
                elif kind=='image':
                    counts['images']+=1
                elif kind=='audio':
                    counts['audio']+=1
                elif kind=='video':
                    counts['video']+=1
                else:
                    counts['other']+=1
                if len(samples)<200:
                    samples.append({'path':str(p),'relative':rel,'kind':kind,'size':size,'large':size>max_bytes})
            except Exception as e:
                counts['errors']+=1
                if len(errors)<50:
                    errors.append({'path':str(p),'error':str(e)})
        if counts['files']>=max_files:
            break

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Folder Scan Report',
        'root':str(ROOT),
        'target':str(target),
        'read_only':True,
        'limits':{'max_files':max_files,'max_bytes':max_bytes},
        'ignored_dirs':sorted(SCAN_SKIP_DIRS),
        'counts':counts,
        'total_bytes_seen':total_bytes,
        'manifests':manifests,
        'samples':samples,
        'skipped_dirs':skipped_dirs[:200],
        'errors':errors
    }

    if export:
        reports=FOLDERS.get('scan_reports',ROOT/'Reports'/'Scans')
        reports.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        safe=slug(target.name or 'FOXAI')
        json_path=reports/f'Folder_Scan_{safe}_{stamp}.json'
        md_path=reports/f'Folder_Scan_{safe}_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Folder Scan Report','',
            f"Created: {report['created']}",
            f"Target: {report['target']}",
            f"Read only: {report['read_only']}",
            '',
            '## Counts',''
        ]
        for k,v in counts.items():
            lines.append(f"- {k}: {v}")
        lines += ['', '## Manifests', '']
        if manifests:
            for item in manifests:
                lines.append(f"- {item.get('relative')} ({item.get('size')} bytes)")
        else:
            lines.append('No manifests found.')
        lines += ['', '## Sample Files', '']
        for item in samples[:100]:
            lines.append(f"- [{item.get('kind')}] {item.get('relative')} ({item.get('size')} bytes)")
        if errors:
            lines += ['', '## Errors', '']
            for item in errors:
                lines.append(f"- {item.get('path')}: {item.get('error')}")
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(reports)}
        if active_project:
            timeline(active_project,f'Folder scan exported: {md_path.name}')

    return report


def read_scan_report(d):
    raw=(d.get('path') or d.get('report') or '').strip()
    if not raw:
        return {'ok':False,'message':'Report path required.'}
    try:
        p=safe_scan_target(raw)
    except Exception as e:
        return {'ok':False,'message':f'Invalid report path: {e}'}
    if not p.exists() or not p.is_file():
        return {'ok':False,'message':'Report file not found.'}
    if p.suffix.lower() not in {'.json','.md','.txt'}:
        return {'ok':False,'message':'Only JSON, Markdown, and TXT scan reports can be previewed.'}
    max_read=int(d.get('max_read') or 120000)
    try:
        size=p.stat().st_size
        text=p.read_text(encoding='utf-8',errors='replace')
    except Exception as e:
        return {'ok':False,'message':f'Could not read report: {e}'}
    truncated=False
    if len(text)>max_read:
        text=text[:max_read]+'\n\n[TRUNCATED FOR PREVIEW]'
        truncated=True
    parsed=None
    summary=None
    if p.suffix.lower()=='.json':
        try:
            parsed=json.loads(p.read_text(encoding='utf-8',errors='replace'))
            if isinstance(parsed,dict):
                summary={
                    'title':parsed.get('title',''),
                    'created':parsed.get('created',''),
                    'target':parsed.get('target',''),
                    'read_only':parsed.get('read_only',''),
                    'counts':parsed.get('counts',{}),
                    'manifests':len(parsed.get('manifests',[]) or []),
                    'samples':len(parsed.get('samples',[]) or []),
                    'errors':len(parsed.get('errors',[]) or [])
                }
        except Exception as e:
            summary={'parse_error':str(e)}
    return {
        'ok':True,
        'message':'Scan report loaded.',
        'path':str(p),
        'relative':str(p.relative_to(ROOT)).replace('\\','/') if ROOT.resolve() in p.resolve().parents or p.resolve()==ROOT.resolve() else str(p),
        'size':size,
        'truncated':truncated,
        'kind':p.suffix.lower().lstrip('.'),
        'summary':summary,
        'content':text
    }


def safe_write_generated_file(target, content, backup=True):
    target=Path(target)
    try:
        rp=target.resolve()
        rr=ROOT.resolve()
        if not (rp==rr or rr in rp.parents):
            return {'ok':False,'message':'Target must be inside FOXAI root.'}
    except Exception as e:
        return {'ok':False,'message':f'Invalid target: {e}'}
    target.parent.mkdir(parents=True,exist_ok=True)
    backup_path=''
    if target.exists() and backup:
        bdir=FOLDERS.get('file_backups',ROOT/'Backups'/'GeneratedFiles')
        bdir.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path=bdir/f"{slug(target.stem)}_{stamp}{target.suffix or '.bak'}"
        try:
            shutil.copy2(target,backup_path)
        except Exception as e:
            return {'ok':False,'message':f'Could not back up existing file: {e}'}
    try:
        target.write_text(content,encoding='utf-8')
    except Exception as e:
        return {'ok':False,'message':f'Could not write file: {e}','backup':str(backup_path) if backup_path else ''}
    return {'ok':True,'path':str(target),'backup':str(backup_path) if backup_path else ''}

def build_root_manifest_data():
    exts=list_extensions()
    scan=folder_scan_bridge({'path':'Departments','max_files':3000,'max_bytes':1048576,'export':False})
    return {
        'api_version':'kayock.project.v1',
        'id':'kayock-command-os',
        'name':'Kayock Command OS',
        'version':'0.10.6',
        'engine':'FOXAI Core',
        'runtime':'FOXKernel',
        'description':'Portable local-first knowledge, creation, repair, and story operating system.',
        'root':str(ROOT),
        'created_or_updated':now(),
        'principles':[
            'Local-first',
            'Read-only scan by default',
            'Backup before write',
            'No telemetry by default',
            'Modules report through manifests'
        ],
        'module_summary':exts.get('summary',{}) if isinstance(exts.get('summary'),dict) else {
            'count':exts.get('count',0),
            'enabled':exts.get('enabled',0),
            'valid':exts.get('valid',0)
        },
        'departments':[{
            'key':x.get('key'),
            'name':x.get('name'),
            'version':x.get('version'),
            'kind':x.get('kind'),
            'enabled':x.get('enabled'),
            'status':x.get('status'),
            'manifest':x.get('manifest')
        } for x in exts.get('items',[]) if x.get('kind') in ['department','system','extension']],
        'scan_summary':{
            'target':scan.get('target'),
            'counts':scan.get('counts',{}),
            'manifests':[x.get('relative') for x in scan.get('manifests',[])]
        }
    }

def project_manifest_preview(d):
    data=build_root_manifest_data()
    content=json.dumps(data,indent=2,ensure_ascii=False)
    target=ROOT/'manifest.json'
    return {'ok':True,'message':'Root manifest preview generated.','target':str(target),'exists':target.exists(),'content':content}

def apply_project_manifest(d):
    preview=project_manifest_preview(d)
    if not preview.get('ok'):
        return preview
    result=safe_write_generated_file(ROOT/'manifest.json',preview.get('content',''),backup=True)
    if not result.get('ok'):
        return result
    validation=validate_extensions()
    if active_project:
        timeline(active_project,'Generated root project manifest.')
    return {'ok':True,'message':'Root project manifest written safely.','target':result.get('path'),'backup':result.get('backup'),'validation':validation}

def build_department_readme(dept_key='engineering'):
    exts=list_extensions()
    item=None
    for x in exts.get('items',[]):
        if x.get('key')==dept_key or slug(x.get('name','')).lower()==dept_key:
            item=x
            break
    if not item:
        # fallback to first department
        for x in exts.get('items',[]):
            if x.get('kind')=='department':
                item=x
                break
    if not item:
        return None,None

    raw=item.get('raw') or {}
    folder=Path(item.get('folder') or ROOT)
    officer=raw.get('officer') or item.get('officer') or ''
    if isinstance(officer,dict):
        officer_text=f"{officer.get('name','')} ({officer.get('callsign','')}) — {officer.get('role','')}".strip()
    else:
        officer_text=str(officer)

    services=raw.get('services') or []
    provides=raw.get('provides') or []
    depends=raw.get('depends_on') or []
    tools=raw.get('tools') or []

    tool_lines=[]
    for t in tools:
        if isinstance(t,dict):
            tool_lines.append(f"- **{t.get('id','tool')}** (`{t.get('import','')}`): {t.get('purpose','')}")
        else:
            tool_lines.append(f"- {t}")

    content=f"""# {item.get('name','Department')}

Generated: {now()}

## Purpose

{item.get('description') if item.get('description') else (item.get('name','This department') + ' module for Kayock Command OS.')}

## Ownership

- **Key:** `{item.get('key','')}`
- **Kind:** `{item.get('kind','')}`
- **Version:** `{item.get('version','')}`
- **Enabled:** `{item.get('enabled')}`
- **Status:** `{item.get('status','')}`
- **Officer:** {officer_text}

## Manifest

`{item.get('manifest','')}`

## Dependencies

{chr(10).join(f"- `{x}`" for x in depends) if depends else "- None listed"}

## Provides

{chr(10).join(f"- `{x}`" for x in provides) if provides else "- None listed"}

## Services

{chr(10).join(f"- {x}" for x in services) if services else "- None listed"}

## Tools

{chr(10).join(tool_lines) if tool_lines else "- None listed"}

## Files

This department currently contains the manifest and Python service files discovered by the Folder Scan Bridge.

## Safety Notes

- Treat department scans as read-only by default.
- Back up manifests before automated changes.
- Keep tool execution behind explicit user approval.
- Prefer report-first workflows before repair actions.

## Next Maintenance Steps

- Keep this README updated when services or tools change.
- Add docstrings to Python modules explaining ownership and purpose.
- Add health-check expectations and example outputs.
- Add tests when the Repair Bay test runner is connected.
"""
    return folder/'README.md',content

def department_readme_preview(d):
    key=(d.get('key') or d.get('department') or 'engineering').strip().lower()
    target,content=build_department_readme(key)
    if target is None:
        return {'ok':False,'message':'No department found for README generation.'}
    return {'ok':True,'message':'Department README preview generated.','target':str(target),'exists':target.exists(),'content':content}

def apply_department_readme(d):
    preview=department_readme_preview(d)
    if not preview.get('ok'):
        return preview
    result=safe_write_generated_file(preview.get('target'),preview.get('content',''),backup=True)
    if not result.get('ok'):
        return result
    if active_project:
        timeline(active_project,f"Generated department README: {Path(result.get('path')).name}")
    return {'ok':True,'message':'Department README written safely.','target':result.get('path'),'backup':result.get('backup')}

def generated_file_reader(d):
    raw=(d.get('path') or '').strip()
    if not raw:
        return {'ok':False,'message':'File path required.'}
    try:
        p=safe_scan_target(raw)
    except Exception as e:
        return {'ok':False,'message':f'Invalid file path: {e}'}
    if not p.exists() or not p.is_file():
        return {'ok':False,'message':'File not found.'}
    if p.suffix.lower() not in {'.json','.md','.txt'}:
        return {'ok':False,'message':'Only JSON, Markdown, and TXT generated files can be read.'}
    try:
        txt=p.read_text(encoding='utf-8',errors='replace')
    except Exception as e:
        return {'ok':False,'message':f'Could not read file: {e}'}
    if len(txt)>120000:
        txt=txt[:120000]+'\n\n[TRUNCATED]'
    return {'ok':True,'path':str(p),'content':txt,'size':p.stat().st_size}


def project_docs_status(d=None):
    docs=[]
    problems=[]

    def info_for(path,label,kind):
        p=Path(path)
        item={
            'label':label,
            'kind':kind,
            'path':str(p),
            'relative':str(p.relative_to(ROOT)).replace('\\','/') if p.exists() and (ROOT.resolve() in p.resolve().parents or p.resolve()==ROOT.resolve()) else str(p),
            'exists':p.exists(),
            'size':0,
            'modified':'',
            'valid':False,
            'message':'Missing'
        }
        if p.exists():
            try:
                st=p.stat()
                item['size']=st.st_size
                item['modified']=datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds')
                if p.suffix.lower()=='.json':
                    try:
                        data=json.loads(p.read_text(encoding='utf-8',errors='replace'))
                        item['valid']=True
                        top=len(data.keys()) if isinstance(data,dict) else 'non-object'
                        item['message']=f'Valid JSON with {top} top-level keys'
                    except Exception as e:
                        item['valid']=False
                        item['message']=f'Invalid JSON: {e}'
                elif p.suffix.lower() in {'.md','.txt'}:
                    txt=p.read_text(encoding='utf-8',errors='replace')
                    item['valid']=len(txt.strip())>0
                    item['message']='Readable Markdown/Text' if item['valid'] else 'Empty Markdown/Text'
                else:
                    item['valid']=True
                    item['message']='Exists'
            except Exception as e:
                item['valid']=False
                item['message']=f'Could not inspect: {e}'
        if (not item['exists']) or (not item['valid']):
            problems.append({'label':label,'path':str(p),'message':item['message']})
        return item

    docs.append(info_for(ROOT/'manifest.json','Root Project Manifest','root_manifest'))

    dept_root=ROOT/'Departments'
    if dept_root.exists():
        found=False
        for p in sorted(dept_root.glob('*/README.md')):
            found=True
            docs.append(info_for(p,f'{p.parent.name} README','department_readme'))
        if not found:
            docs.append(info_for(dept_root/'Engineering'/'README.md','Engineering README','department_readme'))

    backups=FOLDERS.get('file_backups',ROOT/'Backups'/'GeneratedFiles')
    backup_count=0
    if backups.exists():
        try:
            backup_count=sum(1 for x in backups.glob('*') if x.is_file())
        except Exception:
            backup_count=0

    return {
        'ok':True,
        'created':now(),
        'summary':{
            'docs':len(docs),
            'present':sum(1 for x in docs if x.get('exists')),
            'valid':sum(1 for x in docs if x.get('valid')),
            'problems':len(problems),
            'backup_count':backup_count
        },
        'docs':docs,
        'problems':problems,
        'backup_folder':str(backups)
    }


def build_verification_lite(d=None):
    d=d or {}
    export=bool(d.get('export',True))
    max_py=int(d.get('max_py') or 200)
    checks=[]
    problems=[]

    def add_check(name, ok, message, details=None, severity='info'):
        item={'name':name,'ok':bool(ok),'message':message,'severity':severity,'details':details or {}}
        checks.append(item)
        if not ok:
            problems.append(item)
        return item

    # Root manifest
    root_manifest=ROOT/'manifest.json'
    if root_manifest.exists():
        try:
            root_data=json.loads(root_manifest.read_text(encoding='utf-8',errors='replace'))
            required=['api_version','id','name','version']
            missing=[x for x in required if not root_data.get(x)]
            add_check('Root manifest JSON',not missing,f"Root manifest valid; missing required keys: {missing if missing else 'none'}",{'path':str(root_manifest),'keys':list(root_data.keys()),'missing':missing},'manifest')
        except Exception as e:
            add_check('Root manifest JSON',False,f'Root manifest invalid JSON: {e}',{'path':str(root_manifest)},'manifest')
    else:
        add_check('Root manifest exists',False,'Root manifest is missing.',{'path':str(root_manifest)},'manifest')

    # Extension manifests
    try:
        ext=list_extensions()
        validation=validate_extensions()
        add_check('Extension manifest validation',len(validation.get('problems',[]))==0,f"{validation.get('checked',0)} manifest(s) checked; {len(validation.get('problems',[]))} problem(s).",{'validation':validation,'summary':{'count':ext.get('count'), 'enabled':ext.get('enabled'), 'valid':ext.get('valid')}},'manifest')
    except Exception as e:
        add_check('Extension manifest validation',False,f'Extension validation failed: {e}',{},'manifest')

    # Project docs
    try:
        docs=project_docs_status({})
        add_check('Project docs status',docs.get('summary',{}).get('problems',0)==0,f"{docs.get('summary',{}).get('present',0)} present, {docs.get('summary',{}).get('valid',0)} valid, {docs.get('summary',{}).get('problems',0)} problem(s).",docs,'docs')
    except Exception as e:
        add_check('Project docs status',False,f'Docs status failed: {e}',{},'docs')

    # Expected paths
    expected=[
        ROOT/'core'/'foxai_web.py',
        ROOT/'Departments',
        ROOT/'Departments'/'Engineering',
        ROOT/'Departments'/'Engineering'/'manifest.json',
        ROOT/'Departments'/'Engineering'/'health.py',
        ROOT/'Departments'/'Engineering'/'officer.py',
        ROOT/'Departments'/'Engineering'/'services.py',
    ]
    missing_paths=[str(p) for p in expected if not p.exists()]
    add_check('Expected project paths',not missing_paths,f"{len(expected)-len(missing_paths)}/{len(expected)} expected paths found.",{'missing':missing_paths,'expected':[str(p) for p in expected]},'paths')

    # Folder scan summary
    try:
        scan=folder_scan_bridge({'path':'Departments','max_files':3000,'max_bytes':1048576,'export':False})
        add_check('Departments folder scan',scan.get('ok') and scan.get('counts',{}).get('errors',0)==0,f"Departments scan: {scan.get('counts',{}).get('files',0)} file(s), {scan.get('counts',{}).get('errors',0)} error(s).",{'counts':scan.get('counts',{}),'manifests':scan.get('manifests',[])},'scan')
    except Exception as e:
        add_check('Departments folder scan',False,f'Departments scan failed: {e}',{},'scan')

    # Python compile checks: Department Python + core app
    py_files=[]
    for base in [ROOT/'Departments', ROOT/'core']:
        if base.exists():
            for p in base.rglob('*.py'):
                if any(part in SCAN_SKIP_DIRS for part in p.parts):
                    continue
                py_files.append(p)
                if len(py_files)>=max_py:
                    break
        if len(py_files)>=max_py:
            break

    py_results=[]
    py_ok=True
    for p in py_files:
        try:
            py_compile.compile(str(p),doraise=True)
            py_results.append({'path':str(p),'relative':str(p.relative_to(ROOT)).replace('\\','/'),'ok':True,'message':'compiled'})
        except Exception as e:
            py_ok=False
            py_results.append({'path':str(p),'relative':str(p.relative_to(ROOT)).replace('\\','/') if ROOT.resolve() in p.resolve().parents else str(p),'ok':False,'message':str(e)})
    add_check('Python compile check',py_ok,f"{sum(1 for x in py_results if x.get('ok'))}/{len(py_results)} Python file(s) compiled.",{'files':py_results},'python')

    # Health check path presence, not executing.
    health=ROOT/'Departments'/'Engineering'/'health.py'
    add_check('Engineering health check presence',health.exists(),'Engineering health.py found.' if health.exists() else 'Engineering health.py missing.',{'path':str(health)},'health')

    report={
        'ok':len(problems)==0,
        'created':now(),
        'title':'Kayock Build Verification Lite Report',
        'read_only':True,
        'report_only':True,
        'root':str(ROOT),
        'summary':{
            'checks':len(checks),
            'passed':sum(1 for x in checks if x.get('ok')),
            'problems':len(problems),
            'python_files':len(py_files)
        },
        'checks':checks,
        'problems':problems
    }

    if export:
        reports=FOLDERS.get('build_reports',ROOT/'Reports'/'BuildVerification')
        reports.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=reports/f'Build_Verification_{stamp}.json'
        md_path=reports/f'Build_Verification_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Build Verification Lite Report','',
            f"Created: {report['created']}",
            f"Root: {report['root']}",
            f"Read only: {report['read_only']}",
            f"Report only: {report['report_only']}",
            '',
            '## Summary','',
            f"- Checks: {report['summary']['checks']}",
            f"- Passed: {report['summary']['passed']}",
            f"- Problems: {report['summary']['problems']}",
            f"- Python files checked: {report['summary']['python_files']}",
            '',
            '## Checks',''
        ]
        for c in checks:
            mark='PASS' if c.get('ok') else 'FAIL'
            lines += [f"### {mark}: {c.get('name')}",'',c.get('message',''),'']
        if problems:
            lines += ['## Problems','']
            for c in problems:
                lines += [f"- {c.get('name')}: {c.get('message')}"]
        else:
            lines += ['## Problems','','No problems found.']
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(reports)}
        if active_project:
            timeline(active_project,f'Build verification exported: {md_path.name}')

    return report


def env_dependency_verification(d=None):
    d=d or {}
    export=bool(d.get('export',True))
    checks=[]
    problems=[]

    def add_check(name, ok, message, details=None, severity='info', optional=False):
        item={'name':name,'ok':bool(ok),'message':message,'severity':severity,'optional':bool(optional),'details':details or {}}
        checks.append(item)
        if (not ok) and (not optional):
            problems.append(item)
        return item

    # Python runtime.
    py_version='.'.join(str(x) for x in sys.version_info[:3])
    py_exe=sys.executable
    add_check('Python runtime',True,f'Python {py_version} running at {py_exe}',{
        'version':py_version,
        'executable':py_exe,
        'platform':platform.platform(),
        'machine':platform.machine()
    },'runtime')

    portable_candidates=[
        ROOT/'env'/'python'/'python.exe',
        ROOT/'env'/'python'/'python',
        ROOT/'python'/'python.exe',
        ROOT/'runtime'/'python'/'python.exe'
    ]
    portable_found=[str(p) for p in portable_candidates if p.exists()]
    add_check('Portable Python path',bool(portable_found), 'Portable Python found.' if portable_found else 'Portable Python not found in expected local paths; current interpreter may still be valid.', {
        'current_executable':py_exe,
        'candidates':[str(p) for p in portable_candidates],
        'found':portable_found
    }, 'runtime', optional=True)

    # Required imports used by current web app/runtime.
    required_imports=['json','os','sys','pathlib','http.server','urllib.parse','datetime','subprocess','py_compile','shutil','importlib.util']
    req_results=[]
    req_ok=True
    for mod in required_imports:
        try:
            spec=importlib.util.find_spec(mod)
            ok=spec is not None
        except Exception:
            ok=False
        req_results.append({'module':mod,'ok':ok})
        if not ok:
            req_ok=False
    add_check('Required Python imports',req_ok,f"{sum(1 for x in req_results if x.get('ok'))}/{len(req_results)} required import(s) available.",{'imports':req_results},'imports')

    # Optional Repair Bay tools from Engineering manifest.
    optional_imports=[
        ('ruff','ruff','Fast linting and formatting checks'),
        ('black','black','Python formatting'),
        ('mypy','mypy','Static type checking'),
        ('pydeps','pydeps','Import graph visualization'),
        ('import-linter','importlinter','Architecture boundary enforcement'),
        ('grimp','grimp','Import graph analysis'),
        ('pip-audit','pip_audit','Dependency vulnerability scanning'),
        ('cyclonedx-bom','cyclonedx_py','SBOM generation')
    ]
    opt_results=[]
    for tool,mod,purpose in optional_imports:
        try:
            spec=importlib.util.find_spec(mod)
            ok=spec is not None
        except Exception:
            ok=False
        opt_results.append({'tool':tool,'module':mod,'purpose':purpose,'available':ok})
    available=sum(1 for x in opt_results if x.get('available'))
    add_check('Optional Repair Bay imports',True,f"{available}/{len(opt_results)} optional Repair Bay tool import(s) available. Missing optional tools are not failures yet.",{'tools':opt_results},'imports',optional=True)

    # Node/npm presence.
    node_path=shutil.which('node') or str(ROOT/'node'/'node.exe') if (ROOT/'node'/'node.exe').exists() else ''
    npm_path=shutil.which('npm') or shutil.which('npm.cmd') or str(ROOT/'node'/'npm.cmd') if (ROOT/'node'/'npm.cmd').exists() else ''
    node_details={'node':node_path,'npm':npm_path}
    add_check('Node / npm presence',bool(node_path) or bool(npm_path),'Node/npm detected.' if (node_path or npm_path) else 'Node/npm not detected; only needed for Electron/browser packaging workflows.',node_details,'node',optional=True)

    # Key BAT files.
    bat_patterns=['*.bat','*.cmd']
    bat_files=[]
    for pat in bat_patterns:
        bat_files.extend(sorted(ROOT.glob(pat)))
    key_bats=[]
    for p in bat_files:
        n=p.name.lower()
        if any(x in n for x in ['start','run','launch','foxai','kayock','build']):
            key_bats.append(p)
    add_check('Key launcher/build BAT files',bool(key_bats),f"{len(key_bats)} key BAT/CMD launcher or build file(s) found.",{'files':[str(p) for p in key_bats],'all_root_bats':[str(p) for p in bat_files]},'paths',optional=True)

    # Key folders.
    essential=['core','Departments','Reports','Config']
    optional=['NovelForge','Prompts','Extensions','Modules','Models','models','ComfyUI','Library','IronLibrary']
    folder_results=[]
    for name in essential:
        p=ROOT/name
        folder_results.append({'name':name,'path':str(p),'exists':p.exists(),'required':True})
    for name in optional:
        p=ROOT/name
        folder_results.append({'name':name,'path':str(p),'exists':p.exists(),'required':False})
    missing_required=[x for x in folder_results if x.get('required') and not x.get('exists')]
    add_check('Key folders',len(missing_required)==0,f"{sum(1 for x in folder_results if x.get('exists'))}/{len(folder_results)} tracked folder(s) exist; {len(missing_required)} required missing.",{'folders':folder_results,'missing_required':missing_required},'paths')

    # Models / GGUF count.
    model_dirs=[ROOT/'Models',ROOT/'models',ROOT/'AI'/'models',ROOT/'models_local']
    model_files=[]
    for md in model_dirs:
        if md.exists():
            try:
                for p in md.rglob('*.gguf'):
                    model_files.append(p)
            except Exception:
                pass
    add_check('Model folder / GGUF inventory',True,f"{len(model_files)} GGUF model file(s) found in tracked model folders.",{
        'model_dirs':[str(p) for p in model_dirs],
        'models':[{'path':str(p),'size':p.stat().st_size if p.exists() else 0} for p in model_files[:100]]
    },'models',optional=True)

    # Report folders.
    report_keys=['reports','scan_reports','build_reports','env_reports','novel_exports']
    report_results=[]
    for key in report_keys:
        p=FOLDERS.get(key)
        if p:
            report_results.append({'key':key,'path':str(p),'exists':p.exists()})
    add_check('Report export folders',all(x.get('exists') for x in report_results),f"{sum(1 for x in report_results if x.get('exists'))}/{len(report_results)} report folder(s) exist.",{'folders':report_results},'reports',optional=True)

    # Existing build verification report folder presence.
    build_report_dir=FOLDERS.get('build_reports',ROOT/'Reports'/'BuildVerification')
    build_reports=list(build_report_dir.glob('Build_Verification_*.md')) if build_report_dir.exists() else []
    add_check('Previous build verification reports',True,f"{len(build_reports)} previous build verification Markdown report(s) found.",{'reports':[str(p) for p in sorted(build_reports)[-10:]]},'reports',optional=True)

    report={
        'ok':len(problems)==0,
        'created':now(),
        'title':'Kayock Environment + Dependency Verification Report',
        'read_only':True,
        'report_only':True,
        'root':str(ROOT),
        'summary':{
            'checks':len(checks),
            'passed':sum(1 for x in checks if x.get('ok')),
            'problems':len(problems),
            'optional_missing':sum(1 for x in checks if (not x.get('ok')) and x.get('optional')),
            'optional_tools_available':available,
            'optional_tools_total':len(optional_imports),
            'gguf_models':len(model_files)
        },
        'checks':checks,
        'problems':problems
    }

    if export:
        reports=FOLDERS.get('env_reports',ROOT/'Reports'/'Environment')
        reports.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=reports/f'Environment_Verification_{stamp}.json'
        md_path=reports/f'Environment_Verification_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Environment + Dependency Verification Report','',
            f"Created: {report['created']}",
            f"Root: {report['root']}",
            f"Read only: {report['read_only']}",
            f"Report only: {report['report_only']}",
            '',
            '## Summary','',
            f"- Checks: {report['summary']['checks']}",
            f"- Passed: {report['summary']['passed']}",
            f"- Problems: {report['summary']['problems']}",
            f"- Optional tools available: {report['summary']['optional_tools_available']}/{report['summary']['optional_tools_total']}",
            f"- GGUF models found: {report['summary']['gguf_models']}",
            '',
            '## Checks',''
        ]
        for c in checks:
            mark='PASS' if c.get('ok') else ('OPTIONAL-MISSING' if c.get('optional') else 'FAIL')
            lines += [f"### {mark}: {c.get('name')}",'',c.get('message',''),'']
        if problems:
            lines += ['## Problems','']
            for c in problems:
                lines.append(f"- {c.get('name')}: {c.get('message')}")
        else:
            lines += ['## Problems','','No required environment problems found.']
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(reports)}
        if active_project:
            timeline(active_project,f'Environment verification exported: {md_path.name}')

    return report


def portable_readiness_report(d=None):
    d=d or {}
    export=bool(d.get('export',True))
    checks=[]
    blockers=[]
    warnings=[]

    def rel(p):
        try:
            pp=Path(p).resolve()
            rr=ROOT.resolve()
            if pp==rr or rr in pp.parents:
                return str(pp.relative_to(rr)).replace('\\','/')
        except Exception:
            pass
        return str(p)

    def add_check(name, ok, message, details=None, weight=10, blocker=False, warning=False):
        item={
            'name':name,
            'ok':bool(ok),
            'message':message,
            'weight':int(weight),
            'blocker':bool(blocker),
            'warning':bool(warning),
            'details':details or {}
        }
        checks.append(item)
        if not ok and blocker:
            blockers.append(item)
        elif not ok and warning:
            warnings.append(item)
        return item

    # Runtime lock: current Python must be the portable Python when present.
    expected_python=(ROOT/'env'/'python'/'python.exe').resolve()
    current_python=Path(sys.executable).resolve()
    expected_exists=expected_python.exists()
    runtime_locked=expected_exists and current_python==expected_python
    if runtime_locked:
        msg=f'Runtime locked to portable Python: {expected_python}'
    elif expected_exists:
        msg=f'Portable Python exists, but current runtime is {current_python}'
    else:
        msg=f'Portable Python not found at {expected_python}'
    add_check('Runtime Lock',runtime_locked,msg,{
        'expected':str(expected_python),
        'current':str(current_python),
        'expected_exists':expected_exists
    },weight=25,blocker=True)

    # Portable launcher.
    launcher=ROOT/'START_FOXAI_WEB_PORTABLE.bat'
    launcher_ok=launcher.exists()
    add_check('Portable Web Launcher',launcher_ok,'START_FOXAI_WEB_PORTABLE.bat found.' if launcher_ok else 'Portable web launcher missing.',{
        'path':str(launcher)
    },weight=10,blocker=True)

    # Root path is removable-drive-ish / drive-root friendly.
    root_drive=Path(ROOT).drive
    root_ok=bool(root_drive) and str(ROOT).upper().startswith(root_drive.upper())
    add_check('FOXAI Root Path',root_ok,f'FOXAI root is {ROOT}',{
        'root':str(ROOT),
        'drive':root_drive
    },weight=8,warning=True)

    # Required folders.
    required_folders=[ROOT/'core',ROOT/'Config',ROOT/'Reports',ROOT/'Departments']
    missing_required=[str(p) for p in required_folders if not p.exists()]
    add_check('Required Folders',not missing_required,f'{len(required_folders)-len(missing_required)}/{len(required_folders)} required folders present.',{
        'missing':missing_required,
        'required':[str(p) for p in required_folders]
    },weight=12,blocker=True)

    # Required imports.
    required_imports=['json','os','sys','pathlib','http.server','urllib.parse','datetime','subprocess','py_compile','shutil','importlib.util']
    import_results=[]
    imports_ok=True
    for mod in required_imports:
        try:
            spec=importlib.util.find_spec(mod)
            ok=spec is not None
        except Exception:
            ok=False
        import_results.append({'module':mod,'ok':ok})
        if not ok:
            imports_ok=False
    add_check('Required Python Imports',imports_ok,f"{sum(1 for x in import_results if x.get('ok'))}/{len(import_results)} required import(s) available.",{
        'imports':import_results
    },weight=12,blocker=True)

    # Reports folders.
    report_dirs=[
        FOLDERS.get('reports',ROOT/'Reports'),
        FOLDERS.get('scan_reports',ROOT/'Reports'/'Scans'),
        FOLDERS.get('build_reports',ROOT/'Reports'/'BuildVerification'),
        FOLDERS.get('env_reports',ROOT/'Reports'/'Environment'),
        FOLDERS.get('portable_reports',ROOT/'Reports'/'PortableReadiness'),
    ]
    # Ensure the current report folder exists before checking.
    FOLDERS.get('portable_reports',ROOT/'Reports'/'PortableReadiness').mkdir(parents=True,exist_ok=True)
    report_dir_results=[{'path':str(p),'exists':p.exists()} for p in report_dirs]
    report_dirs_ok=all(x.get('exists') for x in report_dir_results)
    add_check('Report Folders',report_dirs_ok,f"{sum(1 for x in report_dir_results if x.get('exists'))}/{len(report_dir_results)} report folder(s) present.",{
        'folders':report_dir_results
    },weight=8,warning=True)

    # Model duplicate detection.
    model_dirs=[ROOT/'Models',ROOT/'models',ROOT/'AI'/'models',ROOT/'models_local']
    model_files=[]
    for md in model_dirs:
        if md.exists():
            try:
                for p in md.rglob('*.gguf'):
                    try:
                        st=p.stat()
                        model_files.append({'path':str(p),'relative':rel(p),'name':p.name,'size':st.st_size})
                    except Exception:
                        model_files.append({'path':str(p),'relative':rel(p),'name':p.name,'size':0})
            except Exception:
                pass

    unique_map={}
    duplicates=[]
    for item in model_files:
        key=(item.get('name','').lower(),item.get('size',0))
        unique_map.setdefault(key,[]).append(item)
    for key,items in unique_map.items():
        if len(items)>1:
            duplicates.append({'name':key[0],'size':key[1],'copies':items})
    unique_count=len(unique_map)
    duplicate_count=sum(len(x.get('copies',[]))-1 for x in duplicates)
    models_ok=len(model_files)>0
    add_check('GGUF Model Inventory',models_ok,f"{len(model_files)} GGUF file(s), {unique_count} unique model(s), {duplicate_count} duplicate copy/copies detected.",{
        'model_dirs':[str(p) for p in model_dirs],
        'total_files':len(model_files),
        'unique_models':unique_count,
        'duplicate_copies':duplicate_count,
        'duplicates':duplicates,
        'models':model_files[:200]
    },weight=8,warning=True)

    # Optional dependency plan.
    optional_tools=[
        {'tool':'ruff','module':'ruff','reason':'Fast lint/format checks for Repair Bay'},
        {'tool':'black','module':'black','reason':'Python formatting'},
        {'tool':'mypy','module':'mypy','reason':'Static type checking'},
        {'tool':'pydeps','module':'pydeps','reason':'Import graph visualization'},
        {'tool':'import-linter','module':'importlinter','reason':'Architecture boundary enforcement'},
        {'tool':'grimp','module':'grimp','reason':'Import graph analysis'},
        {'tool':'pip-audit','module':'pip_audit','reason':'Dependency vulnerability scanning'},
        {'tool':'cyclonedx-bom','module':'cyclonedx_py','reason':'SBOM generation'},
    ]
    optional_results=[]
    for t in optional_tools:
        try:
            ok=importlib.util.find_spec(t['module']) is not None
        except Exception:
            ok=False
        optional_results.append({**t,'available':ok})
    optional_available=sum(1 for x in optional_results if x.get('available'))
    add_check('Optional Repair Bay Tools',True,f"{optional_available}/{len(optional_results)} optional Repair Bay tool(s) available. Missing tools do not block portability.",{
        'tools':optional_results,
        'install_later_order':['ruff','black','mypy','pip-audit','cyclonedx-bom','pydeps','grimp','import-linter']
    },weight=4,warning=False)

    # Node/npm optional but not core blocker.
    node_path=shutil.which('node') or (str(ROOT/'node'/'node.exe') if (ROOT/'node'/'node.exe').exists() else '')
    npm_path=shutil.which('npm') or shutil.which('npm.cmd') or (str(ROOT/'node'/'npm.cmd') if (ROOT/'node'/'npm.cmd').exists() else '')
    node_ok=bool(node_path) and bool(npm_path)
    add_check('Node/npm for Packaging',node_ok,'Node/npm available for Electron packaging.' if node_ok else 'Node/npm not detected. This only blocks Electron/browser packaging, not the web bridge.',{
        'node':node_path,
        'npm':npm_path
    },weight=3,warning=True)

    # BAT cleanup signal. Not a blocker, but too many root BAT files affects clarity.
    bat_files=list(ROOT.glob('*.bat'))+list(ROOT.glob('*.cmd'))
    suspicious=[str(p) for p in bat_files if p.name.lower().startswith('@echo off')]
    add_check('Root Launcher Clarity',len(suspicious)==0,f"{len(bat_files)} BAT/CMD file(s) in root; {len(suspicious)} suspicious filename(s).",{
        'total_root_bat_cmd':len(bat_files),
        'suspicious':suspicious
    },weight=2,warning=True)

    # Score: based on weights. Warnings lose their weighted points only partially.
    total_weight=sum(c.get('weight',0) for c in checks)
    earned=0
    for c in checks:
        if c.get('ok'):
            earned+=c.get('weight',0)
        elif c.get('warning'):
            earned+=max(0,int(c.get('weight',0)*0.35))
    score=round((earned/total_weight)*100) if total_weight else 0

    portability_blockers=[{
        'name':b.get('name'),
        'message':b.get('message'),
        'details':b.get('details',{})
    } for b in blockers]

    if runtime_locked and not blockers:
        readiness='USB-ready for current web bridge workflows'
    elif not blockers:
        readiness='Mostly portable with warnings'
    else:
        readiness='Not USB-ready until blockers are resolved'

    report={
        'ok':len(blockers)==0,
        'created':now(),
        'title':'Kayock Runtime Lock + Portable Readiness Report',
        'read_only':True,
        'report_only':True,
        'root':str(ROOT),
        'summary':{
            'score':score,
            'readiness':readiness,
            'checks':len(checks),
            'passed':sum(1 for x in checks if x.get('ok')),
            'blockers':len(blockers),
            'warnings':len(warnings),
            'runtime_locked':runtime_locked,
            'current_python':str(current_python),
            'expected_python':str(expected_python),
            'gguf_files':len(model_files),
            'unique_gguf_models':unique_count,
            'duplicate_gguf_copies':duplicate_count,
            'optional_tools_available':optional_available,
            'optional_tools_total':len(optional_results)
        },
        'blockers':portability_blockers,
        'warnings':[{'name':w.get('name'),'message':w.get('message'),'details':w.get('details',{})} for w in warnings],
        'checks':checks
    }

    if export:
        reports=FOLDERS.get('portable_reports',ROOT/'Reports'/'PortableReadiness')
        reports.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=reports/f'Portable_Readiness_{stamp}.json'
        md_path=reports/f'Portable_Readiness_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Runtime Lock + Portable Readiness Report','',
            f"Created: {report['created']}",
            f"Root: {report['root']}",
            f"Read only: {report['read_only']}",
            f"Report only: {report['report_only']}",
            '',
            '## Summary','',
            f"- Portable readiness score: {score}/100",
            f"- Readiness: {readiness}",
            f"- Runtime locked: {runtime_locked}",
            f"- Current Python: {current_python}",
            f"- Expected Python: {expected_python}",
            f"- Blockers: {len(blockers)}",
            f"- Warnings: {len(warnings)}",
            f"- GGUF files: {len(model_files)}",
            f"- Unique GGUF models: {unique_count}",
            f"- Duplicate GGUF copies: {duplicate_count}",
            f"- Optional tools: {optional_available}/{len(optional_results)}",
            '',
            '## Checks',''
        ]
        for c in checks:
            mark='PASS' if c.get('ok') else ('BLOCKER' if c.get('blocker') else 'WARNING')
            lines += [f"### {mark}: {c.get('name')}",'',c.get('message',''),'']
        if blockers:
            lines += ['## USB Portability Blockers','']
            for b in blockers:
                lines.append(f"- {b.get('name')}: {b.get('message')}")
        else:
            lines += ['## USB Portability Blockers','','No USB portability blockers found for current web bridge workflows.']
        if warnings:
            lines += ['','## Warnings','']
            for w in warnings:
                lines.append(f"- {w.get('name')}: {w.get('message')}")
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(reports)}
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        if active_project:
            timeline(active_project,f'Portable readiness exported: {md_path.name}')

    return report


def canonical_path_key(p):
    try:
        return os.path.normcase(os.path.realpath(str(Path(p).resolve())))
    except Exception:
        try:
            return os.path.normcase(os.path.realpath(str(p)))
        except Exception:
            return str(p).lower()

def bytes_human(n):
    try:
        n=float(n)
    except Exception:
        return str(n)
    units=['B','KB','MB','GB','TB']
    i=0
    while n>=1024 and i<len(units)-1:
        n/=1024
        i+=1
    return f"{n:.2f} {units[i]}"

def model_duplicate_truth_report(d=None):
    d=d or {}
    export=bool(d.get('export',True))
    model_dirs=[
        ROOT/'Models',
        ROOT/'models',
        ROOT/'AI'/'models',
        ROOT/'models_local'
    ]

    dir_records=[]
    scanned_dirs=[]
    skipped_alias_dirs=[]
    seen_dir_keys={}

    for md in model_dirs:
        exists=md.exists()
        key=canonical_path_key(md) if exists else ''
        rec={'path':str(md),'exists':exists,'canonical':key,'scanned':False,'alias_of':''}
        if exists:
            if key in seen_dir_keys:
                rec['alias_of']=seen_dir_keys[key]
                skipped_alias_dirs.append(rec)
            else:
                seen_dir_keys[key]=str(md)
                rec['scanned']=True
                scanned_dirs.append(md)
        dir_records.append(rec)

    # Scan only canonical unique directories to avoid Windows Models/models double count.
    raw_models=[]
    scan_errors=[]
    for md in scanned_dirs:
        try:
            for p in md.rglob('*.gguf'):
                try:
                    st=p.stat()
                    raw_models.append({
                        'path':str(p),
                        'relative':str(p.relative_to(ROOT)).replace('\\','/') if ROOT.resolve() in p.resolve().parents else str(p),
                        'canonical':canonical_path_key(p),
                        'name':p.name,
                        'name_key':p.name.lower(),
                        'size':st.st_size,
                        'size_human':bytes_human(st.st_size),
                        'parent':str(p.parent)
                    })
                except Exception as e:
                    scan_errors.append({'path':str(p),'error':str(e)})
        except Exception as e:
            scan_errors.append({'path':str(md),'error':str(e)})

    # Remove accidental same physical path duplicates if they still occur.
    physical_map={}
    physical_aliases=[]
    for m in raw_models:
        k=m.get('canonical')
        physical_map.setdefault(k,[]).append(m)
    physical_models=[]
    for k,items in physical_map.items():
        physical_models.append(items[0])
        if len(items)>1:
            physical_aliases.append({'canonical':k,'copies':items})

    # True duplicates = same filename + same byte size but different canonical files.
    dup_key_map={}
    for m in physical_models:
        key=(m.get('name_key'),m.get('size'))
        dup_key_map.setdefault(key,[]).append(m)

    true_duplicates=[]
    duplicate_bytes=0
    for (name,size),items in dup_key_map.items():
        if len(items)>1:
            copies=items[1:]
            duplicate_bytes += sum(int(x.get('size') or 0) for x in copies)
            true_duplicates.append({
                'name':name,
                'size':size,
                'size_human':bytes_human(size),
                'kept_suggestion':items[0],
                'duplicate_candidates':copies,
                'all_copies':items,
                'duplicate_bytes':sum(int(x.get('size') or 0) for x in copies),
                'duplicate_bytes_human':bytes_human(sum(int(x.get('size') or 0) for x in copies))
            })

    unique_models=len(dup_key_map)
    physical_count=len(physical_models)

    cleanup_plan=[]
    if skipped_alias_dirs:
        cleanup_plan.append({
            'priority':'info',
            'action':'No cleanup needed for folder casing aliases',
            'reason':'One or more model folder paths resolve to the same physical folder. The scanner now skips alias directories before counting models.',
            'items':skipped_alias_dirs
        })
    if true_duplicates:
        cleanup_plan.append({
            'priority':'review',
            'action':'Review confirmed duplicate GGUF files before any future cleanup action',
            'reason':'These are separate physical files with the same filename and byte size. Do not delete until a future user-approved action confirms which copy to keep.',
            'estimated_space_recoverable':duplicate_bytes,
            'estimated_space_recoverable_human':bytes_human(duplicate_bytes),
            'items':true_duplicates
        })
    else:
        cleanup_plan.append({
            'priority':'safe',
            'action':'No confirmed duplicate model deletion recommended',
            'reason':'No true duplicate GGUF files were found after canonical folder and physical path detection.',
            'items':[]
        })

    folder_alias_count=len(skipped_alias_dirs)
    physical_alias_count=sum(len(x.get('copies',[]))-1 for x in physical_aliases)
    true_duplicate_count=sum(len(x.get('duplicate_candidates',[])) for x in true_duplicates)

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Model Duplicate Truth Check + Cleanup Planner',
        'read_only':True,
        'report_only':True,
        'root':str(ROOT),
        'summary':{
            'tracked_model_dirs':len(model_dirs),
            'existing_model_dirs':sum(1 for x in dir_records if x.get('exists')),
            'scanned_canonical_dirs':len(scanned_dirs),
            'skipped_alias_dirs':folder_alias_count,
            'raw_scan_models':len(raw_models),
            'physical_model_files':physical_count,
            'unique_model_keys':unique_models,
            'physical_alias_duplicate_copies':physical_alias_count,
            'true_duplicate_groups':len(true_duplicates),
            'true_duplicate_copies':true_duplicate_count,
            'estimated_true_duplicate_bytes':duplicate_bytes,
            'estimated_true_duplicate_bytes_human':bytes_human(duplicate_bytes),
            'scan_errors':len(scan_errors)
        },
        'model_dirs':dir_records,
        'skipped_alias_dirs':skipped_alias_dirs,
        'physical_aliases':physical_aliases,
        'models':physical_models,
        'true_duplicates':true_duplicates,
        'cleanup_plan':cleanup_plan,
        'scan_errors':scan_errors
    }

    if export:
        reports=FOLDERS.get('model_reports',ROOT/'Reports'/'Models')
        reports.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=reports/f'Model_Duplicate_Truth_{stamp}.json'
        md_path=reports/f'Model_Duplicate_Truth_{stamp}.md'
        jwrite(json_path,report)
        s=report['summary']
        lines=[
            '# Kayock Model Duplicate Truth Check + Cleanup Planner','',
            f"Created: {report['created']}",
            f"Root: {report['root']}",
            f"Read only: {report['read_only']}",
            f"Report only: {report['report_only']}",
            '',
            '## Summary','',
            f"- Tracked model dirs: {s['tracked_model_dirs']}",
            f"- Existing model dirs: {s['existing_model_dirs']}",
            f"- Scanned canonical dirs: {s['scanned_canonical_dirs']}",
            f"- Skipped alias dirs: {s['skipped_alias_dirs']}",
            f"- Raw scan models: {s['raw_scan_models']}",
            f"- Physical model files: {s['physical_model_files']}",
            f"- Unique model keys: {s['unique_model_keys']}",
            f"- True duplicate groups: {s['true_duplicate_groups']}",
            f"- True duplicate copies: {s['true_duplicate_copies']}",
            f"- Estimated true duplicate space: {s['estimated_true_duplicate_bytes_human']}",
            f"- Scan errors: {s['scan_errors']}",
            '',
            '## Model Directories',''
        ]
        for drec in dir_records:
            alias=f" alias of {drec.get('alias_of')}" if drec.get('alias_of') else ''
            lines.append(f"- {drec.get('path')} | exists={drec.get('exists')} | scanned={drec.get('scanned')}{alias}")
        lines += ['','## Cleanup Plan','']
        for item in cleanup_plan:
            lines += [f"### {item.get('priority','info').upper()}: {item.get('action')}",'',item.get('reason',''),'']
            if item.get('estimated_space_recoverable_human'):
                lines.append(f"Estimated space recoverable: {item.get('estimated_space_recoverable_human')}")
                lines.append('')
        if true_duplicates:
            lines += ['## Confirmed Duplicate Candidates','']
            for group in true_duplicates:
                lines.append(f"### {group.get('name')} ({group.get('size_human')})")
                lines.append(f"Suggested keep: {group.get('kept_suggestion',{}).get('path')}")
                for c in group.get('duplicate_candidates',[]):
                    lines.append(f"- Candidate duplicate: {c.get('path')}")
                lines.append('')
        else:
            lines += ['## Confirmed Duplicate Candidates','','No confirmed duplicate GGUF files found.']
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(reports)}
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        if active_project:
            timeline(active_project,f'Model duplicate truth report exported: {md_path.name}')

    return report


def repair_action_log(action_id, result, dry_run=False):
    reports=FOLDERS.get('repair_reports',ROOT/'Reports'/'RepairActions')
    reports.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    verification=result.get('verification') or {}
    payload={
        'ok':bool(result.get('ok')),
        'created':now(),
        'title':'Kayock Repair Bay Action Log',
        'action_id':action_id,
        'dry_run':bool(dry_run),
        'result':result,
        'verification':verification,
        'verified':bool(verification.get('ok')) if verification else False,
        'read_only':False,
        'user_approved_action':not dry_run
    }
    json_path=reports/f'Repair_Action_{slug(action_id)}_{stamp}.json'
    md_path=reports/f'Repair_Action_{slug(action_id)}_{stamp}.md'
    jwrite(json_path,payload)
    lines=[
        '# Kayock Repair Bay Action Log','',
        f"Created: {payload['created']}",
        f"Action: {action_id}",
        f"OK: {payload['ok']}",
        f"Verified: {payload['verified']}",
        f"Dry run: {payload['dry_run']}",
        f"User approved action: {payload['user_approved_action']}",
        '',
        '## Message','',
        result.get('message','')
    ]
    if verification:
        lines += [
            '',
            '## Verification',
            '',
            f"Verification OK: {verification.get('ok')}",
            f"Message: {verification.get('message','')}",
            ''
        ]
        for check in verification.get('checks',[]):
            status='PASS' if check.get('ok') else 'FAIL'
            lines.append(f"- **{status}** `{check.get('id','check')}` — {check.get('message','')}")
    lines += [
        '',
        '## Details','',
        '```json',
        json.dumps(result,indent=2,ensure_ascii=False),
        '```'
    ]
    md_path.write_text('\n'.join(lines),encoding='utf-8')
    payload['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(reports)}
    return payload

def _verify_inside_root(path_text):
    if not path_text:
        return None, False, 'No path provided.'
    try:
        p=Path(path_text)
        rp=p.resolve()
        rr=ROOT.resolve()
        if not (rp==rr or rr in rp.parents):
            return p, False, 'Path is outside FOXAI root.'
        return p, True, ''
    except Exception as e:
        return Path(path_text), False, f'Invalid path: {e}'

def verify_repair_action_result(action_id, result):
    checks=[]
    def add(cid, ok, message, path=''):
        checks.append({'id':cid,'ok':bool(ok),'message':message,'path':path})

    action_ok=bool(result.get('ok'))
    add('action_result_ok',action_ok,'Action reported OK.' if action_ok else result.get('message','Action reported failure.'))

    if action_id=='refresh_root_manifest':
        target=result.get('target') or str(ROOT/'manifest.json')
        p,inside,msg=_verify_inside_root(target)
        add('target_inside_root',inside,msg or 'Target is inside FOXAI root.',target)
        if inside:
            exists=p.exists() and p.is_file()
            add('manifest_exists',exists,'Root manifest file exists.' if exists else 'Root manifest file is missing.',str(p))
            if exists:
                try:
                    raw=p.read_text(encoding='utf-8',errors='replace')
                    data=json.loads(raw)
                    add('manifest_json_valid',True,'Root manifest is valid JSON.',str(p))
                    add('manifest_identity',data.get('id')=='kayock-command-os' and data.get('name')=='Kayock Command OS','Root manifest identity fields are present.' if data.get('id')=='kayock-command-os' and data.get('name')=='Kayock Command OS' else 'Root manifest identity fields were not as expected.',str(p))
                except Exception as e:
                    add('manifest_json_valid',False,f'Root manifest could not be parsed: {e}',str(p))
        backup=result.get('backup') or ''
        if backup:
            bp,binroot,bmsg=_verify_inside_root(backup)
            add('backup_inside_root',binroot,bmsg or 'Backup path is inside FOXAI root.',backup)
            add('backup_exists',bool(binroot and bp.exists() and bp.is_file()),'Backup file exists.' if binroot and bp.exists() and bp.is_file() else 'Backup file missing.',backup)
        validation=result.get('validation') or validate_extensions()
        add('extension_validation',bool(validation.get('ok') and not validation.get('problems')),(validation.get('message') or 'Extension manifest validation complete.'))

    elif action_id=='refresh_engineering_readme':
        target=result.get('target') or str(ROOT/'Departments'/'Engineering'/'README.md')
        p,inside,msg=_verify_inside_root(target)
        add('target_inside_root',inside,msg or 'Target is inside FOXAI root.',target)
        if inside:
            exists=p.exists() and p.is_file()
            add('readme_exists',exists,'Engineering README exists.' if exists else 'Engineering README is missing.',str(p))
            if exists:
                try:
                    raw=p.read_text(encoding='utf-8',errors='replace')
                    add('readme_readable',True,'Engineering README is readable.',str(p))
                    add('readme_nonempty',len(raw.strip())>40,'Engineering README has content.' if len(raw.strip())>40 else 'Engineering README is unexpectedly short.',str(p))
                    add('readme_heading',raw.lstrip().startswith('#'),'Engineering README begins with a Markdown heading.' if raw.lstrip().startswith('#') else 'Engineering README does not begin with a Markdown heading.',str(p))
                except Exception as e:
                    add('readme_readable',False,f'Engineering README could not be read: {e}',str(p))
        backup=result.get('backup') or ''
        if backup:
            bp,binroot,bmsg=_verify_inside_root(backup)
            add('backup_inside_root',binroot,bmsg or 'Backup path is inside FOXAI root.',backup)
            add('backup_exists',bool(binroot and bp.exists() and bp.is_file()),'Backup file exists.' if binroot and bp.exists() and bp.is_file() else 'Backup file missing.',backup)
        else:
            add('backup_recorded',False,'No backup path was recorded for README refresh.')

    elif action_id=='generate_optional_dependency_plan':
        target=result.get('target') or str(FOLDERS.get('repair_reports',ROOT/'Reports'/'RepairActions')/'Optional_Dependency_Install_Plan.md')
        p,inside,msg=_verify_inside_root(target)
        add('target_inside_root',inside,msg or 'Target is inside FOXAI root.',target)
        if inside:
            exists=p.exists() and p.is_file()
            add('plan_exists',exists,'Optional dependency plan exists.' if exists else 'Optional dependency plan is missing.',str(p))
            if exists:
                try:
                    raw=p.read_text(encoding='utf-8',errors='replace')
                    add('plan_readable',True,'Optional dependency plan is readable.',str(p))
                    add('plan_declares_no_install','No packages were installed' in raw,'Plan declares no packages were installed.' if 'No packages were installed' in raw else 'Plan does not clearly say no packages were installed.',str(p))
                    add('plan_uses_portable_python','Z:\\FOXAI\\env\\python\\python.exe' in raw,'Plan references the portable Python runtime.' if 'Z:\\FOXAI\\env\\python\\python.exe' in raw else 'Plan does not reference the portable Python runtime.',str(p))
                    add('plan_blocks_auto_run','Do not run this automatically' in raw,'Plan blocks automatic installation.' if 'Do not run this automatically' in raw else 'Plan does not clearly block automatic installation.',str(p))
                except Exception as e:
                    add('plan_readable',False,f'Optional dependency plan could not be read: {e}',str(p))

    elif action_id=='create_missing_standard_folders':
        standard_folders=[
            ROOT/'Reports'/'RepairActions',
            ROOT/'Reports'/'Models',
            ROOT/'Reports'/'PortableReadiness',
            ROOT/'Backups'/'GeneratedFiles',
            ROOT/'LegacyLaunchers',
            ROOT/'Prompts',
            ROOT/'NovelForge',
            ROOT/'NovelForge'/'Exports',
            ROOT/'Extensions',
            ROOT/'Modules',
            ROOT/'Library'
        ]
        for folder in standard_folders:
            add('folder_exists',folder.exists() and folder.is_dir(),'Folder exists.' if folder.exists() and folder.is_dir() else 'Folder missing.',str(folder))

    elif action_id=='move_suspicious_root_launchers':
        moved=result.get('moved') or []
        if moved:
            for item in moved:
                src=Path(item.get('from',''))
                dst=Path(item.get('to',''))
                add('moved_source_absent',not src.exists(),'Original suspicious launcher is no longer at root.' if not src.exists() else 'Original suspicious launcher still exists.',str(src))
                add('moved_destination_exists',dst.exists() and dst.is_file(),'Moved launcher exists in LegacyLaunchers.' if dst.exists() and dst.is_file() else 'Moved launcher destination missing.',str(dst))
        else:
            add('no_suspicious_launchers_remaining',not any(p.name.lower().startswith('@echo off') for p in list(ROOT.glob('*.bat'))+list(ROOT.glob('*.cmd'))),'No suspicious root launcher filenames remain.')

    else:
        add('known_action',False,f'No verification recipe exists for action: {action_id}')

    ok=bool(checks) and all(c.get('ok') for c in checks)
    failed=[c for c in checks if not c.get('ok')]
    return {
        'ok':ok,
        'checked':len(checks),
        'passed':len(checks)-len(failed),
        'failed':len(failed),
        'message':f"Post-action verification {'passed' if ok else 'failed'}: {len(checks)-len(failed)}/{len(checks)} check(s) passed.",
        'checks':checks
    }

def repair_action_plan(d=None):
    d=d or {}
    actions=[]

    def add_action(action_id,title,description,risk='low',available=True,reason='',writes=None):
        actions.append({
            'id':action_id,
            'title':title,
            'description':description,
            'risk':risk,
            'available':bool(available),
            'reason':reason,
            'writes':writes or [],
            'requires_confirmation':True,
            'safety':['Preview first','User confirmation required','Repair log created','No package installs','No model deletion']
        })

    standard_folders=[
        ROOT/'Reports'/'RepairActions',
        ROOT/'Reports'/'Models',
        ROOT/'Reports'/'PortableReadiness',
        ROOT/'Backups'/'GeneratedFiles',
        ROOT/'LegacyLaunchers',
        ROOT/'Prompts',
        ROOT/'NovelForge',
        ROOT/'NovelForge'/'Exports',
        ROOT/'Extensions',
        ROOT/'Modules',
        ROOT/'Library'
    ]
    missing=[str(p) for p in standard_folders if not p.exists()]
    add_action(
        'create_missing_standard_folders',
        'Create Missing Standard Folders',
        'Creates safe standard Kayock folders that are missing. It does not delete, move, or overwrite files.',
        'low',
        bool(missing),
        f"{len(missing)} folder(s) missing." if missing else 'No standard folders are missing.',
        missing
    )

    root_manifest=ROOT/'manifest.json'
    add_action(
        'refresh_root_manifest',
        'Refresh Root Project Manifest',
        'Regenerates Z:\\FOXAI\\manifest.json from current module and scan state. Existing manifest is backed up before overwrite.',
        'low',
        True,
        'Available. Existing file will be backed up first.' if root_manifest.exists() else 'Available. File does not exist yet.',
        [str(root_manifest)]
    )

    readme=ROOT/'Departments'/'Engineering'/'README.md'
    add_action(
        'refresh_engineering_readme',
        'Refresh Engineering README',
        'Regenerates the Engineering README from the Engineering manifest. Existing README is backed up before overwrite.',
        'low',
        (ROOT/'Departments'/'Engineering'/'manifest.json').exists(),
        'Available. Existing README will be backed up first.' if readme.exists() else 'Available if Engineering manifest exists.',
        [str(readme)]
    )

    dep_plan=FOLDERS.get('repair_reports',ROOT/'Reports'/'RepairActions')/'Optional_Dependency_Install_Plan.md'
    add_action(
        'generate_optional_dependency_plan',
        'Generate Optional Dependency Plan',
        'Writes a report-only plan for optional Repair Bay tools. It does not install packages.',
        'low',
        True,
        'Available. No installs will run.',
        [str(dep_plan)]
    )

    suspicious=[]
    for p in list(ROOT.glob('*.bat'))+list(ROOT.glob('*.cmd')):
        if p.name.lower().startswith('@echo off'):
            suspicious.append(str(p))
    add_action(
        'move_suspicious_root_launchers',
        'Move Suspicious Root Launchers',
        'Moves suspicious root BAT/CMD files into LegacyLaunchers with safer names. No deletion.',
        'low',
        bool(suspicious),
        f"{len(suspicious)} suspicious launcher(s) found." if suspicious else 'No suspicious root launcher filenames found.',
        suspicious
    )

    plan={
        'ok':True,
        'created':now(),
        'title':'Kayock Repair Bay Action Plan',
        'read_only':True,
        'report_only':True,
        'summary':{
            'actions':len(actions),
            'available':sum(1 for x in actions if x.get('available')),
            'low_risk':sum(1 for x in actions if x.get('risk')=='low'),
            'blocked':sum(1 for x in actions if not x.get('available'))
        },
        'actions':actions,
        'rules':[
            'No action runs without explicit user confirmation.',
            'Actions are applied one at a time.',
            'Backups are created before overwriting generated files.',
            'Every action writes a repair log.',
            'No model deletion.',
            'No dependency installation.'
        ]
    }

    try:
        reports=FOLDERS.get('repair_reports',ROOT/'Reports'/'RepairActions')
        plans_dir=reports/'Plans'
        plans_dir.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=plans_dir/f'Repair_Action_Plan_{stamp}.json'
        md_path=plans_dir/f'Repair_Action_Plan_{stamp}.md'
        jwrite(json_path,plan)
        lines=[
            '# Kayock Repair Bay Action Plan','',
            f"Created: {plan['created']}",
            f"Read only: {plan['read_only']}",
            f"Report only: {plan['report_only']}",
            '',
            '## Summary','',
            f"- Actions: {plan['summary']['actions']}",
            f"- Available: {plan['summary']['available']}",
            f"- Blocked: {plan['summary']['blocked']}",
            f"- Low risk: {plan['summary']['low_risk']}",
            '',
            '## Safety Rules',''
        ]
        for rule in plan.get('rules',[]):
            lines.append(f"- {rule}")
        lines += ['','## Actions','']
        for a in actions:
            lines += [
                f"### {'AVAILABLE' if a.get('available') else 'BLOCKED'}: {a.get('title')}",
                '',
                f"- ID: `{a.get('id')}`",
                f"- Risk: `{a.get('risk')}`",
                f"- Available: `{a.get('available')}`",
                f"- Reason: {a.get('reason','')}",
                '',
                a.get('description',''),
                '',
                'Writes:',
            ]
            writes=a.get('writes') or []
            if writes:
                for w in writes:
                    lines.append(f"- `{w}`")
            else:
                lines.append("- none")
            lines.append('')
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        plan['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(plans_dir)}
    except Exception as e:
        plan['export_error']=str(e)

    return plan

def apply_repair_action(d):
    action_id=(d.get('action_id') or d.get('id') or '').strip()
    confirm=str(d.get('confirm') or '').strip().upper()
    if confirm not in {'YES','CONFIRM','APPLY'}:
        return {'ok':False,'message':'Confirmation required. Send confirm=YES to apply a Repair Bay action.'}

    result={'ok':False,'message':'Unknown action.','action_id':action_id}

    if action_id=='create_missing_standard_folders':
        standard_folders=[
            ROOT/'Reports'/'RepairActions',
            ROOT/'Reports'/'Models',
            ROOT/'Reports'/'PortableReadiness',
            ROOT/'Backups'/'GeneratedFiles',
            ROOT/'LegacyLaunchers',
            ROOT/'Prompts',
            ROOT/'NovelForge',
            ROOT/'NovelForge'/'Exports',
            ROOT/'Extensions',
            ROOT/'Modules',
            ROOT/'Library'
        ]
        created=[]
        existed=[]
        errors=[]
        for p in standard_folders:
            try:
                if p.exists():
                    existed.append(str(p))
                else:
                    p.mkdir(parents=True,exist_ok=True)
                    created.append(str(p))
            except Exception as e:
                errors.append({'path':str(p),'error':str(e)})
        result={'ok':len(errors)==0,'message':f"Created {len(created)} folder(s); {len(existed)} already existed; {len(errors)} error(s).",'created':created,'existed':existed,'errors':errors}

    elif action_id=='refresh_root_manifest':
        try:
            result=apply_project_manifest({})
            result['action_id']=action_id
        except Exception as e:
            result={'ok':False,'message':f'Root manifest refresh failed: {e}','action_id':action_id}

    elif action_id=='refresh_engineering_readme':
        try:
            result=apply_department_readme({'key':'engineering'})
            result['action_id']=action_id
        except Exception as e:
            result={'ok':False,'message':f'Engineering README refresh failed: {e}','action_id':action_id}

    elif action_id=='generate_optional_dependency_plan':
        try:
            reports=FOLDERS.get('repair_reports',ROOT/'Reports'/'RepairActions')
            reports.mkdir(parents=True,exist_ok=True)
            target=reports/'Optional_Dependency_Install_Plan.md'
            content=f"""# Kayock Optional Dependency Install Plan

Generated: {now()}

This is a planning document only. No packages were installed.

## Safety Rules

- Install optional tools only after core workflows are stable.
- Prefer the portable Python runtime: `Z:\\FOXAI\\env\\python\\python.exe`
- Keep installation commands user-approved.
- Install to the portable environment, not the system Python.
- Export a verification report after installation.

## Suggested Later Install Order

1. `ruff` — fast linting and formatting checks.
2. `black` — Python formatting.
3. `mypy` — static type checking.
4. `pip-audit` — dependency vulnerability scanning.
5. `cyclonedx-bom` — SBOM generation.
6. `pydeps` — import graph visualization.
7. `grimp` — import graph analysis.
8. `import-linter` — architecture boundary enforcement.

## Future User-Approved Command Pattern

```bat
Z:\\FOXAI\\env\\python\\python.exe -m pip install ruff black mypy
```

Do not run this automatically. Use a future Repair Bay approved action with confirmation and logging.
"""
            write=safe_write_generated_file(target,content,backup=True)
            result={'ok':write.get('ok'), 'message':'Optional dependency plan written.' if write.get('ok') else write.get('message','Write failed.'), 'target':write.get('path'), 'backup':write.get('backup'), 'action_id':action_id}
        except Exception as e:
            result={'ok':False,'message':f'Optional dependency plan failed: {e}','action_id':action_id}

    elif action_id=='move_suspicious_root_launchers':
        legacy=ROOT/'LegacyLaunchers'
        legacy.mkdir(parents=True,exist_ok=True)
        moved=[]
        errors=[]
        for p in list(ROOT.glob('*.bat'))+list(ROOT.glob('*.cmd')):
            if p.name.lower().startswith('@echo off'):
                try:
                    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
                    dest=legacy/f'OLD_SUSPICIOUS_LAUNCHER_{stamp}{p.suffix.lower()}'
                    p.replace(dest)
                    moved.append({'from':str(p),'to':str(dest)})
                except Exception as e:
                    errors.append({'path':str(p),'error':str(e)})
        result={'ok':len(errors)==0,'message':f"Moved {len(moved)} suspicious launcher(s); {len(errors)} error(s).",'moved':moved,'errors':errors,'action_id':action_id}

    result.setdefault('action_id',action_id)
    original_ok=bool(result.get('ok'))
    verification=verify_repair_action_result(action_id,result)
    result['verification']=verification
    result['verified']=bool(verification.get('ok'))
    result['ok']=bool(original_ok and verification.get('ok'))
    if original_ok and not verification.get('ok'):
        result['message']=result.get('message','Action completed, but verification failed.')+' Verification failed after action.'
    log=repair_action_log(action_id,result,dry_run=False)
    result['log']=log.get('exported',{})
    if active_project:
        timeline(active_project,f"Repair Bay action applied: {action_id} ({'OK' if result.get('ok') else 'FAILED'}; verified={'YES' if result.get('verified') else 'NO'})")
    return result


def repair_action_history(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    action_filter=(d.get('action_filter') or d.get('filter') or '').strip().lower()
    limit=int(d.get('limit') or 200)
    reports=FOLDERS.get('repair_reports',ROOT/'Reports'/'RepairActions')
    reports.mkdir(parents=True,exist_ok=True)

    logs=[]
    errors=[]
    for p in sorted(reports.glob('Repair_Action_*.json'), key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True):
        try:
            data=json.loads(p.read_text(encoding='utf-8',errors='replace'))
            action_id=(data.get('action_id') or data.get('result',{}).get('action_id') or '').strip()
            if action_filter and action_filter not in action_id.lower():
                continue
            result=data.get('result') or {}
            verification=data.get('verification') or result.get('verification') or {}
            target=result.get('target') or ''
            backup=result.get('backup') or ''
            md_path=p.with_suffix('.md')
            verified_state='not_recorded'
            if verification:
                verified_state='passed' if verification.get('ok') else 'failed'
            item={
                'path':str(p),
                'markdown':str(md_path) if md_path.exists() else '',
                'created':data.get('created',''),
                'title':data.get('title',''),
                'action_id':action_id,
                'ok':bool(data.get('ok')),
                'dry_run':bool(data.get('dry_run')),
                'user_approved_action':bool(data.get('user_approved_action')),
                'verified':bool(verification.get('ok')) if verification else False,
                'verified_state':verified_state,
                'verification':verification,
                'message':result.get('message',''),
                'target':target,
                'backup':backup,
                'result':result,
                'size':p.stat().st_size
            }
            logs.append(item)
            if len(logs)>=limit:
                break
        except Exception as e:
            errors.append({'path':str(p),'error':str(e)})

    by_action={}
    for item in logs:
        key=item.get('action_id') or 'unknown'
        by_action.setdefault(key,{'action_id':key,'count':0,'ok':0,'failed':0,'verified':0,'verification_failed':0,'not_recorded':0,'last_created':''})
        by_action[key]['count']+=1
        if item.get('ok'):
            by_action[key]['ok']+=1
        else:
            by_action[key]['failed']+=1
        if item.get('verified_state')=='passed':
            by_action[key]['verified']+=1
        elif item.get('verified_state')=='failed':
            by_action[key]['verification_failed']+=1
        else:
            by_action[key]['not_recorded']+=1
        if not by_action[key]['last_created'] or item.get('created','')>by_action[key]['last_created']:
            by_action[key]['last_created']=item.get('created','')

    verification_passed=sum(1 for x in logs if x.get('verified_state')=='passed')
    verification_failed=sum(1 for x in logs if x.get('verified_state')=='failed')
    verification_not_recorded=sum(1 for x in logs if x.get('verified_state')=='not_recorded')
    summary={
        'logs':len(logs),
        'ok':sum(1 for x in logs if x.get('ok')),
        'failed':sum(1 for x in logs if not x.get('ok')),
        'dry_runs':sum(1 for x in logs if x.get('dry_run')),
        'user_approved':sum(1 for x in logs if x.get('user_approved_action')),
        'actions':len(by_action),
        'errors':len(errors),
        'verification_passed':verification_passed,
        'verification_failed':verification_failed,
        'verification_not_recorded':verification_not_recorded,
        'last_action':logs[0].get('action_id','') if logs else '',
        'last_created':logs[0].get('created','') if logs else ''
    }

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Repair Bay Action History',
        'read_only':True,
        'report_only':True,
        'filter':action_filter,
        'summary':summary,
        'by_action':list(by_action.values()),
        'logs':logs,
        'errors':errors,
        'folder':str(reports)
    }

    if export:
        history_dir=reports/'History'
        history_dir.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=history_dir/f'Repair_Action_History_{stamp}.json'
        md_path=history_dir/f'Repair_Action_History_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Repair Bay Action History','',
            f"Created: {report['created']}",
            f"Folder: {report['folder']}",
            f"Filter: {action_filter or 'none'}",
            '',
            '## Summary','',
            f"- Logs: {summary['logs']}",
            f"- OK: {summary['ok']}",
            f"- Failed: {summary['failed']}",
            f"- Dry runs: {summary['dry_runs']}",
            f"- User approved: {summary['user_approved']}",
            f"- Action types: {summary['actions']}",
            f"- Parse errors: {summary['errors']}",
            f"- Verification passed: {summary['verification_passed']}",
            f"- Verification failed: {summary['verification_failed']}",
            f"- Verification not recorded: {summary['verification_not_recorded']}",
            f"- Last action: {summary['last_action']}",
            f"- Last created: {summary['last_created']}",
            '',
            '## By Action',''
        ]
        for a in report['by_action']:
            lines.append(f"- `{a.get('action_id')}` — count: {a.get('count')}, ok: {a.get('ok')}, failed: {a.get('failed')}, verified: {a.get('verified')}, verification failed: {a.get('verification_failed')}, not recorded: {a.get('not_recorded')}, last: {a.get('last_created')}")
        lines += ['','## Logs','']
        for l in logs:
            v=l.get('verification') or {}
            lines += [
                f"### {'OK' if l.get('ok') else 'FAILED'}: {l.get('action_id')}",
                '',
                f"- Created: {l.get('created')}",
                f"- Dry run: {l.get('dry_run')}",
                f"- User approved: {l.get('user_approved_action')}",
                f"- Verification: {l.get('verified_state')}",
                f"- Verification message: {v.get('message','') if v else 'not recorded'}",
                f"- Message: {l.get('message')}",
                f"- Target: `{l.get('target') or ''}`",
                f"- Backup: `{l.get('backup') or ''}`",
                f"- JSON: `{l.get('path')}`",
                f"- Markdown: `{l.get('markdown') or ''}`",
                ''
            ]
            if v:
                lines.append('Verification checks:')
                for c in v.get('checks',[]):
                    status='PASS' if c.get('ok') else 'FAIL'
                    lines.append(f"- **{status}** `{c.get('id','check')}` — {c.get('message','')}")
                lines.append('')
        if errors:
            lines += ['## Parse Errors','']
            for e in errors:
                lines.append(f"- `{e.get('path')}`: {e.get('error')}")
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(history_dir)}

    return report

def _backup_type_from_name(name):
    n=name.lower()
    if n.startswith('manifest_'):
        return 'root_manifest'
    if n.startswith('readme_'):
        return 'engineering_readme'
    if n.startswith('optional_dependency_install_plan_'):
        return 'optional_dependency_plan'
    if n.endswith('.json'):
        return 'json_backup'
    if n.endswith('.md'):
        return 'markdown_backup'
    if n.endswith('.txt'):
        return 'text_backup'
    return 'other'

def _infer_target_from_backup_name(name):
    n=name.lower()
    if n.startswith('manifest_'):
        return str(ROOT/'manifest.json')
    if n.startswith('readme_'):
        return str(ROOT/'Departments'/'Engineering'/'README.md')
    if n.startswith('optional_dependency_install_plan_'):
        return str(ROOT/'Reports'/'RepairActions'/'Optional_Dependency_Install_Plan.md')
    return ''

def _repair_log_backup_index():
    reports=FOLDERS.get('repair_reports',ROOT/'Reports'/'RepairActions')
    idx={}
    errors=[]
    for p in reports.glob('Repair_Action_*.json'):
        try:
            data=json.loads(p.read_text(encoding='utf-8',errors='replace'))
            result=data.get('result') or {}
            backup=result.get('backup') or ''
            if not backup:
                continue
            bp=str(Path(backup))
            md_path=p.with_suffix('.md')
            verification=data.get('verification') or result.get('verification') or {}
            idx[bp.lower()]={
                'action_id':data.get('action_id') or result.get('action_id') or '',
                'action_created':data.get('created',''),
                'action_ok':bool(data.get('ok')),
                'verified':bool(verification.get('ok')) if verification else False,
                'verified_state':'passed' if verification.get('ok') else ('failed' if verification else 'not_recorded'),
                'target':result.get('target') or '',
                'message':result.get('message') or '',
                'log_json':str(p),
                'log_markdown':str(md_path) if md_path.exists() else ''
            }
        except Exception as e:
            errors.append({'path':str(p),'error':str(e)})
    return idx,errors

def backup_vault_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    q=(d.get('query') or d.get('filter') or '').strip().lower()
    limit=int(d.get('limit') or 500)
    vault=FOLDERS.get('file_backups',ROOT/'Backups'/'GeneratedFiles')
    vault.mkdir(parents=True,exist_ok=True)

    log_index,log_errors=_repair_log_backup_index()
    backups=[]
    scan_errors=[]
    for p in sorted([x for x in vault.rglob('*') if x.is_file()], key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True):
        try:
            st=p.stat()
            assoc=log_index.get(str(p).lower()) or {}
            btype=_backup_type_from_name(p.name)
            inferred=_infer_target_from_backup_name(p.name)
            backup_stamp=''
            stamp_match=re.search(r'(20\d{6}_\d{6})',p.name)
            if stamp_match:
                try:
                    backup_stamp=datetime.strptime(stamp_match.group(1),'%Y%m%d_%H%M%S').isoformat(timespec='seconds')
                except Exception:
                    backup_stamp=stamp_match.group(1)
            item={
                'path':str(p),
                'name':p.name,
                'relative':str(p.relative_to(vault)) if vault in p.parents or p.parent==vault else p.name,
                'type':btype,
                'size':st.st_size,
                'file_modified_time':datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds'),
                'modified':datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds'),
                'backup_filename_time':backup_stamp,
                'original_target':assoc.get('target') or inferred,
                'action_id':assoc.get('action_id') or '',
                'action_created':assoc.get('action_created') or '',
                'action_ok':assoc.get('action_ok') if assoc else None,
                'verified':assoc.get('verified') if assoc else False,
                'verified_state':assoc.get('verified_state') if assoc else 'unassociated',
                'message':assoc.get('message') or '',
                'log_json':assoc.get('log_json') or '',
                'log_markdown':assoc.get('log_markdown') or '',
                'associated':bool(assoc),
                'timestamp_note':'Windows Date modified may reflect the original file metadata preserved during backup, not the backup creation time.'
            }
            blob=' '.join(str(item.get(k,'')) for k in ['name','type','original_target','action_id','message','path']).lower()
            if q and q not in blob:
                continue
            backups.append(item)
            if len(backups)>=limit:
                break
        except Exception as e:
            scan_errors.append({'path':str(p),'error':str(e)})

    by_type={}
    by_action={}
    for b in backups:
        by_type.setdefault(b['type'],{'type':b['type'],'count':0,'bytes':0})
        by_type[b['type']]['count']+=1
        by_type[b['type']]['bytes']+=b['size']
        key=b.get('action_id') or 'unassociated'
        by_action.setdefault(key,{'action_id':key,'count':0,'bytes':0,'verified':0,'unverified':0})
        by_action[key]['count']+=1
        by_action[key]['bytes']+=b['size']
        if b.get('verified_state')=='passed':
            by_action[key]['verified']+=1
        else:
            by_action[key]['unverified']+=1

    total_bytes=sum(b['size'] for b in backups)
    summary={
        'backups':len(backups),
        'bytes':total_bytes,
        'associated':sum(1 for b in backups if b.get('associated')),
        'unassociated':sum(1 for b in backups if not b.get('associated')),
        'verified':sum(1 for b in backups if b.get('verified_state')=='passed'),
        'types':len(by_type),
        'actions':len(by_action),
        'scan_errors':len(scan_errors),
        'log_errors':len(log_errors),
        'latest_backup':backups[0].get('name','') if backups else '',
        'latest_file_modified_time':backups[0].get('file_modified_time','') if backups else '',
        'latest_backup_filename_time':backups[0].get('backup_filename_time','') if backups else '',
        'latest_action_created':backups[0].get('action_created','') if backups else '',
        'latest_modified':backups[0].get('file_modified_time','') if backups else '',
        'timestamp_note':'File modified time may reflect original file metadata preserved during backup; action-created time or filename timestamp is the better backup creation clue.'
    }

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Backup Vault Inventory',
        'read_only':True,
        'report_only':True,
        'filter':q,
        'folder':str(vault),
        'summary':summary,
        'by_type':list(by_type.values()),
        'by_action':list(by_action.values()),
        'backups':backups,
        'errors':{'scan':scan_errors,'logs':log_errors}
    }

    if export:
        out=ROOT/'Reports'/'Backups'
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=out/f'Backup_Vault_Inventory_{stamp}.json'
        md_path=out/f'Backup_Vault_Inventory_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Backup Vault Inventory','',
            f"Created: {report['created']}",
            f"Folder: {report['folder']}",
            f"Filter: {q or 'none'}",
            '',
            '## Summary','',
            f"- Backups: {summary['backups']}",
            f"- Total bytes: {summary['bytes']}",
            f"- Associated with repair action: {summary['associated']}",
            f"- Unassociated/older backups: {summary['unassociated']}",
            f"- Verified action backups: {summary['verified']}",
            f"- Backup types: {summary['types']}",
            f"- Repair action types: {summary['actions']}",
            f"- Scan errors: {summary['scan_errors']}",
            f"- Log parse errors: {summary['log_errors']}",
            f"- Latest backup: {summary['latest_backup']}",
            f"- Latest file modified time: {summary.get('latest_file_modified_time','')}",
            f"- Latest backup filename time: {summary.get('latest_backup_filename_time','')}",
            f"- Latest action-created time: {summary.get('latest_action_created','')}",
            f"- Timestamp note: {summary.get('timestamp_note','')}",
            '',
            '## By Type',''
        ]
        for t in report['by_type']:
            lines.append(f"- `{t.get('type')}` — count: {t.get('count')}, bytes: {t.get('bytes')}")
        lines += ['','## By Repair Action','']
        for a in report['by_action']:
            lines.append(f"- `{a.get('action_id')}` — count: {a.get('count')}, bytes: {a.get('bytes')}, verified: {a.get('verified')}, unverified/older: {a.get('unverified')}")
        lines += ['','## Backups','']
        for b in backups:
            lines += [
                f"### {b.get('name')}",
                '',
                f"- Type: `{b.get('type')}`",
                f"- Size: {b.get('size')} bytes",
                f"- File modified time: {b.get('file_modified_time') or b.get('modified')}",
                f"- Backup filename time: {b.get('backup_filename_time') or ''}",
                f"- Action-created time: {b.get('action_created') or ''}",
                f"- Timestamp note: {b.get('timestamp_note') or ''}",
                f"- Original target: `{b.get('original_target') or ''}`",
                f"- Created by action: `{b.get('action_id') or 'unknown/older backup'}`",
                f"- Action created: {b.get('action_created') or ''}",
                f"- Verified state: {b.get('verified_state')}",
                f"- Backup path: `{b.get('path')}`",
                f"- Repair log JSON: `{b.get('log_json') or ''}`",
                f"- Repair log Markdown: `{b.get('log_markdown') or ''}`",
                ''
            ]
        if scan_errors or log_errors:
            lines += ['## Errors','']
            for e in scan_errors:
                lines.append(f"- Scan error `{e.get('path')}`: {e.get('error')}")
            for e in log_errors:
                lines.append(f"- Log parse error `{e.get('path')}`: {e.get('error')}")
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def _sha256_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def _looks_text_file(path):
    ext=path.suffix.lower()
    if ext in {'.txt','.md','.json','.py','.js','.html','.css','.bat','.cmd','.ps1','.yml','.yaml','.toml','.ini','.cfg','.csv','.xml'}:
        return True
    try:
        sample=path.read_bytes()[:4096]
        if b'\x00' in sample:
            return False
        sample.decode('utf-8')
        return True
    except Exception:
        return False

def _safe_text_read(path, limit=200000):
    raw=path.read_bytes()
    truncated=False
    if len(raw)>limit:
        raw=raw[:limit]
        truncated=True
    try:
        txt=raw.decode('utf-8',errors='replace')
    except Exception:
        txt=''
    return txt,truncated

def _diff_preview(old_text,new_text,old_label='backup',new_label='current',max_lines=160):
    import difflib
    old_lines=old_text.splitlines()
    new_lines=new_text.splitlines()
    diff=list(difflib.unified_diff(old_lines,new_lines,fromfile=old_label,tofile=new_label,lineterm=''))
    truncated=False
    if len(diff)>max_lines:
        diff=diff[:max_lines]
        truncated=True
        diff.append(f'... diff truncated after {max_lines} lines ...')
    return '\n'.join(diff),truncated,len(old_lines),len(new_lines)

def _backup_metadata_for_path(path_text):
    vault=FOLDERS.get('file_backups',ROOT/'Backups'/'GeneratedFiles')
    p=Path(path_text)
    if not p.is_absolute():
        p=vault/p
    p=p.resolve()
    vr=vault.resolve()
    if not (p==vr or vr in p.parents):
        return None,{'ok':False,'message':'Backup path is outside Backup Vault.'}
    if not p.exists() or not p.is_file():
        return None,{'ok':False,'message':'Backup file does not exist.'}
    # Reuse backup vault inventory to infer target/action association.
    inv=backup_vault_report({'limit':2000})
    for b in inv.get('backups',[]):
        if str(Path(b.get('path','')).resolve()).lower()==str(p).lower():
            return b,{'ok':True,'message':'Backup metadata found in vault inventory.'}
    st=p.stat()
    item={
        'path':str(p),
        'name':p.name,
        'type':_backup_type_from_name(p.name),
        'size':st.st_size,
        'file_modified_time':datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds'),
        'backup_filename_time':'',
        'original_target':_infer_target_from_backup_name(p.name),
        'action_id':'',
        'action_created':'',
        'associated':False,
        'verified_state':'unassociated'
    }
    return item,{'ok':True,'message':'Backup metadata inferred from filename.'}

def restore_preview_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    backup_path=(d.get('backup_path') or d.get('path') or '').strip()
    if not backup_path:
        return {'ok':False,'message':'No backup_path provided. Select a backup first.','read_only':True,'report_only':True}

    backup,meta_status=_backup_metadata_for_path(backup_path)
    if not meta_status.get('ok'):
        return {'ok':False,'message':meta_status.get('message','Could not inspect backup.'),'read_only':True,'report_only':True}

    bp=Path(backup['path']).resolve()
    target_text=backup.get('original_target') or ''
    target_path=Path(target_text).resolve() if target_text else None
    target_inside=False
    target_exists=False
    target_size=0
    target_hash=''
    target_file_modified_time=''
    problems=[]
    warnings=[]

    if not target_text:
        problems.append('No original target could be inferred for this backup.')
    else:
        try:
            rr=ROOT.resolve()
            target_inside=bool(target_path==rr or rr in target_path.parents)
            if not target_inside:
                problems.append('Original target is outside FOXAI root.')
            target_exists=target_path.exists() and target_path.is_file()
            if target_exists:
                st=target_path.stat()
                target_size=st.st_size
                target_hash=_sha256_file(target_path)
                target_file_modified_time=datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds')
            else:
                warnings.append('Current target file does not exist. A future restore would create it if allowed.')
        except Exception as e:
            problems.append(f'Could not inspect target: {e}')

    backup_hash=_sha256_file(bp)
    backup_size=bp.stat().st_size
    backup_file_modified_time=datetime.fromtimestamp(bp.stat().st_mtime).isoformat(timespec='seconds')
    same_hash=bool(target_exists and target_hash==backup_hash)

    text_preview_available=False
    diff_text=''
    diff_truncated=False
    backup_text_truncated=False
    target_text_truncated=False
    backup_line_count=0
    target_line_count=0
    readable_reason=''
    if target_exists and _looks_text_file(bp) and _looks_text_file(target_path):
        try:
            backup_text,backup_text_truncated=_safe_text_read(bp)
            target_text_content,target_text_truncated=_safe_text_read(target_path)
            diff_text,diff_truncated,backup_line_count,target_line_count=_diff_preview(backup_text,target_text_content,'backup_would_restore_from','current_target')
            text_preview_available=True
            if not diff_text.strip():
                diff_text='No text differences detected.'
        except Exception as e:
            readable_reason=f'Could not generate text diff: {e}'
    elif not target_exists:
        if _looks_text_file(bp):
            try:
                backup_text,backup_text_truncated=_safe_text_read(bp)
                lines=backup_text.splitlines()
                preview='\n'.join(lines[:160])
                if len(lines)>160:
                    preview += '\n... preview truncated after 160 lines ...'
                    diff_truncated=True
                diff_text=preview or 'Backup text file is empty.'
                backup_line_count=len(lines)
                target_line_count=0
                text_preview_available=True
                readable_reason='Target missing; showing backup content preview instead of diff.'
            except Exception as e:
                readable_reason=f'Could not read backup preview: {e}'
        else:
            readable_reason='Target missing and backup is not a recognized text file.'
    else:
        readable_reason='Backup/current target are not both recognized text files.'

    risk='low'
    if problems:
        risk='blocked'
    elif not target_exists:
        risk='medium'
    elif not same_hash:
        risk='medium'
    else:
        risk='low'

    would_overwrite=bool(target_exists)
    would_create=bool(not target_exists and target_inside and target_text)
    required_future_confirmation='RESTORE PREVIEW ONLY - NO RESTORE AVAILABLE'
    restore_allowed_now=False

    summary={
        'backup':str(bp),
        'target':str(target_path) if target_path else '',
        'backup_exists':True,
        'target_exists':target_exists,
        'target_inside_root':target_inside,
        'backup_size':backup_size,
        'target_size':target_size,
        'same_hash':same_hash,
        'would_overwrite':would_overwrite,
        'would_create':would_create,
        'risk':risk,
        'text_preview_available':text_preview_available,
        'problems':len(problems),
        'warnings':len(warnings)
    }

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Restore Preview Plan',
        'read_only':True,
        'report_only':True,
        'restore_allowed_now':restore_allowed_now,
        'required_future_confirmation':required_future_confirmation,
        'summary':summary,
        'backup':{
            'path':str(bp),
            'name':backup.get('name') or bp.name,
            'type':backup.get('type') or _backup_type_from_name(bp.name),
            'size':backup_size,
            'sha256':backup_hash,
            'file_modified_time':backup_file_modified_time,
            'filename_timestamp':backup.get('backup_filename_time',''),
            'created_by_action':backup.get('action_id',''),
            'action_created':backup.get('action_created',''),
            'verified_state':backup.get('verified_state',''),
            'repair_log':backup.get('log_markdown') or backup.get('log_json') or ''
        },
        'target':{
            'path':str(target_path) if target_path else '',
            'exists':target_exists,
            'inside_root':target_inside,
            'size':target_size,
            'sha256':target_hash,
            'file_modified_time':target_file_modified_time
        },
        'comparison':{
            'same_hash':same_hash,
            'backup_size':backup_size,
            'target_size':target_size,
            'size_delta_if_restored':backup_size-target_size if target_exists else backup_size,
            'text_preview_available':text_preview_available,
            'diff_truncated':diff_truncated,
            'backup_text_truncated':backup_text_truncated,
            'target_text_truncated':target_text_truncated,
            'backup_line_count':backup_line_count,
            'target_line_count':target_line_count,
            'readable_reason':readable_reason,
            'diff_preview':diff_text
        },
        'safety':{
            'no_restore_button':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'preview_only':True
        },
        'warnings':warnings,
        'problems':problems
    }

    if export:
        out=ROOT/'Reports'/'Backups'/'RestorePreviews'
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name=slug(bp.stem)[:80]
        json_path=out/f'Restore_Preview_{safe_name}_{stamp}.json'
        md_path=out/f'Restore_Preview_{safe_name}_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Restore Preview Plan','',
            f"Created: {report['created']}",
            '',
            '## Safety',
            '',
            '- Preview only.',
            '- No restore button exists in this build.',
            '- No overwrite was performed.',
            '- No copy-back was performed.',
            '- No delete was performed.',
            '- No install was performed.',
            '- No model cleanup was performed.',
            '',
            '## Summary','',
            f"- Risk: `{risk}`",
            f"- Backup: `{summary['backup']}`",
            f"- Target: `{summary['target']}`",
            f"- Target exists: {target_exists}",
            f"- Target inside FOXAI root: {target_inside}",
            f"- Would overwrite: {would_overwrite}",
            f"- Would create: {would_create}",
            f"- Same hash: {same_hash}",
            f"- Backup size: {backup_size} bytes",
            f"- Target size: {target_size} bytes",
            f"- Size delta if restored: {report['comparison']['size_delta_if_restored']} bytes",
            '',
            '## Backup Metadata','',
            f"- Name: `{report['backup']['name']}`",
            f"- Type: `{report['backup']['type']}`",
            f"- SHA256: `{backup_hash}`",
            f"- File-modified time: {backup_file_modified_time}",
            f"- Filename timestamp: {report['backup']['filename_timestamp']}",
            f"- Created by action: `{report['backup']['created_by_action']}`",
            f"- Action-created time: {report['backup']['action_created']}",
            f"- Verified state: {report['backup']['verified_state']}",
            f"- Repair log: `{report['backup']['repair_log']}`",
            '',
            '## Target Metadata','',
            f"- Path: `{report['target']['path']}`",
            f"- Exists: {target_exists}",
            f"- SHA256: `{target_hash}`",
            f"- File-modified time: {target_file_modified_time}",
            '',
            '## Problems',''
        ]
        lines += [f"- {p}" for p in problems] if problems else ['- none']
        lines += ['','## Warnings','']
        lines += [f"- {w}" for w in warnings] if warnings else ['- none']
        lines += ['','## Diff / Preview','']
        lines += [
            f"- Text preview available: {text_preview_available}",
            f"- Diff truncated: {diff_truncated}",
            f"- Backup text truncated: {backup_text_truncated}",
            f"- Target text truncated: {target_text_truncated}",
            f"- Readable reason: {readable_reason}",
            '',
            '```diff',
            diff_text or 'No diff preview available.',
            '```'
        ]
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def restore_readiness_gate(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    backup_path=(d.get('backup_path') or d.get('path') or '').strip()
    if not backup_path:
        return {'ok':False,'message':'No backup_path provided. Select a backup first.','read_only':True,'report_only':True,'restore_allowed_now':False}

    preview=restore_preview_report({'backup_path':backup_path,'export':False})
    if not preview.get('ok'):
        return {
            'ok':False,
            'message':preview.get('message','Could not create restore preview.'),
            'read_only':True,
            'report_only':True,
            'restore_allowed_now':False,
            'preview':preview
        }

    backup=preview.get('backup') or {}
    target=preview.get('target') or {}
    comparison=preview.get('comparison') or {}
    summary=preview.get('summary') or {}
    problems=list(preview.get('problems') or [])
    warnings=list(preview.get('warnings') or [])
    gates=[]

    def add_gate(gid, status, message, detail=''):
        # status: pass, warn, block, info
        gates.append({'id':gid,'status':status,'message':message,'detail':detail})

    def exists_file(path_text):
        try:
            return bool(path_text and Path(path_text).exists() and Path(path_text).is_file())
        except Exception:
            return False

    backup_path_resolved=backup.get('path') or summary.get('backup') or backup_path
    target_path=target.get('path') or summary.get('target') or ''
    backup_exists=exists_file(backup_path_resolved)
    target_exists=bool(target.get('exists'))
    backup_hash=backup.get('sha256') or ''
    target_hash=target.get('sha256') or ''
    target_inside=bool(target.get('inside_root'))
    repair_log=backup.get('repair_log') or ''
    verified_state=backup.get('verified_state') or ''
    linked_action=backup.get('created_by_action') or ''

    add_gate('backup_exists','pass' if backup_exists else 'block','Backup file exists.' if backup_exists else 'Backup file is missing.',backup_path_resolved)
    add_gate('backup_hash_readable','pass' if backup_hash else 'block','Backup SHA256 was calculated.' if backup_hash else 'Backup hash could not be calculated.',backup_hash)
    add_gate('target_inferred','pass' if target_path else 'block','Original target path was inferred.' if target_path else 'Original target path could not be inferred.',target_path)
    add_gate('target_inside_root','pass' if target_inside else 'block','Target is inside FOXAI root.' if target_inside else 'Target is outside FOXAI root or unknown.',target_path)

    if target_path:
        if target_exists:
            add_gate('target_exists_now','pass','Current target exists now.',target_path)
            add_gate('target_hash_readable','pass' if target_hash else 'block','Current target SHA256 was calculated.' if target_hash else 'Current target hash could not be calculated.',target_hash)
        else:
            add_gate('target_exists_now','warn','Current target does not exist. A future restore would create it, not overwrite it.',target_path)
            add_gate('target_hash_readable','warn','No current target hash because target is missing.','')

    if linked_action:
        add_gate('linked_to_repair_action','pass','Backup is linked to a Repair Bay action.',linked_action)
    else:
        add_gate('linked_to_repair_action','warn','Backup is not linked to a Repair Bay action. It may be older/pre-verification.',backup_path_resolved)

    if repair_log and exists_file(repair_log):
        add_gate('repair_log_exists','pass','Associated repair log exists.',repair_log)
    elif repair_log:
        add_gate('repair_log_exists','warn','Repair log path was recorded but file was not found.',repair_log)
    else:
        add_gate('repair_log_exists','warn','No associated repair log path is recorded.','')

    if verified_state=='passed':
        add_gate('backup_action_verified','pass','The action that created this backup was verified.',verified_state)
    elif verified_state in {'not_recorded','unassociated',''}:
        add_gate('backup_action_verified','warn','Backup is older/unverified or verification was not recorded. Preview may still be useful.',verified_state or 'not recorded')
    else:
        add_gate('backup_action_verified','block','The backup/action verification state is not acceptable.',verified_state)

    if comparison.get('text_preview_available'):
        add_gate('readable_diff_available','pass','Text diff/preview is available.',comparison.get('readable_reason',''))
    else:
        add_gate('readable_diff_available','warn','Text diff/preview is not available. Hash and size checks still apply.',comparison.get('readable_reason',''))

    risk=summary.get('risk') or 'unknown'
    if risk=='blocked':
        add_gate('preview_risk','block','Restore preview risk is blocked.',risk)
    elif risk=='medium':
        add_gate('preview_risk','warn','Restore preview risk is medium. Future restore would require explicit confirmation.',risk)
    else:
        add_gate('preview_risk','pass','Restore preview risk is low.',risk)

    if comparison.get('same_hash'):
        add_gate('hash_difference','warn','Backup and current target are identical. Restore may be unnecessary.',backup_hash)
    else:
        add_gate('hash_difference','pass','Backup and current target differ, or current target is missing. Restore preview has meaningful value.','')

    confirmation_phrase=''
    if target_path and backup_path_resolved:
        confirmation_phrase=f"RESTORE {Path(backup_path_resolved).name} TO {Path(target_path).name}"
    else:
        confirmation_phrase='RESTORE SELECTED BACKUP'

    add_gate('future_confirmation_phrase','info','Future restore confirmation phrase generated.',confirmation_phrase)
    add_gate('restore_currently_blocked','block','Actual restore is intentionally unavailable in this build. Preview only.','No restore endpoint/button exists.')

    block_count=sum(1 for g in gates if g.get('status')=='block')
    warn_count=sum(1 for g in gates if g.get('status')=='warn')
    pass_count=sum(1 for g in gates if g.get('status')=='pass')
    info_count=sum(1 for g in gates if g.get('status')=='info')
    hard_block_ids=[g['id'] for g in gates if g.get('status')=='block' and g.get('id')!='restore_currently_blocked']
    candidate_status='blocked'
    if not hard_block_ids:
        candidate_status='eligible_preview_only_with_warnings' if warn_count else 'eligible_preview_only'

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Restore Readiness Gate',
        'read_only':True,
        'report_only':True,
        'restore_allowed_now':False,
        'candidate_status':candidate_status,
        'future_confirmation_phrase':confirmation_phrase,
        'summary':{
            'gates':len(gates),
            'pass':pass_count,
            'warn':warn_count,
            'block':block_count,
            'info':info_count,
            'hard_blocks':len(hard_block_ids),
            'hard_block_ids':hard_block_ids,
            'candidate_status':candidate_status,
            'restore_allowed_now':False,
            'backup':backup_path_resolved,
            'target':target_path,
            'preview_risk':risk,
            'same_hash':bool(comparison.get('same_hash')),
            'target_exists':target_exists,
            'target_inside_root':target_inside
        },
        'gates':gates,
        'preview':preview,
        'problems':problems,
        'warnings':warnings,
        'safety':{
            'no_restore_button':True,
            'no_restore_endpoint':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'preview_only':True
        }
    }

    if export:
        out=ROOT/'Reports'/'Backups'/'RestoreReadiness'
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name=slug(Path(backup_path_resolved).stem)[:80]
        json_path=out/f'Restore_Readiness_{safe_name}_{stamp}.json'
        md_path=out/f'Restore_Readiness_{safe_name}_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Restore Readiness Gate','',
            f"Created: {report['created']}",
            '',
            '## Safety Lock','',
            '- Actual restore is intentionally unavailable in this build.',
            '- No restore button.',
            '- No restore endpoint.',
            '- No overwrite.',
            '- No copy-back.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '',
            '## Summary','',
            f"- Candidate status: `{candidate_status}`",
            f"- Restore allowed now: {False}",
            f"- Gates: {len(gates)}",
            f"- Passed: {pass_count}",
            f"- Warnings: {warn_count}",
            f"- Blocks: {block_count}",
            f"- Hard blocks excluding intentional restore lock: {len(hard_block_ids)}",
            f"- Preview risk: `{risk}`",
            f"- Same hash: {bool(comparison.get('same_hash'))}",
            f"- Target exists: {target_exists}",
            f"- Target inside FOXAI root: {target_inside}",
            f"- Backup: `{backup_path_resolved}`",
            f"- Target: `{target_path}`",
            f"- Future confirmation phrase: `{confirmation_phrase}`",
            '',
            '## Gates',''
        ]
        for g in gates:
            lines.append(f"- **{g.get('status','').upper()}** `{g.get('id')}` — {g.get('message')} {(' — '+g.get('detail')) if g.get('detail') else ''}")
        lines += ['','## Problems From Preview','']
        lines += [f"- {p}" for p in problems] if problems else ['- none']
        lines += ['','## Warnings From Preview','']
        lines += [f"- {w}" for w in warnings] if warnings else ['- none']
        lines += ['','## Preview Reference','']
        lines += [
            f"- Backup SHA256: `{backup.get('sha256','')}`",
            f"- Target SHA256: `{target.get('sha256','')}`",
            f"- Backup size: {backup.get('size','')} bytes",
            f"- Target size: {target.get('size','')} bytes",
            f"- Text preview available: {comparison.get('text_preview_available')}",
            f"- Readable reason: {comparison.get('readable_reason','')}"
        ]
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def restore_staging_copy(d=None):
    d=d or {}
    backup_path=(d.get('backup_path') or d.get('path') or '').strip()
    confirm=(d.get('confirm') or '').strip().upper()
    if not backup_path:
        return {'ok':False,'message':'No backup_path provided. Select a backup first.','read_only':False,'restore_allowed_now':False}
    if confirm not in {'STAGE','STAGE COPY','STAGE RESTORE','CONFIRM','YES'}:
        return {
            'ok':False,
            'message':'Staging copy blocked. Type STAGE to confirm this preview-only staging action.',
            'requires_confirmation':True,
            'expected_confirmation':'STAGE',
            'read_only':False,
            'restore_allowed_now':False,
            'safety':{
                'no_restore_to_original_location':True,
                'no_overwrite_live_target':True,
                'no_copy_back':True,
                'no_delete':True,
                'no_install':True,
                'no_model_cleanup':True
            }
        }

    readiness=restore_readiness_gate({'backup_path':backup_path,'export':False})
    if not readiness.get('ok'):
        return {'ok':False,'message':'Could not build readiness gate before staging copy. '+readiness.get('message',''),'read_only':False,'restore_allowed_now':False,'readiness':readiness}

    summary=readiness.get('summary') or {}
    hard_blocks=summary.get('hard_block_ids') or []
    if hard_blocks:
        return {'ok':False,'message':'Staging copy blocked by hard readiness gate issue(s): '+', '.join(hard_blocks),'read_only':False,'restore_allowed_now':False,'readiness':readiness}

    preview=readiness.get('preview') or {}
    backup=preview.get('backup') or {}
    target=preview.get('target') or {}
    bp=Path(backup.get('path') or backup_path).resolve()
    if not bp.exists() or not bp.is_file():
        return {'ok':False,'message':'Backup file is missing.','read_only':False,'restore_allowed_now':False,'backup_path':str(bp)}

    # Confirm backup remains inside Backup Vault.
    vault=FOLDERS.get('file_backups',ROOT/'Backups'/'GeneratedFiles').resolve()
    try:
        if not (bp==vault or vault in bp.parents):
            return {'ok':False,'message':'Backup path is outside Backup Vault.','read_only':False,'restore_allowed_now':False,'backup_path':str(bp)}
    except Exception:
        return {'ok':False,'message':'Backup path could not be validated.','read_only':False,'restore_allowed_now':False,'backup_path':str(bp)}

    target_path=target.get('path') or ''
    target_hash_before=target.get('sha256') or ''
    target_exists_before=bool(target.get('exists'))
    target_mtime_before=target.get('file_modified_time') or ''
    backup_hash_before=backup.get('sha256') or _sha256_file(bp)

    staging_root=ROOT/'Reports'/'Backups'/'RestoreStaging'
    staging_root.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    stage_dir=staging_root/f"Stage_{slug(bp.stem)[:70]}_{stamp}"
    stage_dir.mkdir(parents=True,exist_ok=False)

    copy_path=stage_dir/f"STAGED_COPY_{bp.name}"
    metadata_path=stage_dir/'staging_metadata.json'
    markdown_path=stage_dir/'staging_report.md'
    readiness_path=stage_dir/'readiness_gate.json'
    preview_path=stage_dir/'restore_preview.json'

    # The only file copy: backup -> staging folder. No target writes.
    shutil.copy2(bp,copy_path)

    staged_hash=_sha256_file(copy_path)
    staged_size=copy_path.stat().st_size
    target_hash_after=''
    target_exists_after=False
    target_mtime_after=''
    target_unchanged=True
    if target_path:
        tp=Path(target_path)
        target_exists_after=tp.exists() and tp.is_file()
        if target_exists_after:
            target_hash_after=_sha256_file(tp)
            target_mtime_after=datetime.fromtimestamp(tp.stat().st_mtime).isoformat(timespec='seconds')
        target_unchanged=(target_exists_before==target_exists_after and target_hash_before==target_hash_after and target_mtime_before==target_mtime_after)

    verification_checks=[
        {'id':'backup_exists','ok':bp.exists() and bp.is_file(),'message':'Backup source exists.','path':str(bp)},
        {'id':'staging_folder_created','ok':stage_dir.exists() and stage_dir.is_dir(),'message':'Staging folder was created.','path':str(stage_dir)},
        {'id':'staged_copy_exists','ok':copy_path.exists() and copy_path.is_file(),'message':'Staged backup copy exists.','path':str(copy_path)},
        {'id':'hash_matches_backup','ok':staged_hash==backup_hash_before,'message':'Staged copy hash matches source backup.','path':str(copy_path)},
        {'id':'size_matches_backup','ok':staged_size==bp.stat().st_size,'message':'Staged copy size matches source backup.','path':str(copy_path)},
        {'id':'live_target_untouched','ok':target_unchanged,'message':'Live target was not changed by staging.','path':target_path},
        {'id':'restore_still_blocked','ok':True,'message':'No restore-to-target operation exists in this staging action.','path':''}
    ]
    verification_ok=all(c.get('ok') for c in verification_checks)

    metadata={
        'ok':verification_ok,
        'created':now(),
        'title':'Kayock Restore Staging Copy',
        'action_id':'restore_staging_copy',
        'read_only':False,
        'user_approved_action':True,
        'restore_allowed_now':False,
        'stage_dir':str(stage_dir),
        'staged_copy':str(copy_path),
        'backup':{
            'path':str(bp),
            'name':bp.name,
            'sha256':backup_hash_before,
            'size':bp.stat().st_size,
            'created_by_action':backup.get('created_by_action',''),
            'verified_state':backup.get('verified_state',''),
            'repair_log':backup.get('repair_log','')
        },
        'target':{
            'path':target_path,
            'exists_before':target_exists_before,
            'exists_after':target_exists_after,
            'sha256_before':target_hash_before,
            'sha256_after':target_hash_after,
            'file_modified_time_before':target_mtime_before,
            'file_modified_time_after':target_mtime_after,
            'unchanged':target_unchanged
        },
        'readiness_summary':summary,
        'future_confirmation_phrase':readiness.get('future_confirmation_phrase',''),
        'verification':{
            'ok':verification_ok,
            'checked':len(verification_checks),
            'passed':sum(1 for c in verification_checks if c.get('ok')),
            'failed':sum(1 for c in verification_checks if not c.get('ok')),
            'message':f"Restore staging verification {'passed' if verification_ok else 'failed'}: {sum(1 for c in verification_checks if c.get('ok'))}/{len(verification_checks)} check(s) passed.",
            'checks':verification_checks
        },
        'safety':{
            'no_restore_to_original_location':True,
            'no_overwrite_live_target':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'staging_only':True
        }
    }
    jwrite(readiness_path,readiness)
    jwrite(preview_path,preview)
    jwrite(metadata_path,metadata)

    lines=[
        '# Kayock Restore Staging Copy','',
        f"Created: {metadata['created']}",
        '',
        '## Safety',
        '',
        '- Staging copy only.',
        '- No restore to original location.',
        '- No live target overwrite.',
        '- No copy-back.',
        '- No delete.',
        '- No install.',
        '- No model cleanup.',
        '',
        '## Summary','',
        f"- OK: {metadata['ok']}",
        f"- Stage folder: `{stage_dir}`",
        f"- Staged copy: `{copy_path}`",
        f"- Source backup: `{bp}`",
        f"- Future target: `{target_path}`",
        f"- Future confirmation phrase: `{metadata['future_confirmation_phrase']}`",
        '',
        '## Verification','',
        f"- Verification OK: {verification_ok}",
        f"- Message: {metadata['verification']['message']}",
        ''
    ]
    for c in verification_checks:
        status='PASS' if c.get('ok') else 'FAIL'
        lines.append(f"- **{status}** `{c.get('id')}` — {c.get('message')} {('`'+c.get('path','')+'`') if c.get('path') else ''}")
    lines += [
        '',
        '## Backup',
        '',
        f"- Path: `{bp}`",
        f"- SHA256: `{backup_hash_before}`",
        f"- Size: {bp.stat().st_size} bytes",
        f"- Created by action: `{backup.get('created_by_action','')}`",
        f"- Verified state: {backup.get('verified_state','')}",
        f"- Repair log: `{backup.get('repair_log','')}`",
        '',
        '## Target Untouched Check',
        '',
        f"- Target path: `{target_path}`",
        f"- Exists before: {target_exists_before}",
        f"- Exists after: {target_exists_after}",
        f"- SHA256 before: `{target_hash_before}`",
        f"- SHA256 after: `{target_hash_after}`",
        f"- File-modified time before: {target_mtime_before}",
        f"- File-modified time after: {target_mtime_after}",
        f"- Unchanged: {target_unchanged}",
        '',
        '## Included Files',
        '',
        f"- `STAGED_COPY_{bp.name}`",
        '- `staging_metadata.json`',
        '- `staging_report.md`',
        '- `readiness_gate.json`',
        '- `restore_preview.json`'
    ]
    markdown_path.write_text('\n'.join(lines),encoding='utf-8')

    # Create a RepairActions audit log too, so Repair History sees it.
    repair_log_payload={
        'ok':verification_ok,
        'message':'Restore staging copy prepared safely.' if verification_ok else 'Restore staging copy completed but verification failed.',
        'target':str(copy_path),
        'backup':str(bp),
        'action_id':'restore_staging_copy',
        'stage_dir':str(stage_dir),
        'verification':metadata['verification'],
        'restore_allowed_now':False
    }
    try:
        action_log=repair_action_log('restore_staging_copy',repair_log_payload,dry_run=False)
        metadata['repair_action_log']=action_log.get('exported',{})
        jwrite(metadata_path,metadata)
    except Exception as e:
        metadata['repair_action_log_error']=str(e)

    result={
        'ok':verification_ok,
        'message':metadata['verification']['message'],
        'title':'Kayock Restore Staging Copy',
        'stage_dir':str(stage_dir),
        'staged_copy':str(copy_path),
        'metadata':str(metadata_path),
        'markdown':str(markdown_path),
        'readiness':str(readiness_path),
        'preview':str(preview_path),
        'verification':metadata['verification'],
        'restore_allowed_now':False,
        'safety':metadata['safety'],
        'repair_action_log':metadata.get('repair_action_log',{})
    }
    return result



def staging_package_inventory(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    q=(d.get('query') or d.get('filter') or '').strip().lower()
    limit=int(d.get('limit') or 500)
    root=ROOT/'Reports'/'Backups'/'RestoreStaging'
    root.mkdir(parents=True,exist_ok=True)

    packages=[]
    scan_errors=[]
    for stage_dir in sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p:p.stat().st_mtime if p.exists() else 0, reverse=True):
        try:
            meta_path=stage_dir/'staging_metadata.json'
            report_path=stage_dir/'staging_report.md'
            readiness_path=stage_dir/'readiness_gate.json'
            preview_path=stage_dir/'restore_preview.json'
            meta={}
            readiness={}
            preview={}
            if meta_path.exists():
                try: meta=json.loads(meta_path.read_text(encoding='utf-8',errors='replace'))
                except Exception as e: scan_errors.append({'path':str(meta_path),'error':str(e)})
            if readiness_path.exists():
                try: readiness=json.loads(readiness_path.read_text(encoding='utf-8',errors='replace'))
                except Exception as e: scan_errors.append({'path':str(readiness_path),'error':str(e)})
            if preview_path.exists():
                try: preview=json.loads(preview_path.read_text(encoding='utf-8',errors='replace'))
                except Exception as e: scan_errors.append({'path':str(preview_path),'error':str(e)})

            files=[]
            total_size=0
            for f in sorted([x for x in stage_dir.iterdir() if x.is_file()], key=lambda x:x.name.lower()):
                try:
                    st=f.stat()
                    total_size+=st.st_size
                    files.append({
                        'name':f.name,
                        'path':str(f),
                        'size':st.st_size,
                        'modified':datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds')
                    })
                except Exception as e:
                    scan_errors.append({'path':str(f),'error':str(e)})

            staged_copy=meta.get('staged_copy') or ''
            if not staged_copy:
                staged_candidates=[f for f in stage_dir.glob('STAGED_COPY_*') if f.is_file()]
                staged_copy=str(staged_candidates[0]) if staged_candidates else ''
            staged_copy_exists=bool(staged_copy and Path(staged_copy).exists() and Path(staged_copy).is_file())

            verification=meta.get('verification') or {}
            target=meta.get('target') or {}
            backup=meta.get('backup') or {}
            readiness_summary=meta.get('readiness_summary') or readiness.get('summary') or {}
            repair_action_log=meta.get('repair_action_log') or {}
            safety=meta.get('safety') or {}

            live_untouched=bool(target.get('unchanged'))
            if not live_untouched and verification:
                for c in verification.get('checks',[]):
                    if c.get('id')=='live_target_untouched':
                        live_untouched=bool(c.get('ok'))

            required_files={
                'staging_metadata.json':meta_path.exists(),
                'staging_report.md':report_path.exists(),
                'readiness_gate.json':readiness_path.exists(),
                'restore_preview.json':preview_path.exists(),
                'staged_copy':staged_copy_exists
            }
            missing_required=[k for k,v in required_files.items() if not v]
            ok=bool(meta.get('ok')) and staged_copy_exists and not missing_required and bool(verification.get('ok')) and live_untouched

            item={
                'stage_dir':str(stage_dir),
                'name':stage_dir.name,
                'created':meta.get('created') or datetime.fromtimestamp(stage_dir.stat().st_mtime).isoformat(timespec='seconds'),
                'ok':ok,
                'meta_ok':bool(meta.get('ok')),
                'verification_ok':bool(verification.get('ok')),
                'verification_checked':verification.get('checked',0),
                'verification_passed':verification.get('passed',0),
                'verification_failed':verification.get('failed',0),
                'verification_message':verification.get('message',''),
                'staged_copy':staged_copy,
                'staged_copy_exists':staged_copy_exists,
                'source_backup':backup.get('path') or preview.get('backup',{}).get('path',''),
                'future_target':target.get('path') or preview.get('target',{}).get('path','') or readiness_summary.get('target',''),
                'target_exists_before':target.get('exists_before'),
                'target_exists_after':target.get('exists_after'),
                'target_hash_before':target.get('sha256_before',''),
                'target_hash_after':target.get('sha256_after',''),
                'live_target_untouched':live_untouched,
                'future_confirmation_phrase':meta.get('future_confirmation_phrase') or readiness.get('future_confirmation_phrase',''),
                'candidate_status':readiness_summary.get('candidate_status',''),
                'preview_risk':readiness_summary.get('preview_risk',''),
                'same_hash':readiness_summary.get('same_hash'),
                'restore_allowed_now':bool(meta.get('restore_allowed_now')),
                'metadata':str(meta_path) if meta_path.exists() else '',
                'markdown':str(report_path) if report_path.exists() else '',
                'readiness':str(readiness_path) if readiness_path.exists() else '',
                'preview':str(preview_path) if preview_path.exists() else '',
                'repair_action_log_json':repair_action_log.get('json','') if isinstance(repair_action_log,dict) else '',
                'repair_action_log_markdown':repair_action_log.get('markdown','') if isinstance(repair_action_log,dict) else '',
                'files':files,
                'file_count':len(files),
                'total_size':total_size,
                'required_files':required_files,
                'missing_required':missing_required,
                'safety':safety
            }

            blob=' '.join(str(item.get(k,'')) for k in ['name','stage_dir','staged_copy','source_backup','future_target','future_confirmation_phrase','candidate_status','preview_risk']).lower()
            if q and q not in blob:
                continue
            packages.append(item)
            if len(packages)>=limit:
                break
        except Exception as e:
            scan_errors.append({'path':str(stage_dir),'error':str(e)})

    by_status={}
    by_risk={}
    for p in packages:
        status='ok' if p.get('ok') else 'problem'
        by_status.setdefault(status,{'status':status,'count':0,'bytes':0})
        by_status[status]['count']+=1
        by_status[status]['bytes']+=p.get('total_size',0)
        risk=p.get('preview_risk') or 'unknown'
        by_risk.setdefault(risk,{'risk':risk,'count':0,'bytes':0})
        by_risk[risk]['count']+=1
        by_risk[risk]['bytes']+=p.get('total_size',0)

    summary={
        'packages':len(packages),
        'ok':sum(1 for p in packages if p.get('ok')),
        'problems':sum(1 for p in packages if not p.get('ok')),
        'verified':sum(1 for p in packages if p.get('verification_ok')),
        'live_target_untouched':sum(1 for p in packages if p.get('live_target_untouched')),
        'restore_allowed_now':sum(1 for p in packages if p.get('restore_allowed_now')),
        'files':sum(p.get('file_count',0) for p in packages),
        'bytes':sum(p.get('total_size',0) for p in packages),
        'scan_errors':len(scan_errors),
        'latest_package':packages[0].get('name','') if packages else '',
        'latest_created':packages[0].get('created','') if packages else ''
    }

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Staging Package Inventory',
        'read_only':True,
        'report_only':True,
        'filter':q,
        'folder':str(root),
        'summary':summary,
        'by_status':list(by_status.values()),
        'by_risk':list(by_risk.values()),
        'packages':packages,
        'errors':scan_errors,
        'safety':{
            'read_only_viewer':True,
            'no_restore':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'inventory_export_only':True
        }
    }

    if export:
        out=ROOT/'Reports'/'Backups'/'StagingInventory'
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=out/f'Staging_Package_Inventory_{stamp}.json'
        md_path=out/f'Staging_Package_Inventory_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Staging Package Inventory','',
            f"Created: {report['created']}",
            f"Folder: {report['folder']}",
            f"Filter: {q or 'none'}",
            '',
            '## Safety','',
            '- Read-only viewer.',
            '- No restore.',
            '- No overwrite.',
            '- No copy-back.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '',
            '## Summary','',
            f"- Packages: {summary['packages']}",
            f"- OK: {summary['ok']}",
            f"- Problems: {summary['problems']}",
            f"- Verified: {summary['verified']}",
            f"- Live target untouched: {summary['live_target_untouched']}",
            f"- Restore allowed now: {summary['restore_allowed_now']}",
            f"- Files: {summary['files']}",
            f"- Total bytes: {summary['bytes']}",
            f"- Scan errors: {summary['scan_errors']}",
            f"- Latest package: {summary['latest_package']}",
            f"- Latest created: {summary['latest_created']}",
            '',
            '## Packages',''
        ]
        for p in packages:
            lines += [
                f"### {'OK' if p.get('ok') else 'PROBLEM'}: {p.get('name')}",
                '',
                f"- Created: {p.get('created')}",
                f"- Stage folder: `{p.get('stage_dir')}`",
                f"- Staged copy: `{p.get('staged_copy')}`",
                f"- Staged copy exists: {p.get('staged_copy_exists')}",
                f"- Source backup: `{p.get('source_backup')}`",
                f"- Future target: `{p.get('future_target')}`",
                f"- Live target untouched: {p.get('live_target_untouched')}",
                f"- Candidate status: `{p.get('candidate_status')}`",
                f"- Preview risk: `{p.get('preview_risk')}`",
                f"- Same hash: {p.get('same_hash')}",
                f"- Future confirmation phrase: `{p.get('future_confirmation_phrase')}`",
                f"- Verification OK: {p.get('verification_ok')}",
                f"- Verification: {p.get('verification_message')}",
                f"- Metadata: `{p.get('metadata')}`",
                f"- Markdown: `{p.get('markdown')}`",
                f"- Readiness: `{p.get('readiness')}`",
                f"- Preview: `{p.get('preview')}`",
                f"- Repair action log: `{p.get('repair_action_log_markdown') or p.get('repair_action_log_json')}`",
                '',
                'Required files:',
            ]
            for k,v in p.get('required_files',{}).items():
                lines.append(f"- {'PASS' if v else 'MISSING'} `{k}`")
            lines += ['','Included files:']
            for f in p.get('files',[]):
                lines.append(f"- `{f.get('name')}` — {f.get('size')} bytes")
            lines.append('')
        if scan_errors:
            lines += ['## Errors','']
            for e in scan_errors:
                lines.append(f"- `{e.get('path')}`: {e.get('error')}")
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def _find_staging_package(stage_dir_text):
    inv=staging_package_inventory({'limit':2000})
    if not inv.get('ok'):
        return None, inv
    wanted=str(Path(stage_dir_text).resolve()).lower() if stage_dir_text else ''
    if not wanted:
        packages=inv.get('packages') or []
        return (packages[0] if packages else None), inv
    for p in inv.get('packages',[]):
        try:
            if str(Path(p.get('stage_dir','')).resolve()).lower()==wanted:
                return p, inv
        except Exception:
            pass
    # Also allow selecting metadata/staged copy path within the package.
    for p in inv.get('packages',[]):
        try:
            sd=Path(p.get('stage_dir','')).resolve()
            test=Path(stage_dir_text).resolve()
            if test==sd or sd in test.parents:
                return p, inv
        except Exception:
            pass
    return None, inv

def restore_final_checklist(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    stage_dir=(d.get('stage_dir') or d.get('path') or '').strip()
    package,inv=_find_staging_package(stage_dir)
    if not package:
        return {'ok':False,'message':'No staging package found. Create or select a staging package first.','read_only':True,'report_only':True,'restore_allowed_now':False,'inventory':inv}

    stage_path=Path(package.get('stage_dir',''))
    meta_path=Path(package.get('metadata','')) if package.get('metadata') else stage_path/'staging_metadata.json'
    readiness_path=Path(package.get('readiness','')) if package.get('readiness') else stage_path/'readiness_gate.json'
    preview_path=Path(package.get('preview','')) if package.get('preview') else stage_path/'restore_preview.json'
    report_path=Path(package.get('markdown','')) if package.get('markdown') else stage_path/'staging_report.md'
    staged_copy=Path(package.get('staged_copy','')) if package.get('staged_copy') else None
    source_backup=Path(package.get('source_backup','')) if package.get('source_backup') else None
    future_target=Path(package.get('future_target','')) if package.get('future_target') else None

    meta={}
    readiness={}
    preview={}
    read_errors=[]
    for label,path,objname in [('metadata',meta_path,'meta'),('readiness',readiness_path,'readiness'),('preview',preview_path,'preview')]:
        try:
            if path.exists():
                data=json.loads(path.read_text(encoding='utf-8',errors='replace'))
                if objname=='meta': meta=data
                elif objname=='readiness': readiness=data
                elif objname=='preview': preview=data
            else:
                read_errors.append(f'{label} file missing: {path}')
        except Exception as e:
            read_errors.append(f'{label} read error: {e}')

    checks=[]
    def add(cid,status,message,detail=''):
        checks.append({'id':cid,'status':status,'ok':status=='pass','message':message,'detail':detail})

    # Basic package checks.
    add('stage_folder_exists','pass' if stage_path.exists() and stage_path.is_dir() else 'block','Stage folder exists.' if stage_path.exists() and stage_path.is_dir() else 'Stage folder missing.',str(stage_path))
    required={
        'staging_metadata.json':meta_path,
        'staging_report.md':report_path,
        'readiness_gate.json':readiness_path,
        'restore_preview.json':preview_path,
        'staged_copy':staged_copy
    }
    for name,path in required.items():
        ok=bool(path and path.exists() and path.is_file())
        add(f'required_{slug(name)}','pass' if ok else 'block',f'Required file present: {name}.' if ok else f'Required file missing: {name}.',str(path) if path else '')

    # Safety flags and package condition.
    add('package_viewer_ok','pass' if package.get('ok') else 'block','Staging Package Viewer marked package OK.' if package.get('ok') else 'Staging Package Viewer found package problem.',package.get('name',''))
    add('staging_verification_ok','pass' if package.get('verification_ok') else 'block','Staging verification passed.' if package.get('verification_ok') else 'Staging verification did not pass.',package.get('verification_message',''))
    add('package_live_target_untouched','pass' if package.get('live_target_untouched') else 'block','Package records live target untouched.' if package.get('live_target_untouched') else 'Package does not prove live target untouched.',package.get('future_target',''))

    # Hash/source checks.
    staged_hash=''
    backup_hash=''
    target_hash_now=''
    target_unchanged_since_staging=False
    source_backup_exists=bool(source_backup and source_backup.exists() and source_backup.is_file())
    staged_copy_exists=bool(staged_copy and staged_copy.exists() and staged_copy.is_file())
    add('source_backup_exists','pass' if source_backup_exists else 'block','Source backup exists.' if source_backup_exists else 'Source backup missing.',str(source_backup) if source_backup else '')
    add('staged_copy_exists_now','pass' if staged_copy_exists else 'block','Staged copy still exists.' if staged_copy_exists else 'Staged copy missing.',str(staged_copy) if staged_copy else '')

    if staged_copy_exists:
        try: staged_hash=_sha256_file(staged_copy)
        except Exception as e: add('staged_hash_readable','block',f'Staged copy hash could not be read: {e}',str(staged_copy))
    if source_backup_exists:
        try: backup_hash=_sha256_file(source_backup)
        except Exception as e: add('source_backup_hash_readable','block',f'Source backup hash could not be read: {e}',str(source_backup))
    if staged_copy_exists and source_backup_exists:
        add('staged_hash_matches_source','pass' if staged_hash==backup_hash else 'block','Staged copy hash still matches source backup.' if staged_hash==backup_hash else 'Staged copy hash differs from source backup.',f'staged={staged_hash} source={backup_hash}')

    # Readiness/preview checks.
    readiness_summary=readiness.get('summary') or package
    hard_blocks=readiness_summary.get('hard_block_ids') or []
    add('readiness_no_hard_blocks','pass' if not hard_blocks else 'block','Readiness gate had no hard blocks excluding intentional restore lock.' if not hard_blocks else 'Readiness gate has hard block(s).',', '.join(hard_blocks))
    candidate=readiness_summary.get('candidate_status') or package.get('candidate_status','')
    add('candidate_status_preview_only','pass' if str(candidate).startswith('eligible_preview_only') else 'warn','Candidate is preview-only eligible.' if str(candidate).startswith('eligible_preview_only') else 'Candidate status is not preview-only eligible.',candidate)
    preview_risk=readiness_summary.get('preview_risk') or package.get('preview_risk','')
    add('preview_risk_recorded','pass' if preview_risk in {'low','medium','blocked'} else 'warn','Preview risk is recorded.' if preview_risk else 'Preview risk not recorded.',preview_risk)
    add('restore_allowed_false','pass' if not package.get('restore_allowed_now') and not meta.get('restore_allowed_now') and not readiness.get('restore_allowed_now') else 'block','Restore is still not allowed by package/readiness metadata.' if not package.get('restore_allowed_now') and not meta.get('restore_allowed_now') and not readiness.get('restore_allowed_now') else 'A restore_allowed flag was true; keep blocked.', '')

    # Target current state must match "after staging" proof.
    target_exists_now=False
    target_hash_after=package.get('target_hash_after') or meta.get('target',{}).get('sha256_after','')
    target_mtime_after=meta.get('target',{}).get('file_modified_time_after','')
    target_mtime_now=''
    if future_target:
        try:
            target_exists_now=future_target.exists() and future_target.is_file()
            add('future_target_exists_now','pass' if target_exists_now else 'warn','Future target exists now.' if target_exists_now else 'Future target does not exist now.',str(future_target))
            if target_exists_now:
                target_hash_now=_sha256_file(future_target)
                target_mtime_now=datetime.fromtimestamp(future_target.stat().st_mtime).isoformat(timespec='seconds')
                add('target_hash_current_readable','pass','Current target hash was calculated.',target_hash_now)
                if target_hash_after:
                    target_unchanged_since_staging=(target_hash_now==target_hash_after)
                    add('target_still_matches_post_staging_hash','pass' if target_unchanged_since_staging else 'block','Current target still matches post-staging hash.' if target_unchanged_since_staging else 'Current target changed since staging.',f'now={target_hash_now} after_staging={target_hash_after}')
                else:
                    add('post_staging_target_hash_recorded','warn','Post-staging target hash was not recorded.','')
        except Exception as e:
            add('target_current_check','block',f'Could not check current target: {e}',str(future_target))
    else:
        add('future_target_known','block','Future target path is unknown.','')

    # Confirmation phrase.
    phrase=meta.get('future_confirmation_phrase') or readiness.get('future_confirmation_phrase') or package.get('future_confirmation_phrase') or ''
    if not phrase and source_backup and future_target:
        phrase=f"RESTORE {source_backup.name} TO {future_target.name}"
    final_phrase=f"FINAL CHECK ONLY - {phrase}" if phrase else "FINAL CHECK ONLY - RESTORE PHRASE UNAVAILABLE"
    add('future_confirmation_phrase_present','pass' if phrase else 'warn','Future confirmation phrase is present.' if phrase else 'Future confirmation phrase missing.',phrase)

    # Final intentional lock.
    add('actual_restore_still_blocked','block','Actual restore remains intentionally blocked in this build.','No restore endpoint/button exists.')

    pass_count=sum(1 for c in checks if c['status']=='pass')
    warn_count=sum(1 for c in checks if c['status']=='warn')
    block_count=sum(1 for c in checks if c['status']=='block')
    hard_blocks=[c['id'] for c in checks if c['status']=='block' and c['id']!='actual_restore_still_blocked']
    status='blocked'
    if not hard_blocks:
        status='final_check_passed_restore_still_locked' if warn_count==0 else 'final_check_passed_with_warnings_restore_still_locked'

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Restore Final Checklist',
        'read_only':True,
        'report_only':True,
        'restore_allowed_now':False,
        'final_status':status,
        'final_confirmation_phrase':final_phrase,
        'future_restore_phrase':phrase,
        'summary':{
            'checks':len(checks),
            'pass':pass_count,
            'warn':warn_count,
            'block':block_count,
            'hard_blocks':len(hard_blocks),
            'hard_block_ids':hard_blocks,
            'final_status':status,
            'restore_allowed_now':False,
            'stage_package':package.get('name',''),
            'stage_dir':str(stage_path),
            'staged_copy':str(staged_copy) if staged_copy else '',
            'source_backup':str(source_backup) if source_backup else '',
            'future_target':str(future_target) if future_target else '',
            'preview_risk':preview_risk,
            'candidate_status':candidate,
            'target_unchanged_since_staging':target_unchanged_since_staging,
            'read_errors':len(read_errors)
        },
        'checks':checks,
        'package':package,
        'metadata_paths':{
            'metadata':str(meta_path),
            'staging_report':str(report_path),
            'readiness_gate':str(readiness_path),
            'restore_preview':str(preview_path)
        },
        'hashes':{
            'source_backup_sha256':backup_hash,
            'staged_copy_sha256':staged_hash,
            'target_sha256_after_staging':target_hash_after,
            'target_sha256_now':target_hash_now
        },
        'read_errors':read_errors,
        'safety':{
            'no_restore_button':True,
            'no_restore_endpoint':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'final_check_only':True
        }
    }

    if export:
        out=ROOT/'Reports'/'Backups'/'FinalChecklist'
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name=slug(package.get('name','staging_package'))[:80]
        json_path=out/f'Restore_Final_Checklist_{safe_name}_{stamp}.json'
        md_path=out/f'Restore_Final_Checklist_{safe_name}_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Restore Final Checklist','',
            f"Created: {report['created']}",
            '',
            '## Safety Lock','',
            '- Final check only.',
            '- Actual restore is still unavailable.',
            '- No restore button.',
            '- No restore endpoint.',
            '- No overwrite.',
            '- No copy-back.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '',
            '## Summary','',
            f"- Final status: `{status}`",
            f"- Restore allowed now: {False}",
            f"- Checks: {len(checks)}",
            f"- Passed: {pass_count}",
            f"- Warnings: {warn_count}",
            f"- Blocks: {block_count}",
            f"- Hard blocks excluding intentional restore lock: {len(hard_blocks)}",
            f"- Stage package: `{package.get('name','')}`",
            f"- Stage folder: `{stage_path}`",
            f"- Staged copy: `{staged_copy}`",
            f"- Source backup: `{source_backup}`",
            f"- Future target: `{future_target}`",
            f"- Preview risk: `{preview_risk}`",
            f"- Candidate status: `{candidate}`",
            f"- Target unchanged since staging: {target_unchanged_since_staging}",
            f"- Final confirmation phrase: `{final_phrase}`",
            '',
            '## Checks',''
        ]
        for c in checks:
            lines.append(f"- **{c.get('status','').upper()}** `{c.get('id')}` — {c.get('message')} {('— '+c.get('detail')) if c.get('detail') else ''}")
        lines += [
            '',
            '## Hashes','',
            f"- Source backup SHA256: `{backup_hash}`",
            f"- Staged copy SHA256: `{staged_hash}`",
            f"- Target SHA256 after staging: `{target_hash_after}`",
            f"- Target SHA256 now: `{target_hash_now}`",
            '',
            '## Metadata Paths','',
            f"- Metadata: `{meta_path}`",
            f"- Staging report: `{report_path}`",
            f"- Readiness gate: `{readiness_path}`",
            f"- Restore preview: `{preview_path}`"
        ]
        if read_errors:
            lines += ['','## Read Errors','']
            for e in read_errors:
                lines.append(f"- {e}")
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def single_file_restore_action(d=None):
    d=d or {}
    stage_dir=(d.get('stage_dir') or d.get('path') or '').strip()
    confirm=(d.get('confirm') or '').strip()
    if not stage_dir:
        return {'ok':False,'message':'No staging package selected.','restore_allowed_now':False}

    final=restore_final_checklist({'stage_dir':stage_dir,'export':False})
    if not final.get('ok'):
        return {'ok':False,'message':'Final checklist could not be built. '+final.get('message',''),'restore_allowed_now':False,'final_checklist':final}

    future_phrase=final.get('future_restore_phrase') or ''
    if not future_phrase:
        return {'ok':False,'message':'Restore blocked: no future restore phrase is available.','restore_allowed_now':False,'final_checklist':final}

    if confirm != future_phrase:
        return {
            'ok':False,
            'message':'Restore blocked: exact confirmation phrase did not match.',
            'requires_confirmation':True,
            'expected_confirmation':future_phrase,
            'restore_allowed_now':False,
            'final_checklist_summary':final.get('summary',{})
        }

    summary=final.get('summary') or {}
    hard_blocks=summary.get('hard_block_ids') or []
    if hard_blocks:
        return {'ok':False,'message':'Restore blocked by hard final-check issue(s): '+', '.join(hard_blocks),'restore_allowed_now':False,'final_checklist':final}

    if final.get('final_status') not in {'final_check_passed_restore_still_locked','final_check_passed_with_warnings_restore_still_locked'}:
        return {'ok':False,'message':'Restore blocked: final checklist status is not eligible.','restore_allowed_now':False,'final_checklist':final}

    package=final.get('package') or {}
    hashes=final.get('hashes') or {}
    staged_copy=Path(summary.get('staged_copy') or package.get('staged_copy') or '')
    source_backup=Path(summary.get('source_backup') or package.get('source_backup') or '')
    target=Path(summary.get('future_target') or package.get('future_target') or '')

    if not staged_copy.exists() or not staged_copy.is_file():
        return {'ok':False,'message':'Restore blocked: staged copy is missing.','restore_allowed_now':False}
    if not source_backup.exists() or not source_backup.is_file():
        return {'ok':False,'message':'Restore blocked: source backup is missing.','restore_allowed_now':False}
    if not target.exists() or not target.is_file():
        return {'ok':False,'message':'Restore blocked: live target is missing. This first restore action only overwrites an existing original target.','restore_allowed_now':False,'target':str(target)}

    # Path containment: target must stay inside FOXAI root; staged copy must stay inside RestoreStaging.
    rr=ROOT.resolve()
    tr=target.resolve()
    if not (tr==rr or rr in tr.parents):
        return {'ok':False,'message':'Restore blocked: target is outside FOXAI root.','restore_allowed_now':False,'target':str(target)}

    staging_root=(ROOT/'Reports'/'Backups'/'RestoreStaging').resolve()
    sr=staged_copy.resolve()
    if not (sr==staging_root or staging_root in sr.parents):
        return {'ok':False,'message':'Restore blocked: staged copy is outside RestoreStaging.','restore_allowed_now':False,'staged_copy':str(staged_copy)}

    expected_target_before=hashes.get('target_sha256_now') or hashes.get('target_sha256_after_staging') or ''
    target_hash_before=_sha256_file(target)
    if expected_target_before and target_hash_before != expected_target_before:
        return {
            'ok':False,
            'message':'Restore blocked: live target changed after final checklist. Run staging/final checklist again.',
            'restore_allowed_now':False,
            'expected_target_hash':expected_target_before,
            'current_target_hash':target_hash_before,
            'target':str(target)
        }

    staged_hash=_sha256_file(staged_copy)
    source_hash=_sha256_file(source_backup)
    if staged_hash != source_hash:
        return {
            'ok':False,
            'message':'Restore blocked: staged copy no longer matches source backup.',
            'restore_allowed_now':False,
            'staged_hash':staged_hash,
            'source_hash':source_hash
        }

    # Create pre-restore live target backup.
    live_backup_root=ROOT/'Backups'/'RestoreLiveTargets'
    live_backup_root.mkdir(parents=True,exist_ok=True)
    reports_root=ROOT/'Reports'/'Backups'/'RestoreActions'
    reports_root.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_target=slug(target.stem)[:80]
    live_backup=live_backup_root/f'PRE_RESTORE_{safe_target}_{stamp}{target.suffix}'
    shutil.copy2(target,live_backup)
    live_backup_hash=_sha256_file(live_backup)
    if live_backup_hash != target_hash_before:
        return {
            'ok':False,
            'message':'Restore blocked after live backup: live backup hash did not match target before hash. Target was not overwritten.',
            'restore_allowed_now':False,
            'target_hash_before':target_hash_before,
            'live_backup_hash':live_backup_hash,
            'live_backup':str(live_backup)
        }

    target_stat_before=target.stat()
    target_mtime_before=datetime.fromtimestamp(target_stat_before.st_mtime).isoformat(timespec='seconds')
    target_size_before=target_stat_before.st_size

    # Actual restore: staged copy -> target. This is the only live-target write.
    shutil.copy2(staged_copy,target)

    target_hash_after=_sha256_file(target)
    target_stat_after=target.stat()
    target_mtime_after=datetime.fromtimestamp(target_stat_after.st_mtime).isoformat(timespec='seconds')
    target_size_after=target_stat_after.st_size

    verification_checks=[
        {'id':'confirmation_phrase_exact','ok':confirm==future_phrase,'message':'Exact restore confirmation phrase matched.','path':''},
        {'id':'final_check_had_no_hard_blocks','ok':not hard_blocks,'message':'Final checklist had no hard blocks except intentional restore lock.','path':''},
        {'id':'target_hash_before_matched_final_check','ok':(not expected_target_before or target_hash_before==expected_target_before),'message':'Target hash before restore matched final checklist.','path':str(target)},
        {'id':'pre_restore_backup_created','ok':live_backup.exists() and live_backup.is_file(),'message':'Pre-restore live target backup exists.','path':str(live_backup)},
        {'id':'pre_restore_backup_hash_matches_old_target','ok':live_backup_hash==target_hash_before,'message':'Pre-restore backup hash matches old target.','path':str(live_backup)},
        {'id':'staged_copy_hash_matches_source_backup','ok':staged_hash==source_hash,'message':'Staged copy hash matches source backup.','path':str(staged_copy)},
        {'id':'target_hash_after_matches_staged_copy','ok':target_hash_after==staged_hash,'message':'Target hash after restore matches staged copy.','path':str(target)},
        {'id':'target_size_after_matches_staged_copy','ok':target_size_after==staged_copy.stat().st_size,'message':'Target size after restore matches staged copy.','path':str(target)},
        {'id':'no_delete_no_install_no_model_cleanup','ok':True,'message':'Restore action performed only single-file copy with no delete/install/model cleanup.','path':''}
    ]
    verification_ok=all(c.get('ok') for c in verification_checks)

    payload={
        'ok':verification_ok,
        'created':now(),
        'title':'Kayock Single-File Restore Action',
        'action_id':'single_file_restore',
        'read_only':False,
        'user_approved_action':True,
        'restore_allowed_now':True,
        'message':'Single-file restore completed and verified.' if verification_ok else 'Single-file restore completed but verification failed.',
        'stage_dir':str(Path(stage_dir)),
        'staged_copy':str(staged_copy),
        'source_backup':str(source_backup),
        'target':str(target),
        'pre_restore_live_backup':str(live_backup),
        'confirmation_phrase':future_phrase,
        'hashes':{
            'target_before':target_hash_before,
            'live_backup':live_backup_hash,
            'staged_copy':staged_hash,
            'source_backup':source_hash,
            'target_after':target_hash_after
        },
        'sizes':{
            'target_before':target_size_before,
            'target_after':target_size_after,
            'staged_copy':staged_copy.stat().st_size,
            'live_backup':live_backup.stat().st_size
        },
        'times':{
            'target_mtime_before':target_mtime_before,
            'target_mtime_after':target_mtime_after
        },
        'verification':{
            'ok':verification_ok,
            'checked':len(verification_checks),
            'passed':sum(1 for c in verification_checks if c.get('ok')),
            'failed':sum(1 for c in verification_checks if not c.get('ok')),
            'message':f"Single-file restore verification {'passed' if verification_ok else 'failed'}: {sum(1 for c in verification_checks if c.get('ok'))}/{len(verification_checks)} check(s) passed.",
            'checks':verification_checks
        },
        'safety':{
            'single_file_only':True,
            'from_staging_package_only':True,
            'original_target_only':True,
            'pre_restore_live_backup_required':True,
            'exact_confirmation_phrase_required':True,
            'no_folder_restore':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True
        }
    }

    json_path=reports_root/f'Single_File_Restore_{safe_target}_{stamp}.json'
    md_path=reports_root/f'Single_File_Restore_{safe_target}_{stamp}.md'
    jwrite(json_path,payload)
    lines=[
        '# Kayock Single-File Restore Action','',
        f"Created: {payload['created']}",
        '',
        '## Result','',
        f"- OK: {payload['ok']}",
        f"- Message: {payload['message']}",
        f"- Target: `{target}`",
        f"- Staged copy: `{staged_copy}`",
        f"- Source backup: `{source_backup}`",
        f"- Pre-restore live backup: `{live_backup}`",
        '',
        '## Verification','',
        f"- Verification OK: {verification_ok}",
        f"- Message: {payload['verification']['message']}",
        ''
    ]
    for c in verification_checks:
        status='PASS' if c.get('ok') else 'FAIL'
        lines.append(f"- **{status}** `{c.get('id')}` — {c.get('message')} {('`'+c.get('path','')+'`') if c.get('path') else ''}")
    lines += [
        '',
        '## Hashes','',
        f"- Target before: `{target_hash_before}`",
        f"- Pre-restore live backup: `{live_backup_hash}`",
        f"- Staged copy: `{staged_hash}`",
        f"- Source backup: `{source_hash}`",
        f"- Target after: `{target_hash_after}`",
        '',
        '## Safety','',
        '- Single file only.',
        '- From staging package only.',
        '- Original target only.',
        '- Pre-restore live backup created before overwrite.',
        '- Exact confirmation phrase required.',
        '- No folder restore.',
        '- No delete.',
        '- No install.',
        '- No model cleanup.'
    ]
    md_path.write_text('\n'.join(lines),encoding='utf-8')
    payload['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(reports_root)}

    # RepairActions log for central audit history.
    repair_result={
        'ok':verification_ok,
        'message':payload['message'],
        'target':str(target),
        'backup':str(live_backup),
        'action_id':'single_file_restore',
        'stage_dir':str(Path(stage_dir)),
        'staged_copy':str(staged_copy),
        'restore_report':str(md_path),
        'verification':payload['verification']
    }
    try:
        action_log=repair_action_log('single_file_restore',repair_result,dry_run=False)
        payload['repair_action_log']=action_log.get('exported',{})
        jwrite(json_path,payload)
    except Exception as e:
        payload['repair_action_log_error']=str(e)

    return payload



def restore_action_audit_inventory(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    q=(d.get('query') or d.get('filter') or '').strip().lower()
    limit=int(d.get('limit') or 1000)
    reports_root=ROOT/'Reports'/'Backups'/'RestoreActions'
    reports_root.mkdir(parents=True,exist_ok=True)
    live_backup_root=ROOT/'Backups'/'RestoreLiveTargets'
    live_backup_root.mkdir(parents=True,exist_ok=True)

    actions=[]
    errors=[]
    report_files=sorted(reports_root.glob('Single_File_Restore_*.json'), key=lambda p:p.stat().st_mtime if p.exists() else 0, reverse=True)
    for report_path in report_files:
        try:
            payload=json.loads(report_path.read_text(encoding='utf-8',errors='replace'))
            target_path=payload.get('target','')
            staged_path=payload.get('staged_copy','')
            source_path=payload.get('source_backup','')
            live_backup_path=payload.get('pre_restore_live_backup','')
            hashes=payload.get('hashes') or {}
            verification=payload.get('verification') or {}
            repair_log=payload.get('repair_action_log') or {}
            exported=payload.get('exported') or {}

            def fexists(p):
                try:
                    return bool(p and Path(p).exists() and Path(p).is_file())
                except Exception:
                    return False

            target_exists=fexists(target_path)
            staged_exists=fexists(staged_path)
            source_exists=fexists(source_path)
            live_backup_exists=fexists(live_backup_path)
            markdown_path=exported.get('markdown') or str(report_path.with_suffix('.md'))
            markdown_exists=fexists(markdown_path)
            repair_log_markdown=repair_log.get('markdown','') if isinstance(repair_log,dict) else ''
            repair_log_json=repair_log.get('json','') if isinstance(repair_log,dict) else ''
            repair_log_exists=fexists(repair_log_markdown) or fexists(repair_log_json)

            target_current_hash=''
            target_current_matches_restored=None
            target_current_mtime=''
            target_current_size=None
            if target_exists:
                try:
                    tp=Path(target_path)
                    target_current_hash=_sha256_file(tp)
                    target_current_matches_restored=(target_current_hash==hashes.get('target_after',''))
                    target_current_mtime=datetime.fromtimestamp(tp.stat().st_mtime).isoformat(timespec='seconds')
                    target_current_size=tp.stat().st_size
                except Exception as e:
                    errors.append({'path':target_path,'error':str(e)})

            live_backup_current_hash=''
            live_backup_hash_ok=None
            if live_backup_exists:
                try:
                    live_backup_current_hash=_sha256_file(Path(live_backup_path))
                    live_backup_hash_ok=(live_backup_current_hash==hashes.get('live_backup',''))
                except Exception as e:
                    errors.append({'path':live_backup_path,'error':str(e)})

            staged_current_hash=''
            staged_hash_ok=None
            if staged_exists:
                try:
                    staged_current_hash=_sha256_file(Path(staged_path))
                    staged_hash_ok=(staged_current_hash==hashes.get('staged_copy',''))
                except Exception as e:
                    errors.append({'path':staged_path,'error':str(e)})

            checks=[
                {'id':'restore_report_json_exists','ok':report_path.exists(),'message':'Restore action JSON report exists.','path':str(report_path)},
                {'id':'restore_report_markdown_exists','ok':markdown_exists,'message':'Restore action Markdown report exists.','path':markdown_path},
                {'id':'action_verification_ok','ok':bool(verification.get('ok')),'message':'Original restore action verification passed.','path':''},
                {'id':'pre_restore_live_backup_exists','ok':live_backup_exists,'message':'Pre-restore live backup exists.','path':live_backup_path},
                {'id':'pre_restore_live_backup_hash_intact','ok':bool(live_backup_hash_ok),'message':'Pre-restore live backup hash still matches recorded hash.','path':live_backup_path},
                {'id':'staged_copy_exists','ok':staged_exists,'message':'Staged copy still exists.','path':staged_path},
                {'id':'staged_copy_hash_intact','ok':bool(staged_hash_ok),'message':'Staged copy hash still matches recorded hash.','path':staged_path},
                {'id':'target_exists_now','ok':target_exists,'message':'Target exists now.','path':target_path},
                {'id':'target_current_hash_readable','ok':bool(target_current_hash),'message':'Current target hash was calculated.','path':target_path},
                {'id':'target_still_matches_restored_hash','ok':bool(target_current_matches_restored),'message':'Current target still matches restored hash.','path':target_path},
                {'id':'repair_action_log_exists','ok':repair_log_exists,'message':'RepairActions audit log exists.','path':repair_log_markdown or repair_log_json}
            ]

            intact=bool(verification.get('ok')) and live_backup_exists and bool(live_backup_hash_ok) and bool(staged_hash_ok) and target_exists and bool(target_current_matches_restored)
            status='intact' if intact else 'attention'

            item={
                'name':report_path.stem,
                'status':status,
                'ok':bool(payload.get('ok')),
                'created':payload.get('created',''),
                'message':payload.get('message',''),
                'target':target_path,
                'staged_copy':staged_path,
                'source_backup':source_path,
                'pre_restore_live_backup':live_backup_path,
                'confirmation_phrase':payload.get('confirmation_phrase',''),
                'restore_report_json':str(report_path),
                'restore_report_markdown':markdown_path,
                'repair_action_log_json':repair_log_json,
                'repair_action_log_markdown':repair_log_markdown,
                'verification_ok':bool(verification.get('ok')),
                'verification_checked':verification.get('checked',0),
                'verification_passed':verification.get('passed',0),
                'verification_failed':verification.get('failed',0),
                'verification_message':verification.get('message',''),
                'target_exists_now':target_exists,
                'target_current_hash':target_current_hash,
                'target_current_mtime':target_current_mtime,
                'target_current_size':target_current_size,
                'target_current_matches_restored_hash':target_current_matches_restored,
                'pre_restore_live_backup_exists':live_backup_exists,
                'pre_restore_live_backup_hash_intact':live_backup_hash_ok,
                'staged_copy_exists':staged_exists,
                'staged_copy_hash_intact':staged_hash_ok,
                'source_backup_exists':source_exists,
                'hashes':hashes,
                'sizes':payload.get('sizes') or {},
                'times':payload.get('times') or {},
                'safety':payload.get('safety') or {},
                'checks':checks,
                'failed_checks':[c['id'] for c in checks if not c.get('ok')]
            }

            blob=' '.join(str(item.get(k,'')) for k in ['name','status','target','staged_copy','source_backup','pre_restore_live_backup','message','confirmation_phrase']).lower()
            if q and q not in blob:
                continue

            actions.append(item)
            if len(actions)>=limit:
                break
        except Exception as e:
            errors.append({'path':str(report_path),'error':str(e)})

    by_status={}
    by_target={}
    for a in actions:
        status=a.get('status','unknown')
        by_status.setdefault(status,{'status':status,'count':0})
        by_status[status]['count']+=1
        target=a.get('target','unknown')
        by_target.setdefault(target,{'target':target,'count':0,'intact':0,'attention':0})
        by_target[target]['count']+=1
        if status=='intact':
            by_target[target]['intact']+=1
        else:
            by_target[target]['attention']+=1

    summary={
        'actions':len(actions),
        'intact':sum(1 for a in actions if a.get('status')=='intact'),
        'attention':sum(1 for a in actions if a.get('status')!='intact'),
        'verified':sum(1 for a in actions if a.get('verification_ok')),
        'live_backups_present':sum(1 for a in actions if a.get('pre_restore_live_backup_exists')),
        'live_backup_hashes_intact':sum(1 for a in actions if a.get('pre_restore_live_backup_hash_intact')),
        'staged_copy_hashes_intact':sum(1 for a in actions if a.get('staged_copy_hash_intact')),
        'targets_still_restored':sum(1 for a in actions if a.get('target_current_matches_restored_hash')),
        'repair_logs_present':sum(1 for a in actions if a.get('repair_action_log_markdown') or a.get('repair_action_log_json')),
        'errors':len(errors),
        'latest_action':actions[0].get('name','') if actions else '',
        'latest_created':actions[0].get('created','') if actions else ''
    }

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Post-Restore Audit Inventory',
        'read_only':True,
        'report_only':True,
        'filter':q,
        'restore_reports_folder':str(reports_root),
        'live_backup_folder':str(live_backup_root),
        'summary':summary,
        'by_status':list(by_status.values()),
        'by_target':list(by_target.values()),
        'actions':actions,
        'errors':errors,
        'safety':{
            'read_only_viewer':True,
            'no_restore':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'audit_export_only':True
        }
    }

    if export:
        out=ROOT/'Reports'/'Backups'/'RestoreAudit'
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=out/f'Post_Restore_Audit_{stamp}.json'
        md_path=out/f'Post_Restore_Audit_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Post-Restore Audit Inventory','',
            f"Created: {report['created']}",
            f"Restore reports folder: `{reports_root}`",
            f"Live backup folder: `{live_backup_root}`",
            f"Filter: {q or 'none'}",
            '',
            '## Safety','',
            '- Read-only viewer.',
            '- No restore.',
            '- No overwrite.',
            '- No copy-back.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '',
            '## Summary','',
            f"- Actions: {summary['actions']}",
            f"- Intact: {summary['intact']}",
            f"- Attention: {summary['attention']}",
            f"- Verified: {summary['verified']}",
            f"- Live backups present: {summary['live_backups_present']}",
            f"- Live backup hashes intact: {summary['live_backup_hashes_intact']}",
            f"- Staged copy hashes intact: {summary['staged_copy_hashes_intact']}",
            f"- Targets still restored: {summary['targets_still_restored']}",
            f"- Repair logs present: {summary['repair_logs_present']}",
            f"- Errors: {summary['errors']}",
            f"- Latest action: `{summary['latest_action']}`",
            f"- Latest created: {summary['latest_created']}",
            '',
            '## Restore Actions',''
        ]
        for a in actions:
            lines += [
                f"### {a.get('status','').upper()}: {a.get('name')}",
                '',
                f"- Created: {a.get('created')}",
                f"- Message: {a.get('message')}",
                f"- Target: `{a.get('target')}`",
                f"- Staged copy: `{a.get('staged_copy')}`",
                f"- Source backup: `{a.get('source_backup')}`",
                f"- Pre-restore live backup: `{a.get('pre_restore_live_backup')}`",
                f"- Verification OK: {a.get('verification_ok')}",
                f"- Verification: {a.get('verification_message')}",
                f"- Current target hash: `{a.get('target_current_hash')}`",
                f"- Target still matches restored hash: {a.get('target_current_matches_restored_hash')}",
                f"- Live backup hash intact: {a.get('pre_restore_live_backup_hash_intact')}",
                f"- Staged copy hash intact: {a.get('staged_copy_hash_intact')}",
                f"- Restore report: `{a.get('restore_report_markdown') or a.get('restore_report_json')}`",
                f"- Repair log: `{a.get('repair_action_log_markdown') or a.get('repair_action_log_json')}`",
                '',
                'Checks:'
            ]
            for c in a.get('checks',[]):
                lines.append(f"- {'PASS' if c.get('ok') else 'FAIL'} `{c.get('id')}` — {c.get('message')} {('`'+c.get('path','')+'`') if c.get('path') else ''}")
            lines += ['','Hashes:']
            h=a.get('hashes') or {}
            for key in ['target_before','live_backup','staged_copy','source_backup','target_after']:
                lines.append(f"- {key}: `{h.get(key,'')}`")
            lines.append('')
        if errors:
            lines += ['## Errors','']
            for e in errors:
                lines.append(f"- `{e.get('path')}`: {e.get('error')}")
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def rollback_preview_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    action_report=(d.get('action_report') or d.get('path') or '').strip()
    target_override=(d.get('target') or '').strip()
    backup_override=(d.get('pre_restore_backup') or d.get('backup') or '').strip()

    audit=restore_action_audit_inventory({'limit':2000})
    if not audit.get('ok'):
        return {'ok':False,'message':'Could not load restore audit inventory.','read_only':True,'report_only':True,'rollback_allowed_now':False,'audit':audit}

    selected=None
    if action_report:
        wanted=action_report.lower()
        for a in audit.get('actions',[]):
            paths=[
                a.get('restore_report_json',''),
                a.get('restore_report_markdown',''),
                a.get('repair_action_log_json',''),
                a.get('repair_action_log_markdown',''),
                a.get('pre_restore_live_backup',''),
                a.get('target',''),
                a.get('name','')
            ]
            if any(wanted == str(p).lower() or wanted in str(p).lower() for p in paths):
                selected=a
                break
    if not selected and audit.get('actions'):
        selected=audit.get('actions')[0]

    if not selected:
        return {'ok':False,'message':'No completed restore action found to preview rollback.','read_only':True,'report_only':True,'rollback_allowed_now':False}

    backup_path=Path(backup_override or selected.get('pre_restore_live_backup',''))
    target_path=Path(target_override or selected.get('target',''))
    hashes=selected.get('hashes') or {}
    problems=[]
    warnings=[]
    checks=[]

    def add(cid,status,message,detail=''):
        checks.append({'id':cid,'status':status,'ok':status=='pass','message':message,'detail':detail})
        if status=='block':
            problems.append(f'{cid}: {message}')
        elif status=='warn':
            warnings.append(f'{cid}: {message}')

    root_resolved=ROOT.resolve()
    backup_exists=backup_path.exists() and backup_path.is_file()
    target_exists=target_path.exists() and target_path.is_file()

    add('restore_action_selected','pass' if selected else 'block','Completed restore action selected.' if selected else 'No completed restore action selected.',selected.get('name','') if selected else '')
    add('pre_restore_backup_exists','pass' if backup_exists else 'block','Pre-restore live backup exists.' if backup_exists else 'Pre-restore live backup is missing.',str(backup_path))
    add('target_exists','pass' if target_exists else 'block','Current target exists.' if target_exists else 'Current target is missing.',str(target_path))

    target_inside=False
    try:
        target_resolved=target_path.resolve()
        target_inside=(target_resolved==root_resolved or root_resolved in target_resolved.parents)
    except Exception:
        pass
    add('target_inside_root','pass' if target_inside else 'block','Target is inside FOXAI root.' if target_inside else 'Target is outside FOXAI root or could not be validated.',str(target_path))

    live_backup_root=(ROOT/'Backups'/'RestoreLiveTargets').resolve()
    backup_inside=False
    try:
        backup_resolved=backup_path.resolve()
        backup_inside=(backup_resolved==live_backup_root or live_backup_root in backup_resolved.parents)
    except Exception:
        pass
    add('backup_inside_live_backup_vault','pass' if backup_inside else 'block','Pre-restore backup is inside RestoreLiveTargets vault.' if backup_inside else 'Pre-restore backup is outside RestoreLiveTargets vault or could not be validated.',str(backup_path))

    backup_hash=''
    target_hash_now=''
    target_mtime_now=''
    backup_size=None
    target_size=None
    if backup_exists:
        try:
            backup_hash=_sha256_file(backup_path)
            backup_size=backup_path.stat().st_size
            add('pre_restore_backup_hash_readable','pass','Pre-restore backup hash was calculated.',backup_hash)
        except Exception as e:
            add('pre_restore_backup_hash_readable','block',f'Could not calculate pre-restore backup hash: {e}',str(backup_path))
    if target_exists:
        try:
            target_hash_now=_sha256_file(target_path)
            target_size=target_path.stat().st_size
            target_mtime_now=datetime.fromtimestamp(target_path.stat().st_mtime).isoformat(timespec='seconds')
            add('target_hash_readable','pass','Current target hash was calculated.',target_hash_now)
        except Exception as e:
            add('target_hash_readable','block',f'Could not calculate current target hash: {e}',str(target_path))

    recorded_live_backup=hashes.get('live_backup','')
    recorded_target_before=hashes.get('target_before','')
    recorded_target_after=hashes.get('target_after','')
    if backup_hash and recorded_live_backup:
        add('backup_hash_matches_recorded_live_backup','pass' if backup_hash==recorded_live_backup else 'block','Pre-restore backup hash matches recorded live-backup hash.' if backup_hash==recorded_live_backup else 'Pre-restore backup hash does not match recorded live-backup hash.',f'backup={backup_hash} recorded={recorded_live_backup}')
    if backup_hash and recorded_target_before:
        add('backup_hash_matches_old_target','pass' if backup_hash==recorded_target_before else 'block','Pre-restore backup hash matches old target hash.' if backup_hash==recorded_target_before else 'Pre-restore backup hash does not match old target hash.',f'backup={backup_hash} old_target={recorded_target_before}')
    if target_hash_now and recorded_target_after:
        add('current_target_matches_restored_hash','pass' if target_hash_now==recorded_target_after else 'warn','Current target still matches restored hash.' if target_hash_now==recorded_target_after else 'Current target changed since restore; rollback preview may be stale.',f'current={target_hash_now} restored={recorded_target_after}')

    same_hash=False
    if backup_hash and target_hash_now:
        same_hash=(backup_hash==target_hash_now)
        add('rollback_would_change_target','warn' if same_hash else 'pass','Pre-restore backup already matches target; rollback may be unnecessary.' if same_hash else 'Pre-restore backup differs from current target; rollback preview has meaningful value.',f'backup={backup_hash} current={target_hash_now}')

    # Text diff preview.
    text_preview_available=False
    diff_preview=''
    backup_line_count=0
    target_line_count=0
    readable_reason=''
    try:
        if backup_exists and target_exists:
            max_bytes=250000
            if backup_path.stat().st_size <= max_bytes and target_path.stat().st_size <= max_bytes:
                backup_text=backup_path.read_text(encoding='utf-8',errors='replace')
                target_text=target_path.read_text(encoding='utf-8',errors='replace')
                backup_lines=backup_text.splitlines()
                target_lines=target_text.splitlines()
                backup_line_count=len(backup_lines)
                target_line_count=len(target_lines)
                import difflib
                diff_lines=list(difflib.unified_diff(target_lines, backup_lines, fromfile='current_target', tofile='pre_restore_backup_would_rollback_to', lineterm=''))
                if len(diff_lines)>160:
                    diff_preview='\n'.join(diff_lines[:160]+['... diff truncated ...'])
                else:
                    diff_preview='\n'.join(diff_lines)
                text_preview_available=True
                add('text_diff_available','pass','Text diff preview is available.','')
            else:
                readable_reason='Backup or target is too large for inline text diff.'
                add('text_diff_available','warn',readable_reason,'')
    except Exception as e:
        readable_reason=str(e)
        add('text_diff_available','warn','Text diff preview could not be generated.',str(e))

    phrase=''
    if backup_path and target_path:
        phrase=f"ROLLBACK {backup_path.name} TO {target_path.name}"
    add('future_rollback_phrase_present','pass' if phrase else 'block','Future rollback confirmation phrase generated.' if phrase else 'Future rollback confirmation phrase could not be generated.',phrase)

    add('rollback_currently_blocked','block','Actual rollback is intentionally unavailable in this build. Preview only.','No rollback endpoint/button exists.')

    hard_blocks=[c['id'] for c in checks if c['status']=='block' and c['id']!='rollback_currently_blocked']
    pass_count=sum(1 for c in checks if c['status']=='pass')
    warn_count=sum(1 for c in checks if c['status']=='warn')
    block_count=sum(1 for c in checks if c['status']=='block')
    candidate_status='blocked'
    if not hard_blocks:
        candidate_status='rollback_preview_eligible_with_warnings' if warn_count else 'rollback_preview_eligible'

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Rollback Preview From Pre-Restore Backup',
        'read_only':True,
        'report_only':True,
        'rollback_allowed_now':False,
        'candidate_status':candidate_status,
        'future_rollback_phrase':phrase,
        'summary':{
            'checks':len(checks),
            'pass':pass_count,
            'warn':warn_count,
            'block':block_count,
            'hard_blocks':len(hard_blocks),
            'hard_block_ids':hard_blocks,
            'candidate_status':candidate_status,
            'rollback_allowed_now':False,
            'restore_action':selected.get('name',''),
            'target':str(target_path),
            'pre_restore_backup':str(backup_path),
            'backup_exists':backup_exists,
            'target_exists':target_exists,
            'target_inside_root':target_inside,
            'backup_inside_live_backup_vault':backup_inside,
            'same_hash':same_hash,
            'would_overwrite':bool(target_exists and not same_hash),
            'text_preview_available':text_preview_available,
            'warnings':len(warnings),
            'problems':len(problems)
        },
        'checks':checks,
        'restore_action':selected,
        'rollback_source_backup':{
            'path':str(backup_path),
            'exists':backup_exists,
            'sha256':backup_hash,
            'size':backup_size,
            'recorded_live_backup_sha256':recorded_live_backup,
            'recorded_old_target_sha256':recorded_target_before
        },
        'target':{
            'path':str(target_path),
            'exists':target_exists,
            'inside_root':target_inside,
            'sha256_now':target_hash_now,
            'size_now':target_size,
            'file_modified_time_now':target_mtime_now,
            'recorded_restored_sha256':recorded_target_after
        },
        'comparison':{
            'same_hash':same_hash,
            'would_overwrite':bool(target_exists and not same_hash),
            'backup_size':backup_size,
            'target_size':target_size,
            'size_delta_if_rolled_back':(backup_size-target_size) if backup_size is not None and target_size is not None else None,
            'text_preview_available':text_preview_available,
            'backup_line_count':backup_line_count,
            'target_line_count':target_line_count,
            'readable_reason':readable_reason,
            'diff_preview':diff_preview
        },
        'warnings':warnings,
        'problems':problems,
        'safety':{
            'preview_only':True,
            'no_rollback_button':True,
            'no_rollback_endpoint':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True
        }
    }

    if export:
        out=ROOT/'Reports'/'Backups'/'RollbackPreviews'
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name=slug(selected.get('name','restore_action'))[:80]
        json_path=out/f'Rollback_Preview_{safe_name}_{stamp}.json'
        md_path=out/f'Rollback_Preview_{safe_name}_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Rollback Preview From Pre-Restore Backup','',
            f"Created: {report['created']}",
            '',
            '## Safety Lock','',
            '- Preview only.',
            '- Actual rollback is still unavailable.',
            '- No rollback button.',
            '- No rollback endpoint.',
            '- No overwrite.',
            '- No copy-back.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '',
            '## Summary','',
            f"- Candidate status: `{candidate_status}`",
            f"- Rollback allowed now: {False}",
            f"- Checks: {len(checks)}",
            f"- Passed: {pass_count}",
            f"- Warnings: {warn_count}",
            f"- Blocks: {block_count}",
            f"- Hard blocks excluding intentional rollback lock: {len(hard_blocks)}",
            f"- Restore action: `{selected.get('name','')}`",
            f"- Target: `{target_path}`",
            f"- Pre-restore backup: `{backup_path}`",
            f"- Same hash: {same_hash}",
            f"- Would overwrite: {bool(target_exists and not same_hash)}",
            f"- Text diff available: {text_preview_available}",
            f"- Future rollback phrase: `{phrase}`",
            '',
            '## Checks',''
        ]
        for c in checks:
            lines.append(f"- **{c.get('status','').upper()}** `{c.get('id')}` — {c.get('message')} {('— '+c.get('detail')) if c.get('detail') else ''}")
        lines += [
            '',
            '## Hashes','',
            f"- Pre-restore backup SHA256: `{backup_hash}`",
            f"- Recorded live-backup SHA256: `{recorded_live_backup}`",
            f"- Recorded old-target SHA256: `{recorded_target_before}`",
            f"- Current target SHA256: `{target_hash_now}`",
            f"- Recorded restored-target SHA256: `{recorded_target_after}`",
            '',
            '## Diff Preview','',
            '```diff',
            diff_preview or '(no diff preview)',
            '```'
        ]
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def single_file_rollback_action(d=None):
    d=d or {}
    action_report=(d.get('action_report') or d.get('path') or '').strip()
    confirm=(d.get('confirm') or '').strip()
    if not action_report:
        return {'ok':False,'message':'No restore action selected for rollback.','rollback_allowed_now':False}

    preview=rollback_preview_report({'action_report':action_report,'export':False})
    if not preview.get('ok'):
        return {'ok':False,'message':'Rollback preview could not be built. '+preview.get('message',''),'rollback_allowed_now':False,'preview':preview}

    phrase=preview.get('future_rollback_phrase') or ''
    if not phrase:
        return {'ok':False,'message':'Rollback blocked: no rollback phrase is available.','rollback_allowed_now':False,'preview':preview}

    if confirm != phrase:
        return {
            'ok':False,
            'message':'Rollback blocked: exact confirmation phrase did not match.',
            'requires_confirmation':True,
            'expected_confirmation':phrase,
            'rollback_allowed_now':False,
            'preview_summary':preview.get('summary',{})
        }

    summary=preview.get('summary') or {}
    hard_blocks=summary.get('hard_block_ids') or []
    if hard_blocks:
        return {'ok':False,'message':'Rollback blocked by hard preview issue(s): '+', '.join(hard_blocks),'rollback_allowed_now':False,'preview':preview}

    if not str(summary.get('candidate_status','')).startswith('rollback_preview_eligible'):
        return {'ok':False,'message':'Rollback blocked: preview candidate status is not eligible.','rollback_allowed_now':False,'preview':preview}

    backup_info=preview.get('rollback_source_backup') or {}
    target_info=preview.get('target') or {}
    restore_action=preview.get('restore_action') or {}
    backup_path=Path(backup_info.get('path',''))
    target_path=Path(target_info.get('path',''))

    if not backup_path.exists() or not backup_path.is_file():
        return {'ok':False,'message':'Rollback blocked: pre-restore backup is missing.','rollback_allowed_now':False,'backup':str(backup_path)}
    if not target_path.exists() or not target_path.is_file():
        return {'ok':False,'message':'Rollback blocked: target is missing. This first rollback only overwrites an existing original target.','rollback_allowed_now':False,'target':str(target_path)}

    root_resolved=ROOT.resolve()
    target_resolved=target_path.resolve()
    if not (target_resolved==root_resolved or root_resolved in target_resolved.parents):
        return {'ok':False,'message':'Rollback blocked: target is outside FOXAI root.','rollback_allowed_now':False,'target':str(target_path)}

    backup_vault=(ROOT/'Backups'/'RestoreLiveTargets').resolve()
    backup_resolved=backup_path.resolve()
    if not (backup_resolved==backup_vault or backup_vault in backup_resolved.parents):
        return {'ok':False,'message':'Rollback blocked: rollback source is outside RestoreLiveTargets vault.','rollback_allowed_now':False,'backup':str(backup_path)}

    expected_target_before=target_info.get('sha256_now') or target_info.get('recorded_restored_sha256') or ''
    target_hash_before=_sha256_file(target_path)
    if expected_target_before and target_hash_before != expected_target_before:
        return {
            'ok':False,
            'message':'Rollback blocked: target changed after rollback preview. Run rollback preview again.',
            'rollback_allowed_now':False,
            'expected_target_hash':expected_target_before,
            'current_target_hash':target_hash_before,
            'target':str(target_path)
        }

    backup_hash=_sha256_file(backup_path)
    recorded_live_backup=backup_info.get('recorded_live_backup_sha256') or ''
    recorded_old_target=backup_info.get('recorded_old_target_sha256') or ''
    if recorded_live_backup and backup_hash != recorded_live_backup:
        return {
            'ok':False,
            'message':'Rollback blocked: pre-restore backup hash no longer matches recorded live-backup hash.',
            'rollback_allowed_now':False,
            'backup_hash':backup_hash,
            'recorded_live_backup':recorded_live_backup
        }
    if recorded_old_target and backup_hash != recorded_old_target:
        return {
            'ok':False,
            'message':'Rollback blocked: pre-restore backup hash no longer matches old target hash.',
            'rollback_allowed_now':False,
            'backup_hash':backup_hash,
            'recorded_old_target':recorded_old_target
        }

    rollback_live_root=ROOT/'Backups'/'RollbackLiveTargets'
    rollback_live_root.mkdir(parents=True,exist_ok=True)
    reports_root=ROOT/'Reports'/'Backups'/'RollbackActions'
    reports_root.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_target=slug(target_path.stem)[:80]
    current_target_backup=rollback_live_root/f'PRE_ROLLBACK_{safe_target}_{stamp}{target_path.suffix}'

    # Backup the current target before rolling back.
    shutil.copy2(target_path,current_target_backup)
    current_backup_hash=_sha256_file(current_target_backup)
    if current_backup_hash != target_hash_before:
        return {
            'ok':False,
            'message':'Rollback blocked after current-target backup: backup hash did not match target-before hash. Target was not overwritten.',
            'rollback_allowed_now':False,
            'target_hash_before':target_hash_before,
            'current_target_backup_hash':current_backup_hash,
            'current_target_backup':str(current_target_backup)
        }

    target_stat_before=target_path.stat()
    target_mtime_before=datetime.fromtimestamp(target_stat_before.st_mtime).isoformat(timespec='seconds')
    target_size_before=target_stat_before.st_size

    # Actual rollback: pre-restore backup -> target. This is the only live-target write.
    shutil.copy2(backup_path,target_path)

    target_hash_after=_sha256_file(target_path)
    target_stat_after=target_path.stat()
    target_mtime_after=datetime.fromtimestamp(target_stat_after.st_mtime).isoformat(timespec='seconds')
    target_size_after=target_stat_after.st_size

    verification_checks=[
        {'id':'confirmation_phrase_exact','ok':confirm==phrase,'message':'Exact rollback confirmation phrase matched.','path':''},
        {'id':'rollback_preview_had_no_hard_blocks','ok':not hard_blocks,'message':'Rollback preview had no hard blocks except intentional rollback lock.','path':''},
        {'id':'target_hash_before_matched_preview','ok':(not expected_target_before or target_hash_before==expected_target_before),'message':'Target hash before rollback matched rollback preview.','path':str(target_path)},
        {'id':'pre_rollback_current_target_backup_created','ok':current_target_backup.exists() and current_target_backup.is_file(),'message':'Current target backup before rollback exists.','path':str(current_target_backup)},
        {'id':'pre_rollback_backup_hash_matches_current_target','ok':current_backup_hash==target_hash_before,'message':'Pre-rollback backup hash matches current target before rollback.','path':str(current_target_backup)},
        {'id':'rollback_source_backup_hash_matches_recorded_old_target','ok':(not recorded_old_target or backup_hash==recorded_old_target),'message':'Rollback source hash matches recorded old target hash.','path':str(backup_path)},
        {'id':'rollback_source_backup_hash_matches_recorded_live_backup','ok':(not recorded_live_backup or backup_hash==recorded_live_backup),'message':'Rollback source hash matches recorded live backup hash.','path':str(backup_path)},
        {'id':'target_hash_after_matches_rollback_source','ok':target_hash_after==backup_hash,'message':'Target hash after rollback matches pre-restore backup.','path':str(target_path)},
        {'id':'target_size_after_matches_rollback_source','ok':target_size_after==backup_path.stat().st_size,'message':'Target size after rollback matches pre-restore backup.','path':str(target_path)},
        {'id':'no_delete_no_install_no_model_cleanup','ok':True,'message':'Rollback action performed only single-file copy with no delete/install/model cleanup.','path':''}
    ]
    verification_ok=all(c.get('ok') for c in verification_checks)

    payload={
        'ok':verification_ok,
        'created':now(),
        'title':'Kayock Single-File Rollback Action',
        'action_id':'single_file_rollback',
        'read_only':False,
        'user_approved_action':True,
        'rollback_allowed_now':True,
        'message':'Single-file rollback completed and verified.' if verification_ok else 'Single-file rollback completed but verification failed.',
        'restore_action':restore_action.get('name',''),
        'restore_action_report':restore_action.get('restore_report_json') or restore_action.get('restore_report_markdown',''),
        'rollback_source_backup':str(backup_path),
        'target':str(target_path),
        'pre_rollback_current_target_backup':str(current_target_backup),
        'confirmation_phrase':phrase,
        'hashes':{
            'target_before_rollback':target_hash_before,
            'pre_rollback_current_target_backup':current_backup_hash,
            'rollback_source_backup':backup_hash,
            'recorded_old_target':recorded_old_target,
            'recorded_live_backup':recorded_live_backup,
            'target_after_rollback':target_hash_after
        },
        'sizes':{
            'target_before_rollback':target_size_before,
            'target_after_rollback':target_size_after,
            'rollback_source_backup':backup_path.stat().st_size,
            'pre_rollback_current_target_backup':current_target_backup.stat().st_size
        },
        'times':{
            'target_mtime_before_rollback':target_mtime_before,
            'target_mtime_after_rollback':target_mtime_after
        },
        'verification':{
            'ok':verification_ok,
            'checked':len(verification_checks),
            'passed':sum(1 for c in verification_checks if c.get('ok')),
            'failed':sum(1 for c in verification_checks if not c.get('ok')),
            'message':f"Single-file rollback verification {'passed' if verification_ok else 'failed'}: {sum(1 for c in verification_checks if c.get('ok'))}/{len(verification_checks)} check(s) passed.",
            'checks':verification_checks
        },
        'safety':{
            'single_file_only':True,
            'from_pre_restore_backup_only':True,
            'original_target_only':True,
            'pre_rollback_current_target_backup_required':True,
            'exact_confirmation_phrase_required':True,
            'no_folder_rollback':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True
        }
    }

    json_path=reports_root/f'Single_File_Rollback_{safe_target}_{stamp}.json'
    md_path=reports_root/f'Single_File_Rollback_{safe_target}_{stamp}.md'
    jwrite(json_path,payload)
    lines=[
        '# Kayock Single-File Rollback Action','',
        f"Created: {payload['created']}",
        '',
        '## Result','',
        f"- OK: {payload['ok']}",
        f"- Message: {payload['message']}",
        f"- Target: `{target_path}`",
        f"- Rollback source backup: `{backup_path}`",
        f"- Pre-rollback current target backup: `{current_target_backup}`",
        f"- Original restore action: `{payload['restore_action']}`",
        '',
        '## Verification','',
        f"- Verification OK: {verification_ok}",
        f"- Message: {payload['verification']['message']}",
        ''
    ]
    for c in verification_checks:
        status='PASS' if c.get('ok') else 'FAIL'
        lines.append(f"- **{status}** `{c.get('id')}` — {c.get('message')} {('`'+c.get('path','')+'`') if c.get('path') else ''}")
    lines += [
        '',
        '## Hashes','',
        f"- Target before rollback: `{target_hash_before}`",
        f"- Pre-rollback current target backup: `{current_backup_hash}`",
        f"- Rollback source backup: `{backup_hash}`",
        f"- Recorded old target: `{recorded_old_target}`",
        f"- Recorded live backup: `{recorded_live_backup}`",
        f"- Target after rollback: `{target_hash_after}`",
        '',
        '## Safety','',
        '- Single file only.',
        '- From pre-restore live backup only.',
        '- Original target only.',
        '- Current target backed up before rollback.',
        '- Exact confirmation phrase required.',
        '- No folder rollback.',
        '- No delete.',
        '- No install.',
        '- No model cleanup.'
    ]
    md_path.write_text('\n'.join(lines),encoding='utf-8')
    payload['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(reports_root)}

    # RepairActions log for central audit.
    repair_result={
        'ok':verification_ok,
        'message':payload['message'],
        'target':str(target_path),
        'backup':str(current_target_backup),
        'action_id':'single_file_rollback',
        'rollback_source_backup':str(backup_path),
        'rollback_report':str(md_path),
        'verification':payload['verification']
    }
    try:
        action_log=repair_action_log('single_file_rollback',repair_result,dry_run=False)
        payload['repair_action_log']=action_log.get('exported',{})
        jwrite(json_path,payload)
    except Exception as e:
        payload['repair_action_log_error']=str(e)

    return payload



def rollback_action_audit_inventory(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    q=(d.get('query') or d.get('filter') or '').strip().lower()
    limit=int(d.get('limit') or 1000)

    reports_root=ROOT/'Reports'/'Backups'/'RollbackActions'
    reports_root.mkdir(parents=True,exist_ok=True)
    pre_rollback_root=ROOT/'Backups'/'RollbackLiveTargets'
    pre_rollback_root.mkdir(parents=True,exist_ok=True)
    restore_live_root=ROOT/'Backups'/'RestoreLiveTargets'
    restore_live_root.mkdir(parents=True,exist_ok=True)

    actions=[]
    errors=[]
    report_files=sorted(reports_root.glob('Single_File_Rollback_*.json'), key=lambda p:p.stat().st_mtime if p.exists() else 0, reverse=True)

    for report_path in report_files:
        try:
            payload=json.loads(report_path.read_text(encoding='utf-8',errors='replace'))
            target_path=payload.get('target','')
            rollback_source_path=payload.get('rollback_source_backup','')
            pre_rollback_backup_path=payload.get('pre_rollback_current_target_backup','')
            restore_action_report=payload.get('restore_action_report','')
            hashes=payload.get('hashes') or {}
            verification=payload.get('verification') or {}
            repair_log=payload.get('repair_action_log') or {}
            exported=payload.get('exported') or {}

            def fexists(p):
                try:
                    return bool(p and Path(p).exists() and Path(p).is_file())
                except Exception:
                    return False

            target_exists=fexists(target_path)
            rollback_source_exists=fexists(rollback_source_path)
            pre_rollback_backup_exists=fexists(pre_rollback_backup_path)
            restore_action_report_exists=fexists(restore_action_report)
            markdown_path=exported.get('markdown') or str(report_path.with_suffix('.md'))
            markdown_exists=fexists(markdown_path)
            repair_log_markdown=repair_log.get('markdown','') if isinstance(repair_log,dict) else ''
            repair_log_json=repair_log.get('json','') if isinstance(repair_log,dict) else ''
            repair_log_exists=fexists(repair_log_markdown) or fexists(repair_log_json)

            target_current_hash=''
            target_current_matches_rollback_hash=None
            target_current_mtime=''
            target_current_size=None
            if target_exists:
                try:
                    tp=Path(target_path)
                    target_current_hash=_sha256_file(tp)
                    target_current_matches_rollback_hash=(target_current_hash==hashes.get('target_after_rollback',''))
                    target_current_mtime=datetime.fromtimestamp(tp.stat().st_mtime).isoformat(timespec='seconds')
                    target_current_size=tp.stat().st_size
                except Exception as e:
                    errors.append({'path':target_path,'error':str(e)})

            rollback_source_current_hash=''
            rollback_source_hash_intact=None
            if rollback_source_exists:
                try:
                    rollback_source_current_hash=_sha256_file(Path(rollback_source_path))
                    rollback_source_hash_intact=(rollback_source_current_hash==hashes.get('rollback_source_backup',''))
                except Exception as e:
                    errors.append({'path':rollback_source_path,'error':str(e)})

            pre_rollback_backup_current_hash=''
            pre_rollback_backup_hash_intact=None
            if pre_rollback_backup_exists:
                try:
                    pre_rollback_backup_current_hash=_sha256_file(Path(pre_rollback_backup_path))
                    pre_rollback_backup_hash_intact=(pre_rollback_backup_current_hash==hashes.get('pre_rollback_current_target_backup',''))
                except Exception as e:
                    errors.append({'path':pre_rollback_backup_path,'error':str(e)})

            checks=[
                {'id':'rollback_report_json_exists','ok':report_path.exists(),'message':'Rollback action JSON report exists.','path':str(report_path)},
                {'id':'rollback_report_markdown_exists','ok':markdown_exists,'message':'Rollback action Markdown report exists.','path':markdown_path},
                {'id':'action_verification_ok','ok':bool(verification.get('ok')),'message':'Original rollback action verification passed.','path':''},
                {'id':'restore_action_report_exists','ok':restore_action_report_exists,'message':'Original restore action report exists.','path':restore_action_report},
                {'id':'rollback_source_backup_exists','ok':rollback_source_exists,'message':'Rollback source backup exists.','path':rollback_source_path},
                {'id':'rollback_source_backup_hash_intact','ok':bool(rollback_source_hash_intact),'message':'Rollback source backup hash still matches recorded hash.','path':rollback_source_path},
                {'id':'pre_rollback_current_target_backup_exists','ok':pre_rollback_backup_exists,'message':'Pre-rollback current-target backup exists.','path':pre_rollback_backup_path},
                {'id':'pre_rollback_current_target_backup_hash_intact','ok':bool(pre_rollback_backup_hash_intact),'message':'Pre-rollback current-target backup hash still matches recorded hash.','path':pre_rollback_backup_path},
                {'id':'target_exists_now','ok':target_exists,'message':'Target exists now.','path':target_path},
                {'id':'target_current_hash_readable','ok':bool(target_current_hash),'message':'Current target hash was calculated.','path':target_path},
                {'id':'target_still_matches_rollback_hash','ok':bool(target_current_matches_rollback_hash),'message':'Current target still matches rolled-back hash.','path':target_path},
                {'id':'repair_action_log_exists','ok':repair_log_exists,'message':'RepairActions audit log exists.','path':repair_log_markdown or repair_log_json}
            ]

            intact=bool(verification.get('ok')) and rollback_source_exists and bool(rollback_source_hash_intact) and pre_rollback_backup_exists and bool(pre_rollback_backup_hash_intact) and target_exists and bool(target_current_matches_rollback_hash)
            status='intact' if intact else 'attention'

            item={
                'name':report_path.stem,
                'status':status,
                'ok':bool(payload.get('ok')),
                'created':payload.get('created',''),
                'message':payload.get('message',''),
                'restore_action':payload.get('restore_action',''),
                'restore_action_report':restore_action_report,
                'target':target_path,
                'rollback_source_backup':rollback_source_path,
                'pre_rollback_current_target_backup':pre_rollback_backup_path,
                'confirmation_phrase':payload.get('confirmation_phrase',''),
                'rollback_report_json':str(report_path),
                'rollback_report_markdown':markdown_path,
                'repair_action_log_json':repair_log_json,
                'repair_action_log_markdown':repair_log_markdown,
                'verification_ok':bool(verification.get('ok')),
                'verification_checked':verification.get('checked',0),
                'verification_passed':verification.get('passed',0),
                'verification_failed':verification.get('failed',0),
                'verification_message':verification.get('message',''),
                'target_exists_now':target_exists,
                'target_current_hash':target_current_hash,
                'target_current_mtime':target_current_mtime,
                'target_current_size':target_current_size,
                'target_current_matches_rollback_hash':target_current_matches_rollback_hash,
                'rollback_source_backup_exists':rollback_source_exists,
                'rollback_source_backup_hash_intact':rollback_source_hash_intact,
                'pre_rollback_current_target_backup_exists':pre_rollback_backup_exists,
                'pre_rollback_current_target_backup_hash_intact':pre_rollback_backup_hash_intact,
                'restore_action_report_exists':restore_action_report_exists,
                'hashes':hashes,
                'sizes':payload.get('sizes') or {},
                'times':payload.get('times') or {},
                'safety':payload.get('safety') or {},
                'checks':checks,
                'failed_checks':[c['id'] for c in checks if not c.get('ok')]
            }

            blob=' '.join(str(item.get(k,'')) for k in ['name','status','target','rollback_source_backup','pre_rollback_current_target_backup','message','confirmation_phrase','restore_action']).lower()
            if q and q not in blob:
                continue

            actions.append(item)
            if len(actions)>=limit:
                break
        except Exception as e:
            errors.append({'path':str(report_path),'error':str(e)})

    by_status={}
    by_target={}
    for a in actions:
        status=a.get('status','unknown')
        by_status.setdefault(status,{'status':status,'count':0})
        by_status[status]['count']+=1
        target=a.get('target','unknown')
        by_target.setdefault(target,{'target':target,'count':0,'intact':0,'attention':0})
        by_target[target]['count']+=1
        if status=='intact':
            by_target[target]['intact']+=1
        else:
            by_target[target]['attention']+=1

    summary={
        'actions':len(actions),
        'intact':sum(1 for a in actions if a.get('status')=='intact'),
        'attention':sum(1 for a in actions if a.get('status')!='intact'),
        'verified':sum(1 for a in actions if a.get('verification_ok')),
        'rollback_sources_present':sum(1 for a in actions if a.get('rollback_source_backup_exists')),
        'rollback_source_hashes_intact':sum(1 for a in actions if a.get('rollback_source_backup_hash_intact')),
        'pre_rollback_backups_present':sum(1 for a in actions if a.get('pre_rollback_current_target_backup_exists')),
        'pre_rollback_backup_hashes_intact':sum(1 for a in actions if a.get('pre_rollback_current_target_backup_hash_intact')),
        'targets_still_rolled_back':sum(1 for a in actions if a.get('target_current_matches_rollback_hash')),
        'restore_action_reports_present':sum(1 for a in actions if a.get('restore_action_report_exists')),
        'repair_logs_present':sum(1 for a in actions if a.get('repair_action_log_markdown') or a.get('repair_action_log_json')),
        'errors':len(errors),
        'latest_action':actions[0].get('name','') if actions else '',
        'latest_created':actions[0].get('created','') if actions else ''
    }

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Rollback Audit Inventory',
        'read_only':True,
        'report_only':True,
        'filter':q,
        'rollback_reports_folder':str(reports_root),
        'pre_rollback_backup_folder':str(pre_rollback_root),
        'restore_live_backup_folder':str(restore_live_root),
        'summary':summary,
        'by_status':list(by_status.values()),
        'by_target':list(by_target.values()),
        'actions':actions,
        'errors':errors,
        'safety':{
            'read_only_viewer':True,
            'no_rollback':True,
            'no_restore':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'audit_export_only':True
        }
    }

    if export:
        out=ROOT/'Reports'/'Backups'/'RollbackAudit'
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=out/f'Rollback_Audit_{stamp}.json'
        md_path=out/f'Rollback_Audit_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Rollback Audit Inventory','',
            f"Created: {report['created']}",
            f"Rollback reports folder: `{reports_root}`",
            f"Pre-rollback backup folder: `{pre_rollback_root}`",
            f"Restore live backup folder: `{restore_live_root}`",
            f"Filter: {q or 'none'}",
            '',
            '## Safety','',
            '- Read-only viewer.',
            '- No rollback.',
            '- No restore.',
            '- No overwrite.',
            '- No copy-back.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '',
            '## Summary','',
            f"- Actions: {summary['actions']}",
            f"- Intact: {summary['intact']}",
            f"- Attention: {summary['attention']}",
            f"- Verified: {summary['verified']}",
            f"- Rollback sources present: {summary['rollback_sources_present']}",
            f"- Rollback source hashes intact: {summary['rollback_source_hashes_intact']}",
            f"- Pre-rollback backups present: {summary['pre_rollback_backups_present']}",
            f"- Pre-rollback backup hashes intact: {summary['pre_rollback_backup_hashes_intact']}",
            f"- Targets still rolled back: {summary['targets_still_rolled_back']}",
            f"- Restore action reports present: {summary['restore_action_reports_present']}",
            f"- Repair logs present: {summary['repair_logs_present']}",
            f"- Errors: {summary['errors']}",
            f"- Latest action: `{summary['latest_action']}`",
            f"- Latest created: {summary['latest_created']}",
            '',
            '## Rollback Actions',''
        ]
        for a in actions:
            lines += [
                f"### {a.get('status','').upper()}: {a.get('name')}",
                '',
                f"- Created: {a.get('created')}",
                f"- Message: {a.get('message')}",
                f"- Original restore action: `{a.get('restore_action')}`",
                f"- Target: `{a.get('target')}`",
                f"- Rollback source backup: `{a.get('rollback_source_backup')}`",
                f"- Pre-rollback current-target backup: `{a.get('pre_rollback_current_target_backup')}`",
                f"- Verification OK: {a.get('verification_ok')}",
                f"- Verification: {a.get('verification_message')}",
                f"- Current target hash: `{a.get('target_current_hash')}`",
                f"- Target still matches rollback hash: {a.get('target_current_matches_rollback_hash')}",
                f"- Rollback source hash intact: {a.get('rollback_source_backup_hash_intact')}",
                f"- Pre-rollback backup hash intact: {a.get('pre_rollback_current_target_backup_hash_intact')}",
                f"- Rollback report: `{a.get('rollback_report_markdown') or a.get('rollback_report_json')}`",
                f"- Repair log: `{a.get('repair_action_log_markdown') or a.get('repair_action_log_json')}`",
                '',
                'Checks:'
            ]
            for c in a.get('checks',[]):
                lines.append(f"- {'PASS' if c.get('ok') else 'FAIL'} `{c.get('id')}` — {c.get('message')} {('`'+c.get('path','')+'`') if c.get('path') else ''}")
            lines += ['','Hashes:']
            h=a.get('hashes') or {}
            for key in ['target_before_rollback','pre_rollback_current_target_backup','rollback_source_backup','recorded_old_target','recorded_live_backup','target_after_rollback']:
                lines.append(f"- {key}: `{h.get(key,'')}`")
            lines.append('')
        if errors:
            lines += ['## Errors','']
            for e in errors:
                lines.append(f"- `{e.get('path')}`: {e.get('error')}")
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def recovery_timeline_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    q=(d.get('query') or d.get('filter') or '').strip().lower()
    limit=int(d.get('limit') or 1000)

    restore_audit=restore_action_audit_inventory({'limit':limit})
    rollback_audit=rollback_action_audit_inventory({'limit':limit})

    events=[]
    errors=[]

    def add_event(kind, created, target, title, status, summary, paths=None, hashes=None, checks=None, source=''):
        item={
            'kind':kind,
            'created':created or '',
            'target':target or '',
            'title':title or '',
            'status':status or '',
            'summary':summary or '',
            'paths':paths or {},
            'hashes':hashes or {},
            'checks':checks or [],
            'source':source or ''
        }
        blob=' '.join(str(v) for v in [item['kind'],item['created'],item['target'],item['title'],item['status'],item['summary'],item['source'],item['paths'],item['hashes']]).lower()
        if q and q not in blob:
            return
        events.append(item)

    # A restore action can become intentionally superseded after a verified rollback.
    # That is not a failure; it means recovery history moved forward.
    rollback_targets={}
    for rb in rollback_audit.get('actions',[]):
        if rb.get('verification_ok') and rb.get('target_current_matches_rollback_hash'):
            rollback_targets[rb.get('target','')]=rb

    # Restore actions
    for a in restore_audit.get('actions',[]):
        h=a.get('hashes') or {}
        paths={
            'target':a.get('target',''),
            'staged_copy':a.get('staged_copy',''),
            'source_backup':a.get('source_backup',''),
            'pre_restore_live_backup':a.get('pre_restore_live_backup',''),
            'restore_report':a.get('restore_report_markdown') or a.get('restore_report_json',''),
            'repair_log':a.get('repair_action_log_markdown') or a.get('repair_action_log_json','')
        }
        restore_status=a.get('status','')
        superseding_rollback=rollback_targets.get(a.get('target',''))
        if restore_status=='attention' and superseding_rollback and a.get('verification_ok') and not a.get('target_current_matches_restored_hash'):
            restore_status='superseded_by_rollback'
            summary=f"Restore action superseded by verified rollback {superseding_rollback.get('name','')}; original restore verification {a.get('verification_passed',0)}/{a.get('verification_checked',0)}; target no longer matches restored hash because rollback succeeded."
        else:
            summary=f"Restore action {restore_status or 'unknown'}; verification {a.get('verification_passed',0)}/{a.get('verification_checked',0)}; target still restored: {a.get('target_current_matches_restored_hash')}"
        add_event('restore_action',a.get('created',''),a.get('target',''),a.get('name',''),restore_status,summary,paths,h,a.get('checks',[]),'restore_audit')

        # Source/staging sub-events from restore action
        add_event('restore_source_backup',a.get('created',''),a.get('target',''),'Source backup used for restore','intact' if a.get('source_backup_exists') else 'attention',f"Source backup exists: {a.get('source_backup_exists')}",{'source_backup':a.get('source_backup','')},{'source_backup':h.get('source_backup','')},[],a.get('name',''))
        add_event('restore_staged_copy',a.get('created',''),a.get('target',''),'Staged copy used for restore','intact' if a.get('staged_copy_hash_intact') else 'attention',f"Staged copy hash intact: {a.get('staged_copy_hash_intact')}",{'staged_copy':a.get('staged_copy','')},{'staged_copy':h.get('staged_copy','')},[],a.get('name',''))
        add_event('pre_restore_live_backup',a.get('created',''),a.get('target',''),'Live target backup before restore','intact' if a.get('pre_restore_live_backup_hash_intact') else 'attention',f"Pre-restore backup hash intact: {a.get('pre_restore_live_backup_hash_intact')}",{'pre_restore_live_backup':a.get('pre_restore_live_backup','')},{'target_before':h.get('target_before',''),'live_backup':h.get('live_backup','')},[],a.get('name',''))

    # Rollback actions
    for a in rollback_audit.get('actions',[]):
        h=a.get('hashes') or {}
        paths={
            'target':a.get('target',''),
            'rollback_source_backup':a.get('rollback_source_backup',''),
            'pre_rollback_current_target_backup':a.get('pre_rollback_current_target_backup',''),
            'restore_action_report':a.get('restore_action_report',''),
            'rollback_report':a.get('rollback_report_markdown') or a.get('rollback_report_json',''),
            'repair_log':a.get('repair_action_log_markdown') or a.get('repair_action_log_json','')
        }
        summary=f"Rollback action {a.get('status','unknown')}; verification {a.get('verification_passed',0)}/{a.get('verification_checked',0)}; target still rolled back: {a.get('target_current_matches_rollback_hash')}"
        add_event('rollback_action',a.get('created',''),a.get('target',''),a.get('name',''),a.get('status',''),summary,paths,h,a.get('checks',[]),'rollback_audit')

        add_event('rollback_source_backup',a.get('created',''),a.get('target',''),'Rollback source backup','intact' if a.get('rollback_source_backup_hash_intact') else 'attention',f"Rollback source hash intact: {a.get('rollback_source_backup_hash_intact')}",{'rollback_source_backup':a.get('rollback_source_backup','')},{'rollback_source_backup':h.get('rollback_source_backup',''),'recorded_old_target':h.get('recorded_old_target','')},[],a.get('name',''))
        add_event('pre_rollback_current_target_backup',a.get('created',''),a.get('target',''),'Current target backup before rollback','intact' if a.get('pre_rollback_current_target_backup_hash_intact') else 'attention',f"Pre-rollback backup hash intact: {a.get('pre_rollback_current_target_backup_hash_intact')}",{'pre_rollback_current_target_backup':a.get('pre_rollback_current_target_backup','')},{'target_before_rollback':h.get('target_before_rollback',''),'pre_rollback_current_target_backup':h.get('pre_rollback_current_target_backup','')},[],a.get('name',''))

    # Existing preview/audit export files as timeline evidence.
    evidence_folders=[
        ('restore_preview_report',ROOT/'Reports'/'Backups'/'RestorePreviews','Restore_Preview_*.json'),
        ('restore_final_check_report',ROOT/'Reports'/'Backups'/'FinalChecklist','Restore_Final_Checklist_*.json'),
        ('restore_audit_report',ROOT/'Reports'/'Backups'/'RestoreAudit','Post_Restore_Audit_*.json'),
        ('rollback_preview_report',ROOT/'Reports'/'Backups'/'RollbackPreviews','Rollback_Preview_*.json'),
        ('rollback_audit_report',ROOT/'Reports'/'Backups'/'RollbackAudit','Rollback_Audit_*.json')
    ]
    for kind, folder, pattern in evidence_folders:
        try:
            if folder.exists():
                for p in sorted(folder.glob(pattern), key=lambda x:x.stat().st_mtime if x.exists() else 0, reverse=True)[:50]:
                    created=''
                    target=''
                    status='evidence'
                    title=p.stem
                    summary='Evidence report found.'
                    hashes={}
                    try:
                        obj=json.loads(p.read_text(encoding='utf-8',errors='replace'))
                        created=obj.get('created','')
                        target=(obj.get('summary') or {}).get('target','') or (obj.get('target') or {}).get('path','') or ''
                        status=(obj.get('summary') or {}).get('candidate_status','') or obj.get('final_status','') or 'evidence'
                        summary=f"{obj.get('title',kind)}; ok={obj.get('ok')}; read_only={obj.get('read_only')}; report_only={obj.get('report_only')}"
                        if kind=='restore_audit_report':
                            target=''
                            s=obj.get('summary') or {}
                            summary=f"Post-restore audit; actions={s.get('actions')}; intact={s.get('intact')}; attention={s.get('attention')}; errors={s.get('errors')}"
                        if kind=='rollback_audit_report':
                            target=''
                            s=obj.get('summary') or {}
                            summary=f"Rollback audit; actions={s.get('actions')}; intact={s.get('intact')}; attention={s.get('attention')}; errors={s.get('errors')}"
                    except Exception as e:
                        errors.append({'path':str(p),'error':str(e)})
                    add_event(kind,created,target,title,status,summary,{'json':str(p),'markdown':str(p.with_suffix(".md")) if p.with_suffix(".md").exists() else ''},hashes,[],str(folder))
        except Exception as e:
            errors.append({'path':str(folder),'error':str(e)})

    def sort_key(e):
        return e.get('created') or ''
    events=sorted(events,key=sort_key)
    if len(events)>limit:
        events=events[-limit:]

    # Build target chains.
    target_map={}
    for e in events:
        target=e.get('target') or 'global/evidence'
        target_map.setdefault(target,[]).append(e)

    chains=[]
    for target, evs in target_map.items():
        kinds=[e.get('kind') for e in evs]
        statuses=[e.get('status') for e in evs]
        chains.append({
            'target':target,
            'event_count':len(evs),
            'restore_actions':sum(1 for e in evs if e.get('kind')=='restore_action'),
            'rollback_actions':sum(1 for e in evs if e.get('kind')=='rollback_action'),
            'backup_events':sum(1 for e in evs if 'backup' in e.get('kind','') or 'staged' in e.get('kind','')),
            'evidence_reports':sum(1 for e in evs if e.get('kind','').endswith('_report')),
            'attention_events':sum(1 for e in evs if e.get('status')=='attention'),
            'superseded_events':sum(1 for e in evs if e.get('status')=='superseded_by_rollback'),
            'intact_events':sum(1 for e in evs if e.get('status')=='intact'),
            'latest_created':max([e.get('created','') for e in evs] or ['']),
            'kinds':kinds,
            'statuses':statuses
        })

    chains=sorted(chains,key=lambda c:c.get('latest_created',''),reverse=True)

    kind_counts={}
    status_counts={}
    for e in events:
        kind_counts[e.get('kind','unknown')]=kind_counts.get(e.get('kind','unknown'),0)+1
        status_counts[e.get('status','unknown')]=status_counts.get(e.get('status','unknown'),0)+1

    summary={
        'events':len(events),
        'targets':len(chains),
        'restore_actions':sum(1 for e in events if e.get('kind')=='restore_action'),
        'rollback_actions':sum(1 for e in events if e.get('kind')=='rollback_action'),
        'backup_events':sum(1 for e in events if 'backup' in e.get('kind','') or 'staged' in e.get('kind','')),
        'evidence_reports':sum(1 for e in events if e.get('kind','').endswith('_report')),
        'intact_events':sum(1 for e in events if e.get('status')=='intact'),
        'attention_events':sum(1 for e in events if e.get('status')=='attention'),
        'superseded_events':sum(1 for e in events if e.get('status')=='superseded_by_rollback'),
        'errors':len(errors),
        'latest_event':events[-1].get('title','') if events else '',
        'latest_created':events[-1].get('created','') if events else '',
        'restore_audit_ok':bool(restore_audit.get('ok')),
        'rollback_audit_ok':bool(rollback_audit.get('ok'))
    }

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Recovery Timeline Viewer',
        'read_only':True,
        'report_only':True,
        'filter':q,
        'summary':summary,
        'kind_counts':[{'kind':k,'count':v} for k,v in sorted(kind_counts.items())],
        'status_counts':[{'status':k,'count':v} for k,v in sorted(status_counts.items())],
        'chains':chains,
        'events':events,
        'restore_audit_summary':restore_audit.get('summary',{}),
        'rollback_audit_summary':rollback_audit.get('summary',{}),
        'errors':errors,
        'folders':{
            'restore_actions':str(ROOT/'Reports'/'Backups'/'RestoreActions'),
            'rollback_actions':str(ROOT/'Reports'/'Backups'/'RollbackActions'),
            'restore_live_backups':str(ROOT/'Backups'/'RestoreLiveTargets'),
            'rollback_live_backups':str(ROOT/'Backups'/'RollbackLiveTargets'),
            'recovery_timeline':str(ROOT/'Reports'/'Backups'/'RecoveryTimeline')
        },
        'safety':{
            'read_only_timeline':True,
            'no_restore':True,
            'no_rollback':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'timeline_export_only':True
        }
    }

    if export:
        out=ROOT/'Reports'/'Backups'/'RecoveryTimeline'
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=out/f'Recovery_Timeline_{stamp}.json'
        md_path=out/f'Recovery_Timeline_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Recovery Timeline Viewer','',
            f"Created: {report['created']}",
            f"Filter: {q or 'none'}",
            '',
            '## Safety','',
            '- Read-only timeline.',
            '- No restore.',
            '- No rollback.',
            '- No overwrite.',
            '- No copy-back.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '',
            '## Summary','',
            f"- Events: {summary['events']}",
            f"- Targets/chains: {summary['targets']}",
            f"- Restore actions: {summary['restore_actions']}",
            f"- Rollback actions: {summary['rollback_actions']}",
            f"- Backup/staging events: {summary['backup_events']}",
            f"- Evidence reports: {summary['evidence_reports']}",
            f"- Intact events: {summary['intact_events']}",
            f"- Attention events: {summary['attention_events']}",
            f"- Superseded-by-rollback events: {summary.get('superseded_events',0)}",
            f"- Errors: {summary['errors']}",
            f"- Latest event: `{summary['latest_event']}`",
            f"- Latest created: {summary['latest_created']}",
            '',
            '## Recovery Chains',''
        ]
        for c in chains:
            lines += [
                f"### {c.get('target')}",
                '',
                f"- Events: {c.get('event_count')}",
                f"- Restore actions: {c.get('restore_actions')}",
                f"- Rollback actions: {c.get('rollback_actions')}",
                f"- Backup/staging events: {c.get('backup_events')}",
                f"- Evidence reports: {c.get('evidence_reports')}",
                f"- Intact events: {c.get('intact_events')}",
                f"- Attention events: {c.get('attention_events')}",
                f"- Superseded-by-rollback events: {c.get('superseded_events',0)}",
                f"- Latest created: {c.get('latest_created')}",
                ''
            ]
        lines += ['## Timeline Events','']
        for e in events:
            lines += [
                f"### {e.get('created') or 'unknown time'} — {e.get('kind')} — {e.get('title')}",
                '',
                f"- Status: `{e.get('status')}`",
                f"- Target: `{e.get('target')}`",
                f"- Summary: {e.get('summary')}",
                f"- Source: `{e.get('source')}`",
                '',
                'Paths:'
            ]
            for k,v in (e.get('paths') or {}).items():
                lines.append(f"- {k}: `{v}`")
            if e.get('hashes'):
                lines += ['','Hashes:']
                for k,v in (e.get('hashes') or {}).items():
                    lines.append(f"- {k}: `{v}`")
            failed=[c for c in e.get('checks',[]) if not c.get('ok')]
            if failed:
                lines += ['','Failed checks:']
                for c in failed:
                    lines.append(f"- `{c.get('id')}` — {c.get('message')} `{c.get('path','')}`")
            lines.append('')
        if errors:
            lines += ['## Errors','']
            for e in errors:
                lines.append(f"- `{e.get('path')}`: {e.get('error')}")
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def recovery_dashboard_summary(d=None):
    d=d or {}
    timeline=recovery_timeline_report({'limit':int(d.get('limit') or 1000)})
    if not timeline.get('ok'):
        return {
            'ok':False,
            'message':'Recovery dashboard could not load the recovery timeline.',
            'healthy':False,
            'read_only':True,
            'report_only':True,
            'safety':{
                'read_only_dashboard':True,
                'no_restore':True,
                'no_rollback':True,
                'no_overwrite':True,
                'no_copy_back':True,
                'no_delete':True,
                'no_install':True,
                'no_model_cleanup':True
            }
        }

    s=timeline.get('summary') or {}
    restore_summary=timeline.get('restore_audit_summary') or {}
    rollback_summary=timeline.get('rollback_audit_summary') or {}

    attention=int(s.get('attention_events') or 0)
    errors=int(s.get('errors') or 0)
    restore_actions=int(s.get('restore_actions') or 0)
    rollback_actions=int(s.get('rollback_actions') or 0)
    superseded=int(s.get('superseded_events') or 0)
    intact=int(s.get('intact_events') or 0)
    current_chain='unknown'
    if rollback_actions and rollback_summary.get('targets_still_rolled_back',0):
        current_chain='rolled_back'
    elif restore_actions and restore_summary.get('targets_still_restored',0):
        current_chain='restored'
    elif restore_actions and rollback_actions:
        current_chain='recovery_chain_present'
    elif restore_actions:
        current_chain='restore_only'
    elif rollback_actions:
        current_chain='rollback_only'
    else:
        current_chain='no_recovery_actions'

    healthy=bool(
        timeline.get('ok') and
        timeline.get('read_only') and
        timeline.get('report_only') and
        errors==0 and
        attention==0 and
        (restore_actions>0 or rollback_actions>0)
    )

    if healthy and current_chain=='rolled_back':
        health_label='HEALTHY — ROLLED BACK'
    elif healthy and current_chain=='restored':
        health_label='HEALTHY — RESTORED'
    elif healthy:
        health_label='HEALTHY'
    elif errors:
        health_label='CHECK ERRORS'
    elif attention:
        health_label='CHECK ATTENTION'
    else:
        health_label='NO RECOVERY ACTIONS YET'

    latest_event=s.get('latest_event','')
    latest_created=s.get('latest_created','')

    result={
        'ok':True,
        'created':now(),
        'title':'Kayock Recovery Dashboard Summary',
        'read_only':True,
        'report_only':True,
        'healthy':healthy,
        'health_label':health_label,
        'current_chain':current_chain,
        'summary':{
            'events':s.get('events',0),
            'targets':s.get('targets',0),
            'restore_actions':restore_actions,
            'rollback_actions':rollback_actions,
            'backup_events':s.get('backup_events',0),
            'evidence_reports':s.get('evidence_reports',0),
            'intact_events':intact,
            'attention_events':attention,
            'superseded_events':superseded,
            'errors':errors,
            'latest_event':latest_event,
            'latest_created':latest_created,
            'restore_audit_ok':bool(s.get('restore_audit_ok')),
            'rollback_audit_ok':bool(s.get('rollback_audit_ok'))
        },
        'restore_audit_summary':restore_summary,
        'rollback_audit_summary':rollback_summary,
        'chains':timeline.get('chains',[]),
        'folders':timeline.get('folders',{}),
        'safety':{
            'read_only_dashboard':True,
            'no_restore':True,
            'no_rollback':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True
        }
    }
    result['message']=f"Recovery Foundation: {health_label}"
    return result



def repair_ops_dashboard_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    limit=int(d.get('limit') or 300)

    # Build a read-only view of the currently available Repair Bay actions.
    actions=[]
    def add_action(action_id,title,description,risk='low',available=True,reason='',writes=None):
        actions.append({
            'id':action_id,
            'title':title,
            'description':description,
            'risk':risk,
            'available':bool(available),
            'reason':reason,
            'writes':writes or [],
            'requires_confirmation':True,
            'safety':['Preview first','User confirmation required','Repair log created','No package installs','No model deletion']
        })

    standard_folders=[
        ROOT/'Reports'/'RepairActions',
        ROOT/'Reports'/'Models',
        ROOT/'Reports'/'PortableReadiness',
        ROOT/'Backups'/'GeneratedFiles',
        ROOT/'LegacyLaunchers',
        ROOT/'Prompts',
        ROOT/'NovelForge',
        ROOT/'NovelForge'/'Exports',
        ROOT/'Extensions',
        ROOT/'Modules',
        ROOT/'Library'
    ]
    missing=[str(p) for p in standard_folders if not p.exists()]
    add_action(
        'create_missing_standard_folders',
        'Create Missing Standard Folders',
        'Creates safe standard Kayock folders that are missing. It does not delete, move, or overwrite files.',
        'low',
        bool(missing),
        f"{len(missing)} folder(s) missing." if missing else 'No standard folders are missing.',
        missing
    )
    root_manifest=ROOT/'manifest.json'
    add_action(
        'refresh_root_manifest',
        'Refresh Root Project Manifest',
        'Regenerates Z:\\FOXAI\\manifest.json from current module and scan state. Existing manifest is backed up before overwrite.',
        'low',
        True,
        'Available. Existing file will be backed up first.' if root_manifest.exists() else 'Available. File does not exist yet.',
        [str(root_manifest)]
    )
    readme=ROOT/'Departments'/'Engineering'/'README.md'
    add_action(
        'refresh_engineering_readme',
        'Refresh Engineering README',
        'Regenerates the Engineering README from the Engineering manifest. Existing README is backed up before overwrite.',
        'low',
        (ROOT/'Departments'/'Engineering'/'manifest.json').exists(),
        'Available. Existing README will be backed up first.' if readme.exists() else 'Blocked until Engineering manifest exists.',
        [str(readme)]
    )
    dep_plan=FOLDERS.get('repair_reports',ROOT/'Reports'/'RepairActions')/'Optional_Dependency_Install_Plan.md'
    add_action(
        'generate_optional_dependency_plan',
        'Generate Optional Dependency Plan',
        'Writes a report-only plan for optional Repair Bay tools. It does not install packages.',
        'low',
        True,
        'Available. No installs will run.',
        [str(dep_plan)]
    )
    suspicious=[]
    for p in list(ROOT.glob('*.bat'))+list(ROOT.glob('*.cmd')):
        if p.name.lower().startswith('@echo off'):
            suspicious.append(str(p))
    add_action(
        'move_suspicious_root_launchers',
        'Move Suspicious Root Launchers',
        'Moves suspicious root BAT/CMD files into LegacyLaunchers with safer names. No deletion.',
        'low',
        bool(suspicious),
        f"{len(suspicious)} suspicious launcher(s) found." if suspicious else 'No suspicious root launcher filenames found.',
        suspicious
    )

    action_plan_summary={
        'actions':len(actions),
        'available':sum(1 for x in actions if x.get('available')),
        'blocked':sum(1 for x in actions if not x.get('available')),
        'low_risk':sum(1 for x in actions if x.get('risk')=='low')
    }

    history=repair_action_history({'limit':limit})
    backup_vault=backup_vault_report({'limit':limit})
    recovery=recovery_dashboard_summary({'limit':limit})

    hs=history.get('summary') or {}
    bs=backup_vault.get('summary') or {}
    rs=recovery.get('summary') or {}

    failed_actions=int(hs.get('failed') or 0)
    verification_failed=int(hs.get('verification_failed') or 0)
    history_errors=int(hs.get('errors') or 0)
    backup_errors=int(bs.get('scan_errors') or 0) + int(bs.get('log_errors') or 0)
    recovery_errors=int(rs.get('errors') or 0)
    recovery_attention=int(rs.get('attention_events') or 0)

    legacy_logs=int(hs.get('verification_not_recorded') or 0)
    healthy=bool(
        history.get('ok') and
        backup_vault.get('ok') and
        recovery.get('ok') and
        failed_actions==0 and
        verification_failed==0 and
        history_errors==0 and
        backup_errors==0 and
        recovery_errors==0 and
        recovery_attention==0
    )

    if healthy:
        health_label='REPAIR SHOP HEALTHY'
    elif verification_failed:
        health_label='VERIFY FAILED — CHECK REPAIR LOGS'
    elif failed_actions:
        health_label='ACTION FAILURE — CHECK REPAIR LOGS'
    elif backup_errors:
        health_label='BACKUP VAULT WARNING'
    elif recovery_errors or recovery_attention:
        health_label='RECOVERY WARNING'
    else:
        health_label='CHECK REPAIR SHOP'

    recent_logs=(history.get('logs') or [])[:12]
    by_action=history.get('by_action') or []
    latest_log=recent_logs[0] if recent_logs else {}

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Repair Shop Operations Dashboard',
        'read_only':True,
        'report_only':True,
        'healthy':healthy,
        'health_label':health_label,
        'summary':{
            'repair_logs':int(hs.get('logs') or 0),
            'repair_ok':int(hs.get('ok') or 0),
            'repair_failed':failed_actions,
            'user_approved':int(hs.get('user_approved') or 0),
            'dry_runs':int(hs.get('dry_runs') or 0),
            'action_types':int(hs.get('actions') or 0),
            'verification_passed':int(hs.get('verification_passed') or 0),
            'verification_failed':verification_failed,
            'legacy_logs_without_verification':legacy_logs,
            'history_errors':history_errors,
            'available_actions':action_plan_summary['available'],
            'blocked_actions':action_plan_summary['blocked'],
            'low_risk_actions':action_plan_summary['low_risk'],
            'generated_backups':int(bs.get('backups') or 0),
            'associated_backups':int(bs.get('associated') or 0),
            'verified_backups':int(bs.get('verified') or 0),
            'unassociated_backups':int(bs.get('unassociated') or 0),
            'backup_errors':backup_errors,
            'recovery_health':recovery.get('health_label',''),
            'recovery_chain':recovery.get('current_chain',''),
            'recovery_attention':recovery_attention,
            'recovery_errors':recovery_errors,
            'latest_action':hs.get('last_action',''),
            'latest_action_created':hs.get('last_created',''),
            'latest_backup':bs.get('latest_backup',''),
            'latest_recovery_event':rs.get('latest_event',''),
            'latest_recovery_created':rs.get('latest_created','')
        },
        'action_plan_summary':action_plan_summary,
        'safe_actions':actions,
        'history_summary':hs,
        'history_by_action':by_action,
        'recent_logs':recent_logs,
        'backup_summary':bs,
        'backup_by_type':backup_vault.get('by_type',[]),
        'backup_by_action':backup_vault.get('by_action',[]),
        'recovery_summary':recovery.get('summary',{}),
        'recovery_health_label':recovery.get('health_label',''),
        'recovery_current_chain':recovery.get('current_chain',''),
        'latest_log':latest_log,
        'folders':{
            'repair_reports':str(FOLDERS.get('repair_reports',ROOT/'Reports'/'RepairActions')),
            'repair_ops_dashboard':str(FOLDERS.get('repair_ops_dashboard',ROOT/'Reports'/'RepairActions'/'OperationsDashboard')),
            'generated_backups':str(FOLDERS.get('file_backups',ROOT/'Backups'/'GeneratedFiles')),
            'recovery_timeline':str(FOLDERS.get('recovery_timeline',ROOT/'Reports'/'Backups'/'RecoveryTimeline'))
        },
        'safety':{
            'read_only_dashboard':True,
            'no_repair_action':True,
            'no_restore':True,
            'no_rollback':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'dashboard_export_only':True
        }
    }

    report['message']=f"Repair Shop Operations: {health_label}"

    if export:
        out=FOLDERS.get('repair_ops_dashboard',ROOT/'Reports'/'RepairActions'/'OperationsDashboard')
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=out/f'Repair_Shop_Operations_{stamp}.json'
        md_path=out/f'Repair_Shop_Operations_{stamp}.md'
        jwrite(json_path,report)
        s=report['summary']
        lines=[
            '# Kayock Repair Shop Operations Dashboard','',
            f"Created: {report['created']}",
            f"Health: **{health_label}**",
            f"Read only: {report['read_only']}",
            f"Report only: {report['report_only']}",
            '',
            '## Safety','',
            '- Read-only operations dashboard.',
            '- No repair action.',
            '- No restore.',
            '- No rollback.',
            '- No overwrite.',
            '- No copy-back.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '',
            '## Summary','',
            f"- Repair logs: {s['repair_logs']}",
            f"- Repair OK: {s['repair_ok']}",
            f"- Repair failed: {s['repair_failed']}",
            f"- User-approved actions: {s['user_approved']}",
            f"- Verification passed: {s['verification_passed']}",
            f"- Verification failed: {s['verification_failed']}",
            f"- Legacy logs without verification: {s['legacy_logs_without_verification']}",
            f"- Available safe actions: {s['available_actions']}",
            f"- Blocked safe actions: {s['blocked_actions']}",
            f"- Generated backups: {s['generated_backups']}",
            f"- Associated backups: {s['associated_backups']}",
            f"- Verified backups: {s['verified_backups']}",
            f"- Backup errors: {s['backup_errors']}",
            f"- Recovery health: {s['recovery_health']}",
            f"- Recovery chain: {s['recovery_chain']}",
            f"- Recovery attention: {s['recovery_attention']}",
            f"- Recovery errors: {s['recovery_errors']}",
            f"- Latest action: `{s['latest_action']}`",
            f"- Latest action created: {s['latest_action_created']}",
            f"- Latest backup: `{s['latest_backup']}`",
            f"- Latest recovery event: `{s['latest_recovery_event']}`",
            '',
            '## Safe Actions',''
        ]
        for a in actions:
            lines += [
                f"### {'AVAILABLE' if a.get('available') else 'BLOCKED'}: {a.get('title')}",
                '',
                f"- ID: `{a.get('id')}`",
                f"- Risk: `{a.get('risk')}`",
                f"- Reason: {a.get('reason','')}",
                f"- Writes: {', '.join('`'+w+'`' for w in (a.get('writes') or [])) if a.get('writes') else 'none'}",
                ''
            ]
        lines += ['## Action Types','']
        for a in by_action:
            lines.append(f"- `{a.get('action_id')}` — count {a.get('count')}, ok {a.get('ok')}, failed {a.get('failed')}, verified {a.get('verified')}, older logs {a.get('not_recorded')}")
        lines += ['','## Recent Logs','']
        for l in recent_logs:
            lines += [
                f"### {l.get('created')} — {l.get('action_id')}",
                '',
                f"- OK: {l.get('ok')}",
                f"- Verified state: {l.get('verified_state')}",
                f"- Message: {l.get('message')}",
                f"- Target: `{l.get('target')}`",
                f"- Backup: `{l.get('backup')}`",
                f"- Log: `{l.get('markdown') or l.get('path')}`",
                ''
            ]
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def repair_action_detail_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    needle=(d.get('path') or d.get('log_path') or d.get('query') or d.get('filter') or '').strip()
    nlow=needle.lower()
    hist=repair_action_history({'limit':1000})
    if not hist.get('ok'):
        return {'ok':False,'message':'Could not load RepairActions history.','read_only':True,'report_only':True,'history':hist}
    logs=hist.get('logs') or []
    chosen=None
    if nlow:
        for l in logs:
            blob=' '.join(str(l.get(k,'')) for k in ['path','markdown','action_id','created','message','target','backup']).lower()
            if nlow in blob:
                chosen=l; break
    if not chosen and logs:
        chosen=logs[0]
    if not chosen:
        return {'ok':False,'message':'No RepairActions log found.','read_only':True,'report_only':True}
    log_path=Path(chosen.get('path',''))
    if not log_path.exists():
        return {'ok':False,'message':'Selected RepairActions JSON log is missing.','read_only':True,'report_only':True,'path':str(log_path)}
    try:
        payload=json.loads(log_path.read_text(encoding='utf-8',errors='replace'))
    except Exception as e:
        return {'ok':False,'message':f'Could not parse selected RepairActions log: {e}','read_only':True,'report_only':True,'path':str(log_path)}

    result=payload.get('result') or chosen.get('result') or {}
    verification=payload.get('verification') or chosen.get('verification') or result.get('verification') or {}
    checks=verification.get('checks') or []
    action_id=payload.get('action_id') or chosen.get('action_id') or result.get('action_id') or 'unknown'
    md_path=Path(chosen.get('markdown') or str(log_path.with_suffix('.md')))
    target_raw=payload.get('target') or chosen.get('target') or result.get('target') or ''
    backup_raw=payload.get('backup') or chosen.get('backup') or result.get('backup') or ''

    def info(raw):
        out={'path':raw or '', 'exists':False, 'is_file':False, 'inside_root':False, 'size':None, 'modified':'', 'sha256':'', 'error':''}
        if not raw: return out
        try:
            p=Path(raw); out['exists']=p.exists(); out['is_file']=p.exists() and p.is_file()
            rr=ROOT.resolve(); pr=p.resolve(); out['inside_root']=(pr==rr or rr in pr.parents)
            if out['is_file']:
                st=p.stat(); out['size']=st.st_size; out['modified']=datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds'); out['sha256']=_sha256_file(p)
        except Exception as e:
            out['error']=str(e)
        return out

    target=info(target_raw); backup=info(backup_raw)
    verified_state=chosen.get('verified_state') or ('passed' if verification.get('ok') else ('failed' if verification and not verification.get('ok') else 'not_recorded'))
    failed=[c for c in checks if not c.get('ok')]
    passed=[c for c in checks if c.get('ok')]
    action_ok=bool(payload.get('ok',chosen.get('ok')))
    if verified_state=='passed': status='verified'
    elif verified_state=='not_recorded' and action_ok: status='legacy_ok'
    elif verified_state=='failed' or not action_ok: status='failed'
    else: status='attention'

    related=[]
    seen=set()
    for key in ['stage_dir','restore_report','rollback_report','restore_action_report','rollback_source_backup','staged_copy','backup','target']:
        val=result.get(key) or payload.get(key) or ''
        if not val or val in seen: continue
        seen.add(val)
        try:
            p=Path(val); exists=p.exists(); kind='folder' if p.is_dir() else ('file' if p.is_file() else 'path')
        except Exception:
            exists=False; kind='path'
        related.append({'key':key,'path':val,'exists':exists,'kind':kind})
    for c in checks:
        val=c.get('path','')
        if val and val not in seen:
            seen.add(val)
            try:
                p=Path(val); exists=p.exists(); kind='folder' if p.is_dir() else ('file' if p.is_file() else 'path')
            except Exception:
                exists=False; kind='path'
            related.append({'key':'check_'+str(c.get('id','path')),'path':val,'exists':exists,'kind':kind})

    detail_checks=[
        {'id':'action_log_json_exists','ok':log_path.exists(),'message':'RepairActions JSON log exists.','path':str(log_path)},
        {'id':'action_log_json_parsed','ok':True,'message':'RepairActions JSON log parsed successfully.','path':str(log_path)},
        {'id':'action_log_markdown_exists','ok':md_path.exists(),'message':'RepairActions Markdown log exists.','path':str(md_path)},
        {'id':'action_reported_ok','ok':action_ok,'message':'Action reported OK.','path':''},
        {'id':'user_approved_action','ok':bool(payload.get('user_approved_action',chosen.get('user_approved_action'))),'message':'Action was user-approved.','path':''},
        {'id':'verification_passed_or_legacy','ok':verified_state in ['passed','not_recorded'],'message':'Verification passed or this is an older successful legacy log.','path':''},
        {'id':'target_inside_root_or_empty','ok':(not target_raw or target.get('inside_root')),'message':'Target path is empty or inside FOXAI root.','path':target_raw},
        {'id':'backup_inside_root_or_empty','ok':(not backup_raw or backup.get('inside_root')),'message':'Backup path is empty or inside FOXAI root.','path':backup_raw},
        {'id':'no_detail_side_effects','ok':True,'message':'Detail viewer performed read-only inspection only.','path':''}
    ]

    report={'ok':True,'created':now(),'title':'Kayock Repair Action Detail Viewer','read_only':True,'report_only':True,'status':status,
        'action_id':action_id,'action_created':payload.get('created') or chosen.get('created',''),'action_ok':action_ok,
        'dry_run':bool(payload.get('dry_run',chosen.get('dry_run'))),'user_approved_action':bool(payload.get('user_approved_action',chosen.get('user_approved_action'))),
        'verified_state':verified_state,'message':payload.get('message') or chosen.get('message') or result.get('message',''),
        'log':{'json':str(log_path),'markdown':str(md_path),'json_exists':log_path.exists(),'markdown_exists':md_path.exists(),'size':log_path.stat().st_size if log_path.exists() else None},
        'target':target,'backup':backup,
        'verification':{'recorded':bool(verification),'ok':bool(verification.get('ok')) if verification else False,'state':verified_state,'checked':verification.get('checked',len(checks)) if verification else 0,'passed':verification.get('passed',len(passed)) if verification else 0,'failed':verification.get('failed',len(failed)) if verification else 0,'message':verification.get('message','No verification was recorded for this legacy log.') if verification else 'No verification was recorded for this legacy log.','checks':checks,'failed_checks':failed},
        'detail_checks':detail_checks,'detail_ok':all(c.get('ok') for c in detail_checks),'related_paths':related,'raw_result':result,
        'safety':{'read_only_detail_viewer':True,'no_repair_action':True,'no_restore':True,'no_rollback':True,'no_overwrite':True,'no_copy_back':True,'no_delete':True,'no_install':True,'no_model_cleanup':True,'detail_export_only':True}}
    if export:
        out=FOLDERS.get('repair_action_details',ROOT/'Reports'/'RepairActions'/'ActionDetails'); out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S'); safe=slug(action_id)[:60]
        jp=out/f'Repair_Action_Detail_{safe}_{stamp}.json'; mp=out/f'Repair_Action_Detail_{safe}_{stamp}.md'
        jwrite(jp,report)
        lines=['# Kayock Repair Action Detail Viewer','',f"Created: {report['created']}",f"Status: **{status}**",f"Action ID: `{action_id}`",f"Action created: {report['action_created']}",f"Action OK: {action_ok}",f"Verified state: `{verified_state}`",f"Message: {report['message']}",'','## Safety','','- Read-only detail viewer.','- No repair action.','- No restore.','- No rollback.','- No overwrite.','- No copy-back.','- No delete.','- No install.','- No model cleanup.','','## Log','',f"- JSON: `{log_path}`",f"- Markdown: `{md_path}`",'','## Target','',f"- Path: `{target.get('path','')}`",f"- Exists: {target.get('exists')}",f"- Inside root: {target.get('inside_root')}",f"- Size: {target.get('size')}",f"- Modified: {target.get('modified')}",f"- SHA256: `{target.get('sha256','')}`",'','## Backup','',f"- Path: `{backup.get('path','')}`",f"- Exists: {backup.get('exists')}",f"- Inside root: {backup.get('inside_root')}",f"- Size: {backup.get('size')}",f"- Modified: {backup.get('modified')}",f"- SHA256: `{backup.get('sha256','')}`",'','## Verification','',f"- Recorded: {report['verification']['recorded']}",f"- OK: {report['verification']['ok']}",f"- Checked: {report['verification']['checked']}",f"- Passed: {report['verification']['passed']}",f"- Failed: {report['verification']['failed']}",f"- Message: {report['verification']['message']}",'']
        for c in checks: lines.append(f"- {'PASS' if c.get('ok') else 'FAIL'} `{c.get('id')}` — {c.get('message')} {('`'+c.get('path','')+'`') if c.get('path') else ''}")
        lines += ['','## Detail Checks','']
        for c in detail_checks: lines.append(f"- {'PASS' if c.get('ok') else 'FAIL'} `{c.get('id')}` — {c.get('message')} {('`'+c.get('path','')+'`') if c.get('path') else ''}")
        lines += ['','## Related Paths','']
        for r in related: lines.append(f"- `{r.get('key')}` — {r.get('kind')} — exists={r.get('exists')} — `{r.get('path')}`")
        mp.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(jp),'markdown':str(mp),'folder':str(out)}
    return report


def verified_action_dashboard_card(d=None):
    d=d or {}
    ops=repair_ops_dashboard_report({'limit':int(d.get('limit') or 300)})
    if not ops.get('ok'):
        return {'ok':False,'message':'Verified Action dashboard could not load Repair Shop operations.','read_only':True,'report_only':True,'healthy':False,'safety':{'read_only_card':True,'no_repair_action':True,'no_restore':True,'no_rollback':True,'no_overwrite':True,'no_copy_back':True,'no_delete':True,'no_install':True,'no_model_cleanup':True}}
    s=ops.get('summary') or {}
    latest=ops.get('latest_log') or {}
    healthy=bool(ops.get('healthy') and int(s.get('repair_failed') or 0)==0 and int(s.get('verification_failed') or 0)==0 and int(s.get('history_errors') or 0)==0 and int(s.get('backup_errors') or 0)==0 and int(s.get('recovery_errors') or 0)==0 and int(s.get('recovery_attention') or 0)==0)
    if healthy:
        health_label='REPAIR SHOP HEALTHY'
    elif int(s.get('verification_failed') or 0):
        health_label='VERIFY FAILED'
    elif int(s.get('repair_failed') or 0):
        health_label='REPAIR FAILURE'
    else:
        health_label='CHECK REPAIR SHOP'
    return {
        'ok':True,'created':now(),'title':'Kayock Verified Action Dashboard Card','read_only':True,'report_only':True,'healthy':healthy,'health_label':health_label,'message':f'Verified Actions: {health_label}',
        'latest_action':{'action_id':latest.get('action_id',''),'created':latest.get('created',''),'ok':latest.get('ok'),'verified_state':latest.get('verified_state',''),'message':latest.get('message',''),'target':latest.get('target',''),'backup':latest.get('backup',''),'log_json':latest.get('path',''),'log_markdown':latest.get('markdown','')},
        'summary':{'repair_logs':s.get('repair_logs',0),'repair_ok':s.get('repair_ok',0),'repair_failed':s.get('repair_failed',0),'verification_passed':s.get('verification_passed',0),'verification_failed':s.get('verification_failed',0),'legacy_logs_without_verification':s.get('legacy_logs_without_verification',0),'safe_actions_available':s.get('available_actions',0),'safe_actions_blocked':s.get('blocked_actions',0),'generated_backups':s.get('generated_backups',0),'backup_errors':s.get('backup_errors',0),'recovery_health':s.get('recovery_health',''),'recovery_chain':s.get('recovery_chain',''),'recovery_attention':s.get('recovery_attention',0),'recovery_errors':s.get('recovery_errors',0),'latest_backup':s.get('latest_backup',''),'latest_recovery_event':s.get('latest_recovery_event','')},
        'safe_action_summary':ops.get('action_plan_summary',{}),'action_types':ops.get('history_by_action',[]),
        'safety':{'read_only_card':True,'no_repair_action':True,'no_restore':True,'no_rollback':True,'no_overwrite':True,'no_copy_back':True,'no_delete':True,'no_install':True,'no_model_cleanup':True}
    }


def repair_ticket_queue_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    limit=int(d.get('limit') or 500)
    include_healthy=bool(d.get('include_healthy',True))
    tickets=[]
    errors=[]

    severity_order={'critical':0,'high':1,'medium':2,'low':3,'info':4,'healthy':5}

    def add_ticket(ticket_id,title,source,severity='info',status='informational',summary='',evidence=None,suggested_action='',safe_action_id='',risk='low',details=None):
        evidence=evidence or []
        details=details or {}
        tickets.append({
            'id':ticket_id,
            'title':title,
            'source':source,
            'severity':severity,
            'status':status,
            'summary':summary,
            'evidence':evidence,
            'suggested_action':suggested_action,
            'safe_action_id':safe_action_id,
            'risk':risk,
            'details':details,
            'read_only':True
        })

    def call_report(label, fn, arg=None):
        try:
            return fn(arg or {})
        except Exception as e:
            errors.append({'source':label,'error':str(e)})
            add_ticket(f'{slug(label)}_report_error',f'{label} report could not run',label,'medium','open',str(e),[], 'Inspect the source report manually before any action.', '', 'medium')
            return {'ok':False,'message':str(e)}

    build=call_report('Build Verify',build_verification_lite,{'export':False})
    env=call_report('Env Verify',env_dependency_verification,{'export':False})
    portable=call_report('Portable Ready',portable_readiness_report,{'export':False})
    models=call_report('Model Check',model_duplicate_truth_report,{'export':False})
    repair=call_report('Repair Shop',repair_ops_dashboard_report,{'limit':limit})
    recovery=call_report('Recovery Foundation',recovery_dashboard_summary,{'limit':limit})
    backup=call_report('Backup Vault',backup_vault_report,{'limit':limit})

    # Build Verify tickets
    bs=build.get('summary') or {}
    if build.get('ok'):
        problems=int(bs.get('problems') or 0)
        if problems:
            add_ticket('build_verify_problems','Build verification found problems','Build Verify','high','open',f'{problems} build verification problem(s) found.',[f"Checks: {bs.get('checks',0)}",f"Passed: {bs.get('passed',0)}"],'Open Build Verify and inspect failed checks before changing files.','', 'medium', {'summary':bs})
        elif include_healthy:
            add_ticket('build_verify_clear','Build verification clear','Build Verify','healthy','clear','Build verification currently reports no problems.',[f"Checks: {bs.get('checks',0)}",f"Passed: {bs.get('passed',0)}"],'No action needed.','', 'low', {'summary':bs})

    # Environment tickets
    es=env.get('summary') or {}
    if env.get('ok'):
        problems=int(es.get('problems') or 0)
        opt_total=int(es.get('optional_tools_total') or 0)
        opt_avail=int(es.get('optional_tools_available') or 0)
        if problems:
            add_ticket('env_required_problems','Required environment problem detected','Env Verify','high','open',f'{problems} required environment problem(s) found.',[f"Python runtime: {es.get('python_runtime','')}",f"Problems: {problems}"],'Open Env Verify and inspect required failures before any repair action.','', 'medium', {'summary':es})
        elif include_healthy:
            add_ticket('env_required_clear','Required environment checks clear','Env Verify','healthy','clear','Required environment checks currently report no problems.',[f"Checks: {es.get('checks',0)}",f"Passed: {es.get('passed',0)}"],'No required action needed.','', 'low', {'summary':es})
        if opt_total and opt_avail < opt_total:
            missing=opt_total-opt_avail
            add_ticket('optional_repair_tools_missing','Optional Repair Bay tools are not fully installed','Env Verify','low','available_action',f'{missing} optional Repair Bay tool(s) appear missing. This is not a blocker.',[f"Optional tools available: {opt_avail}/{opt_total}", 'Optional tools are advisory only.'],'Generate the optional dependency plan; do not auto-install packages.','generate_optional_dependency_plan','low',{'summary':es})

    # Portable Readiness tickets
    ps=portable.get('summary') or {}
    if portable.get('ok'):
        blockers=int(ps.get('blockers') or 0)
        warnings=int(ps.get('warnings') or 0)
        score=ps.get('score',ps.get('readiness_score',''))
        if blockers:
            add_ticket('portable_blockers','Portable readiness blockers found','Portable Ready','critical','open',f'{blockers} portability blocker(s) found.',[f"Score: {score}",f"Warnings: {warnings}"],'Open Portable Ready and resolve blockers before moving the drive.','', 'high', {'summary':ps})
        elif warnings:
            add_ticket('portable_warnings','Portable readiness warnings found','Portable Ready','medium','open',f'{warnings} portability warning(s) found.',[f"Score: {score}",f"Blockers: {blockers}"],'Open Portable Ready and inspect warnings.','', 'medium', {'summary':ps})
        elif include_healthy:
            add_ticket('portable_ready_clear','Portable readiness clear','Portable Ready','healthy','clear','Portable readiness currently reports no blockers or warnings.',[f"Score: {score}",f"Blockers: {blockers}",f"Warnings: {warnings}"],'No action needed.','', 'low', {'summary':ps})

    # Model tickets
    ms=models.get('summary') or {}
    if models.get('ok'):
        dup_groups=int(ms.get('true_duplicate_groups') or ms.get('duplicate_groups') or 0)
        dup_copies=int(ms.get('true_duplicate_copies') or ms.get('duplicate_copies') or 0)
        dup_space=ms.get('duplicate_space') or ms.get('duplicate_bytes') or 0
        if dup_groups or dup_copies:
            add_ticket('model_true_duplicates','True model duplicates detected','Model Check','medium','open',f'{dup_groups} duplicate model group(s), {dup_copies} duplicate copy/copies detected.',[f"Duplicate space: {dup_space}", 'No deletion should run automatically.'],'Review Model Check before any manual cleanup. No automatic deletion.','', 'medium', {'summary':ms})
        elif include_healthy:
            add_ticket('model_duplicates_clear','No true model duplicates detected','Model Check','healthy','clear','Model Check currently reports no true duplicate GGUF model files.',[f"Physical model files: {ms.get('physical_model_files',ms.get('physical_files',''))}",f"Unique model keys: {ms.get('unique_model_keys','')}"] ,'No action needed.','', 'low', {'summary':ms})

    # Repair operations tickets
    rs=repair.get('summary') or {}
    if repair.get('ok'):
        failed=int(rs.get('repair_failed') or 0)
        verify_failed=int(rs.get('verification_failed') or 0)
        legacy=int(rs.get('legacy_logs_without_verification') or 0)
        available=int(rs.get('available_actions') or 0)
        blocked=int(rs.get('blocked_actions') or 0)
        if failed:
            add_ticket('repair_actions_failed','RepairActions failures detected','Repair Shop','high','open',f'{failed} RepairActions failure(s) found.',[f"Repair logs: {rs.get('repair_logs',0)}",f"Latest action: {rs.get('latest_action','')}"] ,'Open Repair Shop and inspect failed logs.','', 'high', {'summary':rs})
        if verify_failed:
            add_ticket('repair_verification_failed','Repair verification failure detected','Repair Shop','high','open',f'{verify_failed} verification failure(s) found.',[f"Verification passed: {rs.get('verification_passed',0)}",f"Latest action: {rs.get('latest_action','')}"] ,'Open Action Detail for the failed verification.','', 'high', {'summary':rs})
        if legacy:
            add_ticket('legacy_repair_logs','Legacy RepairActions logs without verification','Repair History','info','informational',f'{legacy} older successful log(s) predate verified-action logging.',[f"Repair logs: {rs.get('repair_logs',0)}", 'These are historical, not failures.'],'Leave as historical unless a later migration tool is built.','', 'low', {'summary':rs})
        if available:
            add_ticket('safe_actions_available','Safe Repair Shop actions are available','Repair Shop','low','available_action',f'{available} safe action(s) are currently available.',[f"Blocked actions: {blocked}", 'All listed actions still require explicit approval.'],'Use Repair Actions page only when you intentionally want to run one.','', 'low', {'safe_actions':repair.get('safe_actions',[])})
        elif include_healthy:
            add_ticket('no_safe_actions_needed','No safe Repair Shop actions currently needed','Repair Shop','healthy','clear','No safe action is currently available because nothing in that category needs fixing.',[f"Blocked actions: {blocked}"],'No action needed.','', 'low', {'summary':rs})

    # Backup tickets
    bvs=backup.get('summary') or {}
    if backup.get('ok'):
        scan_errors=int(bvs.get('scan_errors') or 0)
        log_errors=int(bvs.get('log_errors') or 0)
        unassoc=int(bvs.get('unassociated') or 0)
        verified=int(bvs.get('verified') or 0)
        if scan_errors or log_errors:
            add_ticket('backup_vault_errors','Backup Vault has scan/log errors','Backup Vault','medium','open',f'{scan_errors} scan error(s), {log_errors} log error(s).',[f"Backups: {bvs.get('backups',0)}"] ,'Open Backup Vault and inspect errors.','', 'medium', {'summary':bvs})
        if unassoc:
            add_ticket('unassociated_backups','Unassociated backup files exist','Backup Vault','info','informational',f'{unassoc} backup file(s) are not linked to a verified action log.',[f"Backups: {bvs.get('backups',0)}",f"Verified backups: {verified}"] ,'Leave as historical unless later cleanup/migration is built.','', 'low', {'summary':bvs})
        elif include_healthy:
            add_ticket('backup_vault_clear','Backup Vault has no unassociated backups','Backup Vault','healthy','clear','Backup Vault currently has no unassociated backup files.',[f"Backups: {bvs.get('backups',0)}",f"Verified backups: {verified}"] ,'No action needed.','', 'low', {'summary':bvs})

    # Recovery tickets
    rcs=recovery.get('summary') or {}
    if recovery.get('ok'):
        att=int(rcs.get('attention_events') or 0)
        errs=int(rcs.get('errors') or 0)
        if errs or att:
            add_ticket('recovery_attention','Recovery Foundation needs attention','Recovery Foundation','high','open',f'{att} attention event(s), {errs} error(s).',[f"Recovery health: {recovery.get('health_label','')}",f"Current chain: {recovery.get('current_chain','')}"] ,'Open Recovery Timeline and Recovery Dashboard.','', 'high', {'summary':rcs})
        elif include_healthy:
            add_ticket('recovery_clear','Recovery Foundation healthy','Recovery Foundation','healthy','clear',f"Recovery Foundation reports {recovery.get('health_label','healthy')}.",[f"Current chain: {recovery.get('current_chain','')}",f"Events: {rcs.get('events',0)}"] ,'No action needed.','', 'low', {'summary':rcs})

    # Latest Scan Bridge report ticket (best-effort)
    try:
        scan_dir=FOLDERS.get('scan_reports',ROOT/'Reports'/'Scans')
        scan_files=sorted(scan_dir.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True) if scan_dir.exists() else []
        if scan_files:
            sf=scan_files[0]
            sp=jread(sf,{})
            ss=sp.get('summary') or sp.get('stats') or {}
            problems=int(ss.get('problems') or ss.get('errors') or ss.get('findings') or 0)
            warnings=int(ss.get('warnings') or 0)
            files=ss.get('files') or ss.get('files_scanned') or ss.get('scanned_files') or ''
            if problems:
                add_ticket('latest_scan_findings','Latest Scan Bridge report has findings','Scan Bridge','medium','open',f'Latest scan report contains {problems} finding(s).',[f"Report: {sf}",f"Files: {files}",f"Warnings: {warnings}"] ,'Open Scan Bridge report reader and inspect findings.','', 'medium', {'summary':ss,'report':str(sf)})
            else:
                add_ticket('latest_scan_clear','Latest Scan Bridge report has no parsed problems','Scan Bridge','healthy','clear','Latest scan report did not expose parsed problems in its summary.',[f"Report: {sf}",f"Files: {files}",f"Warnings: {warnings}"] ,'No action needed from ticket queue.','', 'low', {'summary':ss,'report':str(sf)})
        else:
            add_ticket('no_scan_reports','No Scan Bridge reports found yet','Scan Bridge','info','informational','No exported Scan Bridge JSON reports were found.',[],'Run a folder scan when you want Repair Shop tickets to include scan evidence.','', 'low')
    except Exception as e:
        errors.append({'source':'Scan Bridge','error':str(e)})
        add_ticket('scan_bridge_read_error','Could not inspect Scan Bridge reports','Scan Bridge','low','open',str(e),[], 'Open Scan Bridge manually.', '', 'low')

    tickets=sorted(tickets,key=lambda x:(severity_order.get(x.get('severity','info'),9), x.get('source',''), x.get('title','')))
    active=[t for t in tickets if t.get('severity') not in ['healthy'] and t.get('status')!='clear']
    actionable=[t for t in tickets if t.get('status')=='available_action']
    open_t=[t for t in tickets if t.get('status')=='open']
    informational=[t for t in tickets if t.get('status')=='informational']
    healthy_t=[t for t in tickets if t.get('severity')=='healthy' or t.get('status')=='clear']
    high_or_worse=[t for t in active if t.get('severity') in ['critical','high']]
    medium=[t for t in active if t.get('severity')=='medium']
    low=[t for t in active if t.get('severity')=='low']

    if errors or high_or_worse:
        health_label='REPAIR TICKETS NEED ATTENTION'
        healthy=False
    elif medium:
        health_label='REPAIR TICKETS HAVE WARNINGS'
        healthy=False
    else:
        health_label='REPAIR TICKET QUEUE HEALTHY'
        healthy=True

    summary={
        'tickets':len(tickets),
        'active_tickets':len(active),
        'open_tickets':len(open_t),
        'available_action_tickets':len(actionable),
        'informational_tickets':len(informational),
        'healthy_tickets':len(healthy_t),
        'critical':sum(1 for t in tickets if t.get('severity')=='critical'),
        'high':sum(1 for t in tickets if t.get('severity')=='high'),
        'medium':sum(1 for t in tickets if t.get('severity')=='medium'),
        'low':sum(1 for t in tickets if t.get('severity')=='low'),
        'info':sum(1 for t in tickets if t.get('severity')=='info'),
        'healthy':sum(1 for t in tickets if t.get('severity')=='healthy'),
        'errors':len(errors),
        'repair_shop_health':repair.get('health_label',''),
        'recovery_health':recovery.get('health_label',''),
        'latest_repair_action':(repair.get('summary') or {}).get('latest_action',''),
        'latest_recovery_event':(recovery.get('summary') or {}).get('latest_event','')
    }

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Repair Ticket Queue',
        'read_only':True,
        'report_only':True,
        'healthy':healthy,
        'health_label':health_label,
        'summary':summary,
        'tickets':tickets,
        'active_tickets':active,
        'available_action_tickets':actionable,
        'open_tickets':open_t,
        'informational_tickets':informational,
        'healthy_tickets':healthy_t,
        'sources':{
            'build_verify_ok':bool(build.get('ok')),
            'env_verify_ok':bool(env.get('ok')),
            'portable_ready_ok':bool(portable.get('ok')),
            'model_check_ok':bool(models.get('ok')),
            'repair_shop_ok':bool(repair.get('ok')),
            'backup_vault_ok':bool(backup.get('ok')),
            'recovery_foundation_ok':bool(recovery.get('ok'))
        },
        'errors':errors,
        'folders':{
            'repair_tickets':str(FOLDERS.get('repair_tickets',ROOT/'Reports'/'RepairActions'/'Tickets')),
            'repair_reports':str(FOLDERS.get('repair_reports',ROOT/'Reports'/'RepairActions')),
            'scan_reports':str(FOLDERS.get('scan_reports',ROOT/'Reports'/'Scans')),
            'recovery_timeline':str(FOLDERS.get('recovery_timeline',ROOT/'Reports'/'Backups'/'RecoveryTimeline'))
        },
        'safety':{
            'read_only_ticket_queue':True,
            'no_repair_action':True,
            'no_restore':True,
            'no_rollback':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'ticket_export_only':True
        },
        'message':f'Repair Ticket Queue: {health_label}'
    }

    if export:
        out=FOLDERS.get('repair_tickets',ROOT/'Reports'/'RepairActions'/'Tickets')
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        jp=out/f'Repair_Ticket_Queue_{stamp}.json'
        mp=out/f'Repair_Ticket_Queue_{stamp}.md'
        jwrite(jp,report)
        lines=['# Kayock Repair Ticket Queue','',f"Created: {report['created']}",f"Health: **{health_label}**",f"Read only: {report['read_only']}",f"Report only: {report['report_only']}",'','## Safety','','- Read-only ticket queue.','- No repair action.','- No restore.','- No rollback.','- No overwrite.','- No copy-back.','- No delete.','- No install.','- No model cleanup.','','## Summary','']
        for k,v in summary.items():
            lines.append(f"- {k}: {v}")
        lines += ['','## Tickets','']
        for t in tickets:
            lines += [
                f"### [{t.get('severity').upper()} / {t.get('status')}] {t.get('title')}",'',
                f"- ID: `{t.get('id')}`",
                f"- Source: {t.get('source')}",
                f"- Risk: `{t.get('risk')}`",
                f"- Summary: {t.get('summary')}",
                f"- Suggested action: {t.get('suggested_action') or 'None'}",
                f"- Safe action ID: `{t.get('safe_action_id') or ''}`",
                ''
            ]
            ev=t.get('evidence') or []
            if ev:
                lines.append('Evidence:')
                for e in ev:
                    lines.append(f"- {e}")
                lines.append('')
        if errors:
            lines += ['## Report Errors','']
            for e in errors:
                lines.append(f"- {e.get('source')}: {e.get('error')}")
        mp.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(jp),'markdown':str(mp),'folder':str(out)}

    return report



def repair_ticket_detail_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    ticket_id=(d.get('ticket_id') or d.get('id') or '').strip()
    query=(d.get('query') or d.get('filter') or '').strip().lower()
    include_healthy=True

    queue=repair_ticket_queue_report({'limit':int(d.get('limit') or 500),'include_healthy':include_healthy})
    if not queue.get('ok'):
        return {'ok':False,'message':'Could not load Repair Ticket Queue.','read_only':True,'report_only':True,'queue':queue}

    tickets=queue.get('tickets') or []
    selected=None
    if ticket_id:
        for t in tickets:
            if str(t.get('id','')).lower()==ticket_id.lower():
                selected=t; break
    if not selected and query:
        for t in tickets:
            blob=' '.join([
                str(t.get('id','')),str(t.get('title','')),str(t.get('source','')),
                str(t.get('severity','')),str(t.get('status','')),str(t.get('summary','')),
                str(t.get('suggested_action','')),str(t.get('safe_action_id','')),
                ' '.join(str(x) for x in (t.get('evidence') or []))
            ]).lower()
            if query in blob:
                selected=t; break
    if not selected:
        active=queue.get('active_tickets') or []
        selected=active[0] if active else (tickets[0] if tickets else None)
    if not selected:
        return {'ok':False,'message':'No repair tickets found.','read_only':True,'report_only':True}

    ops=repair_ops_dashboard_report({'limit':300})
    safe_actions=(ops.get('safe_actions') or []) if ops.get('ok') else []
    action_map={a.get('id',''):a for a in safe_actions}
    matching_action=None
    if selected.get('safe_action_id'):
        matching_action=action_map.get(selected.get('safe_action_id'))

    source=str(selected.get('source',''))
    source_folder_map={
        'Build Verify':'build_reports',
        'Env Verify':'env_reports',
        'Portable Ready':'portable_reports',
        'Model Check':'model_reports',
        'Scan Bridge':'scan_reports',
        'Repair Shop':'repair_reports',
        'Repair History':'repair_reports',
        'Backup Vault':'file_backups',
        'Recovery Foundation':'recovery_timeline'
    }
    source_folder_key=source_folder_map.get(source,'repair_reports')
    source_folder=FOLDERS.get(source_folder_key,ROOT/'Reports')

    related=[]
    def add_related(key,path,kind_hint=''):
        if not path: return
        p=Path(str(path))
        exists=False; kind=kind_hint or 'path'; size=None; modified=None
        try:
            exists=p.exists()
            if p.is_dir(): kind='folder'
            elif p.is_file():
                kind='file'; size=p.stat().st_size; modified=datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec='seconds')
        except Exception:
            pass
        related.append({'key':key,'path':str(path),'exists':exists,'kind':kind,'size':size,'modified':modified})

    add_related('source_folder',source_folder,'folder')
    add_related('repair_reports',FOLDERS.get('repair_reports',ROOT/'Reports'/'RepairActions'),'folder')
    if selected.get('safe_action_id')=='generate_optional_dependency_plan':
        add_related('optional_dependency_plan',ROOT/'Reports'/'RepairActions'/'Optional_Dependency_Install_Plan.md','file')
    if selected.get('id')=='legacy_repair_logs':
        add_related('repair_history_logs',FOLDERS.get('repair_reports',ROOT/'Reports'/'RepairActions'),'folder')
    if selected.get('id')=='unassociated_backups':
        add_related('generated_backups',FOLDERS.get('file_backups',ROOT/'Backups'/'GeneratedFiles'),'folder')
    if selected.get('id')=='recovery_clear':
        add_related('recovery_timeline',FOLDERS.get('recovery_timeline',ROOT/'Reports'/'Backups'/'RecoveryTimeline'),'folder')
    details=selected.get('details') or {}
    if isinstance(details,dict):
        report_path=details.get('report') or details.get('path') or ''
        if report_path: add_related('source_report',report_path,'file')

    ticket_status=selected.get('status','')
    severity=selected.get('severity','')
    if ticket_status=='clear' or severity=='healthy': status='healthy'
    elif ticket_status=='available_action': status='available_action'
    elif ticket_status=='informational': status='informational'
    elif severity in ('critical','high','medium'): status='needs_attention'
    else: status='open'

    detail_checks=[
        {'id':'ticket_selected','ok':True,'message':'Ticket was selected from current Repair Ticket Queue.','path':''},
        {'id':'ticket_queue_loaded','ok':bool(queue.get('ok')),'message':'Repair Ticket Queue loaded.','path':''},
        {'id':'ticket_queue_read_only','ok':bool(queue.get('read_only') and queue.get('report_only')),'message':'Ticket Queue is read-only/report-only.','path':''},
        {'id':'source_declared','ok':bool(source),'message':'Ticket source is declared.','path':source},
        {'id':'severity_declared','ok':bool(severity),'message':'Ticket severity is declared.','path':severity},
        {'id':'safe_action_resolved_or_not_required','ok':(not selected.get('safe_action_id') or bool(matching_action)),'message':'Safe action is either not required or resolved from Repair Shop action list.','path':selected.get('safe_action_id','')},
        {'id':'safe_action_requires_confirmation_or_not_required','ok':(not matching_action or bool(matching_action.get('requires_confirmation'))),'message':'Matching safe action still requires explicit confirmation.','path':selected.get('safe_action_id','')},
        {'id':'no_ticket_detail_side_effects','ok':True,'message':'Ticket detail viewer performed read-only inspection only.','path':''}
    ]

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Repair Ticket Detail Viewer',
        'read_only':True,
        'report_only':True,
        'status':status,
        'ticket':selected,
        'ticket_id':selected.get('id',''),
        'ticket_title':selected.get('title',''),
        'ticket_source':source,
        'ticket_severity':severity,
        'ticket_status':ticket_status,
        'ticket_summary':selected.get('summary',''),
        'evidence':selected.get('evidence') or [],
        'suggested_action':selected.get('suggested_action',''),
        'safe_action_id':selected.get('safe_action_id',''),
        'matching_safe_action':matching_action,
        'safe_action_available':bool(matching_action.get('available')) if matching_action else False,
        'safe_action_requires_confirmation':bool(matching_action.get('requires_confirmation')) if matching_action else False,
        'source_folder':str(source_folder),
        'related_paths':related,
        'detail_checks':detail_checks,
        'detail_ok':all(c.get('ok') for c in detail_checks),
        'queue_summary':queue.get('summary',{}),
        'repair_shop_summary':ops.get('summary',{}) if ops.get('ok') else {},
        'safety':{
            'read_only_ticket_detail':True,
            'no_repair_action':True,
            'no_restore':True,
            'no_rollback':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'ticket_detail_export_only':True
        }
    }
    report['message']=f"Repair Ticket Detail: {selected.get('title','Ticket')}"

    if export:
        out=FOLDERS.get('repair_ticket_details',ROOT/'Reports'/'RepairActions'/'TicketDetails')
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name=slug(selected.get('id','ticket'))[:70]
        json_path=out/f'Repair_Ticket_Detail_{safe_name}_{stamp}.json'
        md_path=out/f'Repair_Ticket_Detail_{safe_name}_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Repair Ticket Detail Viewer','',
            f"Created: {report['created']}",
            f"Status: **{status}**",
            f"Ticket ID: `{selected.get('id','')}`",
            f"Title: {selected.get('title','')}",
            f"Source: {source}",
            f"Severity: `{severity}`",
            f"Ticket status: `{ticket_status}`",
            f"Read only: {report['read_only']}",
            f"Report only: {report['report_only']}",
            '',
            '## Safety','',
            '- Read-only ticket detail viewer.',
            '- No repair action.',
            '- No restore.',
            '- No rollback.',
            '- No overwrite.',
            '- No copy-back.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '',
            '## Summary','',
            selected.get('summary',''),
            '',
            '## Evidence',''
        ]
        for e in selected.get('evidence') or []:
            lines.append(f'- {e}')
        lines += ['', '## Suggested Action','', selected.get('suggested_action','None'), '']
        if matching_action:
            lines += [
                '## Matching Safe Action','',
                f"- ID: `{matching_action.get('id')}`",
                f"- Title: {matching_action.get('title')}",
                f"- Available: {matching_action.get('available')}",
                f"- Requires confirmation: {matching_action.get('requires_confirmation')}",
                f"- Risk: `{matching_action.get('risk')}`",
                f"- Reason: {matching_action.get('reason','')}",
                f"- Writes: {', '.join('`'+w+'`' for w in (matching_action.get('writes') or [])) if matching_action.get('writes') else 'none'}",
                ''
            ]
        else:
            lines += ['## Matching Safe Action','','None required or none linked.','']
        lines += ['## Detail Checks','']
        for c in detail_checks:
            lines.append(f"- {'PASS' if c.get('ok') else 'FAIL'} `{c.get('id')}` — {c.get('message')} {('`'+c.get('path','')+'`') if c.get('path') else ''}")
        lines += ['', '## Related Paths','']
        for r in related:
            lines.append(f"- `{r.get('key')}` — {r.get('kind')} — exists={r.get('exists')} — `{r.get('path')}`")
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def repair_ticket_action_bridge_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    ticket_id=(d.get('ticket_id') or d.get('id') or '').strip()
    query=(d.get('query') or d.get('filter') or ticket_id).strip()

    detail=repair_ticket_detail_report({'ticket_id':ticket_id,'query':query,'limit':int(d.get('limit') or 500),'export':False})
    if not detail.get('ok'):
        return {'ok':False,'message':'Could not load ticket detail for bridge.','read_only':True,'report_only':True,'detail':detail}

    plan=repair_action_plan({})
    if not plan.get('ok'):
        return {'ok':False,'message':'Could not load Repair Actions plan for bridge.','read_only':True,'report_only':True,'detail':detail,'plan':plan}

    safe_action_id=(detail.get('safe_action_id') or '').strip()
    matching=None
    for a in plan.get('actions',[]) or []:
        if a.get('id')==safe_action_id:
            matching=a
            break

    if safe_action_id and matching and matching.get('available'):
        bridge_status='ready_for_manual_approval'
        bridge_label='READY — MANUAL APPROVAL REQUIRED'
        bridge_message='Matching safe action is available, but the user must still open Repair Actions and explicitly approve it.'
    elif safe_action_id and matching and not matching.get('available'):
        bridge_status='safe_action_blocked'
        bridge_label='ACTION CURRENTLY BLOCKED'
        bridge_message='Matching safe action exists but is currently blocked by its safety conditions.'
    elif safe_action_id and not matching:
        bridge_status='safe_action_missing'
        bridge_label='ACTION NOT FOUND'
        bridge_message='Ticket names a safe action ID, but the current Repair Actions plan did not expose it.'
    elif detail.get('ticket_status') in ('clear','informational'):
        bridge_status='informational_only'
        bridge_label='INFORMATIONAL — NO ACTION REQUIRED'
        bridge_message='Ticket is informational/healthy and should not be bridged to an action.'
    else:
        bridge_status='no_safe_action'
        bridge_label='NO SAFE ACTION MATCH'
        bridge_message='Ticket does not currently map to an approved safe action.'

    related=list(detail.get('related_paths') or [])
    for key,val in {
        'repair_actions_page':'internal:repairactions',
        'ticket_detail_page':'internal:repairticketdetail',
        'ticket_queue_page':'internal:repairtickets',
        'repair_reports':str(FOLDERS.get('repair_reports',ROOT/'Reports'/'RepairActions')),
        'ticket_bridge_reports':str(FOLDERS.get('repair_ticket_bridges',ROOT/'Reports'/'RepairActions'/'TicketBridges'))
    }.items():
        exists=False; kind='internal' if str(val).startswith('internal:') else 'path'
        try:
            if not str(val).startswith('internal:'):
                p=Path(val); exists=p.exists(); kind='folder' if p.is_dir() else ('file' if p.is_file() else 'path')
        except Exception:
            pass
        related.append({'key':key,'path':val,'exists':exists,'kind':kind})

    checks=[
        {'id':'ticket_detail_loaded','ok':bool(detail.get('ok')),'message':'Ticket detail loaded.','path':detail.get('ticket_id','')},
        {'id':'repair_action_plan_loaded','ok':bool(plan.get('ok')),'message':'Repair Actions plan loaded.','path':''},
        {'id':'bridge_is_read_only','ok':True,'message':'Bridge generated context only and ran no repair action.','path':''},
        {'id':'safe_action_resolved_when_declared','ok':(not safe_action_id or bool(matching)),'message':'Declared safe action was resolved from current Repair Actions plan, if one was declared.','path':safe_action_id},
        {'id':'manual_confirmation_required_when_action_exists','ok':(not matching or bool(matching.get('requires_confirmation'))),'message':'Matching safe action still requires explicit confirmation.','path':safe_action_id},
        {'id':'no_auto_apply','ok':True,'message':'Bridge did not call /api/repair/actions/apply and did not write target files.','path':''},
        {'id':'no_install_no_delete_no_model_cleanup','ok':True,'message':'Bridge performed no install, delete, or model cleanup.','path':''}
    ]

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Ticket-to-Approved-Action Bridge',
        'read_only':True,
        'report_only':True,
        'bridge_status':bridge_status,
        'bridge_label':bridge_label,
        'message':bridge_message,
        'ticket_id':detail.get('ticket_id',''),
        'ticket_title':detail.get('ticket_title',''),
        'ticket_source':detail.get('ticket_source',''),
        'ticket_severity':detail.get('ticket_severity',''),
        'ticket_status':detail.get('ticket_status',''),
        'ticket_summary':detail.get('ticket_summary',''),
        'evidence':detail.get('evidence',[]),
        'suggested_action':detail.get('suggested_action',''),
        'safe_action_id':safe_action_id,
        'matching_safe_action':matching or {},
        'safe_action_available':bool(matching and matching.get('available')),
        'safe_action_requires_confirmation':bool(matching and matching.get('requires_confirmation')),
        'manual_next_steps':[
            'Open Repair Actions.',
            'Build Repair Action Plan.',
            f"Review action ID: {safe_action_id or 'none'}." if safe_action_id else 'No safe action is mapped for this ticket.',
            'Only click Apply This Action if you intentionally approve it.',
            'Browser confirmation and backend confirmation are still required.'
        ],
        'action_plan_summary':plan.get('summary',{}),
        'detail_checks':checks,
        'detail_ok':all(c.get('ok') for c in checks),
        'related_paths':related,
        'ticket_detail_summary':{
            'detail_ok':detail.get('detail_ok'),
            'safe_action_available':detail.get('safe_action_available'),
            'safe_action_requires_confirmation':detail.get('safe_action_requires_confirmation')
        },
        'safety':{
            'read_only_bridge':True,
            'no_repair_action':True,
            'no_restore':True,
            'no_rollback':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'bridge_export_only':True
        }
    }

    if export:
        out=FOLDERS.get('repair_ticket_bridges',ROOT/'Reports'/'RepairActions'/'TicketBridges')
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name=slug(report.get('ticket_id') or 'ticket')[:70]
        jp=out/f'Ticket_Action_Bridge_{safe_name}_{stamp}.json'
        mp=out/f'Ticket_Action_Bridge_{safe_name}_{stamp}.md'
        jwrite(jp,report)
        lines=[
            '# Kayock Ticket-to-Approved-Action Bridge','',
            f"Created: {report['created']}",
            f"Bridge status: **{bridge_label}**",
            f"Ticket: `{report['ticket_id']}` — {report['ticket_title']}",
            f"Source: {report['ticket_source']}",
            f"Severity: {report['ticket_severity']}",
            f"Ticket status: {report['ticket_status']}",
            '',
            '## Safety','',
            '- Read-only bridge.',
            '- No repair action.',
            '- No restore.',
            '- No rollback.',
            '- No overwrite.',
            '- No copy-back.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '',
            '## Ticket Summary','',
            report.get('ticket_summary',''),
            '',
            '## Evidence',''
        ]
        for e in report.get('evidence') or []:
            lines.append(f"- {e}")
        lines += ['', '## Suggested Action','', report.get('suggested_action','') or 'No suggested action.', '']
        if matching:
            lines += [
                '## Matching Safe Action','',
                f"- ID: `{matching.get('id')}`",
                f"- Title: {matching.get('title')}",
                f"- Available: {matching.get('available')}",
                f"- Requires confirmation: {matching.get('requires_confirmation')}",
                f"- Risk: `{matching.get('risk')}`",
                f"- Reason: {matching.get('reason')}",
                f"- Writes: {', '.join('`'+w+'`' for w in (matching.get('writes') or [])) if matching.get('writes') else 'none'}",
                ''
            ]
        lines += ['## Manual Next Steps','']
        for step in report.get('manual_next_steps') or []:
            lines.append(f"- {step}")
        lines += ['', '## Bridge Checks','']
        for c in checks:
            lines.append(f"- {'PASS' if c.get('ok') else 'FAIL'} `{c.get('id')}` — {c.get('message')} {('`'+c.get('path','')+'`') if c.get('path') else ''}")
        lines += ['', '## Related Paths','']
        for r in related:
            lines.append(f"- `{r.get('key')}` — {r.get('kind')} — exists={r.get('exists')} — `{r.get('path')}`")
        mp.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(jp),'markdown':str(mp),'folder':str(out)}

    return report


def repair_shop_session_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    limit=int(d.get('limit') or 300)

    ops=repair_ops_dashboard_report({'limit':limit})
    tickets=repair_ticket_queue_report({'limit':limit})
    verified_card=verified_action_dashboard_card({'limit':limit})
    recovery=recovery_dashboard_summary({'limit':limit})
    backup=backup_vault_report({'limit':limit})
    history=repair_action_history({'limit':limit})

    osum=ops.get('summary') or {}
    tsum=tickets.get('summary') or {}
    rsum=recovery.get('summary') or {}
    bsum=backup.get('summary') or {}
    hsum=history.get('summary') or {}

    recent_logs=history.get('logs',[])[:10]
    active_tickets=tickets.get('active_tickets',[])
    available_action_tickets=tickets.get('available_action_tickets',[])
    informational_tickets=tickets.get('informational_tickets',[])
    healthy_tickets=tickets.get('healthy_tickets',[])

    what_changed=[]
    for l in recent_logs[:8]:
        what_changed.append({
            'kind':'repair_action',
            'created':l.get('created',''),
            'title':l.get('action_id','unknown'),
            'summary':l.get('message',''),
            'ok':l.get('ok'),
            'verified_state':l.get('verified_state',''),
            'target':l.get('target',''),
            'backup':l.get('backup',''),
            'log':l.get('markdown') or l.get('path','')
        })

    safe_to_ignore=[]
    for t in informational_tickets:
        safe_to_ignore.append({
            'ticket_id':t.get('id',''),
            'title':t.get('title',''),
            'reason':t.get('summary',''),
            'suggested_action':t.get('suggested_action','')
        })
    for t in healthy_tickets:
        safe_to_ignore.append({
            'ticket_id':t.get('id',''),
            'title':t.get('title',''),
            'reason':t.get('summary',''),
            'suggested_action':'No action needed.'
        })

    recommended_next=[]
    for t in available_action_tickets:
        recommended_next.append({
            'ticket_id':t.get('id',''),
            'title':t.get('title',''),
            'severity':t.get('severity',''),
            'safe_action_id':t.get('safe_action_id',''),
            'recommendation':t.get('suggested_action',''),
            'manual_approval_required':True,
            'auto_apply':False
        })

    if not recommended_next:
        recommended_next.append({
            'ticket_id':'none',
            'title':'No available repair action needed',
            'severity':'healthy',
            'safe_action_id':'',
            'recommendation':'Continue development. No automatic repair is needed.',
            'manual_approval_required':True,
            'auto_apply':False
        })

    errors=[]
    for name,obj in [('repair_shop',ops),('ticket_queue',tickets),('verified_card',verified_card),('recovery',recovery),('backup_vault',backup),('repair_history',history)]:
        if not obj.get('ok',False):
            errors.append({'source':name,'message':obj.get('message','not ok')})
    errors += tickets.get('errors',[]) if isinstance(tickets.get('errors'),list) else []

    health_inputs={
        'repair_shop_healthy':bool(ops.get('healthy')),
        'ticket_queue_healthy':bool(tickets.get('healthy')),
        'verified_card_healthy':bool(verified_card.get('healthy')),
        'recovery_healthy':bool(recovery.get('healthy')),
        'backup_vault_ok':bool(backup.get('ok')),
        'repair_failures':int(osum.get('repair_failed') or 0),
        'verification_failures':int(osum.get('verification_failed') or 0),
        'open_tickets':int(tsum.get('open_tickets') or 0),
        'critical_tickets':int(tsum.get('critical') or 0),
        'high_tickets':int(tsum.get('high') or 0),
        'medium_tickets':int(tsum.get('medium') or 0),
        'recovery_errors':int(rsum.get('errors') or 0),
        'recovery_attention':int(rsum.get('attention_events') or 0),
        'backup_errors':int((bsum.get('scan_errors') or 0)+(bsum.get('log_errors') or 0)),
        'session_errors':len(errors)
    }

    healthy=bool(
        health_inputs['repair_shop_healthy'] and
        health_inputs['ticket_queue_healthy'] and
        health_inputs['verified_card_healthy'] and
        health_inputs['recovery_healthy'] and
        health_inputs['backup_vault_ok'] and
        health_inputs['repair_failures']==0 and
        health_inputs['verification_failures']==0 and
        health_inputs['open_tickets']==0 and
        health_inputs['critical_tickets']==0 and
        health_inputs['high_tickets']==0 and
        health_inputs['medium_tickets']==0 and
        health_inputs['recovery_errors']==0 and
        health_inputs['recovery_attention']==0 and
        health_inputs['backup_errors']==0 and
        health_inputs['session_errors']==0
    )

    if healthy:
        health_label='SESSION HEALTHY — CHIEF ENGINEERING CLEAR'
    elif health_inputs['critical_tickets'] or health_inputs['high_tickets'] or health_inputs['repair_failures'] or health_inputs['verification_failures']:
        health_label='SESSION NEEDS ATTENTION'
    else:
        health_label='SESSION HAS ADVISORIES'

    summary={
        'repair_shop_health':ops.get('health_label',''),
        'ticket_queue_health':tickets.get('health_label',''),
        'verified_action_health':verified_card.get('health_label',''),
        'recovery_health':recovery.get('health_label',''),
        'recovery_chain':recovery.get('current_chain',''),
        'repair_logs':osum.get('repair_logs',0),
        'repair_ok':osum.get('repair_ok',0),
        'repair_failed':osum.get('repair_failed',0),
        'verification_passed':osum.get('verification_passed',0),
        'verification_failed':osum.get('verification_failed',0),
        'legacy_logs_without_verification':osum.get('legacy_logs_without_verification',0),
        'tickets':tsum.get('tickets',0),
        'active_tickets':tsum.get('active_tickets',0),
        'open_tickets':tsum.get('open_tickets',0),
        'available_action_tickets':tsum.get('available_action_tickets',0),
        'informational_tickets':tsum.get('informational_tickets',0),
        'healthy_tickets':tsum.get('healthy_tickets',0),
        'critical':tsum.get('critical',0),
        'high':tsum.get('high',0),
        'medium':tsum.get('medium',0),
        'low':tsum.get('low',0),
        'info':tsum.get('info',0),
        'generated_backups':bsum.get('backups',0),
        'verified_backups':bsum.get('verified',0),
        'unassociated_backups':bsum.get('unassociated',0),
        'backup_errors':health_inputs['backup_errors'],
        'latest_action':osum.get('latest_action','') or hsum.get('last_action',''),
        'latest_action_created':osum.get('latest_action_created','') or hsum.get('last_created',''),
        'latest_backup':bsum.get('latest_backup',''),
        'latest_recovery_event':rsum.get('latest_event',''),
        'latest_recovery_created':rsum.get('latest_created','')
    }

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Repair Shop Session Report',
        'read_only':True,
        'report_only':True,
        'healthy':healthy,
        'health_label':health_label,
        'message':f"Repair Shop Session: {health_label}",
        'summary':summary,
        'health_inputs':health_inputs,
        'what_changed_this_session':what_changed,
        'active_tickets':active_tickets,
        'recommended_next':recommended_next,
        'safe_to_ignore':safe_to_ignore,
        'recent_logs':recent_logs,
        'available_action_tickets':available_action_tickets,
        'informational_tickets':informational_tickets,
        'healthy_tickets':healthy_tickets,
        'repair_shop_summary':osum,
        'ticket_queue_summary':tsum,
        'backup_summary':bsum,
        'recovery_summary':rsum,
        'verified_action_card':verified_card,
        'errors':errors,
        'folders':{
            'session_reports':str(FOLDERS.get('repair_session_reports',ROOT/'Reports'/'RepairActions'/'SessionReports')),
            'repair_reports':str(FOLDERS.get('repair_reports',ROOT/'Reports'/'RepairActions')),
            'ticket_reports':str(FOLDERS.get('repair_tickets',ROOT/'Reports'/'RepairActions'/'Tickets')),
            'backup_vault':str(FOLDERS.get('file_backups',ROOT/'Backups'/'GeneratedFiles')),
            'recovery_timeline':str(FOLDERS.get('recovery_timeline',ROOT/'Reports'/'Backups'/'RecoveryTimeline'))
        },
        'safety':{
            'read_only_session_report':True,
            'no_repair_action':True,
            'no_restore':True,
            'no_rollback':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'session_export_only':True
        }
    }

    if export:
        out=FOLDERS.get('repair_session_reports',ROOT/'Reports'/'RepairActions'/'SessionReports')
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=out/f'Repair_Shop_Session_{stamp}.json'
        md_path=out/f'Repair_Shop_Session_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Repair Shop Session Report','',
            f"Created: {report['created']}",
            f"Health: **{health_label}**",
            f"Read only: {report['read_only']}",
            f"Report only: {report['report_only']}",
            '',
            '## Safety','',
            '- Read-only session report.',
            '- No repair action.',
            '- No restore.',
            '- No rollback.',
            '- No overwrite.',
            '- No copy-back.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '',
            '## Session Summary',''
        ]
        for k,v in summary.items():
            lines.append(f"- {k.replace('_',' ').title()}: {v}")
        lines += ['','## What Changed This Session','']
        for item in what_changed:
            lines += [
                f"### {item.get('created')} — {item.get('title')}",
                '',
                f"- OK: {item.get('ok')}",
                f"- Verified: {item.get('verified_state')}",
                f"- Summary: {item.get('summary')}",
                f"- Target: `{item.get('target')}`",
                f"- Backup: `{item.get('backup')}`",
                f"- Log: `{item.get('log')}`",
                ''
            ]
        lines += ['','## Active Tickets','']
        for t in active_tickets:
            lines += [
                f"### {t.get('severity','').upper()} — {t.get('title')}",
                '',
                f"- ID: `{t.get('id')}`",
                f"- Source: {t.get('source')}",
                f"- Status: {t.get('status')}",
                f"- Summary: {t.get('summary')}",
                f"- Suggested action: {t.get('suggested_action')}",
                f"- Safe action ID: `{t.get('safe_action_id','')}`",
                ''
            ]
        lines += ['','## Recommended Next','']
        for r in recommended_next:
            lines += [
                f"- `{r.get('ticket_id')}` — {r.get('title')} — {r.get('recommendation')} — manual approval required: {r.get('manual_approval_required')}"
            ]
        lines += ['','## Safe To Ignore / Historical','']
        for r in safe_to_ignore:
            lines.append(f"- `{r.get('ticket_id')}` — {r.get('title')} — {r.get('reason')}")
        if errors:
            lines += ['','## Errors','']
            for e in errors:
                lines.append(f"- {e}")
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def repair_shop_milestone_freeze_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    limit=int(d.get('limit') or 300)

    session=repair_shop_session_report({'limit':limit})
    ops=repair_ops_dashboard_report({'limit':limit})
    action_detail=repair_action_detail_report({'query':'single_file_rollback'})
    verified_card=verified_action_dashboard_card({'limit':limit})
    ticket_queue=repair_ticket_queue_report({'limit':limit})
    ticket_detail=repair_ticket_detail_report({'ticket_id':'optional_repair_tools_missing'})
    bridge=repair_ticket_action_bridge_report({'ticket_id':'optional_repair_tools_missing'})
    recovery=recovery_dashboard_summary({'limit':limit})
    backup=backup_vault_report({'limit':limit})

    ss=session.get('summary') or {}
    osum=ops.get('summary') or {}
    tq=ticket_queue.get('summary') or {}
    rs=recovery.get('summary') or {}
    bs=backup.get('summary') or {}

    milestone_modules=[
        {
            'version':'v10.9.0',
            'name':'Repair Shop Operations Dashboard',
            'status':'complete_proven' if ops.get('healthy') else 'check',
            'proof':'Repair Shop health, RepairActions history, safe actions, generated backups, and Recovery Foundation status are summarized.',
            'endpoint':'/api/repair/ops_dashboard',
            'page':'repairops',
            'read_only':True
        },
        {
            'version':'v10.9.1',
            'name':'Repair Action Detail Viewer',
            'status':'complete_proven' if action_detail.get('detail_ok') and action_detail.get('status') in ('verified','legacy_ok') else 'check',
            'proof':'A selected RepairActions log can be inspected with verification checks, target, backup, related paths, and safety state.',
            'endpoint':'/api/repair/action_detail',
            'page':'repairdetail',
            'read_only':True
        },
        {
            'version':'v10.9.2',
            'name':'Verified Action Dashboard Card',
            'status':'complete_proven' if verified_card.get('healthy') else 'check',
            'proof':'Command Bridge can surface the latest verified RepairActions state without running repairs.',
            'endpoint':'/api/repair/verified_dashboard',
            'page':'dash',
            'read_only':True
        },
        {
            'version':'v10.9.3',
            'name':'Repair Ticket Queue',
            'status':'complete_proven' if ticket_queue.get('healthy') and int(tq.get('open_tickets') or 0)==0 else 'check',
            'proof':'Repair issues and advisories are triaged into healthy, informational, and available-action tickets.',
            'endpoint':'/api/repair/ticket_queue',
            'page':'repairtickets',
            'read_only':True
        },
        {
            'version':'v10.9.4',
            'name':'Repair Ticket Detail Viewer',
            'status':'complete_proven' if ticket_detail.get('detail_ok') else 'check',
            'proof':'A selected ticket can be inspected with evidence, suggested action, matching safe action, and confirmation requirements.',
            'endpoint':'/api/repair/ticket_detail',
            'page':'repairticketdetail',
            'read_only':True
        },
        {
            'version':'v10.9.5',
            'name':'Ticket-to-Approved-Action Bridge',
            'status':'complete_proven' if bridge.get('detail_ok') and bridge.get('bridge_status') in ('ready_for_manual_approval','informational_only','no_matching_action') else 'check',
            'proof':'A ticket can be bridged to a safe action context while preserving manual approval and no-auto-apply rules.',
            'endpoint':'/api/repair/ticket_action_bridge',
            'page':'ticketbridge',
            'read_only':True
        },
        {
            'version':'v10.9.6',
            'name':'Repair Shop Session Report',
            'status':'complete_proven' if session.get('healthy') else 'check',
            'proof':'Chief Engineering session report summarizes Repair Shop health, tickets, backups, Recovery Foundation, and recommended next steps.',
            'endpoint':'/api/repair/session_report',
            'page':'repairsession',
            'read_only':True
        }
    ]

    problems=[]
    for name,obj in [
        ('session',session),('operations',ops),('action_detail',action_detail),
        ('verified_card',verified_card),('ticket_queue',ticket_queue),
        ('ticket_detail',ticket_detail),('ticket_bridge',bridge),
        ('recovery',recovery),('backup_vault',backup)
    ]:
        if not obj.get('ok'):
            problems.append({'source':name,'message':obj.get('message','not ok')})
    for m in milestone_modules:
        if m.get('status')!='complete_proven':
            problems.append({'source':m.get('version'),'message':m.get('name')+' is not marked complete/proven.'})

    safety_contract={
        'scan_first':True,
        'report_second':True,
        'ask_before_action':True,
        'read_only_freeze_report':True,
        'no_repair_action':True,
        'no_restore':True,
        'no_rollback':True,
        'no_overwrite':True,
        'no_copy_back':True,
        'no_delete':True,
        'no_install':True,
        'no_model_cleanup':True,
        'freeze_export_only':True
    }

    foundation_ready=bool(
        not problems and
        session.get('healthy') and
        ops.get('healthy') and
        verified_card.get('healthy') and
        ticket_queue.get('healthy') and
        recovery.get('healthy') and
        backup.get('ok') and
        int(ss.get('repair_failed') or 0)==0 and
        int(ss.get('verification_failed') or 0)==0 and
        int(ss.get('open_tickets') or 0)==0 and
        int(ss.get('critical') or 0)==0 and
        int(ss.get('high') or 0)==0 and
        int(ss.get('medium') or 0)==0 and
        int(ss.get('backup_errors') or 0)==0 and
        int(rs.get('errors') or 0)==0 and
        int(rs.get('attention_events') or 0)==0
    )

    freeze_label='REPAIR SHOP FOUNDATION FROZEN — COMPLETE / PROVEN' if foundation_ready else 'REPAIR SHOP FREEZE NEEDS REVIEW'

    recommendations=[
        {
            'id':'freeze_repair_shop_foundation',
            'title':'Freeze v10.9.x Repair Shop Foundation',
            'recommendation':'Treat v10.9.0 through v10.9.6 as the proven Repair Shop foundation.',
            'status':'recommended' if foundation_ready else 'blocked_until_review',
            'risk':'low'
        },
        {
            'id':'do_not_auto_install_optional_tools',
            'title':'Keep optional tool installation manual',
            'recommendation':'Optional Repair Bay tools can remain advisory. Continue using the optional dependency plan rather than automatic install.',
            'status':'recommended',
            'risk':'low'
        },
        {
            'id':'leave_legacy_logs_historical',
            'title':'Leave legacy logs as historical',
            'recommendation':'Older successful logs without verification can remain historical unless a future migration tool is intentionally built.',
            'status':'recommended',
            'risk':'low'
        },
        {
            'id':'next_milestone',
            'title':'Move to next milestone',
            'recommendation':'Start v10.10.x as a new foundation area rather than adding more complexity to Repair Shop.',
            'status':'recommended' if foundation_ready else 'wait',
            'risk':'low'
        }
    ]

    freeze_summary={
        'modules':len(milestone_modules),
        'modules_complete_proven':sum(1 for m in milestone_modules if m.get('status')=='complete_proven'),
        'modules_need_review':sum(1 for m in milestone_modules if m.get('status')!='complete_proven'),
        'repair_shop_health':ops.get('health_label',''),
        'session_health':session.get('health_label',''),
        'ticket_queue_health':ticket_queue.get('health_label',''),
        'verified_action_health':verified_card.get('health_label',''),
        'recovery_health':recovery.get('health_label',''),
        'recovery_chain':recovery.get('current_chain',''),
        'repair_logs':ss.get('repair_logs',0),
        'repair_failed':ss.get('repair_failed',0),
        'verification_failed':ss.get('verification_failed',0),
        'open_tickets':ss.get('open_tickets',0),
        'critical':ss.get('critical',0),
        'high':ss.get('high',0),
        'medium':ss.get('medium',0),
        'active_tickets':ss.get('active_tickets',0),
        'available_action_tickets':ss.get('available_action_tickets',0),
        'informational_tickets':ss.get('informational_tickets',0),
        'healthy_tickets':ss.get('healthy_tickets',0),
        'generated_backups':ss.get('generated_backups',0),
        'verified_backups':ss.get('verified_backups',0),
        'backup_errors':ss.get('backup_errors',0),
        'latest_action':ss.get('latest_action',''),
        'latest_action_created':ss.get('latest_action_created',''),
        'latest_recovery_event':ss.get('latest_recovery_event','')
    }

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Repair Shop Milestone Freeze',
        'read_only':True,
        'report_only':True,
        'healthy':foundation_ready,
        'freeze_ready':foundation_ready,
        'health_label':freeze_label,
        'message':f"Repair Shop Milestone Freeze: {freeze_label}",
        'milestone':'v10.9.x Repair Shop Foundation',
        'version_range':'v10.9.0 through v10.9.6',
        'summary':freeze_summary,
        'milestone_modules':milestone_modules,
        'recommendations':recommendations,
        'problems':problems,
        'safety_contract':safety_contract,
        'source_reports':{
            'session_summary':ss,
            'repair_shop_summary':osum,
            'ticket_queue_summary':tq,
            'recovery_summary':rs,
            'backup_summary':bs,
            'latest_verified_action':verified_card.get('latest_action',{}),
            'active_tickets':session.get('active_tickets',[]),
            'safe_to_ignore':session.get('safe_to_ignore',[]),
            'recommended_next':session.get('recommended_next',[])
        },
        'folders':{
            'milestone_freeze':str(FOLDERS.get('repair_milestone_freeze',ROOT/'Reports'/'RepairActions'/'MilestoneFreeze')),
            'session_reports':str(FOLDERS.get('repair_session_reports',ROOT/'Reports'/'RepairActions'/'SessionReports')),
            'repair_reports':str(FOLDERS.get('repair_reports',ROOT/'Reports'/'RepairActions')),
            'ticket_reports':str(FOLDERS.get('repair_tickets',ROOT/'Reports'/'RepairActions'/'Tickets')),
            'recovery_timeline':str(FOLDERS.get('recovery_timeline',ROOT/'Reports'/'Backups'/'RecoveryTimeline'))
        }
    }

    if export:
        out=FOLDERS.get('repair_milestone_freeze',ROOT/'Reports'/'RepairActions'/'MilestoneFreeze')
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=out/f'Repair_Shop_Milestone_Freeze_{stamp}.json'
        md_path=out/f'Repair_Shop_Milestone_Freeze_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Repair Shop Milestone Freeze','',
            f"Created: {report['created']}",
            f"Milestone: **{report['milestone']}**",
            f"Version range: {report['version_range']}",
            f"Health: **{freeze_label}**",
            f"Freeze ready: {foundation_ready}",
            f"Read only: {report['read_only']}",
            f"Report only: {report['report_only']}",
            '',
            '## Safety Contract','',
            '- Scan first.',
            '- Report second.',
            '- Ask before action.',
            '- Read-only freeze report.',
            '- No repair action.',
            '- No restore.',
            '- No rollback.',
            '- No overwrite.',
            '- No copy-back.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '',
            '## Summary',''
        ]
        for k,v in freeze_summary.items():
            lines.append(f"- {k.replace('_',' ').title()}: {v}")
        lines += ['','## Proven Modules','']
        for m in milestone_modules:
            lines += [
                f"### {m.get('version')} — {m.get('name')}",
                '',
                f"- Status: `{m.get('status')}`",
                f"- Endpoint: `{m.get('endpoint')}`",
                f"- Page: `{m.get('page')}`",
                f"- Read only: {m.get('read_only')}",
                f"- Proof: {m.get('proof')}",
                ''
            ]
        lines += ['','## Recommendations','']
        for r in recommendations:
            lines += [
                f"- `{r.get('id')}` — {r.get('title')} — {r.get('status')} — {r.get('recommendation')}"
            ]
        lines += ['','## Problems','']
        if problems:
            for p in problems:
                lines.append(f"- {p}")
        else:
            lines.append('- None.')
        lines += ['','## Safe To Ignore / Historical','']
        for item in session.get('safe_to_ignore',[]):
            lines.append(f"- `{item.get('ticket_id')}` — {item.get('title')} — {item.get('reason')}")
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def command_center_foundation_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    limit=int(d.get('limit') or 300)

    def safe_call(name, func, payload=None):
        try:
            return func(payload or {})
        except TypeError:
            try:
                return func()
            except Exception as e:
                return {'ok':False,'message':f'{name} failed: {e}'}
        except Exception as e:
            return {'ok':False,'message':f'{name} failed: {e}'}

    repair_freeze=safe_call('repair_milestone_freeze', repair_shop_milestone_freeze_report, {'limit':limit})
    repair_session=safe_call('repair_session', repair_shop_session_report, {'limit':limit})
    recovery=safe_call('recovery_dashboard', recovery_dashboard_summary, {'limit':limit})
    build=safe_call('build_verify', build_verification_lite, {'export':False,'max_py':200})
    env=safe_call('env_verify', env_dependency_verification, {'export':False})
    portable=safe_call('portable_readiness', portable_readiness_report, {'export':False})
    models=safe_call('model_check', model_duplicate_truth_report, {'export':False})
    docs=safe_call('project_docs_status', project_docs_status, {})
    extensions=safe_call('list_extensions', list_extensions, {})
    try:
        ext_validation=validate_extensions()
    except Exception as e:
        ext_validation={'ok':False,'message':str(e),'problems':[str(e)]}

    scan_folder=FOLDERS.get('scan_reports',ROOT/'Reports'/'Scans')
    scan_reports=[]
    latest_scan={}
    scan_ok=True
    scan_message='No Scan Bridge reports found yet.'
    try:
        if scan_folder.exists():
            files=sorted([p for p in scan_folder.glob('*.json') if p.is_file()], key=lambda p:p.stat().st_mtime, reverse=True)
            for p in files[:5]:
                info={'path':str(p),'name':p.name,'modified':datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec='seconds'),'ok':True,'summary':{}}
                try:
                    data=json.loads(p.read_text(encoding='utf-8',errors='replace'))
                    info['summary']=data.get('summary') or data.get('counts') or {}
                    if isinstance(data.get('counts'),dict) and int(data.get('counts',{}).get('errors') or 0)>0:
                        info['ok']=False
                    if isinstance(data.get('errors'),list) and len(data.get('errors'))>0:
                        info['ok']=False
                except Exception as e:
                    info['ok']=False
                    info['message']=str(e)
                scan_reports.append(info)
            if scan_reports:
                latest_scan=scan_reports[0]
                scan_ok=bool(latest_scan.get('ok'))
                scan_message='Latest Scan Bridge report is clear.' if scan_ok else 'Latest Scan Bridge report needs review.'
    except Exception as e:
        scan_ok=False
        scan_message=f'Could not inspect Scan Bridge reports: {e}'

    def status_from_bool(ok, advisory=False):
        if ok and advisory:
            return 'advisory'
        if ok:
            return 'clear'
        return 'needs_attention'

    def score_status(status):
        return {'clear':100,'advisory':70,'needs_attention':0}.get(status,0)

    bsum=build.get('summary') or {}
    esum=env.get('summary') or {}
    psum=portable.get('summary') or {}
    msum=models.get('summary') or {}
    dsum=docs.get('summary') or {}
    xproblems=ext_validation.get('problems') or []
    fsum=repair_freeze.get('summary') or {}
    ssum=repair_session.get('summary') or {}
    rsum=recovery.get('summary') or {}

    foundations=[
        {
            'id':'repair_shop_foundation',
            'title':'Repair Shop Foundation',
            'status':status_from_bool(bool(repair_freeze.get('freeze_ready')) and bool(repair_freeze.get('healthy'))),
            'health':repair_freeze.get('health_label',''),
            'summary':f"{fsum.get('modules_complete_proven',0)}/{fsum.get('modules',0)} Repair Shop modules proven; repair failures {fsum.get('repair_failed',0)}; verification failures {fsum.get('verification_failed',0)}.",
            'source':'v10.9.x Milestone Freeze',
            'page':'repairfreeze',
            'endpoint':'/api/repair/milestone_freeze',
            'metrics':fsum,
            'recommended_action':'No action needed.' if repair_freeze.get('freeze_ready') else 'Review Repair Shop milestone freeze.'
        },
        {
            'id':'recovery_foundation',
            'title':'Recovery Foundation',
            'status':status_from_bool(bool(recovery.get('healthy')) and int(rsum.get('errors') or 0)==0 and int(rsum.get('attention_events') or 0)==0),
            'health':recovery.get('health_label',''),
            'summary':f"Recovery chain {recovery.get('current_chain','')}; restore actions {rsum.get('restore_actions',0)}; rollback actions {rsum.get('rollback_actions',0)}; events {rsum.get('events',0)}.",
            'source':'Recovery Dashboard',
            'page':'recoverytimeline',
            'endpoint':'/api/backups/recovery_dashboard',
            'metrics':rsum,
            'recommended_action':'No action needed.' if recovery.get('healthy') else 'Review Recovery Foundation.'
        },
        {
            'id':'build_verify',
            'title':'Build Verify',
            'status':status_from_bool(bool(build.get('ok')) and int(bsum.get('problems') or 0)==0),
            'health':'BUILD VERIFY CLEAR' if bool(build.get('ok')) and int(bsum.get('problems') or 0)==0 else 'BUILD VERIFY NEEDS ATTENTION',
            'summary':f"{bsum.get('passed',0)}/{bsum.get('checks',0)} checks passed; Python files checked {bsum.get('python_files',0)}.",
            'source':'Build Verify',
            'page':'buildverify',
            'endpoint':'/api/build/verify',
            'metrics':bsum,
            'recommended_action':'No action needed.' if build.get('ok') else 'Open Build Verify and inspect problems.'
        },
        {
            'id':'env_verify',
            'title':'Environment Verify',
            'status':status_from_bool(bool(env.get('ok')) and int(esum.get('problems') or 0)==0, advisory=int(esum.get('optional_missing') or 0)>0),
            'health':'ENV REQUIRED CLEAR' if bool(env.get('ok')) and int(esum.get('problems') or 0)==0 else 'ENV NEEDS ATTENTION',
            'summary':f"{esum.get('passed',0)}/{esum.get('checks',0)} checks passed; required problems {esum.get('problems',0)}; optional tools available {esum.get('optional_tools_available',0)}/{esum.get('optional_tools_total',0)}.",
            'source':'Env Verify',
            'page':'envverify',
            'endpoint':'/api/env/verify',
            'metrics':esum,
            'recommended_action':'Optional tools can remain advisory; use the dependency plan only when intentionally approved.' if int(esum.get('optional_missing') or 0)>0 else 'No action needed.'
        },
        {
            'id':'portable_ready',
            'title':'Portable Ready',
            'status':status_from_bool(bool(portable.get('ok')) and int(psum.get('blockers') or 0)==0 and int(psum.get('warnings') or 0)==0),
            'health':psum.get('readiness','PORTABLE READY') if portable.get('ok') else 'PORTABLE READINESS NEEDS ATTENTION',
            'summary':f"Score {psum.get('score',0)}; blockers {psum.get('blockers',0)}; warnings {psum.get('warnings',0)}; runtime locked {psum.get('runtime_locked',False)}.",
            'source':'Portable Ready',
            'page':'portable',
            'endpoint':'/api/portable/readiness',
            'metrics':psum,
            'recommended_action':'No action needed.' if portable.get('ok') and int(psum.get('blockers') or 0)==0 else 'Review portable readiness blockers.'
        },
        {
            'id':'model_check',
            'title':'Model Check',
            'status':status_from_bool(bool(models.get('ok')) and int(msum.get('true_duplicate_groups') or 0)==0 and int(msum.get('scan_errors') or 0)==0),
            'health':'MODEL CHECK CLEAR' if int(msum.get('true_duplicate_groups') or 0)==0 else 'MODEL DUPLICATES NEED REVIEW',
            'summary':f"Physical model files {msum.get('physical_model_files',0)}; unique model keys {msum.get('unique_model_keys',0)}; true duplicate groups {msum.get('true_duplicate_groups',0)}.",
            'source':'Model Check',
            'page':'modelcheck',
            'endpoint':'/api/models/duplicates',
            'metrics':msum,
            'recommended_action':'No action needed. Do not delete models automatically.' if int(msum.get('true_duplicate_groups') or 0)==0 else 'Review model duplicates; no automatic cleanup.'
        },
        {
            'id':'scan_bridge',
            'title':'Scan Bridge',
            'status':status_from_bool(scan_ok),
            'health':'SCAN BRIDGE CLEAR' if scan_ok else 'SCAN BRIDGE NEEDS REVIEW',
            'summary':scan_message,
            'source':'Scan Bridge reports',
            'page':'scanbridge',
            'endpoint':'/api/scan/folder',
            'metrics':latest_scan.get('summary',{}),
            'recommended_action':'No action needed.' if scan_ok else 'Open Scan Bridge and inspect the latest report.'
        },
        {
            'id':'project_docs',
            'title':'Project Docs',
            'status':status_from_bool(bool(docs.get('ok')) and int(dsum.get('problems') or 0)==0),
            'health':'PROJECT DOCS CLEAR' if int(dsum.get('problems') or 0)==0 else 'PROJECT DOCS NEED REVIEW',
            'summary':f"Present {dsum.get('present',0)}; problems {dsum.get('problems',0)}.",
            'source':'Project Docs Status',
            'page':'projectgen',
            'endpoint':'/api/project_docs/status',
            'metrics':dsum,
            'recommended_action':'No action needed.' if int(dsum.get('problems') or 0)==0 else 'Open Project Docs and inspect missing/invalid docs.'
        },
        {
            'id':'extension_manager',
            'title':'Extension Manager',
            'status':status_from_bool(bool(extensions.get('ok')) and len(xproblems)==0),
            'health':'EXTENSIONS CLEAR' if len(xproblems)==0 else 'EXTENSIONS NEED REVIEW',
            'summary':f"Extensions {extensions.get('count',0)}; enabled {extensions.get('enabled',0)}; valid {extensions.get('valid',0)}; problems {len(xproblems)}.",
            'source':'Extension Manager',
            'page':'extensions',
            'endpoint':'/api/extensions/list',
            'metrics':{'count':extensions.get('count',0),'enabled':extensions.get('enabled',0),'valid':extensions.get('valid',0),'problems':len(xproblems)},
            'recommended_action':'No action needed.' if len(xproblems)==0 else 'Open Extension Manager and review manifest problems.'
        }
    ]

    clear=sum(1 for f in foundations if f.get('status')=='clear')
    advisory=sum(1 for f in foundations if f.get('status')=='advisory')
    needs_attention=sum(1 for f in foundations if f.get('status')=='needs_attention')
    score=round(sum(score_status(f.get('status')) for f in foundations)/max(1,len(foundations)))
    command_ready=needs_attention==0
    fully_clear=needs_attention==0 and advisory==0
    health_label='COMMAND CENTER CLEAR — ALL FOUNDATIONS READY' if fully_clear else ('COMMAND CENTER READY — ADVISORIES ONLY' if command_ready else 'COMMAND CENTER NEEDS ATTENTION')

    advisories=[]
    attention=[]
    for f in foundations:
        if f.get('status')=='advisory':
            advisories.append({'id':f.get('id'), 'title':f.get('title'), 'summary':f.get('summary'), 'recommended_action':f.get('recommended_action')})
        elif f.get('status')=='needs_attention':
            attention.append({'id':f.get('id'), 'title':f.get('title'), 'summary':f.get('summary'), 'recommended_action':f.get('recommended_action')})

    safe_to_ignore=[]
    if repair_session.get('safe_to_ignore'):
        safe_to_ignore.extend(repair_session.get('safe_to_ignore',[])[:10])
    for a in advisories:
        safe_to_ignore.append({'ticket_id':a.get('id'), 'title':a.get('title'), 'reason':a.get('summary'), 'suggested_action':a.get('recommended_action')})

    recommendations=[]
    if command_ready:
        recommendations.append({
            'id':'proceed_with_work',
            'title':'Command Center is ready for work',
            'recommendation':'Proceed with normal Kayock Command OS work. Treat advisories as optional maintenance.',
            'risk':'low',
            'auto_apply':False
        })
    for a in attention:
        recommendations.append({
            'id':a.get('id'),
            'title':'Review '+a.get('title','foundation'),
            'recommendation':a.get('recommended_action','Review this foundation.'),
            'risk':'medium',
            'auto_apply':False
        })
    for a in advisories:
        recommendations.append({
            'id':a.get('id'),
            'title':'Advisory: '+a.get('title','foundation'),
            'recommendation':a.get('recommended_action','Advisory only.'),
            'risk':'low',
            'auto_apply':False
        })

    summary={
        'foundations':len(foundations),
        'clear':clear,
        'advisory':advisory,
        'needs_attention':needs_attention,
        'score':score,
        'command_ready':command_ready,
        'fully_clear':fully_clear,
        'repair_shop_foundation':repair_freeze.get('health_label',''),
        'recovery_foundation':recovery.get('health_label',''),
        'build_verify_problems':bsum.get('problems',0),
        'env_required_problems':esum.get('problems',0),
        'env_optional_missing':esum.get('optional_missing',0),
        'portable_score':psum.get('score',0),
        'portable_blockers':psum.get('blockers',0),
        'portable_warnings':psum.get('warnings',0),
        'true_model_duplicate_groups':msum.get('true_duplicate_groups',0),
        'scan_bridge_status':'clear' if scan_ok else 'needs_attention',
        'project_docs_problems':dsum.get('problems',0),
        'extension_problems':len(xproblems),
        'latest_repair_action':(repair_session.get('summary') or {}).get('latest_action',''),
        'latest_recovery_event':rsum.get('latest_event','')
    }

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Command Center Foundation',
        'read_only':True,
        'report_only':True,
        'healthy':command_ready,
        'command_ready':command_ready,
        'fully_clear':fully_clear,
        'health_label':health_label,
        'message':f"Command Center Foundation: {health_label}",
        'milestone':'v10.10.0 Command Center Foundation',
        'summary':summary,
        'foundations':foundations,
        'attention':attention,
        'advisories':advisories,
        'recommendations':recommendations,
        'safe_to_ignore':safe_to_ignore,
        'latest_scan_reports':scan_reports,
        'source_reports':{
            'repair_freeze_summary':fsum,
            'repair_session_summary':ssum,
            'recovery_summary':rsum,
            'build_summary':bsum,
            'env_summary':esum,
            'portable_summary':psum,
            'model_summary':msum,
            'project_docs_summary':dsum,
            'extension_summary':extensions,
            'extension_validation':ext_validation
        },
        'folders':{
            'command_center_reports':str(FOLDERS.get('command_center_reports',ROOT/'Reports'/'CommandCenter')),
            'repair_milestone_freeze':str(FOLDERS.get('repair_milestone_freeze',ROOT/'Reports'/'RepairActions'/'MilestoneFreeze')),
            'recovery_timeline':str(FOLDERS.get('recovery_timeline',ROOT/'Reports'/'Backups'/'RecoveryTimeline')),
            'scan_reports':str(scan_folder)
        },
        'safety_contract':{
            'scan_first':True,
            'report_second':True,
            'ask_before_action':True,
            'read_only_command_center':True,
            'no_repair_action':True,
            'no_restore':True,
            'no_rollback':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'command_center_export_only':True
        }
    }

    if export:
        out=FOLDERS.get('command_center_reports',ROOT/'Reports'/'CommandCenter')
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=out/f'Command_Center_Foundation_{stamp}.json'
        md_path=out/f'Command_Center_Foundation_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Command Center Foundation','',
            f"Created: {report['created']}",
            f"Milestone: **{report['milestone']}**",
            f"Health: **{health_label}**",
            f"Command ready: {command_ready}",
            f"Fully clear: {fully_clear}",
            f"Score: {score}",
            f"Read only: {report['read_only']}",
            f"Report only: {report['report_only']}",
            '',
            '## Safety Contract','',
            '- Scan first.',
            '- Report second.',
            '- Ask before action.',
            '- Read-only Command Center.',
            '- No repair action.',
            '- No restore.',
            '- No rollback.',
            '- No overwrite.',
            '- No copy-back.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '',
            '## Summary',''
        ]
        for k,v in summary.items():
            lines.append(f"- {k.replace('_',' ').title()}: {v}")
        lines += ['','## Foundations','']
        for f in foundations:
            lines += [
                f"### {f.get('title')}",
                '',
                f"- Status: `{f.get('status')}`",
                f"- Health: {f.get('health')}",
                f"- Source: {f.get('source')}",
                f"- Page: `{f.get('page')}`",
                f"- Endpoint: `{f.get('endpoint')}`",
                f"- Summary: {f.get('summary')}",
                f"- Recommended action: {f.get('recommended_action')}",
                ''
            ]
        lines += ['','## Recommendations','']
        for r in recommendations:
            lines.append(f"- `{r.get('id')}` — {r.get('title')} — {r.get('recommendation')} — auto apply: {r.get('auto_apply')}")
        lines += ['','## Attention','']
        if attention:
            for a in attention:
                lines.append(f"- `{a.get('id')}` — {a.get('title')} — {a.get('summary')}")
        else:
            lines.append('- None.')
        lines += ['','## Advisories','']
        if advisories:
            for a in advisories:
                lines.append(f"- `{a.get('id')}` — {a.get('title')} — {a.get('summary')}")
        else:
            lines.append('- None.')
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def command_center_detail_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    foundation_id=(d.get('foundation_id') or d.get('id') or '').strip()
    if not foundation_id:
        foundation_id='env_verify'

    foundation_report=command_center_foundation_report({'limit':int(d.get('limit') or 300)})
    foundations=foundation_report.get('foundations') or []
    selected=None
    for f in foundations:
        if f.get('id')==foundation_id or f.get('title','').lower()==foundation_id.lower():
            selected=f
            break

    if not selected:
        return {
            'ok':False,
            'created':now(),
            'title':'Kayock Command Center Detail Viewer',
            'read_only':True,
            'report_only':True,
            'message':f'Foundation not found: {foundation_id}',
            'available_foundations':[{'id':f.get('id'),'title':f.get('title')} for f in foundations],
            'safety':{
                'read_only_command_detail':True,
                'no_repair_action':True,
                'no_restore':True,
                'no_rollback':True,
                'no_overwrite':True,
                'no_copy_back':True,
                'no_delete':True,
                'no_install':True,
                'no_model_cleanup':True,
                'command_detail_export_only':True
            }
        }

    status=selected.get('status','')
    attention=foundation_report.get('attention') or []
    advisories=foundation_report.get('advisories') or []
    matching_attention=[a for a in attention if a.get('id')==selected.get('id')]
    matching_advisory=[a for a in advisories if a.get('id')==selected.get('id')]

    source_reports=foundation_report.get('source_reports') or {}
    source_key_map={
        'repair_shop_foundation':'repair_freeze_summary',
        'recovery_foundation':'recovery_summary',
        'build_verify':'build_summary',
        'env_verify':'env_summary',
        'portable_ready':'portable_summary',
        'model_check':'model_summary',
        'scan_bridge':'latest_scan_reports',
        'project_docs':'project_docs_summary',
        'extension_manager':'extension_summary'
    }
    source_key=source_key_map.get(selected.get('id'),'')
    source_summary=source_reports.get(source_key,{}) if source_key else {}
    if selected.get('id')=='scan_bridge':
        latest_scans=foundation_report.get('latest_scan_reports') or []
        source_summary=latest_scans[0] if latest_scans else {}

    detail_checks=[
        {'id':'command_center_loaded','ok':bool(foundation_report.get('ok')),'message':'Command Center foundation report loaded.','path':''},
        {'id':'foundation_selected','ok':True,'message':'Requested foundation was found.','path':selected.get('id','')},
        {'id':'status_declared','ok':bool(status),'message':'Foundation status is declared.','path':status},
        {'id':'health_declared','ok':bool(selected.get('health')),'message':'Foundation health label is declared.','path':selected.get('health','')},
        {'id':'source_declared','ok':bool(selected.get('source')),'message':'Foundation source is declared.','path':selected.get('source','')},
        {'id':'page_declared','ok':bool(selected.get('page')),'message':'Related page is declared.','path':selected.get('page','')},
        {'id':'endpoint_declared','ok':bool(selected.get('endpoint')),'message':'Related endpoint is declared.','path':selected.get('endpoint','')},
        {'id':'metrics_present','ok':isinstance(selected.get('metrics'),dict),'message':'Foundation metrics are present.','path':''},
        {'id':'no_command_detail_side_effects','ok':True,'message':'Command Center Detail performed read-only inspection only.','path':''}
    ]

    detail_ok=all(bool(c.get('ok')) for c in detail_checks)
    health_label='FOUNDATION CLEAR' if status=='clear' else ('FOUNDATION ADVISORY' if status=='advisory' else 'FOUNDATION NEEDS ATTENTION')

    recommended_next=[]
    if status=='clear':
        recommended_next.append({
            'id':'no_action_needed',
            'title':'No action needed',
            'recommendation':'This foundation is clear. Continue normal work.',
            'risk':'low',
            'auto_apply':False
        })
    elif status=='advisory':
        recommended_next.append({
            'id':'advisory_only',
            'title':'Advisory only',
            'recommendation':selected.get('recommended_action','Treat as advisory unless you intentionally choose to act.'),
            'risk':'low',
            'auto_apply':False
        })
    else:
        recommended_next.append({
            'id':'review_foundation',
            'title':'Review foundation',
            'recommendation':selected.get('recommended_action','Open the related page and review the source report.'),
            'risk':'medium',
            'auto_apply':False
        })

    related_paths=[]
    folders=foundation_report.get('folders') or {}
    if selected.get('id')=='repair_shop_foundation':
        related_paths.append({'key':'repair_milestone_freeze','path':folders.get('repair_milestone_freeze',''),'kind':'folder'})
    elif selected.get('id')=='recovery_foundation':
        related_paths.append({'key':'recovery_timeline','path':folders.get('recovery_timeline',''),'kind':'folder'})
    elif selected.get('id')=='scan_bridge':
        related_paths.append({'key':'scan_reports','path':folders.get('scan_reports',''),'kind':'folder'})
        for i,scan in enumerate(foundation_report.get('latest_scan_reports') or []):
            related_paths.append({'key':f'scan_report_{i+1}','path':scan.get('path',''),'kind':'file','exists':True})
    elif selected.get('id') in ('build_verify','env_verify','portable_ready','model_check','project_docs','extension_manager'):
        related_paths.append({'key':'command_center_reports','path':folders.get('command_center_reports',''),'kind':'folder'})
    related_paths.append({'key':'related_page','path':'internal:'+str(selected.get('page','')),'kind':'internal'})
    related_paths.append({'key':'related_endpoint','path':selected.get('endpoint',''),'kind':'endpoint'})

    # Add existence information for real paths.
    checked_paths=[]
    for p in related_paths:
        qpath=p.get('path','')
        item=dict(p)
        if qpath and not qpath.startswith('internal:') and not qpath.startswith('/api/'):
            try:
                pp=Path(qpath)
                item['exists']=pp.exists()
                item['kind']='folder' if pp.exists() and pp.is_dir() else ('file' if pp.exists() else item.get('kind','path'))
                item['size']=pp.stat().st_size if pp.exists() and pp.is_file() else None
                item['modified']=datetime.fromtimestamp(pp.stat().st_mtime).isoformat(timespec='seconds') if pp.exists() else None
            except Exception as e:
                item['exists']=False
                item['error']=str(e)
        checked_paths.append(item)

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Command Center Detail Viewer',
        'read_only':True,
        'report_only':True,
        'detail_ok':detail_ok,
        'health_label':health_label,
        'message':f"Command Center Detail: {selected.get('title','')}",
        'foundation_id':selected.get('id',''),
        'foundation_title':selected.get('title',''),
        'foundation_status':status,
        'foundation_health':selected.get('health',''),
        'foundation_summary':selected.get('summary',''),
        'foundation_source':selected.get('source',''),
        'foundation_page':selected.get('page',''),
        'foundation_endpoint':selected.get('endpoint',''),
        'recommended_action':selected.get('recommended_action',''),
        'metrics':selected.get('metrics') or {},
        'source_key':source_key,
        'source_summary':source_summary,
        'matching_attention':matching_attention,
        'matching_advisory':matching_advisory,
        'recommended_next':recommended_next,
        'detail_checks':detail_checks,
        'related_paths':checked_paths,
        'command_center_summary':foundation_report.get('summary') or {},
        'available_foundations':[{'id':f.get('id'),'title':f.get('title'),'status':f.get('status'),'health':f.get('health')} for f in foundations],
        'safety':{
            'read_only_command_detail':True,
            'no_repair_action':True,
            'no_restore':True,
            'no_rollback':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'command_detail_export_only':True
        }
    }

    if export:
        out=FOLDERS.get('command_center_detail_reports',ROOT/'Reports'/'CommandCenter'/'Details')
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_id=re.sub(r'[^A-Za-z0-9_.-]+','_',selected.get('id','foundation')).strip('_') or 'foundation'
        json_path=out/f'Command_Center_Detail_{safe_id}_{stamp}.json'
        md_path=out/f'Command_Center_Detail_{safe_id}_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Command Center Detail Viewer','',
            f"Created: {report['created']}",
            f"Foundation: **{report['foundation_title']}**",
            f"ID: `{report['foundation_id']}`",
            f"Status: `{status}`",
            f"Health: **{report['foundation_health']}**",
            f"Detail OK: {detail_ok}",
            f"Read only: {report['read_only']}",
            f"Report only: {report['report_only']}",
            '',
            '## Safety','',
            '- Read-only foundation detail.',
            '- No repair action.',
            '- No restore.',
            '- No rollback.',
            '- No overwrite.',
            '- No copy-back.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '',
            '## Summary','',
            f"- Source: {report['foundation_source']}",
            f"- Page: `{report['foundation_page']}`",
            f"- Endpoint: `{report['foundation_endpoint']}`",
            f"- Summary: {report['foundation_summary']}",
            f"- Recommended action: {report['recommended_action']}",
            '',
            '## Metrics',''
        ]
        for k,v in (report.get('metrics') or {}).items():
            lines.append(f"- {k}: {v}")
        lines += ['','## Detail Checks','']
        for c in detail_checks:
            lines.append(f"- [{'PASS' if c.get('ok') else 'FAIL'}] `{c.get('id')}` — {c.get('message')} {c.get('path','')}")
        lines += ['','## Related Paths','']
        for p in checked_paths:
            lines.append(f"- `{p.get('key')}` — `{p.get('path')}` — exists: {p.get('exists','n/a')}")
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def command_center_dashboard_card_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    limit=int(d.get('limit') or 300)
    foundation=command_center_foundation_report({'limit':limit})
    summary=foundation.get('summary') or {}
    foundations=foundation.get('foundations') or []
    attention=foundation.get('attention') or []
    advisories=foundation.get('advisories') or []
    recommendations=foundation.get('recommendations') or []

    score=int(summary.get('score') or 0)
    needs_attention=int(summary.get('needs_attention') or 0)
    advisory=int(summary.get('advisory') or 0)
    clear=int(summary.get('clear') or 0)
    total=int(summary.get('foundations') or len(foundations) or 0)

    if needs_attention:
        card_label='COMMAND CENTER NEEDS ATTENTION'
        card_state='needs_attention'
    elif advisory:
        card_label='COMMAND CENTER READY — ADVISORIES ONLY'
        card_state='advisory'
    else:
        card_label='COMMAND CENTER CLEAR — ALL FOUNDATIONS READY'
        card_state='clear'

    top_foundations=[]
    for f in foundations:
        top_foundations.append({
            'id':f.get('id',''),
            'title':f.get('title',''),
            'status':f.get('status',''),
            'health':f.get('health',''),
            'summary':f.get('summary',''),
            'page':f.get('page',''),
            'endpoint':f.get('endpoint','')
        })

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Command Center Dashboard Card',
        'read_only':True,
        'report_only':True,
        'healthy':bool(foundation.get('command_ready')),
        'command_ready':bool(foundation.get('command_ready')),
        'fully_clear':bool(foundation.get('fully_clear')),
        'card_state':card_state,
        'health_label':card_label,
        'message':f'Command Center Dashboard Card: {card_label}',
        'score':score,
        'foundations_total':total,
        'foundations_clear':clear,
        'foundations_advisory':advisory,
        'foundations_needs_attention':needs_attention,
        'repair_shop_foundation':summary.get('repair_shop_foundation',''),
        'recovery_foundation':summary.get('recovery_foundation',''),
        'latest_repair_action':summary.get('latest_repair_action',''),
        'latest_recovery_event':summary.get('latest_recovery_event',''),
        'primary_advisory':advisories[0] if advisories else {},
        'primary_attention':attention[0] if attention else {},
        'attention':attention,
        'advisories':advisories,
        'recommendations':recommendations,
        'foundations':top_foundations,
        'summary':summary,
        'folders':{
            'command_center_reports':str(FOLDERS.get('command_center_reports',ROOT/'Reports'/'CommandCenter')),
            'command_center_detail_reports':str(FOLDERS.get('command_center_detail_reports',ROOT/'Reports'/'CommandCenter'/'Details')),
            'command_center_card_reports':str(FOLDERS.get('command_center_card_reports',ROOT/'Reports'/'CommandCenter'/'DashboardCards'))
        },
        'safety':{
            'read_only_dashboard_card':True,
            'no_repair_action':True,
            'no_restore':True,
            'no_rollback':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'dashboard_card_export_only':True
        }
    }

    if export:
        out=FOLDERS.get('command_center_card_reports',ROOT/'Reports'/'CommandCenter'/'DashboardCards')
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=out/f'Command_Center_Dashboard_Card_{stamp}.json'
        md_path=out/f'Command_Center_Dashboard_Card_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Command Center Dashboard Card','',
            f"Created: {report['created']}",
            f"Health: **{card_label}**",
            f"Command ready: {report['command_ready']}",
            f"Fully clear: {report['fully_clear']}",
            f"Score: {score}",
            '',
            '## Summary','',
            f"- Foundations: {clear}/{total} clear",
            f"- Advisory: {advisory}",
            f"- Needs attention: {needs_attention}",
            f"- Repair Shop Foundation: {report['repair_shop_foundation']}",
            f"- Recovery Foundation: {report['recovery_foundation']}",
            f"- Latest repair action: {report['latest_repair_action']}",
            f"- Latest recovery event: {report['latest_recovery_event']}",
            '',
            '## Foundations',''
        ]
        for f in top_foundations:
            lines += [
                f"### {f.get('title')}",
                f"- ID: `{f.get('id')}`",
                f"- Status: `{f.get('status')}`",
                f"- Health: {f.get('health')}",
                f"- Summary: {f.get('summary')}",
                ''
            ]
        lines += ['## Safety','',
            '- Read-only dashboard card.',
            '- No repair action.',
            '- No restore.',
            '- No rollback.',
            '- No overwrite.',
            '- No copy-back.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.'
        ]
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def command_center_archive_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    limit=int(d.get('limit') or 200)

    folders=[
        ('foundation_reports',FOLDERS.get('command_center_reports',ROOT/'Reports'/'CommandCenter')),
        ('detail_reports',FOLDERS.get('command_center_detail_reports',ROOT/'Reports'/'CommandCenter'/'Details')),
        ('dashboard_card_reports',FOLDERS.get('command_center_card_reports',ROOT/'Reports'/'CommandCenter'/'DashboardCards')),
    ]

    reports=[]
    errors=[]

    def classify_report(path, data, bucket):
        name=path.name
        title=data.get('title','')
        if bucket=='detail_reports' or 'Command_Center_Detail_' in name or 'Detail Viewer' in title:
            rtype='foundation_detail'
        elif bucket=='dashboard_card_reports' or 'Dashboard_Card' in name or 'Dashboard Card' in title:
            rtype='dashboard_card'
        else:
            rtype='foundation'
        return rtype

    def safe_int(v, default=0):
        try:
            return int(v)
        except Exception:
            return default

    for bucket,folder in folders:
        try:
            folder=Path(folder)
            if not folder.exists():
                continue
            files=sorted([p for p in folder.glob('*.json') if p.is_file()], key=lambda p:p.stat().st_mtime, reverse=True)
            for p in files[:limit]:
                try:
                    data=json.loads(p.read_text(encoding='utf-8',errors='replace'))
                    rtype=classify_report(p,data,bucket)
                    summary=data.get('summary') or data.get('command_center_summary') or {}
                    item={
                        'type':rtype,
                        'bucket':bucket,
                        'name':p.name,
                        'path':str(p),
                        'created':data.get('created',''),
                        'modified':datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec='seconds'),
                        'title':data.get('title',''),
                        'health_label':data.get('health_label',''),
                        'ok':bool(data.get('ok',False)),
                        'read_only':bool(data.get('read_only',False)),
                        'report_only':bool(data.get('report_only',False)),
                        'command_ready':bool(data.get('command_ready',False)),
                        'fully_clear':bool(data.get('fully_clear',False)),
                        'score':safe_int(data.get('score',summary.get('score',0))),
                        'foundations_total':safe_int(data.get('foundations_total',summary.get('foundations',0))),
                        'foundations_clear':safe_int(data.get('foundations_clear',summary.get('clear',0))),
                        'foundations_advisory':safe_int(data.get('foundations_advisory',summary.get('advisory',0))),
                        'foundations_needs_attention':safe_int(data.get('foundations_needs_attention',summary.get('needs_attention',0))),
                        'foundation_id':data.get('foundation_id',''),
                        'foundation_title':data.get('foundation_title',''),
                        'foundation_status':data.get('foundation_status',''),
                        'detail_ok':data.get('detail_ok',None),
                        'latest_repair_action':data.get('latest_repair_action',summary.get('latest_repair_action','')),
                        'latest_recovery_event':data.get('latest_recovery_event',summary.get('latest_recovery_event','')),
                        'message':data.get('message',''),
                        'source_summary':summary
                    }
                    if rtype=='foundation':
                        item['command_ready']=bool(data.get('command_ready',summary.get('command_ready',False)))
                        item['fully_clear']=bool(data.get('fully_clear',summary.get('fully_clear',False)))
                    reports.append(item)
                except Exception as e:
                    errors.append({'path':str(p),'message':str(e)})
        except Exception as e:
            errors.append({'folder':str(folder),'message':str(e)})

    reports=sorted(reports, key=lambda x: x.get('created') or x.get('modified') or '', reverse=True)
    foundation_reports=[r for r in reports if r.get('type')=='foundation']
    detail_reports=[r for r in reports if r.get('type')=='foundation_detail']
    dashboard_reports=[r for r in reports if r.get('type')=='dashboard_card']

    latest_foundation=foundation_reports[0] if foundation_reports else {}
    latest_detail=detail_reports[0] if detail_reports else {}
    latest_dashboard=dashboard_reports[0] if dashboard_reports else {}

    timeline=[]
    for r in reports[:limit]:
        timeline.append({
            'created':r.get('created') or r.get('modified',''),
            'type':r.get('type',''),
            'name':r.get('name',''),
            'health_label':r.get('health_label',''),
            'score':r.get('score',0),
            'command_ready':r.get('command_ready',False),
            'foundation_id':r.get('foundation_id',''),
            'foundation_status':r.get('foundation_status',''),
            'path':r.get('path','')
        })

    # Trend based on foundation/dashboard reports only.
    trend_source=[r for r in reports if r.get('type') in ('foundation','dashboard_card')]
    trend_source=sorted(trend_source, key=lambda x: x.get('created') or x.get('modified') or '')
    trend=[]
    for r in trend_source[-20:]:
        trend.append({
            'created':r.get('created') or r.get('modified',''),
            'type':r.get('type',''),
            'health_label':r.get('health_label',''),
            'score':r.get('score',0),
            'clear':r.get('foundations_clear',0),
            'advisory':r.get('foundations_advisory',0),
            'needs_attention':r.get('foundations_needs_attention',0),
            'command_ready':r.get('command_ready',False)
        })

    needs_attention_count=sum(1 for r in trend_source if int(r.get('foundations_needs_attention') or 0)>0 or 'NEEDS ATTENTION' in (r.get('health_label','')))
    advisory_count=sum(1 for r in trend_source if int(r.get('foundations_advisory') or 0)>0 or 'ADVISORIES' in (r.get('health_label','')))
    clear_count=sum(1 for r in trend_source if int(r.get('foundations_needs_attention') or 0)==0 and int(r.get('foundations_advisory') or 0)==0 and bool(r.get('command_ready')))

    latest_ready=bool(latest_foundation.get('command_ready') or latest_dashboard.get('command_ready'))
    latest_attention=int((latest_dashboard or latest_foundation).get('foundations_needs_attention') or 0)
    latest_advisory=int((latest_dashboard or latest_foundation).get('foundations_advisory') or 0)
    health_label='COMMAND CENTER ARCHIVE HEALTHY'
    if latest_attention:
        health_label='COMMAND CENTER ARCHIVE SHOWS ATTENTION'
    elif latest_advisory:
        health_label='COMMAND CENTER ARCHIVE HEALTHY — ADVISORIES ONLY'

    summary={
        'reports':len(reports),
        'foundation_reports':len(foundation_reports),
        'dashboard_card_reports':len(dashboard_reports),
        'detail_reports':len(detail_reports),
        'errors':len(errors),
        'latest_foundation_report':latest_foundation.get('name',''),
        'latest_foundation_health':latest_foundation.get('health_label',''),
        'latest_dashboard_report':latest_dashboard.get('name',''),
        'latest_dashboard_health':latest_dashboard.get('health_label',''),
        'latest_detail_report':latest_detail.get('name',''),
        'latest_detail_foundation':latest_detail.get('foundation_id',''),
        'latest_detail_status':latest_detail.get('foundation_status',''),
        'latest_score':(latest_dashboard or latest_foundation).get('score',0),
        'latest_clear':(latest_dashboard or latest_foundation).get('foundations_clear',0),
        'latest_advisory':latest_advisory,
        'latest_needs_attention':latest_attention,
        'latest_command_ready':latest_ready,
        'trend_clear_reports':clear_count,
        'trend_advisory_reports':advisory_count,
        'trend_attention_reports':needs_attention_count,
        'latest_repair_action':(latest_dashboard or latest_foundation).get('latest_repair_action',''),
        'latest_recovery_event':(latest_dashboard or latest_foundation).get('latest_recovery_event','')
    }

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Command Center History / Archive Viewer',
        'read_only':True,
        'report_only':True,
        'healthy':len(errors)==0 and latest_attention==0,
        'health_label':health_label,
        'message':f'Command Center Archive: {health_label}',
        'summary':summary,
        'latest_foundation':latest_foundation,
        'latest_dashboard':latest_dashboard,
        'latest_detail':latest_detail,
        'timeline':timeline,
        'trend':trend,
        'reports':reports[:limit],
        'errors':errors,
        'folders':{
            'command_center_reports':str(FOLDERS.get('command_center_reports',ROOT/'Reports'/'CommandCenter')),
            'command_center_detail_reports':str(FOLDERS.get('command_center_detail_reports',ROOT/'Reports'/'CommandCenter'/'Details')),
            'command_center_card_reports':str(FOLDERS.get('command_center_card_reports',ROOT/'Reports'/'CommandCenter'/'DashboardCards')),
            'command_center_archive_reports':str(FOLDERS.get('command_center_archive_reports',ROOT/'Reports'/'CommandCenter'/'Archive'))
        },
        'safety':{
            'read_only_archive_viewer':True,
            'no_repair_action':True,
            'no_restore':True,
            'no_rollback':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'archive_export_only':True
        }
    }

    if export:
        out=FOLDERS.get('command_center_archive_reports',ROOT/'Reports'/'CommandCenter'/'Archive')
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=out/f'Command_Center_Archive_{stamp}.json'
        md_path=out/f'Command_Center_Archive_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Command Center History / Archive Viewer','',
            f"Created: {report['created']}",
            f"Health: **{health_label}**",
            f"Read only: {report['read_only']}",
            f"Report only: {report['report_only']}",
            '',
            '## Safety','',
            '- Read-only archive viewer.',
            '- No repair action.',
            '- No restore.',
            '- No rollback.',
            '- No overwrite.',
            '- No copy-back.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '',
            '## Summary',''
        ]
        for k,v in summary.items():
            lines.append(f"- {k.replace('_',' ').title()}: {v}")
        lines += ['','## Trend','']
        for t in trend:
            lines.append(f"- {t.get('created')} — {t.get('type')} — {t.get('health_label')} — score {t.get('score')} — clear/advisory/attention {t.get('clear')}/{t.get('advisory')}/{t.get('needs_attention')}")
        lines += ['','## Timeline','']
        for t in timeline[:50]:
            lines.append(f"- {t.get('created')} — {t.get('type')} — {t.get('name')} — {t.get('health_label')} — `{t.get('path')}`")
        if errors:
            lines += ['','## Errors','']
            for e in errors:
                lines.append(f"- {e}")
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def command_center_milestone_freeze_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    limit=int(d.get('limit') or 300)

    foundation=command_center_foundation_report({'limit':limit})
    detail=command_center_detail_report({'foundation_id':'repair_shop_foundation','limit':limit})
    dashboard=command_center_dashboard_card_report({'limit':limit})
    archive=command_center_archive_report({'limit':limit})

    fsum=foundation.get('summary') or {}
    asum=archive.get('summary') or {}

    modules=[
        {
            'version':'v10.10.0',
            'name':'Command Center Foundation',
            'status':'complete_proven' if foundation.get('ok') and foundation.get('command_ready') and int(fsum.get('needs_attention') or 0)==0 else 'needs_review',
            'proof':'Command Center aggregates foundation health across Repair Shop, Recovery, Build, Env, Portable Ready, Model Check, Scan Bridge, Project Docs, and Extension Manager.',
            'endpoint':'/api/command_center/foundation',
            'page':'commandcenter',
            'read_only':True,
            'health':foundation.get('health_label','')
        },
        {
            'version':'v10.10.1',
            'name':'Command Center Detail Viewer',
            'status':'complete_proven' if detail.get('ok') and detail.get('detail_ok') else 'needs_review',
            'proof':'A selected foundation can be inspected with status, health, metrics, source, page, endpoint, related paths, and safety contract.',
            'endpoint':'/api/command_center/detail',
            'page':'commanddetail',
            'read_only':True,
            'health':detail.get('health_label','')
        },
        {
            'version':'v10.10.2',
            'name':'Command Center Dashboard Card',
            'status':'complete_proven' if dashboard.get('ok') and dashboard.get('command_ready') and int(dashboard.get('foundations_needs_attention') or 0)==0 else 'needs_review',
            'proof':'Command Bridge can display Command Center health, score, clear/advisory/attention counts, latest repair action, and latest recovery event.',
            'endpoint':'/api/command_center/dashboard_card',
            'page':'dash',
            'read_only':True,
            'health':dashboard.get('health_label','')
        },
        {
            'version':'v10.10.3',
            'name':'Command Center History / Archive Viewer',
            'status':'complete_proven' if archive.get('ok') and archive.get('healthy') and int(asum.get('errors') or 0)==0 else 'needs_review',
            'proof':'Command Center archive can scan foundation/detail/dashboard reports, build a timeline and trend, and report archive errors.',
            'endpoint':'/api/command_center/archive',
            'page':'commandarchive',
            'read_only':True,
            'health':archive.get('health_label','')
        }
    ]

    problems=[]
    for obj_name,obj in [('foundation',foundation),('detail',detail),('dashboard',dashboard),('archive',archive)]:
        if not obj.get('ok'):
            problems.append({'source':obj_name,'message':obj.get('message','not ok')})
    for m in modules:
        if m.get('status')!='complete_proven':
            problems.append({'source':m.get('version'),'message':m.get('name')+' is not marked complete/proven.'})

    advisory_items=[]
    for a in foundation.get('advisories') or []:
        advisory_items.append({
            'id':a.get('id',''),
            'title':a.get('title',''),
            'summary':a.get('summary',''),
            'recommended_action':a.get('recommended_action',''),
            'safe_to_ignore':True
        })
    if int(asum.get('dashboard_card_reports') or 0)==0:
        advisory_items.append({
            'id':'dashboard_card_exports_optional',
            'title':'Dashboard card exports are optional',
            'summary':'Archive currently found no dashboard-card JSON exports. This is not a failure if the card visibly loads on Command Bridge.',
            'recommended_action':'Export a dashboard card report only when you want archival evidence.',
            'safe_to_ignore':True
        })

    freeze_ready=bool(
        not problems and
        foundation.get('command_ready') and
        int(fsum.get('needs_attention') or 0)==0 and
        int(fsum.get('build_verify_problems') or 0)==0 and
        int(fsum.get('env_required_problems') or 0)==0 and
        int(fsum.get('portable_blockers') or 0)==0 and
        int(fsum.get('portable_warnings') or 0)==0 and
        int(fsum.get('true_model_duplicate_groups') or 0)==0 and
        int(fsum.get('project_docs_problems') or 0)==0 and
        int(fsum.get('extension_problems') or 0)==0 and
        int(asum.get('errors') or 0)==0 and
        int(asum.get('latest_needs_attention') or 0)==0
    )

    if freeze_ready and int(fsum.get('advisory') or 0)>0:
        health_label='COMMAND CENTER FOUNDATION FROZEN — COMPLETE / PROVEN — ADVISORIES ONLY'
    elif freeze_ready:
        health_label='COMMAND CENTER FOUNDATION FROZEN — COMPLETE / PROVEN'
    else:
        health_label='COMMAND CENTER FREEZE NEEDS REVIEW'

    recommendations=[
        {
            'id':'freeze_command_center_foundation',
            'title':'Freeze v10.10.x Command Center Foundation',
            'recommendation':'Treat v10.10.0 through v10.10.3 as the proven Command Center foundation.',
            'status':'recommended' if freeze_ready else 'blocked_until_review',
            'risk':'low',
            'auto_apply':False
        },
        {
            'id':'keep_optional_tools_advisory',
            'title':'Keep optional Repair Bay tools advisory',
            'recommendation':'Optional tools should remain manual and should not be installed automatically by Command Center.',
            'status':'recommended',
            'risk':'low',
            'auto_apply':False
        },
        {
            'id':'move_to_next_foundation',
            'title':'Move to next foundation milestone',
            'recommendation':'Start the next work area as a new milestone rather than adding more complexity to Command Center.',
            'status':'recommended' if freeze_ready else 'wait',
            'risk':'low',
            'auto_apply':False
        }
    ]

    summary={
        'modules':len(modules),
        'modules_complete_proven':sum(1 for m in modules if m.get('status')=='complete_proven'),
        'modules_need_review':sum(1 for m in modules if m.get('status')!='complete_proven'),
        'freeze_ready':freeze_ready,
        'command_center_health':foundation.get('health_label',''),
        'dashboard_card_health':dashboard.get('health_label',''),
        'archive_health':archive.get('health_label',''),
        'score':fsum.get('score',dashboard.get('score',0)),
        'foundations':fsum.get('foundations',dashboard.get('foundations_total',0)),
        'clear':fsum.get('clear',dashboard.get('foundations_clear',0)),
        'advisory':fsum.get('advisory',dashboard.get('foundations_advisory',0)),
        'needs_attention':fsum.get('needs_attention',dashboard.get('foundations_needs_attention',0)),
        'command_ready':foundation.get('command_ready',False),
        'fully_clear':foundation.get('fully_clear',False),
        'archive_reports':asum.get('reports',0),
        'archive_foundation_reports':asum.get('foundation_reports',0),
        'archive_dashboard_card_reports':asum.get('dashboard_card_reports',0),
        'archive_detail_reports':asum.get('detail_reports',0),
        'archive_errors':asum.get('errors',0),
        'trend_attention_reports':asum.get('trend_attention_reports',0),
        'latest_repair_action':fsum.get('latest_repair_action',dashboard.get('latest_repair_action','')),
        'latest_recovery_event':fsum.get('latest_recovery_event',dashboard.get('latest_recovery_event','')),
        'repair_shop_foundation':fsum.get('repair_shop_foundation',''),
        'recovery_foundation':fsum.get('recovery_foundation','')
    }

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Command Center Milestone Freeze',
        'read_only':True,
        'report_only':True,
        'healthy':freeze_ready,
        'freeze_ready':freeze_ready,
        'health_label':health_label,
        'message':f'Command Center Milestone Freeze: {health_label}',
        'milestone':'v10.10.x Command Center Foundation',
        'version_range':'v10.10.0 through v10.10.3',
        'summary':summary,
        'modules':modules,
        'advisories':advisory_items,
        'recommendations':recommendations,
        'problems':problems,
        'source_reports':{
            'foundation_summary':fsum,
            'dashboard_card_summary':{
                'health_label':dashboard.get('health_label',''),
                'score':dashboard.get('score',0),
                'foundations_total':dashboard.get('foundations_total',0),
                'foundations_clear':dashboard.get('foundations_clear',0),
                'foundations_advisory':dashboard.get('foundations_advisory',0),
                'foundations_needs_attention':dashboard.get('foundations_needs_attention',0),
                'command_ready':dashboard.get('command_ready',False)
            },
            'detail_summary':{
                'detail_ok':detail.get('detail_ok',False),
                'foundation_id':detail.get('foundation_id',''),
                'foundation_status':detail.get('foundation_status',''),
                'foundation_health':detail.get('foundation_health','')
            },
            'archive_summary':asum
        },
        'folders':{
            'command_center_reports':str(FOLDERS.get('command_center_reports',ROOT/'Reports'/'CommandCenter')),
            'command_center_detail_reports':str(FOLDERS.get('command_center_detail_reports',ROOT/'Reports'/'CommandCenter'/'Details')),
            'command_center_card_reports':str(FOLDERS.get('command_center_card_reports',ROOT/'Reports'/'CommandCenter'/'DashboardCards')),
            'command_center_archive_reports':str(FOLDERS.get('command_center_archive_reports',ROOT/'Reports'/'CommandCenter'/'Archive')),
            'command_center_milestone_freeze':str(FOLDERS.get('command_center_milestone_freeze',ROOT/'Reports'/'CommandCenter'/'MilestoneFreeze'))
        },
        'safety':{
            'scan_first':True,
            'report_second':True,
            'ask_before_action':True,
            'read_only_milestone_freeze':True,
            'no_repair_action':True,
            'no_restore':True,
            'no_rollback':True,
            'no_overwrite':True,
            'no_copy_back':True,
            'no_delete':True,
            'no_install':True,
            'no_model_cleanup':True,
            'milestone_freeze_export_only':True
        }
    }

    if export:
        out=FOLDERS.get('command_center_milestone_freeze',ROOT/'Reports'/'CommandCenter'/'MilestoneFreeze')
        out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=out/f'Command_Center_Milestone_Freeze_{stamp}.json'
        md_path=out/f'Command_Center_Milestone_Freeze_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Command Center Milestone Freeze','',
            f"Created: {report['created']}",
            f"Milestone: **{report['milestone']}**",
            f"Version range: {report['version_range']}",
            f"Health: **{health_label}**",
            f"Freeze ready: {freeze_ready}",
            f"Read only: {report['read_only']}",
            f"Report only: {report['report_only']}",
            '',
            '## Safety','',
            '- Scan first.',
            '- Report second.',
            '- Ask before action.',
            '- Read-only milestone freeze report.',
            '- No repair action.',
            '- No restore.',
            '- No rollback.',
            '- No overwrite.',
            '- No copy-back.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '',
            '## Summary',''
        ]
        for k,v in summary.items():
            lines.append(f"- {k.replace('_',' ').title()}: {v}")
        lines += ['','## Proven Modules','']
        for m in modules:
            lines += [
                f"### {m.get('version')} — {m.get('name')}",
                '',
                f"- Status: `{m.get('status')}`",
                f"- Health: {m.get('health')}",
                f"- Endpoint: `{m.get('endpoint')}`",
                f"- Page: `{m.get('page')}`",
                f"- Proof: {m.get('proof')}",
                ''
            ]
        lines += ['','## Advisories','']
        if advisory_items:
            for a in advisory_items:
                lines.append(f"- `{a.get('id')}` — {a.get('title')} — {a.get('summary')} — {a.get('recommended_action')}")
        else:
            lines.append('- None.')
        lines += ['','## Recommendations','']
        for r in recommendations:
            lines.append(f"- `{r.get('id')}` — {r.get('title')} — {r.get('status')} — {r.get('recommendation')}")
        lines += ['','## Problems','']
        if problems:
            for p in problems:
                lines.append(f"- {p}")
        else:
            lines.append('- None.')
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}

    return report



def kayock_writer_foundation_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    writer_root=ROOT/'Departments'/'KayockWriter'
    legacy_novel=ROOT/'NovelForge'
    legacy_dept=ROOT/'Departments'/'NovelForge'
    story_projects=ROOT/'Projects'/'KayockWriter'
    writer_reports=FOLDERS.get('kayock_writer_reports',ROOT/'Reports'/'KayockWriter')
    foundation_reports=FOLDERS.get('kayock_writer_foundation_reports',ROOT/'Reports'/'KayockWriter'/'Foundation')

    module_plan=[
        {'id':'story_forge','name':'Story Forge','status':'planned_foundation','purpose':'Novels, short stories, scripts, CYOA, scene drafting, chapter planning, and narrative development.','read_only_now':True,'future_writes':'Story project Markdown and JSON files only, after explicit user action.'},
        {'id':'poetry_studio','name':'Poetry Studio','status':'planned_foundation','purpose':'Poem Creator and Poem Polisher for theme, emotion, poetic form, rhythm, imagery, line breaks, and preserving the writer voice.','read_only_now':True,'future_writes':'Poetry drafts and polish reports only, after explicit user action.'},
        {'id':'codex','name':'Codex','status':'already_conceptualized','purpose':'Characters, lore, factions, artifacts, locations, prophecy, reader knowledge, author knowledge, and canon notes.','read_only_now':True,'future_writes':'Codex entries only, after explicit user action.'},
        {'id':'timeline','name':'Timeline','status':'already_conceptualized','purpose':'Book, chapter, scene, flashback, prophecy, and cross-series chronology.','read_only_now':True,'future_writes':'Timeline records only, after explicit user action.'},
        {'id':'continuity','name':'Continuity','status':'already_conceptualized','purpose':'Canon checks, contradiction tracking, unresolved setup/payoff tracking, and author memory.','read_only_now':True,'future_writes':'Continuity reports only, after explicit user action.'},
        {'id':'mystery_tracker','name':'Mystery Tracker','status':'already_conceptualized','purpose':'Unresolved mysteries, clues, reveals, prophecy fragments, and payoff status.','read_only_now':True,'future_writes':'Mystery tracker records only, after explicit user action.'},
        {'id':'story_bible_export','name':'Story Bible Export','status':'already_conceptualized','purpose':'Export a readable project bible from Codex, Timeline, Continuity, and project notes.','read_only_now':True,'future_writes':'Exported story-bible Markdown only, after explicit user action.'}
    ]
    naming_decisions=[
        {'id':'rename_novel_forge','decision':'Rename Novel Forge to Kayock Writer as the main creative writing department.','status':'locked_in','notes':'Novel Forge becomes legacy/internal wording while Kayock Writer becomes the public department name.'},
        {'id':'story_forge_module','decision':'Use Story Forge as the narrative-writing module inside Kayock Writer.','status':'locked_in','notes':'Story Forge covers novels, short stories, scripts, CYOA, narrative drafting, and scene/chapter work.'},
        {'id':'poetry_studio_module','decision':'Add Poetry Studio with Poem Creator and Poem Polisher.','status':'locked_in','notes':'Poetry work supports creation and polishing while preserving the writer voice.'},
        {'id':'markdown_source_of_truth','decision':'Keep Markdown as the long-term portable source of truth.','status':'locked_in','notes':'Future storage should remain portable, inspectable, and friendly to Obsidian or other tools.'},
        {'id':'provider_toggle','decision':'Preserve Local Mode and Cloud Mode as a future provider toggle.','status':'planned','notes':'Local Mode for private canon/manuscripts; Cloud Mode for public-safe research and critique.'}
    ]
    flagship_universe={'id':'slipping_into_darkness','title':'Slipping into Darkness','status':'flagship_demo_universe','book_1':'Anthony learns the prophecy; Kayock dies; Jokaya kills him; Anthony stops Jokaya; Anthony learns his ex has been turned.','book_2':'Anthony hunts the ex, learns who she has become, defeats her, discovers Jokaya sanctuary clues, follows Olmec/Croatoan/Crystal Skull threads.','use':'Demonstration universe for Codex, Timeline, Continuity, Mystery Tracker, and Story Bible export.'}
    path_checks=[]
    for key,p in [('writer_department_root',writer_root),('legacy_novel_forge_root',legacy_novel),('legacy_novel_forge_department',legacy_dept),('writer_projects_root',story_projects),('writer_reports_root',writer_reports),('writer_foundation_reports',foundation_reports)]:
        item={'key':key,'path':str(p),'exists':False,'kind':'missing','read_only_check':True}
        try:
            item['exists']=p.exists(); item['kind']='folder' if p.exists() and p.is_dir() else ('file' if p.exists() else 'missing')
            item['modified']=datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec='seconds') if p.exists() else ''
        except Exception as e:
            item['error']=str(e)
        path_checks.append(item)
    safety={'read_only_writer_foundation':True,'no_story_file_mutation':True,'no_rename_performed':True,'no_migration_performed':True,'no_overwrite':True,'no_delete':True,'no_install':True,'no_model_cleanup':True,'foundation_export_only':True,'future_writes_require_user_approval':True}
    checks=[
        {'id':'name_locked','ok':True,'message':'Kayock Writer is the selected department name.'},
        {'id':'module_plan_present','ok':len(module_plan)>=7,'message':'Core Kayock Writer module plan is present.'},
        {'id':'poetry_studio_present','ok':any(m.get('id')=='poetry_studio' for m in module_plan),'message':'Poetry Studio is included.'},
        {'id':'story_forge_present','ok':any(m.get('id')=='story_forge' for m in module_plan),'message':'Story Forge is included.'},
        {'id':'codex_present','ok':any(m.get('id')=='codex' for m in module_plan),'message':'Codex is included.'},
        {'id':'flagship_universe_declared','ok':bool(flagship_universe.get('title')),'message':'Flagship demo universe is declared.'},
        {'id':'read_only_scope','ok':all(safety.values()),'message':'Foundation scope is read-only/report-only.'}
    ]
    recommendations=[
        {'id':'start_kayock_writer_foundation','title':'Start Kayock Writer as the new creative writing foundation','recommendation':'Treat this as the beginning of v10.11.x. Keep Novel Forge as legacy wording while the interface transitions to Kayock Writer.','risk':'low','auto_apply':False},
        {'id':'next_story_forge_shell','title':'Build Story Forge Shell next','recommendation':'Create a read-only Story Forge overview with project list, scene/chapter plan, and future explicit-save workflow.','risk':'low','auto_apply':False},
        {'id':'poetry_studio_after_story_shell','title':'Add Poetry Studio after Story Forge shell','recommendation':'Add Poem Creator and Poem Polisher as separate cards after the writer foundation is stable.','risk':'low','auto_apply':False},
        {'id':'do_not_migrate_automatically','title':'Do not auto-migrate Novel Forge files','recommendation':'Any rename, folder creation, or migration should be a later explicit approved action with preview and backup.','risk':'low','auto_apply':False}
    ]
    healthy=all(c.get('ok') for c in checks)
    summary={'modules':len(module_plan),'checks':len(checks),'checks_passed':sum(1 for c in checks if c.get('ok')),'problems':sum(1 for c in checks if not c.get('ok')),'naming_decisions':len(naming_decisions),'path_checks':len(path_checks),'existing_paths':sum(1 for p in path_checks if p.get('exists')),'flagship_universe':flagship_universe.get('title',''),'foundation_ready':healthy,'read_only':True,'report_only':True}
    report={'ok':True,'created':now(),'title':'Kayock Writer Foundation','read_only':True,'report_only':True,'healthy':healthy,'foundation_ready':healthy,'health_label':'KAYOCK WRITER FOUNDATION READY','message':'Kayock Writer Foundation: KAYOCK WRITER FOUNDATION READY','milestone':'v10.11.0 Kayock Writer Foundation','summary':summary,'module_plan':module_plan,'naming_decisions':naming_decisions,'flagship_universe':flagship_universe,'path_checks':path_checks,'checks':checks,'recommendations':recommendations,'folders':{'writer_department_root':str(writer_root),'writer_projects_root':str(story_projects),'writer_reports':str(writer_reports),'writer_foundation_reports':str(foundation_reports)},'safety':safety}
    if export:
        out=foundation_reports; out.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=out/f'Kayock_Writer_Foundation_{stamp}.json'; md_path=out/f'Kayock_Writer_Foundation_{stamp}.md'
        jwrite(json_path,report)
        lines=['# Kayock Writer Foundation','',f"Created: {report['created']}",f"Milestone: **{report['milestone']}**",f"Health: **{report['health_label']}**",f"Foundation ready: {healthy}",f"Read only: {report['read_only']}",f"Report only: {report['report_only']}",'','## Safety','','- Read-only Kayock Writer foundation report.','- No story-file mutation.','- No rename performed.','- No migration performed.','- No overwrite.','- No delete.','- No install.','- No model cleanup.','- Future writes require explicit user approval.','','## Summary','']
        for k,v in summary.items(): lines.append(f"- {k.replace('_',' ').title()}: {v}")
        lines += ['','## Module Plan','']
        for m in module_plan:
            lines += [f"### {m.get('name')}",f"- ID: `{m.get('id')}`",f"- Status: `{m.get('status')}`",f"- Purpose: {m.get('purpose')}",f"- Read only now: {m.get('read_only_now')}",f"- Future writes: {m.get('future_writes')}",'']
        lines += ['','## Naming Decisions','']
        for n in naming_decisions: lines.append(f"- `{n.get('id')}` — {n.get('status')} — {n.get('decision')} {n.get('notes')}")
        lines += ['','## Flagship Universe','',f"- Title: {flagship_universe.get('title')}",f"- Status: {flagship_universe.get('status')}",f"- Book 1: {flagship_universe.get('book_1')}",f"- Book 2: {flagship_universe.get('book_2')}",f"- Use: {flagship_universe.get('use')}",'','## Path Checks','']
        for p in path_checks: lines.append(f"- `{p.get('key')}` — `{p.get('path')}` — exists: {p.get('exists')} — kind: {p.get('kind')}")
        lines += ['','## Checks','']
        for c in checks: lines.append(f"- [{'PASS' if c.get('ok') else 'FAIL'}] `{c.get('id')}` — {c.get('message')}")
        lines += ['','## Recommendations','']
        for r in recommendations: lines.append(f"- `{r.get('id')}` — {r.get('title')} — {r.get('recommendation')} — auto apply: {r.get('auto_apply')}")
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(out)}
    return report


def kayock_writer_story_forge_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    limit=int(d.get('limit') or 80)
    foundation=kayock_writer_foundation_report({})
    root=ROOT

    legacy_root=root/'NovelForge'
    writer_projects=root/'Projects'/'KayockWriter'
    writer_department=root/'Departments'/'KayockWriter'
    reports=FOLDERS.get('kayock_writer_story_forge_reports',root/'Reports'/'KayockWriter'/'StoryForge')

    def count_files(folder):
        counts={'markdown':0,'json':0,'text':0,'other':0,'total':0}
        samples=[]
        try:
            if not folder.exists() or not folder.is_dir():
                return counts,samples
            for p in folder.rglob('*'):
                if len(samples)>=12 and counts['total']>=limit:
                    break
                if p.is_file():
                    counts['total']+=1
                    suf=p.suffix.lower()
                    if suf=='.md': counts['markdown']+=1
                    elif suf=='.json': counts['json']+=1
                    elif suf in ('.txt','.text'): counts['text']+=1
                    else: counts['other']+=1
                    if len(samples)<12 and suf in ('.md','.json','.txt','.text'):
                        samples.append({'name':p.name,'path':str(p),'suffix':suf,'modified':datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec='seconds')})
        except Exception as e:
            counts['error']=str(e)
        return counts,samples

    project_roots=[
        {'id':'legacy_novel_forge','title':'Legacy NovelForge','path':legacy_root,'role':'legacy/source candidate'},
        {'id':'kayock_writer_projects','title':'Kayock Writer Projects','path':writer_projects,'role':'future project home'},
        {'id':'kayock_writer_department','title':'Kayock Writer Department','path':writer_department,'role':'future department home'}
    ]

    project_candidates=[]
    for root_info in project_roots:
        p=root_info['path']
        item={'id':root_info['id'],'title':root_info['title'],'role':root_info['role'],'path':str(p),'exists':p.exists(),'kind':'folder' if p.exists() and p.is_dir() else ('file' if p.exists() else 'missing'),'children':[]}
        if p.exists() and p.is_dir():
            counts,samples=count_files(p)
            item['counts']=counts
            item['samples']=samples
            try:
                for child in sorted([c for c in p.iterdir() if c.is_dir()], key=lambda x:x.name.lower())[:20]:
                    ccounts,csamples=count_files(child)
                    item['children'].append({'name':child.name,'path':str(child),'counts':ccounts,'samples':csamples[:5]})
            except Exception as e:
                item['children_error']=str(e)
        else:
            item['counts']={'markdown':0,'json':0,'text':0,'other':0,'total':0}
            item['samples']=[]
        project_candidates.append(item)

    flagship={
        'id':'slipping_into_darkness',
        'title':'Slipping into Darkness',
        'status':'flagship_story_forge_demo',
        'book_1':'Anthony learns the prophecy; Kayock dies; Jokaya kills him; Anthony stops Jokaya; Anthony learns his ex has been turned.',
        'book_2':'Anthony hunts the ex, learns who she has become, defeats her, discovers Jokaya sanctuary clues, follows Olmec/Croatoan/Crystal Skull threads.',
        'story_forge_use':['series overview','book breakdown','chapter planning','scene planning','prophecy/payoff tracking','Codex and Continuity handoff']
    }

    shell_sections=[
        {'id':'project_overview','title':'Project Overview','status':'active_shell','purpose':'Show project title, series, book, premise, current phase, and safe next steps.'},
        {'id':'project_list','title':'Story Project List','status':'read_only_detection','purpose':'Detect legacy and future project homes without moving or creating files.'},
        {'id':'chapter_planner','title':'Chapter Planner','status':'planned_shell','purpose':'Future explicit-save chapter cards with chapter goal, conflict, reveal, and ending hook.'},
        {'id':'scene_planner','title':'Scene Planner','status':'planned_shell','purpose':'Future explicit-save scene cards with POV, location, characters, stakes, beat, and continuity flags.'},
        {'id':'beat_board','title':'Beat Board','status':'planned_shell','purpose':'Future story beats, act structure, clue placement, setup/payoff, and emotional turns.'},
        {'id':'cyoa_script_support','title':'CYOA / Script Support','status':'planned_shell','purpose':'Future branching story and script-friendly planning views.'},
        {'id':'explicit_save_gate','title':'Explicit Save Gate','status':'required_safety','purpose':'All future story writes require preview, target path, and explicit user approval.'}
    ]

    future_actions=[
        {'id':'create_writer_project','title':'Create Kayock Writer Project','available_now':False,'requires_preview':True,'requires_user_approval':True,'writes':'future project folder and manifest only'},
        {'id':'import_legacy_novel_forge','title':'Import Legacy NovelForge Project','available_now':False,'requires_preview':True,'requires_user_approval':True,'writes':'future copied import only; no move/delete'},
        {'id':'save_chapter_plan','title':'Save Chapter Plan','available_now':False,'requires_preview':True,'requires_user_approval':True,'writes':'future chapter Markdown/JSON only'},
        {'id':'save_scene_card','title':'Save Scene Card','available_now':False,'requires_preview':True,'requires_user_approval':True,'writes':'future scene Markdown/JSON only'}
    ]

    checks=[
        {'id':'writer_foundation_loaded','ok':bool(foundation.get('ok')),'message':'Kayock Writer foundation report loaded.'},
        {'id':'story_forge_declared','ok':any(m.get('id')=='story_forge' for m in foundation.get('module_plan',[])),'message':'Story Forge module is declared in Kayock Writer.'},
        {'id':'flagship_declared','ok':bool(flagship.get('title')),'message':'Slipping into Darkness flagship card is declared.'},
        {'id':'sections_present','ok':len(shell_sections)>=7,'message':'Story Forge shell sections are present.'},
        {'id':'project_detection_read_only','ok':True,'message':'Project detection is read-only.'},
        {'id':'future_actions_disabled','ok':all(not a.get('available_now') for a in future_actions),'message':'Future story-write actions are disabled in this shell.'},
        {'id':'no_story_file_mutation','ok':True,'message':'No story files were created, moved, renamed, overwritten, or deleted.'}
    ]

    safety={
        'read_only_story_forge_shell':True,
        'no_story_file_mutation':True,
        'no_project_creation':True,
        'no_legacy_migration':True,
        'no_rename_performed':True,
        'no_overwrite':True,
        'no_delete':True,
        'no_install':True,
        'no_model_cleanup':True,
        'future_writes_require_preview_and_approval':True,
        'shell_export_only':True
    }

    summary={
        'sections':len(shell_sections),
        'future_actions':len(future_actions),
        'future_actions_available_now':sum(1 for a in future_actions if a.get('available_now')),
        'project_roots_checked':len(project_candidates),
        'existing_project_roots':sum(1 for p in project_candidates if p.get('exists')),
        'legacy_novel_forge_exists':legacy_root.exists(),
        'checks':len(checks),
        'checks_passed':sum(1 for c in checks if c.get('ok')),
        'problems':sum(1 for c in checks if not c.get('ok')),
        'foundation_ready':all(c.get('ok') for c in checks),
        'flagship_universe':flagship.get('title',''),
        'read_only':True,
        'report_only':True
    }

    recommendations=[
        {'id':'mark_story_forge_shell_proven','title':'Mark Story Forge Shell proven','recommendation':'Use this as the read-only foundation for Story Forge before adding any save or migration actions.','risk':'low','auto_apply':False},
        {'id':'next_story_project_manifest_preview','title':'Build Story Project Manifest Preview next','recommendation':'Add a preview-only manifest generator for a Kayock Writer story project; no file creation until a later approved action.','risk':'low','auto_apply':False},
        {'id':'keep_legacy_novelforge_read_only','title':'Keep legacy NovelForge read-only','recommendation':'Detect existing NovelForge content, but do not rename, move, or migrate automatically.','risk':'low','auto_apply':False},
        {'id':'poetry_studio_after_story_manifest','title':'Poetry Studio follows Story Forge shell','recommendation':'After Story Forge has a project manifest preview, add Poetry Studio foundation cards.','risk':'low','auto_apply':False}
    ]

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Writer Story Forge Shell',
        'read_only':True,
        'report_only':True,
        'healthy':summary['foundation_ready'],
        'shell_ready':summary['foundation_ready'],
        'health_label':'STORY FORGE SHELL READY',
        'message':'Story Forge Shell: STORY FORGE SHELL READY',
        'milestone':'v10.11.1 Story Forge Shell',
        'summary':summary,
        'flagship':flagship,
        'shell_sections':shell_sections,
        'project_candidates':project_candidates,
        'future_actions':future_actions,
        'checks':checks,
        'recommendations':recommendations,
        'folders':{
            'legacy_novel_forge':str(legacy_root),
            'writer_projects':str(writer_projects),
            'writer_department':str(writer_department),
            'story_forge_reports':str(reports)
        },
        'safety':safety
    }

    if export:
        reports.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=reports/f'Story_Forge_Shell_{stamp}.json'
        md_path=reports/f'Story_Forge_Shell_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Writer Story Forge Shell','',
            f"Created: {report['created']}",
            f"Milestone: **{report['milestone']}**",
            f"Health: **{report['health_label']}**",
            f"Shell ready: {report['shell_ready']}",
            f"Read only: {report['read_only']}",
            f"Report only: {report['report_only']}",
            '',
            '## Safety','',
            '- Read-only Story Forge shell.',
            '- No story-file mutation.',
            '- No project creation.',
            '- No legacy migration.',
            '- No rename performed.',
            '- No overwrite.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '- Future writes require preview and approval.',
            '',
            '## Summary',''
        ]
        for k,v in summary.items():
            lines.append(f"- {k.replace('_',' ').title()}: {v}")
        lines += ['','## Flagship','',f"- Title: {flagship['title']}",f"- Book 1: {flagship['book_1']}",f"- Book 2: {flagship['book_2']}",'','## Shell Sections','']
        for s in shell_sections:
            lines += [f"### {s['title']}",f"- ID: `{s['id']}`",f"- Status: `{s['status']}`",f"- Purpose: {s['purpose']}",'']
        lines += ['## Project Candidates','']
        for p in project_candidates:
            lines.append(f"- `{p['id']}` — `{p['path']}` — exists: {p['exists']} — kind: {p['kind']} — files: {p.get('counts',{}).get('total',0)}")
        lines += ['','## Checks','']
        for c in checks:
            lines.append(f"- [{'PASS' if c.get('ok') else 'FAIL'}] `{c['id']}` — {c['message']}")
        lines += ['','## Recommendations','']
        for r in recommendations:
            lines.append(f"- `{r['id']}` — {r['title']} — {r['recommendation']} — auto apply: {r['auto_apply']}")
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(reports)}

    return report



def kayock_writer_manifest_preview_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    project_id=str(d.get('project_id') or 'slipping_into_darkness').strip().lower().replace(' ','_')
    if project_id in ('','slipping','slipping_into_darkness'):
        project_id='slipping_into_darkness'
        title='Slipping into Darkness'
    else:
        title=str(d.get('title') or project_id.replace('_',' ').title()).strip()

    root=ROOT
    legacy_root=root/'NovelForge'
    legacy_markdown=legacy_root/'Markdown'
    legacy_exports=legacy_root/'Exports'
    proposed_root=root/'Projects'/'KayockWriter'/title.replace(' ','_')
    reports=FOLDERS.get('kayock_writer_manifest_preview_reports',root/'Reports'/'KayockWriter'/'ManifestPreview')

    def file_info(p):
        item={'name':p.name,'path':str(p),'suffix':p.suffix.lower(),'exists':False,'size':0,'modified':''}
        try:
            item['exists']=p.exists()
            if p.exists():
                item['size']=p.stat().st_size
                item['modified']=datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec='seconds')
        except Exception as e:
            item['error']=str(e)
        return item

    legacy_candidates=[]
    candidate_paths=[
        legacy_root/'Slipping_into_Darkness.json',
        legacy_markdown/'Slipping_into_Darkness.md',
        legacy_exports/'Slipping_into_Darkness_Story_Bible_20260707_172721.json',
        legacy_exports/'Slipping_into_Darkness_Story_Bible_20260707_172721.md',
        legacy_exports/'Slipping_into_Darkness_Story_Bible_20260707_172721.txt',
        legacy_root/'Slipping.json',
        legacy_markdown/'Slipping.md'
    ]
    seen=set()
    for p in candidate_paths:
        if str(p).lower() in seen:
            continue
        seen.add(str(p).lower())
        legacy_candidates.append(file_info(p))

    # Broader detection for similarly named files, still read-only.
    try:
        if legacy_root.exists():
            for p in legacy_root.rglob('*'):
                if not p.is_file():
                    continue
                low=p.name.lower()
                if ('slipping' in low or 'darkness' in low or 'story_bible' in low) and str(p).lower() not in seen:
                    seen.add(str(p).lower())
                    legacy_candidates.append(file_info(p))
    except Exception:
        pass

    detected_existing=[x for x in legacy_candidates if x.get('exists')]
    legacy_counts={
        'files_detected':len(detected_existing),
        'json':sum(1 for x in detected_existing if x.get('suffix')=='.json'),
        'markdown':sum(1 for x in detected_existing if x.get('suffix')=='.md'),
        'text':sum(1 for x in detected_existing if x.get('suffix') in ('.txt','.text')),
        'other':sum(1 for x in detected_existing if x.get('suffix') not in ('.json','.md','.txt','.text')),
        'bytes':sum(int(x.get('size') or 0) for x in detected_existing)
    }

    parsed_legacy=[]
    for f in detected_existing:
        if f.get('suffix')=='.json':
            try:
                data=json.loads(Path(f['path']).read_text(encoding='utf-8',errors='replace'))
                parsed_legacy.append({
                    'path':f['path'],
                    'top_level_keys':list(data.keys())[:30] if isinstance(data,dict) else [],
                    'type':type(data).__name__,
                    'parsed':True
                })
            except Exception as e:
                parsed_legacy.append({'path':f['path'],'parsed':False,'error':str(e)})

    proposed_folders=[
        {'id':'project_root','path':str(proposed_root),'purpose':'Main Kayock Writer project folder.'},
        {'id':'source','path':str(proposed_root/'Source'),'purpose':'Copied/imported legacy source files after explicit approval only.'},
        {'id':'markdown','path':str(proposed_root/'Markdown'),'purpose':'Portable manuscript and planning Markdown.'},
        {'id':'chapters','path':str(proposed_root/'Chapters'),'purpose':'Future chapter cards and chapter drafts.'},
        {'id':'scenes','path':str(proposed_root/'Scenes'),'purpose':'Future scene cards and scene drafts.'},
        {'id':'codex','path':str(proposed_root/'Codex'),'purpose':'Characters, lore, factions, artifacts, locations, prophecy, and canon entries.'},
        {'id':'timeline','path':str(proposed_root/'Timeline'),'purpose':'Book, chapter, scene, flashback, and prophecy chronology.'},
        {'id':'continuity','path':str(proposed_root/'Continuity'),'purpose':'Continuity checks, contradictions, setup/payoff, and unresolved threads.'},
        {'id':'mysteries','path':str(proposed_root/'Mysteries'),'purpose':'Mystery tracker, clues, reveals, prophecy fragments, and payoff status.'},
        {'id':'exports','path':str(proposed_root/'Exports'),'purpose':'Story bible, project bible, and shareable exports.'}
    ]

    manifest_preview={
        'api_version':'kayock.writer.project.v1',
        'project_id':project_id,
        'title':title,
        'department':'Kayock Writer',
        'module':'Story Forge',
        'status':'manifest_preview_only',
        'storage':'Markdown source of truth with JSON sidecars where useful',
        'legacy_source':'Z:\\FOXAI\\NovelForge',
        'proposed_project_root':str(proposed_root),
        'flagship_demo':project_id=='slipping_into_darkness',
        'books':[
            {
                'id':'book_1',
                'title':'Book 1',
                'status':'outline_seed',
                'summary':'Anthony learns the prophecy; Kayock dies; Jokaya kills him; Anthony stops Jokaya; Anthony learns his ex has been turned.',
                'chapter_placeholder_count':0,
                'scene_placeholder_count':0
            },
            {
                'id':'book_2',
                'title':'Book 2',
                'status':'outline_seed',
                'summary':'Anthony hunts the ex, learns who she has become, defeats her, discovers Jokaya sanctuary clues, follows Olmec/Croatoan/Crystal Skull threads.',
                'chapter_placeholder_count':0,
                'scene_placeholder_count':0
            }
        ],
        'handoff_points':{
            'codex':['characters','locations','artifacts','prophecy','factions','reader knowledge','author knowledge'],
            'timeline':['book chronology','chapter chronology','flashbacks','prophecy timing','ancient-history threads'],
            'continuity':['canon checks','contradiction flags','setup/payoff','unresolved mystery links'],
            'mystery_tracker':['clues','reveals','prophecy fragments','Crystal Skulls','Croatoan trail','Jokaya sanctuary']
        },
        'provider_mode_plan':{
            'local_mode':'Private canon, lore, manuscript, and story-bible work.',
            'cloud_mode':'Public-safe research, trope review, pacing critique, and fresh-eyes feedback.'
        },
        'detected_legacy_files':legacy_counts
    }

    future_writes=[
        {'id':'create_project_root','target':str(proposed_root),'action':'create folder','enabled_now':False,'requires_preview':True,'requires_user_approval':True},
        {'id':'create_manifest','target':str(proposed_root/'project.kayock-writer.json'),'action':'write manifest JSON','enabled_now':False,'requires_preview':True,'requires_user_approval':True},
        {'id':'create_readme','target':str(proposed_root/'README.md'),'action':'write project README Markdown','enabled_now':False,'requires_preview':True,'requires_user_approval':True},
        {'id':'create_folder_skeleton','target':str(proposed_root),'action':'create Story Forge folder skeleton','enabled_now':False,'requires_preview':True,'requires_user_approval':True},
        {'id':'copy_legacy_sources','target':str(proposed_root/'Source'),'action':'copy selected legacy source files; no move/delete','enabled_now':False,'requires_preview':True,'requires_user_approval':True},
        {'id':'seed_book_outlines','target':str(proposed_root/'Markdown'/'Books.md'),'action':'write Book 1 and Book 2 outline seed','enabled_now':False,'requires_preview':True,'requires_user_approval':True}
    ]

    approval_gate={
        'required_phrase':'CREATE KAYOCK WRITER PROJECT',
        'future_mode':'approved_action_only',
        'preview_required':True,
        'backup_required_before_write':True,
        'copy_not_move_for_legacy_sources':True,
        'no_delete_allowed':True,
        'no_overwrite_without_backup':True,
        'no_automatic_migration':True
    }

    checks=[
        {'id':'story_forge_shell_loaded','ok':bool(kayock_writer_story_forge_report({}).get('ok')),'message':'Story Forge shell report loaded.'},
        {'id':'manifest_preview_generated','ok':bool(manifest_preview.get('project_id')),'message':'Manifest preview was generated.'},
        {'id':'legacy_scan_read_only','ok':True,'message':'Legacy NovelForge scan was read-only.'},
        {'id':'legacy_sources_detected','ok':legacy_counts['files_detected']>0,'message':f"Detected {legacy_counts['files_detected']} legacy source file(s)."},
        {'id':'future_writes_disabled','ok':all(not x.get('enabled_now') for x in future_writes),'message':'All future writes are disabled in preview mode.'},
        {'id':'approval_gate_present','ok':bool(approval_gate.get('required_phrase')),'message':'Approval gate is present for future project creation.'},
        {'id':'no_story_file_mutation','ok':True,'message':'No story files were created, moved, renamed, overwritten, or deleted.'}
    ]

    safety={
        'preview_only':True,
        'read_only_legacy_scan':True,
        'no_project_creation':True,
        'no_story_file_mutation':True,
        'no_legacy_migration':True,
        'no_rename_performed':True,
        'no_overwrite':True,
        'no_delete':True,
        'no_install':True,
        'no_model_cleanup':True,
        'future_writes_require_preview_and_approval':True,
        'manifest_preview_export_only':True
    }

    summary={
        'project_id':project_id,
        'title':title,
        'legacy_files_detected':legacy_counts['files_detected'],
        'legacy_json':legacy_counts['json'],
        'legacy_markdown':legacy_counts['markdown'],
        'legacy_text':legacy_counts['text'],
        'proposed_folders':len(proposed_folders),
        'future_writes':len(future_writes),
        'future_writes_enabled_now':sum(1 for x in future_writes if x.get('enabled_now')),
        'checks':len(checks),
        'checks_passed':sum(1 for c in checks if c.get('ok')),
        'problems':sum(1 for c in checks if not c.get('ok')),
        'preview_ready':all(c.get('ok') for c in checks),
        'proposed_project_root':str(proposed_root),
        'manifest_target':str(proposed_root/'project.kayock-writer.json'),
        'read_only':True,
        'report_only':True
    }

    recommendations=[
        {'id':'mark_manifest_preview_proven','title':'Mark Story Project Manifest Preview proven','recommendation':'Use this as the approved preview shape before building any project-creation action.','risk':'low','auto_apply':False},
        {'id':'next_create_project_gate','title':'Build Create Project Approval Gate next','recommendation':'Add a future approved action that creates the project skeleton only after exact phrase approval and backup preparation.','risk':'medium_low','auto_apply':False},
        {'id':'copy_not_move_legacy','title':'Copy legacy sources, never move automatically','recommendation':'Legacy NovelForge should remain untouched; future imports should copy selected files into Source after approval.','risk':'low','auto_apply':False},
        {'id':'after_gate_add_poetry_studio','title':'Poetry Studio after project gate','recommendation':'Once project skeleton creation is safe, add Poetry Studio foundation cards.','risk':'low','auto_apply':False}
    ]

    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Writer Story Project Manifest Preview',
        'read_only':True,
        'report_only':True,
        'healthy':summary['preview_ready'],
        'preview_ready':summary['preview_ready'],
        'health_label':'STORY PROJECT MANIFEST PREVIEW READY',
        'message':'Story Project Manifest Preview: STORY PROJECT MANIFEST PREVIEW READY',
        'milestone':'v10.11.2 Story Project Manifest Preview',
        'summary':summary,
        'manifest_preview':manifest_preview,
        'legacy_candidates':legacy_candidates,
        'parsed_legacy':parsed_legacy,
        'proposed_folders':proposed_folders,
        'future_writes':future_writes,
        'approval_gate':approval_gate,
        'checks':checks,
        'recommendations':recommendations,
        'folders':{
            'legacy_novel_forge':str(legacy_root),
            'proposed_project_root':str(proposed_root),
            'manifest_preview_reports':str(reports)
        },
        'safety':safety
    }

    if export:
        reports.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=reports/f'Story_Project_Manifest_Preview_{project_id}_{stamp}.json'
        md_path=reports/f'Story_Project_Manifest_Preview_{project_id}_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Writer Story Project Manifest Preview','',
            f"Created: {report['created']}",
            f"Milestone: **{report['milestone']}**",
            f"Health: **{report['health_label']}**",
            f"Preview ready: {report['preview_ready']}",
            f"Project: **{title}**",
            f"Project ID: `{project_id}`",
            '',
            '## Safety','',
            '- Preview only.',
            '- Read-only legacy scan.',
            '- No project creation.',
            '- No story-file mutation.',
            '- No legacy migration.',
            '- No rename performed.',
            '- No overwrite.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '- Future writes require preview and approval.',
            '',
            '## Summary',''
        ]
        for k,v in summary.items():
            lines.append(f"- {k.replace('_',' ').title()}: {v}")
        lines += ['','## Proposed Manifest','', '```json', json.dumps(manifest_preview,indent=2), '```', '', '## Legacy Sources','']
        for f in detected_existing:
            lines.append(f"- `{f.get('suffix')}` — `{f.get('path')}` — {f.get('size')} bytes")
        lines += ['','## Proposed Folders','']
        for f in proposed_folders:
            lines.append(f"- `{f.get('id')}` — `{f.get('path')}` — {f.get('purpose')}")
        lines += ['','## Future Writes Disabled In Preview','']
        for w in future_writes:
            lines.append(f"- `{w.get('id')}` — {w.get('action')} — target: `{w.get('target')}` — enabled now: {w.get('enabled_now')}")
        lines += ['','## Approval Gate','']
        for k,v in approval_gate.items():
            lines.append(f"- {k}: {v}")
        lines += ['','## Checks','']
        for c in checks:
            lines.append(f"- [{'PASS' if c.get('ok') else 'FAIL'}] `{c.get('id')}` — {c.get('message')}")
        lines += ['','## Recommendations','']
        for r in recommendations:
            lines.append(f"- `{r.get('id')}` — {r.get('title')} — {r.get('recommendation')} — auto apply: {r.get('auto_apply')}")
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(reports)}

    return report



def kayock_writer_create_project_gate_report(d=None):
    d=d or {}
    export=bool(d.get('export',False))
    typed_phrase=str(d.get('approval_phrase') or '').strip()
    project_id=str(d.get('project_id') or 'slipping_into_darkness').strip().lower().replace(' ','_')
    if project_id in ('','slipping','slipping_into_darkness'):
        project_id='slipping_into_darkness'
    manifest=kayock_writer_manifest_preview_report({'project_id':project_id})
    summary=manifest.get('summary') or {}
    mp=manifest.get('manifest_preview') or {}
    root=ROOT
    proposed_root=Path(summary.get('proposed_project_root') or mp.get('proposed_project_root') or (root/'Projects'/'KayockWriter'/'Slipping_into_Darkness'))
    reports=FOLDERS.get('kayock_writer_create_gate_reports',root/'Reports'/'KayockWriter'/'CreateProjectGate')

    required_phrase='CREATE KAYOCK WRITER PROJECT'
    phrase_matches=(typed_phrase==required_phrase)

    proposed_writes=[
        {'id':'create_project_root','kind':'folder','target':str(proposed_root),'action':'create folder','required':True},
        {'id':'create_source_folder','kind':'folder','target':str(proposed_root/'Source'),'action':'create folder','required':True},
        {'id':'create_markdown_folder','kind':'folder','target':str(proposed_root/'Markdown'),'action':'create folder','required':True},
        {'id':'create_chapters_folder','kind':'folder','target':str(proposed_root/'Chapters'),'action':'create folder','required':True},
        {'id':'create_scenes_folder','kind':'folder','target':str(proposed_root/'Scenes'),'action':'create folder','required':True},
        {'id':'create_codex_folder','kind':'folder','target':str(proposed_root/'Codex'),'action':'create folder','required':True},
        {'id':'create_timeline_folder','kind':'folder','target':str(proposed_root/'Timeline'),'action':'create folder','required':True},
        {'id':'create_continuity_folder','kind':'folder','target':str(proposed_root/'Continuity'),'action':'create folder','required':True},
        {'id':'create_mysteries_folder','kind':'folder','target':str(proposed_root/'Mysteries'),'action':'create folder','required':True},
        {'id':'create_exports_folder','kind':'folder','target':str(proposed_root/'Exports'),'action':'create folder','required':True},
        {'id':'write_manifest','kind':'file','target':str(proposed_root/'project.kayock-writer.json'),'action':'write manifest JSON','required':True},
        {'id':'write_readme','kind':'file','target':str(proposed_root/'README.md'),'action':'write README Markdown','required':True},
        {'id':'seed_books_outline','kind':'file','target':str(proposed_root/'Markdown'/'Books.md'),'action':'write Book 1 and Book 2 outline seed','required':True}
    ]

    legacy_files=[f for f in manifest.get('legacy_candidates',[]) if f.get('exists')]
    for idx,f in enumerate(legacy_files):
        source=Path(f.get('path',''))
        target=proposed_root/'Source'/source.name
        proposed_writes.append({'id':f'copy_legacy_source_{idx+1}','kind':'file_copy','source':str(source),'target':str(target),'action':'copy legacy source file; no move/delete','required':False})

    write_checks=[]
    overwrite_risks=[]
    parent_missing=[]
    for w in proposed_writes:
        target=Path(w.get('target',''))
        exists=False
        parent_exists=False
        try:
            exists=target.exists()
            parent_exists=target.parent.exists()
        except Exception as e:
            w['error']=str(e)
        item=dict(w)
        item['target_exists']=exists
        item['parent_exists']=parent_exists
        item['would_overwrite']=exists and w.get('kind')!='folder'
        item['folder_already_exists']=exists and w.get('kind')=='folder'
        item['enabled_now']=False
        item['requires_exact_phrase']=True
        item['requires_user_approval']=True
        item['will_execute_in_this_build']=False
        if item['would_overwrite']:
            overwrite_risks.append(item)
        if not parent_exists and w.get('id')!='create_project_root':
            parent_missing.append(item)
        write_checks.append(item)

    legacy_import_policy={
        'copy_only':True,
        'move_allowed':False,
        'delete_allowed':False,
        'legacy_root_remains_untouched':True,
        'import_enabled_now':False,
        'requires_explicit_selection_later':True
    }

    approval_gate={
        'required_phrase':required_phrase,
        'typed_phrase_present':bool(typed_phrase),
        'typed_phrase_matches':phrase_matches,
        'creation_enabled_in_this_build':False,
        'reason_creation_disabled':'v10.11.3 is a gate/pre-flight report only. The actual create-project action must be a later approved build.',
        'future_mode':'approved_action_only',
        'preview_required':True,
        'backup_required_before_write':True,
        'copy_not_move_for_legacy_sources':True,
        'no_delete_allowed':True,
        'no_overwrite_without_backup':True,
        'no_automatic_migration':True
    }

    safe_to_create_later=bool(
        manifest.get('preview_ready') and
        len(overwrite_risks)==0 and
        len(legacy_files)>0 and
        all(not w.get('will_execute_in_this_build') for w in write_checks)
    )

    checks=[
        {'id':'manifest_preview_loaded','ok':bool(manifest.get('ok')),'message':'Story Project Manifest Preview loaded.'},
        {'id':'preview_ready','ok':bool(manifest.get('preview_ready')),'message':'Manifest preview is ready.'},
        {'id':'legacy_files_detected','ok':len(legacy_files)>0,'message':f'Detected {len(legacy_files)} legacy source file(s) for future copy-only import.'},
        {'id':'proposed_writes_listed','ok':len(proposed_writes)>=10,'message':f'Listed {len(proposed_writes)} proposed future write(s).'},
        {'id':'overwrite_risk_clear','ok':len(overwrite_risks)==0,'message':f'Overwrite risks detected: {len(overwrite_risks)}.'},
        {'id':'creation_disabled_this_build','ok':all(not w.get('will_execute_in_this_build') for w in write_checks),'message':'No project creation will execute in this build.'},
        {'id':'phrase_gate_declared','ok':approval_gate.get('required_phrase')==required_phrase,'message':'Exact approval phrase gate is declared.'},
        {'id':'legacy_import_copy_only','ok':legacy_import_policy.get('copy_only') and not legacy_import_policy.get('move_allowed') and not legacy_import_policy.get('delete_allowed'),'message':'Legacy import policy is copy-only; move/delete disabled.'},
        {'id':'no_story_file_mutation','ok':True,'message':'No story files were created, moved, renamed, overwritten, or deleted.'}
    ]

    safety={
        'gate_preview_only':True,
        'read_only_legacy_scan':True,
        'no_project_creation':True,
        'no_story_file_mutation':True,
        'no_legacy_migration':True,
        'no_rename_performed':True,
        'no_overwrite':True,
        'no_delete':True,
        'no_install':True,
        'no_model_cleanup':True,
        'future_writes_require_preview_and_approval':True,
        'create_gate_export_only':True
    }

    recommendations=[
        {'id':'mark_create_gate_proven','title':'Mark Create Project Approval Gate proven','recommendation':'Use this gate as the last pre-flight check before building the actual approved creation action.','risk':'low','auto_apply':False},
        {'id':'next_create_project_action','title':'Build Create Project Approved Action next','recommendation':'Next build can add an actual project skeleton creation action, but only behind exact phrase approval and no-overwrite checks.','risk':'medium','auto_apply':False},
        {'id':'include_backup_marker','title':'Create a backup/evidence marker before writes','recommendation':'The future create action should export the gate report and manifest preview before creating folders/files.','risk':'low','auto_apply':False},
        {'id':'legacy_copy_only','title':'Keep legacy NovelForge copy-only','recommendation':'Future import must copy legacy files into Source and leave Z:\\FOXAI\\NovelForge untouched.','risk':'low','auto_apply':False}
    ]

    summary={
        'project_id':summary.get('project_id',project_id),
        'title':summary.get('title',mp.get('title','Slipping into Darkness')),
        'preview_ready':bool(manifest.get('preview_ready')),
        'safe_to_create_later':safe_to_create_later,
        'creation_enabled_in_this_build':False,
        'required_phrase':required_phrase,
        'typed_phrase_present':bool(typed_phrase),
        'typed_phrase_matches':phrase_matches,
        'legacy_files_detected':len(legacy_files),
        'proposed_writes':len(proposed_writes),
        'required_writes':sum(1 for w in proposed_writes if w.get('required')),
        'optional_copy_writes':sum(1 for w in proposed_writes if not w.get('required')),
        'overwrite_risks':len(overwrite_risks),
        'parent_missing_expected':len(parent_missing),
        'checks':len(checks),
        'checks_passed':sum(1 for c in checks if c.get('ok')),
        'problems':sum(1 for c in checks if not c.get('ok')),
        'proposed_project_root':str(proposed_root),
        'manifest_target':str(proposed_root/'project.kayock-writer.json'),
        'read_only':True,
        'report_only':True
    }

    healthy=all(c.get('ok') for c in checks)
    report={
        'ok':True,
        'created':now(),
        'title':'Kayock Writer Create Project Approval Gate',
        'read_only':True,
        'report_only':True,
        'healthy':healthy,
        'gate_ready':healthy,
        'safe_to_create_later':safe_to_create_later,
        'health_label':'CREATE PROJECT APPROVAL GATE READY',
        'message':'Create Project Approval Gate: CREATE PROJECT APPROVAL GATE READY',
        'milestone':'v10.11.3 Create Project Approval Gate',
        'summary':summary,
        'approval_gate':approval_gate,
        'legacy_import_policy':legacy_import_policy,
        'proposed_writes':write_checks,
        'overwrite_risks':overwrite_risks,
        'parent_missing_expected':parent_missing,
        'legacy_files':legacy_files,
        'manifest_preview_summary':manifest.get('summary',{}),
        'checks':checks,
        'recommendations':recommendations,
        'folders':{
            'proposed_project_root':str(proposed_root),
            'legacy_novel_forge':str(root/'NovelForge'),
            'create_gate_reports':str(reports)
        },
        'safety':safety
    }

    if export:
        reports.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path=reports/f'Create_Project_Approval_Gate_{project_id}_{stamp}.json'
        md_path=reports/f'Create_Project_Approval_Gate_{project_id}_{stamp}.md'
        jwrite(json_path,report)
        lines=[
            '# Kayock Writer Create Project Approval Gate','',
            f"Created: {report['created']}",
            f"Milestone: **{report['milestone']}**",
            f"Health: **{report['health_label']}**",
            f"Gate ready: {report['gate_ready']}",
            f"Safe to create later: {safe_to_create_later}",
            f"Creation enabled in this build: **False**",
            '',
            '## Safety','',
            '- Gate preview only.',
            '- Read-only legacy scan.',
            '- No project creation.',
            '- No story-file mutation.',
            '- No legacy migration.',
            '- No rename performed.',
            '- No overwrite.',
            '- No delete.',
            '- No install.',
            '- No model cleanup.',
            '- Future writes require preview and approval.',
            '',
            '## Summary',''
        ]
        for k,v in summary.items():
            lines.append(f"- {k.replace('_',' ').title()}: {v}")
        lines += ['','## Approval Gate','']
        for k,v in approval_gate.items():
            lines.append(f"- {k}: {v}")
        lines += ['','## Proposed Writes - Disabled In This Build','']
        for w in write_checks:
            lines.append(f"- `{w.get('id')}` — {w.get('action')} — `{w.get('target')}` — exists: {w.get('target_exists')} — overwrite risk: {w.get('would_overwrite')} — executes now: {w.get('will_execute_in_this_build')}")
        lines += ['','## Legacy Files For Future Copy-Only Import','']
        for f in legacy_files:
            lines.append(f"- `{f.get('suffix')}` — `{f.get('path')}` — {f.get('size')} bytes")
        lines += ['','## Overwrite Risks','']
        if overwrite_risks:
            for r in overwrite_risks:
                lines.append(f"- `{r.get('target')}`")
        else:
            lines.append('- None.')
        lines += ['','## Checks','']
        for c in checks:
            lines.append(f"- [{'PASS' if c.get('ok') else 'FAIL'}] `{c.get('id')}` — {c.get('message')}")
        lines += ['','## Recommendations','']
        for r in recommendations:
            lines.append(f"- `{r.get('id')}` — {r.get('title')} — {r.get('recommendation')} — auto apply: {r.get('auto_apply')}")
        md_path.write_text('\n'.join(lines),encoding='utf-8')
        report['exported']={'json':str(json_path),'markdown':str(md_path),'folder':str(reports)}

    return report


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

def bridge_feed():
    feed=jread(BRIDGE_FEED_FILE,{})
    builder=jread(BUILDER_REPORT_FILE,{})
    def walk_find(obj, wanted):
        if isinstance(obj,dict):
            for k,v in obj.items():
                if k in wanted and v not in [None,'',[]]:
                    return v
                found=walk_find(v,wanted)
                if found not in [None,'',[]]:
                    return found
        elif isinstance(obj,list):
            for v in obj:
                found=walk_find(v,wanted)
                if found not in [None,'',[]]:
                    return found
        return None
    def normalize_event(ev):
        if isinstance(ev,dict):
            return {
                'time': ev.get('timestamp') or ev.get('time') or ev.get('created') or '',
                'type': ev.get('type') or ev.get('event_type') or '',
                'source': ev.get('source') or '',
                'severity': ev.get('severity') or ev.get('level') or '',
                'message': ev.get('message') or ev.get('summary') or ev.get('title') or str(ev)[:400],
                'payload': ev.get('payload') if isinstance(ev.get('payload'),dict) else {}
            }
        if ev:
            return {'time':'','type':'','source':'','severity':'','message':str(ev),'payload':{}}
        return {'time':'','type':'','source':'','severity':'','message':'No recent Bridge event found.','payload':{}}
    latest_event=None
    if isinstance(feed,dict):
        for key in ['latest_event','last_event','event']:
            if feed.get(key):
                latest_event=feed.get(key); break
        if latest_event is None and isinstance(feed.get('events'),list) and feed.get('events'):
            latest_event=feed.get('events')[-1]
    ev=normalize_event(latest_event)

    steps=[]
    if isinstance(builder,dict):
        steps=builder.get('steps') or builder.get('results') or []
    if not steps and isinstance(ev.get('payload'),dict):
        steps=ev['payload'].get('steps') or []
    builder_passed=None; builder_total=None
    if isinstance(builder,dict):
        builder_passed=builder.get('passed') or builder.get('passed_steps') or builder.get('steps_passed')
        builder_total=builder.get('total') or builder.get('total_steps') or builder.get('steps_total')
    if (builder_passed is None or builder_total is None) and isinstance(steps,list) and steps:
        builder_total=len(steps)
        builder_passed=sum(1 for s in steps if isinstance(s,dict) and s.get('ok') is True)
    if (builder_passed is None or builder_total is None) and ev.get('message'):
        m=re.search(r'(\d+)\s*/\s*(\d+)', ev['message'])
        if m:
            builder_passed=int(m.group(1)); builder_total=int(m.group(2))
    builder_ok=None
    if isinstance(builder,dict) and 'ok' in builder:
        builder_ok=builder.get('ok')
    elif builder_passed is not None and builder_total is not None:
        builder_ok=(builder_passed==builder_total)

    kernel=feed.get('kernel',{}) if isinstance(feed,dict) else {}
    kernel_status='UNKNOWN'
    if isinstance(kernel,dict):
        kernel_status=str(kernel.get('status') or kernel.get('state') or kernel.get('health') or 'UNKNOWN')
    elif kernel:
        kernel_status=str(kernel)
    if kernel_status=='UNKNOWN':
        possible=walk_find(feed,{'kernel_status','status'})
        if possible and not isinstance(possible,(dict,list)):
            kernel_status=str(possible)
    runtime_packages=None
    if isinstance(feed,dict):
        runtime_packages=feed.get('runtime_packages') or feed.get('packages') or feed.get('package_count')
    if runtime_packages is None:
        runtime_packages=walk_find(feed,{'runtime_packages','runtime_package_count','package_count','packages_found'})

    dep_cards=[]
    departments=feed.get('departments',{}) if isinstance(feed,dict) else {}
    if isinstance(departments,dict):
        for name,data in departments.items():
            if isinstance(data,dict):
                status_txt=str(data.get('status') or data.get('state') or data.get('health') or 'UNKNOWN')
                officer=data.get('officer') or data.get('lead') or ''
            else:
                status_txt=str(data); officer=''
            dep_cards.append({'name':name,'status':status_txt,'officer':officer})
    elif isinstance(departments,list):
        for item in departments:
            if isinstance(item,dict):
                dep_cards.append({'name':item.get('name') or item.get('department') or 'Department','status':str(item.get('status') or item.get('state') or item.get('health') or 'UNKNOWN'),'officer':item.get('officer') or item.get('lead') or ''})

    if not dep_cards and isinstance(steps,list):
        for step in steps:
            if not isinstance(step,dict): continue
            out=str(step.get('stdout_tail') or step.get('stdout') or '')
            for line in out.splitlines():
                mm=re.search(r'-\s*(.*?)\s+\[(.*?)\]\s+Officer:\s*(.*?)\s+Manifest:\s*(\w+)\s+Health:\s*(\w+)', line)
                if mm:
                    dep_cards.append({'name':mm.group(1).strip(),'key':mm.group(2).strip(),'officer':mm.group(3).strip(),'status':'ONLINE' if mm.group(4).upper()=='PASS' and mm.group(5).upper()=='PASS' else 'CHECK'})

    if not dep_cards:
        def exists_any(*paths):
            return any(Path(p).exists() for p in paths)
        dep_cards=[
            {'name':'Command Bridge','status':'ACTIVE','officer':'Kayock Command OS'},
            {'name':'Academy','status':'ONLINE' if exists_any(ROOT/'core_v10'/'academy', ROOT/'Academy') else 'STAGED','officer':'Professor Kayock'},
            {'name':'Engineering','status':'ACTIVE' if exists_any(ROOT/'Departments'/'Engineering') else 'STAGED','officer':'Chief Engineer Ada'},
            {'name':'Artificial Minds','status':'READY' if (ENGINE.exists() or len(models())>0) else 'STAGED','officer':'Agent Fox'},
            {'name':'Iron Library','status':'READY' if LIB.exists() else 'MISSING','officer':'Archivist'},
            {'name':'Creative Studio','status':'READY' if COMFY_MAIN.exists() else 'STAGED','officer':'Image Forge'},
            {'name':'Repair Bay','status':'READY','officer':'Diagnostics First'},
            {'name':'PromptSmith','status':'STAGED','officer':'Prompt Workshop'},
            {'name':'Novel Forge','status':'STAGED','officer':'Story OS'}
        ]

    dep_count=len(dep_cards)
    dep_online=sum(1 for d in dep_cards if str(d.get('status','')).lower() in ['online','ok','ready','active','healthy','pass','passed'])

    return {
        'ok': True,
        'feed_found': BRIDGE_FEED_FILE.exists(),
        'builder_found': BUILDER_REPORT_FILE.exists(),
        'bridge_feed_file': str(BRIDGE_FEED_FILE),
        'builder_report_file': str(BUILDER_REPORT_FILE),
        'kernel_status': kernel_status,
        'departments': dep_count,
        'departments_online': dep_online,
        'department_cards': dep_cards[:24],
        'runtime_packages': runtime_packages,
        'latest_event': ev,
        'latest_event_message': ev.get('message'),
        'builder_ok': builder_ok,
        'builder_passed': builder_passed,
        'builder_total': builder_total,
        'raw_keys': sorted(feed.keys()) if isinstance(feed,dict) else []
    }


def library_type_match(p, kind):
    kind=(kind or 'all').lower()
    if kind in ['all','any','']:
        return True
    if kind in ['folder','folders']:
        return p.is_dir()
    if p.is_dir():
        return False
    ext=p.suffix.lower()
    groups={
        'pdf':{'.pdf'},
        'text':{'.txt','.md','.markdown','.log','.csv','.json','.xml','.yaml','.yml'},
        'doc':{'.doc','.docx','.rtf','.odt'},
        'image':{'.png','.jpg','.jpeg','.webp','.gif','.bmp','.svg'},
        'code':{'.py','.js','.html','.css','.json','.bat','.ps1','.sh','.ts','.tsx','.jsx','.sql'},
        'audio':{'.mp3','.wav','.ogg','.flac','.m4a'},
        'video':{'.mp4','.mkv','.mov','.avi','.webm'}
    }
    return ext in groups.get(kind,set())

def search_library(q='', kind='all', limit=250):
    LIB.mkdir(parents=True,exist_ok=True)
    term=(q or '').strip().lower()
    try:
        limit=max(1,min(int(limit),1000))
    except Exception:
        limit=250
    results=[]
    scanned=0
    for p in LIB.rglob('*'):
        scanned+=1
        try:
            rel=str(p.relative_to(LIB)).replace('\\','/')
            hay=(p.name+' '+rel).lower()
            if term and term not in hay:
                continue
            if not library_type_match(p,kind):
                continue
            results.append({
                'name':p.name,
                'rel_path':rel,
                'is_dir':p.is_dir(),
                'ext':'folder' if p.is_dir() else p.suffix.lower(),
                'size':'' if p.is_dir() else human(p.stat().st_size),
                'modified':datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            })
            if len(results)>=limit:
                break
        except Exception:
            pass
    return {'ok':True,'query':q,'type':kind,'scanned':scanned,'count':len(results),'limit':limit,'results':results,'library':str(LIB)}


def preview_library_file(rel, limit=16000):
    p=safelib(rel)
    if not p or not p.exists() or p.is_dir():
        return {'ok':False,'message':'Invalid file.'}
    try:
        limit=max(1000,min(int(limit),60000))
    except Exception:
        limit=16000
    ext=p.suffix.lower()
    readable={
        '.txt','.md','.markdown','.log','.json','.csv','.xml','.yaml','.yml',
        '.py','.js','.html','.css','.bat','.ps1','.sh','.ts','.tsx','.jsx',
        '.sql','.ini','.cfg','.conf','.toml','.rst'
    }
    if ext not in readable:
        return {
            'ok':False,
            'message':'Preview is available for text, markdown, logs, JSON, code, and config files only for now.',
            'name':p.name,
            'rel_path':str(p.relative_to(LIB)).replace('\\','/'),
            'ext':ext,
            'size':human(p.stat().st_size)
        }
    try:
        raw=p.read_text(encoding='utf-8',errors='replace')
        truncated=len(raw)>limit
        content=raw[:limit]
        if active_project:
            timeline(active_project,f'Iron Library previewed file: {p.name}')
        return {
            'ok':True,
            'name':p.name,
            'rel_path':str(p.relative_to(LIB)).replace('\\','/'),
            'ext':ext,
            'size':human(p.stat().st_size),
            'modified':datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y-%m-%d %H:%M'),
            'content':content,
            'truncated':truncated,
            'chars':len(raw)
        }
    except Exception as e:
        return {'ok':False,'message':f'Preview failed: {e}'}


IRON_INDEX_FILE=ROOT/'Config'/'iron_library_index.json'

def iron_readable_ext(p):
    return p.suffix.lower() in {
        '.txt','.md','.markdown','.log','.json','.csv','.xml','.yaml','.yml',
        '.py','.js','.html','.css','.bat','.ps1','.sh','.ts','.tsx','.jsx',
        '.sql','.ini','.cfg','.conf','.toml','.rst'
    }

def library_index_status():
    d=jread(IRON_INDEX_FILE,{})
    return {
        'ok':True,
        'index_found':IRON_INDEX_FILE.exists(),
        'index_file':str(IRON_INDEX_FILE),
        'built':d.get('built'),
        'items':len(d.get('items',[])) if isinstance(d.get('items'),list) else 0,
        'scanned':d.get('scanned',0),
        'skipped':d.get('skipped',0),
        'library':str(LIB)
    }

def build_library_index(max_files=2000,max_size=5*1024*1024,max_chars=60000):
    LIB.mkdir(parents=True,exist_ok=True)
    items=[]; scanned=0; skipped=0
    try:
        max_files=max(1,min(int(max_files),10000))
    except Exception:
        max_files=2000
    for p in LIB.rglob('*'):
        scanned+=1
        try:
            if not p.is_file() or not iron_readable_ext(p):
                continue
            size=p.stat().st_size
            if size>max_size:
                skipped+=1; continue
            rel=str(p.relative_to(LIB)).replace('\\','/')
            raw=p.read_text(encoding='utf-8',errors='replace')
            content=raw[:max_chars]
            # Compact searchable text. We keep the first chunk, not the whole library.
            compact=re.sub(r'\s+',' ',content).strip()
            items.append({
                'name':p.name,
                'rel_path':rel,
                'ext':p.suffix.lower(),
                'size':human(size),
                'modified':datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y-%m-%d %H:%M'),
                'text':compact
            })
            if len(items)>=max_files:
                break
        except Exception:
            skipped+=1
    data={'built':now(),'library':str(LIB),'scanned':scanned,'skipped':skipped,'items':items}
    jwrite(IRON_INDEX_FILE,data)
    if active_project:
        timeline(active_project,f'Iron Library index built: {len(items)} items')
    return {'ok':True,'message':f'Indexed {len(items)} readable file(s).','built':data['built'],'items':len(items),'scanned':scanned,'skipped':skipped,'index_file':str(IRON_INDEX_FILE)}

def search_library_index(q='',limit=100):
    term=(q or '').strip().lower()
    if not term:
        return {'ok':False,'message':'Enter a search term.','results':[]}
    try:
        limit=max(1,min(int(limit),500))
    except Exception:
        limit=100
    data=jread(IRON_INDEX_FILE,{})
    items=data.get('items',[])
    if not isinstance(items,list) or not items:
        return {'ok':False,'message':'Iron Library index is empty. Build the index first.','results':[]}
    terms=[t for t in re.split(r'\s+',term) if t]
    results=[]
    for it in items:
        hay=(it.get('name','')+' '+it.get('rel_path','')+' '+it.get('text','')).lower()
        score=0
        for t in terms:
            if t in hay:
                score+=hay.count(t)
        if score<=0:
            continue
        text_value=it.get('text','')
        pos=min([hay.find(t) for t in terms if hay.find(t)>=0] or [0])
        start=max(0,pos-180)
        end=min(len(text_value),start+520)
        snippet=text_value[start:end]
        results.append({
            'name':it.get('name'),
            'rel_path':it.get('rel_path'),
            'ext':it.get('ext'),
            'size':it.get('size'),
            'modified':it.get('modified'),
            'score':score,
            'snippet':snippet
        })
    results=sorted(results,key=lambda x:x.get('score',0),reverse=True)[:limit]
    return {'ok':True,'query':q,'built':data.get('built'),'count':len(results),'results':results}

def status():
    PROJECTS.mkdir(exist_ok=True); LIB.mkdir(exist_ok=True); d={'root':str(ROOT),'drive_root':str(DRIVE),'kayock_browser':str(KAYOCK),'kayock_browser_found':KAYOCK.exists(),'engine':str(ENGINE),'engine_found':ENGINE.exists(),'chat_online':check(CHAT_HEALTH),'chat_model':chat_model,'chat_model_name':Path(chat_model).name if chat_model else None,'active_project':active_project,'projects':len([p for p in PROJECTS.iterdir() if p.is_dir()]),'projects_root':str(PROJECTS),'active_professor_name':active_prof()[0],'comfy_exists':COMFY_MAIN.exists(),'comfy_online':check('http://127.0.0.1:8188'),'chat_models':len(models()),'library_items':len(list(LIB.rglob('*'))) if LIB.exists() else 0,'library_pdfs':len(list(LIB.rglob('*.pdf'))) if LIB.exists() else 0}
    d.update(metric()); return d

def main():
    LOGS.mkdir(exist_ok=True); PROJECTS.mkdir(exist_ok=True); log(f'Starting FOXAI Web Console at {URL}'); ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
if __name__=='__main__': main()
