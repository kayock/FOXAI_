from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import socket
import statistics
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOCKED_HASHES = {
    "core/foxai_web.py": "b94ac8e3b3a01b86cf34a509a64178e5efe047f38ac48e8ab5d08306ddf7ea48",
    "core/server.py": "9ee8871553113459ac4e234873de2cd3352aa5529ab58fab8d02ece0a53d0c07",
    "core/security_containment.py": "9a00ed8c1b2ef45a02fab2e4c2e552b3a6532e1609b6995a7985034ccf002a24",
    "core/engineer_agent.py": "f6346d4fbb8bda82535281e650042a0aeb290de26a000b1f85f0dd572ac28c19",
    "ui/main_window.py": "2e8f452d36f3a3c697b23ebdee2921f5fe01aa1b1c28460dfbc36921ca5ee0c3",
    "tests/test_boundary_watch.py": "b2eab44689c24802bf0168e8ea3bc94dd8c32a15f9365bb2cd5aea8f896cd382",
    "Config/FoxAI.ini": "677067e2b58416ba7d7bacc1dcfe40b9f43783e625dd305d0bbf82b6d3174d41",
    "Engine/llama-server.exe": "936cfb77f011911f879a5af715013eb12141115547c1f731114d8e9c20ebd89e",
}

MODEL_RELATIVE = "Models/Chat/PsyLLM-8B-Q5_K_M.gguf"
MODEL_EXPECTED_SIZE = 5851112672

HOST = "127.0.0.1"
PORT = 8099
CONTEXT = "8192"
THREADS = "12"
HEALTH_TIMEOUT = 300
REQUEST_TIMEOUT = 900
SEED_BASE = 260715
TEMPERATURE = 0.80
TOP_P = 0.92

REQUIRED_CLOSED_PORTS = {
    8765: "FOXAI WebUI",
    8080: "Chat Engine",
    8099: "Creative benchmark engine",
}

SYSTEM_PROMPT = (
    "You are being evaluated as a creative-writing model. Follow every visible "
    "structural and length constraint. Return only the finished creative work, "
    "without analysis, planning notes, hidden reasoning, or XML-style wrappers."
)

PROMPTS = [
    {
        "id": "warmup",
        "title": "Warmup",
        "modes": ["quick", "full"],
        "max_tokens": 48,
        "measured": False,
        "user": "Reply with exactly: creative benchmark ready",
        "validator": "warmup",
    },
    {
        "id": "microfiction",
        "title": "Atmospheric Microfiction",
        "modes": ["quick", "full"],
        "max_tokens": 720,
        "measured": True,
        "user": (
            "Write an original atmospheric science-fiction story of 320 to 430 "
            "words. It must take place at an abandoned weather station beneath "
            "an artificial moon. The protagonist repairs one harmless machine "
            "and discovers a tender, nonviolent mystery. Do not use headings. "
            "End with this exact sentence: By morning, the moon had learned his name."
        ),
        "validator": "microfiction",
    },
    {
        "id": "dialogue",
        "title": "Distinct Character Dialogue",
        "modes": ["quick", "full"],
        "max_tokens": 700,
        "measured": True,
        "user": (
            "Write exactly 12 alternating dialogue exchanges between Mara and "
            "Ivo. Mara is practical, dry, and hides affection behind criticism. "
            "Ivo is imaginative, anxious, and speaks in unusual comparisons. "
            "They are deciding whether to open a sealed room in their late "
            "mother's workshop. Format every exchange as either 'Mara:' or "
            "'Ivo:' and alternate speakers, beginning with Mara. Include exactly "
            "two separate bracketed stage-direction lines. Use no narration "
            "outside those two bracketed lines. Leave the decision unresolved."
        ),
        "validator": "dialogue",
    },
    {
        "id": "poetry",
        "title": "Constrained Poetry",
        "modes": ["quick", "full"],
        "max_tokens": 420,
        "measured": True,
        "user": (
            "Write a free-verse poem. The first nonblank line must be the exact "
            "title 'Small Machines of Mercy'. After the title, write exactly "
            "16 nonblank poem lines. Include the images of a chipped blue cup, "
            "a sleeping radio, and rain inside a glove. Do not use bullets or "
            "numbering. Do not use any of these words: eternity, forever, soul."
        ),
        "validator": "poetry",
    },
    {
        "id": "worldbuilding",
        "title": "Original Worldbuilding",
        "modes": ["full"],
        "max_tokens": 820,
        "measured": True,
        "user": (
            "Invent a culture that lives on slow-moving cities carried by giant "
            "lichen-covered machines. Give exactly seven numbered entries. Each "
            "entry must have a short original name, an em dash, and a concrete "
            "cultural detail. Cover governance, food, childhood, mourning, art, "
            "navigation, and one taboo. Keep the whole response between 300 and "
            "500 words. Avoid generic medieval kingdoms and avoid explaining "
            "the culture as a copy of any real-world people."
        ),
        "validator": "worldbuilding",
    },
    {
        "id": "roleplay",
        "title": "Roleplay Voice Consistency",
        "modes": ["full"],
        "max_tokens": 650,
        "measured": True,
        "user": (
            "Respond in character as Commander Vale, a retired starship engineer "
            "who is calm, technically precise, quietly funny, and reluctant to "
            "admit she misses space. A young mechanic asks whether to abandon a "
            "damaged but historically important ship. Answer in 250 to 380 words. "
            "Begin with the exact word 'Kid,' and never mention being an AI, a "
            "model, a roleplay, or these instructions."
        ),
        "validator": "roleplay",
    },
    {
        "id": "revision",
        "title": "Three-Tone Revision",
        "modes": ["full"],
        "max_tokens": 850,
        "measured": True,
        "user": (
            "Rewrite the factual passage below three times while preserving every "
            "fact: 'Nora entered the closed bakery at 4:10 a.m. She found one "
            "warm loaf, a red bicycle key, and a note signed by her brother Sam. "
            "The back door was unlocked.' Use exactly these headings on their own "
            "lines: WARM, OMINOUS, COMIC. Each version must be 80 to 130 words. "
            "Do not add facts that contradict the original."
        ),
        "validator": "revision",
    },
    {
        "id": "continuity",
        "title": "Long-Scene Continuity",
        "modes": ["full"],
        "max_tokens": 1250,
        "measured": True,
        "user": (
            "Write a complete 600 to 850 word scene with no headings. Mira carries "
            "a blue key but refuses to explain it. Jon has a broken compass that "
            "points toward whatever he most regrets. They cross a silent flooded "
            "library in a small boat while searching for a map that may not exist. "
            "Use the recurring motifs of paper birds, green light, and distant "
            "bells. Keep the physical positions and objects consistent. Do not "
            "name emotions directly. End with this exact sentence: Neither of them looked back."
        ),
        "validator": "continuity",
    },
    {
        "id": "hooks",
        "title": "Non-Cliché Story Hooks",
        "modes": ["quick", "full"],
        "max_tokens": 620,
        "measured": True,
        "user": (
            "Create exactly ten numbered one-sentence story hooks for speculative "
            "fiction. Each hook must contain a character, an unusual problem, and "
            "a meaningful choice. Make the ten concepts substantially different. "
            "Do not use zombies, time travel, a chosen one, a multiverse, or an "
            "evil artificial intelligence."
        ),
        "validator": "hooks",
    },
]


