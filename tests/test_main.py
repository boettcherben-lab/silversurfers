from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app import main
from app.database import create_sqlite_engine


def test_startup_creates_schema_and_health_check_works(tmp_path, monkeypatch) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'startup.db'}")
    monkeypatch.setattr(main, "engine", engine)

    with TestClient(main.app) as client:
        response = client.get("/health")
        cors_response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert cors_response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert set(inspect(engine).get_table_names()) == {
        "appearances",
        "matches",
        "players",
        "team_sync_statuses",
        "teams",
    }
