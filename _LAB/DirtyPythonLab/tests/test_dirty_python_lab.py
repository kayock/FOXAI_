from __future__ import annotations

import ast
import json
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dirty_python_lab import (  # noqa: E402
    DirtyPythonLabEngine,
    LabApplication,
    LabConfig,
    QwenClient,
    WorkspaceTools,
    main,
)


class MockQwenHandler(BaseHTTPRequestHandler):
    request_count = 0

    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path == "/v1/models":
            body = json.dumps({"data": [{"id": "mock-qwen-model"}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length).decode("utf-8"))
        type(self).request_count += 1
        last_user = request["messages"][-1]["content"]
        if "Previous script:" in last_user:
            content = "```python\nprint('repaired and working')\n```"
        else:
            content = "```python\nprint(missing_name)\n```"
        body = json.dumps({"choices": [{"message": {"content": content}}]}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class DirtyPythonLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        MockQwenHandler.request_count = 0
        cls.mock_server = ThreadingHTTPServer(("127.0.0.1", 0), MockQwenHandler)
        cls.mock_thread = threading.Thread(target=cls.mock_server.serve_forever, daemon=True)
        cls.mock_thread.start()
        cls.endpoint = f"http://127.0.0.1:{cls.mock_server.server_address[1]}/v1/chat/completions"

    @classmethod
    def tearDownClass(cls):
        cls.mock_server.shutdown()
        cls.mock_server.server_close()

    def test_extracts_fenced_python(self):
        source = "Before\n```python\nprint('ok')\n```\nAfter"
        self.assertEqual(QwenClient.extract_python_code(source), "print('ok')\n")


    def test_runtime_uses_standard_library_only(self):
        source_path = Path(__file__).resolve().parents[1] / "dirty_python_lab.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        third_party = sorted(
            name for name in imported
            if name not in sys.stdlib_module_names and name != "__future__"
        )
        self.assertEqual(third_party, [])
        self.assertNotIn("tkinter", imported)

    def test_full_generate_fail_repair_rerun_loop(self):
        with tempfile.TemporaryDirectory() as temp:
            config = LabConfig(
                workspace_root=temp,
                qwen_endpoint=self.endpoint,
                max_repairs=2,
                run_timeout_seconds=5,
                request_timeout_seconds=5,
            )
            result = DirtyPythonLabEngine(config).run("Print a success message")
            self.assertTrue(result.success)
            self.assertEqual(len(result.attempts), 2)
            self.assertNotEqual(result.attempts[0].return_code, 0)
            self.assertIn("NameError", result.attempts[0].stderr)
            self.assertEqual(result.attempts[1].return_code, 0)
            self.assertIn("repaired and working", result.attempts[1].stdout)
            run_folder = Path(result.run_folder)
            self.assertTrue((run_folder / "ATTEMPT_1.py").exists())
            self.assertTrue((run_folder / "ATTEMPT_2.py").exists())
            self.assertTrue((run_folder / "RESULT.json").exists())


    def test_vscode_locator_finds_and_remembers_exact_executable(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / "workspace"
            search_root = base / "portable-vscode"
            shallow = search_root / "release" / "Code.exe"
            deep = search_root / "old" / "nested" / "Code.exe"
            shallow.parent.mkdir(parents=True)
            deep.parent.mkdir(parents=True)
            shallow.write_bytes(b"test executable placeholder")
            deep.write_bytes(b"older executable placeholder")
            config = LabConfig(
                workspace_root=str(workspace),
                qwen_endpoint=self.endpoint,
                vscode_search_root=str(search_root),
            )
            tools = WorkspaceTools(config)
            located = tools.locate_vscode(force=True)
            self.assertTrue(located["found"])
            self.assertEqual(Path(located["path"]), shallow)
            self.assertEqual(located["candidate_count"], 2)
            state = json.loads((workspace / "lab_state.json").read_text(encoding="utf-8"))
            self.assertEqual(Path(state["vscode_executable"]), shallow)
            remembered = tools.locate_vscode(force=False)
            self.assertTrue(remembered["found"])
            self.assertEqual(remembered["source"], "remembered")

    def test_open_vscode_uses_verified_executable_and_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            workspace = base / "workspace"
            executable = base / "portable-vscode" / "Code.exe"
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"test executable placeholder")
            config = LabConfig(
                workspace_root=str(workspace),
                qwen_endpoint=self.endpoint,
                vscode_search_root=str(executable.parent),
            )
            tools = WorkspaceTools(config)
            with patch("dirty_python_lab.subprocess.Popen") as popen:
                result = tools.open_vscode()
            self.assertTrue(result["found"])
            popen.assert_called_once_with(
                [str(executable), str(workspace)],
                cwd=str(executable.parent),
                shell=False,
            )

    def test_history_skips_incomplete_folders(self):
        with tempfile.TemporaryDirectory() as temp:
            config = LabConfig(
                workspace_root=temp,
                qwen_endpoint=self.endpoint,
                max_repairs=2,
                run_timeout_seconds=5,
                request_timeout_seconds=5,
            )
            engine = DirtyPythonLabEngine(config)
            (engine.runs_root / "INCOMPLETE").mkdir()
            result = engine.run("Create a history entry")
            history = engine.list_history()
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["run_id"], result.run_id)
            self.assertTrue(history[0]["success"])
            self.assertEqual(history[0]["attempt_count"], 2)

    def test_one_click_acceptance_cli_uses_same_repair_loop(self):
        with tempfile.TemporaryDirectory() as temp:
            config_path = Path(temp) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "workspace_root": temp,
                        "qwen_endpoint": self.endpoint,
                        "max_repairs": 2,
                        "run_timeout_seconds": 5,
                        "request_timeout_seconds": 5,
                    }
                ),
                encoding="utf-8",
            )
            exit_code = main(["--config", str(config_path), "--acceptance-test"])
            self.assertEqual(exit_code, 0)
            history = DirtyPythonLabEngine(LabConfig.load(config_path)).list_history()
            self.assertEqual(len(history), 1)
            self.assertTrue(history[0]["success"])
            self.assertEqual(history[0]["attempt_count"], 2)

    def test_browser_home_and_status(self):
        with tempfile.TemporaryDirectory() as temp:
            vscode_root = Path(temp) / "portable-vscode"
            vscode_root.mkdir()
            (vscode_root / "Code.exe").write_bytes(b"test executable placeholder")
            config = LabConfig(
                workspace_root=temp,
                qwen_endpoint=self.endpoint,
                host="127.0.0.1",
                port=0,
                vscode_search_root=str(vscode_root),
            )
            app = LabApplication(config)
            app.server = ThreadingHTTPServer((config.host, 0), app.make_handler())
            thread = threading.Thread(target=app.server.serve_forever, daemon=True)
            thread.start()
            port = app.server.server_address[1]
            try:
                home = urlopen(f"http://127.0.0.1:{port}/", timeout=5).read().decode("utf-8")
                self.assertIn("RUN &amp; AUTO-REPAIR", home)
                self.assertIn("OPEN IN PORTABLE VS CODE", home)
                self.assertIn("Recent Runs", home)
                status = json.loads(
                    urlopen(f"http://127.0.0.1:{port}/api/status", timeout=5).read().decode("utf-8")
                )
                self.assertEqual(status["version"], "0.2.0")

                request = Request(
                    f"http://127.0.0.1:{port}/api/run",
                    data=json.dumps({"prompt": "Print a browser-path success message"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                api_result = json.loads(urlopen(request, timeout=10).read().decode("utf-8"))
                self.assertTrue(api_result["success"])
                self.assertEqual(len(api_result["attempts"]), 2)
                self.assertIn("repaired and working", api_result["attempts"][-1]["stdout"])
                history = json.loads(
                    urlopen(f"http://127.0.0.1:{port}/api/history", timeout=5).read().decode("utf-8")
                )
                self.assertEqual(len(history["runs"]), 1)
                self.assertTrue(history["runs"][0]["success"])
                preflight = json.loads(
                    urlopen(f"http://127.0.0.1:{port}/api/preflight", timeout=5).read().decode("utf-8")
                )
                self.assertTrue(preflight["python"]["available"])
                self.assertTrue(preflight["qwen"]["reachable"])
                self.assertTrue(preflight["vscode"]["found"])
                self.assertTrue(preflight["vscode"]["path"].endswith("Code.exe"))
            finally:
                app.server.shutdown()
                app.server.server_close()


if __name__ == "__main__":
    unittest.main()
