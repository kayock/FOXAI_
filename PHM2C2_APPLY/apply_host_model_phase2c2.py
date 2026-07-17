from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import argparse
import difflib
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import traceback
from typing import Any

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
PLAN = json.loads((PACKAGE / 'APPLY_PLAN.json').read_text(encoding='utf-8'))
CANDIDATE = PACKAGE / 'candidate'
APPROVAL_PHRASE = PLAN['approval_phrase']
TARGET_MODIFIED = list(PLAN['modified'])
TARGET_ADDED = list(PLAN['added'])
TARGETS = TARGET_MODIFIED + TARGET_ADDED
PORT_REQUIRED_CLOSED = 8765
PRIORITY_MACHINE = 'DESKTOP-G9ERN9B'
PRIORITY_MODEL = Path(r'C:\KayockModels\General\Qwen3-30B-A3B\Qwen3-30B-A3B-Q4_K_M.gguf')


class ApplyError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def file_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {'exists': False, 'sha256': None, 'size_bytes': 0}
    if not path.is_file():
        return {'exists': True, 'not_file': True, 'sha256': None}
    stat = path.stat()
    return {
        'exists': True,
        'sha256': sha256(path),
        'size_bytes': stat.st_size,
        'modified_ns': stat.st_mtime_ns,
    }


def machine_name() -> str:
    return str(os.environ.get('COMPUTERNAME') or platform.node() or 'UNKNOWN').strip().upper()


def bundled_python_check() -> dict[str, Any]:
    expected = (ROOT / 'env/python/python.exe').resolve()
    actual = Path(sys.executable).resolve()
    passed = expected == actual
    result = {'passed': passed, 'expected': str(expected), 'actual': str(actual), 'version': sys.version}
    if not passed:
        raise ApplyError('Guarded apply is not running under FOXAI bundled Python.')
    return result


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.35)
        return sock.connect_ex(('127.0.0.1', port)) == 0


def package_manifest_check() -> dict[str, Any]:
    manifest = PACKAGE / 'PACKAGE_SHA256SUMS.txt'
    if not manifest.is_file():
        raise ApplyError('Package manifest is missing.')
    checks = []
    for line in manifest.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        expected, relative = line.split('  ', 1)
        path = PACKAGE / relative
        actual = sha256(path) if path.is_file() else None
        checks.append({'path': relative, 'expected': expected, 'actual': actual, 'ok': actual == expected})
    if not checks or not all(item['ok'] for item in checks):
        raise ApplyError('Package manifest verification failed.')
    return {'passed': True, 'files': checks}


def verify_grounding() -> dict[str, Any]:
    expected = PLAN['grounding']
    paths = {
        'success_receipt': PACKAGE / 'grounding/PHM2C2_SUCCESS_RECEIPT.json',
        'success_report': PACKAGE / 'grounding/PHM2C2_SUCCESS_REPORT.md',
        'preview_plan': PACKAGE / 'grounding/EXACT_PREVIEW_PLAN.json',
    }
    checks = {
        'success_receipt_sha256': sha256(paths['success_receipt']),
        'success_report_sha256': sha256(paths['success_report']),
        'preview_plan_sha256': sha256(paths['preview_plan']),
    }
    if checks['success_receipt_sha256'] != expected['success_receipt_sha256']:
        raise ApplyError('Approved exact-preview receipt hash changed.')
    if checks['success_report_sha256'] != expected['success_report_sha256']:
        raise ApplyError('Approved exact-preview report hash changed.')
    if checks['preview_plan_sha256'] != expected['preview_plan_sha256']:
        raise ApplyError('Exact-preview plan hash changed.')
    receipt = json.loads(paths['success_receipt'].read_text(encoding='utf-8'))
    required = {
        'state': receipt.get('state') == 'exact_preview_verified',
        'verified': receipt.get('verified') is True,
        'apply_absent': receipt.get('apply_capability_present') is False,
        'live_unmodified': receipt.get('live_files_modified') is False,
        'models_unmodified': receipt.get('model_files_modified') is False,
        'tests_10': (receipt.get('checks', {}).get('model_source_tests', {}).get('passed') is True and receipt.get('checks', {}).get('model_source_tests', {}).get('tests') == 10),
        'javascript': receipt.get('checks', {}).get('embedded_javascript', {}).get('passed') is True,
        'integration': receipt.get('checks', {}).get('integration_contract', {}).get('passed') is True,
        'candidate_hashes': {
            item['path']: item['actual'] for item in receipt.get('checks', {}).get('candidate_hashes', {}).get('files', [])
        } == PLAN['candidate_hashes'],
    }
    if not all(required.values()):
        raise ApplyError('Approved exact-preview receipt is not fully verified.')

    live_matches = []
    preview_root = ROOT / 'Reports/HostModelPreview'
    if preview_root.is_dir():
        for path in preview_root.glob('PHM2C2_*/receipt.json'):
            try:
                if sha256(path) == expected['required_live_preview_receipt_hash']:
                    live_matches.append(str(path))
            except OSError:
                pass
    if not live_matches:
        raise ApplyError('The exact approved preview receipt was not found under Reports\\HostModelPreview.')
    return {'passed': True, 'hashes': checks, 'receipt_contract': required, 'live_receipt_matches': live_matches}


