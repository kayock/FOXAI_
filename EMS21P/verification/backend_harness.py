from __future__ import annotations
import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path


def make_stubs(root: Path) -> None:
    (root/'core').mkdir(parents=True,exist_ok=True)
    (root/'core/__init__.py').write_text('',encoding='utf-8')
    (root/'core/security_containment.py').write_text('''
def _generic(*a,**k): return {}
def guard_model_action_claims(x): return x
def is_explicit_engineer_command(x): return False
def make_tool_receipt(*a,**k): return {'receipt_id':'stub'}
def new_airlock_correlation_id(): return 'cid'
def validate_airlock_route_receipt(*a,**k): return {'ok':True}
def verify_airlock_audit_log(*a,**k): return {'ok':True}
airlock_chain_alert=authorize_department_route=authorize_repair_action=is_protected_path=record_authorization_decision=record_boundary_denial=record_trip_sentry_test_event=redact_mapping=redact_secrets=_generic
''',encoding='utf-8')
    (root/'core/director.py').write_text('def direct(*a,**k): return {}\n',encoding='utf-8')
    (root/'core/mission_session.py').write_text('''
class MissionSession:
 def __init__(self,*a,**k): pass
 def start(self,**k): return {'ok':True}
 def ensure_started(self,**k): return {'ok':True}
''',encoding='utf-8')
    (root/'core/server.py').write_text('''
class LlamaServer:
 def __init__(self,*a,**k): pass
''',encoding='utf-8')


def import_candidate(candidate: Path, root: Path, module_name: str):
    make_stubs(root)
    target=root/'core/foxai_web.py'
    shutil.copy2(candidate,target)
    sys.path.insert(0,str(root))
    try:
        spec=importlib.util.spec_from_file_location(module_name,target)
        module=importlib.util.module_from_spec(spec)
        sys.modules[module_name]=module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        try: sys.path.remove(str(root))
        except ValueError: pass


def base_layout(root: Path) -> None:
    for relative in ('Config','Engine','ui','tests','Models/Chat','ComfyUI/models/checkpoints'):
        (root/relative).mkdir(parents=True,exist_ok=True)
    (root/'Engine/llama-server.exe').write_bytes(b'engine')
    (root/'ui/main_window.py').write_text('# stub\n',encoding='utf-8')
    (root/'tests/test_boundary_watch.py').write_text('# stub\n',encoding='utf-8')
    for name in ('application_registry.py','department_registry.py','service_registry.py'):
        (root/'core'/name).write_text('# stub\n',encoding='utf-8')
    (root/'Config/application_registry.json').write_text(json.dumps({'applications':[]}),encoding='utf-8')
    (root/'Config/fleet_registry.json').write_text(json.dumps({'mode':'passive','shuttles':{}}),encoding='utf-8')
    (root/'Config/FoxAI.ini').write_text('',encoding='utf-8')


def write_manifest(root: Path, key: str, raw: dict) -> Path:
    folder=root/'Extensions'/'Harness'/key
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/'extension.json'
    path.write_text(json.dumps(raw,indent=2),encoding='utf-8')
    return path


def apply_request(preview: dict, phrase: str|None=None) -> dict:
    return {
        'target':preview['target'],
        'action':preview['action'],
        'proposal_time':preview['proposal_time'],
        'preview_digest':preview['preview_digest'],
        'approval_phrase':preview['approval_phrase'] if phrase is None else phrase,
    }


