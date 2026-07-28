"""Export the locally calculated dashboard data as a static JSON document."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Match, Team, TeamSyncStatus
from app.services.eligibility import calculate_team_eligibilities


def _serialize_match(match: Match | None) -> dict[str, str | int | None] | None:
    if match is None:
        return None
    return {
        "id": match.id,
        "fussballde_id": match.fussballde_id,
        "played_on": match.played_on.isoformat(),
        "kickoff_time": match.kickoff_time.isoformat() if match.kickoff_time else None,
        "competition": match.competition,
        "home_team": match.home_team,
        "away_team": match.away_team,
        "report_url": match.report_url,
    }


def _next_match(session, *, team_id: int, as_of: date) -> Match | None:
    return session.scalar(
        select(Match)
        .where(
            Match.team_id == team_id,
            Match.is_competitive.is_(True),
            Match.finished.is_(False),
            Match.played_on >= as_of,
        )
        .order_by(Match.played_on, Match.kickoff_time.is_(None), Match.kickoff_time, Match.id)
    )


def build_dashboard_payload(
    *,
    higher_team_id: int,
    lower_team_id: int,
    as_of: date | None = None,
) -> dict[str, object]:
    """Build the public static representation consumed by the React dashboard."""
    calculation_date = as_of or date.today()
    with SessionLocal() as session:
        higher_team, eligibilities = calculate_team_eligibilities(
            session,
            team_id=higher_team_id,
            as_of=calculation_date,
        )
        if higher_team is None:
            raise ValueError(f"Unknown higher team ID: {higher_team_id}")
        if session.get(Team, lower_team_id) is None:
            raise ValueError(f"Unknown lower team ID: {lower_team_id}")

        sync_status = session.scalar(
            select(TeamSyncStatus).where(TeamSyncStatus.team_id == higher_team_id)
        )
        return {
            "next_higher_match": _serialize_match(
                _next_match(session, team_id=higher_team_id, as_of=calculation_date)
            ),
            "next_lower_match": _serialize_match(
                _next_match(session, team_id=lower_team_id, as_of=calculation_date)
            ),
            "eligibility": {
                "team_name": higher_team.name,
                "as_of": calculation_date.isoformat(),
                "players": [
                    {
                        "player_id": item.player.id,
                        "player_name": item.player.display_name or item.player.name,
                        "jersey_number": item.preferred_jersey_number,
                        "status": item.result.status.value,
                        "matches_to_skip": item.result.matches_to_skip,
                        "eligible_on": (
                            item.result.eligible_on.isoformat()
                            if item.result.eligible_on is not None
                            else None
                        ),
                    }
                    for item in eligibilities
                ],
            },
            "sync_status": {
                "last_successful_sync_at": (
                    sync_status.last_successful_sync_at.isoformat() if sync_status else None
                )
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--higher-team-id", type=int, default=1)
    parser.add_argument("--lower-team-id", type=int, default=2)
    arguments = parser.parse_args()

    payload = build_dashboard_payload(
        higher_team_id=arguments.higher_team_id,
        lower_team_id=arguments.lower_team_id,
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
