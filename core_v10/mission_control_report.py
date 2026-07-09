from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich import box

from .fleet_registry import FleetRegistry
from .mission_planner import MissionPlanner
from .vault import Vault


STATE_STYLE = {
    "Operational": "green",
    "Reserved": "cyan",
    "Missing": "red",
    "Docked": "yellow",
    "Unknown": "magenta",
}


@dataclass
class MissionControlReport:
    foxai_root: Path
    console: Console | None = None

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.console = self.console or Console()

    def fleet_table(self) -> Table:
        fleet = FleetRegistry(self.foxai_root)
        data = fleet.refresh()
        summary = fleet.summary(data)

        table = Table(title="Hangar Bay Fleet", box=box.ROUNDED)
        table.add_column("State", style="bold")
        table.add_column("Callsign")
        table.add_column("Department")
        table.add_column("Capabilities")
        table.add_column("Path", overflow="fold")

        for dept, shuttles in summary.get("departments", {}).items():
            for s in shuttles:
                state = s.get("service_state", "Unknown")
                style = STATE_STYLE.get(state, "white")
                caps = ", ".join(s.get("capabilities", [])[:4])
                if len(s.get("capabilities", [])) > 4:
                    caps += ", ..."
                table.add_row(
                    Text(state, style=style),
                    s.get("callsign", ""),
                    s.get("department", dept),
                    caps,
                    s.get("path") or "",
                )

        return table

    def vault_table(self) -> Table:
        vault = Vault(self.foxai_root)
        vault.initialize()
        missions = vault.list_missions(limit=8).get("missions", [])

        table = Table(title="Recent Vault Missions", box=box.ROUNDED)
        table.add_column("ID", justify="right")
        table.add_column("Created")
        table.add_column("Professor")
        table.add_column("Title")
        table.add_column("Status")

        for m in missions:
            table.add_row(
                str(m.get("id")),
                str(m.get("created")),
                str(m.get("professor") or ""),
                str(m.get("title") or ""),
                str(m.get("status") or ""),
            )

        return table

    def plan_panel(self, request: str) -> Panel:
        planner = MissionPlanner(self.foxai_root)
        plan = planner.create_plan(request, professor="Professor Ada")
        text = planner.render_plan_text(plan)
        return Panel(text, title="Mission Planner", border_style="blue")

    def status_panel(self) -> Panel:
        fleet = FleetRegistry(self.foxai_root)
        data = fleet.refresh()
        summary = fleet.summary(data)

        vault = Vault(self.foxai_root)
        info = vault.initialize()

        body = (
            f"[bold]Mission Bus:[/bold] ONLINE\n"
            f"[bold]Vault:[/bold] ONLINE\n"
            f"[bold]Database:[/bold] {info.get('db')}\n"
            f"[bold]Fleet Pods:[/bold] {summary.get('total')}\n"
            f"[bold]Fleet States:[/bold] {summary.get('states')}\n"
        )
        return Panel(body, title="FOXAI Mission Control", border_style="green")

    def render(self, request: str = "Professor Ada, find every place MissionBus is used.") -> None:
        self.console.rule("[bold cyan]FOXAI Mission Control[/bold cyan]")
        self.console.print(self.status_panel())
        self.console.print(self.plan_panel(request))
        self.console.print(self.fleet_table())
        self.console.print(self.vault_table())
        self.console.rule("[bold cyan]End Report[/bold cyan]")
