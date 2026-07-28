from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, create_sqlite_engine
from app.models import Appearance, Player, Team
from app.services.fussballde_import import MatchImport
from app.services.fussballde_sync import sync_match


class FakeFussballDeSource:
    def __init__(self, lineup_html: str, profile_html_by_url: dict[str, str]) -> None:
        self.lineup_html = lineup_html
        self.profile_html_by_url = profile_html_by_url
        self.fetched_profile_urls: list[str] = []

    def fetch_lineup_html(self, match_id: str) -> str:
        assert match_id == "match-1"
        return self.lineup_html

    def fetch_player_profile_html(self, profile_url: str) -> str:
        self.fetched_profile_urls.append(profile_url)
        return self.profile_html_by_url[profile_url]


def test_sync_match_imports_only_monitored_team_with_resolved_names(tmp_path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'sync.db'}")
    Base.metadata.create_all(bind=engine)
    fixture_directory = Path(__file__).parent / "fixtures"
    lineup_html = (fixture_directory / "fussballde_lineup.html").read_text(encoding="utf-8")

    profile_html_by_url = {
        "https://www.fussball.de/spielerprofil/-/player-id/HOME_CAPTAIN": (
            "<title>Maik Fischer Basisprofil | FUSSBALL.DE</title>"
        ),
        "https://www.fussball.de/spielerprofil/-/player-id/HOME_STARTER": (
            "<title>Christian Goldenstein Basisprofil | FUSSBALL.DE</title>"
        ),
        "https://www.fussball.de/spielerprofil/-/player-id/HOME_SUB": (
            "<title>Thomas Martens Basisprofil | FUSSBALL.DE</title>"
        ),
    }
    source = FakeFussballDeSource(lineup_html, profile_html_by_url)

    with Session(engine) as session:
        session.add(Team(name="FC Burgwedel Ü40 I", fussballde_id="higher-team"))
        session.commit()

        match = sync_match(
            session,
            source,
            MatchImport(
                fussballde_id="match-1",
                team_fussballde_id="higher-team",
                monitored_team_side="home",
                played_on=date(2026, 8, 7),
                competition="Kreispokal",
                home_team="FC Burgwedel",
                away_team="SSV Thönse",
                finished=True,
                is_competitive=True,
            ),
        )
        session.commit()

        assert match.id is not None
        assert session.scalars(select(Player).order_by(Player.name)).all()
        assert len(session.scalars(select(Appearance)).all()) == 3
        assert source.fetched_profile_urls == list(profile_html_by_url)
