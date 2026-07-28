# ruff: noqa: E501

from fastapi.testclient import TestClient

from app.api.fussballde_imports import get_fussballde_client
from app.main import app


class FakeFussballDeSource:
    def fetch_team_matchplan_html(self, team_id: str) -> str:
        assert team_id == "TEAM123"
        return """
        <table><tbody>
          <tr class="row-competition"><td class="column-date">Fr, 07.08.26 | 19:00</td><td class="column-team">Kreispokal</td></tr>
          <tr><td class="column-club">SSV Thönse</td><td class="column-club">FC Burgwedel</td><td><a href="https://www.fussball.de/spiel/ssv-thoense-fc-burgwedel/-/spiel/MATCH1">Zum Spiel</a></td></tr>
        </tbody></table>
        """


def test_matchplan_preview_returns_parsed_fixtures_without_importing_them() -> None:
    app.dependency_overrides[get_fussballde_client] = FakeFussballDeSource
    try:
        with TestClient(app) as client:
            response = client.get("/imports/fussballde/teams/TEAM123/matchplan?limit=1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == [
        {
            "fussballde_id": "MATCH1",
            "played_on": "2026-08-07",
            "kickoff_time": "19:00:00",
            "competition": "Kreispokal",
            "home_team": "SSV Thönse",
            "away_team": "FC Burgwedel",
            "report_url": "https://www.fussball.de/spiel/ssv-thoense-fc-burgwedel/-/spiel/MATCH1",
        }
    ]
