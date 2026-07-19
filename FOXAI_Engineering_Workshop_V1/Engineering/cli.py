from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .workshop import EngineeringWorkshop, WorkshopError
except ImportError:  # Direct-script fallback for maintenance use.
    from workshop import EngineeringWorkshop, WorkshopError  # type: ignore


def _default_data_root() -> Path:
    here = Path(__file__).resolve()
    foxai_root = here.parents[2] if len(here.parents) >= 3 else here.parent
    return foxai_root / "System" / "EngineeringWorkshop"


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FOXAI Engineering Workshop V1")
    parser.add_argument("--data-root", default=str(_default_data_root()))
    sub = parser.add_subparsers(dest="command", required=True)

    route = sub.add_parser("route", help="Classify a mission without changing files")
    route.add_argument("text")

    begin = sub.add_parser("begin", help="Create structured mission state")
    begin.add_argument("mission_id")
    begin.add_argument("title")
    begin.add_argument("text")
    begin.add_argument("--project-root")

    locate = sub.add_parser("locate", help="Read-only live-source discovery")
    locate.add_argument("mission_id")
    locate.add_argument("terms", nargs="+")

    preview = sub.add_parser("preview", help="Validate and preview an exact plan")
    preview.add_argument("plan")

    apply_cmd = sub.add_parser("apply", help="Apply a previewed exact plan")
    apply_cmd.add_argument("plan")
    apply_cmd.add_argument("--approve", required=True, help="Exact SHA-256 from preview")

    rollback = sub.add_parser("rollback", help="Restore the mission snapshot")
    rollback.add_argument("mission_id")

    status = sub.add_parser("status", help="Show active or named mission state")
    status.add_argument("mission_id", nargs="?")

    caps = sub.add_parser("capabilities", help="Show real interface capabilities")
    caps.add_argument("--project-root")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workshop = EngineeringWorkshop(args.data_root)
    try:
        if args.command == "route":
            decision = workshop.route(args.text)
            _print(
                {
                    "mission_type": decision.mission_type,
                    "authorized": decision.authorized,
                    "confidence": decision.confidence,
                    "reasons": decision.reasons,
                }
            )
        elif args.command == "begin":
            _print(
                workshop.begin_mission(
                    args.mission_id,
                    args.title,
                    args.text,
                    args.project_root,
                ).to_dict()
            )
        elif args.command == "locate":
            _print(workshop.locate(args.mission_id, args.terms))
        elif args.command == "preview":
            _print(workshop.preview_plan(args.plan))
        elif args.command == "apply":
            _print(workshop.apply_plan(args.plan, args.approve))
        elif args.command == "rollback":
            _print(workshop.rollback(args.mission_id))
        elif args.command == "status":
            state = (
                workshop.state_store.load(args.mission_id)
                if args.mission_id
                else workshop.state_store.load_active()
            )
            _print(state.to_dict() if state else {"active_mission": None})
        elif args.command == "capabilities":
            _print(workshop.capabilities(args.project_root))
        else:
            raise AssertionError("unhandled command")
        return 0
    except (WorkshopError, ValueError, OSError, KeyError) as exc:
        _print({"ok": False, "error": str(exc), "error_type": type(exc).__name__})
        return 2


if __name__ == "__main__":
    sys.exit(main())
