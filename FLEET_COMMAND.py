from pathlib import Path
import sys

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
except Exception:
    Console = None

from core_v10.fleet_command import FleetCommand

root = Path(__file__).resolve().parent
request = " ".join(sys.argv[1:]).strip() or "Tell me a joke about a toaster joining Starfleet."

command = FleetCommand(root)
report = command.command(request)

if Console:
    console = Console()
    console.rule("[bold cyan]FOXAI Fleet Command[/bold cyan]")

    console.print(Panel(
        f"[bold]Version:[/bold] {report['version']}\n"
        f"[bold]OK:[/bold] {report['ok']}\n"
        f"[bold]Elapsed:[/bold] {report['elapsed_ms']} ms\n"
        f"[bold]Fleet:[/bold] {report['fleet'].get('states')}",
        title="Fleet Command Report",
        border_style="green" if report["ok"] else "red",
    ))

    plan = report["plan"]
    console.print(Panel(
        f"[bold]Request:[/bold] {plan.get('request')}\n"
        f"[bold]Mission Type:[/bold] {plan.get('mission_type')}\n"
        f"[bold]Department:[/bold] {plan.get('department')}\n"
        f"[bold]Professor:[/bold] {plan.get('professor')}",
        title="Mission Order",
        border_style="blue",
    ))

    decision = report["decision"]
    console.print(Panel(
        f"[bold]Decision:[/bold] {decision.get('decision')}\n"
        f"[bold]Reason:[/bold] {decision.get('reason')}",
        title="Command Decision",
        border_style="yellow" if decision.get("decision") == "hold" else "green",
    ))

    table = Table(title="Fleet Assignments", box=box.ROUNDED)
    table.add_column("Capability")
    table.add_column("Status")
    table.add_column("Assigned Shuttle")
    table.add_column("Department")
    for a in decision.get("assignments", []):
        table.add_row(
            str(a.get("capability")),
            "OK" if a.get("available") else "MISSING",
            str(a.get("assigned_shuttle") or ""),
            str(a.get("department") or ""),
        )
    console.print(table)

    execution = report.get("execution")
    if execution:
        res = Table(title="Execution Results", box=box.ROUNDED)
        res.add_column("#")
        res.add_column("Capability")
        res.add_column("Shuttle")
        res.add_column("Status")
        res.add_column("Output", overflow="fold")
        for i, r in enumerate(execution.get("results", []), start=1):
            inner = r.get("result") if isinstance(r.get("result"), dict) else {}
            output = inner.get("answer") or inner.get("message") or r.get("message", "")
            res.add_row(str(i), str(r.get("capability")), str(r.get("shuttle")), str(r.get("status")), str(output))
        console.print(res)

    console.rule("[bold cyan]End Fleet Command[/bold cyan]")
else:
    print(command.render_text(report))