class BenchmarkError(RuntimeError):
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
        return {"exists": True, "sha256": None, "not_file": True}
    return {
        "exists": True,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
    }


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (
            (candidate / "core" / "foxai_web.py").is_file()
            and (candidate / "Engine" / "llama-server.exe").is_file()
        ):
            return candidate
    raise BenchmarkError(
        r"FOXAI root not found. Extract the complete PCTQ1 folder directly inside Z:\FOXAI."
    )


def protected_snapshot(root: Path) -> dict[str, Any]:
    result = {relative: file_state(root / relative) for relative in LOCKED_HASHES}
    security = root / "Logs" / "Security"
    if security.exists():
        for path in sorted(security.rglob("*")):
            if path.is_file():
                relative = str(path.relative_to(root)).replace("\\", "/")
                result[relative] = file_state(path)
    return result


def snapshot_changes(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return [
        key
        for key in sorted(set(before) | set(after))
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


def wait_for_health(process: subprocess.Popen) -> dict[str, Any]:
    started = time.perf_counter()
    deadline = started + HEALTH_TIMEOUT
    last = ""

    while time.perf_counter() < deadline:
        exit_code = process.poll()
        if exit_code is not None:
            return {
                "ready": False,
                "load_seconds": round(time.perf_counter() - started, 3),
                "failure": f"llama-server exited with code {exit_code}",
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
                    "load_seconds": round(time.perf_counter() - started, 3),
                    "health": parsed if parsed is not None else raw,
                }
        except Exception as exc:
            last = str(exc)
        time.sleep(0.5)

    return {
        "ready": False,
        "load_seconds": round(time.perf_counter() - started, 3),
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
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
            else:
                process.kill()
            process.wait(timeout=15)
        result.update({
            "stopped": process.poll() is not None,
            "exit_code": process.poll(),
        })
    except Exception as exc:
        result["error"] = str(exc)
    return result


def extract_message(parsed: Any) -> dict[str, str]:
    if not isinstance(parsed, dict):
        return {"content": "", "reasoning_content": "", "finish_reason": ""}
    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices:
        return {"content": "", "reasoning_content": "", "finish_reason": ""}
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message") if isinstance(first.get("message"), dict) else {}
    return {
        "content": (
            message.get("content")
            if isinstance(message.get("content"), str)
            else ""
        ),
        "reasoning_content": (
            message.get("reasoning_content")
            if isinstance(message.get("reasoning_content"), str)
            else ""
        ),
        "finish_reason": (
            first.get("finish_reason")
            if isinstance(first.get("finish_reason"), str)
            else ""
        ),
    }


def strip_content_wrapper(text: str) -> tuple[str, bool]:
    value = text.strip()
    lower = value.lower()
    if lower.startswith("<content>") and lower.endswith("</content>"):
        return value[len("<content>"):-len("</content>")].strip(), True
    return value, False


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text)


def word_count(text: str) -> int:
    return len(words(text))


def nonblank_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def ngram_repetition(text: str, size: int = 4) -> float:
    tokens = [token.lower() for token in words(text)]
    if len(tokens) < size * 2:
        return 0.0
    grams = [tuple(tokens[index:index + size]) for index in range(len(tokens) - size + 1)]
    counts = Counter(grams)
    repeated = sum(count - 1 for count in counts.values() if count > 1)
    return round(repeated / max(1, len(grams)), 4)


def duplicate_line_count(text: str) -> int:
    lines = [line.lower() for line in nonblank_lines(text)]
    counts = Counter(lines)
    return sum(count - 1 for count in counts.values() if count > 1)


def common_metrics(text: str) -> dict[str, Any]:
    token_list = [token.lower() for token in words(text)]
    unique_ratio = (
        round(len(set(token_list)) / len(token_list), 4)
        if token_list
        else 0.0
    )
    lower = text.lower()
    return {
        "word_count": len(token_list),
        "nonblank_line_count": len(nonblank_lines(text)),
        "unique_word_ratio": unique_ratio,
        "fourgram_repetition_ratio": ngram_repetition(text, 4),
        "duplicate_line_count": duplicate_line_count(text),
        "wrapper_like_markup_present": any(
            marker in lower
            for marker in ("<content>", "</content>", "<analysis>", "</analysis>")
        ),
        "model_meta_language_present": any(
            phrase in lower
            for phrase in (
                "as an ai",
                "as a language model",
                "i cannot roleplay",
                "here is the requested",
                "here's the requested",
                "analysis:",
                "reasoning:",
            )
        ),
    }


def numbered_entries(text: str) -> list[tuple[int, str]]:
    entries = []
    for line in nonblank_lines(text):
        match = re.match(r"^\s*(\d+)[.)]\s+(.+)$", line)
        if match:
            entries.append((int(match.group(1)), match.group(2).strip()))
    return entries


def validation_result(checks: dict[str, bool], notes: list[str] | None = None) -> dict[str, Any]:
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "failed_checks": [name for name, value in checks.items() if not value],
        "notes": notes or [],
    }


def validate_warmup(text: str) -> dict[str, Any]:
    return validation_result({
        "exact_text": text.strip() == "creative benchmark ready",
    })


def validate_microfiction(text: str) -> dict[str, Any]:
    count = word_count(text)
    lower = text.lower()
    return validation_result({
        "word_range_320_430": 320 <= count <= 430,
        "no_heading": not any(
            line.endswith(":") or line.startswith("#")
            for line in nonblank_lines(text)[:2]
        ),
        "weather_station_present": "weather station" in lower,
        "artificial_moon_present": "artificial moon" in lower,
        "exact_ending": text.rstrip().endswith(
            "By morning, the moon had learned his name."
        ),
    })


def validate_dialogue(text: str) -> dict[str, Any]:
    lines = nonblank_lines(text)
    dialogue_lines = [
        line for line in lines
        if line.startswith("Mara:") or line.startswith("Ivo:")
    ]
    stage_lines = [
        line for line in lines
        if line.startswith("[") and line.endswith("]")
    ]
    allowed = len(dialogue_lines) + len(stage_lines) == len(lines)
    expected_speakers = ["Mara" if index % 2 == 0 else "Ivo" for index in range(12)]
    actual_speakers = [
        line.split(":", 1)[0]
        for line in dialogue_lines
    ]
    return validation_result({
        "exactly_12_dialogue_exchanges": len(dialogue_lines) == 12,
        "alternates_mara_ivo": actual_speakers == expected_speakers,
        "exactly_two_stage_directions": len(stage_lines) == 2,
        "no_other_narration": allowed,
        "decision_not_explicitly_resolved": not any(
            phrase in text.lower()
            for phrase in (
                "we'll open it",
                "we will open it",
                "we won't open it",
                "we will not open it",
                "decision is made",
            )
        ),
    })


def validate_poetry(text: str) -> dict[str, Any]:
    lines = nonblank_lines(text)
    lower_words = {token.lower() for token in words(text)}
    return validation_result({
        "exact_title": bool(lines) and lines[0] == "Small Machines of Mercy",
        "exactly_16_poem_lines": len(lines) == 17,
        "chipped_blue_cup": "chipped blue cup" in text.lower(),
        "sleeping_radio": "sleeping radio" in text.lower(),
        "rain_inside_a_glove": "rain inside a glove" in text.lower(),
        "forbidden_words_absent": not bool(
            {"eternity", "forever", "soul"} & lower_words
        ),
        "no_numbering_or_bullets": not any(
            re.match(r"^\s*(?:[-*]|\d+[.)])\s+", line)
            for line in lines[1:]
        ),
    })


def validate_worldbuilding(text: str) -> dict[str, Any]:
    entries = numbered_entries(text)
    count = word_count(text)
    entry_numbers = [number for number, _ in entries]
    entry_text = [body for _, body in entries]
    return validation_result({
        "exactly_seven_numbered_entries": len(entries) == 7,
        "numbers_1_through_7": entry_numbers == list(range(1, 8)),
        "every_entry_has_em_dash": all("—" in body for body in entry_text),
        "word_range_300_500": 300 <= count <= 500,
    })


def validate_roleplay(text: str) -> dict[str, Any]:
    count = word_count(text)
    lower = text.lower()
    return validation_result({
        "begins_with_kid": text.lstrip().startswith("Kid,"),
        "word_range_250_380": 250 <= count <= 380,
        "no_meta_roleplay_language": not any(
            phrase in lower
            for phrase in (
                "as an ai",
                "language model",
                "roleplay",
                "these instructions",
                "the prompt",
            )
        ),
    })


def split_heading_sections(text: str, headings: list[str]) -> dict[str, str]:
    lines = text.splitlines()
    positions = {}
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped in headings and stripped not in positions:
            positions[stripped] = index

    result = {}
    if any(heading not in positions for heading in headings):
        return result

    for index, heading in enumerate(headings):
        start = positions[heading] + 1
        end = positions[headings[index + 1]] if index + 1 < len(headings) else len(lines)
        result[heading] = "\n".join(lines[start:end]).strip()
    return result


def validate_revision(text: str) -> dict[str, Any]:
    headings = ["WARM", "OMINOUS", "COMIC"]
    sections = split_heading_sections(text, headings)
    required_facts = (
        "nora",
        "4:10",
        "warm loaf",
        "red bicycle key",
        "sam",
        "back door",
        "unlocked",
    )
    each_fact_preserved = bool(sections) and all(
        all(fact in body.lower() for fact in required_facts)
        for body in sections.values()
    )
    each_length = bool(sections) and all(
        80 <= word_count(body) <= 130
        for body in sections.values()
    )
    heading_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() in headings
    ]
    return validation_result({
        "exact_heading_order": heading_lines == headings,
        "three_sections_found": set(sections) == set(headings),
        "each_section_80_130_words": each_length,
        "all_required_facts_preserved": each_fact_preserved,
    })


