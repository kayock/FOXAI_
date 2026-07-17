from __future__ import annotations

import base64
import csv
import hashlib
import html
import json
import os
import re
import shutil
import socket
import statistics
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LIVE_HASHES = {
    "core/foxai_web.py":
        "e4d5811f14ae3ffb0b3f8b59369bee5c0a1218d19459f2decc875589540d04fb",
    "core/server.py":
        "9ee8871553113459ac4e234873de2cd3352aa5529ab58fab8d02ece0a53d0c07",
    "core/security_containment.py":
        "9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24",
    "core/engineer_agent.py":
        "f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19",
    "tests/test_boundary_watch.py":
        "b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382",
    "Config/FoxAI.ini":
        "677067e2b58416ba7d7bacc1dcfe40b9f43783e625dd305d0bbf82b6d3174d41",
    "Engine/llama-server.exe":
        "936cfb77f011911f879a5af715013eb12141115547c1f731114d8e9c20ebd89e",
}

MODELS = {
    "fast": {
        "profile": "Fast Vision",
        "filename": "Qwen3VL-8B-Instruct-Q4_K_M.gguf",
        "relative": "Models/Chat/Qwen3VL-8B-Instruct-Q4_K_M.gguf",
        "expected_size": 5027784800,
    },
    "quality": {
        "profile": "Quality Vision",
        "filename": "Qwen3VL-8B-Instruct-Q8_0.gguf",
        "relative": "Models/Chat/Qwen3VL-8B-Instruct-Q8_0.gguf",
        "expected_size": 8709519456,
    },
}

HOST = "127.0.0.1"
PORT = 8098
CONTEXT = "8192"
THREADS = "12"
HEALTH_TIMEOUT = 360
REQUEST_TIMEOUT = 600
MAX_PROJECTOR_ATTEMPTS = 3

CLOSED_PORTS = {
    8765: "FOXAI WebUI",
    8080: "Chat Engine",
    8098: "Vision benchmark",
    8099: "Other benchmark",
}

TESTS = [
    {
        "id": "ocr",
        "title": "Exact OCR and Counting",
        "image": "images/ocr_card.png",
        "max_tokens": 180,
        "prompt": (
            "Read the image carefully. Return JSON only with exactly these keys: "
            "title, code, door_label, star_count, bicycle_present. Preserve visible "
            "capitalization for text values. Use an integer for star_count and a "
            "JSON boolean for bicycle_present."
        ),
    },
    {
        "id": "spatial",
        "title": "Spatial Relationships",
        "image": "images/spatial_scene.png",
        "max_tokens": 180,
        "prompt": (
            "Analyze the diagram. Return JSON only with exactly these keys: "
            "leftmost_shape, rightmost_shape, topmost_shape, bottommost_shape, "
            "arrow_direction, colored_shape_count. Include each shape's color and "
            "geometry, and use an integer for colored_shape_count."
        ),
    },
    {
        "id": "ui",
        "title": "Screenshot/UI Understanding",
        "image": "images/ui_mock.png",
        "max_tokens": 180,
        "prompt": (
            "Treat this as a software screenshot. Return JSON only with exactly "
            "these keys: app_title, selected_profile, selected_status, main_button, "
            "mode, screen_code. Copy the visible wording without adding commentary."
        ),
    },
    {
        "id": "detail",
        "title": "Detailed Scene Description",
        "image": "images/detail_scene.png",
        "max_tokens": 320,
        "prompt": (
            "Describe the image in 120 to 180 words. Mention the time written in the "
            "image, the mug color, the number of visible paper clips, the plant, "
            "the notebook, and the key. Do not invent people or animals."
        ),
    },
    {
        "id": "hallucination",
        "title": "Hallucination Resistance",
        "image": "images/ocr_card.png",
        "max_tokens": 120,
        "prompt": (
            "Return JSON only with exactly these keys: bicycle_visible, evidence. "
            "Use a JSON boolean for bicycle_visible. For evidence, quote the exact "
            "visible sentence that answers the question."
        ),
    },
]


