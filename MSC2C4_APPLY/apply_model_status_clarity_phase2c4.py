from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import argparse
import ast
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
import zipfile
from typing import Any

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
PLAN = json.loads((PACKAGE / 'APPLY_PLAN.json').read_text(encoding='utf-8'))
CANDIDATE = PACKAGE / 'candidate/core/foxai_web.py'
APPROVAL_PHRASE = PLAN['approval_phrase']
PORT_REQUIRED_CLOSED = 8765


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


def model_metadata(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {'path': None, 'exists': False}
    result = {'path': str(path), 'exists': path.is_file()}
    if path.is_file():
        stat = path.stat()
        result.update({
            'size_bytes': stat.st_size,
            'modified_ns': stat.st_mtime_ns,
            'readable': os.access(path, os.R_OK),
        })
    return result


def same_model_metadata(before: dict[str, Any], after: dict[str, Any]) -> bool:
    return all(before.get(k) == after.get(k) for k in ('path', 'exists', 'size_bytes', 'modified_ns'))


def priority_model_path() -> Path | None:
    config = ROOT / 'Config/model_sources.json'
    if not config.is_file():
        return None
    try:
        data = json.loads(config.read_text(encoding='utf-8'))
        machine = str(os.environ.get('COMPUTERNAME') or platform.node() or '').strip().upper()
        profile = data.get('machines', {}).get(machine, {})
        preferred = profile.get('preferred_models', {})
        value = preferred.get('general')
        return Path(value) if value else None
    except Exception:
        return None


def usb_sample_path() -> Path | None:
    root = ROOT / 'Models/Chat'
    if not root.is_dir():
        return None
    for path in sorted(root.rglob('*.gguf')):
        if path.is_file():
            return path
    return None


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.35)
        return sock.connect_ex(('127.0.0.1', port)) == 0


def package_manifest_check() -> dict[str, Any]:
    manifest = PACKAGE / 'PACKAGE_SHA256SUMS.txt'
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


def bundled_python_check(root: Path = ROOT) -> dict[str, Any]:
    expected = (root / 'env/python/python.exe').resolve()
    actual = Path(sys.executable).resolve()
    passed = expected == actual
    result = {'passed': passed, 'expected': str(expected), 'actual': str(actual), 'version': sys.version}
    if not passed:
        raise ApplyError('Guarded apply is not running under FOXAI bundled Python.')
    return result


def grounding_check(require_live_receipt: bool = True) -> dict[str, Any]:
    files = {
        'success_receipt': PACKAGE / 'grounding/MSC2C4_SUCCESS_RECEIPT.json',
        'success_report': PACKAGE / 'grounding/MSC2C4_SUCCESS_REPORT.md',
        'preview_plan': PACKAGE / 'grounding/EXACT_PREVIEW_PLAN.json',
        'exact_diff': PACKAGE / 'grounding/EXACT_DIFF.txt',
        'preview_build': PACKAGE / 'grounding/EXACT_PREVIEW_BUILD_RECEIPT.json',
    }
    expected = PLAN['grounding']
    hashes = {
        'success_receipt_sha256': sha256(files['success_receipt']),
        'success_report_sha256': sha256(files['success_report']),
        'preview_plan_sha256': sha256(files['preview_plan']),
        'exact_diff_sha256': sha256(files['exact_diff']),
        'preview_build_receipt_sha256': sha256(files['preview_build']),
    }
    for key, actual in hashes.items():
        if actual != expected[key]:
            raise ApplyError(f'Grounding hash changed: {key}')
    receipt = json.loads(files['success_receipt'].read_text(encoding='utf-8'))
    contract = {
        'state': receipt.get('state') == 'exact_preview_verified',
        'verified': receipt.get('verified') is True,
        'apply_absent': receipt.get('apply_capability_present') is False,
        'live_unmodified': receipt.get('live_files_modified') is False,
        'models_unmodified': receipt.get('model_files_modified') is False,
        'registry_unmodified': receipt.get('registry_modified') is False,
        'status_tests': receipt.get('checks', {}).get('status_clarity_tests', {}).get('tests') == 10,
        'model_source_tests': receipt.get('checks', {}).get('model_source_tests', {}).get('tests') == 10,
        'boundary_watch': receipt.get('checks', {}).get('boundary_watch', {}).get('tests') == 5,
        'javascript': receipt.get('checks', {}).get('javascript', {}).get('passed') is True,
        'candidate_hash': receipt.get('checks', {}).get('exact_transformation', {}).get('candidate_sha256') == PLAN['candidate_foxai_web_sha256'],
    }
    if not all(contract.values()):
        raise ApplyError('Approved exact-preview receipt contract failed.')
    live_matches = []
    if require_live_receipt:
        preview_root = ROOT / 'Reports/ModelStatusClarityPreview'
        if preview_root.is_dir():
            for path in preview_root.glob('MSC2C4_*/receipt.json'):
                try:
                    if sha256(path) == expected['required_live_preview_receipt_sha256']:
                        live_matches.append(str(path))
                except OSError:
                    pass
        if not live_matches:
            raise ApplyError('The exact approved Phase 2C4 preview receipt was not found in Reports\\ModelStatusClarityPreview.')
    return {'passed': True, 'hashes': hashes, 'receipt_contract': contract, 'live_receipt_matches': live_matches}


