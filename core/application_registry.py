from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NORMALIZED_STATES = {
    "ONLINE", "READY", "DEGRADED", "OFFLINE",
    "UNAVAILABLE", "PLANNED", "UNKNOWN",
}
HEALTHY_STATES = {"ONLINE", "READY"}
ATTENTION_STATES = {"DEGRADED", "OFFLINE", "UNAVAILABLE", "UNKNOWN"}


class ApplicationRegistryError(RuntimeError):
    """Raised when the read-only application registry cannot be loaded safely."""


class ApplicationRegistry:
    """
    Read-only KayocktheOS application inventory and passive health adapter.

    It never launches, stops, repairs, installs, deletes, or writes. It has no dependency on any Fox Sentry audit writer. Health is telemetry,
    not a security incident.
    """

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        config_path: str | Path | None = None,
        fleet_path: str | Path | None = None,
        timeout: float = 0.6,
        allow_network: bool = True,
    ) -> None:
        self.root = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]
        self.config_path = Path(config_path) if config_path is not None else self.root / "Config" / "application_registry.json"
        self.fleet_path = Path(fleet_path) if fleet_path is not None else self.root / "Config" / "fleet_registry.json"
        self.timeout = max(0.1, min(float(timeout), 2.0))
        self.allow_network = bool(allow_network)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            raw = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ApplicationRegistryError(f"Registry file is missing: {path}") from exc
        except OSError as exc:
            raise ApplicationRegistryError(f"Registry file could not be read: {path}: {exc}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ApplicationRegistryError(f"Registry JSON is invalid: {path}: line {exc.lineno}") from exc
        if not isinstance(data, dict):
            raise ApplicationRegistryError(f"Registry root must be a JSON object: {path}")
        return data

    @staticmethod
    def _slug(value: Any) -> str:
        text = str(value or "").strip().lower()
        output: list[str] = []
        underscore = False
        for character in text:
            if character.isalnum():
                output.append(character)
                underscore = False
            elif not underscore:
                output.append("_")
                underscore = True
        return "".join(output).strip("_") or "unnamed"

    def _resolve_path(self, value: Any) -> Path | None:
        text = str(value or "").strip()
        if not text:
            return None
        path = Path(text)
        return path if path.is_absolute() else self.root / path

    @staticmethod
    def _canonical(record: dict[str, Any], index: int) -> dict[str, Any]:
        entry_id = str(record.get("id") or "").strip()
        name = str(record.get("name") or "").strip()
        if not entry_id or not name:
            raise ApplicationRegistryError(f"Application entry {index} requires id and name.")
        lifecycle = str(record.get("lifecycle") or "active").strip().lower()
        if lifecycle not in {"active", "development", "planned", "retired"}:
            raise ApplicationRegistryError(f"Unsupported lifecycle for {entry_id}: {lifecycle}")
        return {
            **record,
            "id": entry_id,
            "name": name,
            "kind": str(record.get("kind") or "application").strip(),
            "department": str(record.get("department") or "Unassigned").strip(),
            "lifecycle": lifecycle,
            "health_mode": str(record.get("health_mode") or "path").strip().lower(),
            "display_order": int(record.get("display_order") or index * 10),
            "security_role": str(record.get("security_role") or "ordinary_application").strip(),
            "source": "canonical",
        }

    def _load_canonical(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        data = self._read_json(self.config_path)
        raw_entries = data.get("applications")
        if not isinstance(raw_entries, list):
            raise ApplicationRegistryError(f"'applications' must be a list in {self.config_path}")
        entries = [self._canonical(item, index) for index, item in enumerate(raw_entries, 1) if isinstance(item, dict)]
        if len(entries) != len(raw_entries):
            raise ApplicationRegistryError("Every canonical application record must be an object.")
        ids = [entry["id"] for entry in entries]
        duplicates = sorted(value for value in set(ids) if ids.count(value) > 1)
        if duplicates:
            raise ApplicationRegistryError("Duplicate application ids: " + ", ".join(duplicates))
        return entries, data

    def _load_fleet(self, existing_ids: set[str], enabled: bool) -> list[dict[str, Any]]:
        if not enabled or not self.fleet_path.is_file():
            return []
        data = self._read_json(self.fleet_path)
        shuttles = data.get("shuttles")
        if not isinstance(shuttles, dict):
            return []
        merged: list[dict[str, Any]] = []
        for index, (key, raw) in enumerate(sorted(shuttles.items()), 1):
            if not isinstance(raw, dict):
                continue
            entry_id = f"fleet_{self._slug(key)}"
            if entry_id in existing_ids:
                continue
            reserved = bool(raw.get("reserved"))
            merged.append({
                "id": entry_id,
                "name": str(raw.get("name") or key),
                "kind": str(raw.get("kind") or "extension"),
                "department": str(raw.get("department") or "Extensions"),
                "category": str(raw.get("category") or "Extension"),
                "lifecycle": "planned" if reserved else "active",
                "health_mode": "fleet",
                "display_order": 1000 + index,
                "security_role": "ordinary_extension",
                "source": "fleet",
                "installed": bool(raw.get("installed")),
                "reserved": reserved,
                "service_state": raw.get("service_state"),
                "health_status": raw.get("health_status"),
                "health_message": raw.get("health_message"),
                "path": raw.get("path"),
                "callsign": raw.get("callsign"),
                "capabilities": raw.get("capabilities") or [],
            })
        return merged

    def load_entries(self) -> list[dict[str, Any]]:
        canonical, data = self._load_canonical()
        fleet_settings = data.get("fleet_merge") if isinstance(data.get("fleet_merge"), dict) else {}
        entries = canonical + self._load_fleet({item["id"] for item in canonical}, bool(fleet_settings.get("enabled", True)))
        return sorted(entries, key=lambda item: (int(item.get("display_order") or 9999), item["name"].lower()))

    @staticmethod
    def _result(entry: dict[str, Any], status: str, message: str, *, latency_ms: float | None = None) -> dict[str, Any]:
        state = status if status in NORMALIZED_STATES else "UNKNOWN"
        return {
            "id": entry["id"],
            "name": entry["name"],
            "kind": entry.get("kind", "application"),
            "department": entry.get("department", "Unassigned"),
            "category": entry.get("category"),
            "lifecycle": entry.get("lifecycle", "active"),
            "health_mode": entry.get("health_mode", "path"),
            "security_role": entry.get("security_role", "ordinary_application"),
            "source": entry.get("source", "canonical"),
            "status": state,
            "healthy": True if state in HEALTHY_STATES else False if state in ATTENTION_STATES else None,
            "message": str(message),
            "latency_ms": round(float(latency_ms), 1) if latency_ms is not None else None,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "path": entry.get("path"),
            "url": entry.get("url"),
            "host": entry.get("host"),
            "port": entry.get("port"),
            "callsign": entry.get("callsign"),
            "capabilities": entry.get("capabilities") or [],
        }

    def _required_path(self, entry: dict[str, Any]) -> dict[str, Any] | None:
        path = self._resolve_path(entry.get("path"))
        if path is not None and not path.exists():
            return self._result(entry, "UNAVAILABLE", f"Required path is missing: {path}")
        return None

    def _probe_path(self, entry: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve_path(entry.get("path"))
        if path is None:
            return self._result(entry, "UNKNOWN", "No passive path probe is configured.")
        if path.exists():
            kind = "folder" if path.is_dir() else "file"
            return self._result(entry, "READY", f"Required {kind} is present: {path}")
        return self._result(entry, "UNAVAILABLE", f"Required path is missing: {path}")

    def _probe_process_self(self, entry: dict[str, Any]) -> dict[str, Any]:
        failure = self._required_path(entry)
        return failure or self._result(entry, "ONLINE", "The FOXAI Desktop process is running this registry view.")

    def _probe_tcp(self, entry: dict[str, Any]) -> dict[str, Any]:
        failure = self._required_path(entry)
        if failure:
            return failure
        if not self.allow_network:
            return self._result(entry, "UNKNOWN", "Network probe disabled for validation.")
        host = str(entry.get("host") or "127.0.0.1")
        try:
            port = int(entry.get("port"))
        except (TypeError, ValueError):
            return self._result(entry, "UNKNOWN", "TCP health probe has no valid port.")
        started = time.perf_counter()
        try:
            with socket.create_connection((host, port), timeout=self.timeout):
                return self._result(entry, "ONLINE", f"TCP endpoint is accepting connections at {host}:{port}.", latency_ms=(time.perf_counter() - started) * 1000)
        except OSError as exc:
            return self._result(entry, "OFFLINE", f"TCP endpoint is not responding at {host}:{port}: {exc}", latency_ms=(time.perf_counter() - started) * 1000)

    def _probe_http(self, entry: dict[str, Any]) -> dict[str, Any]:
        failure = self._required_path(entry)
        if failure:
            return failure
        if not self.allow_network:
            return self._result(entry, "UNKNOWN", "Network probe disabled for validation.")
        url = str(entry.get("url") or "").strip()
        if not url:
            return self._result(entry, "UNKNOWN", "HTTP health probe has no URL.")
        started = time.perf_counter()
        request = urllib.request.Request(url, headers={"User-Agent": "KayocktheOS-ApplicationRegistry/1"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                code = int(getattr(response, "status", 200))
                return self._result(entry, "ONLINE" if code < 500 else "DEGRADED", f"HTTP endpoint responded with status {code}: {url}", latency_ms=(time.perf_counter() - started) * 1000)
        except urllib.error.HTTPError as exc:
            return self._result(entry, "ONLINE" if exc.code < 500 else "DEGRADED", f"HTTP endpoint responded with status {exc.code}: {url}", latency_ms=(time.perf_counter() - started) * 1000)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return self._result(entry, "OFFLINE", f"HTTP endpoint is not responding: {url}: {exc}", latency_ms=(time.perf_counter() - started) * 1000)

    def _probe_fleet(self, entry: dict[str, Any]) -> dict[str, Any]:
        if entry.get("lifecycle") == "planned" or entry.get("reserved"):
            return self._result(entry, "PLANNED", "Reserved extension is visible but not commissioned.")
        if not bool(entry.get("installed")):
            return self._result(entry, "UNAVAILABLE", "Extension registry reports that this component is not installed.")
        path = self._resolve_path(entry.get("path"))
        if path is not None and not path.exists():
            return self._result(entry, "DEGRADED", f"Extension is registered as installed but its path is missing: {path}")
        health = str(entry.get("health_status") or "").strip().lower()
        service = str(entry.get("service_state") or "").strip().lower()
        message = str(entry.get("health_message") or entry.get("service_state") or "Extension is registered as installed.")
        if health in {"ready", "healthy", "online", "operational"} or service in {"operational", "ready", "enabled", "online"}:
            return self._result(entry, "READY", message)
        if health in {"degraded", "warning", "attention"}:
            return self._result(entry, "DEGRADED", message)
        if health in {"offline", "stopped", "unavailable", "error", "failed"}:
            return self._result(entry, "OFFLINE", message)
        return self._result(entry, "UNKNOWN", message)

    def assess(self, entry: dict[str, Any]) -> dict[str, Any]:
        lifecycle = str(entry.get("lifecycle") or "active").lower()
        if lifecycle in {"planned", "retired"}:
            return self._result(entry, "PLANNED", f"{lifecycle.title()} application is visible and is not a failure.")
        mode = str(entry.get("health_mode") or "path").lower()
        try:
            if mode in {"path", "component"}:
                return self._probe_path(entry)
            if mode == "process_self":
                return self._probe_process_self(entry)
            if mode == "tcp":
                return self._probe_tcp(entry)
            if mode == "http":
                return self._probe_http(entry)
            if mode == "fleet":
                return self._probe_fleet(entry)
            if mode == "static":
                return self._result(entry, "READY", str(entry.get("health_message") or "Registered and ready."))
            return self._result(entry, "UNKNOWN", f"Unsupported passive health mode: {mode}")
        except Exception as exc:
            return self._result(entry, "UNKNOWN", f"Passive health check failed safely: {type(exc).__name__}: {exc}")

    def snapshot(self) -> dict[str, Any]:
        entries = self.load_entries()
        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max(1, min(8, len(entries))), thread_name_prefix="kayock-health") as executor:
            futures = {executor.submit(self.assess, entry): entry for entry in entries}
            for future in as_completed(futures):
                entry = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    results.append(self._result(entry, "UNKNOWN", f"Passive worker failed safely: {type(exc).__name__}: {exc}"))
        order = {entry["id"]: int(entry.get("display_order") or 9999) for entry in entries}
        results.sort(key=lambda item: (order.get(item["id"], 9999), item["name"].lower()))
        counts = {state: 0 for state in NORMALIZED_STATES}
        for result in results:
            counts[result["status"]] = counts.get(result["status"], 0) + 1
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "telemetry_only": True,
            "incident_written": False,
            "config_path": str(self.config_path),
            "fleet_path": str(self.fleet_path),
            "summary": {
                "total": len(results),
                "canonical": sum(1 for item in results if item["source"] == "canonical"),
                "fleet": sum(1 for item in results if item["source"] == "fleet"),
                "online": counts.get("ONLINE", 0),
                "ready": counts.get("READY", 0),
                "attention": sum(counts.get(state, 0) for state in ATTENTION_STATES),
                "planned": counts.get("PLANNED", 0),
                "status_counts": {state: counts.get(state, 0) for state in sorted(NORMALIZED_STATES)},
            },
            "applications": results,
        }


def get_application_health_snapshot(
    root: str | Path | None = None,
    *,
    timeout: float = 0.6,
    allow_network: bool = True,
) -> dict[str, Any]:
    """Convenience wrapper for the Desktop telemetry panel."""
    return ApplicationRegistry(root=root, timeout=timeout, allow_network=allow_network).snapshot()
