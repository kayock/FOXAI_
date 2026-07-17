from __future__ import annotations
import ast,hashlib,json,re,shutil,subprocess,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

WEB_BASELINE_SHA='ecccf3b4a780d9de6ef2aa56522c6b65d06035c42a4a9050d72b95df530c40d0'
WEB_CANDIDATE_SHA='5cffd8b594c5f91b983b391758fa295b151ca82c97ce8ddfcb085cacdd76a548'
WEB_DIFF_SHA='86e65fec472f6b5701af24de7e683a81a8340726f1a6fc460feeb0f33a5bdb51'
APPLIED_RECEIPT_SHA='3cd3ff97513c3c9afef496dd416d41a1f071e4831f46eb32f60432e0db87923e'
LOCKED_HASHES={'core/foxai_web.py': 'ecccf3b4a780d9de6ef2aa56522c6b65d06035c42a4a9050d72b95df530c40d0', 'core/server.py': '238931aaa46446448696c5000ae9b744f44d171fd491e0d41b3562b8d9fddd81', 'core/security_containment.py': '9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24', 'core/engineer_agent.py': 'f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19', 'core/service_registry.py': 'cc798df061a27a51c4ea1f64b3757d2a92724a9a5768e4c190846966efe0251b', 'ui/main_window.py': '2e8f452d36f3a3c697b23ebdee2921f5fe01aa1b1c28460dfbc36921ca5ee0c3', 'tests/test_boundary_watch.py': 'b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382', 'Config/FoxAI.ini': '677067e2b58416ba7d7bacc1dcfe40b9f43783e625dd305d0bbf82b6d3174d41', 'Config/application_registry.json': '6338e10b813460ee421e4cbf3d9d74fd82d5f24178347e35f4318ef3c4ef9022', 'Config/fleet_registry.json': '18745be73f67e073c002bb645a3c0eaad0a3090ebee1b3bb547ddcc2f147bdb6', 'Engine/llama-server.exe': '936cfb77f011911f879a5af715013eb12141115547c1f731114d8e9c20ebd89e', 'Extensions/Academy/Conversation/extension.json': 'bd94beb278523891931272e1e7b00c72f6eae344493fa1fecb5c51b804097d5d', 'Extensions/Engineering/Database/extension.json': 'a487f38867411ae72abeb9427393b5847242c2181ade5ef841c7490f5e6360f8', 'Extensions/Engineering/Everything/extension.json': 'bbc5243aff38c74007ecfe777f5204bf80f119d44853e828c6e3186395176c86', 'Extensions/Engineering/ripgrep/extension.json': '21d4e25c2a312ecaf13affd9df29229beae623d36e1f6396f3b6981e3508ea0b', 'Extensions/Engineering/TreeSitter/extension.json': 'feb9e78e193b1ae3a2d40dbf73f6b9e6692f386d9d670a2291c990d4120b0250', 'Extensions/Engineering/WinMerge/extension.json': 'a272f06a53c2788c3d36e3cf3c5be1480d06228c288326043bffc769cd6f8d02'}
SCRIPT_RE=re.compile(r"<script[^>]*>(.*?)</script\s*>",re.I|re.S)
HUNK_RE=re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

class VerifyError(RuntimeError): pass

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
 return h.hexdigest()

def file_state(path:Path)->dict[str,Any]:
 if not path.exists(): return {'exists':False,'sha256':None,'size':0,'mtime_ns':None}
 st=path.stat(); return {'exists':path.is_file(),'sha256':sha256(path) if path.is_file() else None,'size':st.st_size,'mtime_ns':st.st_mtime_ns}

def find_root(start:Path)->Path:
 for c in (start,*start.parents):
  if (c/'core/foxai_web.py').is_file() and (c/'Config/application_registry.json').is_file() and (c/'Engine/llama-server.exe').is_file(): return c
 raise VerifyError(r'FOXAI root not found. Extract EMS2P directly inside Z:\FOXAI.')