def verify_live_baselines(*, before_apply: bool) -> dict[str, Any]:
    checks = []
    for relative, expected in PLAN['baselines'].items():
        if not before_apply and relative in TARGET_MODIFIED:
            continue
        path = ROOT / relative
        actual = sha256(path) if path.is_file() else None
        checks.append({'path': relative, 'expected': expected, 'actual': actual, 'ok': actual == expected})
    if not all(item['ok'] for item in checks):
        stage = 'before' if before_apply else 'after'
        raise ApplyError(f'A locked live baseline changed {stage} the transaction.')
    if before_apply:
        absence = [{'path': rel, 'absent': not (ROOT / rel).exists()} for rel in PLAN['expected_absent']]
        if not all(item['absent'] for item in absence):
            raise ApplyError('One or more approved new files already exist. No apply occurred.')
    else:
        absence = []
    return {'passed': True, 'files': checks, 'expected_absent': absence}


def candidate_hash_check() -> dict[str, Any]:
    checks = []
    for relative, expected in PLAN['candidate_hashes'].items():
        path = CANDIDATE / relative
        actual = sha256(path) if path.is_file() else None
        checks.append({'path': relative, 'expected': expected, 'actual': actual, 'ok': actual == expected})
    if not all(item['ok'] for item in checks):
        raise ApplyError('Candidate hash verification failed.')
    diff_path = PACKAGE / 'EXACT_DIFF_core_foxai_web.py.diff'
    if sha256(diff_path) != PLAN['exact_diff_sha256']:
        raise ApplyError('Exact diff hash changed.')
    return {'passed': True, 'files': checks, 'diff_hash_verified': True}


def python_compile_check(base: Path) -> dict[str, Any]:
    files = ['core/foxai_web.py', 'core/model_sources.py', 'tests/test_model_sources.py']
    for relative in files:
        path = base / relative
        compile(path.read_text(encoding='utf-8'), str(path), 'exec')
    json.loads((base / 'Config/model_sources.json').read_text(encoding='utf-8'))
    return {'passed': True, 'files': files}


def child_env() -> dict[str, str]:
    env = os.environ.copy()
    env['PYTHONNOUSERSITE'] = '1'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def run_model_source_tests(project_root: Path, label: str) -> dict[str, Any]:
    runner = (
        "import sys,unittest;"
        "sys.dont_write_bytecode=True;"
        "sys.path.insert(0,sys.argv[1]);"
        "suite=unittest.defaultTestLoader.discover(start_dir=sys.argv[2],pattern='test_model_sources.py');"
        "result=unittest.TextTestRunner(verbosity=2).run(suite);"
        "sys.exit(0 if result.wasSuccessful() else 1)"
    )
    process = subprocess.run(
        [sys.executable, '-s', '-c', runner, str(project_root), str(project_root / 'tests')],
        cwd=str(project_root), env=child_env(), capture_output=True, text=True, timeout=180,
    )
    combined = (process.stdout or '') + '\n' + (process.stderr or '')
    passed = process.returncode == 0 and 'Ran 10 tests' in combined and '\nOK' in combined
    result = {'passed': passed, 'label': label, 'tests': 10 if 'Ran 10 tests' in combined else None, 'returncode': process.returncode, 'stdout': process.stdout, 'stderr': process.stderr, 'candidate_path_inserted_explicitly': True}
    if not passed:
        raise ApplyError(f'{label} model-source tests failed: ' + combined[-4000:])
    return result