def validate_continuity(text: str) -> dict[str, Any]:
    count = word_count(text)
    lower = text.lower()
    return validation_result({
        "word_range_600_850": 600 <= count <= 850,
        "mira_present": "mira" in lower,
        "jon_present": "jon" in lower,
        "blue_key_present": "blue key" in lower,
        "broken_compass_present": "broken compass" in lower,
        "paper_birds_present": "paper birds" in lower,
        "green_light_present": "green light" in lower,
        "distant_bells_present": "distant bells" in lower,
        "exact_ending": text.rstrip().endswith(
            "Neither of them looked back."
        ),
    })


def sentence_count(text: str) -> int:
    return len(re.findall(r"[.!?](?:[\"')\]]*)\s*(?=$|\n)", text.strip()))


def validate_hooks(text: str) -> dict[str, Any]:
    entries = numbered_entries(text)
    forbidden = (
        "zombie",
        "time travel",
        "chosen one",
        "multiverse",
        "evil artificial intelligence",
        "evil ai",
    )
    each_one_sentence = bool(entries) and all(
        sentence_count(body) == 1
        for _, body in entries
    )
    return validation_result({
        "exactly_ten_numbered_hooks": len(entries) == 10,
        "numbers_1_through_10": [number for number, _ in entries] == list(range(1, 11)),
        "each_hook_one_sentence": each_one_sentence,
        "forbidden_tropes_absent": not any(
            phrase in text.lower()
            for phrase in forbidden
        ),
    })


