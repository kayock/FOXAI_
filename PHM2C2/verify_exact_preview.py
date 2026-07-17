from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
PLAN = json.loads((PACKAGE / 'EXACT_PREVIEW_PLAN.json').read_text(encoding='utf-8'))
CANDIDATE = PACKAGE / 'candidate'
REPORT_ROOT = ROOT / 'Reports' / 'HostModelPreview'


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime('PHM2C2_%Y%m%dT%H%M%SZ')
    report_dir = REPORT_ROOT / stamp
    report_dir.mkdir(parents=True, exist_ok=False)
    receipt = {
        'action': 'foxai_portable_host_model_library_phase2c2_exact_preview',
        'created': datetime.now(timezone.utc).isoformat(),
        'state': 'stopped_fail_closed',
        'verified': False,
        'root': str(ROOT),
        'apply_capability_present': False,
        'live_files_modified': False,
        'model_files_modified': False,
        'automatic_model_launch': False,
        'network_access': False,
        'delete_operations': [],
        'checks': {},
        'failure': None,
    }
    try:
        baseline_records = []
        for relative, expected in PLAN['baselines'].items():
            path = ROOT / relative
            actual = sha256(path) if path.is_file() else None
            item = {'path': relative, 'expected': expected, 'actual': actual, 'ok': actual == expected}
            baseline_records.append(item)
        if not all(item['ok'] for item in baseline_records):
            raise RuntimeError('One or more locked live baselines changed.')
        receipt['checks']['live_baselines'] = {'passed': True, 'files': baseline_records}

        absent = []
        for relative in PLAN['expected_absent']:
            exists = (ROOT / relative).exists()
            absent.append({'path': relative, 'absent': not exists})
        if not all(item['absent'] for item in absent):
            raise RuntimeError('One or more proposed new files already exist. Preview stopped.')
        receipt['checks']['new_file_absence'] = {'passed': True, 'files': absent}

        candidate_records = []
        for relative, expected in PLAN['candidate_hashes'].items():
            path = CANDIDATE / relative
            actual = sha256(path) if path.is_file() else None
            item = {'path': relative, 'expected': expected, 'actual': actual, 'ok': actual == expected}
            candidate_records.append(item)
        if not all(item['ok'] for item in candidate_records):
            raise RuntimeError('Candidate file hash verification failed.')
        receipt['checks']['candidate_hashes'] = {'passed': True, 'files': candidate_records}

        for relative in ('core/foxai_web.py', 'core/model_sources.py', 'tests/test_model_sources.py'):
            source = (CANDIDATE / relative).read_text(encoding='utf-8')
            compile(source, str(CANDIDATE / relative), 'exec')
        receipt['checks']['python_compile'] = {'passed': True}

        config = json.loads((CANDIDATE / 'Config/model_sources.json').read_text(encoding='utf-8'))
        machine = config['machines']['DESKTOP-G9ERN9B']
        checks = {
            'schema': config.get('schema') == 'foxai.model-sources.v1',
            'machine_preconfigured': machine.get('machine_name') == 'DESKTOP-G9ERN9B',
            'host_root': machine['approved_host_roots'][0]['path'] == r'C:\KayockModels',
            'preferred_model': machine['preferred_models']['general'].endswith('Qwen3-30B-A3B-Q4_K_M.gguf'),
            'no_whole_drive_scan': bool(config['policy']['no_whole_drive_scan']),
            'never_modify_models': bool(config['policy']['never_modify_model_files']),
            'no_silent_switch': bool(config['policy']['no_silent_model_switch']),
            'online_disabled': not bool(config['policy']['online_sources_enabled']),
        }
        if not all(checks.values()):
            raise RuntimeError('Candidate model-source configuration contract failed.')
        receipt['checks']['registry_contract'] = {'passed': True, 'checks': checks}

        env = os.environ.copy()
        env['PYTHONPATH'] = str(CANDIDATE)
        env['PYTHONNOUSERSITE'] = '1'
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        tests = subprocess.run(
            [sys.executable, '-s', '-m', 'unittest', 'discover', '-s', str(CANDIDATE / 'tests'), '-p', 'test_model_sources.py', '-v'],
            cwd=str(CANDIDATE), env=env, capture_output=True, text=True, timeout=180,
        )
        if tests.returncode != 0 or 'Ran 10 tests' not in (tests.stdout + tests.stderr):
            raise RuntimeError('Candidate model-source tests failed: ' + (tests.stdout + tests.stderr)[-4000:])
        receipt['checks']['model_source_tests'] = {'passed': True, 'tests': 10, 'stdout': tests.stdout, 'stderr': tests.stderr}

        node = shutil.which('node') or shutil.which('node.exe')
        if not node:
            raise RuntimeError('Node.js was not found; embedded JavaScript cannot be verified.')
        web_source = (CANDIDATE / 'core/foxai_web.py').read_text(encoding='utf-8')
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', web_source, flags=re.IGNORECASE | re.DOTALL)
        if not scripts:
            raise RuntimeError('No embedded JavaScript blocks were found.')
        js_dir = report_dir / 'candidate_javascript'
        js_dir.mkdir()
        js_results = []
        for index, script in enumerate(scripts, start=1):
            path = js_dir / f'embedded_script_{index:03d}.js'
            path.write_text(script, encoding='utf-8')
            run = subprocess.run([node, '--check', str(path)], capture_output=True, text=True, timeout=120)
            result = {'path': str(path), 'returncode': run.returncode, 'stdout': run.stdout, 'stderr': run.stderr}
            js_results.append(result)
            if run.returncode != 0:
                raise RuntimeError('Embedded JavaScript failed node --check: ' + run.stderr[-3000:])
        receipt['checks']['embedded_javascript'] = {'passed': True, 'blocks': len(scripts), 'results': js_results}

        required_markers = [
            'ModelSourceRegistry',
            '/api/model-sources/approve-folder',
            '/api/model-sources/forget-folder',
            '/api/model-sources/forget-model',
            '/api/model-sources/forget-machine',
            "'silent_fallback_used':False",
            "'model_source_label':model_record['source_label']",
            'The approved host model is unavailable. FOXAI did not switch to a USB model.',
        ]
        marker_checks = {marker: marker in web_source for marker in required_markers}
        if not all(marker_checks.values()):
            raise RuntimeError('Candidate integration markers are incomplete.')
        receipt['checks']['integration_contract'] = {'passed': True, 'markers': marker_checks}

        receipt['state'] = 'exact_preview_verified'
        receipt['verified'] = True
    except Exception as exc:
        receipt['failure'] = {'type': type(exc).__name__, 'message': str(exc)}

    receipt_path = report_dir / 'receipt.json'
    report_path = report_dir / 'report.md'
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    lines = [
        '# Portable Host Model Library Phase 2C2 — Exact Preview Report',
        '',
        f"- State: **{receipt['state']}**",
        f"- Verified: **{receipt['verified']}**",
        '- Apply capability: **False**',
        '- Live files modified: **False**',
        '- Model files modified: **False**',
        '- Automatic model launch: **False**',
        '- Network access: **False**',
        '- Deleted files: **None**',
        '',
        '## Exact proposed changes',
        '',
        '- Modify `core/foxai_web.py`.',
        '- Add `core/model_sources.py`.',
        '- Add `Config/model_sources.json`.',
        '- Add `tests/test_model_sources.py`.',
        '- Delete nothing.',
        '',
        '## Machine profile',
        '',
        '- `DESKTOP-G9ERN9B` is preconfigured through the removable registry file.',
        '- Approved root: `C:\\KayockModels`.',
        '- Other machines may approve different folders for one session or remember them locally.',
        '- Forget controls remove registry references only.',
        '- Whole-drive scanning and silent fallback remain prohibited.',
        '- LAN and online providers remain disabled.',
    ]
    if receipt['failure']:
        lines += ['', '## Failure', '', f"- `{receipt['failure']['type']}: {receipt['failure']['message']}`"]
    report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    print('=' * 72)
    print('FOXAI PORTABLE HOST MODEL LIBRARY PHASE 2C2')
    print('=' * 72)
    print(f"State: {receipt['state']}")
    print(f"Verified: {receipt['verified']}")
    print('Apply capability present: False')
    print('Live files modified: False')
    print('Model files modified: False')
    print(f'Report: {report_dir}')
    if receipt['failure']:
        print(f"Failure: {receipt['failure']['message']}")
    return 0 if receipt['verified'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
