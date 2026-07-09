from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
except Exception:
    Console = None

from core_v10.fox_kernel import FOXKernel

root = Path(__file__).resolve().parent
kernel = FOXKernel(root)
report = kernel.boot()

if Console:
    console = Console()
    console.rule("[bold cyan]FOXAI Command OS v6.0[/bold cyan]")
    console.print(Panel(
        f"[bold]OK:[/bold] {report.get('ok')}\n"
        f"[bold]Booted:[/bold] {report.get('booted')}\n"
        f"[bold]Root:[/bold] {report.get('root')}\n"
        f"[bold]Uptime:[/bold] {report.get('uptime_seconds')} seconds",
        title="FOXKernel Status",
        border_style="green" if report.get("ok") else "red",
    ))

    comp = Table(title="Kernel Components", box=box.ROUNDED)
    comp.add_column("Component")
    comp.add_column("Status")
    for key, value in report.get("components", {}).items():
        comp.add_row(key, "READY" if value else "MISSING")
    console.print(comp)

    fleet_summary = report.get("fleet", {}).get("summary", {})
    console.print(Panel(
        f"[bold]Total:[/bold] {fleet_summary.get('total')}\n"
        f"[bold]States:[/bold] {fleet_summary.get('states')}\n"
        f"[bold]Kinds:[/bold] {fleet_summary.get('kinds')}",
        title="Fleet",
        border_style="green",
    ))

    runtime = report.get("runtime", {})
    console.print(Panel(
        f"[bold]Roots:[/bold] {runtime.get('roots')}\n"
        f"[bold]Packages:[/bold] {runtime.get('package_count')}\n"
        f"[bold]Imports:[/bold] {runtime.get('import_count')}",
        title="Hangar Bay Runtime",
        border_style="blue",
    ))

    fw = Table(title="Officer Frameworks", box=box.ROUNDED)
    fw.add_column("Framework")
    fw.add_column("Status")
    fw.add_column("Source")
    fw.add_column("Version")
    for key, item in report.get("officers", {}).get("frameworks", {}).items():
        fw.add_row(
            str(item.get("label")),
            str(item.get("status")),
            str(item.get("source")),
            str(item.get("version", "")),
        )
    console.print(fw)

    console.rule("[bold cyan]End FOXKernel Status[/bold cyan]")
else:
    print(kernel.render_status(report))