def node_executable() -> str:
    node = shutil.which('node') or shutil.which('node.exe')
    if not node:
        raise ApplyError('Node.js is required for the embedded JavaScript safety check.')
    return node


def embedded_javascript_check(web_path: Path, output_dir: Path, label: str) -> dict[str, Any]:
    source = web_path.read_text(encoding='utf-8')
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', source, flags=re.I | re.S)
    if not scripts:
        raise ApplyError('No embedded JavaScript block was found.')
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    node = node_executable()
    for index, script in enumerate(scripts, 1):
        path = output_dir / f'{label}_embedded_{index:03d}.js'
        path.write_text(script, encoding='utf-8')
        process = subprocess.run([node, '--check', str(path)], capture_output=True, text=True, timeout=120)
        item = {'path': str(path), 'returncode': process.returncode, 'stdout': process.stdout, 'stderr': process.stderr}
        results.append(item)
    passed = all(item['returncode'] == 0 for item in results)
    if not passed:
        raise ApplyError(f'{label} embedded JavaScript failed node --check.')
    return {'passed': True, 'blocks': len(results), 'results': results}


def integration_contract(base: Path) -> dict[str, Any]:
    web = (base / 'core/foxai_web.py').read_text(encoding='utf-8')
    config = json.loads((base / 'Config/model_sources.json').read_text(encoding='utf-8'))
    markers = {
        'ModelSourceRegistry': 'ModelSourceRegistry' in web,
        'approve_api': '/api/model-sources/approve-folder' in web,
        'forget_folder_api': '/api/model-sources/forget-folder' in web,
        'forget_model_api': '/api/model-sources/forget-model' in web,
        'forget_machine_api': '/api/model-sources/forget-machine' in web,
        'no_silent_runtime_receipt': "'silent_fallback_used':False" in web,
        'backend_source_label': "'model_source_label':model_record['source_label']" in web,
        'unavailable_message': 'The approved host model is unavailable. FOXAI did not switch to a USB model.' in web,
        'schema': config.get('schema') == 'foxai.model-sources.v1',
        'machine_preconfigured': 'DESKTOP-G9ERN9B' in (config.get('machines') or {}),
        'host_root': ((config.get('machines') or {}).get('DESKTOP-G9ERN9B') or {}).get('approved_host_roots', [{}])[0].get('path') == r'C:\KayockModels',
        'preferred_model': ((config.get('machines') or {}).get('DESKTOP-G9ERN9B') or {}).get('preferred_models', {}).get('general') == str(PRIORITY_MODEL),
        'whole_drive_scan_prohibited': config.get('policy', {}).get('no_whole_drive_scan') is True,
        'model_modification_prohibited': config.get('policy', {}).get('never_modify_model_files') is True,
        'no_silent_switch': config.get('policy', {}).get('no_silent_model_switch') is True,
        'online_disabled': config.get('reserved_source_types', {}).get('ONLINE_PROVIDER', {}).get('enabled') is False,
        'lan_disabled': config.get('reserved_source_types', {}).get('LAN_OPENAI_COMPATIBLE', {}).get('enabled') is False,
    }
    if not all(markers.values()):
        raise ApplyError('Model-source integration contract failed.')
    return {'passed': True, 'markers': markers}


