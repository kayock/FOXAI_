from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import random
import re
import secrets
import shutil
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from typing import Any


APP_VERSION = "1.0.0"
HOST = "127.0.0.1"
PORT = 8776
CHAT_HEALTH = "http://127.0.0.1:8080/health"
CHAT_API = "http://127.0.0.1:8080/v1/chat/completions"

BONUS_THRESHOLDS = [
    (2, -10),
    (3, -8),
    (4, -7),
    (5, -6),
    (6, -5),
    (7, -3),
    (8, -1),
    (10, 0),
    (12, 1),
    (13, 2),
    (14, 3),
    (15, 4),
    (16, 5),
    (17, 6),
    (18, 7),
    (19, 8),
    (20, 9),
    (25, 10),
    (30, 11),
    (35, 12),
    (40, 13),
    (45, 14),
]

ROLE_TEMPLATES = {
    "E-Branch Investigator": {
        "summary": "A trained field investigator with no confirmed psychic talent.",
        "attributes": {
            "Agility": 8,
            "Dexterity": 9,
            "Endurance": 8,
            "Strength": 8,
            "Intellect": 11,
            "Mind": 9,
            "Confidence": 10,
            "Charisma": 9,
        },
        "skills": {
            "Deduction": 13,
            "Espionage": 12,
            "Perception": 12,
            "Fire Combat": 11,
            "Willpower": 11,
        },
        "talent": "None confirmed",
        "equipment": "Agency credentials, concealed pistol, radio, notebook, field kit",
    },
    "Deadspeaker": {
        "summary": "An E-Branch psychic able to communicate with the dead.",
        "attributes": {
            "Agility": 8,
            "Dexterity": 8,
            "Endurance": 7,
            "Strength": 7,
            "Intellect": 10,
            "Mind": 12,
            "Confidence": 11,
            "Charisma": 8,
        },
        "skills": {
            "ESP: Deadspeak": 14,
            "Research": 12,
            "Interrogation": 12,
            "Willpower": 12,
            "Perception": 11,
        },
        "talent": "Deadspeak",
        "equipment": "Agency credentials, recorder, radio, protective charms, pistol",
    },
    "Telepath": {
        "summary": "A mind-reader trained for covert interrogation and psychic defense.",
        "attributes": {
            "Agility": 8,
            "Dexterity": 8,
            "Endurance": 8,
            "Strength": 7,
            "Intellect": 10,
            "Mind": 12,
            "Confidence": 11,
            "Charisma": 9,
        },
        "skills": {
            "ESP: Telepathy": 15,
            "Psychology": 12,
            "Interrogation": 12,
            "Willpower": 13,
            "Espionage": 11,
        },
        "talent": "Telepathy",
        "equipment": "Agency credentials, radio, recorder, concealed pistol",
    },
    "Empath": {
        "summary": "A psychic who senses and influences emotional states.",
        "attributes": {
            "Agility": 8,
            "Dexterity": 8,
            "Endurance": 7,
            "Strength": 7,
            "Intellect": 10,
            "Mind": 13,
            "Confidence": 7,
            "Charisma": 10,
        },
        "skills": {
            "ESP: Empathy": 16,
            "Charm": 12,
            "Con": 9,
            "Computer Ops": 12,
            "Willpower": 10,
        },
        "talent": "Empathy",
        "equipment": "Agency credentials, compact pistol, radio, field recorder",
    },
    "Cryokinetic": {
        "summary": "A psychic able to lower temperatures and freeze targets.",
        "attributes": {
            "Agility": 8,
            "Dexterity": 8,
            "Endurance": 7,
            "Strength": 10,
            "Intellect": 12,
            "Mind": 9,
            "Confidence": 7,
            "Charisma": 7,
        },
        "skills": {
            "ESP: Cryokinetic": 15,
            "Computer Ops": 15,
            "Mechanic": 13,
            "Dodge": 10,
            "Resist Shock": 11,
        },
        "talent": "Cryokinesis",
        "equipment": "Agency credentials, revolver, notebook computer, recorder",
    },
    "Elemental": {
        "summary": "A ritual-minded psychic whose gift manipulates weather or elements.",
        "attributes": {
            "Agility": 7,
            "Dexterity": 8,
            "Endurance": 7,
            "Strength": 7,
            "Intellect": 11,
            "Mind": 11,
            "Confidence": 10,
            "Charisma": 7,
        },
        "skills": {
            "ESP: Elemental": 13,
            "Demolitions": 14,
            "Espionage": 14,
            "Perception": 13,
            "Tracking": 13,
        },
        "talent": "Elemental control",
        "equipment": "Agency credentials, revolver, fake identification, gas scanner",
    },
    "Exorcist": {
        "summary": "A psychic operative trained to confront possession and hostile entities.",
        "attributes": {
            "Agility": 8,
            "Dexterity": 8,
            "Endurance": 7,
            "Strength": 8,
            "Intellect": 9,
            "Mind": 7,
            "Confidence": 12,
            "Charisma": 9,
        },
        "skills": {
            "ESP: Exorcist": 14,
            "Faith: E-Branch": 13,
            "Interrogation": 13,
            "Deduction": 12,
            "Willpower": 10,
        },
        "talent": "Exorcism",
        "equipment": "Agency credentials, ritual kit, radio, concealed pistol",
    },
}