class VisionError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "sha256": None, "size_bytes": 0}
    if not path.is_file():
        return {"exists": True, "not_file": True, "sha256": None}
    return {
        "exists": True,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
    }


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (
            (candidate / "core/foxai_web.py").is_file()
            and (candidate / "Engine/llama-server.exe").is_file()
        ):
            return candidate
    raise VisionError(
        r"FOXAI root not found. Extract the complete VIT1 folder directly inside Z:\FOXAI."
    )


def protected_snapshot(root: Path) -> dict[str, Any]:
    result = {
        relative: file_state(root / relative)
        for relative in LIVE_HASHES
    }
    security = root / "Logs/Security"
    if security.exists():
        for path in sorted(security.rglob("*")):
            if path.is_file():
                relative = str(path.relative_to(root)).replace("\\", "/")
                result[relative] = file_state(path)
    return result


def snapshot_changes(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return [
        key for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    ]


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((HOST, port)) == 0


def request_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> tuple[int, Any, str]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = None
            return response.status, parsed, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = None
        return exc.code, parsed, raw


def image_data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def projector_candidates(root: Path, model_name: str) -> list[dict[str, Any]]:
    model_tokens = {
        token.lower()
        for token in re.split(r"[-_.]+", Path(model_name).stem)
        if len(token) >= 2
    }
    result = []
    model_paths = [root / "Models", root]
    seen = set()
    for base in model_paths:
        if not base.exists():
            continue
        for path in base.rglob("*.gguf"):
            resolved = str(path.resolve()).lower()
            if resolved in seen:
                continue
            seen.add(resolved)
            name = path.name.lower()
            if "mmproj" not in name and "projector" not in name:
                continue
            tokens = {
                token.lower()
                for token in re.split(r"[-_.]+", path.stem)
                if len(token) >= 2
            }
            score = len(model_tokens & tokens)
            if "qwen3vl" in name or ("qwen3" in name and "vl" in name):
                score += 12
            if "8b" in name:
                score += 4
            if "instruct" in name:
                score += 2
            if "f16" in name:
                score += 1
            result.append({
                "path": str(path),
                "relative": str(path.relative_to(root)).replace("\\", "/")
                    if root in path.parents else str(path),
                "filename": path.name,
                "size_bytes": path.stat().st_size,
                "score": score,
            })
    return sorted(
        result,
        key=lambda item: (-item["score"], item["filename"].lower()),
    )


def engine_help(engine: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [str(engine), "--help"],
        cwd=str(engine.parent.parent),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    text = (completed.stdout or "") + "\n" + (completed.stderr or "")
    return {
        "returncode": completed.returncode,
        "supports_mmproj": "--mmproj" in text,
        "supports_reasoning": "--reasoning" in text,
        "supports_reasoning_budget": "--reasoning-budget" in text,
        "excerpt": "\n".join(
            line for line in text.splitlines()
            if any(key in line.lower() for key in ("mmproj", "multimodal", "vision"))
        )[:10000],
    }


def wait_health(process: subprocess.Popen) -> dict[str, Any]:
    started = time.perf_counter()
    deadline = started + HEALTH_TIMEOUT
    last = ""
    while time.perf_counter() < deadline:
        if process.poll() is not None:
            return {
                "ready": False,
                "seconds": round(time.perf_counter() - started, 3),
                "failure": f"server exited with code {process.returncode}",
                "last": last[-3000:],
            }
        try:
            status, parsed, raw = request_json(
                "GET",
                f"http://{HOST}:{PORT}/health",
                timeout=3,
            )
            last = raw
            if status == 200:
                return {
                    "ready": True,
                    "seconds": round(time.perf_counter() - started, 3),
                    "health": parsed if parsed is not None else raw,
                }
        except Exception as exc:
            last = str(exc)
        time.sleep(0.5)
    return {
        "ready": False,
        "seconds": round(time.perf_counter() - started, 3),
        "failure": "health timeout",
        "last": last[-3000:],
    }


def stop_process(process: subprocess.Popen | None) -> dict[str, Any]:
    if process is None:
        return {"requested": False, "stopped": True}
    if process.poll() is not None:
        return {
            "requested": False,
            "stopped": True,
            "exit_code": process.returncode,
        }
    result = {"requested": True, "stopped": False}
    try:
        process.terminate()
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    timeout=40,
                    check=False,
                )
            else:
                process.kill()
            process.wait(timeout=20)
        result.update({
            "stopped": process.poll() is not None,
            "exit_code": process.poll(),
        })
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def extract_answer(parsed: Any) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        return {"content": "", "reasoning": "", "finish_reason": ""}
    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices:
        return {"content": "", "reasoning": "", "finish_reason": ""}
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message") if isinstance(first.get("message"), dict) else {}
    content = message.get("content")
    if isinstance(content, list):
        content = "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict)
        )
    if not isinstance(content, str):
        content = ""
    reasoning = message.get("reasoning_content")
    if not isinstance(reasoning, str):
        reasoning = ""
    return {
        "content": content.strip(),
        "reasoning": reasoning,
        "finish_reason": str(first.get("finish_reason") or ""),
    }


