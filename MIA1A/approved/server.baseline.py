from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.request

from core.paths import ENGINE


RUNTIME_DIR = ENGINE.parent.parent / "Logs"
DEFAULT_STATE_FILE = RUNTIME_DIR / "shared_llama_runtime.json"
DEFAULT_LOCK_FILE = RUNTIME_DIR / "shared_llama_runtime.lock"


@dataclass
class RuntimeResult:
    ok: bool
    action: str
    message: str
    model_name: str | None = None
    pid: int | None = None
    owned: bool = False
    details: dict = field(default_factory=dict)

    def __bool__(self):
        return self.ok

    def to_dict(self):
        return asdict(self)


class LlamaServer:
    """
    Shared llama-server coordinator for FOXAI frontends.

    A healthy FOXAI-managed runtime is identified by a small state file plus
    the live health endpoint. Each frontend registers its own process as a
    client. A frontend may detach without terminating the server while
    another live client is still using it.
    """

    def __init__(
        self,
        interface_name="Desktop",
        *,
        state_file=None,
        new_console=False,
    ):
        self.interface_name = str(interface_name or "FOXAI")
        self.process = None
        self.model = None
        self.host = "127.0.0.1"
        self.port = "8080"
        self.state_file = Path(state_file) if state_file else DEFAULT_STATE_FILE
        self.lock_file = (
            self.state_file.with_suffix(".lock")
            if state_file
            else DEFAULT_LOCK_FILE
        )
        self.new_console = bool(new_console)
        self.last_result = RuntimeResult(
            False,
            "offline",
            "Shared neural runtime is offline.",
        )

    # -------------------------
    # Public runtime interface
    # -------------------------

    def ensure_running(
        self,
        model,
        host="127.0.0.1",
        port="8080",
        context="8192",
        threads="12",
        reasoning_mode="current",
        reasoning_budget=None,
        require_verified_settings=False,
    ):
        target = self._target(
            model,
            host,
            port,
            context,
            threads,
            reasoning_mode,
            reasoning_budget,
            require_verified_settings,
        )
        self.model = Path(model)
        self.host = target["host"]
        self.port = target["port"]

        try:
            with self._runtime_lock():
                state = self._prune_clients(self._read_state())
                healthy = self._health_ok(target["host"], target["port"])
                port_open = self._port_open(target["host"], target["port"])

                if healthy:
                    result = self._attach_to_healthy_runtime(state, target)
                    self.last_result = result
                    return result

                if state and self._same_endpoint(state, target):
                    state_pid = self._int_or_none(state.get("server_pid"))
                    state_active = (
                        (state_pid is not None and self._pid_exists(state_pid))
                        or port_open
                    )

                    if state_active:
                        if not self._same_model(state, target):
                            result = self._conflict_result(
                                target,
                                state,
                                "A different shared model or runtime profile "
                                "is already starting on this endpoint.",
                            )
                            self.last_result = result
                            return result

                        state = self._register_client(state)
                        state["status"] = "starting"
                        state["updated_at"] = self._now()
                        self._write_state(state)
                        result = RuntimeResult(
                            True,
                            "waiting",
                            "Compatible shared neural runtime is already "
                            "starting. No duplicate server was launched.",
                            target["model_name"],
                            state_pid,
                            False,
                            {
                                "host": target["host"],
                                "port": target["port"],
                                "requested_context": target["context"],
                                "requested_threads": target["threads"],
                                "active_context": state.get("context"),
                                "active_threads": state.get("threads"),
                                "requested_reasoning_mode": target["reasoning_mode"],
                                "requested_reasoning_budget": target["reasoning_budget"],
                                "active_reasoning_mode": self._state_reasoning_mode(state),
                                "active_reasoning_budget": self._state_reasoning_budget(state),
                            },
                        )
                        self.last_result = result
                        return result

                    self._clear_state()

                if port_open:
                    result = RuntimeResult(
                        False,
                        "conflict",
                        "Port "
                        f"{target['port']} is already occupied by an "
                        "unverified or still-starting process. FOXAI did "
                        "not launch a duplicate neural server.",
                        target["model_name"],
                        details={
                            "host": target["host"],
                            "port": target["port"],
                        },
                    )
                    self.last_result = result
                    return result

                if not ENGINE.exists():
                    raise FileNotFoundError(
                        f"Missing llama-server.exe at: {ENGINE}"
                    )

                process = self._launch_process(target)
                self.process = process

                state = {
                    "version": 1,
                    "status": "starting",
                    "engine_path": str(ENGINE.resolve()),
                    "server_pid": getattr(process, "pid", None),
                    "owner_interface": self.interface_name,
                    "owner_process_pid": os.getpid(),
                    "host": target["host"],
                    "port": target["port"],
                    "model_path": target["model_path"],
                    "model_name": target["model_name"],
                    "context": target["context"],
                    "threads": target["threads"],
                    "reasoning_mode": target["reasoning_mode"],
                    "reasoning_budget": target["reasoning_budget"],
                    "launched_at": self._now(),
                    "updated_at": self._now(),
                    "clients": {},
                }
                state = self._register_client(state)
                self._write_state(state)

                result = RuntimeResult(
                    True,
                    "launched",
                    f"Shared neural runtime launch requested for "
                    f"{target['model_name']}.",
                    target["model_name"],
                    getattr(process, "pid", None),
                    True,
                    {
                        "host": target["host"],
                        "port": target["port"],
                        "context": target["context"],
                        "threads": target["threads"],
                        "reasoning_mode": target["reasoning_mode"],
                        "reasoning_budget": target["reasoning_budget"],
                        "settings_verified": target["require_verified_settings"],
                    },
                )
                self.last_result = result
                return result

        except TimeoutError as exc:
            result = RuntimeResult(
                False,
                "busy",
                str(exc),
                target["model_name"],
            )
            self.last_result = result
            return result
        except Exception as exc:
            result = RuntimeResult(
                False,
                "failed",
                f"Shared neural runtime error: {exc}",
                target["model_name"],
            )
            self.last_result = result
            return result

    def start(
        self,
        model,
        host="127.0.0.1",
        port="8080",
        context="8192",
        threads="12",
        reasoning_mode="current",
        reasoning_budget=None,
        require_verified_settings=False,
    ):
        """Compatibility wrapper. Prefer ensure_running()."""
        return bool(
            self.ensure_running(
                model,
                host=host,
                port=port,
                context=context,
                threads=threads,
                reasoning_mode=reasoning_mode,
                reasoning_budget=reasoning_budget,
                require_verified_settings=require_verified_settings,
            )
        )

    def wait_until_ready(self, timeout=90, poll_interval=1.0):
        deadline = time.monotonic() + max(0, float(timeout))

        while time.monotonic() <= deadline:
            if self._health_ok(self.host, self.port):
                try:
                    with self._runtime_lock():
                        state = self._prune_clients(self._read_state())
                        if state:
                            state["status"] = "ready"
                            state["updated_at"] = self._now()
                            state = self._register_client(state)
                            self._write_state(state)
                except Exception:
                    pass

                result = RuntimeResult(
                    True,
                    "ready",
                    "Shared neural runtime is healthy and ready.",
                    self.model.name if self.model else None,
                    self._current_server_pid(),
                    self.owns_process(),
                    {
                        "host": self.host,
                        "port": self.port,
                    },
                )
                self.last_result = result
                return result

            if self.process is not None and self.process.poll() is not None:
                result = RuntimeResult(
                    False,
                    "failed",
                    "The neural server process exited before its health "
                    "endpoint became ready.",
                    self.model.name if self.model else None,
                    getattr(self.process, "pid", None),
                    True,
                )
                self.last_result = result
                return result

            time.sleep(max(0.05, float(poll_interval)))

        result = RuntimeResult(
            False,
            "timeout",
            f"Shared neural runtime did not become healthy within "
            f"{int(timeout)} seconds.",
            self.model.name if self.model else None,
            self._current_server_pid(),
            self.owns_process(),
            {
                "host": self.host,
                "port": self.port,
            },
        )
        self.last_result = result
        return result

    def stop(self):
        try:
            with self._runtime_lock():
                state = self._prune_clients(self._read_state())
                if state:
                    state = self._unregister_client(state)
                    remaining = list((state.get("clients") or {}).values())

                    if remaining:
                        state["updated_at"] = self._now()
                        self._write_state(state)
                        result = RuntimeResult(
                            True,
                            "detached",
                            "This interface detached from the shared neural "
                            "runtime. The server remains online for another "
                            "active FOXAI interface.",
                            state.get("model_name"),
                            self._int_or_none(state.get("server_pid")),
                            False,
                            {"remaining_clients": remaining},
                        )
                        self.last_result = result
                        return result

                    pid = self._int_or_none(state.get("server_pid"))
                    terminated = self._terminate_managed_process(state)

                    if not terminated and self._health_ok(
                        state.get("host", self.host),
                        state.get("port", self.port),
                    ):
                        self._write_state(state)
                        result = RuntimeResult(
                            False,
                            "refused",
                            "No other FOXAI clients remain, but the running "
                            "process could not be safely verified for "
                            "termination. It was left online.",
                            state.get("model_name"),
                            pid,
                            False,
                        )
                        self.last_result = result
                        return result

                    self._wait_for_process_exit(pid, timeout=5)
                    self._clear_state()
                    self.process = None
                    result = RuntimeResult(
                        True,
                        "stopped",
                        "Shared neural runtime stopped.",
                        state.get("model_name"),
                        pid,
                        True,
                    )
                    self.last_result = result
                    return result

                if self.process is not None and self.process.poll() is None:
                    pid = getattr(self.process, "pid", None)
                    self.process.terminate()
                    self._wait_for_process_exit(pid, timeout=5)
                    self.process = None
                    result = RuntimeResult(
                        True,
                        "stopped",
                        "Neural runtime owned by this interface stopped.",
                        self.model.name if self.model else None,
                        pid,
                        True,
                    )
                    self.last_result = result
                    return result

                result = RuntimeResult(
                    True,
                    "offline",
                    "No shared neural runtime is registered.",
                )
                self.last_result = result
                return result

        except Exception as exc:
            result = RuntimeResult(
                False,
                "failed",
                f"Shared neural runtime stop error: {exc}",
            )
            self.last_result = result
            return result

    def release(self):
        return self.stop()

    def is_running(self):
        return self._health_ok(self.host, self.port) or self.owns_process()

    def is_healthy(self):
        return self._health_ok(self.host, self.port)

    def owns_process(self):
        return (
            self.process is not None
            and self.process.poll() is None
        )

    # -------------------------
    # Shared-state coordination
    # -------------------------

    def _attach_to_healthy_runtime(self, state, target):
        if state and self._same_endpoint(state, target):
            pid = self._int_or_none(state.get("server_pid"))
            process_match = self._process_matches_state(pid, state)

            process_compatible = (
                process_match is True
                if target["require_verified_settings"]
                else process_match is not False
            )
            if (
                self._same_model(state, target)
                and (pid is None or self._pid_exists(pid))
                and process_compatible
            ):
                state["status"] = "ready"
                state["updated_at"] = self._now()
                state = self._register_client(state)
                self._write_state(state)
                return RuntimeResult(
                    True,
                    "attached",
                    f"Attached to the existing shared neural runtime "
                    f"using {target['model_name']}.",
                    target["model_name"],
                    pid,
                    False,
                    {
                        "host": target["host"],
                        "port": target["port"],
                        "active_context": state.get("context"),
                        "active_threads": state.get("threads"),
                        "requested_context": target["context"],
                        "requested_threads": target["threads"],
                        "active_reasoning_mode": self._state_reasoning_mode(state),
                        "active_reasoning_budget": self._state_reasoning_budget(state),
                        "requested_reasoning_mode": target["reasoning_mode"],
                        "requested_reasoning_budget": target["reasoning_budget"],
                        "settings_verified": target["require_verified_settings"],
                    },
                )

            if not self._same_model(state, target):
                return self._conflict_result(
                    target,
                    state,
                    "A healthy shared neural runtime is using a different "
                    "model or runtime profile.",
                )

        if target["require_verified_settings"]:
            return RuntimeResult(
                False,
                "conflict",
                "A healthy neural runtime is already using the configured "
                "endpoint, but FOXAI cannot verify its context, thread, and "
                "reasoning settings for the selected profile. Stop that "
                "runtime before starting this profile.",
                target["model_name"],
                self._int_or_none((state or {}).get("server_pid")),
                False,
                {
                    "host": target["host"],
                    "port": target["port"],
                    "requested_context": target["context"],
                    "requested_threads": target["threads"],
                    "requested_reasoning_mode": target["reasoning_mode"],
                    "requested_reasoning_budget": target["reasoning_budget"],
                    "settings_verified": False,
                },
            )

        model_ids = self._probe_model_ids(target["host"], target["port"])
        if self._model_matches_ids(target["model_path"], model_ids):
            external_state = state or {
                "version": 1,
                "engine_path": None,
                "server_pid": None,
                "owner_interface": "External",
                "owner_process_pid": None,
                "launched_at": None,
                "clients": {},
            }
            external_state.update(
                {
                    "status": "ready",
                    "host": target["host"],
                    "port": target["port"],
                    "model_path": target["model_path"],
                    "model_name": target["model_name"],
                    "context": external_state.get("context"),
                    "threads": external_state.get("threads"),
                    "reasoning_mode": external_state.get("reasoning_mode"),
                    "reasoning_budget": external_state.get("reasoning_budget"),
                    "updated_at": self._now(),
                }
            )
            external_state = self._register_client(external_state)
            self._write_state(external_state)
            return RuntimeResult(
                True,
                "attached",
                f"Attached to a healthy compatible neural runtime using "
                f"{target['model_name']}.",
                target["model_name"],
                self._int_or_none(external_state.get("server_pid")),
                False,
                {
                    "host": target["host"],
                    "port": target["port"],
                    "model_ids": model_ids,
                },
            )

        return RuntimeResult(
            False,
            "conflict",
            "A healthy service is already using the configured neural "
            "endpoint, but FOXAI could not verify that it is running the "
            f"selected model {target['model_name']}. No duplicate server "
            "was launched.",
            target["model_name"],
            self._int_or_none((state or {}).get("server_pid")),
            False,
            {
                "host": target["host"],
                "port": target["port"],
                "detected_model_ids": model_ids,
            },
        )

    def _conflict_result(self, target, state, reason):
        return RuntimeResult(
            False,
            "conflict",
            f"{reason} Selected: {target['model_name']}. "
            f"Active: {state.get('model_name') or 'unknown'}. "
            "Stop the active runtime or select the same model and profile.",
            target["model_name"],
            self._int_or_none(state.get("server_pid")),
            False,
            {
                "host": target["host"],
                "port": target["port"],
                "active_model": state.get("model_name"),
                "active_context": state.get("context"),
                "active_threads": state.get("threads"),
                "requested_reasoning_mode": target["reasoning_mode"],
                "requested_reasoning_budget": target["reasoning_budget"],
                "active_reasoning_mode": self._state_reasoning_mode(state),
                "active_reasoning_budget": self._state_reasoning_budget(state),
                "settings_verified": False,
            },
        )

    def _target(
        self,
        model,
        host,
        port,
        context,
        threads,
        reasoning_mode="current",
        reasoning_budget=None,
        require_verified_settings=False,
    ):
        path = Path(model).resolve()
        mode = str(reasoning_mode or "current").strip().lower()
        if mode not in {"current", "off"}:
            raise ValueError(
                "Unsupported reasoning mode. Allowed values: current, off."
            )
        if mode == "off":
            budget = 0 if reasoning_budget in (None, "") else int(
                reasoning_budget
            )
            if budget != 0:
                raise ValueError(
                    "The approved reasoning-off profile requires budget 0."
                )
        else:
            if reasoning_budget not in (None, ""):
                raise ValueError(
                    "Reasoning budget must be omitted for current mode."
                )
            budget = None
        return {
            "model_path": str(path),
            "model_name": path.name,
            "host": str(host),
            "port": str(port),
            "context": str(context),
            "threads": str(threads),
            "reasoning_mode": mode,
            "reasoning_budget": budget,
            "require_verified_settings": bool(require_verified_settings),
        }

    def _same_endpoint(self, state, target):
        return (
            str(state.get("host")) == target["host"]
            and str(state.get("port")) == target["port"]
        )

    def _state_reasoning_mode(self, state):
        return str(state.get("reasoning_mode") or "current").strip().lower()

    def _state_reasoning_budget(self, state):
        if self._state_reasoning_mode(state) != "off":
            return None
        value = state.get("reasoning_budget")
        try:
            return 0 if value in (None, "") else int(value)
        except Exception:
            return value

    def _same_model(self, state, target):
        state_path = state.get("model_path")
        if state_path:
            model_matches = (
                self._normalized_path(state_path)
                == self._normalized_path(target["model_path"])
            )
        else:
            model_matches = str(
                state.get("model_name", "")
            ).casefold() == target["model_name"].casefold()
        if not model_matches:
            return False
        if not target["require_verified_settings"]:
            return True
        return (
            str(state.get("context")) == target["context"]
            and str(state.get("threads")) == target["threads"]
            and self._state_reasoning_mode(state)
            == target["reasoning_mode"]
            and self._state_reasoning_budget(state)
            == target["reasoning_budget"]
        )

    def _client_key(self):
        return f"{self.interface_name}:{os.getpid()}"

    def _register_client(self, state):
        clients = dict(state.get("clients") or {})
        clients[self._client_key()] = {
            "interface": self.interface_name,
            "pid": os.getpid(),
            "attached_at": clients.get(
                self._client_key(), {}
            ).get("attached_at", self._now()),
            "last_seen": self._now(),
        }
        state["clients"] = clients
        return state

    def _unregister_client(self, state):
        clients = dict(state.get("clients") or {})
        clients.pop(self._client_key(), None)
        state["clients"] = clients
        return state

    def _prune_clients(self, state):
        if not state:
            return state
        clients = {}
        for key, client in (state.get("clients") or {}).items():
            pid = self._int_or_none(client.get("pid"))
            if pid is not None and self._pid_exists(pid):
                clients[key] = client
        state["clients"] = clients
        return state

    def _read_state(self):
        try:
            if not self.state_file.exists():
                return None
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _write_state(self, state):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state, indent=2, sort_keys=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            dir=str(self.state_file.parent),
            prefix=self.state_file.name + ".",
            suffix=".tmp",
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(payload)
        temp_path.replace(self.state_file)

    def _clear_state(self):
        try:
            self.state_file.unlink(missing_ok=True)
        except Exception:
            pass

    @contextmanager
    def _runtime_lock(self, timeout=10, stale_after=120):
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + timeout
        fd = None

        while fd is None:
            try:
                fd = os.open(
                    str(self.lock_file),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
                os.write(
                    fd,
                    json.dumps(
                        {
                            "interface": self.interface_name,
                            "pid": os.getpid(),
                            "created_at": self._now(),
                        }
                    ).encode("utf-8"),
                )
            except FileExistsError:
                try:
                    age = time.time() - self.lock_file.stat().st_mtime
                    if age > stale_after:
                        self.lock_file.unlink(missing_ok=True)
                        continue
                except Exception:
                    pass

                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        "Shared neural runtime coordinator is busy. "
                        "No server was launched."
                    )
                time.sleep(0.1)

        try:
            yield
        finally:
            try:
                os.close(fd)
            except Exception:
                pass
            try:
                self.lock_file.unlink(missing_ok=True)
            except Exception:
                pass

    # -------------------------
    # Process and endpoint checks
    # -------------------------

    def _launch_process(self, target):
        cmd = [
            str(ENGINE),
            "--model",
            target["model_path"],
            "--host",
            target["host"],
            "--port",
            target["port"],
            "--ctx-size",
            target["context"],
            "--threads",
            target["threads"],
        ]
        if target["reasoning_mode"] == "off":
            cmd.extend(
                [
                    "--reasoning",
                    "off",
                    "--reasoning-budget",
                    str(target["reasoning_budget"]),
                ]
            )
        creationflags = (
            getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            if self.new_console and os.name == "nt"
            else 0
        )
        return subprocess.Popen(
            cmd,
            cwd=str(ENGINE.parent.parent),
            creationflags=creationflags,
        )

    def _health_ok(self, host, port):
        try:
            url = f"http://{host}:{port}/health"
            with urllib.request.urlopen(url, timeout=1.5) as response:
                response.read(64)
            return True
        except Exception:
            return False

    def _port_open(self, host, port):
        try:
            with socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM,
            ) as sock:
                sock.settimeout(0.4)
                return sock.connect_ex((str(host), int(port))) == 0
        except Exception:
            return False

    def _probe_model_ids(self, host, port):
        try:
            url = f"http://{host}:{port}/v1/models"
            with urllib.request.urlopen(url, timeout=1.5) as response:
                payload = json.loads(
                    response.read().decode("utf-8", errors="replace")
                )
            ids = []
            for item in payload.get("data", []):
                if isinstance(item, dict) and item.get("id"):
                    ids.append(str(item["id"]))
            return ids
        except Exception:
            return []

    def _model_matches_ids(self, model_path, model_ids):
        if not model_ids:
            return False
        wanted = self._model_tokens(model_path)
        generic = {"model", "local-model", "local_model", "default"}
        for model_id in model_ids:
            tokens = self._model_tokens(model_id)
            if tokens & generic:
                continue
            if wanted & tokens:
                return True
        return False

    def _model_tokens(self, value):
        raw = str(value or "").replace("\\", "/")
        name = Path(raw).name.casefold()
        stem = Path(name).stem.casefold()
        return {name, stem}

    def _pid_exists(self, pid):
        if not pid or pid <= 0:
            return False
        try:
            import psutil
            return psutil.pid_exists(pid)
        except Exception:
            try:
                os.kill(pid, 0)
                return True
            except Exception:
                return False

    def _process_matches_state(self, pid, state):
        if not pid:
            return None
        try:
            import psutil
            process = psutil.Process(pid)
            cmdline = [str(arg) for arg in process.cmdline()]
            if not cmdline:
                return None

            executable = self._normalized_path(cmdline[0])
            expected_engine = self._normalized_path(
                state.get("engine_path") or ENGINE
            )
            if executable != expected_engine:
                try:
                    executable = self._normalized_path(process.exe())
                except Exception:
                    pass
            if executable != expected_engine:
                return False

            model = state.get("model_path")
            if model:
                normalized_cmd = {
                    self._normalized_path(arg)
                    for arg in cmdline
                    if arg
                }
                if self._normalized_path(model) not in normalized_cmd:
                    return False

            def flag_value(flag):
                try:
                    index = cmdline.index(flag)
                except ValueError:
                    return None
                if index + 1 >= len(cmdline):
                    return None
                return str(cmdline[index + 1])

            if state.get("context") is not None:
                if flag_value("--ctx-size") != str(state.get("context")):
                    return False
            if state.get("threads") is not None:
                if flag_value("--threads") != str(state.get("threads")):
                    return False
            if self._state_reasoning_mode(state) == "off":
                if flag_value("--reasoning") != "off":
                    return False
                if flag_value("--reasoning-budget") != str(
                    self._state_reasoning_budget(state)
                ):
                    return False
            return True
        except Exception:
            return None

    def _terminate_managed_process(self, state):
        pid = self._int_or_none(state.get("server_pid"))

        if (
            self.process is not None
            and self.process.poll() is None
            and getattr(self.process, "pid", None) == pid
        ):
            self.process.terminate()
            return True

        if self._process_matches_state(pid, state) is not True:
            return False

        try:
            import psutil
            psutil.Process(pid).terminate()
            return True
        except Exception:
            return False

    def _wait_for_process_exit(self, pid, timeout=5):
        if not pid:
            return
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self._pid_exists(pid):
                return
            time.sleep(0.1)

    def _current_server_pid(self):
        state = self._read_state() or {}
        return self._int_or_none(state.get("server_pid"))

    def _normalized_path(self, value):
        try:
            return os.path.normcase(
                os.path.abspath(os.path.expandvars(str(value)))
            )
        except Exception:
            return str(value).casefold()

    def _int_or_none(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _now(self):
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