def verify_baselines(root: Path, *, after_apply: bool) -> dict[str, Any]:
    checks = []
    for relative, expected in PLAN['baselines'].items():
        if after_apply and relative == 'core/foxai_web.py':
            continue
        path = root / relative
        actual = sha256(path) if path.is_file() else None
        checks.append({'path': relative, 'expected': expected, 'actual': actual, 'ok': actual == expected})
    if not all(item['ok'] for item in checks):
        stage = 'after' if after_apply else 'before'
        raise ApplyError(f'A protected live baseline changed {stage} the transaction.')
    return {'passed': True, 'files': checks}


def exact_transformation_check(live_path: Path, candidate_path: Path) -> dict[str, Any]:
    transformed = live_path.read_text(encoding='utf-8')
    results = []
    for item in PLAN['exact_replacements']:
        count = transformed.count(item['old'])
        results.append({'id': item['id'], 'occurrences': count, 'expected': 1})
        if count != 1:
            raise ApplyError(f"Exact replacement {item['id']} matched {count} times.")
        transformed = transformed.replace(item['old'], item['new'], 1)
    candidate_text = candidate_path.read_text(encoding='utf-8')
    if transformed != candidate_text:
        raise ApplyError('Candidate is not the exact approved transformation of live core/foxai_web.py.')
    return {'passed': True, 'replacements': results, 'candidate_sha256': sha256(candidate_path)}


def child_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env['PYTHONNOUSERSITE'] = '1'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    if extra:
        env.update(extra)
    return env


def run_unittest(root: Path, tests_dir: Path, pattern: str, expected_count: int, *, extra_env: dict[str, str] | None = None, label: str) -> dict[str, Any]:
    runner = (
        "import sys,unittest;"
        "sys.dont_write_bytecode=True;"
        "sys.path.insert(0,sys.argv[1]);"
        "suite=unittest.defaultTestLoader.discover(start_dir=sys.argv[2],pattern=sys.argv[3]);"
        "result=unittest.TextTestRunner(verbosity=2).run(suite);"
        "sys.exit(0 if result.wasSuccessful() else 1)"
    )
    process = subprocess.run(
        [sys.executable, '-s', '-c', runner, str(root), str(tests_dir), pattern],
        cwd=str(root), env=child_env(extra_env), capture_output=True, text=True, timeout=240,
    )
    combined = (process.stdout or '') + '\n' + (process.stderr or '')
    passed = process.returncode == 0 and f'Ran {expected_count} tests' in combined and '\nOK' in combined
    result = {
        'passed': passed,
        'label': label,
        'tests': expected_count if f'Ran {expected_count} tests' in combined else None,
        'returncode': process.returncode,
        'stdout': process.stdout,
        'stderr': process.stderr,
        'bytecode_writes_disabled': True,
    }
    if not passed:
        raise ApplyError(f'{label} failed: ' + combined[-5000:])
    return result


def node_executable() -> str:
    node = shutil.which('node') or shutil.which('node.exe')
    if not node:
        raise ApplyError('Node.js is required for embedded JavaScript verification.')
    return node


def javascript_check(web_path: Path, output_dir: Path, label: str) -> dict[str, Any]:
    source = web_path.read_text(encoding='utf-8')
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', source, flags=re.I | re.S)
    if not scripts:
        raise ApplyError('No embedded JavaScript block was found.')
    output_dir.mkdir(parents=True, exist_ok=True)
    node = node_executable()
    results = []
    for index, script in enumerate(scripts, 1):
        path = output_dir / f'{label}_embedded_{index:03d}.js'
        path.write_text(script, encoding='utf-8')
        process = subprocess.run([node, '--check', str(path)], capture_output=True, text=True, timeout=120)
        results.append({'path': str(path), 'returncode': process.returncode, 'stdout': process.stdout, 'stderr': process.stderr})
    if not all(item['returncode'] == 0 for item in results):
        raise ApplyError(f'{label} embedded JavaScript verification failed.')
    return {'passed': True, 'blocks': len(results), 'results': results}