VALIDATORS = {
    "warmup": validate_warmup,
    "microfiction": validate_microfiction,
    "dialogue": validate_dialogue,
    "poetry": validate_poetry,
    "worldbuilding": validate_worldbuilding,
    "roleplay": validate_roleplay,
    "revision": validate_revision,
    "continuity": validate_continuity,
    "hooks": validate_hooks,
}


def tokens_per_second(result: dict[str, Any]) -> float | None:
    timings = result.get("timings") or {}
    value = timings.get("predicted_per_second")
    if isinstance(value, (int, float)) and value > 0:
        return round(float(value), 3)

    usage = result.get("usage") or {}
    completion_tokens = usage.get("completion_tokens")
    wall = result.get("wall_seconds")
    if (
        isinstance(completion_tokens, (int, float))
        and completion_tokens > 0
        and isinstance(wall, (int, float))
        and wall > 0
    ):
        return round(float(completion_tokens) / float(wall), 3)
    return None


def run_prompt(prompt: dict[str, Any], index: int) -> dict[str, Any]:
    payload = {
        "model": "local-model",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt["user"]},
        ],
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "seed": SEED_BASE + index,
        "max_tokens": prompt["max_tokens"],
        "stream": False,
    }

    started = time.perf_counter()
    try:
        status, parsed, raw = request_json(
            "POST",
            f"http://{HOST}:{PORT}/v1/chat/completions",
            payload,
            timeout=REQUEST_TIMEOUT,
        )
        elapsed = round(time.perf_counter() - started, 3)
        message = extract_message(parsed)
        normalized, wrapper_stripped = strip_content_wrapper(message["content"])
        usage = parsed.get("usage", {}) if isinstance(parsed, dict) else {}
        timings = parsed.get("timings", {}) if isinstance(parsed, dict) else {}
        metrics = common_metrics(normalized)
        validator = VALIDATORS[prompt["validator"]]
        validation = validator(normalized)

        result = {
            "id": prompt["id"],
            "title": prompt["title"],
            "measured": prompt["measured"],
            "status": status,
            "wall_seconds": elapsed,
            "content": message["content"],
            "normalized_content": normalized,
            "reasoning_content": message["reasoning_content"],
            "reasoning_character_count": len(message["reasoning_content"]),
            "finish_reason": message["finish_reason"],
            "content_wrapper_stripped": wrapper_stripped,
            "usage": usage if isinstance(usage, dict) else {},
            "timings": timings if isinstance(timings, dict) else {},
            "metrics": metrics,
            "validation": validation,
            "request": payload,
            "raw_response": parsed if isinstance(parsed, dict) else raw,
            "error": None,
        }
        result["tokens_per_second"] = tokens_per_second({
            **result,
            "usage": result["usage"],
            "timings": result["timings"],
        })
        result["response_ok"] = status == 200 and bool(normalized)
        result["reasoning_leak_free"] = (
            not message["reasoning_content"]
            and not metrics["wrapper_like_markup_present"]
        )
        result["objective_pass"] = (
            result["response_ok"]
            and validation["passed"]
            and result["reasoning_leak_free"]
            and not metrics["model_meta_language_present"]
            and metrics["fourgram_repetition_ratio"] <= 0.08
            and metrics["duplicate_line_count"] <= 1
        )
        return result

    except Exception as exc:
        return {
            "id": prompt["id"],
            "title": prompt["title"],
            "measured": prompt["measured"],
            "status": None,
            "wall_seconds": round(time.perf_counter() - started, 3),
            "content": "",
            "normalized_content": "",
            "reasoning_content": "",
            "reasoning_character_count": 0,
            "finish_reason": "",
            "content_wrapper_stripped": False,
            "usage": {},
            "timings": {},
            "metrics": common_metrics(""),
            "validation": validation_result({"request_completed": False}),
            "request": payload,
            "raw_response": "",
            "error": f"{type(exc).__name__}: {exc}",
            "tokens_per_second": None,
            "response_ok": False,
            "reasoning_leak_free": True,
            "objective_pass": False,
        }