def run_boundary_watch() -> dict[str, Any]:
    runner = (
        "import sys,unittest;"
        "sys.dont_write_bytecode=True;"
        "sys.path.insert(0,sys.argv[1]);"
        "suite=unittest.defaultTestLoader.discover(start_dir=sys.argv[2],pattern='test_boundary_watch.py');"
        "result=unittest.TextTestRunner(verbosity=2).run(suite);"
        "sys.exit(0 if result.wasSuccessful() else 1)"
    )
    process = subprocess.run(
        [sys.executable, '-s', '-c', runner, str(ROOT), str(ROOT / 'tests')],
        cwd=str(ROOT), env=child_env(), capture_output=True, text=True, timeout=180,
    )
    combined = (process.stdout or '') + '\n' + (process.stderr or '')
    passed = process.returncode == 0 and 'Ran 5 tests' in combined and '\nOK' in combined
    result = {'passed': passed, 'tests': 5 if 'Ran 5 tests' in combined else None, 'returncode': process.returncode, 'stdout': process.stdout, 'stderr': process.stderr}
    if not passed:
        raise ApplyError('Boundary Watch failed: ' + combined[-4000:])
    return result


def model_metadata_snapshot(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding='utf-8'))
    roots: list[Path] = []
    for item in config.get('usb_roots') or []:
        if isinstance(item, dict) and item.get('enabled', True) and item.get('path'):
            path = (ROOT / str(item['path'])).resolve()
            try:
                path.relative_to(ROOT.resolve())
            except ValueError:
                continue
            roots.append(path)
    for profile in (config.get('machines') or {}).values():
        if not isinstance(profile, dict):
            continue
        for item in profile.get('approved_host_roots') or []:
            if isinstance(item, dict) and item.get('enabled', True) and item.get('path'):
                roots.append(Path(str(item['path'])))
    records = []
    seen = set()
    for root in roots:
        if not root.is_dir():
            continue
        count = 0
        try:
            iterator = root.rglob('*')
            for path in iterator:
                if count >= 1000:
                    break
                if not path.is_file() or path.suffix.lower() != '.gguf':
                    continue
                name = path.name.casefold()
                if 'mmproj' in name or 'projector' in name:
                    continue
                count += 1
                key = os.path.normcase(os.path.abspath(str(path)))
                if key in seen:
                    continue
                seen.add(key)
                stat = path.stat()
                records.append({'path': str(path), 'size_bytes': stat.st_size, 'modified_ns': stat.st_mtime_ns})
        except OSError:
            continue
    records.sort(key=lambda item: os.path.normcase(item['path']))
    return {'count': len(records), 'models': records}


def runtime_registry_check() -> dict[str, Any]:
    runner = r"""import json,os,platform,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,sys.argv[1])
from core.model_sources import ModelSourceRegistry
root=Path(sys.argv[1])
machine=str(os.environ.get('COMPUTERNAME') or platform.node() or 'UNKNOWN').strip().upper()
registry=ModelSourceRegistry(root,config_path=root/'Config'/'model_sources.json',machine_name=machine)
state=registry.state(include_catalog=True)
result={'machine':machine,'state':state,'priority':None}
if machine=='DESKTOP-G9ERN9B':
    priority=Path(r'C:\KayockModels\General\Qwen3-30B-A3B\Qwen3-30B-A3B-Q4_K_M.gguf')
    record=registry.record_for_path(priority)
    result['priority']={'exists':priority.is_file(),'readable':os.access(priority,os.R_OK),'record':record}
print(json.dumps(result))
"""
    process = subprocess.run(
        [sys.executable, '-s', '-c', runner, str(ROOT)], cwd=str(ROOT), env=child_env(), capture_output=True, text=True, timeout=180,
    )
    if process.returncode != 0:
        raise ApplyError('Live model-source registry check failed: ' + (process.stdout or '') + (process.stderr or ''))
    try:
        data = json.loads(process.stdout.strip().splitlines()[-1])
    except Exception as exc:
        raise ApplyError('Live registry check returned invalid JSON.') from exc
    state = data.get('state') or {}
    checks = {
        'schema': state.get('schema') == 'foxai.model-sources.v1',
        'policy_no_whole_drive': state.get('policy', {}).get('no_whole_drive_scan') is True,
        'policy_never_modify_models': state.get('policy', {}).get('never_modify_model_files') is True,
        'policy_no_silent_switch': state.get('policy', {}).get('no_silent_model_switch') is True,
        'online_disabled': state.get('allow_online_sources') is False,
        'model_files_modified_false': state.get('model_files_modified') is False,
    }
    if data.get('machine') == PRIORITY_MACHINE:
        priority = data.get('priority') or {}
        record = priority.get('record') or {}
        checks.update({
            'priority_exists': priority.get('exists') is True,
            'priority_readable': priority.get('readable') is True,
            'priority_registered': bool(record),
            'priority_source': record.get('source') == 'HOST_PC',
            'priority_source_label': record.get('source_label') == 'HOST PC',
            'priority_exact_path': os.path.normcase(os.path.abspath(str(record.get('path') or ''))) == os.path.normcase(os.path.abspath(str(PRIORITY_MODEL))),
        })
    if not all(checks.values()):
        raise ApplyError('Live model-source registry contract failed.')
    return {'passed': True, 'checks': checks, 'details': data}


