from __future__ import annotations
import argparse, ast, hashlib, json, os, shutil, socket, sys, traceback, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SUCCESS="C4A_READY_FOR_CONTROLLED_NODE_IMPORT_REVIEW"
REVIEW="C4A_STATIC_REVIEW_COMPLETE_MANUAL_REVIEW_REQUIRED"
FAILURE="C4A_BLOCKED_FAIL_CLOSED"


def now(): return datetime.now(timezone.utc)
def run_id(): return now().strftime("%Y%m%dT%H%M%SZ")
def sha(path:Path, chunk=4*1024*1024):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while True:
            b=f.read(chunk)
            if not b: break
            h.update(b)
    return h.hexdigest()
def readj(p:Path): return json.loads(p.read_text(encoding='utf-8'))
def writej(p:Path,v:Any):
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2),encoding='utf-8',newline='\n')
def within(p:Path,parent:Path):
    try: p.resolve().relative_to(parent.resolve()); return True
    except ValueError: return False

def verify_package(pkg:Path):
    m=readj(pkg/'PACKAGE_INTEGRITY.json'); rows=[]; issues=[]
    for r in m['files']:
        p=pkg/Path(r['path'])
        if not p.is_file() or p.is_symlink() or not within(p,pkg): issues.append(f"missing/unsafe package file: {r['path']}"); continue
        size=p.stat().st_size; digest=sha(p); ok=size==r['size_bytes'] and digest==r['sha256']
        rows.append({'path':r['path'],'size_bytes':size,'sha256':digest,'verified':ok})
        if not ok: issues.append(f"changed package file: {r['path']}")
    if issues: raise RuntimeError(str(issues[:10]))
    return {'verified':True,'file_count':len(rows),'files':rows}

def tree_digest(rows):
    h=hashlib.sha256()
    for r in rows:
        h.update(r['path'].casefold().encode('utf-8',errors='surrogatepass')); h.update(b'\0')
        h.update(str(r['size_bytes']).encode('ascii')); h.update(b'\0'); h.update(r['sha256'].encode('ascii')); h.update(b'\n')
    return h.hexdigest()

def verify_baseline(root:Path, known):
    pp=root/known['pointer']['relative_path']; pr=known['pointer']
    if not pp.is_file() or pp.is_symlink() or pp.stat().st_size!=pr['size_bytes'] or sha(pp)!=pr['sha256']: raise RuntimeError('Known-good baseline pointer changed')
    pointer=readj(pp)
    if pointer.get('baseline_id')!=known['baseline_id'] or pointer.get('classification')!=known['classification']: raise RuntimeError('Unexpected current baseline identity')
    base=root/known['baseline_relative_path']
    if not base.is_dir() or base.is_symlink(): raise RuntimeError('Baseline directory missing/unsafe')
    actual=[]; expected={r['path'].casefold():r for r in known['baseline_files']}
    for p in sorted(base.rglob('*'),key=lambda x:x.relative_to(base).as_posix().casefold()):
        if p.is_symlink(): raise RuntimeError(f'Baseline symlink: {p}')
        if p.is_file(): actual.append({'path':p.relative_to(base).as_posix(),'size_bytes':p.stat().st_size,'sha256':sha(p)})
    if len(actual)!=known['baseline_file_count'] or tree_digest(actual)!=known['baseline_tree_sha256']: raise RuntimeError('Baseline tree changed')
    for r in actual:
        e=expected.get(r['path'].casefold())
        if not e or r['size_bytes']!=e['size_bytes'] or r['sha256']!=e['sha256']: raise RuntimeError(f'Baseline file changed: {r["path"]}')
    return {'verified':True,'baseline_id':known['baseline_id'],'file_count':len(actual),'tree_sha256':tree_digest(actual),'files':actual}

