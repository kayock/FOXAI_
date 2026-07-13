from __future__ import annotations

import importlib.util
import os
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest


class FakeProcess:
    def __init__(self, pid):
        self.pid = pid
        self.returncode = None
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 0


class SharedRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_root = tempfile.TemporaryDirectory()
        root = Path(cls.temp_root.name)
        engine = root / "Engine" / "llama-server.exe"
        engine.parent.mkdir(parents=True)
        engine.write_bytes(b"fake")

        core = types.ModuleType("core")
        paths = types.ModuleType("core.paths")
        paths.ENGINE = engine
        sys.modules["core"] = core
        sys.modules["core.paths"] = paths

        module_path = Path(os.environ["FOXAI_LIVE_ROOT"]) / "core" / "server.py"
        spec = importlib.util.spec_from_file_location("candidate_server", module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["candidate_server"] = module
        spec.loader.exec_module(module)
        cls.module = module
        cls.engine = engine

    @classmethod
    def tearDownClass(cls):
        cls.temp_root.cleanup()

    def setUp(self):
        self.runtime_dir = tempfile.TemporaryDirectory()
        self.state_file = Path(self.runtime_dir.name) / "shared.json"
        self.alive_pids = set()
        self.health = False
        self.port_open = False
        self.model_ids = []
        self.processes = {}
        self.next_pid = 4000

        parent = self

        class FakeServer(self.module.LlamaServer):
            def _health_ok(inner, host, port):
                return parent.health

            def _port_open(inner, host, port):
                return parent.port_open

            def _pid_exists(inner, pid):
                import os
                return int(pid) == os.getpid() or int(pid) in parent.alive_pids

            def _probe_model_ids(inner, host, port):
                return list(parent.model_ids)

            def _process_matches_state(inner, pid, state):
                if pid in parent.alive_pids:
                    return True
                return False

            def _launch_process(inner, target):
                pid = parent.next_pid
                parent.next_pid += 1
                proc = FakeProcess(pid)
                parent.processes[pid] = proc
                parent.alive_pids.add(pid)
                parent.port_open = True
                return proc

            def _terminate_managed_process(inner, state):
                pid = inner._int_or_none(state.get("server_pid"))
                proc = parent.processes.get(pid)
                if proc:
                    proc.terminate()
                parent.alive_pids.discard(pid)
                parent.health = False
                parent.port_open = False
                return pid is not None

            def _wait_for_process_exit(inner, pid, timeout=5):
                return

        self.Server = FakeServer
        self.model_a = Path(self.runtime_dir.name) / "Model-A.gguf"
        self.model_b = Path(self.runtime_dir.name) / "Model-B.gguf"
        self.model_a.write_bytes(b"a")
        self.model_b.write_bytes(b"b")

    def tearDown(self):
        self.runtime_dir.cleanup()

    def make(self, name):
        return self.Server(interface_name=name, state_file=self.state_file)

    def test_second_interface_waits_instead_of_launching_duplicate(self):
        desktop = self.make("Desktop")
        web = self.make("WebUI")

        first = desktop.ensure_running(self.model_a)
        self.assertEqual(first.action, "launched")
        self.assertEqual(len(self.processes), 1)

        second = web.ensure_running(self.model_a)
        self.assertTrue(second.ok)
        self.assertEqual(second.action, "waiting")
        self.assertEqual(len(self.processes), 1)

    def test_healthy_same_model_attaches_and_registers_both_clients(self):
        desktop = self.make("Desktop")
        web = self.make("WebUI")
        desktop.ensure_running(self.model_a)
        self.health = True

        attached = web.ensure_running(self.model_a)
        self.assertEqual(attached.action, "attached")
        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        self.assertEqual(set(state["clients"]), {
            f"Desktop:{__import__('os').getpid()}",
            f"WebUI:{__import__('os').getpid()}",
        })

    def test_different_model_is_blocked_without_duplicate(self):
        desktop = self.make("Desktop")
        web = self.make("WebUI")
        desktop.ensure_running(self.model_a)
        self.health = True

        conflict = web.ensure_running(self.model_b)
        self.assertFalse(conflict.ok)
        self.assertEqual(conflict.action, "conflict")
        self.assertEqual(len(self.processes), 1)

    def test_owner_detaches_without_stopping_other_client(self):
        desktop = self.make("Desktop")
        web = self.make("WebUI")
        launched = desktop.ensure_running(self.model_a)
        self.health = True
        web.ensure_running(self.model_a)

        detached = desktop.stop()
        self.assertTrue(detached.ok)
        self.assertEqual(detached.action, "detached")
        self.assertIn(launched.pid, self.alive_pids)
        self.assertFalse(self.processes[launched.pid].terminated)

    def test_last_client_stops_verified_shared_process(self):
        desktop = self.make("Desktop")
        web = self.make("WebUI")
        launched = desktop.ensure_running(self.model_a)
        self.health = True
        web.ensure_running(self.model_a)
        desktop.stop()

        stopped = web.stop()
        self.assertTrue(stopped.ok)
        self.assertEqual(stopped.action, "stopped")
        self.assertNotIn(launched.pid, self.alive_pids)
        self.assertFalse(self.state_file.exists())

    def test_unknown_healthy_service_is_not_claimed_or_duplicated(self):
        server = self.make("Desktop")
        self.health = True
        self.port_open = True

        conflict = server.ensure_running(self.model_a)
        self.assertFalse(conflict.ok)
        self.assertEqual(conflict.action, "conflict")
        self.assertEqual(len(self.processes), 0)

    def test_compatible_v1_models_service_can_be_attached(self):
        server = self.make("Desktop")
        self.health = True
        self.port_open = True
        self.model_ids = ["Model-A.gguf"]

        attached = server.ensure_running(self.model_a)
        self.assertTrue(attached.ok)
        self.assertEqual(attached.action, "attached")
        self.assertEqual(len(self.processes), 0)

    def test_stale_state_is_replaced_by_one_new_launch(self):
        self.state_file.write_text(json.dumps({
            "version": 1,
            "status": "starting",
            "server_pid": 9999,
            "host": "127.0.0.1",
            "port": "8080",
            "model_path": str(self.model_a.resolve()),
            "model_name": self.model_a.name,
            "clients": {},
        }), encoding="utf-8")

        server = self.make("Desktop")
        result = server.ensure_running(self.model_a)
        self.assertEqual(result.action, "launched")
        self.assertEqual(len(self.processes), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
