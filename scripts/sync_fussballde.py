"""Run the configured FUSSBALL.DE synchronization once without starting the web server."""

from app.services.daily_matchplan_sync import run_configured_matchplan_sync
from app.settings import MatchplanSyncSettings


def main() -> None:
    settings = MatchplanSyncSettings.from_environment()
    run_configured_matchplan_sync(settings)


if __name__ == "__main__":
    main()
