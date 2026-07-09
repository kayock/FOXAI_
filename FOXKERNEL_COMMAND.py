from pathlib import Path
import sys

try:
    from rich.console import Console
    from rich.panel import Panel
except Exception:
    Console = None

from core_v10.fox_kernel import FOXKernel

root = Path(__file__).resolve().parent
request = " ".join(sys.argv[1:]).strip() or "Tell me a joke about a toaster joining Starfleet."

kernel = FOXKernel(root)
kernel.boot()
report = kernel.command(request)

if Console:
    console = Console()
    console.rule("[bold cyan]FOXKernel Command[/bold cyan]")
    console.print(Panel(
        f"[bold]OK:[/bold] {report.get('ok')}\n"
        f"[bold]Request:[/bold] {request}\n"
        f"[bold]Decision:[/bold] {report.get('decision', {}).get('decision')}",
        title="Kernel Mission Result",
        border_style="green" if report.get("ok") else "red",
    ))
    execution = report.get("execution") or {}
    for item in execution.get("results", []):
        inner = item.get("result") if isinstance(item.get("result"), dict) else {}
        answer = inner.get("answer") or inner.get("message") or item.get("message", "")
        console.print(f"[bold]{item.get('capability')}[/bold] via {item.get('shuttle')} [{item.get('status')}]\n{answer}\n")
    console.rule("[bold cyan]End FOXKernel Command[/bold cyan]")
else:
    print(report)