def compile_check(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding='utf-8')
    ast.parse(text, filename=str(path))
    compile(text, str(path), 'exec')
    return {'passed': True, 'path': str(path)}


def atomic_replace(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + '.msc2c4.tmp')
    shutil.copy2(source, temp)
    if sha256(temp) != sha256(source):
        temp.unlink(missing_ok=True)
        raise ApplyError('Temporary replacement hash mismatch.')
    os.replace(temp, target)


def write_report(receipt: dict[str, Any], path: Path) -> None:
    lines = [
        '# FOXAI Model Status Clarity Phase 2C4 — Apply Report',
        '',
        f"- Created: `{receipt['created']}`",
        f"- State: **{receipt['state']}**",
        f"- Verified: **{receipt['verified']}**",
        f"- Approval verified: **{receipt['approval_verified']}**",
        f"- Backup: `{receipt['backup_path']}`",
        '- Automatic launch: **False**',
        '- Model server action: **None**',
        '- Network access: **False**',
        '- Model files modified: **False**',
        '- Registry modified: **False**',
        '- Deleted live files: **None**',
        '',
        '## Applied scope',
        '',
        '- Modified `core/foxai_web.py`.',
        '- Added no live files.',
        '- Deleted no live files.',
        '',
        '## Display',
        '',
        '```text',
        'Engine: RUNNING or STOPPED',
        'Model source: USB, HOST PC, LAN, or ONLINE PROVIDER',
        'Network use: NONE, LAN, or INTERNET',
        '```',
        '',
        '## Verification',
        '',
        f"- Status clarity: **{receipt.get('checks', {}).get('live_status_tests', {}).get('tests', 0)}/10**",
        f"- Model-source tests: **{receipt.get('checks', {}).get('live_model_source_tests', {}).get('tests', 0)}/10**",
        f"- Boundary Watch: **{receipt.get('checks', {}).get('live_boundary_watch', {}).get('tests', 0)}/5**",
        f"- Embedded JavaScript: **{receipt.get('checks', {}).get('live_javascript', {}).get('blocks', 0)} passed**",
        f"- Non-target baselines unchanged: **{receipt.get('checks', {}).get('locked_files_after', {}).get('passed', False)}**",
        f"- Model metadata unchanged: **{receipt.get('checks', {}).get('model_metadata_after', {}).get('passed', False)}**",
        '',
        '## Rollback',
        '',
        f"- Attempted: **{receipt.get('rollback', {}).get('attempted', False)}**",
    ]
    if receipt.get('failure'):
        lines += ['', '## Failure', '', f"- `{receipt['failure']['type']}: {receipt['failure']['message']}`"]
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def perform_self_test() -> int:
    with tempfile.TemporaryDirectory(prefix='msc2c4_self_test_') as td:
        root = Path(td) / 'FOXAI'
        fixture = PACKAGE / 'self_test_fixture'
        shutil.copytree(fixture, root)
        target = root / 'core/foxai_web.py'
        backup = root / 'backup/foxai_web.py'
        backup.parent.mkdir(parents=True)
        shutil.copy2(target, backup)
        checks = {}
        if sha256(target) != PLAN['current_foxai_web_sha256']:
            raise ApplyError('Self-test current source hash mismatch.')
        checks['exact_transformation'] = exact_transformation_check(target, CANDIDATE)
        checks['candidate_compile'] = compile_check(CANDIDATE)
        checks['candidate_status'] = run_unittest(
            root, PACKAGE / 'tests', 'test_model_status_clarity.py', 10,
            extra_env={'FOXAI_WEB_UNDER_TEST': str(CANDIDATE)}, label='Self-test candidate status clarity',
        )
        checks['model_sources_before'] = run_unittest(root, root / 'tests', 'test_model_sources.py', 10, label='Self-test model-source tests')
        checks['boundary_before'] = run_unittest(root, root / 'tests', 'test_boundary_watch.py', 5, label='Self-test Boundary Watch')
        checks['candidate_javascript'] = javascript_check(CANDIDATE, root / 'js_candidate', 'candidate')
        atomic_replace(CANDIDATE, target)
        if sha256(target) != PLAN['candidate_foxai_web_sha256']:
            raise ApplyError('Self-test applied hash mismatch.')
        checks['live_compile'] = compile_check(target)
        checks['live_status'] = run_unittest(
            root, PACKAGE / 'tests', 'test_model_status_clarity.py', 10,
            extra_env={'FOXAI_WEB_UNDER_TEST': str(target)}, label='Self-test live status clarity',
        )
        checks['model_sources_after'] = run_unittest(root, root / 'tests', 'test_model_sources.py', 10, label='Self-test live model-source tests')
        checks['boundary_after'] = run_unittest(root, root / 'tests', 'test_boundary_watch.py', 5, label='Self-test live Boundary Watch')
        checks['live_javascript'] = javascript_check(target, root / 'js_live', 'live')
        if sha256(backup) != PLAN['current_foxai_web_sha256']:
            raise ApplyError('Self-test backup hash mismatch.')
        print(json.dumps({
            'state': 'full_simulated_apply_verified',
            'verified': True,
            'checks': checks,
            'applied_hash': sha256(target),
            'backup_hash': sha256(backup),
        }, indent=2))
        return 0


