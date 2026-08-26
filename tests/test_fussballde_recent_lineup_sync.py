# ruff: noqa: E501

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, create_sqlite_engine
from app.models import Appearance, Match, Team
from app.services.fussballde_recent_lineup_sync import sync_recent_higher_team_lineups


class FakeRecentLineupSource:
    def __init__(
        self,
        lineup_html: str,
        match_course_html: str,
        profile_html_by_url: dict[str, str],
    ) -> None:
        self.lineup_html = lineup_html
        self.match_course_html = match_course_html
        self.profile_html_by_url = profile_html_by_url
        self.profile_requests = 0

    def fetch_previous_games_html(self, team_id: str) -> str:
        assert team_id == "TEAM123"
        return """
        <table><tbody>
          <tr class="row-competition"><td class="column-date">Fr, 07.08.26 | 19:00</td><td class="column-team">Kreispokal</td></tr>
          <tr><td class="column-club"><a href="/mannschaft/-/team-id/TEAM123">FC Burgwedel</a></td><td class="column-club"><a href="/mannschaft/-/team-id/OPPONENT1">SSV Thönse</a></td><td><a href="https://www.fussball.de/spiel/-/spiel/MATCH1">Zum Spiel</a></td></tr>
          <tr class="row-competition"><td class="column-date">Fr, 14.08.26 | 20:00</td><td class="column-team">Freundschaftsspiel</td></tr>
          <tr><td class="column-club">FC Burgwedel</td><td class="column-club">Gastverein</td><td><a href="https://www.fussball.de/spiel/-/spiel/FRIENDLY1">Zum Spiel</a></td></tr>
        </tbody></table>
        """

    def fetch_lineup_html(self, match_id: str) -> str:
        assert match_id == "MATCH1"
        return self.lineup_html

    def fetch_match_course_html(self, match_id: str) -> str:
        assert match_id == "MATCH1"
        return self.match_course_html

    def fetch_player_profile_html(self, profile_url: str) -> str:
        self.profile_requests += 1
        return self.profile_html_by_url[profile_url]


def test_recent_lineup_sync_imports_new_completed_match_once(tmp_path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'recent-lineups.db'}")
    Base.metadata.create_all(bind=engine)
    fixture_directory = Path(__file__).parent / "fixtures"
    source = FakeRecentLineupSource(
        (fixture_directory / "fussballde_lineup.html").read_text(encoding="utf-8"),
        (fixture_directory / "fussballde_match_course.html").read_text(encoding="utf-8"),
        {
            "https://www.fussball.de/spielerprofil/-/player-id/HOME_CAPTAIN": (
                "<title>Maik Fischer Basisprofil | FUSSBALL.DE</title>"
            ),
            "https://www.fussball.de/spielerprofil/-/player-id/HOME_STARTER": (
                "<title>Christian Goldenstein Basisprofil | FUSSBALL.DE</title>"
            ),
            "https://www.fussball.de/spielerprofil/-/player-id/HOME_SUB": (
                "<title>Thomas Martens Basisprofil | FUSSBALL.DE</title>"
            ),
        },
    )

    with Session(engine) as session:
        session.add(Team(name="FC Burgwedel Ü40 I", fussballde_id="TEAM123"))
        session.commit()

        first_summary = sync_recent_higher_team_lineups(
            session,
            source,
            team_fussballde_id="TEAM123",
        )
        session.commit()
        second_summary = sync_recent_higher_team_lineups(
            session,
            source,
            team_fussballde_id="TEAM123",
        )

        match = session.scalar(select(Match).where(Match.fussballde_id == "MATCH1"))
        appearances = session.scalars(select(Appearance)).all()

    assert first_summary.imported == 1
    assert first_summary.ignored == 1
    assert second_summary.already_imported == 1
    assert source.profile_requests == 6
    assert match is not None and match.finished is True
    assert len(appearances) == 3
