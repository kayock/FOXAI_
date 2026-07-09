from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
except Exception:
    Console = None

from core_v10.bridge_feed import BridgeFeed

root = Path(__file__).resolve().parent
feed_service = BridgeFeed(root)
feed = feed_service.build()

if Console:
    c = Console()
    c.rule("[bold cyan]Operation Bridge Alive v8.0[/bold cyan]")
    c.print(Panel(
        f"[bold]Generated:[/bold] {feed.get('generated_at')}\n"
        f"[bold]Kernel:[/bold] {feed.get('kernel', {}).get('status')}\n"
        f"[bold]Departments:[/bold] {feed.get('summary', {}).get('department_count')}\n"
        f"[bold]Online:[/bold] {feed.get('summary', {}).get('departments_online')}\n"
        f"[bold]Bridge Feed:[/bold] {root / 'OpsBridge' / 'outbox' / 'bridge_feed.json'}",
        title="FOXAI Bridge Feed",
        border_style="green",
    ))
    t = Table(title="Bridge Department Cards", box=box.ROUNDED)
    t.add_column("Department")
    t.add_column("Officer")
    t.add_column("Status")
    t.add_column("Accent")
    for card in feed.get("department_cards", []):
        t.add_row(str(card.get("title")), str(card.get("officer")), str(card.get("status")), str(card.get("accent")))
    c.print(t)
    c.rule("[bold cyan]End Bridge Feed[/bold cyan]")
else:
    print(feed_service.render_text(feed))