def perform_apply() -> int:
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup_root = ROOT / 'Backups/SecurityMilestone' / f'MSC2C4_{timestamp}'
    report_dir = ROOT / 'Reports/ModelStatusClarityApply' / f'MSC2C4_APPLY_{timestamp}'
    report_dir.mkdir(parents=True, exist_ok=False)
    receipt_path = report_dir / 'APPLY_RECEIPT.json'
    report_path = report_dir / 'APPLY_REPORT.md'
    target = ROOT / 'core/foxai_web.py'
    backup_file = backup_root / 'core/foxai_web.py'
    transaction_started = False

    receipt: dict[str, Any] = {
        'action': 'foxai_model_status_clarity_phase2c4_apply',
        'created': datetime.now(timezone.utc).isoformat(),
        'state': 'stopped_fail_closed',
        'verified': False,
        'root': str(ROOT),
        'approval_phrase_expected': APPROVAL_PHRASE,
        'approval_verified': False,
        'backup_path': str(backup_root),
        'report_path': str(report_dir),
        'automatic_model_launch': False,
        'model_server_started': False,
        'model_server_stopped': False,
        'network_access': False,
        'pip_install': False,
        'model_files_modified': False,
        'registry_modified': False,
        'delete_operations': [],
        'checks': {},
        'rollback': {'attempted': False, 'actions': []},
        'failure': None,
    }

    priority = priority_model_path()
    usb_sample = usb_sample_path()
    priority_before = model_metadata(priority)
    usb_before = model_metadata(usb_sample)

    try:
        print('Approval required. Type exactly:')
        print(APPROVAL_PHRASE)
        entered = input('> ').strip()
        if entered != APPROVAL_PHRASE:
            raise ApplyError('Approval phrase did not match. No live change occurred.')
        receipt['approval_verified'] = True

        receipt['checks']['bundled_python'] = bundled_python_check()
        receipt['checks']['package_manifest'] = package_manifest_check()
        receipt['checks']['grounding'] = grounding_check(require_live_receipt=True)
        receipt['checks']['live_baselines_before'] = verify_baselines(ROOT, after_apply=False)

        if port_open(PORT_REQUIRED_CLOSED):
            raise ApplyError('FOXAI WebUI is still running on port 8765. Close the black server window before applying.')
        receipt['checks']['port_8765_closed'] = {'passed': True, 'port': PORT_REQUIRED_CLOSED}

        actual_candidate = sha256(CANDIDATE)
        if actual_candidate != PLAN['candidate_foxai_web_sha256']:
            raise ApplyError('Candidate WebUI hash mismatch.')
        receipt['checks']['candidate_hash'] = {'passed': True, 'actual': actual_candidate}
        receipt['checks']['exact_transformation'] = exact_transformation_check(target, CANDIDATE)
        receipt['checks']['candidate_compile'] = compile_check(CANDIDATE)
        receipt['checks']['candidate_status_tests'] = run_unittest(
            ROOT, PACKAGE / 'tests', 'test_model_status_clarity.py', 10,
            extra_env={'FOXAI_WEB_UNDER_TEST': str(CANDIDATE)}, label='Candidate status clarity tests',
        )
        receipt['checks']['candidate_model_source_tests'] = run_unittest(
            ROOT, ROOT / 'tests', 'test_model_sources.py', 10, label='Candidate-stage model-source tests',
        )
        receipt['checks']['candidate_boundary_watch'] = run_unittest(
            ROOT, ROOT / 'tests', 'test_boundary_watch.py', 5, label='Candidate-stage Boundary Watch',
        )
        receipt['checks']['candidate_javascript'] = javascript_check(
            CANDIDATE, report_dir / 'javascript_candidate', 'candidate'
        )

        backup_file.parent.mkdir(parents=True, exist_ok=False)
        shutil.copy2(target, backup_file)
        if sha256(backup_file) != PLAN['current_foxai_web_sha256']:
            raise ApplyError('Backup hash verification failed.')
        receipt['checks']['backup'] = {'passed': True, 'path': str(backup_file), 'sha256': sha256(backup_file)}

        transaction_started = True
        atomic_replace(CANDIDATE, target)

        if sha256(target) != PLAN['candidate_foxai_web_sha256']:
            raise ApplyError('Applied WebUI hash verification failed.')
        receipt['checks']['applied_hash'] = {'passed': True, 'sha256': sha256(target)}
        receipt['checks']['live_compile'] = compile_check(target)
        receipt['checks']['live_status_tests'] = run_unittest(
            ROOT, PACKAGE / 'tests', 'test_model_status_clarity.py', 10,
            extra_env={'FOXAI_WEB_UNDER_TEST': str(target)}, label='Live status clarity tests',
        )
        receipt['checks']['live_model_source_tests'] = run_unittest(
            ROOT, ROOT / 'tests', 'test_model_sources.py', 10, label='Live model-source tests',
        )
        receipt['checks']['live_boundary_watch'] = run_unittest(
            ROOT, ROOT / 'tests', 'test_boundary_watch.py', 5, label='Live Boundary Watch',
        )
        receipt['checks']['live_javascript'] = javascript_check(
            target, report_dir / 'javascript_live', 'live'
        )
        receipt['checks']['locked_files_after'] = verify_baselines(ROOT, after_apply=True)

        priority_after = model_metadata(priority)
        usb_after = model_metadata(usb_sample)
        metadata_passed = same_model_metadata(priority_before, priority_after) and same_model_metadata(usb_before, usb_after)
        receipt['checks']['model_metadata_after'] = {
            'passed': metadata_passed,
            'priority_before': priority_before,
            'priority_after': priority_after,
            'usb_sample_before': usb_before,
            'usb_sample_after': usb_after,
            'full_large_model_hashing': False,
        }
        if not metadata_passed:
            raise ApplyError('Model metadata changed during apply verification.')

        receipt['state'] = 'applied_verified'
        receipt['verified'] = True
    except Exception as exc:
        receipt['failure'] = {'type': type(exc).__name__, 'message': str(exc)}
        if transaction_started:
            receipt['rollback']['attempted'] = True
            try:
                failed_copy = backup_root / 'failed_applied_core_foxai_web.py'
                if target.is_file():
                    shutil.copy2(target, failed_copy)
                    receipt['rollback']['actions'].append({'action': 'preserve_failed_applied_file', 'path': str(failed_copy), 'sha256': sha256(failed_copy)})
                atomic_replace(backup_file, target)
                restored = sha256(target)
                if restored != PLAN['current_foxai_web_sha256']:
                    raise ApplyError('Rollback restored hash did not match the original baseline.')
                receipt['rollback']['actions'].append({'action': 'restore_original_core_foxai_web.py', 'path': str(target), 'sha256': restored})
                receipt['state'] = 'rolled_back_fail_closed'
            except Exception as rollback_exc:
                receipt['rollback']['actions'].append({'action': 'rollback_failure', 'error': f'{type(rollback_exc).__name__}: {rollback_exc}'})
                receipt['state'] = 'rollback_failed_attention_required'
        else:
            receipt['state'] = 'stopped_fail_closed'
    finally:
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        write_report(receipt, report_path)
        print('=' * 72)
        print('FOXAI MODEL STATUS CLARITY PHASE 2C4 — GUARDED APPLY')
        print('=' * 72)
        print(f"State: {receipt['state']}")
        print(f"Verified: {receipt['verified']}")
        print(f"Backup: {backup_root}")
        print(f"Report: {report_dir}")
        print('Automatic launch: False')
        print('Model server action: None')
        print('Network access: False')
        print('Model changes: None')
        if receipt['failure']:
            print(f"Failure: {receipt['failure']['message']}")
    return 0 if receipt['verified'] else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        return perform_self_test()
    return perform_apply()


if __name__ == '__main__':
    raise SystemExit(main())
