import pytest

from app.settings import MatchplanSyncSettings


def test_matchplan_sync_settings_are_opt_in_and_configurable(monkeypatch) -> None:
    monkeypatch.setenv("FUSSBALLDE_MATCHPLAN_SYNC_ENABLED", "true")
    monkeypatch.setenv("FUSSBALLDE_HIGHER_TEAM_ID", "TEAM123")
    monkeypatch.setenv("FUSSBALLDE_LOWER_TEAM_ID", "TEAM456")
    monkeypatch.setenv("FUSSBALLDE_MATCHPLAN_SYNC_HOUR", "5")
    monkeypatch.setenv("FUSSBALLDE_MATCHPLAN_SYNC_MINUTE", "30")

    settings = MatchplanSyncSettings.from_environment()

    assert settings == MatchplanSyncSettings(True, "TEAM123", "TEAM456", 5, 30)
    assert settings.team_fussballde_ids == ("TEAM123", "TEAM456")


def test_matchplan_sync_settings_reject_invalid_time(monkeypatch) -> None:
    monkeypatch.setenv("FUSSBALLDE_MATCHPLAN_SYNC_HOUR", "24")

    with pytest.raises(ValueError, match="valid hour"):
        MatchplanSyncSettings.from_environment()
