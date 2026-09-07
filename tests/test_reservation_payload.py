from p2026_meeting_room.browser import (
    ReservationPlan,
    interval_is_available,
    reservation_preflight_requests,
    reservation_payload,
    reservation_succeeded,
)


def test_reservation_payload_uses_observed_plain_text_wire_format() -> None:
    plan = ReservationPlan("201", "22", "2026-09-08", "09:00", "09:30", "工作進度討論", "https://example.test/save")
    assert reservation_payload(plan) == (
        "itemno=22\r\nborrow_date=2026/09/08\r\nstarttime=09:00\r\nendtime=09:30\r\n"
        "reason=工作進度討論\r\ncnt=0\r\nf_company=\r\nf_name=\r\nf_chk=false"
    )


def test_success_contract_requires_status_and_borrowed_table() -> None:
    assert reservation_succeeded(200, '<table id="Borrowed"></table>')
    assert reservation_succeeded(200, r"'\<table id=\'Borrowed\'\></table>'")
    assert not reservation_succeeded(200, "rule rejected")
    assert not reservation_succeeded(500, '<table id="Borrowed"></table>')


def test_requested_interval_must_fit_an_available_period() -> None:
    periods = ["09:00-11:00", "12:00-20:00"]
    assert interval_is_available(periods, "11:00", "11:30") is False
    assert interval_is_available(periods, "10:30", "11:00") is True
    assert interval_is_available(periods, "12:00", "12:30") is True


def test_preflight_replays_the_observed_rule_checks_and_duration() -> None:
    plan = ReservationPlan(
        "1002",
        "119",
        "2026-09-11",
        "09:30",
        "10:00",
        "reason",
        "https://intranet.example/ajax/_Default,App_Web_generated.ashx?_method=SaveBorrow&_session=rw",
    )
    checks = reservation_preflight_requests(plan)
    assert [marker for _, _, marker in checks] == ["Rule1_Allow", "Rules2_Allow", "Rule1_Allow", "Rules2_Allow"]
    assert checks[0][1] == "borrow_date=2026/09/11"
    assert checks[1][1].endswith("estmin=0")
    assert checks[3][1].endswith("estmin=30")


def test_preflight_uses_the_saveborrow_session_value_for_each_rule_check() -> None:
    plan = ReservationPlan(
        "1002", "119", "2026-09-11", "09:30", "10:00", "reason",
        "https://intranet.example/ajax/_Default,App_Web_generated.ashx?_method=SaveBorrow&_session=custom",
    )
    assert all("_session=custom" in endpoint for endpoint, _, _ in reservation_preflight_requests(plan))
