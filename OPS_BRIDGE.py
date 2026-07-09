from pathlib import Path
import argparse
import json
import sys

try:
    from rich.console import Console
    from rich.panel import Panel
except Exception:
    Console = None

from core_v10.ops_bridge import OPSBridge

root = Path(__file__).resolve().parent

parser = argparse.ArgumentParser(description="FOXAI OPS Bridge")
parser.add_argument("request", nargs="*", help="Mission request text")
parser.add_argument("--mode", default="safe", help="Execution mode")
parser.add_argument("--json", action="store_true", help="Print JSON only")
parser.add_argument("--status", action="store_true", help="Print bridge status")
args = parser.parse_args()

bridge = OPSBridge(root)

if args.status:
    data = bridge.status()
    print(json.dumps(data, indent=2))
    raise SystemExit(0)

request = " ".join(args.request).strip()
if not request:
    request = "Tell me a joke about a toaster joining Starfleet."

result = bridge.execute_text(request, mode=args.mode)

if args.json:
    print(json.dumps(result, indent=2, ensure_ascii=False))
elif Console:
    console = Console()
    console.rule("[bold cyan]FOXAI OPS Bridge[/bold cyan]")
    console.print(Panel(
        f"[bold]OK:[/bold] {result.get('ok')}\n"
        f"[bold]Request:[/bold] {result.get('request')}\n"
        f"[bold]Elapsed:[/bold] {result.get('elapsed_ms')} ms\n"
        f"[bold]Outbox:[/bold] {bridge.outbox}",
        title="OPS Integration",
        border_style="green" if result.get("ok") else "red",
    ))
    console.print(result.get("text", ""))
    console.rule("[bold cyan]End OPS Bridge[/bold cyan]")
else:
    print(result.get("text", ""))
