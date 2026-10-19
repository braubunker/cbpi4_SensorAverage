"""CBPi4 sensor: sample a source sensor on a timeline and publish a moving average."""

from __future__ import annotations

import asyncio
import logging

from cbpi.api import *

from .averaging import TimelineAverager, parse_non_negative_int, parse_number

logger = logging.getLogger(__name__)


@parameters(
    [
        Property.Sensor(
            label="SourceSensor",
            description=(
                "Quellsensor (z.B. Gewicht, Druck, Temperatur), "
                "dessen Werte gemittelt werden sollen."
            ),
        ),
        Property.Number(
            label="SampleInterval",
            configurable=True,
            default_value=5,
            description="Sekunden zwischen zwei Messungen (Zeitlinie). Standard: 5",
        ),
        Property.Number(
            label="AverageCount",
            configurable=True,
            default_value=10,
            description="Anzahl Messungen für den gleitenden Mittelwert. Standard: 10",
        ),
        Property.Select(
            label="AverageMethod",
            options=["mean", "median", "min", "max"],
            description="Aggregation: mean (Mittelwert), median, min oder max",
        ),
        Property.Number(
            label="StartDelay",
            configurable=True,
            default_value=0,
            description="Sekunden warten vor der ersten Messung. Standard: 0",
        ),
        Property.Select(
            label="RequireFullWindow",
            options=["No", "Yes"],
            description=(
                "Yes: erst ausgeben, wenn AverageCount Messungen vorliegen. "
                "No: sobald mindestens eine Messung da ist."
            ),
        ),
        Property.Number(
            label="LogInterval",
            configurable=True,
            default_value=60,
            description=(
                "Sekunden zwischen Chart-/Log-Einträgen. "
                "0 = bei jedem neuen Mittelwert loggen. Standard: 60"
            ),
        ),
        Property.Select(
            label="LogData",
            options=["Yes", "No"],
            description="Yes: in CSV loggen → Chart in Analytics / Sensor-Chart möglich",
        ),
    ]
)
class AveragingSensor(CBPiSensor):
    """
    Liest einen Quell-Sensor in festem Intervall und liefert Mittelwert/Median.
    Mit LogData=Yes erscheinen die Werte in CBPi-Charts und unter /sensorchart.
    """

    def __init__(self, cbpi, id, props):
        super(AveragingSensor, self).__init__(cbpi, id, props)
        self.value = 0
        self.source_id = None
        self.averager = None
        self.log_interval = 60
        self.log_enabled = True
        self._seconds_since_log = 0

    async def on_start(self):
        self.source_id = self.props.get("SourceSensor", None)
        self.averager = TimelineAverager.from_props(self.props)
        self.log_interval = parse_non_negative_int(self.props.get("LogInterval", 60), 60)
        self.log_enabled = (self.props.get("LogData", None) or "Yes") == "Yes"
        self._seconds_since_log = 0

        logger.info(
            "AveragingSensor %s source=%s interval=%ss count=%s method=%s "
            "delay=%ss full=%s log=%ss",
            self.id,
            self.source_id,
            self.averager.sample_interval,
            self.averager.window.size,
            self.averager.method,
            self.averager.start_delay,
            self.averager.require_full_window,
            self.log_interval,
        )

    def get_state(self):
        return dict(value=self.value)

    def _read_source(self):
        if not self.source_id:
            return None
        try:
            if hasattr(self, "get_sensor_value"):
                state = self.get_sensor_value(self.source_id)
            else:
                state = self.cbpi.sensor.get_sensor_value(self.source_id)
            if isinstance(state, dict):
                return parse_number(state.get("value"))
            return parse_number(state)
        except Exception as exc:
            logger.debug("AveragingSensor %s read failed: %s", self.id, exc)
            return None

    async def run(self):
        if self.averager is None:
            await self.on_start()

        if self.averager.start_delay > 0:
            await asyncio.sleep(self.averager.start_delay)

        while self.running is True:
            averaged = self.averager.add_sample(self._read_source())

            if averaged is not None:
                self.value = round(float(averaged), 4)
                try:
                    self.push_update(self.value)
                except Exception:
                    pass

                if self.log_enabled:
                    should_log = False
                    if self.log_interval <= 0:
                        should_log = True
                    else:
                        self._seconds_since_log += self.averager.sample_interval
                        if self._seconds_since_log >= self.log_interval:
                            should_log = True
                            self._seconds_since_log = 0
                    if should_log:
                        try:
                            self.log_data(self.value)
                        except Exception:
                            pass
            else:
                try:
                    self.push_update(self.value, False)
                except Exception:
                    pass

            await asyncio.sleep(self.averager.sample_interval)


TimelineAverageSensor = AveragingSensor
