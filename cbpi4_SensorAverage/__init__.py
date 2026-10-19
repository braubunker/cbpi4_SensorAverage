"""CraftBeerPi4 plugin: AveragingSensor + interactive Sensor Chart page."""

import logging

logger = logging.getLogger(__name__)

try:
    from .averaging import TimelineAverager, average
except Exception:  # pragma: no cover
    TimelineAverager = average = None  # type: ignore

__all__ = [
    "TimelineAverager",
    "average",
    "setup",
]


def setup(cbpi):
    """Register AveragingSensor and SensorChartEndpoint with CraftBeerPi4."""
    try:
        from .averaging_sensor import AveragingSensor

        cbpi.plugin.register("AveragingSensor", AveragingSensor)
        logger.info("Registered AveragingSensor")
    except Exception as exc:
        logger.exception("FAILED to register AveragingSensor: %s", exc)
        raise

    try:
        from .chart_endpoint import SensorChartEndpoint

        cbpi.plugin.register("SensorChartEndpoint", SensorChartEndpoint)
        logger.info("Registered SensorChartEndpoint (/sensorchart)")
    except Exception as exc:
        logger.exception("FAILED to register SensorChartEndpoint: %s", exc)