# Original proxy deck. It is not a transcription of the copyrighted MasterDeck.
STORY_DECK = [
    {"category":"edge","title":"Second Wind","effect":"The player may ignore one immediate fatigue, shock, or hesitation consequence.","tags":["resist","escape","run","survive"]},
    {"category":"edge","title":"Clear Signal","effect":"A jammed message, psychic impression, or damaged recording yields one usable fragment.","tags":["radio","message","psychic","recording","clue"]},
    {"category":"edge","title":"Hidden Exit","effect":"A plausible escape route or overlooked access point becomes available.","tags":["escape","trapped","door","room","building"]},
    {"category":"edge","title":"Cold Read","effect":"The player notices one revealing emotional or behavioral detail.","tags":["talk","question","interrogate","suspect","npc"]},
    {"category":"edge","title":"Steady Hands","effect":"Reduce one situational penalty on a careful physical action.","tags":["shoot","aim","repair","disarm","drive"]},
    {"category":"edge","title":"Old Contact","effect":"A believable contact can provide limited information or a small favor.","tags":["contact","call","information","agency"]},
    {"category":"edge","title":"Moment of Clarity","effect":"The player may ask Agent Fox to restate the most important known clue plainly.","tags":["clue","think","remember","investigate"]},
    {"category":"edge","title":"Protective Instinct","effect":"The player can shield an ally from one immediate narrative consequence.","tags":["ally","protect","save","team"]},
    {"category":"edge","title":"Familiar Pattern","effect":"A repeated symbol, tactic, or psychic signature is recognized.","tags":["pattern","symbol","psychic","evidence"]},
    {"category":"edge","title":"Prepared Equipment","effect":"A reasonable item from the character's field kit is available.","tags":["equipment","tool","kit","need"]},
    {"category":"edge","title":"Quiet Footing","effect":"The next stealthy approach avoids one minor obstacle or noise.","tags":["sneak","stealth","follow","enter"]},
    {"category":"edge","title":"Agency Pull","effect":"Official credentials open a limited door, file, or conversation.","tags":["police","file","official","hospital","agency"]},
    {"category":"edge","title":"Psychic Shelter","effect":"One hostile psychic intrusion is weakened or briefly delayed.","tags":["psychic","telepathy","wamphyri","mind","resist"]},
    {"category":"edge","title":"Lucky Break","effect":"A failed or stalled approach creates a different useful opportunity.","tags":["fail","stuck","blocked","search"]},
    {"category":"edge","title":"Witness Remembers","effect":"A witness recalls one concrete sensory detail after careful questioning.","tags":["witness","question","memory","interview"]},
    {"category":"edge","title":"Dead Drop","effect":"A concealed note, cache, or prearranged signal survives compromise.","tags":["cache","message","contact","spy"]},
    {"category":"edge","title":"Last Match","effect":"A small source of light, heat, or power remains when it is most needed.","tags":["dark","cold","power","light"]},
    {"category":"edge","title":"Calm Under Fire","effect":"The player keeps control during one sudden threat or frightening revelation.","tags":["fear","attack","surprise","horror"]},
    {"category":"edge","title":"Borrowed Time","effect":"An approaching threat is delayed long enough for one meaningful action.","tags":["time","hurry","escape","threat"]},
    {"category":"edge","title":"Useful Rumor","effect":"A local rumor points toward a real place, person, or historical event.","tags":["rumor","town","local","history"]},
    {"category":"edge","title":"Unbroken Thread","effect":"One apparently unrelated clue can be connected to the current investigation.","tags":["clue","connect","evidence","investigate"]},
    {"category":"edge","title":"Field Medicine","effect":"Stabilize a wounded person long enough to move or speak.","tags":["wound","injured","blood","medical"]},
    {"category":"edge","title":"Counter-Surveillance","effect":"The player detects that the team is being watched or followed.","tags":["follow","watch","surveillance","tail"]},
    {"category":"edge","title":"Human Anchor","effect":"A personal memory or trusted voice helps resist psychic isolation.","tags":["mind","memory","psychic","alone"]},

    {"category":"complication","title":"Static on the Line","effect":"Communication becomes unreliable and a crucial message arrives incomplete.","tags":["radio","phone","message","contact"]},
    {"category":"complication","title":"Compromised Contact","effect":"A trusted source has been frightened, turned, watched, or replaced.","tags":["contact","informant","ally","agency"]},
    {"category":"complication","title":"Watcher in the Crowd","effect":"Someone nearby is observing the player with professional patience.","tags":["crowd","street","station","public"]},
    {"category":"complication","title":"Wrong Door, Right Secret","effect":"A mistaken route exposes dangerous information that was not meant to be found yet.","tags":["door","search","building","room"]},
    {"category":"complication","title":"Psychic Echo","effect":"A psychic action leaves a trace that another gifted being may detect.","tags":["psychic","esp","talent","mind"]},
    {"category":"complication","title":"Authority Arrives","effect":"Police, security, military, or hostile officials complicate the scene.","tags":["police","security","official","crime"]},
    {"category":"complication","title":"The Evidence Moves","effect":"A person, object, or body central to the investigation is relocated or disappears.","tags":["evidence","body","object","suspect"]},
    {"category":"complication","title":"Personal Cost","effect":"The next safe choice threatens a relationship, promise, or piece of the character's ordinary life.","tags":["family","friend","promise","home"]},

    {"category":"turn","title":"Catastrophe","effect":"A major plan fails or a hidden threat acts decisively; preserve one fair path forward.","tags":[]},
    {"category":"turn","title":"Opening","effect":"An unexpected but credible chance appears; it will vanish if ignored.","tags":[]},
    {"category":"turn","title":"Intruder","effect":"A third party enters the situation with an agenda different from both sides.","tags":[]},
    {"category":"turn","title":"Unwritten Turn","effect":"Agent Fox introduces one surprising development consistent with established canon and clues.","tags":[]},
]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")


