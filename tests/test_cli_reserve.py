from argparse import Namespace

from dtri_meeting_room import cli
from dtri_meeting_room.browser import ReservationPlan


def test_confirm_yes_submits_with_default_reason_without_prompt(monkeypatch) -> None:
    plan = ReservationPlan("801", "12", "2026-09-11", "10:00", "10:30", cli.DEFAULT_RESERVATION_REASON, "https://example.test")
    prepared: list[dict[str, object]] = []
    submitted: list[ReservationPlan] = []

    monkeypatch.setattr(cli, "prepare_reservation", lambda _root, **kwargs: (prepared.append(kwargs), plan)[1])
    monkeypatch.setattr(cli, "submit_reservation", lambda _root, submitted_plan: (submitted.append(submitted_plan), (200, '<table id="Borrowed">'))[1])
    monkeypatch.setattr(cli, "reservation_succeeded", lambda status, body: status == 200 and "Borrowed" in body)
    monkeypatch.setattr("builtins.input", lambda _prompt: (_ for _ in ()).throw(AssertionError("input must not be called")))

    cli._reserve(Namespace(room_id="801", date="2026-09-11", period=("10:00", "10:30"), confirm="YES", reason=None))

    assert prepared == [{"room_number": "801", "booking_date": "2026-09-11", "start": "10:00", "end": "10:30", "reason": cli.DEFAULT_RESERVATION_REASON}]
    assert submitted == [plan]


def test_confirm_yes_uses_provided_reason_without_prompt(monkeypatch) -> None:
    reason = "客戶訪談"
    plan = ReservationPlan("801", "12", "2026-09-11", "10:00", "10:30", reason, "https://example.test")
    prepared: list[dict[str, object]] = []

    monkeypatch.setattr(cli, "prepare_reservation", lambda _root, **kwargs: (prepared.append(kwargs), plan)[1])
    monkeypatch.setattr(cli, "submit_reservation", lambda _root, _plan: (200, '<table id="Borrowed">'))
    monkeypatch.setattr(cli, "reservation_succeeded", lambda _status, _body: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: (_ for _ in ()).throw(AssertionError("input must not be called")))

    cli._reserve(Namespace(room_id="801", date="2026-09-11", period=("10:00", "10:30"), confirm="YES", reason=reason))

    assert prepared[0]["reason"] == reason
