import httpx
import pytest

from app.scrapers.fussballde_client import FussballDeClient, FussballDeFetchError

USER_AGENT = "Festspielmonitor/0.1 (private club eligibility monitor)"


def test_fetch_lineup_html_requests_the_public_lineup_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/ajax.match.lineup/-/mode/PAGE/spiel/MATCH123"
        assert request.headers["user-agent"] == USER_AGENT
        return httpx.Response(200, text="<section>lineup</section>")

    http_client = httpx.Client(
        base_url="https://www.fussball.de",
        headers={"User-Agent": USER_AGENT},
        transport=httpx.MockTransport(handler),
    )
    client = FussballDeClient(http_client)

    assert client.fetch_lineup_html("MATCH123") == "<section>lineup</section>"


def test_fetch_match_course_html_requests_the_public_match_course_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/ajax.match.course/-/mode/PAGE/spiel/MATCH123"
        return httpx.Response(200, text="<section>match course</section>")

    http_client = httpx.Client(
        base_url="https://www.fussball.de",
        transport=httpx.MockTransport(handler),
    )
    client = FussballDeClient(http_client)

    assert client.fetch_match_course_html("MATCH123") == "<section>match course</section>"


def test_fetch_lineup_html_raises_a_domain_error_for_http_failures() -> None:
    http_client = httpx.Client(
        base_url="https://www.fussball.de",
        transport=httpx.MockTransport(lambda request: httpx.Response(503, request=request)),
    )
    client = FussballDeClient(http_client)

    with pytest.raises(FussballDeFetchError, match="MATCH123"):
        client.fetch_lineup_html("MATCH123")


def test_fetch_lineup_html_rejects_invalid_match_ids() -> None:
    client = FussballDeClient(httpx.Client(transport=httpx.MockTransport(lambda request: None)))

    with pytest.raises(ValueError, match="uppercase"):
        client.fetch_lineup_html("match-123")


def test_fetch_team_matchplan_html_requests_the_public_matchplan_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/ajax.team.matchplan/-/mode/PAGE/team-id/TEAM123"
        return httpx.Response(200, text="<table>match plan</table>")

    http_client = httpx.Client(
        base_url="https://www.fussball.de",
        transport=httpx.MockTransport(handler),
    )
    client = FussballDeClient(http_client)

    assert client.fetch_team_matchplan_html("TEAM123") == "<table>match plan</table>"


def test_fetch_previous_games_html_requests_the_bounded_history_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/ajax.team.prev.games/-/team-id/TEAM123"
        return httpx.Response(200, text="<table>previous games</table>")

    http_client = httpx.Client(
        base_url="https://www.fussball.de",
        transport=httpx.MockTransport(handler),
    )
    client = FussballDeClient(http_client)

    assert client.fetch_previous_games_html("TEAM123") == "<table>previous games</table>"


def test_fetch_player_profile_html_rejects_non_fussballde_urls() -> None:
    client = FussballDeClient(httpx.Client(transport=httpx.MockTransport(lambda request: None)))

    with pytest.raises(ValueError, match="www.fussball.de"):
        client.fetch_player_profile_html("https://example.test/spielerprofil/-/player-id/PLAYER1")