def verify_stopped(root:Path):
    statep=root/'Runtime/ComfyUI/state/normal_instance.json'; state=readj(statep) if statep.is_file() else {}
    if state.get('status')!='STOPPED': raise RuntimeError(f'Normal controller not STOPPED: {state.get("status")}')
    s=socket.socket();
    try: s.bind(('127.0.0.1',8188))
    except OSError as e: raise RuntimeError(f'Port 8188 not free: {e}')
    finally: s.close()
    return {'verified':True,'status':'STOPPED','port_8188_free':True}

def verify_target(root:Path,known):
    base=root/known['baseline_relative_path']; manifest=readj(base/'ISOLATED_TARGET_MANIFEST.json'); target=root/known['isolated_target']['relative_path']
    if not target.is_dir() or target.is_symlink(): raise RuntimeError('Isolated target missing/unsafe')
    expected_rows=manifest['files']; seen=set(); total=0; aggregate=hashlib.sha256(); issues=[]
    print('[C4A] Re-verifying sealed isolated runtime...',flush=True)
    for i,r in enumerate(expected_rows,1):
        rel=str(r['path']).replace('\\','/'); key=rel.casefold()
        if key in seen: raise RuntimeError(f'Duplicate target path in sealed manifest: {rel}')
        seen.add(key); p=target/Path(rel)
        if not p.is_file() or p.is_symlink() or not within(p,target): issues.append(f'missing/unsafe: {rel}'); continue
        size=p.stat().st_size; digest=sha(p); total+=size
        if size!=r['size_bytes'] or digest!=r['sha256']: issues.append(f'mismatch: {rel}')
        aggregate.update(rel.casefold().encode('utf-8',errors='surrogatepass')); aggregate.update(b'\0'); aggregate.update(str(size).encode('ascii')); aggregate.update(b'\0'); aggregate.update(digest.encode('ascii')); aggregate.update(b'\n')
        if i%1000==0: print(f'  {i:,}/{len(expected_rows):,} files',flush=True)
    actual_paths=[]
    for p in target.rglob('*'):
        if p.is_symlink(): issues.append(f'symlink: {p.relative_to(target)}')
        elif p.is_file(): actual_paths.append(p.relative_to(target).as_posix().casefold())
    unexpected=sorted(set(actual_paths)-seen)
    issues.extend(f'unexpected: {x}' for x in unexpected[:100])
    e=known['isolated_target']; digest=aggregate.hexdigest()
    if issues or len(actual_paths)!=e['file_count'] or total!=e['total_bytes'] or digest!=e['tree_sha256']: raise RuntimeError(f'Isolated runtime differs: issues={issues[:10]} count={len(actual_paths)} bytes={total} tree={digest}')
    return {'verified':True,'file_count':len(actual_paths),'total_bytes':total,'tree_sha256':digest,'missing_or_mismatch_count':0,'unexpected_count':0,'symlink_count':0}

CALL_RULES={
 'process':['subprocess','os.system','os.popen','os.startfile'],
 'network':['socket','requests','urllib','httpx','aiohttp','websocket','websockets','ftplib'],
 'dynamic_code':['eval','exec','compile','__import__','importlib.import_module'],
 'destructive_fs':['os.remove','os.unlink','os.rmdir','shutil.rmtree','pathlib.Path.unlink','pathlib.Path.rmdir'],
 'write_fs':['open','pathlib.Path.write_text','pathlib.Path.write_bytes','shutil.copy','shutil.copy2','shutil.move'],
 'native':['ctypes','cffi','winreg'],
 'package_mutation':['pip','ensurepip','setuptools','git'],
}

def dotted(node):
    if isinstance(node,ast.Name): return node.id
    if isinstance(node,ast.Attribute):
        b=dotted(node.value); return f'{b}.{node.attr}' if b else node.attr
    return ''

