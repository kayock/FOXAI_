from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
except Exception:
    Console = None

from core_v10.foxai_builder import FOXAIBuilder

root = Path(__file__).resolve().parent
builder = FOXAIBuilder(root)
report = builder.build_all()

if Console:
    c = Console()
    c.rule("[bold cyan]Operation Bridge Alive v8.1[/bold cyan]")
    c.print(Panel(
        f"[bold]OK:[/bold] {report.get('ok')}\n"
        f"[bold]Passed:[/bold] {report.get('passed')}/{len(report.get('steps', []))}\n"
        f"[bold]Builder Report:[/bold] {root / 'OpsBridge' / 'outbox' / 'builder_report.txt'}\n"
        f"[bold]Bridge Feed:[/bold] {root / 'OpsBridge' / 'outbox' / 'bridge_feed.json'}",
        title="FOXAI Builder",
        border_style="green" if report.get("ok") else "yellow",
    ))

    t = Table(title="Build Steps", box=box.ROUNDED)
    t.add_column("Step")
    t.add_column("Status")
    t.add_column("OK")
    for step in report.get("steps", []):
        t.add_row(str(step.get("step")), str(step.get("status")), "YES" if step.get("ok") else "NO")
    c.print(t)
    c.rule("[bold cyan]End FOXAI Builder[/bold cyan]")
else:
    print(builder.render_text(report))
