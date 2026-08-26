"""Parser for publicly rendered FUSSBALL.DE lineup fragments.

The source renders player names through a webfont. This parser intentionally extracts only
stable player profile IDs and lineup metadata; profile-name resolution is a separate concern.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Literal
from urllib.parse import urljoin

TeamSide = Literal["home", "away"]

_PLAYER_PROFILE_PATTERN = re.compile(r"/spielerprofil/-/(?:player-id|userid)/([^/?#]+)")
_JERSEY_NUMBER_PATTERN = re.compile(r"(?<!\d)(\d{1,2})(?!\d)")
_CAPTAIN_PATTERN = re.compile(r"(?:^|\s)C(?:\s|$)")
_FUSSBALLDE_BASE_URL = "https://www.fussball.de"


@dataclass(frozen=True, slots=True)
class LineupEntry:
    """One player listed in a FUSSBALL.DE lineup or on its bench."""

    fussballde_id: str
    side: TeamSide
    starter: bool
    captain: bool
    jersey_number: int | None
    profile_url: str = ""
    appeared: bool = False


@dataclass(slots=True)
class _ActivePlayer:
    href: str
    side: TeamSide
    starter: bool
    text_parts: list[str]


class _LineupHTMLParser(HTMLParser):
    """Extract player cards from a rendered FUSSBALL.DE lineup fragment."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[LineupEntry] = []
        self._active_player: _ActivePlayer | None = None
        self._in_heading = False
        self._heading_parts: list[str] = []
        self._on_bench = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "h3":
            self._in_heading = True
            self._heading_parts = []
            return

        if tag != "a" or self._active_player is not None:
            return

        classes = set((attributes.get("class") or "").split())
        profile_url = attributes.get("href") or ""
        if "player-wrapper" not in classes or not _PLAYER_PROFILE_PATTERN.search(profile_url):
            return

        if "home" in classes:
            side: TeamSide = "home"
        elif "away" in classes:
            side = "away"
        else:
            return

        self._active_player = _ActivePlayer(
            href=profile_url,
            side=side,
            starter=not self._on_bench,
            text_parts=[],
        )

    def handle_data(self, data: str) -> None:
        if self._in_heading:
            self._heading_parts.append(data)
        if self._active_player is not None:
            self._active_player.text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h3" and self._in_heading:
            heading = " ".join(self._heading_parts).strip().casefold()
            self._on_bench = heading == "ersatzbank"
            self._in_heading = False
            self._heading_parts = []
            return

        if tag != "a" or self._active_player is None:
            return

        active_player = self._active_player
        self._active_player = None
        profile_match = _PLAYER_PROFILE_PATTERN.search(active_player.href)
        if profile_match is None:
            return

        player_text = " ".join(active_player.text_parts)
        jersey_numbers = _JERSEY_NUMBER_PATTERN.findall(player_text)
        self.entries.append(
            LineupEntry(
                fussballde_id=profile_match.group(1),
                side=active_player.side,
                starter=active_player.starter,
                captain=bool(_CAPTAIN_PATTERN.search(player_text)),
                jersey_number=int(jersey_numbers[-1]) if jersey_numbers else None,
                profile_url=urljoin(_FUSSBALLDE_BASE_URL, active_player.href),
                appeared=active_player.starter,
            )
        )


def parse_lineup_html(html: str) -> list[LineupEntry]:
    """Parse a FUSSBALL.DE lineup fragment into stable player metadata.

    The function accepts a rendered lineup fragment, not an entire match page. It does not
    request network resources and is therefore suitable for fixture-based tests.
    """
    parser = _LineupHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.entries


class _MatchCourseHTMLParser(HTMLParser):
    """Extract players brought on from the public match-course fragment."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.substituted_player_ids: set[str] = set()
        self._open_tags: list[str] = []
        self._row_depth: int | None = None
        self._row_player_ids: list[str] = []
        self._row_is_substitution = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        self._open_tags.append(tag)
        classes = set((attributes.get("class") or "").split())

        if tag == "div" and "row-event" in classes:
            self._row_depth = len(self._open_tags)
            self._row_player_ids = []
            self._row_is_substitution = False
        elif self._row_depth is not None and "icon-substitute" in classes:
            self._row_is_substitution = True
        elif tag == "a" and self._row_depth is not None:
            profile_match = _PLAYER_PROFILE_PATTERN.search(attributes.get("href") or "")
            if profile_match is not None:
                self._row_player_ids.append(profile_match.group(1))

    def handle_endtag(self, tag: str) -> None:
        if (
            tag == "div"
            and self._row_depth is not None
            and len(self._open_tags) == self._row_depth
        ):
            if self._row_is_substitution:
                self.substituted_player_ids.update(self._row_player_ids)
            self._row_depth = None
            self._row_player_ids = []
            self._row_is_substitution = False

        if self._open_tags:
            self._open_tags.pop()


def parse_substituted_player_ids(html: str) -> set[str]:
    """Return FUSSBALL.DE IDs of players brought on during a match.

    The lineup lists the full bench; the match course identifies which of those players were
    actually substituted on. A player in the starting eleven does not need to appear here.
    """
    parser = _MatchCourseHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.substituted_player_ids
