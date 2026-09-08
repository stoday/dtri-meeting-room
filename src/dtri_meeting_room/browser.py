"""Authenticated, non-secret meeting-room collection through Playwright."""

from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any
from urllib.parse import parse_qs, urlparse, urlunparse

from playwright.sync_api import BrowserContext, sync_playwright


MEETING_URL = "https://intranet.ideas.iii.org.tw:8242/default.aspx"
DATE = re.compile(r"^\d{4}/\d{2}/\d{2}$")
ROOM = re.compile(r"^(\d+)\s*會議室\s*(.*)$")
TIME_RANGE = re.compile(r"\b\d{2}:\d{2}-\d{2}:\d{2}\b")
SAVE_BORROW_HANDLER = re.compile(r"/ajax/_Default,App_Web_[^/?\s\"'<>]+\.ashx$")
AJAX_SESSION = "rw"


class AuthenticationRequired(RuntimeError):
    """Raised when the isolated profile cannot view the authenticated schedule."""


class ReservationPreflightFailed(RuntimeError):
    """Raised when the observed reservation rule checks reject a submission."""


@dataclass(frozen=True)
class ReservationPlan:
    room_number: str
    itemno: str
    booking_date: str
    start: str
    end: str
    reason: str


def profile_path(project_root: Path) -> Path:
    return project_root / ".dtri-meeting-room" / "profile"


def reservation_payload(plan: ReservationPlan) -> str:
    return "\r\n".join(
        [
            f"itemno={plan.itemno}",
            f"borrow_date={plan.booking_date.replace('-', '/')}",
            f"starttime={plan.start}",
            f"endtime={plan.end}",
            f"reason={plan.reason}",
            "cnt=0",
            "f_company=",
            "f_name=",
            "f_chk=false",
        ]
    )


def reservation_preflight_requests(plan: ReservationPlan, endpoint: str) -> list[tuple[str, str, str]]:
    """Build the browser-observed rule-check sequence preceding SaveBorrow."""
    parsed = urlparse(endpoint)
    query = parse_qs(parsed.query)
    session = query.get("_session", ["rw"])[0]
    handler = urlunparse((parsed.scheme, parsed.netloc, "/ajax/Pub,App_Code.ashx", "", "", ""))
    rule1 = f"{handler}?_method=Check_Borrow_Rule&_session={session}"
    rule2 = f"{handler}?_method=Check_Borrow_Rule2&_session={session}"
    booking_date = plan.booking_date.replace("-", "/")
    duration = _duration_minutes(plan.start, plan.end)
    return [
        (rule1, "borrow_date=" + booking_date, "Rule1_Allow"),
        (rule2, f"borrow_no=-1\r\nselectdate={booking_date}\r\nestmin=0", "Rules2_Allow"),
        (rule1, "borrow_date=" + booking_date, "Rule1_Allow"),
        (rule2, f"borrow_no=-1\r\nselectdate={booking_date}\r\nestmin={duration}", "Rules2_Allow"),
    ]


def _duration_minutes(start: str, end: str) -> int:
    start_hour, start_minute = map(int, start.split(":"))
    end_hour, end_minute = map(int, end.split(":"))
    return (end_hour * 60 + end_minute) - (start_hour * 60 + start_minute)


def _browser_ajax_post(page: Any, endpoint: str, payload: str) -> tuple[int, str]:
    """Make the text/plain Ajax call from the loaded intranet page itself."""
    result = page.evaluate(
        """async ({ endpoint, payload }) => new Promise((resolve, reject) => {
          const request = new XMLHttpRequest();
          request.open('POST', endpoint, true);
          request.setRequestHeader('Content-Type', 'text/plain;charset=UTF-8');
          request.onload = () => resolve({ status: request.status, text: request.responseText });
          request.onerror = () => reject(new Error('Ajax request failed before a response was received.'));
          request.send(payload);
        })""",
        {"endpoint": endpoint, "payload": payload},
    )
    return result["status"], result["text"]


