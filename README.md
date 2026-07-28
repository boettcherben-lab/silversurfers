# festspielmonitor

Monorepo für den **Festspielmonitor**: eine FastAPI-Anwendung mit React-/Vite-Frontend.

## Struktur

```
festspielmonitor/
├── app/                    # FastAPI-Anwendung
├── tests/                  # Backend-Tests
├── frontend/               # React, Vite, TypeScript, Tailwind
├── .github/workflows/      # GitHub Actions CI
├── pyproject.toml          # Python-Abhängigkeiten und Tool-Konfiguration
└── package.json            # Befehle für das Frontend aus dem Projektwurzelverzeichnis
```

## Voraussetzungen

- Python 3.12
- Node.js 22 oder neuer (inklusive npm)

## Einrichtung

Aus dem Projektwurzelverzeichnis in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
npm install --prefix frontend
```

## Entwicklung starten

Terminal 1 – Frontend:

```powershell
npm run dev
```

Terminal 2 – Backend:

```powershell
uvicorn app.main:app --reload
```

Die API-Gesundheitsprüfung ist unter `http://127.0.0.1:8000/health` verfügbar; die interaktive API-Dokumentation unter `http://127.0.0.1:8000/docs`.

Das Dashboard unter dem Vite-Server zeigt das nächste Pflichtspiel und die berechneten
Spielerstatus. Es verwendet standardmäßig die lokale API auf `http://127.0.0.1:8000` und
die höhere Mannschaft mit lokaler ID `1`. Für eine abweichende Installation können
`VITE_API_URL` und `VITE_HIGHER_TEAM_ID` gesetzt werden.

### Manueller FUSSBALL.DE-Import

Die API bietet einen kontrollierten Endpunkt für **ein** ausdrücklich angegebenes Spiel:

```
POST /imports/fussballde/matches/{fussballde_match_id}
```

Er erscheint in der lokalen API-Dokumentation unter `http://127.0.0.1:8000/docs`. Der
Endpunkt benötigt die Spielmetadaten im Request-Body und führt keinen automatischen Import,
Zeitplan oder Massendownload aus.

### FUSSBALL.DE-Spielplanvorschau

Der folgende read-only Endpunkt lädt ausschließlich den Spielplan einer ausdrücklich
angegebenen FUSSBALL.DE-Team-ID und speichert nichts in SQLite:

```
GET /imports/fussballde/teams/{team_fussballde_id}/matchplan?limit=10
```

Die Vorschau enthält Datum, Anstoßzeit, Wettbewerb, Paarung, Spiel-ID und den Link zum
Spielbericht. Sie ist die Grundlage, um später gezielt einzelne Pflichtspiele zu importieren.

Mit einem bewusst manuell ausgelösten `POST` auf dieselbe URL werden nur Liga-, Pokal- und
Relegationsspiele als Spielmetadaten in SQLite übernommen. Freundschafts- und Testspiele
werden übersprungen; Aufstellungen werden dabei nicht abgerufen.

### Aufstellung eines geplanten Spiels importieren

Nach einem ausgetragenen Spiel genügt die lokale Spiel-ID; die Spielmetadaten werden aus
SQLite übernommen:

```
POST /matches/{match_id}/lineup
```

Der Request-Body enthält nur noch optional die beiden Tore. Die Heim-/Gastseite der
überwachten Mannschaft stammt aus den FUSSBALL.DE-Team-IDs des importierten Spielplans. Sie
kann bei unvollständigen Altdaten einmalig über `monitored_team_side` (`home` oder `away`)
angegeben werden. Der Import lädt Aufstellung und Spielernamen, markiert das Spiel als
ausgetragen und aktualisiert die Einsatzhistorie. Er soll erst verwendet werden, wenn ein
öffentlicher Spielbericht verfügbar ist.

### Täglicher FUSSBALL.DE-Abgleich

Der tägliche Abgleich ist absichtlich standardmäßig deaktiviert. Für eine laufende API-Instanz
wird er durch diese Umgebungsvariablen aktiviert:

