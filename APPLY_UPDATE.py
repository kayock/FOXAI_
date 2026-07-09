from pathlib import Path
import argparse
from core_v10.update_center import UpdateCenter

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
except Exception:
    Console = None

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--preview", action="store_true")
parser.add_argument("--package", default=None)
args = parser.parse_args()

package = Path(args.package).resolve() if args.package else root
center = UpdateCenter(root)
report = center.preview(package) if args.preview else center.apply(package)

if Console:
    c = Console()
    c.rule("[bold cyan]FOXAI Update Center[/bold cyan]")
    c.print(Panel(
        f"OK: {report.get('ok')}\nMode: {report.get('mode')}\nCyclic Copy Risk: {report.get('cyclic_copy_risk')}\nFiles: {len(report.get('files', []))}\nApplied: {len(report.get('applied', [])) if 'applied' in report else 'preview'}",
        title="Project Orion v7.5",
        border_style="green" if report.get("ok") else "red",
    ))
    t = Table(title="Files", box=box.ROUNDED)
    t.add_column("Path")
    t.add_column("Action")
    for item in report.get("files", []):
        t.add_row(item["relative_path"], item["action"])
    c.print(t)
else:
    print(center.render_text(report))
