from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import Team

SEED_TEAM_NAME = "FC Burgwedel Ü40 I"
SEED_TEAM_FUSSBALLDE_ID = "02PN6IOCF4000000VS5489B2VT4FEOV2"
SEED_LOWER_TEAM_NAME = "FC Burgwedel Ü40 II"
SEED_LOWER_TEAM_FUSSBALLDE_ID = "0312NHLIUC000000VS5489BRVVV10ESU"


def seed_team(session: Session) -> Team:
    """Create the initial team once and return the existing/new record."""
    team = session.scalar(select(Team).where(Team.name == SEED_TEAM_NAME))
    if team is not None:
        return team

    team = Team(name=SEED_TEAM_NAME, fussballde_id=SEED_TEAM_FUSSBALLDE_ID)
    session.add(team)
    session.flush()
    return team


def seed_lower_team(session: Session) -> Team:
    """Create the monitored lower team once and return it."""
    team = session.scalar(select(Team).where(Team.name == SEED_LOWER_TEAM_NAME))
    if team is not None:
        return team

    team = Team(
        name=SEED_LOWER_TEAM_NAME,
        fussballde_id=SEED_LOWER_TEAM_FUSSBALLDE_ID,
    )
    session.add(team)
    session.flush()
    return team


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        team = seed_team(session)
        lower_team = seed_lower_team(session)
        session.commit()
        print(f"Seeded {team.name} (id={team.id}) and {lower_team.name} (id={lower_team.id})")


if __name__ == "__main__":
    main()