def fake_regression(candidate: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix='ems2_fake_') as temp:
        root=Path(temp)
        make_stubs(root); base_layout(root)
        write_manifest(root,'base',{'key':'base','name':'Base','version':'1.0','kind':'extension','enabled':True})
        write_manifest(root,'child',{'key':'child','name':'Child','version':'1.0','kind':'extension','enabled':True,'depends_on':['base']})
        write_manifest(root,'disabled',{'key':'disabled','name':'Disabled','version':'1.0','kind':'extension','enabled':False})
        write_manifest(root,'required',{'key':'required','name':'Required','version':'1.0','kind':'extension','enabled':True,'required':True})
        mod=import_candidate(candidate,root,'core.foxai_web_ems2_fake')
        state=root/'Config/extension_state.json'
        assert not state.exists()
        blocked=mod.extension_state_change_preview({'target':'base','action':'disable'})
        assert blocked['ok'] and not blocked['can_apply'] and 'child' in ' '.join(blocked['blockers'])
        preview=mod.extension_state_change_preview({'target':'child','action':'disable'})
        assert preview['ok'] and preview['can_apply'] and not state.exists()
        assert preview['approval_phrase']=='APPROVE EXTENSION STATE DISABLE CHILD'
        wrong=mod.apply_extension_state_change(apply_request(preview,'WRONG'))
        assert not wrong['ok'] and not state.exists()
        applied=mod.apply_extension_state_change(apply_request(preview))
        assert applied['ok'] and applied['verified'] and state.is_file()
        assert Path(applied['backup_path']).is_file() and Path(applied['receipt_path']).is_file()
        doc=json.loads(state.read_text(encoding='utf-8'))
        assert doc['child']['enabled'] is False and doc['_meta']['override_count']==1
        base_preview=mod.extension_state_change_preview({'target':'base','action':'disable'})
        assert base_preview['can_apply']
        base_applied=mod.apply_extension_state_change(apply_request(base_preview))
        assert base_applied['ok']
        enable_child=mod.extension_state_change_preview({'target':'child','action':'enable'})
        assert not enable_child['can_apply'] and 'base' in ' '.join(enable_child['blockers'])
        restore_base=mod.extension_state_change_preview({'target':'base','action':'restore'})
        assert restore_base['can_apply']
        assert mod.apply_extension_state_change(apply_request(restore_base))['ok']
        restore_child=mod.extension_state_change_preview({'target':'child','action':'restore'})
        assert restore_child['can_apply']
        restored=mod.apply_extension_state_change(apply_request(restore_child))
        assert restored['ok'] and not state.exists()
        required=mod.extension_state_change_preview({'target':'required','action':'disable'})
        assert required['ok'] and not required['can_apply']
        direct=mod.toggle_extension({'key':'child','enabled':False})
        assert not direct['ok'] and direct['state']=='blocked_safe_preview_required' and not state.exists()
        expired=mod._extension_state_preview_contract('child','disable','2000-01-01T00:00:00')
        assert not expired['ok'] and 'expired' in expired['message'].lower()
        inventory=mod.extension_inventory_snapshot()
        assert inventory['summary']['state_controls']==3 and inventory['summary']['state_overrides']==0
        assert inventory['guarded_state_write_available'] is True and inventory['read_only'] is True

    with tempfile.TemporaryDirectory(prefix='ems2_rollback_') as temp:
        root=Path(temp)
        make_stubs(root); base_layout(root)
        write_manifest(root,'solo',{'key':'solo','name':'Solo','version':'1.0','kind':'extension','enabled':True})
        (root/'Reports').mkdir(exist_ok=True)
        (root/'Reports/ExtensionState').write_text('block receipt directory',encoding='utf-8')
        mod=import_candidate(candidate,root,'core.foxai_web_ems2_rollback')
        preview=mod.extension_state_change_preview({'target':'solo','action':'disable'})
        result=mod.apply_extension_state_change(apply_request(preview))
        assert not result['ok'] and result['state']=='rolled_back_verified' and result['verified'] is True
        assert not (root/'Config/extension_state.json').exists()

    with tempfile.TemporaryDirectory(prefix='ems2_invalid_') as temp:
        root=Path(temp)
        make_stubs(root); base_layout(root)
        write_manifest(root,'solo',{'key':'solo','name':'Solo','version':'1.0','kind':'extension','enabled':True})
        (root/'Config/extension_state.json').write_text('{bad json',encoding='utf-8')
        mod=import_candidate(candidate,root,'core.foxai_web_ems2_invalid')
        result=mod.extension_state_change_preview({'target':'solo','action':'disable'})
        assert not result['ok'] and result['state']=='blocked_invalid_state'
        assert (root/'Config/extension_state.json').read_text(encoding='utf-8')=='{bad json'

    return {
        'passed':True,
        'preview_is_read_only':True,
        'wrong_phrase_no_write':True,
        'optional_disable_apply_verified':True,
        'backup_and_receipt_verified':True,
        'dependency_disable_blocked':True,
        'disabled_dependency_enable_blocked':True,
        'required_extension_blocked':True,
        'restore_default_removes_final_state_file':True,
        'legacy_direct_toggle_blocked':True,
        'expired_preview_blocked':True,
        'receipt_failure_rolls_back':True,
        'malformed_state_fails_closed':True,
    }


def patch_live(module, live: Path) -> None:
    module.ROOT=live
    module.PROJECT_ROOT=live
    module.DRIVE=Path(live.anchor)
    module.COMFY=live/'ComfyUI'
    module.COMFY_MAIN=module.COMFY/'main.py'
    module.ENGINE=live/'Engine/llama-server.exe'
    module.LIB=live/'Library'
    module.PROJECTS=live/'Projects'
    module.LOGS=live/'Logs'
    module.FOLDERS.update({
        'root':live,'models':live/'Models','chat_models':live/'Models/Chat',
        'config':live/'Config','extensions':live/'Extensions','modules':live/'Modules',
        'reports':live/'Reports','logs':live/'Logs',
    })


def live_preview(candidate: Path, live: Path) -> dict:
    state=live/'Config/extension_state.json'
    before=state.read_bytes() if state.is_file() else None
    with tempfile.TemporaryDirectory(prefix='ems2_live_import_') as temp:
        import_root=Path(temp)
        mod=import_candidate(candidate,import_root,'core.foxai_web_ems2_live')
        patch_live(mod,live)
        inventory=mod.extension_inventory_snapshot()
        preview=mod.extension_state_change_preview({'target':'database','action':'disable'})
        direct=mod.toggle_extension({'key':'database','enabled':False})
    after=state.read_bytes() if state.is_file() else None
    assert before==after and before is None
    assert inventory['summary']['total']==44
    assert inventory['summary']['state_controls']==6
    assert inventory['summary']['state_overrides']==0
    assert inventory['sources']['extension_state']['exists'] is False
    assert inventory['summary']['model_scan']['projectors_filtered_from_language_models'] is True
    assert preview['ok'] and preview['can_apply'] and preview['state_file_effect']=='create override file'
    assert not direct['ok'] and direct['state']=='blocked_safe_preview_required'
    return {
        'passed':True,
        'summary':inventory['summary'],
        'state_file_unchanged':True,
        'state_file_exists':False,
        'database_disable_preview':{
            'can_apply':preview['can_apply'],
            'approval_phrase':preview['approval_phrase'],
            'state_file_effect':preview['state_file_effect'],
            'configuration_modified':preview['configuration_modified'],
        },
        'legacy_direct_toggle_blocked':True,
        'projector_separate':inventory['summary']['model_scan']['projectors_filtered_from_language_models'],
    }


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument('candidate',type=Path)
    parser.add_argument('--live-root',type=Path)
    args=parser.parse_args()
    result=live_preview(args.candidate,args.live_root) if args.live_root else fake_regression(args.candidate)
    print(json.dumps(result,indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())