def atomic_install(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=target.name + '.phm2c2.', suffix='.tmp', dir=str(target.parent))
    try:
        with os.fdopen(fd, 'wb') as handle:
            data = source.read_bytes()
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        temp = Path(temp_name)
        if sha256(temp) != sha256(source):
            raise ApplyError(f'Staged file hash mismatch: {target}')
        os.replace(temp, target)
    except Exception:
        try:
            Path(temp_name).unlink(missing_ok=True)
        except OSError:
            pass
        raise


def create_backup(stamp: str) -> Path:
    backup = ROOT / 'Backups/SecurityMilestone' / f'PHM2C2_{stamp}'
    backup.mkdir(parents=True, exist_ok=False)
    for relative in TARGET_MODIFIED:
        source = ROOT / relative
        target = backup / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    shutil.copy2(PACKAGE / 'APPLY_PLAN.json', backup / 'APPLY_PLAN.json')
    shutil.copy2(PACKAGE / 'grounding/PHM2C2_SUCCESS_RECEIPT.json', backup / 'PHM2C2_SUCCESS_RECEIPT.json')
    return backup


def rollback(backup: Path | None) -> dict[str, Any]:
    actions = []
    errors = []
    if backup is None:
        return {'attempted': False, 'actions': [], 'errors': []}
    for relative in TARGET_ADDED:
        path = ROOT / relative
        if not path.exists():
            continue
        expected = PLAN['candidate_hashes'][relative]
        actual = sha256(path) if path.is_file() else None
        if actual != expected:
            errors.append(f'Preserved unexpected changed file during rollback: {relative}')
            continue
        try:
            path.unlink()
            actions.append(f'Removed transaction-added file {relative}')
        except Exception as exc:
            errors.append(f'Could not remove {relative}: {exc}')
    for relative in TARGET_MODIFIED:
        source = backup / relative
        target = ROOT / relative
        try:
            atomic_install(source, target)
            actions.append(f'Restored {relative}')
        except Exception as exc:
            errors.append(f'Could not restore {relative}: {exc}')
    verified = not errors
    if verified:
        for relative in TARGET_MODIFIED:
            if sha256(ROOT / relative) != PLAN['baselines'][relative]:
                verified = False
                errors.append(f'Restored baseline hash failed: {relative}')
        for relative in TARGET_ADDED:
            if (ROOT / relative).exists():
                verified = False
                errors.append(f'Added file remains after rollback: {relative}')
    return {'attempted': True, 'verified': verified, 'actions': actions, 'errors': errors}


