from pathlib import Path
import json
import datetime

ROOT = Path(__file__).resolve().parents[1]
ACADEMY = ROOT / "Academy"
DATA = ACADEMY / "academy.json"

DEFAULT_ACADEMY = {
    "generated_at": None,
    "name": "KayocktheOS Academy",
    "charter": "The purpose of the Academy is not to produce answers. It is to produce understanding.",
    "startup_greeting": "The Academy is open. Today's lesson awaits.",
    "colleges": [
        {
            "id": "practical_curiosity",
            "name": "College of Practical Curiosity",
            "professor": "Professor Kayock",
            "motto": "Wonder is a tool. Build with it.",
            "domains": ["operator guidance", "project building", "practical problem solving"]
        },
        {
            "id": "scientific_curiosity",
            "name": "College of Scientific Curiosity",
            "professor": "Professor Carl Sagan",
            "motto": "Extraordinary claims require extraordinary evidence.",
            "domains": ["science", "evidence", "skepticism", "cosmology"]
        },
        {
            "id": "artificial_minds",
            "name": "College of Artificial Minds",
            "professor": "Professor Asimov",
            "motto": "An intelligent machine earns trust by revealing its reasoning.",
            "domains": ["AI", "safety", "reasoning", "trustworthy systems"]
        },
        {
            "id": "optimistic_futures",
            "name": "College of Optimistic Futures",
            "professor": "Professor Roddenberry",
            "motto": "Technology reaches its highest purpose when it enlarges humanity.",
            "domains": ["future design", "humanism", "ethics", "hopeful technology"]
        },
        {
            "id": "meta_creativity",
            "name": "College of Meta Creativity",
            "professor": "Professor Deadpool",
            "motto": "The best stories know they're being told.",
            "domains": ["storytelling", "humor", "creative critique", "self-aware media"]
        },
        {
            "id": "linux",
            "name": "College of Linux",
            "professor": "Linux Chair",
            "motto": "Everything is a file until it proves otherwise.",
            "domains": ["Linux", "filesystems", "shell", "permissions"]
        },
        {
            "id": "macos",
            "name": "College of macOS",
            "professor": "macOS Chair",
            "motto": "The system has an opinion. Understand it before changing it.",
            "domains": ["macOS", "system design", "defaults", "Apple ecosystem"]
        },
        {
            "id": "networking",
            "name": "College of Networking",
            "professor": "Networking Chair",
            "motto": "Packets never lie.",
            "domains": ["networking", "diagnostics", "routing", "latency"]
        },
        {
            "id": "software_design",
            "name": "College of Software Design",
            "professor": "Software Design Chair",
            "motto": "Optimization begins only after understanding.",
            "domains": ["architecture", "code quality", "maintainability"]
        }
    ],
    "lessons": [
        {
            "id": "welcome_to_the_academy",
            "title": "Welcome to the Academy",
            "college": "practical_curiosity",
            "summary": "KayocktheOS uses an Academy model so knowledge is organized by domains of expertise, not loose tools."
        }
    ]
}

def ensure_academy():
    ACADEMY.mkdir(parents=True, exist_ok=True)
    (ACADEMY / "Professors").mkdir(parents=True, exist_ok=True)
    (ACADEMY / "Colleges").mkdir(parents=True, exist_ok=True)
    (ACADEMY / "Lessons").mkdir(parents=True, exist_ok=True)
    (ACADEMY / "Charter").mkdir(parents=True, exist_ok=True)

    academy = DEFAULT_ACADEMY.copy()
    academy["generated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    DATA.write_text(json.dumps(academy, indent=2), encoding="utf-8")

    (ACADEMY / "Charter" / "ACADEMY_CHARTER.md").write_text(
        "# Academy Charter\n\n"
        + academy["charter"]
        + "\n\n## Startup Greeting\n\n"
        + academy["startup_greeting"]
        + "\n",
        encoding="utf-8"
    )

    for college in academy["colleges"]:
        safe = college["id"]
        md = [
            f"# {college['name']}",
            "",
            f"Professor: **{college['professor']}**",
            "",
            f"Motto: *{college['motto']}*",
            "",
            "## Domains",
            ""
        ]
        md += [f"- {d}" for d in college["domains"]]
        (ACADEMY / "Colleges" / f"{safe}.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    return academy

def academy_status():
    if not DATA.exists():
        return ensure_academy()
    try:
        return json.loads(DATA.read_text(encoding="utf-8"))
    except Exception:
        return ensure_academy()

if __name__ == "__main__":
    data = ensure_academy()
    print(json.dumps({"colleges": len(data["colleges"]), "lessons": len(data["lessons"])}, indent=2))
