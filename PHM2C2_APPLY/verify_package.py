from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
PLAN = json.loads((PACKAGE / 'APPLY_PLAN.json').read_text(encoding='utf-8'))
CANDIDATE = PACKAGE / 'candidate'
RECEIPT = PACKAGE / 'PACKAGE_VERIFY_RECEIPT.json'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def child_env():
    env = os.environ.copy()
    env['PYTHONNOUSERSITE'] = '1'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def main() -> int:
    result = {
        'action': 'foxai_portable_host_model_library_phase2c2_apply_package_verify',
        'created': datetime.now(timezone.utc).isoformat(),
        'state': 'stopped_fail_closed',
        'verified': False,
        'live_files_modified': False,
        'model_files_modified': False,
        'apply_capability_present': True,
        'checks': {},
        'failure': None,
    }
    try:
        expected_python = (ROOT / 'env/python/python.exe').resolve()
        actual_python = Path(sys.executable).resolve()
        if expected_python != actual_python:
            raise RuntimeError('Verifier is not using FOXAI bundled Python.')
        result['checks']['bundled_python'] = {'passed': True, 'executable': sys.executable, 'version': sys.version}

        manifest_checks = []
        for line in (PACKAGE / 'PACKAGE_SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            expected, relative = line.split('  ', 1)
            path = PACKAGE / relative
            actual = sha256(path) if path.is_file() else None
            manifest_checks.append({'path': relative, 'expected': expected, 'actual': actual, 'ok': actual == expected})
        if not manifest_checks or not all(item['ok'] for item in manifest_checks):
            raise RuntimeError('Package manifest failed.')
        result['checks']['package_manifest'] = {'passed': True, 'files': manifest_checks}

        receipt_path = PACKAGE / 'grounding/PHM2C2_SUCCESS_RECEIPT.json'
        receipt_hash = sha256(receipt_path)
        if receipt_hash != PLAN['grounding']['success_receipt_sha256']:
            raise RuntimeError('Approved preview receipt hash changed.')
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        if not (receipt.get('state') == 'exact_preview_verified' and receipt.get('verified') is True):
            raise RuntimeError('Approved preview receipt is not verified.')
        live_found = []
        preview_root = ROOT / 'Reports/HostModelPreview'
        if preview_root.is_dir():
            for path in preview_root.glob('PHM2C2_*/receipt.json'):
                if path.is_file() and sha256(path) == PLAN['grounding']['required_live_preview_receipt_hash']:
                    live_found.append(str(path))
        if not live_found:
            raise RuntimeError('Approved live preview receipt was not found.')
        result['checks']['grounding'] = {'passed': True, 'live_receipts': live_found}

        live_checks = []
        for relative, expected in PLAN['baselines'].items():
            path = ROOT / relative
            actual = sha256(path) if path.is_file() else None
            live_checks.append({'path': relative, 'expected': expected, 'actual': actual, 'ok': actual == expected})
        if not all(item['ok'] for item in live_checks):
            raise RuntimeError('A locked live baseline changed.')
        absent = [{'path': rel, 'absent': not (ROOT / rel).exists()} for rel in PLAN['expected_absent']]
        if not all(item['absent'] for item in absent):
            raise RuntimeError('One or more approved new files already exist.')
        result['checks']['live_baselines'] = {'passed': True, 'files': live_checks, 'expected_absent': absent}

        candidate_checks = []
        for relative, expected in PLAN['candidate_hashes'].items():
            path = CANDIDATE / relative
            actual = sha256(path) if path.is_file() else None
            candidate_checks.append({'path': relative, 'expected': expected, 'actual': actual, 'ok': actual == expected})
        if not all(item['ok'] for item in candidate_checks):
            raise RuntimeError('Candidate hashes failed.')
        result['checks']['candidate_hashes'] = {'passed': True, 'files': candidate_checks}

        for relative in ('core/foxai_web.py', 'core/model_sources.py', 'tests/test_model_sources.py'):
            path = CANDIDATE / relative
            compile(path.read_text(encoding='utf-8'), str(path), 'exec')
        json.loads((CANDIDATE / 'Config/model_sources.json').read_text(encoding='utf-8'))
        result['checks']['python_compile'] = {'passed': True}

        runner = (
            "import sys,unittest;sys.dont_write_bytecode=True;"
            "sys.path.insert(0,sys.argv[1]);"
            "suite=unittest.defaultTestLoader.discover(start_dir=sys.argv[2],pattern='test_model_sources.py');"
            "r=unittest.TextTestRunner(verbosity=2).run(suite);sys.exit(0 if r.wasSuccessful() else 1)"
        )
        process = subprocess.run([sys.executable, '-s', '-c', runner, str(CANDIDATE), str(CANDIDATE / 'tests')], cwd=str(CANDIDATE), env=child_env(), capture_output=True, text=True, timeout=180)
        combined = (process.stdout or '') + '\n' + (process.stderr or '')
        if not (process.returncode == 0 and 'Ran 10 tests' in combined and '\nOK' in combined):
            raise RuntimeError('Candidate model-source tests failed: ' + combined[-4000:])
        result['checks']['model_source_tests'] = {'passed': True, 'tests': 10, 'stdout': process.stdout, 'stderr': process.stderr}

        node = shutil.which('node') or shutil.which('node.exe')
        if not node:
            raise RuntimeError('Node.js was not found.')
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', (CANDIDATE / 'core/foxai_web.py').read_text(encoding='utf-8'), flags=re.I | re.S)
        if not scripts:
            raise RuntimeError('No embedded JavaScript block was found.')
        js_dir = PACKAGE / 'PACKAGE_VERIFY_JAVASCRIPT'
        js_dir.mkdir(exist_ok=True)
        js_results = []
        for index, script in enumerate(scripts, 1):
            path = js_dir / f'embedded_{index:03d}.js'
            path.write_text(script, encoding='utf-8')
            check = subprocess.run([node, '--check', str(path)], capture_output=True, text=True, timeout=120)
            js_results.append({'path': str(path), 'returncode': check.returncode, 'stdout': check.stdout, 'stderr': check.stderr})
        if not all(item['returncode'] == 0 for item in js_results):
            raise RuntimeError('Embedded JavaScript check failed.')
        result['checks']['embedded_javascript'] = {'passed': True, 'blocks': len(js_results), 'results': js_results}

        result['state'] = 'guarded_apply_package_verified'
        result['verified'] = True
    except Exception as exc:
        result['failure'] = {'type': type(exc).__name__, 'message': str(exc)}
    RECEIPT.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({
        'State': result['state'],
        'Verified': result['verified'],
        'Live files modified': False,
        'Model files modified': False,
        'Apply capability present': True,
        'Receipt': str(RECEIPT),
    }, indent=2))
    return 0 if result['verified'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
