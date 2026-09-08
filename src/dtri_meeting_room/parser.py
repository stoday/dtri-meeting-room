"""Parse the intranet's weekly meeting-room table of available periods."""

from __future__ import annotations

from html.parser import HTMLParser
import re
from typing import Any


TIME_RANGE = re.compile(r"\b\d{2}:\d{2}-\d{2}:\d{2}\b")
DATE = re.compile(r"^\d{4}/\d{2}/\d{2}$")
ROOM = re.compile(r"^(\d+)\s*會議室\s*(.*)$")


class _TableTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._table_depth = 0
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            if self._table is None:
                self._table = []
            self._table_depth += 1
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []
        elif tag == "br" and self._cell is not None:
            self._cell.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append("".join(self._cell))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self._table_depth -= 1
            if self._table_depth == 0:
                self.tables.append(self._table)
                self._table = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def _clean(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def parse_weekly_html(html: str, *, source_url: str, retrieved_at: str) -> dict[str, Any]:
    """Return normalized rooms and available slots from a weekly-page HTML export."""
    parser = _TableTextParser()
    parser.feed(html)
    for table in parser.tables:
        header_index = next(
            (index for index, row in enumerate(table) if sum(bool(DATE.match(_clean(cell))) for cell in row) >= 2),
            None,
        )
        if header_index is None:
            continue
        dates = [cell for cell in map(_clean, table[header_index]) if DATE.match(cell)]
        rooms = []
        for row in table[header_index + 1 :]:
            if not row:
                continue
            label = _clean(row[0])
            match = ROOM.match(label)
            if not match:
                continue
            room_id, details = match.groups()
            available_periods = [TIME_RANGE.findall(_clean(row[index + 1]) if index + 1 < len(row) else "") for index, _date in enumerate(dates)]
            rooms.append({"id": room_id, "name": f"{room_id}會議室", "details": details.strip("() "), "available_periods": available_periods})
        if rooms:
            return {"retrieved_at": retrieved_at, "source_url": source_url, "week_dates": dates, "rooms": rooms}
    raise ValueError("The export did not contain a recognizable weekly meeting-room table.")