def write_prompt_registry(output: Path, selected: list[dict[str, Any]]) -> None:
    registry = [
        {
            "id": prompt["id"],
            "title": prompt["title"],
            "max_tokens": prompt["max_tokens"],
            "measured": prompt["measured"],
            "user": prompt["user"],
            "validator": prompt["validator"],
        }
        for prompt in selected
    ]
    (output / "prompts.json").write_text(
        json.dumps(registry, indent=2),
        encoding="utf-8",
    )


def write_responses(output: Path, results: list[dict[str, Any]]) -> None:
    response_dir = output / "responses"
    response_dir.mkdir(parents=True, exist_ok=True)

    markdown = [
        "# PsyLLM Creative Text Quality Responses",
        "",
        "These are raw creative outputs for human quality review.",
        "",
    ]

    for index, result in enumerate(results, start=1):
        safe_id = result["id"]
        (response_dir / f"{index:02d}_{safe_id}.txt").write_text(
            result["normalized_content"],
            encoding="utf-8",
        )
        (response_dir / f"{index:02d}_{safe_id}.json").write_text(
            json.dumps(result, indent=2),
            encoding="utf-8",
        )

        markdown.extend([
            f"## {index}. {result['title']} (`{safe_id}`)",
            "",
            f"- Wall time: {result['wall_seconds']} seconds",
            f"- Tokens/second: {result['tokens_per_second']}",
            f"- Words: {result['metrics']['word_count']}",
            f"- Objective compliance: **{result['objective_pass']}**",
            f"- Failed checks: {result['validation']['failed_checks']}",
            "",
            "```text",
            result["normalized_content"],
            "```",
            "",
        ])

    (output / "responses.md").write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )


