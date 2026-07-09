from pathlib import Path
import sys

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
except Exception:
    Console = None

from core_v10.mission_executor import MissionExecutor

root = Path(__file__).resolve().parent
request = " ".join(sys.argv[1:]).strip() or "Tell me a joke about a toaster joining Starfleet."

executor = MissionExecutor(root)
report = executor.execute(request)

if Console:
    console = Console()
    console.rule("[bold cyan]FOXAI Mission Execution Engine[/bold cyan]")
    console.print(Panel(
        f"[bold]Mission ID:[/bold] {report['mission_id']}\n"
        f"[bold]Status:[/bold] {report['status']}\n"
        f"[bold]OK:[/bold] {report['ok']}\n"
        f"[bold]Elapsed:[/bold] {report['elapsed_ms']} ms",
        title="Mission Execution Report",
        border_style="green" if report["ok"] else "red",
    ))

    plan = report["plan"]
    console.print(Panel(
        f"[bold]Request:[/bold] {plan.get('request')}\n"
        f"[bold]Mission Type:[/bold] {plan.get('mission_type')}\n"
        f"[bold]Department:[/bold] {plan.get('department')}\n"
        f"[bold]Professor:[/bold] {plan.get('professor')}",
        title="Mission Plan",
        border_style="blue",
    ))

    caps = Table(title="Capability Assignment", box=box.ROUNDED)
    caps.add_column("Capability")
    caps.add_column("Available")
    caps.add_column("Assigned")
    caps.add_column("Department")
    for g in report["gap_report"].get("gaps", []):
        caps.add_row(
            str(g.get("capability")),
            "YES" if g.get("available") else "NO",
            str(g.get("assigned_shuttle") or g.get("recommended_shuttle") or ""),
            str(g.get("department") or ""),
        )
    console.print(caps)

    res = Table(title="Execution Results", box=box.ROUNDED)
    res.add_column("#")
    res.add_column("Capability")
    res.add_column("Shuttle")
    res.add_column("Status")
    res.add_column("Output", overflow="fold")
    for i, r in enumerate(report.get("results", []), start=1):
        inner = r.get("result") if isinstance(r.get("result"), dict) else {}
        output = inner.get("answer") or inner.get("message") or r.get("message", "")
        res.add_row(str(i), str(r.get("capability")), str(r.get("shuttle")), str(r.get("status")), str(output))
    console.print(res)

    console.rule("[bold cyan]End Mission Execution[/bold cyan]")
else:
    print(executor.render_text(report))
