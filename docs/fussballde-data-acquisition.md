# FUSSBALL.DE-Datenbeschaffung: Analyse und Entscheidungsvorlage

Stand: 28. Juli 2026

## Ziel dieses Schritts

Dieser Schritt untersucht ausschließlich die Datenquellen und die Risiken einer späteren
Importfunktion. Es wird bewusst noch kein Scraper implementiert.

## Verifizierte öffentliche Daten

Die öffentliche Vereinsseite des FC Burgwedel stellt Mannschaftsseiten, Spielpläne,
Wettbewerbe, Ergebnisse und Verweise auf einzelne Spiele bereit. Eine Spielplanzeile
enthält unter anderem Datum, Uhrzeit, Wettbewerb, Heim- und Auswärtsteam sowie eine
Spielnummer. Die Seite kennzeichnet zudem, ob ein Spielbericht vorhanden ist.

Die FUSSBALL.DE-FAQ und weitere offizielle Hinweise zeigen: Spielberichte und
Spieleraufstellungen werden nur angezeigt, wenn die jeweiligen Daten zur Veröffentlichung
freigegeben sind. Deshalb muss der Import damit umgehen können, dass ein abgeschlossenes
Spiel keine öffentlich sichtbare Aufstellung hat.

## Nicht als Grundlage verwenden

`api-fussball.de` ist ein Drittanbieter und laut eigener Dokumentation ein Crawler. Er
erfordert einen Token und begrenzt Anfragen. Die dokumentierten Team-Endpunkte umfassen
Spielplan- und Ergebnisdaten, nicht aber verlässlich die für die Festspielregel nötigen
Aufstellungen. Diese API wird daher nicht zur Primärquelle des Projekts.

## Rechtlicher und organisatorischer Rahmen

FUSSBALL.DE weist darauf hin, dass Spiel- und Aufstellungsdaten aus der DFBnet-Datenbank
stammen. Die normale Auswertung ist laut Impressum auf private Nutzung beschränkt;
wiederholtes oder systematisches Vervielfältigen auch kleiner Datenmengen außerhalb der
normalen Auswertung ist ohne Zustimmung nicht zulässig.

**Konsequenz:** Vor einem automatisierten Regelbetrieb benötigen wir eine ausdrückliche
Erlaubnis beziehungsweise eine vom DFB/NFV freigegebene Schnittstelle. Bis dahin darf die
Anwendung nur für einen eng begrenzten, privaten Vereinszweck entwickelt und getestet
werden. Es werden keine fremden Wettbewerbsdaten gesammelt oder veröffentlicht.

## Bestätigte Konfiguration: FC Burgwedel, Saison 2026/2027

Die folgenden von der Projektleitung bereitgestellten Mannschaftsseiten wurden im Browser
geprüft:

| Rolle | Mannschaft | FUSSBALL.DE-Team-ID | Wettbewerb |
| --- | --- | --- | --- |
| höhere Mannschaft | FC Burgwedel | `02PN6IOCF4000000VS5489B2VT4FEOV2` | Senioren Ü 40 1.KK, Staffel 2 |
| überwachte Mannschaft | FC Burgwedel II | `0312NHLIUC000000VS5489BRVVV10ESU` | Senioren Ü40 2.Kreisklasse |

Beide Seiten enthalten öffentliche Spielplan-Endpunkte unter
`/ajax.team.next.games`, `/ajax.team.prev.games` und `/ajax.team.matchplan` mit der
jeweiligen Team-ID. Diese Endpunkte sind ein beobachtetes Seitenimplementierungsdetail,
keine dokumentierte oder zugesicherte Programmierschnittstelle.

## Beobachtung zum FC Burgwedel

Die öffentliche Vereinsseite ist saisonabhängig. In der aktuell angezeigten Saison werden
nicht zwingend dieselben Mannschaften gezeigt wie in vergangenen Saisons. Für die fachliche
Konfiguration darf daher weder aus dem Namen noch aus der Vereinsseite eine feste
Mannschaftsreihenfolge abgeleitet werden.

Die Team-IDs und die Saison 2026/2027 sind jetzt festgelegt. Die Konfiguration sollte
später nicht aus dem Anzeigenamen abgeleitet, sondern explizit gespeichert werden.

## Spielbericht-Prüfung

Als Referenz wurde das Spiel `FC Burgwedel – Heesseler SV`
(`02TQJ8PIA4000000VS5489BTVV0LE4BT`) geprüft. Die Spieldetailseite verlinkt eine eigene
öffentliche Aufstellungsansicht unter `/ajax.match.lineup/-/mode/PAGE/spiel/{spiel-id}`.
Sie enthält die Aufstellungen, Ersatzbänke, Trikotnummern und Kennzeichen wie Kapitän.

