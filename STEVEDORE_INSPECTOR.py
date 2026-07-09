from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
except Exception:
    Console = None

from core_v10.stevedore_inspector import StevedoreInspector

root = Path(__file__).resolve().parent
inspector = StevedoreInspector(root)
report = inspector.inspect_all()

if Console:
    console = Console()
    console.rule("[bold cyan]FOXAI Stevedore Plugin Inspector[/bold cyan]")
    console.print(Panel(
        f"[bold]Stevedore Importable:[/bold] {report['stevedore_importable']}\n"
        f"[bold]Extensions:[/bold] {report['extension_count']}\n"
        f"[bold]Plugins:[/bold] {report['plugin_count']}\n"
        f"[bold]Loaded:[/bold] {report['loaded_count']}\n"
        f"[bold]Failed:[/bold] {report['failed_count']}\n"
        f"[bold]Fleet States:[/bold] {report['fleet_summary'].get('states')}\n"
        f"[bold]Fleet Kinds:[/bold] {report['fleet_summary'].get('kinds')}",
        title="Stevedore-style Discovery",
        border_style="green" if report["failed_count"] == 0 else "red",
    ))

    table = Table(title="Plugin Load Results", box=box.ROUNDED)
    table.add_column("Key")
    table.add_column("Kind")
    table.add_column("Loaded")
    table.add_column("Hooks")
    table.add_column("Plugin", overflow="fold")
    table.add_column("Error", overflow="fold")

    for item in report["plugins"]:
        load = item.get("load") or {}
        table.add_row(
            str(item.get("key", "")),
            str(item.get("kind", "")),
            "YES" if load.get("loaded") else "NO",
            ", ".join(load.get("hooks", [])),
            str(item.get("plugin_path", "")),
            str(load.get("error", "")),
        )
    console.print(table)

    comp = Table(title="Raw Health vs Fleet Registry", box=box.ROUNDED)
    comp.add_column("Key")
    comp.add_column("Kind")
    comp.add_column("Raw OK")
    comp.add_column("Raw Status")
    comp.add_column("Fleet State")
    comp.add_column("Fleet Health")
    comp.add_column("Matches")
    comp.add_column("Fleet Message", overflow="fold")

    for row in report["comparison"]:
        comp.add_row(
            str(row.get("key")),
            str(row.get("kind")),
            str(row.get("raw_health_ok")),
            str(row.get("raw_health_status")),
            str(row.get("fleet_state")),
            str(row.get("fleet_health_status")),
            "YES" if row.get("matches") else "NO",
            str(row.get("fleet_health_message")),
        )
    console.print(comp)

    console.rule("[bold cyan]End Stevedore Inspector[/bold cyan]")
else:
    import json
    print(json.dumps(report, indent=2))
