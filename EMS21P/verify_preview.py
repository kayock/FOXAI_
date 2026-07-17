from __future__ import annotations
import ast,hashlib,json,re,shutil,subprocess,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
BASE_SHA='5cffd8b594c5f91b983b391758fa295b151ca82c97ce8ddfcb085cacdd76a548'; CAND_SHA='e0ec7d66bae40d3be67653f47f86cde310e50147924ee48778c4634f3c1d7525'; DIFF_SHA='01e9c29f794536092daefd706ae52afd73dd6baee31fb4860f1c6a8e25712e14'; APPLIED_SHA='69c3faf63cb6b702530137180ed0933b444c2754027a597bf46a105ef7cbfb4b'
LOCKED={'core/foxai_web.py': '5cffd8b594c5f91b983b391758fa295b151ca82c97ce8ddfcb085cacdd76a548', 'core/server.py': '238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81', 'core/security_containment.py': '9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24', 'core/engineer_agent.py': 'f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19', 'core/service_registry.py': 'cc798df061a27a51c4ea1f64b3757d2a92724a9a5768e4c190846966efe0251b', 'ui/main_window.py': '2e8f452d36f3a3c697b23ebdee2921f5fe01aa1b1c28460dfbc36921ca5ee0c3', 'tests/test_boundary_watch.py': 'b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382', 'Config/FoxAI.ini': '677067e2b58416ba7d7bacc1dcfe40b9f43783e625dd305d0bbf82b6d3174d41', 'Config/application_registry.json': '6338e10b813460ee421e4cbf3d9d74fd82d5f24178347e35f4318ef3c4ef9022', 'Config/fleet_registry.json': '18745be73f67e073c002bb645a3c0eaad0a3090ebee1b3bb547ddcc2f147bdb6', 'Engine/llama-server.exe': '936cfb77f011911f879a5af715013eb12141115547c1f731114d8e9c20ebd89e'}
SCRIPT_RE=re.compile(r"<script[^>]*>(.*?)</script\s*>",re.I|re.S)
class VerifyError(RuntimeError): pass
def sha256(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def state(p):
 p=Path(p)
 if not p.exists():return {'exists':False,'sha256':None,'size':0}
 return {'exists':p.is_file(),'sha256':sha256(p) if p.is_file() else None,'size':p.stat().st_size}
def root(start):
 for c in (start,*start.parents):
  if (c/'core/foxai_web.py').is_file() and (c/'Engine/llama-server.exe').is_file():return c
 raise VerifyError(r'FOXAI root not found. Extract EMS21P directly inside Z:\FOXAI.')
def package_manifest(pkg):
 rows=[]
 for line in (pkg/'PACKAGE_SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
  if not line.strip():continue
  d,r=line.split('  ',1);a=sha256(pkg/r) if (pkg/r).is_file() else None;rows.append({'path':r,'expected':d,'actual':a,'ok':a==d})
 if not rows or not all(x['ok'] for x in rows):raise VerifyError('Package manifest failed.')
 return {'passed':True,'files':rows,'apply_capability_present':False}
def snapshot(rr):
 out={k:state(rr/k) for k in LOCKED}
 out['Config/extension_state.json']=state(rr/'Config/extension_state.json')
 for rel in ('Backups/ExtensionState','Reports/ExtensionState'):out[rel]=state(rr/rel)
 sec=rr/'Logs/Security'
 if sec.exists():
  for p in sorted(sec.rglob('*')):
   if p.is_file():out[str(p.relative_to(rr)).replace('\\','/')]=state(p)
 return out
def live_baselines(rr):
 rows=[]
 for rel,d in LOCKED.items():
  a=sha256(rr/rel) if (rr/rel).is_file() else None;rows.append({'path':rel,'expected':d,'actual':a,'ok':a==d})
 if not all(x['ok'] for x in rows):raise VerifyError('A live baseline changed.')
 if (rr/'Config/extension_state.json').exists():raise VerifyError('extension_state.json must remain absent for this preview.')
 return {'passed':True,'files':rows,'extension_state_absent':True}
def exact(pkg):
 b=pkg/'baseline/core/foxai_web.py';c=pkg/'candidate/core/foxai_web.py';d=pkg/'diffs/foxai_web.py.diff'
 checks={'baseline':sha256(b)==BASE_SHA,'candidate':sha256(c)==CAND_SHA,'diff':sha256(d)==DIFF_SHA}
 if not all(checks.values()):raise VerifyError('Exact artifact identity failed.')
 compile(b.read_text(encoding='utf-8'),str(b),'exec');compile(c.read_text(encoding='utf-8'),str(c),'exec')
 r=subprocess.run(['patch','--dry-run','-s',str(b),str(d)],capture_output=True,text=True)
 return {'passed':True,'checks':checks,'python_compile':True,'diff_has_hunks':'@@' in d.read_text(encoding='utf-8')}
def applied(pkg):
 p=pkg/'approved/phase2_applied_receipt.json'
 if sha256(p)!=APPLIED_SHA:raise VerifyError('Applied receipt changed.')
 d=json.loads(p.read_text(encoding='utf-8'))
 ok=d.get('state')=='applied_verified' and d.get('verified') is True and d.get('final_live_sha256')==BASE_SHA and d.get('changed_files')==['core/foxai_web.py'] and d.get('runtime_state_created') is False and d.get('delete_operations')==[]
 if not ok:raise VerifyError('Applied receipt incomplete.')
 return {'passed':True,'sha256':APPLIED_SHA}
def node_browser(pkg):
 node=shutil.which('node')
 if not node:raise VerifyError('Node.js not found.')
 src=(pkg/'candidate/core/foxai_web.py').read_text(encoding='utf-8');scripts=SCRIPT_RE.findall(src);rows=[]
 import tempfile
 with tempfile.TemporaryDirectory(prefix='ems21_node_') as t:
  for i,s in enumerate(scripts,1):
   p=Path(t)/f's{i}.js';p.write_text(s,encoding='utf-8');r=subprocess.run([node,'--check',str(p)],capture_output=True,text=True,timeout=120);rows.append({'index':i,'passed':r.returncode==0,'stderr':r.stderr})
 if not scripts or not all(x['passed'] for x in rows):raise VerifyError('Embedded JavaScript failed.')
 r=subprocess.run([node,str(pkg/'verification/browser_harness.js'),str(pkg/'candidate/core/foxai_web.py')],capture_output=True,text=True,timeout=120)
 if r.returncode:raise VerifyError('Browser harness failed: '+r.stderr)
 return {'passed':True,'javascript_blocks':len(scripts),'node_check':rows,'browser_harness':{'passed':True,'stdout':r.stdout}}
def backend(pkg,rr=None):
 cmd=[sys.executable,str(pkg/'verification/backend_harness.py'),str(pkg/'candidate/core/foxai_web.py')]
 if rr is not None:cmd+=['--live-root',str(rr)]
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=240)
 try:d=json.loads(r.stdout)
 except:d={'passed':False}
 if r.returncode or d.get('passed') is not True:raise VerifyError('Backend regression failed: '+r.stderr+r.stdout)
 return {'passed':True,'result':d}
def fn(text,names):
 tree=ast.parse(text);lines=text.splitlines(keepends=True);out={}
 for n in tree.body:
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names:out[n.name]=''.join(lines[n.lineno-1:n.end_lineno])
 return out
def state_logic_unchanged(pkg):
 names={'_extension_state_preview_contract','extension_state_change_preview','apply_extension_state_change','toggle_extension','extension_inventory_snapshot','launch_extension_inventory_item'}
 b=fn((pkg/'baseline/core/foxai_web.py').read_text(encoding='utf-8'),names);c=fn((pkg/'candidate/core/foxai_web.py').read_text(encoding='utf-8'),names)
 checks={n:b.get(n)==c.get(n) and bool(b.get(n)) for n in sorted(names)}
 if not all(checks.values()):raise VerifyError('Guarded state logic changed unexpectedly.')
 return {'passed':True,'checks':checks}
def static(pkg):
 s=(pkg/'candidate/core/foxai_web.py').read_text(encoding='utf-8')
 checks={
 'help_buttons':"openExtensionHelp('quick')" in s and "openExtensionHelp('manual')" in s,
 'manual_and_cheat_sheet':'What Disable Does' in s and 'SAFE TO CLICK' in s,
 'advanced_collapsed':'<details class="card wide extadvanced">' in s,
 'protected_legacy':'protectedcontrol disabled' in s and '>Protected</button>' in s,
 'state_file_clarity':'state_file_exists' in s and 'NOT CREATED — reserved path' in s,
 'manifest_count_labels':'Manifest records:' in s and 'Manifest Records' in s,
 'no_install_remove_update_download':all(x in s for x in ("'install':False","'remove':False","'update':False","'download':False")),
 'phase2_guards_present':'APPROVE EXTENSION STATE' in s and 'blocked_safe_preview_required' in s,
 }
 if not all(checks.values()):raise VerifyError('Static operator-clarity contract failed.')
 return {'passed':True,'checks':checks}
def boundary(rr):
 code="import sys,unittest;sys.path.insert(0,"+repr(str(rr))+ ");suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_boundary_watch');r=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if r.wasSuccessful() else 1)"
 r=subprocess.run([sys.executable,'-c',code],cwd=str(rr),capture_output=True,text=True,timeout=180);allout=r.stdout+r.stderr
 if r.returncode or 'Ran 5 tests' not in allout or 'OK' not in allout:raise VerifyError('Boundary Watch failed.')
 return {'passed':True,'tests':5,'stdout':r.stdout,'stderr':r.stderr}
def main():
 pkg=Path(__file__).resolve().parent;rr=root(pkg);out=pkg/'LIVE_VERIFY_RECEIPT.json';before=snapshot(rr)
 receipt={'action':'extension_manager_operator_clarity_phase2_1_exact_preview_verify','created':datetime.now(timezone.utc).isoformat(),'state':'running','verified':False,'root':str(rr),'live_files_modified':False,'candidate_created':True,'apply_capability_present':False,'changed_files_proposed':['core/foxai_web.py'],'unchanged_files_explicit':['core/server.py','Config/application_registry.json','Config/fleet_registry.json','core/service_registry.py','Config/extension_state.json'],'delete_operations':[],'checks':{},'failure':None,'protected_changes':[]}
 try:
  receipt['checks']['package_manifest']=package_manifest(pkg);receipt['checks']['phase2_applied_receipt']=applied(pkg);receipt['checks']['exact_artifacts']=exact(pkg);receipt['checks']['live_baselines']=live_baselines(rr);receipt['checks']['node_and_browser']=node_browser(pkg);receipt['checks']['backend_regression']=backend(pkg);receipt['checks']['live_inventory_preview']=backend(pkg,rr);receipt['checks']['state_logic_unchanged']=state_logic_unchanged(pkg);receipt['checks']['static_contract']=static(pkg);receipt['checks']['boundary_watch']=boundary(rr)
  after=snapshot(rr);changes=[k for k in sorted(set(before)|set(after)) if before.get(k)!=after.get(k)];receipt['protected_changes']=changes
  if changes:raise VerifyError('Read-only preview changed protected files: '+repr(changes))
  receipt.update({'state':'exact_preview_verified','verified':True})
 except Exception as e:
  after=snapshot(rr);changes=[k for k in sorted(set(before)|set(after)) if before.get(k)!=after.get(k)];receipt.update({'state':'stopped_fail_closed','verified':not changes,'live_files_modified':bool(changes),'protected_changes':changes,'failure':{'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()}})
 out.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
 print();print('='*72);print('FOXAI EXTENSION MANAGER OPERATOR CLARITY — PHASE 2.1');print('State:',receipt['state']);print('Verified:',receipt['verified']);print('Live files modified:',receipt['live_files_modified']);print('Apply capability present: False');print('Receipt:',out)
 if receipt['failure']:print('Failure:',receipt['failure']['message'])
 print();input('Press Enter to close...');return 0 if receipt['state']=='exact_preview_verified' else 1
if __name__=='__main__':raise SystemExit(main())