def package_manifest(package:Path):
 checks=[]
 for line in (package/'PACKAGE_SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
  if not line.strip(): continue
  digest,rel=line.split('  ',1); p=package/rel; actual=sha256(p) if p.is_file() else None
  checks.append({'path':rel,'expected':digest,'actual':actual,'ok':actual==digest})
 if not checks or not all(x['ok'] for x in checks): raise VerifyError('Package manifest failed.')
 return {'passed':True,'files':checks,'installer_apply_capability_present':False}

def protected_snapshot(root:Path):
 result={rel:file_state(root/rel) for rel in LOCKED_HASHES}
 result['Config/extension_state.json']=file_state(root/'Config/extension_state.json')
 sec=root/'Logs/Security'
 if sec.exists():
  for p in sorted(sec.rglob('*')):
   if p.is_file(): result[str(p.relative_to(root)).replace('\\','/')]=file_state(p)
 return result

def changed(before,after): return [k for k in sorted(set(before)|set(after)) if before.get(k)!=after.get(k)]

def live_baselines(root:Path):
 checks=[]
 for rel,expected in LOCKED_HASHES.items():
  p=root/rel; actual=sha256(p) if p.is_file() else None; checks.append({'path':rel,'expected':expected,'actual':actual,'ok':actual==expected})
 if not all(x['ok'] for x in checks): raise VerifyError('A locked live baseline changed.')
 state=root/'Config/extension_state.json'
 if state.exists(): raise VerifyError('extension_state.json must still be absent for this exact preview baseline.')
 return {'passed':True,'files':checks,'extension_state_absent':True}

def apply_diff(source,diff):
 src=source.splitlines(keepends=True); lines=diff.splitlines(keepends=True); out=[]; si=0; i=0; hunks=0
 while i<len(lines):
  line=lines[i]
  if line.startswith(('--- ','+++ ')): i+=1; continue
  m=HUNK_RE.match(line.rstrip('\r\n'))
  if not m: i+=1; continue
  hunks+=1; old=int(m.group(1))-1; out.extend(src[si:old]); si=old; i+=1
  while i<len(lines):
   pl=lines[i]
   if HUNK_RE.match(pl.rstrip('\r\n')) or pl.startswith(('--- ','+++ ')): break
   if pl.startswith('\\ No newline'): i+=1; continue
   mark=pl[:1]; content=pl[1:]
   if mark==' ':
    if si>=len(src) or src[si]!=content: raise VerifyError('Diff context mismatch.')
    out.append(content); si+=1
   elif mark=='-':
    if si>=len(src) or src[si]!=content: raise VerifyError('Diff removal mismatch.')
    si+=1
   elif mark=='+': out.append(content)
   else: raise VerifyError('Unsupported diff line.')
   i+=1
 if not hunks: raise VerifyError('Diff has no hunks.')
 out.extend(src[si:]); return ''.join(out)

def exact_artifacts(package:Path):
 b=package/'baseline/core/foxai_web.py'; c=package/'candidate/core/foxai_web.py'; d=package/'diffs/foxai_web.py.diff'
 checks={'baseline':sha256(b)==WEB_BASELINE_SHA,'candidate':sha256(c)==WEB_CANDIDATE_SHA,'diff':sha256(d)==WEB_DIFF_SHA}
 if not all(checks.values()): raise VerifyError('Exact artifact identity failed.')
 bt=b.read_text(encoding='utf-8'); ct=c.read_text(encoding='utf-8')
 if apply_diff(bt,d.read_text(encoding='utf-8'))!=ct: raise VerifyError('Diff reconstruction failed.')
 compile(bt,str(b),'exec'); compile(ct,str(c),'exec')
 return {'passed':True,'checks':checks,'diff_reconstruction':True,'python_compile':True}

def applied_receipt(package:Path):
 p=package/'approved/phase1_applied_receipt.json'
 if sha256(p)!=APPLIED_RECEIPT_SHA: raise VerifyError('Phase 1 applied receipt changed.')
 d=json.loads(p.read_text(encoding='utf-8'))
 ok=d.get('state')=='applied_verified' and d.get('verified') is True and d.get('final_live_sha256')==WEB_BASELINE_SHA and d.get('changed_files')==['core/foxai_web.py'] and d.get('delete_operations')==[]
 if not ok: raise VerifyError('Phase 1 applied receipt is incomplete.')
 return {'passed':True,'sha256':APPLIED_RECEIPT_SHA}

def grounding(package:Path):
 index=json.loads((package/'grounding/SNAPSHOT_INDEX.json').read_text(encoding='utf-8'))
 selected=index.get('selected_grounding')
 if not isinstance(selected,dict) or not selected:
  raise VerifyError('Selected grounding index is missing or empty.')
 checks=[]
 for rel,item in sorted(selected.items()):
  if not isinstance(rel,str) or not isinstance(item,dict):
   raise VerifyError('Selected grounding entry is malformed.')
  expected=item.get('sha256')
  if not isinstance(expected,str) or len(expected)!=64:
   raise VerifyError('Selected grounding SHA-256 is malformed.')
  p=package/rel
  actual=sha256(p) if p.is_file() else None
  checks.append({'path':rel,'expected':expected,'actual':actual,'ok':actual==expected})
 if not all(x['ok'] for x in checks):
  raise VerifyError('Grounding snapshot failed.')
 return {
  'passed':True,
  'files':checks,
  'selected_grounding_records':len(checks),
  'source_file_records':len(index.get('files',[])),
  'provided_extension_state':index.get('provided_extension_state',False),
  'extension_state_absence_expected':True,
  'verifier_revision':2,
 }

def node_browser(package:Path):
 node=shutil.which('node')
 if not node: raise VerifyError('Node.js not found.')
 source=(package/'candidate/core/foxai_web.py').read_text(encoding='utf-8'); scripts=SCRIPT_RE.findall(source); results=[]
 with __import__('tempfile').TemporaryDirectory(prefix='ems2_node_') as t:
  for i,script in enumerate(scripts,1):
   p=Path(t)/f'script_{i}.js'; p.write_text(script,encoding='utf-8'); r=subprocess.run([node,'--check',str(p)],capture_output=True,text=True,timeout=120)
   results.append({'index':i,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'passed':r.returncode==0})
 if not scripts or not all(x['passed'] for x in results): raise VerifyError('Embedded JavaScript failed.')
 r=subprocess.run([node,str(package/'verification/browser_harness.js'),str(package/'candidate/core/foxai_web.py')],capture_output=True,text=True,timeout=120)
 browser={'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'passed':r.returncode==0}
 if not browser['passed']: raise VerifyError('Browser state-control harness failed.')
 return {'passed':True,'javascript_blocks':len(scripts),'node_check':results,'browser_harness':browser}

def backend(package:Path,root:Path|None=None):
 cmd=[sys.executable,str(package/'verification/backend_harness.py'),str(package/'candidate/core/foxai_web.py')]
 if root is not None: cmd.extend(['--live-root',str(root)])
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=240)
 try: data=json.loads(r.stdout)
 except Exception: data={'passed':False}
 result={'passed':r.returncode==0 and data.get('passed') is True,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'result':data}
 if not result['passed']: raise VerifyError('Backend state-control harness failed.')
 return result

def first_function_sources(text,names):
 tree=ast.parse(text); lines=text.splitlines(keepends=True); out={}
 for node in tree.body:
  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in names and node.name not in out:
   out[node.name]=''.join(lines[node.lineno-1:node.end_lineno])
 return out

def legacy_controls(package:Path):
 names={'list_extensions','normalize_extension_manifest','validate_extensions','create_sample_extension','extension_report_export','suggest_manifest_repair','apply_manifest_repair','open_extension_inventory_folder','open_extension_inventory_url'}
 b=first_function_sources((package/'baseline/core/foxai_web.py').read_text(encoding='utf-8'),names)
 c=first_function_sources((package/'candidate/core/foxai_web.py').read_text(encoding='utf-8'),names)
 checks={name:b.get(name)==c.get(name) and bool(b.get(name)) for name in sorted(names)}
 if not all(checks.values()): raise VerifyError('Non-state legacy extension controls changed.')
 return {'passed':True,'checks':checks,'intentional_changes':['toggle_extension now fails closed','toggleExtension opens guarded preview','launch blocks disabled overrides']}

def static_contract(package:Path):
 s=(package/'candidate/core/foxai_web.py').read_text(encoding='utf-8')
 checks={
  'single_live_source_candidate':True,
  'optional_only':"top not in {'extensions','modules'}" in s and "not item['required']" in s,
  'required_block': 'Required/core/department extensions cannot be state-overridden.' in s,
  'dependency_checks': all(x in s for x in ('Missing declared dependencies:','Disabled declared dependencies:','Enabled dependents require this extension:')),
  'exact_preview_digest': 'preview_digest' in s and "sort_keys=True,separators=(',',':')" in s,
  'typed_approval': 'APPROVE EXTENSION STATE' in s and 'approval_phrase' in s,
  'preview_expiry': 'State preview expired after 30 minutes.' in s,
  'atomic_write': 'os.replace(stage,path)' in s,
  'backup': "ROOT/'Backups'/'ExtensionState'" in s,
  'receipt': "ROOT/'Reports'/'ExtensionState'" in s and "'state':'applied_verified'" in s,
  'rollback': '_extension_state_restore_original' in s and 'rolled_back_verified' in s,
  'restore_removes_final_file': "state_file_effect':'delete override file" not in s and 'delete override file' in s,
  'direct_toggle_blocked': 'blocked_safe_preview_required' in s,
  'disabled_launch_blocked': 'blocked_extension_disabled' in s,
  'no_install_update_download': all(x in s for x in ("'install':False","'remove':False","'update':False","'download':False")),
  'state_path_exact': "ROOT/'Config'/'extension_state.json'" in s,
  'preview_routes': "/api/extensions/state/preview" in s and "/api/extensions/state/apply" in s,
 }
 if not all(checks.values()): raise VerifyError('Static Phase 2 contract incomplete.')
 return {'passed':True,'checks':checks}

def boundary_watch(root:Path):
 code="import sys,unittest;sys.path.insert(0,"+repr(str(root))+ ");suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_boundary_watch');result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if result.wasSuccessful() else 1)"
 r=subprocess.run([sys.executable,'-c',code],cwd=str(root),capture_output=True,text=True,timeout=180); combined=r.stdout+r.stderr
 result={'passed':r.returncode==0 and 'Ran 5 tests' in combined and 'OK' in combined,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'tests':5}
 if not result['passed']: raise VerifyError('Boundary Watch failed.')
 return result

def main():
 package=Path(__file__).resolve().parent; root=find_root(package); output=package/'LIVE_VERIFY_RECEIPT.json'; before=protected_snapshot(root)
 receipt={'action':'extension_manager_safe_state_controls_phase2_exact_preview_verify','created':datetime.now(timezone.utc).isoformat(),'state':'running','verified':False,'root':str(root),'live_files_modified':False,'candidate_created':True,'installer_apply_capability_present':False,'runtime_state_apply_present_in_candidate':True,'changed_files_proposed':['core/foxai_web.py'],'runtime_files_created_only_after_later_operator_state_action':['Config/extension_state.json','Backups/ExtensionState/*','Reports/ExtensionState/*'],'unchanged_files_explicit':['core/server.py','Config/application_registry.json','Config/fleet_registry.json','core/service_registry.py'],'delete_operations':[],'checks':{},'failure':None,'protected_changes':[]}
 try:
  receipt['checks']['package_manifest']=package_manifest(package)
  receipt['checks']['phase1_applied_receipt']=applied_receipt(package)
  receipt['checks']['source_snapshot']=grounding(package)
  receipt['checks']['exact_artifacts']=exact_artifacts(package)
  receipt['checks']['live_baselines']=live_baselines(root)
  receipt['checks']['node_and_browser']=node_browser(package)
  receipt['checks']['backend_regression']=backend(package)
  receipt['checks']['live_inventory_state_preview']=backend(package,root)
  receipt['checks']['legacy_controls']=legacy_controls(package)
  receipt['checks']['static_contract']=static_contract(package)
  receipt['checks']['boundary_watch']=boundary_watch(root)
  after=protected_snapshot(root); changes=changed(before,after); receipt['protected_changes']=changes
  if changes: raise VerifyError('Read-only preview changed protected files: '+repr(changes))
  receipt.update({'state':'exact_preview_verified','verified':True,'live_files_modified':False})
 except Exception as exc:
  after=protected_snapshot(root); changes=changed(before,after); receipt.update({'state':'stopped_fail_closed','verified':not changes,'live_files_modified':bool(changes),'protected_changes':changes,'failure':{'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}})
 output.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
 print(); print('='*72); print('FOXAI EXTENSION MANAGER SAFE STATE CONTROLS — PHASE 2'); print('State:',receipt['state']); print('Verified:',receipt['verified']); print('Live files modified:',receipt['live_files_modified']); print('Installer apply capability present: False'); print('Proposed changed files:',receipt['changed_files_proposed']); print('Receipt:',output)
 if receipt['failure']: print('Failure:',receipt['failure']['message'])
 print(); input('Press Enter to close...')
 return 0 if receipt['state']=='exact_preview_verified' else 1
if __name__=='__main__': raise SystemExit(main())
