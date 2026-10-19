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
    """
    Register AveragingSensor (required) and SensorChartEndpoint (optional).

    Order matters: AveragingSensor is registered first. Chart mounting is fully
    isolated — CBPi instantiates CBPiExtension classes at plugin.register()
    time, and a failure there must never prevent the sensor type from appearing
    under Hardware → Sensors.
    """
    # --- 1) Sensor type (must succeed for the plugin to be useful) ---
    try:
        from .averaging_sensor import AveragingSensor

        cbpi.plugin.register("AveragingSensor", AveragingSensor)
        logger.info("Registered AveragingSensor")
    except Exception as exc:
        logger.exception("FAILED to register AveragingSensor: %s", exc)
        raise

    # --- 2) Chart HTTP page (best-effort; never abort sensor) ---
    try:
        from .chart_endpoint import mount_sensor_chart

        mount_sensor_chart(cbpi)
    except Exception as exc:
        # Do not re-raise: AveragingSensor stays available in the UI.
        logger.exception(
            "SensorChartEndpoint not mounted (AveragingSensor still available): %s",
            exc,
        )