def interval_is_available(periods: list[str], start: str, end: str) -> bool:
    """Return whether the requested interval is fully contained in one available period."""
    def minutes(value: str) -> int:
        hour, minute = map(int, value.split(":"))
        return hour * 60 + minute

    requested_start, requested_end = minutes(start), minutes(end)
    return any(
        minutes(period_start) <= requested_start and requested_end <= minutes(period_end)
        for period_start, period_end in (period.split("-", maxsplit=1) for period in periods)
    )


def reservation_succeeded(status: int, response_text: str) -> bool:
    """Recognize the observed successful SaveBorrow response contract."""
    return status == 200 and re.search(r"id=(?:\\)?['\"]Borrowed(?:\\)?['\"]", response_text) is not None


def _current_save_borrow_endpoint(page: Any) -> str:
    """Read the deployment-generated SaveBorrow handler from the current authenticated page."""
    script_sources = page.evaluate("""() => [...document.scripts].map(script => script.src).filter(Boolean)""")
    current = urlparse(page.url)
    for source in script_sources:
        handler = urlparse(source)
        if (
            handler.scheme != current.scheme
            or handler.netloc != current.netloc
            or SAVE_BORROW_HANDLER.fullmatch(handler.path) is None
        ):
            continue
        return urlunparse((handler.scheme, handler.netloc, handler.path, "", f"_method=SaveBorrow&_session={AJAX_SESSION}", ""))
    raise RuntimeError("The current authenticated page did not expose a SaveBorrow handler. Run 'dtri-meeting-room login' and try again.")


def _room_itemnos(context: BrowserContext) -> dict[str, str]:
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(MEETING_URL, wait_until="domcontentloaded")
    room_links = page.locator("a[href*='PreviewRoom.aspx']").evaluate_all(
        """links => links.map(link => ({ name: (link.innerText || '').trim(), href: link.href }))"""
    )
    result = {}
    for link in room_links:
        match = ROOM.match(link["name"])
        if not match:
            continue
        itemno = parse_qs(urlparse(link["href"]).query).get("itemno", [None])[0]
        if itemno:
            result[match.group(1)] = itemno
    return result


def prepare_reservation(
    project_root: Path, *, room_number: str, booking_date: str, start: str, end: str, reason: str
) -> ReservationPlan:
    """Refresh the authenticated room map before a user-confirmed submission."""
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(str(profile_path(project_root)), headless=True)
        try:
            itemno = _room_itemnos(context).get(room_number)
            snapshot = snapshot_from_rows(
                _schedule_rows(context), source_url=MEETING_URL, retrieved_at=datetime.now(UTC).isoformat()
            )
        finally:
            context.close()
    if itemno is None:
        raise ValueError(f"Unknown room number: {room_number}")
    requested_date = booking_date.replace("-", "/")
    if requested_date not in snapshot["week_dates"]:
        raise ValueError(f"{booking_date} is not shown in the current weekly schedule")
    room = next(room for room in snapshot["rooms"] if room["id"] == room_number)
    date_index = snapshot["week_dates"].index(requested_date)
    if not interval_is_available(room["available_periods"][date_index], start, end):
        raise ValueError(f"{room_number} is not available for {booking_date} {start}-{end}")
    return ReservationPlan(room_number, itemno, booking_date, start, end, reason)


def submit_reservation(project_root: Path, plan: ReservationPlan) -> tuple[int, str]:
    """Submit a confirmed reservation through the authenticated Playwright profile."""
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(str(profile_path(project_root)), headless=True)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(MEETING_URL, wait_until="domcontentloaded")
            endpoint = _current_save_borrow_endpoint(page)
            for preflight_endpoint, payload, success_marker in reservation_preflight_requests(plan, endpoint):
                check_status, check_text = _browser_ajax_post(page, preflight_endpoint, payload)
                if check_status != 200 or success_marker not in check_text:
                    raise ReservationPreflightFailed(
                        f"{preflight_endpoint.rsplit('_method=', maxsplit=1)[-1].split('&', maxsplit=1)[0]} "
                        f"failed ({check_status}): {' '.join(check_text.split())[:240]}"
                    )
            return _browser_ajax_post(page, endpoint, reservation_payload(plan))
        finally:
            context.close()