Die technische Prüfung hat eine wichtige Besonderheit gezeigt: In der Roh-HTML-/DOM-Ansicht
sind Spielernamen mit einem Webfont obfuskiert. Die visuellen FUSSBALL.DE-Seiten zeigen sie
lesbar, der Parser darf jedoch nicht davon ausgehen, dass `textContent` die Klarnamen
liefert. Stabil verfügbar sind die Profil-URLs mit Spielerkennung, die Teamseite
(Heim/Gast), Rückennummern und Statuskennzeichen.

**Folge:** Der Parser-Prototyp wird zuerst die stabile Spielerkennung und die
Einsatzmerkmale extrahieren. Die Namensauflösung wird als eigener, testbarer Schritt
behandelt. Ein fehlender Aufstellungs-Endpunkt bleibt weiterhin ein fachlicher Zustand
`lineup_unavailable` und bedeutet nicht „Spieler nicht eingesetzt“.

## Empfohlene technische Architektur

Ein späterer Importer bekommt eine klar abgegrenzte Schnittstelle, zum Beispiel
`FussballDeClient`, mit folgenden Verantwortlichkeiten:

1. Mannschaftsseite abrufen und Spiel-URLs/Spielnummern erkennen.
2. Nur noch neue oder geänderte Spiele abrufen; Spielnummer oder Bericht-URL als
   Quellschlüssel verwenden.
3. Spielbericht in einen unabhängigen Datentransfer-Typ überführen.
4. Erst danach per Datenbank-Service in `Match`, `Player` und `Appearance` speichern.

Wichtige Stabilitätsregeln:

- strikte Zeitlimits und eindeutiger User-Agent;
- niedrige Rate, Cache und kein paralleles Massenauslesen;
- Fehler pro Spiel dokumentieren, ohne den gesamten Import abzubrechen;
- fehlende Aufstellungen als fachlichen Zustand behandeln, nicht als leere Aufstellung;
- Roh-HTML nicht dauerhaft speichern, solange Rechtsgrundlage und Speicherfrist nicht
  geklärt sind;
- Parser-Tests ausschließlich mit anonymisierten, lokal abgelegten Test-Fixtures.

## Datenvertrag für den späteren Parser

Der Parser sollte mindestens diese Informationen liefern können:

- stabile Quell-ID oder Bericht-URL;
- Datum und Abschlussstatus;
- Wettbewerb und Kennzeichen Pflichtspiel/Freundschaftsspiel;
- Heim- und Auswärtsteam, Ergebnis;
- eingesetzte Spieler sowie Starter-, Kapitäns- und Rückennummerninformation, soweit
  öffentlich vorhanden.

Erst wenn ein echter Spielbericht gegen diesen Vertrag geprüft wurde, werden die konkreten
CSS-Selektoren oder API-Aufrufe festgelegt.

### Fachliche Klassifikation für die NFV-Regel

Für den Festspielmonitor sind Meisterschafts- **und Pokalspiele** Pflichtspiele. Beide
fließen deshalb in die Folgen von Einsätzen und Aussetzern ein. Freundschaftsspiele,
Testspiele und abgesetzte beziehungsweise nicht ausgetragene Spiele dürfen nicht zählen.

Der spätere Importer speichert diese Entscheidung explizit pro Spiel. Er darf nicht allein
aus einem Ergebnis oder dem Wort „Spiel" im Seitentitel ableiten, ob ein Pflichtspiel
vorliegt.

## Entscheidung für den nächsten Schritt

Kein produktiver Scraper wird implementiert, bevor die Nutzungsfreigabe geklärt ist. Der
nächste technische Schritt ist ein Fixture-basierter Parser-Prototyp für **eine** manuell
freigegebene Spielberichtseite mit tatsächlich öffentlich sichtbarer Aufstellung.

## Umsetzungsstand: lokaler Aufstellungsparser

Der Parser-Prototyp liegt in `app/scrapers/fussballde.py`. Er arbeitet ausschließlich mit
lokalen HTML-Fixtures und extrahiert pro Spieler:

- FUSSBALL.DE-Spielerkennung aus der Profil-URL;
- Heim-/Gastseite;
- Startelf oder Ersatzbank;
- Rückennummer und Kapitänskennzeichen, soweit vorhanden.

Er speichert noch nichts in SQLite und ruft keine FUSSBALL.DE-URL ab. Die Namensauflösung
über Spielerprofile sowie der spätere Import-Service sind bewusst nachgelagerte Schritte.

Die Namensauflösung ist inzwischen als zweiter lokaler Baustein in
`app/scrapers/fussballde_profiles.py` umgesetzt. Sie liest den Namen aus dem Seitentitel
eines gespeicherten Spielerprofil-HTMLs und entfernt einen optionalen Mannschaftszusatz.
Der Live-Abruf und die Datenbankübernahme bleiben weiterhin separate Schritte.

