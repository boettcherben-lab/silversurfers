# ruff: noqa: E501

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.fussballde_imports import get_fussballde_client
from app.database import Base, create_sqlite_engine, get_session
from app.main import app
from app.models import Match, Team


class FakeFussballDeSource:
    def fetch_team_matchplan_html(self, team_id: str) -> str:
        assert team_id == "TEAM123"
        return """
        <table><tbody>
          <tr class="row-competition"><td class="column-date">Fr, 07.08.26 | 19:00</td><td class="column-team">Kreispokal</td></tr>
          <tr><td class="column-club">SSV Thönse</td><td class="column-club">FC Burgwedel</td><td><a href="https://www.fussball.de/spiel/ssv-thoense-fc-burgwedel/-/spiel/MATCH1">Zum Spiel</a></td></tr>
          <tr class="row-competition"><td class="column-date">Fr, 14.08.26 | 20:00</td><td class="column-team">Kreisfreundschaftsspiele</td></tr>
          <tr><td class="column-club">FC Burgwedel</td><td class="column-club">Gastverein</td><td><a href="https://www.fussball.de/spiel/fc-burgwedel-gastverein/-/spiel/FRIENDLY1">Zum Spiel</a></td></tr>
        </tbody></table>
        """


def test_matchplan_import_endpoint_stores_only_relevant_fixtures(tmp_path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'matchplan-import-api.db'}")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        session.add(Team(name="FC Burgwedel Ü40 I", fussballde_id="TEAM123"))
        session.commit()

    app.dependency_overrides[get_session] = lambda: Session(engine)
    app.dependency_overrides[get_fussballde_client] = FakeFussballDeSource
    try:
        with TestClient(app) as client:
            response = client.post("/imports/fussballde/teams/TEAM123/matchplan")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"created": 1, "updated": 0, "skipped": 1}
    with Session(engine) as session:
        assert session.scalars(select(Match)).one().fussballde_id == "MATCH1"