def check_url(url: str, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def post_json(url: str, payload: dict[str, Any], timeout: int = 360) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def bonus_number(total: int) -> int:
    total = int(total)
    if total < 2:
        return -10
    result = -10
    for threshold, value in BONUS_THRESHOLDS:
        if total >= threshold:
            result = value
        else:
            break
    if total >= 45:
        result = 14 + ((total - 45) // 5)
    return result


def roll_masterbook(skill: int, difficulty: int, effect_value: int = 0) -> dict[str, Any]:
    die_one = secrets.randbelow(10) + 1
    die_two = secrets.randbelow(10) + 1
    raw_total = die_one + die_two

    # A natural 10 may explode when the character has trained adds.
    explosions = []
    for original in (die_one, die_two):
        if original == 10 and int(skill) > 0:
            while True:
                extra = secrets.randbelow(10) + 1
                explosions.append(extra)
                raw_total += extra
                if extra != 10:
                    break

    bonus = bonus_number(raw_total)
    action_total = int(skill) + bonus
    result_points = action_total - int(difficulty)
    success = result_points >= 0
    final_effect = int(effect_value) + result_points if success else int(effect_value)

    return {
        "dice": [die_one, die_two],
        "explosions": explosions,
        "roll_total": raw_total,
        "bonus_number": bonus,
        "skill": int(skill),
        "difficulty_number": int(difficulty),
        "action_total": action_total,
        "result_points": result_points,
        "success": success,
        "effect_value": int(effect_value),
        "final_effect": final_effect,
        "created": now_iso(),
    }


def words_for_search(value: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", value.casefold())
    stop = {
        "the","and","that","this","with","from","have","what","when","where",
        "which","will","would","could","should","into","about","there","their",
        "they","them","then","than","your","you","our","are","was","were",
        "been","being","for","but","not","all","any","can","how","why","who",
        "did","does","use","using","make","take","want","agent","fox",
    }
    unique = []
    for word in words:
        if word in stop or word in unique:
            continue
        unique.append(word)
    return unique[:10]


def source_search(
    database: Path,
    query: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    terms = words_for_search(query)
    if not terms:
        terms = ["necroscope"]

    with sqlite3.connect(str(database)) as connection:
        rows = connection.execute(
            """
            SELECT
                book_key,
                title,
                page_number,
                text,
                low_text
            FROM pages
            WHERE text <> ''
            """
        ).fetchall()

    scored = []
    for book_key, title, page_number, text, low_text in rows:
        lowered = str(text).casefold()
        score = sum(lowered.count(term) for term in terms)
        phrase = query.strip().casefold()
        if phrase and len(phrase) >= 5 and phrase in lowered:
            score += 10
        if score <= 0:
            continue
        scored.append(
            (
                score,
                str(title),
                int(page_number),
                str(book_key),
                str(text),
                bool(low_text),
            )
        )

    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    results = []
    used = set()
    for score, title, page_number, book_key, text, low_text in scored:
        key = (book_key, page_number)
        if key in used:
            continue
        used.add(key)

        compact = re.sub(r"\s+", " ", text).strip()
        positions = [
            compact.casefold().find(term)
            for term in terms
            if compact.casefold().find(term) >= 0
        ]
        center = min(positions) if positions else 0
        start = max(0, center - 380)
        end = min(len(compact), center + 1250)
        snippet = ("..." if start else "") + compact[start:end]
        if end < len(compact):
            snippet += "..."

        results.append(
            {
                "book_key": book_key,
                "title": title,
                "page_number": page_number,
                "score": score,
                "snippet": snippet,
                "low_text": low_text,
            }
        )
        if len(results) >= max(1, min(int(limit), 8)):
            break
    return results


class CampaignApp:
    def __init__(self, root: Path):
        self.root = root
        self.app_dir = Path(__file__).resolve().parent
        self.static_dir = self.app_dir / "static"
        self.database = (
            root
            / "Projects"
            / "NecroscopeCampaign"
            / "SourceIndexV1"
            / "necroscope_sources.sqlite3"
        )
        self.state_dir = (
            root
            / "Projects"
            / "NecroscopeCampaign"
            / "CampaignRoomV1"
        )
        self.state_file = self.state_dir / "campaign_state.json"
        self.log_file = self.state_dir / "session_log.jsonl"
        self.deck_file = self.state_dir / "agent_deck_state.json"
        self.lock = threading.RLock()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.ensure_state()

    def ensure_state(self) -> None:
        if not self.state_file.exists():
            atomic_write_json(
                self.state_file,
                {
                    "schema": "foxai.necroscope.campaign_room.v1",
                    "version": APP_VERSION,
                    "created": now_iso(),
                    "updated": now_iso(),
                    "campaign_name": "Operation Grey Lantern",
                    "player_name": "Eric",
                    "character_name": "Agent",
                    "role": "E-Branch Investigator",
                    "canon_mode": "Canon + Original Gaps",
                    "deck_mode": "Agent-Managed",
                    "turn_count": 0,
                    "scene": "Not started",
                    "notes": "",
                    "character": ROLE_TEMPLATES["E-Branch Investigator"],
                    "transcript": [],
                },
            )
        if not self.deck_file.exists():
            self.reset_deck()

    def load_state(self) -> dict[str, Any]:
        self.ensure_state()
        return read_json(self.state_file, {})

    def save_state(self, state: dict[str, Any]) -> None:
        state["updated"] = now_iso()
        atomic_write_json(self.state_file, state)

    def reset_deck(self) -> dict[str, Any]:
        cards = [dict(card, card_id=f"fox-{index+1:03d}") for index, card in enumerate(STORY_DECK)]
        random.SystemRandom().shuffle(cards)
        deck = {
            "schema": "foxai.necroscope.story_deck.v1",
            "created": now_iso(),
            "original_proxy": True,
            "exact_masterdeck": False,
            "draw_pile": cards,
            "discard": [],
            "held_edges": [],
            "last_applied": None,
            "draw_count": 0,
        }
        atomic_write_json(self.deck_file, deck)
        return deck

    def load_deck(self) -> dict[str, Any]:
        deck = read_json(self.deck_file, {})
        if not deck.get("draw_pile") and not deck.get("discard"):
            deck = self.reset_deck()
        return deck

    def save_deck(self, deck: dict[str, Any]) -> None:
        atomic_write_json(self.deck_file, deck)

    def draw_card(self, force_apply: bool = False) -> dict[str, Any]:
        with self.lock:
            deck = self.load_deck()
            if not deck["draw_pile"]:
                deck["draw_pile"] = deck["discard"]
                deck["discard"] = []
                random.SystemRandom().shuffle(deck["draw_pile"])

            card = deck["draw_pile"].pop(0)
            deck["draw_count"] = int(deck.get("draw_count", 0)) + 1
            applied = force_apply or card["category"] in {"complication", "turn"}

            if card["category"] == "edge" and not applied:
                deck["held_edges"].append(card)
                if len(deck["held_edges"]) > 3:
                    deck["discard"].append(deck["held_edges"].pop(0))
            else:
                deck["last_applied"] = dict(card, applied_at=now_iso())
                deck["discard"].append(card)

            self.save_deck(deck)
            append_jsonl(
                self.log_file,
                {
                    "type": "story_deck_draw",
                    "created": now_iso(),
                    "card": card,
                    "applied": applied,
                    "proxy_deck": True,
                },
            )
            return {
                "card": card,
                "applied": applied,
                "held_count": len(deck["held_edges"]),
                "remaining": len(deck["draw_pile"]),
            }

    def maybe_agent_card(self, user_text: str, state: dict[str, Any]) -> dict[str, Any] | None:
        if state.get("deck_mode") == "Off":
            return None

        turn = int(state.get("turn_count", 0))
        # Quiet predictable cadence: every third player turn.
        if turn < 1 or turn % 3 != 0:
            return None

        drawn = self.draw_card(force_apply=False)
        card = drawn["card"]
        if drawn["applied"]:
            return card

        # An Edge is held. Apply it only when the current action matches its tags.
        lowered = user_text.casefold()
        if any(tag in lowered for tag in card.get("tags", [])):
            with self.lock:
                deck = self.load_deck()
                held = deck.get("held_edges", [])
                matched = next(
                    (item for item in held if item.get("card_id") == card.get("card_id")),
                    None,
                )
                if matched:
                    held.remove(matched)
                    deck["discard"].append(matched)
                    deck["last_applied"] = dict(matched, applied_at=now_iso())
                    self.save_deck(deck)
                    return matched
        return None

    def setup(self, data: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            state = self.load_state()
            role = str(data.get("role") or state.get("role") or "E-Branch Investigator")
            if role not in ROLE_TEMPLATES:
                role = "E-Branch Investigator"

            state["campaign_name"] = str(
                data.get("campaign_name") or state.get("campaign_name") or "Operation Grey Lantern"
            )[:120]
            state["player_name"] = str(
                data.get("player_name") or state.get("player_name") or "Eric"
            )[:80]
            state["character_name"] = str(
                data.get("character_name") or state.get("character_name") or "Agent"
            )[:80]
            state["role"] = role
            state["canon_mode"] = str(
                data.get("canon_mode") or state.get("canon_mode") or "Canon + Original Gaps"
            )[:60]
            state["deck_mode"] = str(
                data.get("deck_mode") or state.get("deck_mode") or "Agent-Managed"
            )[:40]
            state["notes"] = str(data.get("notes") or state.get("notes") or "")[:4000]
            state["character"] = ROLE_TEMPLATES[role]
            self.save_state(state)
            append_jsonl(
                self.log_file,
                {
                    "type": "campaign_setup",
                    "created": now_iso(),
                    "campaign_name": state["campaign_name"],
                    "player_name": state["player_name"],
                    "character_name": state["character_name"],
                    "role": role,
                    "canon_mode": state["canon_mode"],
                    "deck_mode": state["deck_mode"],
                },
            )
            return {"ok": True, "state": state}

    def start_campaign(self) -> dict[str, Any]:
        state = self.load_state()
        if state.get("transcript"):
            return {"ok": True, "state": state, "message": "Campaign already started."}

        opening = (
            "Begin the first scene of this private Necroscope campaign. "
            "The player is reporting for a tense E-Branch field assignment. "
            "Establish place, immediate human stakes, one unsettling detail, "
            "and a clear first decision. Do not decide the player's action."
        )
        return self.chat(opening, internal_start=True)

    def recent_history(self, state: dict[str, Any], limit: int = 8) -> list[dict[str, str]]:
        messages = []
        for item in state.get("transcript", [])[-limit:]:
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": str(content)})
        return messages

    def build_system_prompt(
        self,
        state: dict[str, Any],
        sources: list[dict[str, Any]],
        card: dict[str, Any] | None,
    ) -> str:
        character = state.get("character") or {}
        source_text = "\n\n".join(
            (
                f"[SOURCE {index}: {source['title']}, PDF page {source['page_number']}]\n"
                f"{source['snippet']}"
            )
            for index, source in enumerate(sources, start=1)
        )
        if not source_text:
            source_text = "[No matching private source pages were retrieved for this turn.]"

        card_text = "No story-deck effect is active this turn."
        if card:
            card_text = (
                "A FOXAI Story Deck proxy card is active this turn:\n"
                f"- {card['title']} ({card['category']}): {card['effect']}\n"
                "Use it subtly and fairly. This is an original proxy effect, not an exact MasterDeck card."
            )

        return f"""
You are Agent Fox acting as the gamemaster for a private, local Necroscope
tabletop campaign owned and played by the operator.

CAMPAIGN
Name: {state.get('campaign_name')}
Player: {state.get('player_name')}
Character: {state.get('character_name')}
Role: {state.get('role')}
Canon mode: {state.get('canon_mode')}
Current scene: {state.get('scene')}
Operator notes: {state.get('notes') or 'None'}

CHARACTER QUICK SHEET
{json.dumps(character, ensure_ascii=False, indent=2)}

GM RULES
- Present the world through scene, dialogue, sensory detail, and consequences.
- Never choose the player's action, emotion, or dialogue.
- End each turn with a clear situation or question.
- Preserve established facts and the transcript.
- Use the private source excerpts below for rules and canon.
- Cite grounded claims in this exact format:
  [Source: Book Title, PDF p. N]
- Never invent a citation or cite a page not supplied below.
- Distinguish source-grounded canon from new connective material.
- In "Canon Only" mode, do not add unsupported lore.
- In "Canon + Original Gaps" mode, invent only people, locations, clues, and
  incidents that do not contradict supplied canon.
- Keep hidden adversary plans private until revealed in play.
- Horror may be intense, but avoid sexual violence and gratuitous cruelty.
- Keep a turn usually between 180 and 450 words.
- The system's core roll is: roll 2d10, convert the total to a Bonus Number,
  add it to the relevant skill, and compare the Action Total to the Difficulty
  Number. Result Points equal Action Total minus Difficulty Number.
- Ask for a roll only when failure would matter. State the skill and DN plainly.

STORY DECK
{card_text}

PRIVATE SOURCE EXCERPTS
{source_text}
""".strip()

    def chat(self, user_text: str, internal_start: bool = False) -> dict[str, Any]:
        clean = str(user_text or "").strip()
        if not clean:
            return {"ok": False, "message": "Enter an action or question."}
        if not self.database.is_file():
            return {
                "ok": False,
                "message": "The private Necroscope source index is missing.",
            }
        if not check_url(CHAT_HEALTH):
            return {
                "ok": False,
                "message": (
                    "The local chat model is not running. Start Fast Talk or "
                    "Creative Brain in FOXAI Artificial Minds, then try again."
                ),
            }

        with self.lock:
            state = self.load_state()
            state["turn_count"] = int(state.get("turn_count", 0)) + 1
            card = self.maybe_agent_card(clean, state)
            sources = source_search(self.database, clean, limit=5)
            system = self.build_system_prompt(state, sources, card)

            messages = [{"role": "system", "content": system}]
            messages.extend(self.recent_history(state))
            messages.append({"role": "user", "content": clean})

            payload = {
                "model": "local-model",
                "messages": messages,
                "temperature": 0.78,
                "max_tokens": 850,
                "stream": False,
            }

            try:
                result = post_json(CHAT_API, payload, timeout=420)
                answer = str(result["choices"][0]["message"]["content"]).strip()
            except urllib.error.URLError as exc:
                return {"ok": False, "message": f"Local model connection failed: {exc}"}
            except Exception as exc:
                return {
                    "ok": False,
                    "message": f"Agent Fox could not complete the turn: {type(exc).__name__}: {exc}",
                }

            if not answer:
                return {"ok": False, "message": "The local model returned an empty turn."}

            if not internal_start:
                state.setdefault("transcript", []).append(
                    {
                        "role": "user",
                        "content": clean,
                        "created": now_iso(),
                    }
                )
            state.setdefault("transcript", []).append(
                {
                    "role": "assistant",
                    "content": answer,
                    "created": now_iso(),
                    "sources": [
                        {
                            "title": source["title"],
                            "page_number": source["page_number"],
                            "book_key": source["book_key"],
                        }
                        for source in sources
                    ],
                    "story_card": card,
                }
            )
            state["scene"] = answer[:180].replace("\n", " ")
            self.save_state(state)

            append_jsonl(
                self.log_file,
                {
                    "type": "campaign_turn",
                    "created": now_iso(),
                    "turn": state["turn_count"],
                    "user": None if internal_start else clean,
                    "assistant": answer,
                    "sources": state["transcript"][-1]["sources"],
                    "story_card": card,
                    "model_endpoint": CHAT_API,
                    "network_use": "localhost_only",
                },
            )

            return {
                "ok": True,
                "answer": answer,
                "sources": state["transcript"][-1]["sources"],
                "story_card": card,
                "state": state,
            }

    def roll(self, data: dict[str, Any]) -> dict[str, Any]:
        try:
            result = roll_masterbook(
                int(data.get("skill", 10)),
                int(data.get("difficulty", 10)),
                int(data.get("effect_value", 0)),
            )
        except Exception:
            return {"ok": False, "message": "Skill, difficulty, and effect must be numbers."}

        append_jsonl(
            self.log_file,
            {
                "type": "masterbook_roll",
                **result,
            },
        )
        return {"ok": True, "roll": result}

    def status(self) -> dict[str, Any]:
        state = self.load_state()
        deck = self.load_deck()
        return {
            "ok": True,
            "version": APP_VERSION,
            "root": str(self.root),
            "source_index_ready": self.database.is_file(),
            "local_model_online": check_url(CHAT_HEALTH),
            "state": state,
            "roles": ROLE_TEMPLATES,
            "deck": {
                "mode": state.get("deck_mode"),
                "remaining": len(deck.get("draw_pile", [])),
                "discarded": len(deck.get("discard", [])),
                "held_count": len(deck.get("held_edges", [])),
                "last_applied": deck.get("last_applied"),
                "proxy": True,
                "exact_masterdeck": False,
            },
        }

    def reveal_deck(self) -> dict[str, Any]:
        deck = self.load_deck()
        return {
            "ok": True,
            "deck": {
                "remaining": len(deck.get("draw_pile", [])),
                "discarded": len(deck.get("discard", [])),
                "held_edges": deck.get("held_edges", []),
                "last_applied": deck.get("last_applied"),
                "draw_count": deck.get("draw_count", 0),
                "proxy": True,
                "exact_masterdeck": False,
            },
        }

    def reset_campaign(self) -> dict[str, Any]:
        with self.lock:
            stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
            backup_dir = self.state_dir / "Archive" / stamp
            backup_dir.mkdir(parents=True, exist_ok=True)
            for path in (self.state_file, self.log_file, self.deck_file):
                if path.exists():
                    shutil.copy2(path, backup_dir / path.name)
            self.state_file.unlink(missing_ok=True)
            self.log_file.unlink(missing_ok=True)
            self.deck_file.unlink(missing_ok=True)
            self.ensure_state()
            return {
                "ok": True,
                "message": "Campaign archived and reset.",
                "archive": str(backup_dir),
                "state": self.load_state(),
            }


APP: CampaignApp | None = None


class Handler(BaseHTTPRequestHandler):
    server_version = "FOXAINecroscopeCampaignRoom/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def send_bytes(
        self,
        data: bytes,
        content_type: str,
        status: int = 200,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, value: Any, status: int = 200) -> None:
        self.send_bytes(
            json.dumps(value, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
            status,
        )

    def read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(min(length, 2_000_000))
            return json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            return {}

    def do_GET(self) -> None:
        assert APP is not None
        path = self.path.split("?", 1)[0]
        if path in {"/", "/index.html"}:
            data = (APP.static_dir / "index.html").read_bytes()
            self.send_bytes(data, "text/html; charset=utf-8")
            return
        if path == "/api/status":
            self.send_json(APP.status())
            return
        if path == "/api/deck/reveal":
            self.send_json(APP.reveal_deck())
            return
        self.send_json({"ok": False, "message": "Not found."}, 404)

    def do_POST(self) -> None:
        assert APP is not None
        path = self.path.split("?", 1)[0]
        data = self.read_json()

        if path == "/api/setup":
            self.send_json(APP.setup(data))
            return
        if path == "/api/start":
            self.send_json(APP.start_campaign())
            return
        if path == "/api/chat":
            self.send_json(APP.chat(str(data.get("message") or "")))
            return
        if path == "/api/roll":
            self.send_json(APP.roll(data))
            return
        if path == "/api/deck/draw":
            self.send_json({"ok": True, **APP.draw_card(force_apply=True)})
            return
        if path == "/api/deck/reset":
            self.send_json({"ok": True, "deck": APP.reset_deck()})
            return
        if path == "/api/campaign/reset":
            self.send_json(APP.reset_campaign())
            return

        self.send_json({"ok": False, "message": "Not found."}, 404)


def self_test() -> int:
    assert bonus_number(2) == -10
    assert bonus_number(7) == -3
    assert bonus_number(8) == -1
    assert bonus_number(9) == -1
    assert bonus_number(10) == 0
    assert bonus_number(11) == 0
    assert bonus_number(12) == 1
    assert bonus_number(20) == 9
    assert bonus_number(24) == 9
    assert bonus_number(25) == 10
    assert bonus_number(45) == 14
    assert bonus_number(50) == 15
    assert len(STORY_DECK) == 36
    assert len(ROLE_TEMPLATES) >= 7
    print("SELF TEST PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    if not (root / "foxai.py").is_file():
        print("ERROR: FOXAI root was not detected:", root)
        print("Extract this folder directly inside Z:\\FOXAI.")
        return 2

    global APP
    APP = CampaignApp(root)

    if not APP.database.is_file():
        print("ERROR: The private Necroscope source index is missing:")
        print(APP.database)
        print("Run FOXAI_NECROSCOPE_PORTABLE_PDF_INDEX_V1 first.")
        return 3

    url = f"http://{HOST}:{args.port}"
    server = ThreadingHTTPServer((HOST, args.port), Handler)

    print("=" * 70)
    print("FOXAI NECROSCOPE CAMPAIGN ROOM V1")
    print("=" * 70)
    print("URL:", url)
    print("Source index:", APP.database)
    print("Campaign state:", APP.state_dir)
    print("Local model:", CHAT_API)
    print("Story deck: original FOXAI proxy, agent-managed by default")
    print()
    print("Press Ctrl+C to stop.")

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