def parse_json_answer(text: str) -> Any:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.I)
        value = re.sub(r"\s*```$", "", value)
    try:
        return json.loads(value)
    except Exception:
        match = re.search(r"\{.*\}", value, flags=re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return None


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def validate(test_id: str, text: str) -> dict[str, Any]:
    parsed = parse_json_answer(text)
    checks: dict[str, bool] = {}
    notes: list[str] = []
    if test_id == "ocr":
        data = parsed if isinstance(parsed, dict) else {}
        checks = {
            "valid_json": isinstance(parsed, dict),
            "title": norm(data.get("title")) == "fox sentry vision test",
            "code": str(data.get("code", "")).strip() == "7429",
            "door_label": norm(data.get("door_label")) == "purple door",
            "star_count": data.get("star_count") == 3,
            "bicycle_present_false": data.get("bicycle_present") is False,
        }
    elif test_id == "spatial":
        data = parsed if isinstance(parsed, dict) else {}
        checks = {
            "valid_json": isinstance(parsed, dict),
            "leftmost_red_square":
                "red" in norm(data.get("leftmost_shape"))
                and "square" in norm(data.get("leftmost_shape")),
            "rightmost_blue_circle":
                "blue" in norm(data.get("rightmost_shape"))
                and "circle" in norm(data.get("rightmost_shape")),
            "topmost_green_triangle":
                "green" in norm(data.get("topmost_shape"))
                and "triangle" in norm(data.get("topmost_shape")),
            "bottommost_orange_diamond":
                "orange" in norm(data.get("bottommost_shape"))
                and "diamond" in norm(data.get("bottommost_shape")),
            "arrow_left_to_right":
                "left" in norm(data.get("arrow_direction"))
                and "right" in norm(data.get("arrow_direction")),
            "shape_count": data.get("colored_shape_count") == 4,
        }
    elif test_id == "ui":
        data = parsed if isinstance(parsed, dict) else {}
        checks = {
            "valid_json": isinstance(parsed, dict),
            "app_title": norm(data.get("app_title")) == "model lab",
            "selected_profile": norm(data.get("selected_profile")) == "fast vision",
            "selected_status_contains_ready":
                "ready" in norm(data.get("selected_status")),
            "main_button": norm(data.get("main_button")) == "run image test",
            "mode_contains_offline": "offline" in norm(data.get("mode")),
            "screen_code": norm(data.get("screen_code")) == "v-203",
        }
    elif test_id == "detail":
        words = re.findall(r"[A-Za-z0-9']+", text)
        lower = text.lower()
        checks = {
            "word_range_120_180": 120 <= len(words) <= 180,
            "time_7_15": "7:15" in text,
            "blue_mug": "blue" in lower and "mug" in lower,
            "two_paper_clips":
                ("two" in lower or "2" in lower)
                and ("paper clip" in lower or "paperclip" in lower),
            "plant": "plant" in lower,
            "notebook": "notebook" in lower,
            "key": "key" in lower,
            "no_people_or_animals_invented": not any(
                word in lower
                for word in ("person", "woman", "man ", "cat", "dog", "bird")
            ),
        }
    elif test_id == "hallucination":
        data = parsed if isinstance(parsed, dict) else {}
        checks = {
            "valid_json": isinstance(parsed, dict),
            "bicycle_visible_false": data.get("bicycle_visible") is False,
            "evidence_exact":
                "no bicycle present" in norm(data.get("evidence")),
        }
    else:
        checks = {"known_test": False}
    return {
        "parsed_json": parsed,
        "checks": checks,
        "passed": all(checks.values()),
        "failed_checks": [
            key for key, value in checks.items()
            if value is not True
        ],
        "notes": notes,
    }


def request_vision(
    test: dict[str, Any],
    image_path: Path,
) -> dict[str, Any]:
    payload = {
        "model": "local-model",
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": image_data_url(image_path)},
                },
                {
                    "type": "text",
                    "text": test["prompt"],
                },
            ],
        }],
        "temperature": 0.1,
        "top_p": 0.8,
        "max_tokens": test["max_tokens"],
        "stream": False,
    }
    started = time.perf_counter()
    status, parsed, raw = request_json(
        "POST",
        f"http://{HOST}:{PORT}/v1/chat/completions",
        payload,
        timeout=REQUEST_TIMEOUT,
    )
    elapsed = round(time.perf_counter() - started, 3)
    answer = extract_answer(parsed)
    validation = validate(test["id"], answer["content"])
    usage = parsed.get("usage", {}) if isinstance(parsed, dict) else {}
    timings = parsed.get("timings", {}) if isinstance(parsed, dict) else {}
    tps = timings.get("predicted_per_second")
    if not isinstance(tps, (int, float)):
        completion = usage.get("completion_tokens")
        tps = (
            round(float(completion) / elapsed, 3)
            if isinstance(completion, (int, float))
            and completion > 0 and elapsed > 0
            else None
        )
    return {
        "test_id": test["id"],
        "title": test["title"],
        "image": test["image"],
        "status": status,
        "wall_seconds": elapsed,
        "tokens_per_second": (
            round(float(tps), 3)
            if isinstance(tps, (int, float))
            else None
        ),
        "content": answer["content"],
        "reasoning_character_count": len(answer["reasoning"]),
        "finish_reason": answer["finish_reason"],
        "validation": validation,
        "response_ok": status == 200 and bool(answer["content"]),
        "raw_error_excerpt": (
            raw[:3000]
            if status != 200
            else ""
        ),
    }


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = path.with_suffix(path.suffix + ".tmp")
    stage.write_text(
        json.dumps(value, indent=2),
        encoding="utf-8",
    )
    os.replace(stage, path)


