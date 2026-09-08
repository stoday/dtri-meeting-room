from dtri_meeting_room.browser import _current_save_borrow_endpoint


class Page:
    url = "https://intranet.example/default.aspx"

    def evaluate(self, _script: str) -> list[str]:
        return [
            "AjaxPro.endpoint = '/ajax/_Default,App_Web_generated.ashx?_method=SaveBorrow&_session=rw';"
        ]


def test_save_borrow_endpoint_is_read_from_the_current_page() -> None:
    assert _current_save_borrow_endpoint(Page()) == (
        "https://intranet.example/ajax/_Default,App_Web_generated.ashx?_method=SaveBorrow&_session=rw"
    )
