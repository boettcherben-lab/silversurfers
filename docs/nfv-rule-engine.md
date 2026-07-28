# NFV-Regelengine

`app.rules.nfv.NFVEligibilityCalculator` ist reine Fachlogik: Sie kennt weder die Datenbank
noch FUSSBALL.DE noch HTTP. Ein Festspielstatus wird nie gespeichert, sondern aus der
Einsatzhistorie zum angefragten Stichtag berechnet.

## Berücksichtigte Spiele

In die Berechnung fließen ausschließlich Spiele ein, die zum Stichtag ausgetragen
(`finished=True`) und als Pflichtspiel (`is_competitive=True`) markiert sind. Meisterschafts-
und Pokalspiele werden beim Import als Pflichtspiele markiert; Freundschaftsspiele nicht.
Die Kennzeichnung wird ausdrücklich gespeichert und nicht aus dem Wettbewerbsnamen geraten.

## Saisonwechsel

Die historische Einsatz- und Rückennummernhistorie bleibt in der Datenbank erhalten. Für die
Festspielberechnung beginnt eine neue Saison jedoch am 1. Juli: Einsätze vor diesem Datum
werden für den Status der neuen Saison nicht herangezogen. Dadurch starten die Spieler ohne
laufende Festspielbindung in die neue Saison, bleiben aber weiterhin im Dashboard sichtbar.

## Ergebnis

- `eligible`: Der Spieler ist spielberechtigt.
- `at_risk`: Ein Einsatz im nächsten ausgetragenen Pflichtspiel der höheren Mannschaft würde
  ihn festspielen.
- `locked`: Der Spieler ist festgespielt. `matches_to_skip` nennt die noch nötigen
  aufeinanderfolgenden Pflichtspiele der höheren Mannschaft. Nach dem letzten notwendigen
  Aussetzen enthält `eligible_on` den Folgetag, ab dem er spielberechtigt ist.

Für die nächstniedrigere Mannschaft (`lower_team_distance=1`) sind zwei Aussetzer nötig.
Für jede weitere niedrigere Ebene erhöht sich die Anzahl um ein weiteres Spiel.
