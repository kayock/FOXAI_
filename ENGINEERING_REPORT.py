from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
except Exception:
    Console = None

from core_v10.technology_officer import TechnologyOfficer

root = Path(__file__).resolve().parent
officer = TechnologyOfficer(root)
report = officer.engineering_report()

if Console:
    console = Console()
    console.rule("[bold cyan]FOXAI Engineering Report[/bold cyan]")
    console.print(Panel(
        f"[bold]Mission:[/bold] {report['mission']}\n"
        f"[bold]Overall Readiness:[/bold] {report['readiness']['overall']}%\n"
        f"[bold]Services:[/bold] {report['readiness']['services']}%\n"
        f"[bold]Packages:[/bold] {report['readiness']['packages']}%\n"
        f"[bold]Hanger Bay:[/bold] {report['environment'].get('hanger_bay')}",
        title="USS Technology Officer",
        border_style="green" if report["ok"] else "red",
    ))

    svc = Table(title="Core Services", box=box.ROUNDED)
    svc.add_column("Service")
    svc.add_column("Status")
    svc.add_column("Message")
    for item in report["services"]["items"]:
        svc.add_row(item["key"], item["status"], item["message"])
    console.print(svc)

    env = Table(title="Environment Packages", box=box.ROUNDED)
    env.add_column("Package")
    env.add_column("Status")
    env.add_column("Source")
    env.add_column("Path", overflow="fold")
    for p in report["environment"]["packages"]:
        env.add_row(
            p["package"],
            "READY" if p["installed"] else "MISSING",
            p.get("source", ""),
            p.get("path", ""),
        )
    console.print(env)

    contracts = Table(title="Service Contracts", box=box.ROUNDED)
    contracts.add_column("Key")
    contracts.add_column("Kind")
    contracts.add_column("Provides")
    contracts.add_column("Methods")
    for c in report["contracts"]:
        contracts.add_row(
            c.get("key", ""),
            c.get("kind", ""),
            ", ".join(c.get("provides", [])[:4]),
            ", ".join(c.get("methods", [])[:4]),
        )
    console.print(contracts)

    rec = Table(title="Recommendations", box=box.ROUNDED)
    rec.add_column("Priority")
    rec.add_column("Title")
    rec.add_column("Reason")
    for r in report["recommendations"][:8]:
        rec.add_row(str(r["priority"]), r["title"], r["reason"])
    console.print(rec)

    console.rule("[bold cyan]End Engineering Report[/bold cyan]")
else:
    import json
    print(json.dumps(report, indent=2))
