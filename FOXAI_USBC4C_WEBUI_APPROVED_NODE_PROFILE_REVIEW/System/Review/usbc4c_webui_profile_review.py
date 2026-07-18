#!/usr/bin/env python3
"""USB C4C read-only WebUI approved-node profile review."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import sys
from typing import Any
import zipfile

EXPECTED_CLASSIFICATION = "C4B_ALLOWLISTED_NODE_VERIFIED_STOPPED_READY_FOR_C4C_WEBUI_PROFILE_REVIEW"
SUCCESS_CLASSIFICATION = "C4C_READY_FOR_C4D_WEBUI_PROFILE_APPLY_APPROVAL"

class ReviewError(RuntimeError):
    pass

def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()

def run_id() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def sha256_file(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(4*1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding='utf-8', newline='\n')

def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        raise ReviewError(f"Could not read JSON {path}: {type(exc).__name__}: {exc}") from exc

def resolve_dir(raw: str, label: str) -> Path:
    path=Path(raw).resolve(strict=True)
    if not path.is_dir() or path.is_symlink():
        raise ReviewError(f"{label} is missing or unsafe: {path}")
    return path

def verify_package(package: Path) -> dict[str, Any]:
    manifest=read_json(package/'PACKAGE_INTEGRITY.json')
    rows=[]
    for record in manifest.get('files',[]):
        path=package/record['path']
        ok=path.is_file() and not path.is_symlink()
        actual_size=path.stat().st_size if ok else None
        actual_hash=sha256_file(path) if ok else None
        verified=ok and actual_size==record['size_bytes'] and actual_hash==record['sha256']
        rows.append({'path':record['path'],'verified':verified,'actual_size':actual_size,'actual_sha256':actual_hash})
        if not verified:
            raise ReviewError(f"Package integrity failed: {record['path']}")
    return {'verified':True,'file_count':len(rows),'files':rows}

def verify_c4b(root: Path, package: Path) -> dict[str, Any]:
    accepted=read_json(package/'AcceptedEvidence/ACCEPTED_C4B_EVIDENCE.json')
    folder=root/'FOXAI_USBC4B_ALLOWLISTED_NODE_LIFECYCLE_TEST'/'TEST_OUTPUT'/accepted['accepted_run_id']
    if not folder.is_dir() or folder.is_symlink():
        raise ReviewError(f"Accepted C4B evidence folder is missing: {folder}")
    rows=[]
    for record in accepted['evidence_files']:
        path=folder/record['file']
        ok=path.is_file() and not path.is_symlink()
        actual_size=path.stat().st_size if ok else None
        actual_hash=sha256_file(path) if ok else None
        verified=ok and actual_size==record['size_bytes'] and actual_hash==record['sha256']
        rows.append({'file':record['file'],'verified':verified,'actual_size':actual_size,'actual_sha256':actual_hash})
        if not verified:
            raise ReviewError(f"Accepted C4B evidence changed: {record['file']}")
    classification=read_json(folder/'classification.json')
    receipt=read_json(folder/'receipt.json')
    if classification.get('mode')!=EXPECTED_CLASSIFICATION or classification.get('verified') is not True:
        raise ReviewError('C4B classification is not the accepted verified result')
    if receipt.get('verified') is not True or receipt.get('left_running') is not False:
        raise ReviewError('C4B receipt does not prove verified stopped state')
    return {'verified':True,'folder':str(folder),'evidence_file_count':len(rows),'classification':classification,'receipt':receipt,'files':rows}

def verify_node(root: Path, package: Path) -> dict[str, Any]:
    accepted=read_json(package/'AcceptedEvidence/ACCEPTED_C4B_EVIDENCE.json')['approved_node']
    path=root/accepted['relative_path']
    if not path.is_file() or path.is_symlink():
        raise ReviewError('Approved custom node is missing or unsafe')
    result={'path':str(path),'relative_path':accepted['relative_path'],'size_bytes':path.stat().st_size,'sha256':sha256_file(path),**{k:v for k,v in accepted.items() if k not in {'relative_path','size_bytes','sha256'}}}
    result['verified']=result['size_bytes']==accepted['size_bytes'] and result['sha256']==accepted['sha256']
    if not result['verified']:
        raise ReviewError('Approved custom-node identity changed')
    return result

def verify_target(root: Path, package: Path) -> dict[str, Any]:
    accepted=read_json(package/'AcceptedEvidence/ACCEPTED_C4B_EVIDENCE.json')
    baseline=accepted['baseline']
    manifest_path=root/baseline['manifest_relative_path']
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ReviewError('Sealed baseline target manifest is missing or unsafe')
    if sha256_file(manifest_path)!=baseline['manifest_sha256']:
        raise ReviewError('Sealed baseline target manifest hash changed')
    manifest=read_json(manifest_path)
    expected=accepted['isolated_target']
    if any(manifest.get(key)!=expected[value] for key,value in [('file_count','file_count'),('total_bytes','total_bytes'),('tree_sha256','tree_sha256')]):
        raise ReviewError('Sealed target manifest summary changed')
    target=root/expected['relative_path']
    if not target.is_dir() or target.is_symlink():
        raise ReviewError('Isolated target is missing or unsafe')
    actual_paths={p.relative_to(target).as_posix().casefold():p for p in target.rglob('*') if p.is_file() and not p.is_symlink()}
    if len(actual_paths)!=expected['file_count']:
        raise ReviewError(f"Target file count changed: {len(actual_paths)}")
    missing=[]; mismatches=[]; total=0; digest=hashlib.sha256(); seen=set()
    for index,row in enumerate(manifest['files'],1):
        key=str(row['path']).replace('\\','/').casefold()
        if key in seen:
            raise ReviewError(f"Duplicate baseline path: {row['path']}")
        seen.add(key)
        path=actual_paths.get(key)
        if path is None:
            missing.append(row['path']); continue
        size=path.stat().st_size; file_hash=sha256_file(path); total+=size
        if size!=row['size_bytes'] or file_hash!=row['sha256']:
            mismatches.append({'path':row['path'],'size':size,'sha256':file_hash})
        digest.update(str(row['path']).casefold().encode('utf-8')); digest.update(b'\0')
        digest.update(str(size).encode('ascii')); digest.update(b'\0'); digest.update(file_hash.encode('ascii')); digest.update(b'\n')
        if index%1000==0:
            print(f"[C4C] Verified {index}/{expected['file_count']} isolated files...", flush=True)
    unexpected=sorted(set(actual_paths)-seen)
    tree=digest.hexdigest()
    verified=not missing and not unexpected and not mismatches and total==expected['total_bytes'] and tree==expected['tree_sha256']
    result={'verified':verified,'target':str(target),'file_count':len(actual_paths),'total_bytes':total,'tree_sha256':tree,'missing':missing,'unexpected':unexpected,'mismatches':mismatches}
    if not verified:
        raise ReviewError('Isolated target did not match the sealed known-good baseline')
    return result

def verify_live(root: Path, package: Path, phase: str) -> dict[str, Any]:
    expected=read_json(package/'AcceptedEvidence/EXPECTED_LIVE_SURFACES.json')['files']
    rows=[]
    for record in expected:
        path=root/record['path']
        ok=path.is_file() and not path.is_symlink()
        size=path.stat().st_size if ok else None
        digest=sha256_file(path) if ok else None
        verified=ok and size==record['size_bytes'] and digest==record['sha256']
        rows.append({'path':record['path'],'size_bytes':size,'sha256':digest,'verified':verified})
        if not verified:
            raise ReviewError(f"Reviewed live surface changed: {record['path']}")
    return {'verified':True,'phase':phase,'file_count':len(rows),'files':rows}

def process_safety(root: Path) -> dict[str, Any]:
    target=root/'Runtime/ComfyUI/site-packages'
    sys.path.insert(0,str(target))
    try:
        import psutil  # type: ignore
    except Exception as exc:
        raise ReviewError(f"Could not load trusted psutil for process review: {exc}") from exc
    listeners=[]
    for item in psutil.net_connections(kind='tcp'):
        local=getattr(item,'laddr',None)
        if not local: continue
        port=getattr(local,'port',local[1] if len(local)>1 else 0)
        if int(port or 0)==8188 and str(getattr(item,'status','')).upper()=='LISTEN':
            ip=getattr(local,'ip',local[0] if len(local)>0 else '')
            listeners.append({'ip':str(ip),'port':8188,'pid':getattr(item,'pid',None)})
    state=root/'Runtime/ComfyUI/state/normal_instance.json'
    state_data=read_json(state) if state.is_file() else None
    if listeners:
        raise ReviewError(f"Port 8188 must be free for C4C review: {listeners}")
    return {'verified':True,'port_8188_free':True,'listeners':listeners,'state_file_exists':state.is_file(),'recorded_state':state_data}

def inspect_webui(root: Path, output: Path) -> dict[str, Any]:
    manager=root/'System/PortableRuntime/manage_comfyui_normal.py'
    policy=root/'System/PortableRuntime/COMFYUI_NORMAL_POLICY.json'
    web=root/'core/foxai_web.py'
    for path in (manager,policy,web):
        if not path.is_file() or path.is_symlink():
            raise ReviewError(f"Required profile surface is missing or unsafe: {path}")
    snapshots=output/'SOURCE_SNAPSHOTS'
    snapshots.mkdir(parents=True,exist_ok=True)
    for path in (manager,policy,web):
        rel=path.relative_to(root)
        dest=snapshots/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,dest)
    manager_text=manager.read_text(encoding='utf-8',errors='replace')
    web_text=web.read_text(encoding='utf-8',errors='replace')
    policy_data=read_json(policy)
    observations={
        'verified':True,
        'safe_profile_is_default': policy_data.get('default_profile')=='Safe Normal CPU',
        'custom_nodes_currently_disabled': '--disable-all-custom-nodes' in manager_text,
        'manager_has_profile_selector': '--profile' in manager_text or 'profile_id' in manager_text,
        'webui_has_profile_selector': 'comfyProfile' in web_text or 'Approved Custom Nodes CPU' in web_text,
        'webui_has_start_status_stop_open': all(token in web_text for token in ['/api/launch/comfy','/api/status/comfy','/api/stop/comfy','/api/open-url/comfy']),
        'current_get_start_is_safe_default': "if path=='/api/launch/comfy'" in web_text and "comfy_normal_call('spawn'" in web_text,
        'current_manager_sha256':sha256_file(manager),
        'current_policy_sha256':sha256_file(policy),
        'current_webui_sha256':sha256_file(web),
        'snapshot_folder':str(snapshots),
    }
    if not observations['safe_profile_is_default'] or not observations['custom_nodes_currently_disabled']:
        raise ReviewError('Current safe-default policy did not match accepted C3/C4 expectations')
    return observations

def proposal(root: Path, node: dict[str, Any], web: dict[str, Any]) -> tuple[dict[str, Any],dict[str,Any]]:
    contract={
        'contract_id':'FOXAI_COMFYUI_DUAL_CPU_PROFILE_V1',
        'default_profile_id':'safe-normal-cpu',
        'profiles':[
            {
                'id':'safe-normal-cpu','display_name':'Safe Normal CPU','default':True,
                'arguments':['--cpu','--disable-all-custom-nodes','--listen','127.0.0.1','--port','8188'],
                'custom_nodes':'none','browser':'WebUI Open remains separate',
            },
            {
                'id':'approved-custom-nodes-cpu','display_name':'Approved Custom Nodes CPU','default':False,
                'arguments':['--cpu','--disable-all-custom-nodes','--whitelist-custom-nodes','websocket_image_save.py','--listen','127.0.0.1','--port','8188'],
                'approved_nodes':[{
                    'filename':node['filename'],'relative_path':node['relative_path'],'sha256':node['sha256'],
                    'class_key':node['class_key'],'display_name':node['display_name'],'audit_state':'C4B_VERIFIED',
                }],
                'browser':'WebUI Open remains separate',
            },
        ],
        'webui_behavior':{
            'selector_label':'ComfyUI Profile',
            'selector_default_each_page_load':'safe-normal-cpu',
            'do_not_persist_approved_profile':True,
            'start_action':'POST /api/launch/comfy/profile with JSON {profile_id}',
            'legacy_get_start':'GET /api/launch/comfy remains Safe Normal CPU for compatibility',
            'status_display':['state','active_profile_id','active_profile_name','approved_node_hash_state'],
            'stop_action':'unchanged controller-owned graceful stop',
            'open_action':'unchanged separate browser Open action',
        },
        'controller_requirements':{
            'profile_argument':'--profile on start and spawn; omitted means safe-normal-cpu',
            'hash_checks':['approved node immediately before process creation','approved node after verified health'],
            'state_binding':['profile id','profile display name','exact child command fingerprint','approved node path, size, and SHA-256'],
            'profile_switch_rule':'If a different profile is already HEALTHY, refuse and require operator stop first.',
            'unknown_profile_rule':'Fail closed.',
            'changed_node_rule':'Fail closed before launch.',
            'unreviewed_nodes':'Remain disabled.',
            'listen':'127.0.0.1:8188 only',
        },
        'safety':{
            'safe_profile_unchanged':True,'approved_profile_explicit_only':True,'custom_node_install':False,
            'network_policy_change':False,'force_kill':False,'automatic_log_deletion':False,
        },
    }
    scope={
        'stage':'C4D controlled WebUI profile apply (no launch)',
        'replace':[{
            'path':'System/PortableRuntime/manage_comfyui_normal.py','current_sha256':web['current_manager_sha256'],
            'purpose':'Add exact profile selection, node hash locking, state identity, and profile-conflict handling.'},
            {'path':'System/PortableRuntime/COMFYUI_NORMAL_POLICY.json','current_sha256':web['current_policy_sha256'],
             'purpose':'Record both profiles while preserving Safe Normal CPU as default.'},
            {'path':'core/foxai_web.py','current_sha256':web['current_webui_sha256'],
             'purpose':'Add explicit profile selector and profile-aware start receipt/status display.'}],
        'add':[{'path':'START_COMFYUI_APPROVED_NODES.bat','purpose':'Optional explicit direct start for the exact approved profile; never replaces the safe default BAT.'}],
        'unchanged':['START_COMFYUI_NORMAL.bat','STATUS_COMFYUI_NORMAL.bat','STOP_COMFYUI_NORMAL.bat','System/PortableRuntime/launch_comfyui_isolated.py','ComfyUI/main.py','ComfyUI/custom_nodes/websocket_image_save.py','Runtime/ComfyUI/site-packages'],
        'apply_controls':['fresh explicit C4D approval','exact current hashes','backup all replacements','stage all candidates','atomic replace','automatic exact rollback on partial failure','no launch during C4D'],
        'later_test':'C4E must test both profiles through WebUI/controller and leave ComfyUI stopped.',
    }
    return contract,scope

def make_review_zip(output: Path) -> Path:
    destination=output/'UPLOAD_THIS_C4C_REVIEW.zip'
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in sorted(output.rglob('*')):
            if path.is_file() and path!=destination:
                archive.write(path,path.relative_to(output).as_posix())
    return destination

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True); parser.add_argument('--package',required=True)
    args=parser.parse_args()
    root=resolve_dir(args.root,'FOXAI root'); package=resolve_dir(args.package,'C4C package')
    output=package/'REVIEW_OUTPUT'/run_id(); output.mkdir(parents=True,exist_ok=False)
    started=utc_now(); classification='C4C_BLOCKED_FAIL_CLOSED'; blocking=[]
    try:
        print('[C4C] Verifying sealed review package...',flush=True)
        write_json(output/'package_verification.json',verify_package(package))
        print('[C4C] Binding to accepted C4B evidence...',flush=True)
        write_json(output/'c4b_input_verification.json',verify_c4b(root,package))
        safety=process_safety(root); write_json(output/'process_safety.json',safety)
        node=verify_node(root,package); write_json(output/'approved_node_verification.json',node)
        before=verify_live(root,package,'before'); write_json(output/'live_surfaces_before.json',before)
        print('[C4C] Re-verifying the sealed isolated runtime...',flush=True)
        target=verify_target(root,package); write_json(output/'isolated_target_reverification.json',target)
        web=inspect_webui(root,output); write_json(output/'current_webui_profile_surface.json',web)
        contract,apply_scope=proposal(root,node,web)
        write_json(output/'PROPOSED_C4D_CHANGESET/APPROVED_NODE_PROFILE_CONTRACT.json',contract)
        write_json(output/'PROPOSED_C4D_CHANGESET/C4D_APPLY_SCOPE.json',apply_scope)
        after=verify_live(root,package,'after'); write_json(output/'live_surfaces_after.json',after)
        comparison={'verified':before['files']==after['files'],'changes':[] if before['files']==after['files'] else ['live surface changed during review']}
        write_json(output/'live_surface_comparison.json',comparison)
        if not comparison['verified']:
            raise ReviewError('A live surface changed during C4C review')
        classification=SUCCESS_CLASSIFICATION
    except Exception as exc:
        blocking.append(f"{type(exc).__name__}: {exc}")
    verified=classification==SUCCESS_CLASSIFICATION and not blocking
    classification_data={'mode':classification,'verified':verified,'blocking_findings':blocking,'live_change':False,'network_access':False,'comfyui_launched':False,'custom_node_imported':False,'next_gate':'C4D requires fresh explicit operator approval and remains no-launch.' if verified else 'Review blocker before C4D.'}
    write_json(output/'classification.json',classification_data)
    receipt={'action':'foxai_usbc4c_webui_approved_node_profile_review','started':started,'completed':utc_now(),'root':str(root),'output':str(output),'verified':verified,'classification':classification,'approved_node_profile_proposed':verified,'live_change':False,'launcher_change':False,'runtime_change':False,'package_change':False,'network_access':False,'foxai_launched':False,'webui_launched':False,'comfyui_launched':False,'blocking_findings':blocking}
    write_json(output/'receipt.json',receipt)
    report=(f"# FOXAI USB C4C — WebUI Approved Custom-Node Profile Review\n\n- Classification: `{classification}`\n- Verified: `{verified}`\n- Live changes: **0**\n- ComfyUI launched: **False**\n- Approved node imported: **False**\n\n")
    if verified:
        report += "C4C approved the exact two-profile design for later C4D no-launch apply. Safe Normal CPU remains the default; Approved Custom Nodes CPU is explicit and hash-locked.\n"
    else:
        report += "## Blocking findings\n\n"+'\n'.join(f'- {x}' for x in blocking)+'\n'
    (output/'report.md').write_text(report,encoding='utf-8',newline='\n')
    files=[]
    for path in sorted(output.rglob('*')):
        if path.is_file() and path.name not in {'evidence_integrity.json','UPLOAD_THIS_C4C_REVIEW.zip'}:
            files.append({'file':path.relative_to(output).as_posix(),'size_bytes':path.stat().st_size,'sha256':sha256_file(path)})
    write_json(output/'evidence_integrity.json',{'verified':True,'file_count':len(files),'files':files})
    review_zip=make_review_zip(output)
    print(f"[{'COMPLETE' if verified else 'STOPPED'}] {classification}",flush=True)
    print(f"Review package: {review_zip}",flush=True)
    return 0 if verified else 19

if __name__=='__main__':
    raise SystemExit(main())
