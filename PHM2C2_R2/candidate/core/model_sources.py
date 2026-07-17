from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import platform
import subprocess
import tempfile
import time
from typing import Any


MODEL_SUFFIXES = {'.gguf'}
MAX_MODELS_PER_ROOT = 1000
CATALOG_CACHE_SECONDS = 10.0


class ModelSourceError(ValueError):
    pass


def current_machine_name() -> str:
    values = (
        os.environ.get('COMPUTERNAME'),
        platform.node(),
    )
    for value in values:
        if value and str(value).strip():
            return str(value).strip().upper()
    return 'UNKNOWN'


def local_machine_key(machine_name: str) -> str:
    normalized = str(machine_name or 'UNKNOWN').strip().upper()
    return 'sha256:' + hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:24]


def _path_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def choose_host_model_folder() -> dict[str, Any]:
    """Open the Windows folder picker without scanning or registering a path."""
    if os.name != 'nt':
        return {
            'ok': False,
            'message': 'The native folder picker is available on Windows only.',
            'selected_path': None,
            'registered': False,
        }
    script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$dialog=New-Object System.Windows.Forms.FolderBrowserDialog;"
        "$dialog.Description='Choose a folder containing approved GGUF models';"
        "$dialog.ShowNewFolderButton=$false;"
        "if($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK){"
        "[Console]::Out.Write($dialog.SelectedPath)}"
    )
    try:
        process = subprocess.run(
            ['powershell.exe', '-NoProfile', '-STA', '-Command', script],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except Exception as exc:
        return {
            'ok': False,
            'message': f'Folder picker could not be opened: {type(exc).__name__}: {exc}',
            'selected_path': None,
            'registered': False,
        }
    selected = (process.stdout or '').strip()
    if process.returncode != 0:
        return {
            'ok': False,
            'message': (process.stderr or 'Folder picker failed.').strip(),
            'selected_path': None,
            'registered': False,
        }
    if not selected:
        return {
            'ok': True,
            'message': 'Folder selection was cancelled. No registry change occurred.',
            'selected_path': None,
            'registered': False,
        }
    return {
        'ok': True,
        'message': 'Folder selected but not approved yet.',
        'selected_path': selected,
        'registered': False,
    }


class ModelSourceRegistry:
    """Backend-owned local model-source registry.

    It inventories approved locations only. It never modifies model files and
    never selects, starts, stops, or silently substitutes a model.
    """

    def __init__(
        self,
        root: Path,
        *,
        config_path: Path | None = None,
        machine_name: str | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.config_path = (
            Path(config_path)
            if config_path is not None
            else self.root / 'Config' / 'model_sources.json'
        )
        self.machine_name = (
            str(machine_name or current_machine_name()).strip().upper()
            or 'UNKNOWN'
        )
        self.machine_key = local_machine_key(self.machine_name)
        self._session_roots: dict[str, dict[str, Any]] = {}
        self._cache: list[dict[str, Any]] | None = None
        self._cache_time = 0.0

    def _empty_config(self) -> dict[str, Any]:
        return {
            'schema': 'foxai.model-sources.v1',
            'policy': {
                'no_whole_drive_scan': True,
                'never_modify_model_files': True,
                'no_silent_model_switch': True,
                'automatic_model_launch': False,
                'online_sources_enabled': False,
                'credentials_in_plain_config': False,
            },
            'usb_roots': [
                {'id': 'usb_chat', 'path': 'Models/Chat', 'enabled': True, 'recursive': True},
                {'id': 'usb_models', 'path': 'Models', 'enabled': True, 'recursive': True},
                {'id': 'usb_models_legacy', 'path': 'models', 'enabled': True, 'recursive': True},
                {'id': 'usb_engine', 'path': 'Engine', 'enabled': True, 'recursive': True},
            ],
            'machines': {},
            'reserved_source_types': {
                'LAN_OPENAI_COMPATIBLE': {'enabled': False},
                'ONLINE_PROVIDER': {'enabled': False},
            },
        }

    def _load(self) -> dict[str, Any]:
        if not self.config_path.is_file():
            return self._empty_config()
        try:
            data = json.loads(self.config_path.read_text(encoding='utf-8'))
        except Exception as exc:
            raise ModelSourceError(
                f'Model-source registry could not be read: {type(exc).__name__}: {exc}'
            ) from exc
        if not isinstance(data, dict) or data.get('schema') != 'foxai.model-sources.v1':
            raise ModelSourceError('Model-source registry schema is invalid.')
        policy = data.get('policy') or {}
        if not policy.get('no_whole_drive_scan'):
            raise ModelSourceError('Model-source registry must prohibit whole-drive scanning.')
        if not policy.get('never_modify_model_files'):
            raise ModelSourceError('Model-source registry must prohibit model-file modification.')
        return data

    def _save(self, data: dict[str, Any]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(data, indent=2) + '\n').encode('utf-8')
        fd, temp_name = tempfile.mkstemp(
            prefix=self.config_path.name + '.',
            suffix='.tmp',
            dir=str(self.config_path.parent),
        )
        try:
            with os.fdopen(fd, 'wb') as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.config_path)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise
        self.invalidate()

    def invalidate(self) -> None:
        self._cache = None
        self._cache_time = 0.0

    def _machine_profile(self, data: dict[str, Any]) -> dict[str, Any] | None:
        machines = data.get('machines') or {}
        profile = machines.get(self.machine_name)
        return profile if isinstance(profile, dict) else None

    def _ensure_machine_profile(self, data: dict[str, Any]) -> dict[str, Any]:
        machines = data.setdefault('machines', {})
        profile = machines.get(self.machine_name)
        if not isinstance(profile, dict):
            profile = {
                'display_name': self.machine_name,
                'machine_name': self.machine_name,
                'machine_key': self.machine_key,
                'approved_host_roots': [],
                'preferred_models': {},
                'fallback_policy': 'ASK_OR_APPROVED_USB',
                'prompt_for_host_models': True,
                'allow_online_sources': False,
            }
            machines[self.machine_name] = profile
        profile['machine_name'] = self.machine_name
        profile['machine_key'] = self.machine_key
        profile.setdefault('approved_host_roots', [])
        profile.setdefault('preferred_models', {})
        profile.setdefault('fallback_policy', 'ASK_OR_APPROVED_USB')
        profile.setdefault('prompt_for_host_models', True)
        profile['allow_online_sources'] = False
        return profile

    def _validate_host_folder(self, value: str | Path) -> Path:
        raw = str(value or '').strip().strip('"')
        if not raw:
            raise ModelSourceError('Choose a host model folder first.')
        path = Path(raw).expanduser()
        try:
            resolved = path.resolve(strict=True)
        except Exception as exc:
            raise ModelSourceError(f'Host model folder is unavailable: {raw}') from exc
        if not resolved.is_dir():
            raise ModelSourceError('The selected host model path is not a folder.')
        anchor = Path(resolved.anchor)
        try:
            anchor_resolved = anchor.resolve()
        except Exception:
            anchor_resolved = anchor
        if resolved == anchor_resolved:
            raise ModelSourceError('Whole-drive model scanning is prohibited. Choose a specific folder.')
        if _is_relative_to(resolved, self.root):
            raise ModelSourceError('USB model folders are already approved and do not need host registration.')
        return resolved

    def _scan_root(
        self,
        root: Path,
        *,
        source: str,
        source_id: str,
        remembered: bool,
        session_only: bool,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        if not root.is_dir():
            return records
        scanned = 0
        try:
            iterator = root.rglob('*')
            for path in iterator:
                if scanned >= MAX_MODELS_PER_ROOT:
                    break
                if not path.is_file() or path.suffix.lower() not in MODEL_SUFFIXES:
                    continue
                lowered = path.name.casefold()
                if 'mmproj' in lowered or 'projector' in lowered:
                    continue
                scanned += 1
                try:
                    resolved = path.resolve()
                    stat = resolved.stat()
                except OSError:
                    continue
                records.append({
                    'name': resolved.name,
                    'path': str(resolved),
                    'source': source,
                    'source_label': 'USB' if source == 'USB' else 'HOST PC',
                    'source_id': source_id,
                    'machine_name': self.machine_name if source == 'HOST_PC' else None,
                    'approved': True,
                    'remembered': bool(remembered),
                    'session_only': bool(session_only),
                    'available': True,
                    'readable': os.access(resolved, os.R_OK),
                    'size_bytes': stat.st_size,
                    'modified_utc': datetime.fromtimestamp(
                        stat.st_mtime,
                        tz=timezone.utc,
                    ).isoformat(),
                    'full_sha256': None,
                    'hash_policy': 'deferred_for_large_model',
                })
        except OSError:
            return records
        return records

    def _root_records(self) -> list[dict[str, Any]]:
        data = self._load()
        roots: list[dict[str, Any]] = []
        for spec in data.get('usb_roots') or []:
            if not isinstance(spec, dict) or not spec.get('enabled', True):
                continue
            relative = str(spec.get('path') or '').strip()
            if not relative:
                continue
            path = (self.root / relative).resolve()
            if not _is_relative_to(path, self.root):
                continue
            roots.append({
                'id': str(spec.get('id') or relative),
                'path': path,
                'source': 'USB',
                'remembered': True,
                'session_only': False,
            })
        profile = self._machine_profile(data)
        if profile:
            for spec in profile.get('approved_host_roots') or []:
                if not isinstance(spec, dict) or not spec.get('enabled', True):
                    continue
                path_text = str(spec.get('path') or '').strip()
                if not path_text:
                    continue
                roots.append({
                    'id': str(spec.get('id') or 'host_models'),
                    'path': Path(path_text),
                    'source': 'HOST_PC',
                    'remembered': True,
                    'session_only': False,
                })
        roots.extend(self._session_roots.values())
        return roots

    def catalog(self, *, force: bool = False) -> list[dict[str, Any]]:
        now = time.monotonic()
        if (
            not force
            and self._cache is not None
            and now - self._cache_time < CATALOG_CACHE_SECONDS
        ):
            return [dict(item) for item in self._cache]
        output: list[dict[str, Any]] = []
        seen: set[str] = set()
        for root in self._root_records():
            path = Path(root['path'])
            for item in self._scan_root(
                path,
                source=str(root['source']),
                source_id=str(root['id']),
                remembered=bool(root['remembered']),
                session_only=bool(root['session_only']),
            ):
                key = _path_key(Path(item['path']))
                if key in seen:
                    continue
                seen.add(key)
                output.append(item)
        source_order = {'USB': 0, 'HOST_PC': 1}
        output.sort(
            key=lambda item: (
                source_order.get(str(item.get('source')), 9),
                str(item.get('name') or '').casefold(),
                str(item.get('path') or '').casefold(),
            )
        )
        self._cache = [dict(item) for item in output]
        self._cache_time = now
        return [dict(item) for item in output]

    def record_for_path(self, value: str | Path) -> dict[str, Any] | None:
        key = _path_key(Path(value))
        return next(
            (
                item
                for item in self.catalog()
                if _path_key(Path(item['path'])) == key
            ),
            None,
        )

    def approve_folder(
        self,
        value: str | Path,
        *,
        remember: bool,
        confirm: bool,
    ) -> dict[str, Any]:
        if not confirm:
            raise ModelSourceError('Explicit folder approval was not confirmed.')
        path = self._validate_host_folder(value)
        key = _path_key(path)
        if remember:
            data = self._load()
            profile = self._ensure_machine_profile(data)
            roots = profile.setdefault('approved_host_roots', [])
            if not any(_path_key(Path(str(item.get('path') or ''))) == key for item in roots if isinstance(item, dict)):
                roots.append({
                    'id': 'host_' + hashlib.sha256(key.encode('utf-8')).hexdigest()[:12],
                    'path': str(path),
                    'enabled': True,
                    'remembered': True,
                })
            self._save(data)
            scope = 'remembered'
        else:
            self._session_roots[key] = {
                'id': 'session_' + hashlib.sha256(key.encode('utf-8')).hexdigest()[:12],
                'path': path,
                'source': 'HOST_PC',
                'remembered': False,
                'session_only': True,
            }
            self.invalidate()
            scope = 'session'
        models = [
            item for item in self.catalog(force=True)
            if item['source'] == 'HOST_PC'
            and _is_relative_to(Path(item['path']).resolve(), path)
        ]
        return {
            'ok': True,
            'message': (
                f'Approved host model folder for this {scope}: {path}. '
                f'Found {len(models)} GGUF model(s). No model file was changed.'
            ),
            'path': str(path),
            'scope': scope,
            'model_count': len(models),
            'models': models,
            'model_files_modified': False,
        }

    def forget_folder(self, value: str | Path, *, confirm: bool) -> dict[str, Any]:
        if not confirm:
            raise ModelSourceError('Forget-folder action was not confirmed.')
        raw = str(value or '').strip()
        if not raw:
            raise ModelSourceError('No folder was selected to forget.')
        key = _path_key(Path(raw))
        session_removed = self._session_roots.pop(key, None) is not None
        data = self._load()
        profile = self._machine_profile(data)
        remembered_removed = False
        preferences_removed: list[str] = []
        if profile:
            roots = profile.get('approved_host_roots') or []
            kept = []
            for item in roots:
                if isinstance(item, dict) and _path_key(Path(str(item.get('path') or ''))) == key:
                    remembered_removed = True
                    continue
                kept.append(item)
            profile['approved_host_roots'] = kept
            preferred = profile.get('preferred_models') or {}
            for role, model_path in list(preferred.items()):
                try:
                    if _is_relative_to(Path(model_path).resolve(), Path(raw).resolve()):
                        preferred.pop(role, None)
                        preferences_removed.append(str(role))
                except Exception:
                    continue
            profile['preferred_models'] = preferred
            if remembered_removed or preferences_removed:
                self._save(data)
        self.invalidate()
        removed = session_removed or remembered_removed
        return {
            'ok': removed,
            'message': (
                'FOXAI forgot the folder reference. No folder or model file was deleted.'
                if removed
                else 'That folder was not registered for this computer or session.'
            ),
            'path': raw,
            'session_reference_removed': session_removed,
            'remembered_reference_removed': remembered_removed,
            'preferred_roles_removed': preferences_removed,
            'model_files_modified': False,
        }

    def forget_model(self, value: str | Path, *, confirm: bool) -> dict[str, Any]:
        if not confirm:
            raise ModelSourceError('Forget-model action was not confirmed.')
        raw = str(value or '').strip()
        if not raw:
            raise ModelSourceError('No model was selected to forget.')
        key = _path_key(Path(raw))
        data = self._load()
        profile = self._machine_profile(data)
        roles_removed: list[str] = []
        if profile:
            preferred = profile.get('preferred_models') or {}
            for role, model_path in list(preferred.items()):
                if _path_key(Path(str(model_path))) == key:
                    preferred.pop(role, None)
                    roles_removed.append(str(role))
            profile['preferred_models'] = preferred
            if roles_removed:
                self._save(data)
        return {
            'ok': bool(roles_removed),
            'message': (
                'FOXAI forgot the preferred-model reference. The model file remains untouched.'
                if roles_removed
                else 'The selected model was not stored as a preferred model.'
            ),
            'path': raw,
            'preferred_roles_removed': roles_removed,
            'model_files_modified': False,
        }

    def forget_machine(self, *, confirm: bool) -> dict[str, Any]:
        if not confirm:
            raise ModelSourceError('Forget-computer action was not confirmed.')
        data = self._load()
        machines = data.setdefault('machines', {})
        removed = machines.pop(self.machine_name, None) is not None
        session_count = len(self._session_roots)
        self._session_roots.clear()
        if removed:
            self._save(data)
        else:
            self.invalidate()
        return {
            'ok': removed or bool(session_count),
            'message': (
                f'FOXAI forgot the model-source profile for {self.machine_name}. '
                'USB models remain available; no model file was changed.'
            ),
            'machine_name': self.machine_name,
            'remembered_profile_removed': removed,
            'session_roots_removed': session_count,
            'model_files_modified': False,
        }

    def state(self, *, include_catalog: bool = True) -> dict[str, Any]:
        data = self._load()
        profile = self._machine_profile(data)
        roots = []
        if profile:
            for item in profile.get('approved_host_roots') or []:
                if not isinstance(item, dict):
                    continue
                path = str(item.get('path') or '')
                roots.append({
                    'id': str(item.get('id') or 'host_models'),
                    'path': path,
                    'scope': 'remembered',
                    'remembered': True,
                    'available': Path(path).is_dir(),
                })
        for item in self._session_roots.values():
            path = str(item['path'])
            roots.append({
                'id': str(item['id']),
                'path': path,
                'scope': 'session',
                'remembered': False,
                'available': Path(path).is_dir(),
            })
        result = {
            'ok': True,
            'schema': data.get('schema'),
            'machine': {
                'name': self.machine_name,
                'key': self.machine_key,
                'configured': profile is not None,
                'display_name': (
                    str(profile.get('display_name') or self.machine_name)
                    if profile else self.machine_name
                ),
            },
            'approved_host_roots': roots,
            'preferred_models': dict((profile or {}).get('preferred_models') or {}),
            'fallback_policy': str((profile or {}).get('fallback_policy') or 'ASK_OR_APPROVED_USB'),
            'prompt_for_host_models': bool((profile or {}).get('prompt_for_host_models', True)),
            'allow_online_sources': False,
            'reserved_source_types': data.get('reserved_source_types') or {},
            'policy': data.get('policy') or {},
            'session_only_reference_count': len(self._session_roots),
            'model_files_modified': False,
        }
        if include_catalog:
            catalog = self.catalog()
            result['models'] = catalog
            result['counts'] = {
                'total': len(catalog),
                'usb': sum(item['source'] == 'USB' for item in catalog),
                'host_pc': sum(item['source'] == 'HOST_PC' for item in catalog),
            }
        return result
