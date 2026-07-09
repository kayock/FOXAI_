from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
except Exception:
    Console = None

from core_v10.event_bus import EventBus
from core_v10.captains_log import CaptainsLog

root = Path(__file__).resolve().parent
bus = EventBus(root)

events = [
    ("kernel.boot", "FOXKernel", "FOXKernel boot sequence started.", {"state": "starting"}, "info", "system"),
    ("department.online", "Engineering Department", "Engineering Department reports ACTIVE.", {"department": "engineering", "officer": "Chief Engineer Ada"}, "success", "bridge"),
    ("shipyard.ready", "Chief Engineer Ada", "Shipyard tools are ready for stabilization missions.", {"tools": ["ruff", "black", "mypy", "pydeps", "import-linter", "grimp", "pip-audit", "cyclonedx-bom"]}, "success", "engineering"),
    ("captains_log.new", "Captain Kayock", "The first commissioned department now has a crew and a log.", {}, "info", "bridge"),
]

for event_type, source, message, payload, severity, channel in events:
    bus.publish(event_type, source, message, payload, severity, channel)

log = CaptainsLog(root).build(limit=25)

if Console:
    console = Console()
    console.rule("[bold cyan]FOXAI Event Bus Demo[/bold cyan]")
    console.print(Panel(
        f"[bold]Events Published:[/bold] {len(events)}\n"
        f"[bold]Captain's Log Entries:[/bold] {log.get('entry_count')}\n"
        f"[bold]Outbox:[/bold] {root / 'OpsBridge' / 'outbox'}",
        title="Project Orion v7.3",
        border_style="green",
    ))
    console.print(CaptainsLog(root).render_text(log))
    console.rule("[bold cyan]End Event Bus Demo[/bold cyan]")
else:
    print(CaptainsLog(root).render_text(log))