def scan_python(path:Path, rel:str, active:bool, available:set[str], comfy_roots:set[str]):
    raw=path.read_bytes(); result={'path':rel,'active_python':active,'size_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'syntax_ok':False,'imports':[],'missing_import_roots':[],'registrations':{},'findings':[],'risk':'LOW'}
    try: text=raw.decode('utf-8-sig')
    except UnicodeDecodeError as e: result['findings'].append({'severity':'HIGH','category':'encoding','detail':str(e)}); result['risk']='HIGH'; return result
    try: tree=ast.parse(text,filename=rel); result['syntax_ok']=True
    except SyntaxError as e: result['findings'].append({'severity':'HIGH','category':'syntax','detail':str(e)}); result['risk']='HIGH'; return result
    imports=set(); calls=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Import): imports.update(a.name.split('.')[0] for a in n.names)
        elif isinstance(n,ast.ImportFrom) and n.module: imports.add(n.module.split('.')[0])
        elif isinstance(n,ast.Call): calls.append((getattr(n,'lineno',None),dotted(n.func)))
        elif isinstance(n,(ast.Assign,ast.AnnAssign)):
            targets=n.targets if isinstance(n,ast.Assign) else [n.target]
            for t in targets:
                if isinstance(t,ast.Name) and t.id in {'NODE_CLASS_MAPPINGS','NODE_DISPLAY_NAME_MAPPINGS','WEB_DIRECTORY'}: result['registrations'][t.id]=True
    result['imports']=sorted(imports)
    std=set(sys.stdlib_module_names); known_local={'comfy','comfy_execution','folder_paths','nodes','server','execution','latent_preview','node_helpers'}|comfy_roots
    result['missing_import_roots']=sorted(x for x in imports if x not in std and x not in available and x not in known_local)
    for line,name in calls:
        low=name.casefold()
        for cat,prefixes in CALL_RULES.items():
            if any(low==p or low.startswith(p+'.') for p in prefixes):
                sev='HIGH' if cat in {'process','dynamic_code','destructive_fs','package_mutation'} else 'MEDIUM'
                result['findings'].append({'severity':sev,'category':cat,'line':line,'call':name})
    # Text-only indicators, no execution.
    for token,cat,sev in [('http://','remote_url','MEDIUM'),('https://','remote_url','MEDIUM'),('NODE_CLASS_MAPPINGS','node_registration','INFO'),('@routes.','server_route','MEDIUM'),('PromptServer.instance.routes','server_route','MEDIUM')]:
        if token in text: result['findings'].append({'severity':sev,'category':cat,'detail':token})
    if result['missing_import_roots']: result['findings'].append({'severity':'HIGH','category':'missing_dependencies','detail':result['missing_import_roots']})
    severities={f['severity'] for f in result['findings']}
    result['risk']='HIGH' if 'HIGH' in severities else ('MEDIUM' if 'MEDIUM' in severities else 'LOW')
    return result

def available_roots(target:Path):
    roots=set()
    for p in target.iterdir():
        if p.is_dir() and not p.name.endswith('.dist-info') and not p.name.endswith('.data'): roots.add(p.name)
        elif p.is_file() and p.suffix in {'.py','.pyd'}: roots.add(p.name.split('.')[0])
    return roots

