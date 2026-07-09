from pathlib import Path
import sys

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
except Exception:
    Console = None

from core_v10.plugin_diagnostics import PluginDiagnostics

root = Path(__file__).resolve().parent
key = sys.argv[1] if len(sys.argv) > 1 else "conversation"

diag = PluginDiagnostics(root)
report = diag.report(key)

if Console:
    console = Console()
    console.rule("[bold cyan]FOXAI Plugin Diagnostics[/bold cyan]")
    console.print(Panel(
        f"[bold]Service Key:[/bold] {key}\n"
        f"[bold]Manifests Found:[/bold] {report['discovery']['manifest_count']}\n"
        f"[bold]Plugins Found:[/bold] {report['discovery']['plugin_count']}\n"
        f"[bold]Plugins Loaded:[/bold] {report['loading']['loaded_count']}\n"
        f"[bold]Plugins Failed:[/bold] {report['loading']['failed_count']}\n"
        f"[bold]Raw Health OK:[/bold] {report['raw_service_health'].get('ok')}",
        title="Plugin Framework",
        border_style="green" if report["ok"] else "yellow",
    ))

    pairs = Table(title="Extension Manifest / Plugin Pairs", box=box.ROUNDED)
    pairs.add_column("Key")
    pairs.add_column("Kind")
    pairs.add_column("Manifest")
    pairs.add_column("Plugin")
    pairs.add_column("Dir", overflow="fold")
    for pair in report["discovery"]["pairs"]:
        m = pair.get("manifest") or {}
        p = pair.get("plugin") or {}
        pairs.add_row(
            str(m.get("key", "")),
            str(m.get("kind", "")),
            "YES" if pair.get("has_manifest") else "NO",
            "YES" if pair.get("has_plugin") else "NO",
            pair.get("dir", ""),
        )
    console.print(pairs)

    load = Table(title="Plugin Load Results", box=box.ROUNDED)
    load.add_column("Loaded")
    load.add_column("Hooks")
    load.add_column("Plugin", overflow="fold")
    load.add_column("Error", overflow="fold")
    for p in report["loading"]["plugins"]:
        load.add_row(
            "YES" if p["loaded"] else "NO",
            ", ".join(p.get("hooks", [])),
            p["path"],
            p.get("error", ""),
        )
    console.print(load)

    raw = report["raw_service_health"]
    console.print(Panel(str(raw), title=f"Raw Service Health: {key}", border_style="green" if raw.get("ok") else "red"))

    failures = [p for p in report["loading"]["plugins"] if not p["loaded"]]
    for f in failures:
        console.print(Panel(f.get("traceback", ""), title=f"Traceback: {f.get('path')}", border_style="red"))

    console.rule("[bold cyan]End Plugin Diagnostics[/bold cyan]")
else:
    import json
    print(json.dumps(report, indent=2))
