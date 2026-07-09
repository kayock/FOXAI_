from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
except Exception:
    Console = None

from core_v10.engineering_commissioner import EngineeringCommissioner

root = Path(__file__).resolve().parent
commissioner = EngineeringCommissioner(root)
cert = commissioner.commission()
text = commissioner.render_certificate(cert)

if Console:
    console = Console()
    console.rule("[bold cyan]FOXAI Engineering Commissioning[/bold cyan]")
    console.print(Panel(
        f"[bold]Department:[/bold] {cert.get('department')}\n"
        f"[bold]Officer:[/bold] {cert.get('officer')}\n"
        f"[bold]Status:[/bold] {cert.get('status')}\n"
        f"[bold]OK:[/bold] {cert.get('ok')}",
        title="Commissioning Certificate",
        border_style="green" if cert.get("ok") else "red",
    ))

    dept = None
    for item in cert.get("registry_status", {}).get("departments", []):
        if item.get("id") == "engineering":
            dept = item
            break

    if dept:
        tools = Table(title="Engineering Tools", box=box.ROUNDED)
        tools.add_column("Tool")
        tools.add_column("Status")
        tools.add_column("Import")
        for name, item in dept.get("health", {}).get("tools", {}).items():
            tools.add_row(name, item.get("status", ""), item.get("import_name", ""))
        console.print(tools)

    console.rule("[bold cyan]End Commissioning[/bold cyan]")
else:
    print(text)