def write_outputs(receipt: dict[str, Any], report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / 'APPLY_RECEIPT.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    failure = receipt.get('failure')
    lines = [
        '# FOXAI Portable Host Model Library Phase 2C2 — Apply Report', '',
        f"- Created: `{receipt['created']}`",
        f"- State: **{receipt['state']}**",
        f"- Verified: **{receipt['verified']}**",
        f"- Approval verified: **{receipt['approval_verified']}**",
        f"- Transaction started: **{receipt['transaction_started']}**",
        f"- Backup: `{receipt.get('backup_path')}`",
        '- Automatic model launch: **False**',
        '- Network access: **False**',
        '- Model files modified: **False**',
        '- Deleted live files: **None**', '',
        '## Exact applied scope', '',
        '- Modified `core/foxai_web.py`.',
        '- Added `core/model_sources.py`.',
        '- Added `Config/model_sources.json`.',
        '- Added `tests/test_model_sources.py`.',
        '- Deleted nothing.', '',
        '## Verification', '',
        f"- Candidate model-source tests: **{bool(receipt.get('checks', {}).get('candidate_model_source_tests', {}).get('passed'))}**",
        f"- Live model-source tests: **{bool(receipt.get('checks', {}).get('live_model_source_tests', {}).get('passed'))}**",
        f"- Boundary Watch: **{bool(receipt.get('checks', {}).get('live_boundary_watch', {}).get('passed'))}**",
        f"- Embedded JavaScript: **{bool(receipt.get('checks', {}).get('live_javascript', {}).get('passed'))}**",
        f"- Runtime source registry: **{bool(receipt.get('checks', {}).get('runtime_registry', {}).get('passed'))}**",
        f"- Model metadata unchanged: **{bool(receipt.get('checks', {}).get('model_metadata_unchanged', {}).get('passed'))}**",
        f"- Non-target baselines unchanged: **{bool(receipt.get('checks', {}).get('locked_files_after', {}).get('passed'))}**",
    ]
    if failure:
        lines += ['', '## Failure', '', f"- `{failure.get('type')}: {failure.get('message')}`"]
    rollback_info = receipt.get('rollback') or {}
    if rollback_info.get('attempted'):
        lines += ['', '## Rollback', '', f"- Verified: **{rollback_info.get('verified')}**"]
        lines += [f'- {item}' for item in rollback_info.get('actions', [])]
        lines += [f'- ERROR: {item}' for item in rollback_info.get('errors', [])]
    (report_dir / 'APPLY_REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--approval', default=None)
    args = parser.parse_args()
    created = datetime.now(timezone.utc)
    stamp = created.strftime('%Y%m%dT%H%M%SZ')
    report_dir = ROOT / 'Reports/HostModelApply' / f'PHM2C2_APPLY_{stamp}'
    receipt: dict[str, Any] = {
        'action': 'foxai_portable_host_model_library_phase2c2_apply',
        'created': created.isoformat(),
        'state': 'stopped_fail_closed',
        'verified': False,
        'root': str(ROOT),
        'approval_phrase_expected': APPROVAL_PHRASE,
        'approval_verified': False,
        'transaction_started': False,
        'backup_path': None,
        'report_path': str(report_dir),
        'automatic_model_launch': False,
        'network_access': False,
        'pip_install': False,
        'model_files_modified': False,
        'delete_operations': [],
        'checks': {},
        'rollback': {'attempted': False, 'actions': [], 'errors': []},
        'failure': None,
    }
    backup: Path | None = None
    before_models: dict[str, Any] | None = None
    try:
        approval = args.approval
        if approval is None:
            print('=' * 72)
            print('FOXAI PORTABLE HOST MODEL LIBRARY PHASE 2C2 — GUARDED APPLY')
            print('=' * 72)
            print('Exact approved changes:')
            print('  MODIFY core\\foxai_web.py')
            print('  ADD    core\\model_sources.py')
            print('  ADD    Config\\model_sources.json')
            print('  ADD    tests\\test_model_sources.py')
            print('  DELETE nothing')
            print('This does not start a model, use the network, or modify model files.')
            approval = input(f'Type the exact approval phrase: {APPROVAL_PHRASE}\n> ')
        receipt['approval_verified'] = approval == APPROVAL_PHRASE
        if not receipt['approval_verified']:
            raise ApplyError('Approval phrase did not match exactly.')

        receipt['checks']['bundled_python'] = bundled_python_check()
        receipt['checks']['package_manifest'] = package_manifest_check()
        receipt['checks']['grounding'] = verify_grounding()
        receipt['checks']['live_baselines_before'] = verify_live_baselines(before_apply=True)
        if port_open(PORT_REQUIRED_CLOSED):
            raise ApplyError('FOXAI WebUI is still running on port 8765. Close it before applying.')
        receipt['checks']['port_8765_closed'] = {'passed': True, 'port': 8765}
        receipt['checks']['candidate_hashes'] = candidate_hash_check()
        receipt['checks']['candidate_compile'] = python_compile_check(CANDIDATE)
        receipt['checks']['candidate_contract'] = integration_contract(CANDIDATE)
        receipt['checks']['candidate_model_source_tests'] = run_model_source_tests(CANDIDATE, 'Candidate')
        receipt['checks']['candidate_javascript'] = embedded_javascript_check(
            CANDIDATE / 'core/foxai_web.py', report_dir / 'candidate_javascript', 'candidate'
        )
        receipt['checks']['boundary_watch_before'] = run_boundary_watch()
        before_models = model_metadata_snapshot(CANDIDATE / 'Config/model_sources.json')
        receipt['checks']['model_metadata_before'] = before_models

        backup = create_backup(stamp)
        receipt['backup_path'] = str(backup)
        receipt['transaction_started'] = True
        (backup / 'TRANSACTION_JOURNAL.json').write_text(json.dumps({
            'state': 'prepared', 'created': created.isoformat(), 'targets': TARGETS,
            'approval_verified': True,
        }, indent=2), encoding='utf-8')

        # Install dependencies and registry first; WebUI last.
        for relative in TARGET_ADDED:
            atomic_install(CANDIDATE / relative, ROOT / relative)
        for relative in TARGET_MODIFIED:
            atomic_install(CANDIDATE / relative, ROOT / relative)

        receipt['checks']['live_target_hashes'] = {
            'passed': all(sha256(ROOT / rel) == PLAN['candidate_hashes'][rel] for rel in TARGETS),
            'files': [
                {'path': rel, 'expected': PLAN['candidate_hashes'][rel], 'actual': sha256(ROOT / rel)}
                for rel in TARGETS
            ],
        }
        if not receipt['checks']['live_target_hashes']['passed']:
            raise ApplyError('Live target hash verification failed.')

        receipt['checks']['live_compile'] = python_compile_check(ROOT)
        receipt['checks']['live_contract'] = integration_contract(ROOT)
        receipt['checks']['live_model_source_tests'] = run_model_source_tests(ROOT, 'Live')
        receipt['checks']['live_javascript'] = embedded_javascript_check(
            ROOT / 'core/foxai_web.py', report_dir / 'live_javascript', 'live'
        )
        receipt['checks']['live_boundary_watch'] = run_boundary_watch()
        receipt['checks']['runtime_registry'] = runtime_registry_check()
        after_models = model_metadata_snapshot(ROOT / 'Config/model_sources.json')
        models_unchanged = before_models == after_models
        receipt['checks']['model_metadata_after'] = after_models
        receipt['checks']['model_metadata_unchanged'] = {'passed': models_unchanged}
        if not models_unchanged:
            raise ApplyError('Model metadata changed during the guarded apply.')
        receipt['checks']['locked_files_after'] = verify_live_baselines(before_apply=False)

        receipt['state'] = 'applied_verified'
        receipt['verified'] = True
        (backup / 'TRANSACTION_JOURNAL.json').write_text(json.dumps({
            'state': 'applied_verified', 'created': created.isoformat(), 'targets': TARGETS,
            'approval_verified': True,
        }, indent=2), encoding='utf-8')
    except Exception as exc:
        receipt['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
        if receipt['transaction_started']:
            receipt['rollback'] = rollback(backup)
            receipt['state'] = 'rolled_back_fail_closed' if receipt['rollback'].get('verified') else 'rollback_incomplete_fail_closed'
        else:
            receipt['state'] = 'stopped_fail_closed'
    finally:
        write_outputs(receipt, report_dir)
        print('=' * 72)
        print('FOXAI PORTABLE HOST MODEL LIBRARY PHASE 2C2 — GUARDED APPLY')
        print('=' * 72)
        print(f"State: {receipt['state']}")
        print(f"Verified: {receipt['verified']}")
        print(f"Approval verified: {receipt['approval_verified']}")
        print(f"Transaction started: {receipt['transaction_started']}")
        print(f"Backup: {receipt.get('backup_path')}")
        print(f"Report: {receipt['report_path']}")
        print('Automatic model launch: False')
        print('Network access: False')
        print('Model files modified: False')
        print('Deletes: None')
        if receipt['failure']:
            print(f"Failure: {receipt['failure']['message']}")
    return 0 if receipt['verified'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
