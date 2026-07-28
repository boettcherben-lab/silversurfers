from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    fussballde_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

    matches: Mapped[list[Match]] = relationship(back_populates="team", cascade="all, delete-orphan")
    sync_status: Mapped[TeamSyncStatus | None] = relationship(
        back_populates="team", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:
        return f"Team(id={self.id!r}, name={self.name!r})"


class TeamSyncStatus(Base):
    """Last successful FUSSBALL.DE match-plan synchronization for a team."""

    __tablename__ = "team_sync_statuses"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), unique=True, index=True)
    last_successful_sync_at: Mapped[datetime] = mapped_column()

    team: Mapped[Team] = relationship(back_populates="sync_status")

    def __repr__(self) -> str:
        return (
            "TeamSyncStatus("
            f"team_id={self.team_id!r}, last_successful_sync_at={self.last_successful_sync_at!r}"
            ")"
        )


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    fussballde_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    played_on: Mapped[date] = mapped_column(Date, index=True)
    kickoff_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    competition: Mapped[str] = mapped_column(String(120))
    home_team: Mapped[str] = mapped_column(String(120))
    away_team: Mapped[str] = mapped_column(String(120))
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_url: Mapped[str | None] = mapped_column(String(500), unique=True, nullable=True)
    finished: Mapped[bool] = mapped_column(Boolean, default=False)
    is_competitive: Mapped[bool] = mapped_column(Boolean, default=False)
    monitored_team_side: Mapped[str | None] = mapped_column(String(4), nullable=True)

    team: Mapped[Team] = relationship(back_populates="matches")
    appearances: Mapped[list[Appearance]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            "Match("
            f"id={self.id!r}, home_team={self.home_team!r}, away_team={self.away_team!r}, "
            f"played_on={self.played_on!r}"
            ")"
        )


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    fussballde_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    display_name: Mapped[str | None] = mapped_column(String(160), nullable=True)

    appearances: Mapped[list[Appearance]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Player(id={self.id!r}, name={self.name!r})"


class Appearance(Base):
    __tablename__ = "appearances"
    __table_args__ = (UniqueConstraint("player_id", "match_id", name="uq_appearance_player_match"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    starter: Mapped[bool] = mapped_column(Boolean, default=False)
    captain: Mapped[bool] = mapped_column(Boolean, default=False)
    jersey_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    player: Mapped[Player] = relationship(back_populates="appearances")
    match: Mapped[Match] = relationship(back_populates="appearances")

    def __repr__(self) -> str:
        return (
            "Appearance("
            f"id={self.id!r}, player_id={self.player_id!r}, match_id={self.match_id!r}"
            ")"
        )
