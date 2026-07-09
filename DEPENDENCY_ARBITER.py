from pathlib import Path
from core_v10.dependency_arbiter import DependencyArbiter

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
except Exception:
    Console = None

root = Path(__file__).resolve().parent
arbiter = DependencyArbiter(root)
report = arbiter.scan()
paths = arbiter.write_reports(report)

if Console:
    c = Console()
    c.rule("[bold cyan]USS Dependency Arbiter[/bold cyan]")
    c.print(Panel(
        f"[bold]OK:[/bold] {report['ok']}\n[bold]Files Scanned:[/bold] {report['files_scanned']}\n[bold]Problems:[/bold] {report['problem_count']}\n[bold]Report:[/bold] {paths['txt']}",
        title="FOXAI CM v6.1",
        border_style="green" if report["ok"] else "red",
    ))
    if report["problems"]:
        t = Table(title="Dependency Problems", box=box.ROUNDED)
        t.add_column("Type"); t.add_column("Source"); t.add_column("Line"); t.add_column("Message", overflow="fold")
        for p in report["problems"]:
            t.add_row(str(p.get("type")), str(p.get("source_module")), str(p.get("lineno")), str(p.get("message")))
        c.print(t)
    else:
        c.print("[green]No dependency problems detected.[/green]")
    c.rule("[bold cyan]End Dependency Arbiter[/bold cyan]")
else:
    print(arbiter.render_text(report))