def node_inventory(root:Path,out:Path,known):
    base=root/known['custom_nodes_relative_path']; target=root/known['isolated_target']['relative_path']
    if not base.is_dir() or base.is_symlink(): raise RuntimeError('custom_nodes missing/unsafe')
    avail=available_roots(target); comfy_roots={p.name for p in (root/'ComfyUI').iterdir() if p.is_dir()}
    rows=[]; analyses=[]; symlinks=[]; total=0; snapshots=out/'SOURCE_SNAPSHOTS'
    for p in sorted(base.rglob('*'),key=lambda x:x.relative_to(base).as_posix().casefold()):
        rel=p.relative_to(base).as_posix()
        if p.is_symlink(): symlinks.append(rel); continue
        if not p.is_file(): continue
        size=p.stat().st_size; digest=sha(p); total+=size
        kind='cache' if '__pycache__' in p.parts or p.suffix=='.pyc' else ('disabled_example' if p.name.endswith('.example') else ('active_python' if p.suffix=='.py' else 'asset'))
        rows.append({'path':rel,'kind':kind,'size_bytes':size,'sha256':digest})
        if size<=2*1024*1024:
            dest=snapshots/rel; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,dest)
        if kind in {'active_python','disabled_example'}:
            analyses.append(scan_python(p,rel,kind=='active_python',avail,comfy_roots))
    if symlinks: raise RuntimeError(f'custom_nodes contains symlinks: {symlinks}')
    high=[a for a in analyses if a['active_python'] and a['risk']=='HIGH']; medium=[a for a in analyses if a['active_python'] and a['risk']=='MEDIUM']
    active=[a for a in analyses if a['active_python']]
    return {'verified':True,'path':str(base),'file_count':len(rows),'total_bytes':total,'symlinks':symlinks,'files':rows,'python_analyses':analyses,'active_python_count':len(active),'active_high_risk_count':len(high),'active_medium_risk_count':len(medium),'executed_or_imported':False}

def cli_controls(root:Path):
    p=root/'ComfyUI/comfy/cli_args.py'
    if not p.is_file() or p.is_symlink(): raise RuntimeError('ComfyUI cli_args.py missing/unsafe')
    text=p.read_text(encoding='utf-8',errors='replace')
    controls={'disable_all_custom_nodes':'--disable-all-custom-nodes' in text,'whitelist_custom_nodes':'--whitelist-custom-nodes' in text,'disable_custom_node':'--disable-custom-node' in text}
    return {'verified':True,'path':str(p),'size_bytes':p.stat().st_size,'sha256':sha(p),'controls':controls}

def verify_integrated(root:Path,known):
    manifest=readj(root/known['baseline_relative_path']/'INTEGRATED_FILES_MANIFEST.json'); rows=[]
    for r in manifest['files']:
        p=root/Path(r['relative_path']); ok=p.is_file() and not p.is_symlink() and p.stat().st_size==r['size_bytes'] and sha(p)==r['sha256']
        rows.append({'relative_path':r['relative_path'],'verified':ok,'sha256':sha(p) if p.is_file() else None})
        if not ok: raise RuntimeError(f'Integrated file changed: {r["relative_path"]}')
    return {'verified':True,'file_count':len(rows),'files':rows}

def make_proposal(out:Path,inv,cli):
    active=[a for a in inv['python_analyses'] if a['active_python']]
    candidates=[{'path':a['path'],'sha256':a['sha256'],'risk':a['risk'],'missing_import_roots':a['missing_import_roots']} for a in active]
    method='native_whitelist' if cli['controls']['whitelist_custom_nodes'] else 'isolated_approved_nodes_view_required'
    contract={
      'schema':1,'status':'PROPOSED_NOT_APPLIED','safe_default_profile':'FOXAI_COMFYUI_SAFE_NORMAL_CPU_V1',
      'proposed_profile':{'id':'FOXAI_COMFYUI_APPROVED_NODES_CPU_V1','label':'Approved Custom Nodes (CPU)','explicit_operator_selection_required':True,'listen':'127.0.0.1:8188','browser_after_health_only':True,'node_activation_method':method,'all_nodes_enable_control':False},
      'webui_behavior':{'profile_selector':True,'default':'Safe Normal CPU','show_node_name_hash_and_audit_status':True,'block_unreviewed_hashes':True,'separate_start_status_stop_receipts':True},
      'candidate_nodes':candidates,
      'next_gate_requirements':['manual review of static findings','dependency closure per active node','controlled no-network import with audit hooks','controlled start/stop test','fresh approval before WebUI integration'],
    }
    d=out/'PROPOSED_NEXT_GATE'; d.mkdir(parents=True,exist_ok=True); writej(d/'APPROVED_NODES_WEBUI_CONTRACT.json',contract)
    return contract