def write_csv(output: Path, results: list[dict[str, Any]]) -> None:
    path = output / "summary.csv"
    fields = [
        "id",
        "title",
        "status",
        "wall_seconds",
        "tokens_per_second",
        "word_count",
        "finish_reason",
        "objective_pass",
        "failed_checks",
        "reasoning_character_count",
        "content_wrapper_stripped",
        "unique_word_ratio",
        "fourgram_repetition_ratio",
        "duplicate_line_count",
        "error",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in results:
            writer.writerow({
                "id": result["id"],
                "title": result["title"],
                "status": result["status"],
                "wall_seconds": result["wall_seconds"],
                "tokens_per_second": result["tokens_per_second"],
                "word_count": result["metrics"]["word_count"],
                "finish_reason": result["finish_reason"],
                "objective_pass": result["objective_pass"],
                "failed_checks": "; ".join(
                    result["validation"]["failed_checks"]
                ),
                "reasoning_character_count":
                    result["reasoning_character_count"],
                "content_wrapper_stripped":
                    result["content_wrapper_stripped"],
                "unique_word_ratio":
                    result["metrics"]["unique_word_ratio"],
                "fourgram_repetition_ratio":
                    result["metrics"]["fourgram_repetition_ratio"],
                "duplicate_line_count":
                    result["metrics"]["duplicate_line_count"],
                "error": result["error"],
            })


def write_review_sheet(output: Path, results: list[dict[str, Any]]) -> None:
    measured = [result for result in results if result["measured"]]
    lines = [
        "# Human Creative-Quality Review Sheet",
        "",
        "Objective compliance alone cannot prove creative quality. Review each",
        "response from 1 (poor) to 5 (excellent) in the following categories:",
        "",
        "- Originality",
        "- Voice and style",
        "- Coherence and continuity",
        "- Emotional or imaginative impact",
        "- Natural language quality",
        "- Instruction fit beyond mechanical formatting",
        "",
        "Do not reward mere length. Penalize clichés, generic phrasing, repetition,",
        "flat character voices, accidental contradictions, and unfinished endings.",
        "",
    ]

    for result in measured:
        lines.extend([
            f"## {result['title']} (`{result['id']}`)",
            "",
            f"- Objective pass: **{result['objective_pass']}**",
            f"- Failed mechanical checks: {result['validation']['failed_checks']}",
            "- Originality: ___ / 5",
            "- Voice and style: ___ / 5",
            "- Coherence and continuity: ___ / 5",
            "- Emotional/imaginative impact: ___ / 5",
            "- Natural language: ___ / 5",
            "- Instruction fit: ___ / 5",
            "- Notes:",
            "",
        ])

    lines.extend([
        "## Final evidence-based label",
        "",
        "Choose only after reviewing the actual writing:",
        "",
        "- CREATIVE QUALITY SUPPORTED",
        "- GOOD FOR BRAINSTORMING — LONG-FORM PENDING",
        "- QUALITY CHECK PENDING",
        "",
    ])
    (output / "human_review.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def write_findings(
    output: Path,
    mode: str,
    model_hash: str,
    load: dict[str, Any],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    measured = [result for result in results if result["measured"]]
    completed = [result for result in measured if result["response_ok"]]
    objective_passed = [
        result for result in measured if result["objective_pass"]
    ]
    walls = [result["wall_seconds"] for result in completed]
    tps_values = [
        result["tokens_per_second"]
        for result in completed
        if result["tokens_per_second"] is not None
    ]

    summary = {
        "mode": mode,
        "model_sha256": model_hash,
        "load_seconds": load.get("load_seconds"),
        "measured_prompt_count": len(measured),
        "completed_prompt_count": len(completed),
        "objective_pass_count": len(objective_passed),
        "objective_pass_rate": (
            round(len(objective_passed) / len(measured), 4)
            if measured
            else 0.0
        ),
        "total_generation_seconds": round(sum(walls), 3),
        "median_wall_seconds": (
            round(statistics.median(walls), 3) if walls else None
        ),
        "median_tokens_per_second": (
            round(statistics.median(tps_values), 3)
            if tps_values
            else None
        ),
        "wrapper_leak_count": sum(
            1 for result in measured
            if result["content_wrapper_stripped"]
            or result["metrics"]["wrapper_like_markup_present"]
        ),
        "reasoning_leak_count": sum(
            1 for result in measured
            if result["reasoning_character_count"] > 0
        ),
        "meta_language_count": sum(
            1 for result in measured
            if result["metrics"]["model_meta_language_present"]
        ),
        "truncated_or_length_finish_count": sum(
            1 for result in measured
            if result["finish_reason"].lower() in {"length", "max_tokens"}
        ),
        "human_quality_review_required": True,
        "automatic_badge_upgrade_allowed": False,
    }

    lines = [
        "# PsyLLM Creative Text Quality Benchmark",
        "",
        f"- Mode: **{mode.upper()}**",
        "- Model: **PsyLLM-8B-Q5_K_M.gguf**",
        f"- Model SHA-256: `{model_hash}`",
        "- Runtime: **reasoning off; reasoning budget 0**",
        f"- Load time: **{summary['load_seconds']} seconds**",
        f"- Measured prompts: **{summary['measured_prompt_count']}**",
        f"- Completed prompts: **{summary['completed_prompt_count']}**",
        f"- Objective compliance passes: **{summary['objective_pass_count']}**",
        f"- Objective compliance rate: **{summary['objective_pass_rate']:.1%}**",
        f"- Median generation speed: **{summary['median_tokens_per_second']} tok/s**",
        f"- Wrapper leaks: **{summary['wrapper_leak_count']}**",
        f"- Reasoning leaks: **{summary['reasoning_leak_count']}**",
        f"- Meta-language responses: **{summary['meta_language_count']}**",
        f"- Truncated/length finishes: **{summary['truncated_or_length_finish_count']}**",
        "",
        "## Important interpretation boundary",
        "",
        "This benchmark can prove stability, structural instruction-following,",
        "runtime behavior, leakage absence, and obvious repetition problems.",
        "It cannot objectively decide whether prose is moving, original, funny,",
        "beautiful, or genuinely characterful.",
        "",
        "**No profile badge is upgraded automatically.** Review `responses.md` and",
        "`human_review.md`, then upload the output ZIP for the final assessment.",
        "",
        "## Per-task objective results",
        "",
    ]

    for result in measured:
        lines.extend([
            f"### {result['title']}",
            "",
            f"- Completed: **{result['response_ok']}**",
            f"- Objective pass: **{result['objective_pass']}**",
            f"- Words: **{result['metrics']['word_count']}**",
            f"- Time: **{result['wall_seconds']} seconds**",
            f"- Speed: **{result['tokens_per_second']} tok/s**",
            f"- Failed checks: `{result['validation']['failed_checks']}`",
            "",
        ])

    (output / "findings.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return summary


def zip_output(output: Path) -> Path:
    target = output.with_suffix(".zip")
    target.unlink(missing_ok=True)
    with zipfile.ZipFile(
        target,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for file in sorted(output.rglob("*")):
            if file.is_file():
                archive.write(
                    file,
                    arcname=f"{output.name}/{file.relative_to(output)}",
                )
    return target


def main() -> int:
    mode = (
        sys.argv[1].strip().lower()
        if len(sys.argv) > 1
        else "full"
    )
    if mode not in {"quick", "full"}:
        print("Mode must be quick or full.")
        return 2

    package_dir = Path(__file__).resolve().parent
    root = find_root(package_dir)
    created = datetime.now(timezone.utc)
    stamp = created.strftime("%Y%m%dT%H%M%SZ")
    output = package_dir / f"PCTQ_{stamp}"
    output.mkdir(parents=True, exist_ok=False)

    receipt: dict[str, Any] = {
        "action": "psyllm_creative_text_quality_isolated_benchmark",
        "created": created.isoformat(),
        "root": str(root),
        "mode": mode,
        "state": "running",
        "verified": False,
        "read_only_live_sources": True,
        "candidate_created": False,
        "apply_capability_present": False,
        "live_files_modified": False,
        "configuration_modified": False,
        "default_model_changed": False,
        "archive_modified": False,
        "security_logs_modified": False,
        "engine_started": False,
        "model_loaded": False,
        "benchmark_port": PORT,
        "failure": None,
        "checks": [],
    }

    before = protected_snapshot(root)
    process = None
    log_handle = None

    try:
        baseline_checks = []
        for relative, expected in LOCKED_HASHES.items():
            path = root / relative
            actual = sha256(path) if path.is_file() else None
            baseline_checks.append({
                "path": relative,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "ok": actual == expected,
            })
        if not all(check["ok"] for check in baseline_checks):
            raise BenchmarkError(
                "A locked source, configuration, engine, or security baseline changed."
            )

        active_ports = [
            {"port": port, "label": label}
            for port, label in REQUIRED_CLOSED_PORTS.items()
            if port_open(port)
        ]
        if active_ports:
            raise BenchmarkError(
                "Close FOXAI WebUI, Chat Engine, and benchmark servers first: "
                + repr(active_ports)
            )

        engine = root / "Engine" / "llama-server.exe"
        model = root / MODEL_RELATIVE
        if not model.is_file():
            raise BenchmarkError(f"Model not found: {model}")
        actual_size = model.stat().st_size
        if actual_size != MODEL_EXPECTED_SIZE:
            raise BenchmarkError(
                f"Model size changed: {actual_size} != {MODEL_EXPECTED_SIZE}"
            )

        print()
        print("=" * 72)
        print("PSYLLM CREATIVE TEXT QUALITY BENCHMARK")
        print(f"MODE: {mode.upper()}")
        print("=" * 72)
        print()
        print("Hashing the exact model file for the receipt...")
        model_hash = sha256(model)

        selected = [
            prompt for prompt in PROMPTS
            if mode in prompt["modes"]
        ]
        write_prompt_registry(output, selected)

        command = [
            str(engine),
            "--model", str(model),
            "--host", HOST,
            "--port", str(PORT),
            "--ctx-size", CONTEXT,
            "--threads", THREADS,
            "--reasoning", "off",
            "--reasoning-budget", "0",
        ]

        log_path = output / "llama_server.log"
        log_handle = log_path.open(
            "w",
            encoding="utf-8",
            errors="replace",
        )
        creationflags = 0
        if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            creationflags = subprocess.CREATE_NO_WINDOW

        print("Starting isolated PsyLLM on port", PORT)
        process = subprocess.Popen(
            command,
            cwd=str(root),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags,
        )
        receipt["engine_started"] = True

        load = wait_for_health(process)
        if not load.get("ready"):
            raise BenchmarkError(
                load.get("failure") or "llama-server did not become ready"
            )
        receipt["model_loaded"] = True
        print(f"Ready in {load['load_seconds']} seconds.")

        results = []
        for index, prompt in enumerate(selected):
            print()
            print(f"[{index + 1}/{len(selected)}] {prompt['title']}")
            result = run_prompt(prompt, index)
            results.append(result)
            print(
                f"  status={result['status']} "
                f"time={result['wall_seconds']}s "
                f"words={result['metrics']['word_count']} "
                f"objective_pass={result['objective_pass']}"
            )
            if not result["response_ok"]:
                raise BenchmarkError(
                    f"{prompt['id']} did not return a usable response: "
                    f"{result['error'] or result['status']}"
                )

        write_responses(output, results)
        write_csv(output, results)
        write_review_sheet(output, results)
        summary = write_findings(
            output,
            mode,
            model_hash,
            load,
            results,
        )

        (output / "results.json").write_text(
            json.dumps(results, indent=2),
            encoding="utf-8",
        )

        stop = stop_process(process)
        process = None
        if not stop.get("stopped"):
            raise BenchmarkError("Benchmark server did not stop cleanly.")

        if port_open(PORT):
            raise BenchmarkError(
                f"Benchmark port {PORT} remained open after shutdown."
            )

        after = protected_snapshot(root)
        live_changes = snapshot_changes(before, after)
        if live_changes:
            raise BenchmarkError(
                "Protected live state changed during the benchmark: "
                + repr(live_changes)
            )

        receipt.update({
            "state": "benchmark_complete",
            "verified": True,
            "live_files_modified": False,
            "configuration_modified": False,
            "default_model_changed": False,
            "archive_modified": False,
            "security_logs_modified": False,
            "engine_started": True,
            "model_loaded": True,
            "model": {
                "relative_path": MODEL_RELATIVE,
                "size_bytes": actual_size,
                "sha256": model_hash,
            },
            "runtime": {
                "host": HOST,
                "port": PORT,
                "context": CONTEXT,
                "threads": THREADS,
                "reasoning_mode": "off",
                "reasoning_budget": 0,
                "temperature": TEMPERATURE,
                "top_p": TOP_P,
                "seed_base": SEED_BASE,
            },
            "summary": summary,
            "stop": stop,
            "checks": [
                {
                    "id": "locked_baselines_match",
                    "ok": True,
                    "detail": baseline_checks,
                },
                {
                    "id": "required_ports_closed_before_start",
                    "ok": True,
                    "detail": REQUIRED_CLOSED_PORTS,
                },
                {
                    "id": "exact_model_identity_recorded",
                    "ok": True,
                    "detail": {
                        "size_bytes": actual_size,
                        "sha256": model_hash,
                    },
                },
                {
                    "id": "reasoning_disabled_runtime",
                    "ok": True,
                    "detail": {
                        "reasoning_mode": "off",
                        "reasoning_budget": 0,
                    },
                },
                {
                    "id": "all_selected_prompts_completed",
                    "ok": True,
                    "detail": [result["id"] for result in results],
                },
                {
                    "id": "human_quality_review_required",
                    "ok": True,
                    "detail": {
                        "automatic_badge_upgrade_allowed": False,
                    },
                },
                {
                    "id": "benchmark_server_stopped_and_port_released",
                    "ok": True,
                    "detail": stop,
                },
                {
                    "id": "live_sources_configs_archives_and_security_logs_unchanged",
                    "ok": True,
                    "detail": live_changes,
                },
            ],
            "live_snapshot_before": before,
            "live_snapshot_after": after,
        })

    except Exception as exc:
        stop = stop_process(process)
        process = None
        after = protected_snapshot(root)
        live_changes = snapshot_changes(before, after)
        receipt.update({
            "state": "stopped_fail_closed",
            "verified": not live_changes,
            "live_files_modified": bool(live_changes),
            "security_logs_modified": any(
                path.startswith("Logs/Security/")
                for path in live_changes
            ),
            "failure": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
            "stop": stop,
            "live_snapshot_before": before,
            "live_snapshot_after": after,
        })

    finally:
        if log_handle is not None:
            log_handle.close()

    receipt_path = output / "receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, indent=2),
        encoding="utf-8",
    )

    output_zip = zip_output(output)

    print()
    print("=" * 72)
    print("PSYLLM CREATIVE TEXT QUALITY BENCHMARK")
    print()
    print("State:", receipt["state"])
    print("Verified:", receipt["verified"])
    print("Mode:", mode)
    print("Live files modified:", receipt["live_files_modified"])
    print("Apply capability present: False")
    print("Output ZIP:", output_zip)
    if receipt.get("summary"):
        print(
            "Objective compliance:",
            f"{receipt['summary']['objective_pass_count']}/"
            f"{receipt['summary']['measured_prompt_count']}",
        )
        print(
            "Median speed:",
            receipt["summary"]["median_tokens_per_second"],
            "tok/s",
        )
    if receipt["failure"]:
        print("Failure:", receipt["failure"]["message"])
    print()
    input("Press Enter to close...")

    return 0 if receipt["state"] == "benchmark_complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
