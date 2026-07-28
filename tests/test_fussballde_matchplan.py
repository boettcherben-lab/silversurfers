# ruff: noqa: E501

from datetime import date, time

from app.scrapers.fussballde_matchplan import parse_team_matchplan_html


def test_parse_team_matchplan_html_extracts_fixture_metadata() -> None:
    html = """
    <table><tbody>
      <tr class="odd row-competition hidden-small">
        <td class="column-date"><span>Fr, 07.08.26 |</span>19:00</td>
        <td colspan="3" class="column-team"><a>Kreispokal</a></td>
      </tr>
      <tr class="odd">
        <td class="column-club"><a href="https://www.fussball.de/mannschaft/-/team-id/OPPONENT1"><div class="club-name">SSV Thönse</div></a></td>
        <td class="column-colon">:</td>
        <td class="column-club"><a href="https://www.fussball.de/mannschaft/-/team-id/TEAM123"><div class="club-name">FC Burgwedel</div></a></td>
        <td class="column-score"><a href="https://www.fussball.de/spiel/ssv-thoense-fc-burgwedel/-/spiel/MATCH1">Zum Spiel</a></td>
      </tr>
      <tr class="even row-competition hidden-small">
        <td class="column-date"><span>Fr, 14.08.26 |</span>20:00</td>
        <td colspan="3" class="column-team"><a>1. Kreisklasse</a></td>
      </tr>
      <tr class="even">
        <td class="column-club"><a><div class="club-name">FC Burgwedel</div></a></td>
        <td class="column-colon">:</td>
        <td class="column-club"><a><div class="club-name">SP Hannover 1</div></a></td>
        <td class="column-score"><a href="https://www.fussball.de/spiel/fc-burgwedel-sp-hannover-1/-/spiel/MATCH2">Zum Spiel</a></td>
      </tr>
    </tbody></table>
    """

    matches = parse_team_matchplan_html(html)

    assert matches[0].fussballde_id == "MATCH1"
    assert matches[0].played_on == date(2026, 8, 7)
    assert matches[0].kickoff_time == time(19, 0)
    assert matches[0].competition == "Kreispokal"
    assert matches[0].home_team == "SSV Thönse"
    assert matches[0].away_team == "FC Burgwedel"
    assert matches[0].away_team_fussballde_id == "TEAM123"
    assert matches[1].fussballde_id == "MATCH2"
    assert matches[1].competition == "1. Kreisklasse"
