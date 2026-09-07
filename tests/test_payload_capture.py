from p2026_meeting_room.browser import summarize_form_payload


def test_form_summary_redacts_web_forms_state_but_keeps_semantic_fields() -> None:
    assert summarize_form_payload("room=801&start=14%3A00&__VIEWSTATE=secret&remark=planning") == [
        {"name": "room", "value": "801"},
        {"name": "start", "value": "14:00"},
        {"name": "__VIEWSTATE", "value": "[REDACTED]"},
        {"name": "remark", "value": "planning"},
    ]


def test_form_summary_parses_plain_text_newline_delimited_payload() -> None:
    assert summarize_form_payload("itemno=22\r\nstarttime=09:00\r\n__VIEWSTATE=secret") == [
        {"name": "itemno", "value": "22"},
        {"name": "starttime", "value": "09:00"},
        {"name": "__VIEWSTATE", "value": "[REDACTED]"},
    ]
