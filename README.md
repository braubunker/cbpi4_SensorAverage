# cbpi4_SensorAverage

CraftBeerPi4-Plugin mit:

1. **`AveragingSensor`** – Mittelwert über mehrere Messungen eines Quellsensors + Logging für Charts  
2. **Sensor-Chart-Seite** – eigene Chart-UI mit einstellbarer Zeitlinie und Mittelwert unter `/sensorchart`

## Installation (empfohlen)

Auf dem Raspberry Pi / CBPi-Host:

```bash
pipx runpip cbpi4 uninstall cbpi4_SensorAverage
pipx runpip cbpi4 install https://github.com/braubunker/cbpi4_SensorAverage/archive/main.zip
sudo systemctl restart craftbeerpi
```

Repo: https://github.com/braubunker/cbpi4_SensorAverage

### Ältere CBPi-Versionen (Plugin-Liste in config.yaml)

Ab CBPi ~4.1+ werden Pakete mit Namen `cbpi…` automatisch geladen.  
Auf sehr alten Installationen zusätzlich aktivieren:

```bash
cd ~/cbpi   # bzw. dein Config-Ordner mit config/config.yaml
cbpi add cbpi4_SensorAverage
# alternativ manuell in config/config.yaml unter plugins: eintragen
sudo systemctl restart craftbeerpi
```

### Installation prüfen

```bash
pipx runpip cbpi4 list | grep -i sensor
```

Erwartet: Zeile mit `cbpi4_SensorAverage` / `1.0.3`.

Nach dem Neustart in den CBPi-Logs:

```bash
journalctl -u craftbeerpi -n 200 --no-pager | grep -iE 'SensorAverage|AveragingSensor|SensorChart|FAILED'
# oder manuell: cbpi start
```

Erfolgreich:

- `Try to load plugin: cbpi4_SensorAverage == 1.0.3`
- `Registered AveragingSensor`
- `Plugin cbpi4_SensorAverage loaded successfully`

Optional (Chart):

- `SensorChartEndpoint mounted at /sensorchart`

Wenn nur die Chart-Zeile fehlt/fehlschlägt, erscheint `AveragingSensor` trotzdem unter Hardware → Sensors.

Chart:

```text
http://<PI-IP>:8000/sensorchart/
```

Zeitlinie (Dropdown): 1h, 6h, 12h, 24h, 48h, 7 Tage, **14 Tage**, 30 Tage — plus optional benutzerdefinierte Stunden.
API: `GET /sensorchart/api/chart?sensor_id=…&hours=336` (beliebige Stunden, z.B. 14 Tage = 336).

### Optional: lokal aus Clone (nur für Entwickler)

Nur nötig, wenn du das Repo selbst geklont hast. **Nicht** `.` oder einen Beispielpfad wörtlich kopieren, wenn du nicht im Clone-Verzeichnis bist:

```bash
git clone https://github.com/braubunker/cbpi4_SensorAverage.git
cd cbpi4_SensorAverage
pipx runpip cbpi4 install .
sudo systemctl restart craftbeerpi
```

## AveragingSensor anlegen

Hardware → Sensor → **+** → Typ **`AveragingSensor`**

| Parameter | Bedeutung |
|-----------|-----------|
| **SourceSensor** | Quellsensor (Waage, Druck, Temp, …) |
| **SampleInterval** | Sekunden zwischen Einzelmessungen (z.B. `5`) |
| **AverageCount** | Anzahl Messungen für den Mittelwert (z.B. `10`) |
| **AverageMethod** | `mean` / `median` / `min` / `max` |
| **StartDelay** | Sekunden warten vor der ersten Messung (`0` = sofort) |
| **RequireFullWindow** | `Yes` = erst ausgeben, wenn `AverageCount` Messungen da sind |
| **LogInterval** | Sekunden zwischen Chart-Log-Punkten (z.B. `60`; `0` = bei jedem Mittelwert) |
| **LogData** | `Yes` = CSV loggen (nötig für Charts) |

## Dashboard & Charts

Ja – der AveragingSensor kann später auf dem Dashboard angezeigt werden:

1. Sensor anlegen mit **LogData = Yes**
2. Dashboard → Widget **Sensor Data** → AveragingSensor wählen (Live-Wert)
3. Dashboard → Widget **Chart** → denselben AveragingSensor wählen (Historie)
4. Zusätzlich: Analytics → Sensor → Chart, oder `http://<PI-IP>:8000/sensorchart/`

## Entwicklung / Tests

Die Mittelwert-Logik ist ohne laufendes CraftBeerPi testbar:

```bash
cd cbpi4_SensorAverage
python3 -m pip install pytest
python3 -m pytest -q
```

## Changelog

* **1.0.3** – Chart-Zeitlinie: 14 Tage (336h) und 30 Tage (720h) im Dropdown; optional benutzerdefinierte Stunden. API/`filter_hours` akzeptiert weiterhin beliebige `hours`.
* **1.0.2** – Setup robuster: `AveragingSensor` wird **immer zuerst** registriert; Chart/`CBPiExtension` wird separat gemountet und kann den Sensor-Typ nicht mehr blockieren. Docs: Pi-Logs, Reinstall, Dashboard.
* **1.0.1** – Packaging an CBPi4-Konvention angeglichen (`pyproject.toml` nur Build-Backend; Metadaten in `setup.py`), damit `pipx runpip cbpi4 install …/archive/main.zip` zuverlässig baut
* **1.0.0** – Eigenständiges Plugin: `AveragingSensor` + Chart-Seite `/sensorchart` (aus `cbpi4_BrewStart` ausgelagert)
