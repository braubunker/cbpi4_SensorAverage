# cbpi4_SensorAverage

CraftBeerPi4-Plugin mit:

1. **`AveragingSensor`** – Mittelwert über mehrere Messungen eines Quellsensors + Logging für Charts  
2. **Sensor-Chart-Seite** – eigene Chart-UI mit einstellbarer Zeitlinie und Mittelwert unter `/sensorchart`

## Installation

Direkt vom GitHub-Repo (auf dem Pi):

```bash
pipx runpip cbpi4 install https://github.com/braubunker/cbpi4_SensorAverage/archive/main.zip
sudo systemctl restart craftbeerpi
```

Repo: https://github.com/braubunker/cbpi4_SensorAverage

Lokal / editierbar:

```bash
pipx runpip cbpi4 install .
# oder:
pipx runpip cbpi4 install -e /pfad/zu/cbpi4_SensorAverage
```

Danach CraftBeerPi4 neu starten (`cbpi start` bzw. Service neu starten).

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

## Chart anzeigen

Nach Plugin-Install / CBPi-Neustart:

```text
http://<PI-IP>:8000/sensorchart/
```

Dort einstellbar:

- Sensor
- **Zeitlinie** (1h … 7 Tage)
- **Mittelwert über N Punkte**
- Methode (mean/median/…)
- Auto-Refresh alle 30 s

Zusätzlich in CBPi:

- **Analytics** → Sensor wählen → Chart  
- oder Dashboard-Widget **Chart** auf den AveragingSensor

## Entwicklung / Tests

Die Mittelwert-Logik ist ohne laufendes CraftBeerPi testbar:

```bash
cd cbpi4_SensorAverage
python3 -m pip install pytest
python3 -m pytest -q
```

## Changelog

* **1.0.0** – Eigenständiges Plugin: `AveragingSensor` + Chart-Seite `/sensorchart` (aus `cbpi4_BrewStart` ausgelagert)
