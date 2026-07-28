"""Parser for the public FUSSBALL.DE team match-plan fragment."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, time
from html.parser import HTMLParser

_MATCH_ID_PATTERN = re.compile(r"/-/spiel/([A-Z0-9]+)")
_TEAM_ID_PATTERN = re.compile(r"/team-id/([A-Z0-9]+)")
_DATE_PATTERN = re.compile(r"(\d{2})\.(\d{2})\.(\d{2,4})")
_TIME_PATTERN = re.compile(r"\b(\d{1,2}:\d{2})\b")


@dataclass(frozen=True, slots=True)
class ScheduledMatch:
    """One fixture exposed in FUSSBALL.DE's rendered team match plan."""

    fussballde_id: str
    played_on: date
    kickoff_time: time | None
    competition: str
    home_team: str
    away_team: str
    report_url: str
    home_team_fussballde_id: str | None = None
    away_team_fussballde_id: str | None = None


@dataclass(slots=True)
class _Cell:
    classes: set[str]
    text_parts: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(self.text_parts).strip()


class _MatchPlanHTMLParser(HTMLParser):
    """Associate a competition/date row with the fixture row immediately following it."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.matches: list[ScheduledMatch] = []
        self._row_classes: set[str] | None = None
        self._cells: list[_Cell] = []
        self._active_cell: _Cell | None = None
        self._links: list[str] = []
        self._pending_date: date | None = None
        self._pending_time: time | None = None
        self._pending_competition: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "tr":
            self._row_classes = set((attributes.get("class") or "").split())
            self._cells = []
            self._active_cell = None
            self._links = []
        elif tag == "td" and self._row_classes is not None:
            self._active_cell = _Cell(set((attributes.get("class") or "").split()))
        elif tag == "a" and self._row_classes is not None:
            href = attributes.get("href")
            if href is not None:
                self._links.append(href)
                if self._active_cell is not None:
                    self._active_cell.links.append(href)

    def handle_data(self, data: str) -> None:
        if self._active_cell is not None:
            self._active_cell.text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._active_cell is not None:
            self._cells.append(self._active_cell)
            self._active_cell = None
        elif tag == "tr" and self._row_classes is not None:
            self._finish_row()
            self._row_classes = None
            self._cells = []
            self._links = []

    def _finish_row(self) -> None:
        if "row-competition" in self._row_classes:
            self._set_pending_competition()
        elif self._pending_date is not None and self._pending_competition is not None:
            self._append_fixture()

    def _set_pending_competition(self) -> None:
        date_text = self._cell_text("column-date")
        competition = self._cell_text("column-team")
        parsed_date = _parse_date(date_text)
        if parsed_date is None or not competition:
            self._pending_date = None
            self._pending_time = None
            self._pending_competition = None
            return

        self._pending_date = parsed_date
        self._pending_time = _parse_time(date_text)
        self._pending_competition = competition

    def _append_fixture(self) -> None:
        club_cells = [cell for cell in self._cells if "column-club" in cell.classes and cell.text]
        report_url = next((url for url in self._links if _MATCH_ID_PATTERN.search(url)), None)
        if len(club_cells) != 2 or report_url is None:
            return

        match_id = _MATCH_ID_PATTERN.search(report_url)
        if match_id is None:
            return

        self.matches.append(
            ScheduledMatch(
                fussballde_id=match_id.group(1),
                played_on=self._pending_date,
                kickoff_time=self._pending_time,
                competition=self._pending_competition,
                home_team=club_cells[0].text,
                away_team=club_cells[1].text,
                report_url=report_url,
                home_team_fussballde_id=_team_id_from_links(club_cells[0].links),
                away_team_fussballde_id=_team_id_from_links(club_cells[1].links),
            )
        )

    def _cell_text(self, class_name: str) -> str:
        return next((cell.text for cell in self._cells if class_name in cell.classes), "")


def parse_team_matchplan_html(html: str) -> list[ScheduledMatch]:
    """Parse a rendered public team match plan without performing network requests."""
    parser = _MatchPlanHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.matches


def _parse_date(value: str) -> date | None:
    match = _DATE_PATTERN.search(value)
    if match is None:
        return None

    day, month, year = (int(part) for part in match.groups())
    if year < 100:
        year += 2000
    return date(year, month, day)


def _parse_time(value: str) -> time | None:
    match = _TIME_PATTERN.search(value)
    return time.fromisoformat(match.group(1)) if match is not None else None


def _team_id_from_links(links: list[str]) -> str | None:
    for link in links:
        match = _TEAM_ID_PATTERN.search(link)
        if match is not None:
            return match.group(1)
    return None