def evidence_zip(out:Path):
    files=[]
    for p in sorted(out.rglob('*'),key=lambda x:x.relative_to(out).as_posix().casefold()):
        if p.is_file() and p.name not in {'UPLOAD_THIS_C4A_REVIEW.zip','evidence_integrity.json'}:
            files.append({'file':p.relative_to(out).as_posix(),'size_bytes':p.stat().st_size,'sha256':sha(p)})
    writej(out/'evidence_integrity.json',{'verified':True,'file_count':len(files),'files':files})
    z=out/'UPLOAD_THIS_C4A_REVIEW.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as h:
        for p in sorted(out.rglob('*'),key=lambda x:x.relative_to(out).as_posix().casefold()):
            if p.is_file() and p!=z: h.write(p,p.relative_to(out).as_posix())
    return z

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,required=True); ap.add_argument('--package',type=Path,required=True); a=ap.parse_args()
    root=a.root.resolve(); pkg=a.package.resolve(); started=now(); out=pkg/'PREFLIGHT_OUTPUT'/run_id(); out.mkdir(parents=True,exist_ok=False)
    classification=FAILURE; blocking=[]
    try:
        if pkg.parent.resolve()!=root: raise RuntimeError('C4A package must be directly under FOXAI root')
        writej(out/'package_verification.json',verify_package(pkg)); known=readj(pkg/'KNOWN_ACCEPTED_C3L_STATE.json')
        writej(out/'baseline_verification.json',verify_baseline(root,known)); writej(out/'stopped_state.json',verify_stopped(root))
        writej(out/'integrated_files_verification.json',verify_integrated(root,known)); writej(out/'isolated_target_verification.json',verify_target(root,known))
        cli=cli_controls(root); writej(out/'comfyui_custom_node_controls.json',cli)
        inv=node_inventory(root,out,known); writej(out/'custom_node_airlock_inventory.json',inv)
        proposal=make_proposal(out,inv,cli); writej(out/'proposed_profile_summary.json',proposal)
        high=inv['active_high_risk_count']
        classification=REVIEW if high else SUCCESS
        receipt={'action':'foxai_usbc4a_custom_node_airlock_static_preflight','started':started.isoformat(),'completed':now().isoformat(),'verified':True,'classification':classification,'baseline_id':known['baseline_id'],'custom_node_files':inv['file_count'],'active_python_nodes':inv['active_python_count'],'active_high_risk':high,'custom_nodes_imported':False,'custom_nodes_executed':False,'launch_performed':False,'network_access':False,'live_change':False,'next_gate':'controlled node import review; Safe Normal CPU remains default'}
        writej(out/'receipt.json',receipt); writej(out/'classification.json',{'mode':classification,'verified':True,'blocking_findings':[],'safe_normal_default_unchanged':True,'webui_approved_nodes_profile_proposed_not_applied':True})
        report=f"""# FOXAI USB C4A — Custom Node Airlock Static Preflight\n\n- Classification: `{classification}`\n- Baseline: `{known['baseline_id']}`\n- Custom-node files: **{inv['file_count']}**\n- Active Python node files: **{inv['active_python_count']}**\n- Active high-risk findings: **{high}**\n- Custom nodes imported/executed: **No**\n- Live files changed: **No**\n\nSafe Normal CPU remains the WebUI default. An Approved Custom Nodes CPU profile was proposed but not applied.\n"""
        (out/'report.md').write_text(report,encoding='utf-8',newline='\n')
    except Exception as e:
        blocking.append(f'{type(e).__name__}: {e}'); writej(out/'classification.json',{'mode':FAILURE,'verified':False,'blocking_findings':blocking}); (out/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        z=evidence_zip(out); print(f'[C4A] Review package: {z}',flush=True)
    return 0 if classification in {SUCCESS,REVIEW} else 19
if __name__=='__main__': raise SystemExit(main())
