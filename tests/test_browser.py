from dtri_meeting_room.browser import snapshot_from_rows


def test_snapshot_from_rows_extracts_rooms_and_periods() -> None:
    snapshot = snapshot_from_rows(
        [
            ["會議室", "2026/09/07", "2026/09/08"],
            ["201會議室 (容納:6人)", "09:00-10:00 12:00-13:00", ""],
        ],
        source_url="https://example.test/",
        retrieved_at="2026-09-07T00:00:00+00:00",
    )
    assert snapshot["week_dates"] == ["2026/09/07", "2026/09/08"]
    assert snapshot["rooms"] == [
        {
            "id": "201",
            "name": "201會議室",
            "details": "容納:6人",
            "available_periods": [["09:00-10:00", "12:00-13:00"], []],
        }
    ]
