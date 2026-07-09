from pathlib import Path
import sys

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
except Exception:
    Console = None

from core_v10.fleet_command_bridge import FleetCommandBridge

root = Path(__file__).resolve().parent
request = " ".join(sys.argv[1:]).strip() or "Tell me a joke about a toaster joining Starfleet."

bridge = FleetCommandBridge(root)
report = bridge.command(request)

if Console:
    console = Console()
    console.rule("[bold cyan]FOXAI Bridge Command[/bold cyan]")

    console.print(Panel(
        f"[bold]OK:[/bold] {report.get('ok')}\n"
        f"[bold]Decision:[/bold] {report.get('decision', {}).get('decision')}\n"
        f"[bold]Fleet:[/bold] {report.get('fleet', {}).get('states')}",
        title="Fleet Command",
        border_style="green" if report.get("ok") else "red",
    ))

    officer_report = report.get("bridge_officers", {})
    fw = Table(title="Installed Officer Frameworks", box=box.ROUNDED)
    fw.add_column("Framework")
    fw.add_column("Status")
    fw.add_column("Source")
    fw.add_column("Alias")
    fw.add_column("Path", overflow="fold")
    for key, item in officer_report.get("frameworks", {}).items():
        fw.add_row(
            item["label"],
            item["status"],
            item.get("source", ""),
            item.get("matched_alias", ""),
            item.get("path", ""),
        )
    console.print(fw)

    officers = Table(title="Bridge Officer Assignments", box=box.ROUNDED)
    officers.add_column("Callsign")
    officers.add_column("Officer")
    officers.add_column("Department")
    officers.add_column("Mode")
    officers.add_column("Optional Frameworks")
    for o in officer_report.get("officers", []):
        officers.add_row(
            str(o.get("callsign")),
            str(o.get("officer")),
            str(o.get("department")),
            str(o.get("mode")),
            ", ".join(o.get("frameworks_available", [])),
        )
    console.print(officers)

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

    console.rule("[bold cyan]End Bridge Command[/bold cyan]")
else:
    print(bridge.render_text(report))
