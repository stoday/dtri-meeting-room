from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import shutil
from typing import Any

from .browser import (
    login_and_refresh,
    prepare_reservation,
    refresh_snapshot,
    ReservationPreflightFailed,
    reservation_succeeded,
    submit_reservation,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SNAPSHOT = ROOT / "data" / "current_week.json"
DEFAULT_RESERVATION_CAPTURE = ROOT / "data" / "reservation-flow.private.json"
SKILL_NAME = "dtri-meeting-room"
SKILL_SOURCE = Path(__file__).parent / "skills" / SKILL_NAME / "SKILL.md"
PLATFORM_SKILL_ROOTS = {
    "codex": ROOT / ".codex" / "skills",
    "antigravity": ROOT / ".agents" / "skills",
    "claude": ROOT / ".claude" / "skills",
    "anthropic": ROOT / ".claude" / "skills",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, snapshot: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _minutes(value: str) -> int:
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def _snapshot_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT, help="Path to a normalized JSON snapshot")


def _period(value: str) -> tuple[str, str]:
    try:
        start, end = value.split("-", maxsplit=1)
        if _minutes(start) >= _minutes(end):
            raise ValueError
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be HH:MM-HH:MM, with end later than start") from error
    return start, end


def _iso_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be YYYY-MM-DD") from error


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dtri-meeting-room",
        description="View company meeting-room occupancy and prepare reservations safely.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    login = commands.add_parser("login", help="Open the isolated Playwright browser and refresh the weekly snapshot")
    login.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT, help="Where to save the refreshed JSON snapshot")
    login.add_argument(
        "--capture-reservation",
        action="store_true",
        help="Keep the browser open for one manual reservation and save a redacted request summary locally",
    )
    login.set_defaults(handler=_login)
    view = commands.add_parser("view", help="Show occupancy from the local weekly snapshot")
    view.add_argument("--date", type=_iso_date, help="Limit output to a YYYY-MM-DD date")
    view.add_argument("--refresh", action="store_true", help="Refresh the snapshot with the saved Playwright login first")
    _snapshot_arg(view)
    view.set_defaults(handler=_view)
    reserve = commands.add_parser("reserve", help="Prepare a dated reservation; final submission requires YES")
    reserve.add_argument("room_id", help="Room number, for example 801")
    reserve.add_argument("date", type=_iso_date, help="Required YYYY-MM-DD date")
    reserve.add_argument("period", type=_period, help="Required HH:MM-HH:MM period")
    reserve.set_defaults(handler=_reserve)
    cancel = commands.add_parser("cancel", help="List your reservations and select one to cancel")
    cancel.set_defaults(handler=_pending_write)
    install_skill = commands.add_parser("install-skill", help="Install this project's Agent Skill into a skills root")
    install_skill.add_argument("destination", help="A skills-root path, or one of: codex, antigravity, claude")
    install_skill.add_argument("--force", action="store_true", help="Replace an existing SKILL.md at the destination")
    install_skill.set_defaults(handler=_install_skill)
    args = parser.parse_args()
    args.handler(args)


def _login(args: argparse.Namespace) -> None:
    capture_path = DEFAULT_RESERVATION_CAPTURE if args.capture_reservation else None
    snapshot = login_and_refresh(ROOT, capture_path=capture_path)
    if capture_path:
        snapshot = refresh_snapshot(ROOT)
        print(f"Saved redacted reservation request summary to {capture_path}")
    _save(args.snapshot, snapshot)
    print(f"Saved {len(snapshot['rooms'])} rooms to {args.snapshot}")


def _view(args: argparse.Namespace) -> None:
    if args.refresh:
        snapshot = refresh_snapshot(ROOT)
        _save(args.snapshot, snapshot)
        print(f"Refreshed {len(snapshot['rooms'])} rooms in {args.snapshot}")
    snapshot = _load(args.snapshot)
    dates = snapshot["week_dates"]
    requested_date = args.date.replace("-", "/") if args.date else None
    if requested_date and requested_date not in dates:
        raise SystemExit(f"{args.date} is not included in this snapshot")
    indices = [dates.index(requested_date)] if requested_date else range(len(dates))
    print(f"Snapshot: {snapshot['retrieved_at']}")
    for room in snapshot["rooms"]:
        print(f"{room['id']:>4}  {room['details']}")
        for index in indices:
            periods = room.get("available_periods", room.get("bookings", []))[index]
            print(f"      {dates[index]}  {', '.join(periods) or 'unavailable'}")


def _pending_write(args: argparse.Namespace) -> None:
    raise SystemExit(
        f"{args.command} is defined but not enabled yet: the official form submission flow is still being mapped."
    )


def _skill_destination(destination: str) -> Path:
    """Resolve a platform preset or custom skills-root path to this skill's folder."""
    skills_root = PLATFORM_SKILL_ROOTS.get(destination.lower(), Path(destination))
    return skills_root.resolve() / SKILL_NAME


def _install_skill(args: argparse.Namespace) -> None:
    if not SKILL_SOURCE.is_file():
        raise SystemExit(f"Packaged skill source is missing: {SKILL_SOURCE}")
    skill_directory = _skill_destination(args.destination)
    target = skill_directory / "SKILL.md"
    if target.exists() and not args.force:
        raise SystemExit(f"Refusing to overwrite existing skill: {target}. Re-run with --force to replace it.")
    skill_directory.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SKILL_SOURCE, target)
    print(f"Installed {SKILL_NAME} to {target}")


def _reserve(args: argparse.Namespace) -> None:
    reason = input("會議事由 [工作進度討論]: ").lstrip("\ufeff").strip() or "工作進度討論"
    start, end = args.period
    plan = prepare_reservation(
        ROOT, room_number=args.room_id, booking_date=args.date, start=start, end=end, reason=reason
    )
    print("\n預約摘要")
    print(f"  會議室: {plan.room_number} (server ID: {plan.itemno})")
    print(f"  時間: {plan.booking_date} {plan.start}-{plan.end}")
    print(f"  事由: {plan.reason}")
    if input("輸入 YES 以送出預約: ").lstrip("\ufeff").strip() != "YES":
        print("已取消，未送出任何預約請求。")
        return
    try:
        status, response_text = submit_reservation(ROOT, plan)
    except ReservationPreflightFailed as error:
        raise SystemExit(f"預約前置規則檢核未通過，未送出預約：{error}") from error
    if reservation_succeeded(status, response_text):
        print("預約成功：SaveBorrow 回傳更新後的 Borrowed 週表。")
        return
    print(f"預約請求已送出，但未符合已知成功契約（HTTP {status}）。")
    print(f"回應摘要: {' '.join(response_text.split())[:240]}")


def legacy_main() -> None:
    """Reserved for migration of the original snapshot utility commands."""
    raise SystemExit("Use 'dtri-meeting-room --help'.")


if __name__ == "__main__":
    main()