Ein lokaler Importservice ist nun in `app/services/fussballde_import.py` verfügbar. Er
übernimmt bereits geparste Daten idempotent in `Match`, `Player` und `Appearance`. Dabei
werden ausschließlich Aufstellungseinträge der konfigurierten Mannschaftsseite importiert;
gegnerische Spieler bleiben außerhalb der lokalen Einsatzhistorie. Der Service führt keine
Netzwerkzugriffe aus und überlässt die Transaktion bewusst dem aufrufenden Code.

Der begrenzte Abrufzugang liegt in `app/scrapers/fussballde_client.py`. Er ruft ausschließlich
die öffentliche Aufstellungsroute für eine explizite Spiel-ID ab, setzt einen eindeutigen
User-Agent, verwendet ein Timeout und übersetzt HTTP-Fehler in eine projektspezifische
Ausnahme. Automatische Abrufe, Wiederholungen und ein Zeitplan sind bewusst noch nicht
implementiert.

Die Kette wird durch `app/services/fussballde_sync.py` koordiniert: Aufstellung abrufen,
Profilnamen für die überwachte Mannschaft auflösen und die Daten in SQLite importieren. Sie
verarbeitet stets genau eine explizit übergebene Spiel-ID, erstellt keinen Zeitplan und führt
keine Massendownloads durch. Ein Fake-Client testet diese gesamte Kette ohne Live-Zugriff.

Für die lokale, manuelle Auslösung stellt `app/api/fussballde_imports.py` den FastAPI-Endpunkt
`POST /imports/fussballde/matches/{fussballde_match_id}` bereit. Der Request enthält die
bekannten Spielmetadaten und die überwachte Teamseite. Er ist keine Hintergrundaufgabe und
startet niemals einen Import für weitere Spiele.

## Umsetzungsstand: Spielplanvorschau

`app/scrapers/fussballde_matchplan.py` parst den öffentlich gerenderten Mannschaftsspielplan
in eine unabhängige `ScheduledMatch`-Struktur. Sie enthält Spiel-ID, Datum, Anstoßzeit,
Wettbewerb, Paarung und Bericht-Link. Der Parser nutzt nur lokale Test-Fixtures.

Der begrenzte Client-Abruf und der read-only Endpunkt
`GET /imports/fussballde/teams/{team_fussballde_id}/matchplan` liefern eine explizit
angeforderte, begrenzte Vorschau. Diese Funktion schreibt keine Datenbankzeilen und startet
keinen automatischen Abruf weiterer Spielberichte.

## Umsetzungsstand: begrenzter Spielplan-Import

Ein manueller `POST` auf dieselbe Spielplan-URL übernimmt nur Spielmetadaten für Liga-,
Pokal- und Relegationswettbewerbe. Freundschafts-, Test- und Turnierspiele werden vor dem
Speichern übersprungen. Der Import bleibt idempotent und überschreibt weder bereits
importierte Ergebnisse noch Einsatzlisten. Aufstellungen sind ausdrücklich nicht Teil dieses
Schritts.

## Umsetzungsstand: täglicher Abgleich

Die FastAPI-Anwendung kann den begrenzten Spielplanimport einmal täglich für genau eine
explizit konfigurierte höhere Mannschaft ausführen. Die Funktion ist opt-in und ohne die
Umgebungsvariable `FUSSBALLDE_MATCHPLAN_SYNC_ENABLED=true` vollständig deaktiviert. Sie ruft
nicht beim Start der Anwendung ab, sondern erst zur konfigurierten lokalen Uhrzeit.

Der Abgleich verwendet denselben idempotenten Importservice wie der manuelle Endpunkt.
Dadurch werden Spielplanänderungen aktualisiert, ohne Ergebnisse oder bereits importierte
Einsatzhistorien zu überschreiben.

## Umsetzungsstand: Aufstellungen aus lokalem Spielplan

Für ein bereits im lokalen Spielplan gespeichertes und ausgetragenes Pflichtspiel kann
`POST /matches/{match_id}/lineup` die Aufstellung abrufen. Der Aufrufer übergibt nur noch die
optional das Ergebnis; Datum, Wettbewerb, Spiel-ID, Pflichtspiel-Kennzeichen und die
Heim-/Gastseite der überwachten Mannschaft stammen aus der lokalen Datenbank. Die
Heim-/Gastseite wird beim Spielplanimport über die FUSSBALL.DE-Team-IDs abgeleitet.

Der Endpunkt ist weiterhin manuell und auf genau ein Spiel begrenzt. Er markiert das Spiel
erst nach erfolgreicher Aufstellungsübernahme als ausgetragen. Ein nicht vorhandener
öffentlicher Spielbericht wird nicht als leere Aufstellung interpretiert.

Importierte Daten sind über die read-only Endpunkte `GET /matches` und
`GET /matches/{match_id}` einsehbar. Der Detail-Endpunkt liefert die lokale Einsatzliste und
den Link zum ursprünglichen Spielbericht, sofern dieser beim Import übergeben wurde.
