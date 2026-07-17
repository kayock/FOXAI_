from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent
PLAN = json.loads((PACKAGE / 'APPLY_PLAN.json').read_text(encoding='utf-8'))
RECEIPT = PACKAGE / 'PACKAGE_VERIFY_RECEIPT.json'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def child_env(extra=None):
    env = os.environ.copy()
    env['PYTHONNOUSERSITE'] = '1'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    if extra:
        env.update(extra)
    return env


def run_tests(target: Path) -> dict:
    runner = (
        "import sys,unittest;sys.dont_write_bytecode=True;"
        "sys.path.insert(0,sys.argv[1]);"
        "suite=unittest.defaultTestLoader.discover(start_dir=sys.argv[2],pattern='test_model_status_clarity.py');"
        "r=unittest.TextTestRunner(verbosity=2).run(suite);sys.exit(0 if r.wasSuccessful() else 1)"
    )
    p = subprocess.run(
        [sys.executable, '-s', '-c', runner, str(ROOT), str(PACKAGE / 'tests')],
        cwd=str(ROOT), env=child_env({'FOXAI_WEB_UNDER_TEST': str(target)}), capture_output=True, text=True, timeout=180,
    )
    combined = (p.stdout or '') + '\n' + (p.stderr or '')
    if not (p.returncode == 0 and 'Ran 10 tests' in combined and '\nOK' in combined):
        raise RuntimeError('Candidate status clarity tests failed: ' + combined[-5000:])
    return {'passed': True, 'tests': 10, 'stdout': p.stdout, 'stderr': p.stderr}


def main() -> int:
    result = {
        'action': 'foxai_model_status_clarity_phase2c4_package_verify',
        'created': datetime.now(timezone.utc).isoformat(),
        'state': 'stopped_fail_closed',
        'verified': False,
        'apply_capability_present': True,
        'live_files_modified': False,
        'model_files_modified': False,
        'registry_modified': False,
        'automatic_model_launch': False,
        'network_access': False,
        'checks': {},
        'failure': None,
    }
    try:
        manifest_checks = []
        for line in (PACKAGE / 'PACKAGE_SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            expected, relative = line.split('  ', 1)
            path = PACKAGE / relative
            actual = sha256(path) if path.is_file() else None
            manifest_checks.append({'path': relative, 'expected': expected, 'actual': actual, 'ok': actual == expected})
        if not manifest_checks or not all(item['ok'] for item in manifest_checks):
            raise RuntimeError('Package manifest verification failed.')
        result['checks']['package_manifest'] = {'passed': True, 'files': manifest_checks}

        expected_python = (ROOT / 'env/python/python.exe').resolve()
        actual_python = Path(sys.executable).resolve()
        if actual_python != expected_python:
            raise RuntimeError('Verifier is not using FOXAI bundled Python.')
        if sys.version_info[:3] != (3, 14, 6):
            raise RuntimeError('Unexpected bundled Python version.')
        result['checks']['bundled_python'] = {'passed': True, 'expected': str(expected_python), 'actual': str(actual_python), 'version': sys.version}

        grounding_files = {
            'success_receipt_sha256': PACKAGE / 'grounding/MSC2C4_SUCCESS_RECEIPT.json',
            'success_report_sha256': PACKAGE / 'grounding/MSC2C4_SUCCESS_REPORT.md',
            'preview_plan_sha256': PACKAGE / 'grounding/EXACT_PREVIEW_PLAN.json',
            'exact_diff_sha256': PACKAGE / 'grounding/EXACT_DIFF.txt',
            'preview_build_receipt_sha256': PACKAGE / 'grounding/EXACT_PREVIEW_BUILD_RECEIPT.json',
        }
        grounding_checks = {}
        for key, path in grounding_files.items():
            actual = sha256(path)
            expected = PLAN['grounding'][key]
            grounding_checks[key] = {'expected': expected, 'actual': actual, 'ok': expected == actual}
        if not all(item['ok'] for item in grounding_checks.values()):
            raise RuntimeError('Grounding hash verification failed.')
        success = json.loads((PACKAGE / 'grounding/MSC2C4_SUCCESS_RECEIPT.json').read_text(encoding='utf-8'))
        if not (success.get('state') == 'exact_preview_verified' and success.get('verified') is True):
            raise RuntimeError('Grounded exact preview receipt is not verified.')
        live_matches = []
        preview_root = ROOT / 'Reports/ModelStatusClarityPreview'
        if preview_root.is_dir():
            for path in preview_root.glob('MSC2C4_*/receipt.json'):
                if path.is_file() and sha256(path) == PLAN['grounding']['required_live_preview_receipt_sha256']:
                    live_matches.append(str(path))
        if not live_matches:
            raise RuntimeError('Approved live exact preview receipt was not found.')
        result['checks']['grounding'] = {'passed': True, 'hashes': grounding_checks, 'live_receipts': live_matches}

        live_checks = []
        for relative, expected in PLAN['baselines'].items():
            path = ROOT / relative
            actual = sha256(path) if path.is_file() else None
            live_checks.append({'path': relative, 'expected': expected, 'actual': actual, 'ok': actual == expected})
        if not all(item['ok'] for item in live_checks):
            raise RuntimeError('A protected live baseline changed.')
        result['checks']['live_baselines'] = {'passed': True, 'files': live_checks}

        candidate = PACKAGE / 'candidate/core/foxai_web.py'
        if sha256(candidate) != PLAN['candidate_foxai_web_sha256']:
            raise RuntimeError('Candidate WebUI hash mismatch.')
        text = candidate.read_text(encoding='utf-8')
        ast.parse(text, filename=str(candidate))
        compile(text, str(candidate), 'exec')
        result['checks']['candidate_compile'] = {'passed': True, 'sha256': sha256(candidate)}
        result['checks']['status_clarity_tests'] = run_tests(candidate)

        node = shutil.which('node') or shutil.which('node.exe')
        if not node:
            raise RuntimeError('Node.js was not found.')
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', text, flags=re.I | re.S)
        if not scripts:
            raise RuntimeError('No embedded JavaScript block was found.')
        js_dir = PACKAGE / 'PACKAGE_VERIFY_JAVASCRIPT'
        js_dir.mkdir(exist_ok=True)
        js_results = []
        for i, script in enumerate(scripts, 1):
            pth = js_dir / f'embedded_{i:03d}.js'
            pth.write_text(script, encoding='utf-8')
            p = subprocess.run([node, '--check', str(pth)], capture_output=True, text=True, timeout=120)
            js_results.append({'path': str(pth), 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr})
        if not all(item['returncode'] == 0 for item in js_results):
            raise RuntimeError('Embedded JavaScript verification failed.')
        result['checks']['javascript'] = {'passed': True, 'blocks': len(js_results), 'results': js_results}

        result['state'] = 'guarded_apply_package_verified'
        result['verified'] = True
    except Exception as exc:
        result['failure'] = {'type': type(exc).__name__, 'message': str(exc)}
    RECEIPT.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({
        'State': result['state'],
        'Verified': result['verified'],
        'Apply capability present': True,
        'Live files modified': False,
        'Model files modified': False,
        'Receipt': str(RECEIPT),
    }, indent=2))
    return 0 if result['verified'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
