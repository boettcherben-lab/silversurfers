"""Small, explicit HTTP client for public FUSSBALL.DE lineup endpoints."""

from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

_SOURCE_ID_PATTERN = re.compile(r"[A-Z0-9]+")
_USER_AGENT = "Festspielmonitor/0.1 (private club eligibility monitor)"


class FussballDeFetchError(RuntimeError):
    """Raised when a public FUSSBALL.DE resource cannot be retrieved."""


class FussballDeClient:
    """Fetch a single, public FUSSBALL.DE resource with bounded request behavior."""

    def __init__(
        self,
        http_client: httpx.Client | None = None,
        *,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            base_url="https://www.fussball.de",
            headers={"User-Agent": _USER_AGENT},
            timeout=timeout_seconds,
            follow_redirects=True,
        )

    def close(self) -> None:
        """Close the internally created client, if any."""
        if self._owns_client:
            self._client.close()

    def fetch_lineup_html(self, match_id: str) -> str:
        """Return the public lineup fragment for one FUSSBALL.DE match ID."""
        if _SOURCE_ID_PATTERN.fullmatch(match_id) is None:
            raise ValueError("match_id must consist only of uppercase letters and digits")

        path = f"/ajax.match.lineup/-/mode/PAGE/spiel/{match_id}"
        return self._fetch_html(path, f"lineup for match {match_id}")

    def fetch_match_course_html(self, match_id: str) -> str:
        """Return the public match course, including substitutions, for one match."""
        if _SOURCE_ID_PATTERN.fullmatch(match_id) is None:
            raise ValueError("match_id must consist only of uppercase letters and digits")

        path = f"/ajax.match.course/-/mode/PAGE/spiel/{match_id}"
        return self._fetch_html(path, f"match course for match {match_id}")

    def fetch_team_matchplan_html(self, team_id: str) -> str:
        """Return the public match-plan fragment for one explicitly selected team."""
        if _SOURCE_ID_PATTERN.fullmatch(team_id) is None:
            raise ValueError("team_id must consist only of uppercase letters and digits")

        path = f"/ajax.team.matchplan/-/mode/PAGE/team-id/{team_id}"
        return self._fetch_html(path, f"match plan for team {team_id}")

    def fetch_previous_games_html(self, team_id: str) -> str:
        """Return the bounded public list of recently completed games for one team."""
        if _SOURCE_ID_PATTERN.fullmatch(team_id) is None:
            raise ValueError("team_id must consist only of uppercase letters and digits")

        path = f"/ajax.team.prev.games/-/team-id/{team_id}"
        return self._fetch_html(path, f"previous games for team {team_id}")

    def fetch_player_profile_html(self, profile_url: str) -> str:
        """Return one public player-profile page after validating its FUSSBALL.DE origin."""
        parsed_url = urlparse(profile_url)
        if parsed_url.scheme != "https" or parsed_url.netloc != "www.fussball.de":
            raise ValueError("profile_url must be an HTTPS URL on www.fussball.de")
        if not parsed_url.path.startswith("/spielerprofil/"):
            raise ValueError("profile_url must point to a FUSSBALL.DE player profile")

        return self._fetch_html(profile_url, "player profile")

    def _fetch_html(self, url: str, resource_name: str) -> str:
        try:
            response = self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise FussballDeFetchError(f"Could not fetch {resource_name}") from error

        return response.text