```powershell
$env:FUSSBALLDE_MATCHPLAN_SYNC_ENABLED = "true"
$env:FUSSBALLDE_HIGHER_TEAM_ID = "02PN6IOCF4000000VS5489B2VT4FEOV2"
$env:FUSSBALLDE_LOWER_TEAM_ID = "0312NHLIUC000000VS5489BRVVV10ESU"
$env:FUSSBALLDE_MATCHPLAN_SYNC_HOUR = "4"
$env:FUSSBALLDE_MATCHPLAN_SYNC_MINUTE = "0"
uvicorn app.main:app --reload
```

Die Anwendung führt dann täglich um 04:00 Uhr lokaler Serverzeit genau einen begrenzten,
idempotenten Abgleich aus. Sie aktualisiert die Spielpläne beider Ü40-Mannschaften und prüft
für die zuletzt ausgetragenen Pflichtspiele der ersten Ü40, ob eine öffentliche Aufstellung
verfügbar ist. Neue Aufstellungen werden samt Einsatz- und Rückennummerndaten übernommen;
Freundschaftsspiele bleiben ausgeschlossen. Sie startet keinen Abruf sofort beim Hochfahren
und beendet die Hintergrundaufgabe beim Herunterfahren sauber.

### Öffentliche GitHub-Pages-Version

Der Workflow `.github/workflows/pages.yml` macht das Dashboard ohne dauerhaft laufenden Server
öffentlich. Er nutzt die versionsgesicherte Datei `data/festspielmonitor.db` als kleinen,
dauerhaften Datenbestand, führt den FUSSBALL.DE-Abgleich täglich um 02:17 UTC aus, erzeugt eine
statische Dashboard-Datei und veröffentlicht das React-Frontend auf GitHub Pages.

Vor dem ersten Lauf muss in den Repository-Einstellungen unter **Pages** als Quelle
**GitHub Actions** ausgewählt werden. Für eine vollständig kostenlose Veröffentlichung muss das
Repository öffentlich sein. Anschließend kann der Workflow unter **Actions** über
**Synchronize and publish dashboard** einmal manuell gestartet werden.

Die erzeugte Website ist unter `https://<github-name>.github.io/<repository-name>/` erreichbar.
Der grüne Aktualisierungspunkt im Dashboard zeigt nur dann den aktuellen Tag, wenn der
Synchronisationslauf erfolgreich war.

### Importierte Daten lesen

Nach einem erfolgreichen Import stehen die lokalen Daten über diese Endpunkte bereit:

```
GET /matches
GET /matches/{match_id}
```

Der Detail-Endpunkt enthält die gespeicherte Einsatzliste der überwachten Mannschaft.

### Berechnete Spielberechtigung

Für eine höhere Mannschaft mit lokaler Datenbank-ID kann der Status aller Spieler mit
relevanter Einsatzhistorie abgefragt werden:

```
GET /teams/{team_id}/eligibility?as_of=2026-08-15&lower_team_distance=1
```

`as_of` ist optional und verwendet sonst den heutigen Tag. `lower_team_distance=1` steht für
die nächstniedrigere Mannschaft. Der Endpunkt speichert keinen Status, sondern berechnet ihn
für jeden Aufruf neu aus den lokal importierten Pflichtspielen.

Das nächste lokal gespeicherte Pflichtspiel der höheren Mannschaft ist über
`GET /teams/{team_id}/next-match` abrufbar.

### NFV-Regelengine

Der Festspielstatus wird nicht in der Datenbank abgelegt. Die reine Fachlogik in
`app/rules/nfv.py` berechnet ihn anhand ausgetragener Pflichtspiele. Beim manuellen Import
muss jedes Spiel deshalb mit `is_competitive` gekennzeichnet werden; Meisterschaft und Pokal
sind Pflichtspiele, Freundschaftsspiele nicht. Details stehen in
[`docs/nfv-rule-engine.md`](docs/nfv-rule-engine.md).

## Datenbank und Startdaten

Beim Start der API werden die SQLite-Tabellen automatisch in `festspielmonitor.db` angelegt. Um den ersten Verein anzulegen, führe aus:

```powershell
python -m app.seed
```

Das Skript ist wiederholbar und legt `FC Burgwedel Ü40 I` nicht doppelt an.

## Qualitätssicherung

```powershell
ruff check .
pytest
npm run lint
npm run format:check
npm run build
```

Die GitHub-Actions-Workflow führt diese Lint- und Test-/Build-Schritte für Pushes und Pull Requests aus.
