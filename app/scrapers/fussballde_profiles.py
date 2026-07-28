"""Parser for publicly rendered FUSSBALL.DE player-profile pages."""

from __future__ import annotations

import re
from html.parser import HTMLParser

_PROFILE_TITLE_PATTERN = re.compile(
    r"^(?P<name>.+?)\s+(?:Basisprofil|Spielerprofil)\s*\|\s*FUSSBALL\.DE$",
    re.IGNORECASE,
)
_TEAM_SUFFIX_PATTERN = re.compile(r"\s+\([^()]+\)$")


class _TitleHTMLParser(HTMLParser):
    """Read only the document title from an HTML page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._in_title = True

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    @property
    def title(self) -> str:
        return " ".join(self._title_parts).strip()


def parse_player_profile_name(html: str) -> str | None:
    """Extract the public player name from a FUSSBALL.DE profile page.

    Some profiles add the current team in parentheses before the fixed FUSSBALL.DE title
    suffix. The team suffix is intentionally removed because player identity is represented
    by the stable FUSSBALL.DE profile ID.
    """
    parser = _TitleHTMLParser()
    parser.feed(html)
    parser.close()

    title_match = _PROFILE_TITLE_PATTERN.fullmatch(parser.title)
    if title_match is None:
        return None

    return _TEAM_SUFFIX_PATTERN.sub("", title_match.group("name")).strip()