def _clean(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def snapshot_from_rows(rows: list[list[str]], *, source_url: str, retrieved_at: str) -> dict[str, Any]:
    """Normalize browser-extracted schedule table rows into the saved snapshot format."""
    header_index = next(
        (index for index, row in enumerate(rows) if sum(bool(DATE.match(_clean(cell))) for cell in row) >= 2),
        None,
    )
    if header_index is None:
        raise AuthenticationRequired("The weekly schedule was not visible; run 'dtri-meeting-room login'.")
    dates = [cell for cell in map(_clean, rows[header_index]) if DATE.match(cell)]
    rooms = []
    seen_room_ids: set[str] = set()
    for row in rows[header_index + 1 :]:
        if not row:
            continue
        match = ROOM.match(_clean(row[0]))
        if not match:
            continue
        room_id, details = match.groups()
        if room_id in seen_room_ids:
            continue
        seen_room_ids.add(room_id)
        rooms.append(
            {
                "id": room_id,
                "name": f"{room_id}會議室",
                "details": details.strip("() "),
                "available_periods": [
                    TIME_RANGE.findall(_clean(row[index + 1]) if index + 1 < len(row) else "")
                    for index in range(len(dates))
                ],
            }
        )
    if not rooms:
        raise AuthenticationRequired("No meeting rooms were visible; run 'dtri-meeting-room login'.")
    return {"retrieved_at": retrieved_at, "source_url": source_url, "week_dates": dates, "rooms": rooms}


def _schedule_rows(context: BrowserContext) -> list[list[str]]:
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(MEETING_URL, wait_until="domcontentloaded")
    rows = page.evaluate(
        """() => {
          const clean = (value) => (value || '').replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim();
          const tables = [...document.querySelectorAll('table')].map((table) => ({
            rows: [...table.querySelectorAll('tr')].map((row) => [...row.cells].map((cell) => clean(cell.innerText))),
          }));
          const candidates = tables.filter(({ rows }) => rows.some((row) => row.filter((cell) => /^\\d{4}\\/\\d{2}\\/\\d{2}$/.test(cell)).length >= 2));
          candidates.sort((left, right) => left.rows.length - right.rows.length);
          return candidates[0]?.rows || [];
        }"""
    )
    return rows


def refresh_snapshot(project_root: Path, *, headless: bool = True) -> dict[str, Any]:
    """Use the isolated persistent profile to capture the current visible schedule."""
    profile = profile_path(project_root)
    profile.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(str(profile), headless=headless)
        try:
            rows = _schedule_rows(context)
        finally:
            context.close()
    return snapshot_from_rows(rows, source_url=MEETING_URL, retrieved_at=datetime.now(UTC).isoformat())


def login_and_refresh(project_root: Path) -> dict[str, Any]:
    """Open the isolated browser for manual login and wait until the schedule is visible."""
    profile = profile_path(project_root)
    profile.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(str(profile), headless=False)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(MEETING_URL, wait_until="domcontentloaded")
            print("Complete login in the opened browser. The schedule will be saved automatically when it appears.")
            page.wait_for_function(
                """() => [...document.querySelectorAll('tr')].some((row) =>
                    [...row.cells].filter((cell) => /^\\d{4}\\/\\d{2}\\/\\d{2}$/.test((cell.innerText || '').trim())).length >= 2
                )""",
                timeout=300_000,
            )
            rows = _schedule_rows(context)
        finally:
            context.close()
    return snapshot_from_rows(rows, source_url=MEETING_URL, retrieved_at=datetime.now(UTC).isoformat())