def checkpoint_zip(output: Path) -> Path:
    target = output / "RECOVERY_UPLOAD.zip"
    stage = output / "RECOVERY_UPLOAD.zip.tmp"
    stage.unlink(missing_ok=True)
    with zipfile.ZipFile(
        stage,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for file in sorted(output.rglob("*")):
            if (
                file.is_file()
                and file not in {target, stage}
            ):
                archive.write(
                    file,
                    arcname=f"{output.name}/{file.relative_to(output)}",
                )
    os.replace(stage, target)
    return target


def render_html(
    output: Path,
    package_dir: Path,
    receipt: dict[str, Any],
    results: list[dict[str, Any]],
) -> None:
    cards = []
    for result in results:
        image_name = Path(result["image"]).name
        image_target = output / "images" / image_name
        if not image_target.is_file():
            shutil.copy2(package_dir / result["image"], image_target)
        checks = result["validation"]["checks"]
        check_html = "".join(
            f"<li class=\"{'pass' if value else 'fail'}\">"
            f"{html.escape(key)}: {html.escape(str(value))}</li>"
            for key, value in checks.items()
        )
        cards.append(f"""
        <section class="card">
          <h2>{html.escape(result['profile'])} — {html.escape(result['title'])}</h2>
          <div class="grid">
            <img src="images/{html.escape(image_name)}" alt="benchmark image">
            <div>
              <p><strong>Objective pass:</strong> {result['validation']['passed']}</p>
              <p><strong>Time:</strong> {result['wall_seconds']}s</p>
              <p><strong>Speed:</strong> {result['tokens_per_second']} tok/s</p>
              <pre>{html.escape(result['content'])}</pre>
              <ul>{check_html}</ul>
            </div>
          </div>
        </section>
        """)
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>FOXAI Vision Input Test</title>
<style>
body{{font-family:Arial,sans-serif;background:#0e1020;color:#eee;margin:0;padding:28px}}
h1{{color:#c6a8ff}} .meta,.card{{background:#171a2d;border:1px solid #4f357b;border-radius:18px;padding:20px;margin:18px 0}}
.grid{{display:grid;grid-template-columns:minmax(280px,42%) 1fr;gap:22px}}
img{{width:100%;border-radius:12px;background:white}} pre{{white-space:pre-wrap;background:#0a0b14;padding:14px;border-radius:10px}}
.pass{{color:#64e59d}} .fail{{color:#ff9b9b}} a{{color:#c6a8ff}}
@media(max-width:850px){{.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<h1>FOXAI Real Image Input Test</h1>
<div class="meta">
<p><strong>State:</strong> {html.escape(str(receipt.get('state')))}</p>
<p><strong>Verified:</strong> {html.escape(str(receipt.get('verified')))}</p>
<p><strong>Live files modified:</strong> {html.escape(str(receipt.get('live_files_modified')))}</p>
<p>This report uses actual PNG inputs sent to the local Qwen3VL endpoint.</p>
</div>
{''.join(cards)}
</body>
</html>"""
    (output / "report.html").write_text(document, encoding="utf-8")


def write_reports(
    output: Path,
    package_dir: Path,
    receipt: dict[str, Any],
    results: list[dict[str, Any]],
) -> None:
    measured = [item for item in results if item.get("response_ok")]
    by_profile = {}
    for result in results:
        profile = result["profile"]
        by_profile.setdefault(profile, []).append(result)

    summary = {}
    for profile, items in by_profile.items():
        walls = [item["wall_seconds"] for item in items if item["response_ok"]]
        tps = [
            item["tokens_per_second"]
            for item in items
            if item["tokens_per_second"] is not None
        ]
        summary[profile] = {
            "tests": len(items),
            "completed": sum(1 for item in items if item["response_ok"]),
            "objective_passes":
                sum(1 for item in items if item["validation"]["passed"]),
            "median_wall_seconds":
                round(statistics.median(walls), 3) if walls else None,
            "median_tokens_per_second":
                round(statistics.median(tps), 3) if tps else None,
            "reasoning_leak_count":
                sum(
                    1 for item in items
                    if item["reasoning_character_count"] > 0
                ),
        }

    write_json_atomic(output / "summary.json", summary)
    write_json_atomic(output / "results.json", results)

    with (output / "summary.csv").open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        fields = [
            "profile",
            "model",
            "test_id",
            "title",
            "response_ok",
            "objective_pass",
            "wall_seconds",
            "tokens_per_second",
            "failed_checks",
            "reasoning_character_count",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in results:
            writer.writerow({
                "profile": item["profile"],
                "model": item["model"],
                "test_id": item["test_id"],
                "title": item["title"],
                "response_ok": item["response_ok"],
                "objective_pass": item["validation"]["passed"],
                "wall_seconds": item["wall_seconds"],
                "tokens_per_second": item["tokens_per_second"],
                "failed_checks":
                    "; ".join(item["validation"]["failed_checks"]),
                "reasoning_character_count":
                    item["reasoning_character_count"],
            })

    lines = [
        "# FOXAI Real Image Input Test",
        "",
        f"- State: **{receipt.get('state')}**",
        f"- Verified: **{receipt.get('verified')}**",
        f"- Live files modified: **{receipt.get('live_files_modified')}**",
        "- Apply capability present: **False**",
        "",
        "## Profile summary",
        "",
    ]
    for profile, data in summary.items():
        lines.extend([
            f"### {profile}",
            "",
            f"- Completed: **{data['completed']}/{data['tests']}**",
            f"- Objective passes: **{data['objective_passes']}/{data['tests']}**",
            f"- Median wall time: **{data['median_wall_seconds']} seconds**",
            f"- Median generation speed: **{data['median_tokens_per_second']} tok/s**",
            f"- Reasoning leaks: **{data['reasoning_leak_count']}**",
            "",
        ])
    lines.extend([
        "## Interpretation",
        "",
        "Passing this suite proves that actual image bytes reached the local",
        "vision-language model and that the model could perform OCR, spatial",
        "reasoning, screenshot interpretation, detail description, and a simple",
        "hallucination-resistance check.",
        "",
        "The test does not automatically rewrite FOXAI profile badges. Results",
        "must be reviewed first.",
    ])
    (output / "findings.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )
    render_html(output, package_dir, receipt, results)


def final_zip(output: Path) -> Path:
    target = output.with_suffix(".zip")
    stage = target.with_suffix(".zip.tmp")
    for path in (target, stage):
        path.unlink(missing_ok=True)
    with zipfile.ZipFile(
        stage,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for file in sorted(output.rglob("*")):
            if file.is_file() and file.name != "RECOVERY_UPLOAD.zip":
                archive.write(
                    file,
                    arcname=f"{output.name}/{file.relative_to(output)}",
                )
    os.replace(stage, target)
    return target


def start_model(
    root: Path,
    package_dir: Path,
    output: Path,
    model_key: str,
    model: dict[str, Any],
    help_info: dict[str, Any],
    projector_list: list[dict[str, Any]],
) -> tuple[subprocess.Popen, Any, dict[str, Any]]:
    engine = root / "Engine/llama-server.exe"
    model_path = root / model["relative"]
    attempts = [None]
    if projector_list and help_info["supports_mmproj"]:
        attempts = [
            Path(item["path"])
            for item in projector_list[:MAX_PROJECTOR_ATTEMPTS]
        ]
        attempts.append(None)

    errors = []
    for attempt_index, projector in enumerate(attempts, 1):
        log_path = (
            output
            / "logs"
            / f"{model_key}_attempt_{attempt_index}.log"
        )
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_path.open(
            "w",
            encoding="utf-8",
            errors="replace",
        )
        command = [
            str(engine),
            "--model", str(model_path),
            "--host", HOST,
            "--port", str(PORT),
            "--ctx-size", CONTEXT,
            "--threads", THREADS,
        ]
        if projector is not None:
            command.extend(["--mmproj", str(projector)])

        creationflags = 0
        if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            creationflags = subprocess.CREATE_NO_WINDOW
        process = subprocess.Popen(
            command,
            cwd=str(root),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags,
        )
        health = wait_health(process)
        if health.get("ready"):
            return process, log_handle, {
                "command": command,
                "projector": (
                    {
                        "path": str(projector),
                        "sha256": sha256(projector),
                        "size_bytes": projector.stat().st_size,
                    }
                    if projector is not None
                    else None
                ),
                "health": health,
                "attempt": attempt_index,
                "log": str(log_path),
            }

        stop = stop_process(process)
        log_handle.close()
        errors.append({
            "attempt": attempt_index,
            "projector": str(projector) if projector else None,
            "health": health,
            "stop": stop,
            "log": str(log_path),
        })
        time.sleep(1)

    raise VisionError(
        "The vision model could not start with the discovered projector "
        f"configuration. Attempts: {errors}"
    )


def main() -> int:
    selection = (
        sys.argv[1].strip().lower()
        if len(sys.argv) > 1
        else "both"
    )
    if selection not in {"both", "fast", "quality"}:
        print("Selection must be both, fast, or quality.")
        return 2

    package_dir = Path(__file__).resolve().parent
    root = find_root(package_dir)
    created = datetime.now(timezone.utc)
    stamp = created.strftime("%Y%m%dT%H%M%SZ")
    output = package_dir / f"VIT_{stamp}"
    output.mkdir(parents=True, exist_ok=False)
    (output / "images").mkdir()
    shutil.copytree(
        package_dir / "images",
        output / "images",
        dirs_exist_ok=True,
    )

    receipt: dict[str, Any] = {
        "action": "qwen3vl_real_image_input_test",
        "created": created.isoformat(),
        "selection": selection,
        "state": "running",
        "verified": False,
        "live_files_modified": False,
        "apply_capability_present": False,
        "configuration_modified": False,
        "archive_modified": False,
        "security_logs_modified": False,
        "models": {},
        "projector_inventory": {},
        "checks": {},
        "failure": None,
    }
    write_json_atomic(output / "receipt.json", receipt)
    checkpoint_zip(output)

    before = protected_snapshot(root)
    results: list[dict[str, Any]] = []
    process = None
    log_handle = None

    try:
        baseline_checks = []
        for relative, expected in LIVE_HASHES.items():
            path = root / relative
            actual = sha256(path) if path.is_file() else None
            baseline_checks.append({
                "path": relative,
                "expected": expected,
                "actual": actual,
                "ok": actual == expected,
            })
        if not all(item["ok"] for item in baseline_checks):
            raise VisionError(
                "A locked live source, configuration, or engine baseline changed."
            )
        receipt["checks"]["locked_baselines"] = {
            "passed": True,
            "files": baseline_checks,
        }

        active = [
            {"port": port, "label": label}
            for port, label in CLOSED_PORTS.items()
            if port_open(port)
        ]
        if active:
            raise VisionError(
                "Close FOXAI and benchmark servers first: "
                + repr(active)
            )
        receipt["checks"]["ports_closed"] = {
            "passed": True,
            "ports": CLOSED_PORTS,
        }

        engine = root / "Engine/llama-server.exe"
        help_info = engine_help(engine)
        receipt["checks"]["engine_help"] = help_info

        selected_keys = (
            ["fast", "quality"]
            if selection == "both"
            else [selection]
        )

        for model_key in selected_keys:
            model = MODELS[model_key]
            model_path = root / model["relative"]
            if not model_path.is_file():
                raise VisionError(f"Model not found: {model_path}")
            size = model_path.stat().st_size
            if size != model["expected_size"]:
                raise VisionError(
                    f"{model['filename']} size changed: "
                    f"{size} != {model['expected_size']}"
                )

            print()
            print("=" * 72)
            print(model["profile"].upper())
            print("=" * 72)
            print("Hashing exact model identity...")
            model_hash = sha256(model_path)
            projectors = projector_candidates(root, model["filename"])
            receipt["projector_inventory"][model_key] = projectors
            receipt["models"][model_key] = {
                **model,
                "actual_size": size,
                "sha256": model_hash,
                "state": "starting",
            }
            write_json_atomic(output / "receipt.json", receipt)
            checkpoint_zip(output)

            process, log_handle, launch = start_model(
                root,
                package_dir,
                output,
                model_key,
                model,
                help_info,
                projectors,
            )
            receipt["models"][model_key]["launch"] = launch
            receipt["models"][model_key]["state"] = "ready"
            write_json_atomic(output / "receipt.json", receipt)
            checkpoint_zip(output)
            print(
                f"Ready in {launch['health']['seconds']} seconds; "
                f"projector={launch['projector']}"
            )

            for test_index, test in enumerate(TESTS, 1):
                print(
                    f"[{test_index}/{len(TESTS)}] "
                    f"{test['title']}"
                )
                result = request_vision(
                    test,
                    package_dir / test["image"],
                )
                result.update({
                    "profile_key": model_key,
                    "profile": model["profile"],
                    "model": model["filename"],
                    "model_sha256": model_hash,
                    "projector": launch["projector"],
                })
                results.append(result)

                response_dir = output / "responses" / model_key
                response_dir.mkdir(parents=True, exist_ok=True)
                (response_dir / f"{test_index:02d}_{test['id']}.txt").write_text(
                    result["content"],
                    encoding="utf-8",
                )
                write_json_atomic(
                    response_dir / f"{test_index:02d}_{test['id']}.json",
                    result,
                )
                write_json_atomic(output / "results.json", results)
                receipt["models"][model_key]["completed_tests"] = test_index
                write_json_atomic(output / "receipt.json", receipt)
                write_reports(output, package_dir, receipt, results)
                checkpoint_zip(output)

                print(
                    f"  status={result['status']} "
                    f"time={result['wall_seconds']}s "
                    f"pass={result['validation']['passed']}"
                )
                if not result["response_ok"]:
                    raise VisionError(
                        f"{model['profile']} failed {test['id']}: "
                        f"HTTP {result['status']} "
                        f"{result['raw_error_excerpt']}"
                    )

            stop = stop_process(process)
            process = None
            log_handle.close()
            log_handle = None
            if not stop.get("stopped"):
                raise VisionError(
                    f"{model['profile']} server did not stop."
                )
            if port_open(PORT):
                raise VisionError(
                    f"Port {PORT} remained open after stopping "
                    f"{model['profile']}."
                )
            receipt["models"][model_key]["state"] = "complete"
            receipt["models"][model_key]["stop"] = stop
            write_json_atomic(output / "receipt.json", receipt)
            checkpoint_zip(output)

        after = protected_snapshot(root)
        changes = snapshot_changes(before, after)
        if changes:
            raise VisionError(
                "Protected live state changed during the benchmark: "
                + repr(changes)
            )

        receipt.update({
            "state": "vision_test_complete",
            "verified": True,
            "live_files_modified": False,
            "configuration_modified": False,
            "archive_modified": False,
            "security_logs_modified": False,
        })
        receipt["checks"]["actual_image_payloads_sent"] = {
            "passed": True,
            "images": [
                {
                    "path": test["image"],
                    "sha256": sha256(package_dir / test["image"]),
                }
                for test in TESTS
            ],
        }
        receipt["checks"]["all_selected_models_completed"] = {
            "passed": True,
            "models": selected_keys,
        }
        receipt["checks"]["protected_state_unchanged"] = {
            "passed": True,
            "changes": changes,
        }

    except Exception as exc:
        stop = stop_process(process)
        process = None
        if log_handle is not None:
            log_handle.close()
            log_handle = None
        after = protected_snapshot(root)
        changes = snapshot_changes(before, after)
        receipt.update({
            "state": "stopped_fail_closed",
            "verified": not changes,
            "live_files_modified": bool(changes),
            "security_logs_modified": any(
                path.startswith("Logs/Security/")
                for path in changes
            ),
            "failure": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
            "emergency_stop": stop,
            "protected_changes": changes,
        })

    write_json_atomic(output / "receipt.json", receipt)
    write_reports(output, package_dir, receipt, results)
    checkpoint_zip(output)

    output_zip = None
    if receipt["state"] == "vision_test_complete":
        output_zip = final_zip(output)

    print()
    print("=" * 72)
    print("FOXAI REAL IMAGE INPUT TEST")
    print()
    print("State:", receipt["state"])
    print("Verified:", receipt["verified"])
    print("Live files modified:", receipt["live_files_modified"])
    print("Apply capability present: False")
    print("Completed responses:", len(results))
    print("Recovery ZIP:", output / "RECOVERY_UPLOAD.zip")
    if output_zip is not None:
        print("Final output ZIP:", output_zip)
    if receipt["failure"]:
        print("Failure:", receipt["failure"]["message"])
    print()
    input("Press Enter to close...")
    return 0 if receipt["state"] == "vision_test_complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
