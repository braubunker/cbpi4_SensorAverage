import logging
import os
from datetime import datetime

from aiohttp import web
from cbpi.api import *

from .averaging import chart_payload, parse_log_points

logger = logging.getLogger(__name__)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class SensorChartEndpoint(CBPiExtension):
    """HTTP + static Chart page: Zeitlinie und Mittelwert über Log-Daten."""

    def __init__(self, cbpi):
        self.cbpi = cbpi
        static = STATIC_DIR if os.path.isdir(STATIC_DIR) else None
        if static is None:
            logger.warning(
                "SensorChart static dir missing (%s); mounting API without static files",
                STATIC_DIR,
            )
        # cbpi.register parses @request_mapping and mounts the subapp.
        # Keep this resilient: missing static / duplicate prefix must not crash.
        self.cbpi.register(self, "/sensorchart", static=static)
        logger.info("SensorChartEndpoint mounted at /sensorchart")

    @request_mapping(path="/", auth_required=False)
    async def index(self, request):
        raise web.HTTPFound("/sensorchart/static/index.html")

    @request_mapping(path="/api/sensors", auth_required=False)
    async def list_sensors(self, request):
        sensors = []
        try:
            state = self.cbpi.sensor.get_state()
            data = state.get("data", state) if isinstance(state, dict) else state
            if isinstance(data, dict) and "data" in data:
                data = data["data"]
            for item in data or []:
                if not isinstance(item, dict):
                    continue
                sensors.append(
                    {
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "type": item.get("type"),
                    }
                )
        except Exception as exc:
            logger.error("list_sensors failed: %s", exc)
            return web.json_response({"sensors": [], "error": str(exc)})
        return web.json_response({"sensors": sensors})

    @request_mapping(path="/api/chart", auth_required=False)
    async def chart_data(self, request):
        sensor_id = request.rel_url.query.get("sensor_id")
        if not sensor_id:
            return web.json_response({"error": "sensor_id required"}, status=400)

        try:
            hours = float(request.rel_url.query.get("hours", "24") or 24)
        except ValueError:
            hours = 24
        try:
            average_window = int(float(request.rel_url.query.get("average", "1") or 1))
        except ValueError:
            average_window = 1
        method = request.rel_url.query.get("method", "mean") or "mean"

        sensor_name = sensor_id
        try:
            sensor = self.cbpi.sensor.find_by_id(sensor_id)
            if sensor is not None:
                sensor_name = getattr(sensor, "name", sensor_id)
        except Exception:
            pass

        times, values = [], []
        try:
            raw = await self.cbpi.log.get_data2([sensor_id])
            if isinstance(raw, dict) and sensor_id in raw:
                block = raw[sensor_id] or {}
                times = block.get("time", []) or []
                values = block.get("value", []) or []
            elif isinstance(raw, dict) and "time" in raw:
                times = raw.get("time", []) or []
                values = raw.get("value", []) or raw.get(sensor_id, []) or []
            else:
                raw1 = await self.cbpi.log.get_data(sensor_id)
                times, values = self._extract_series(raw1, sensor_id)
        except Exception as exc:
            logger.exception("chart log read failed: %s", exc)
            return web.json_response(
                {
                    "time": [],
                    "value": [],
                    "count": 0,
                    "error": str(exc),
                    "sensor_id": sensor_id,
                    "sensor_name": sensor_name,
                    "hours": hours,
                    "average_window": average_window,
                    "method": method,
                }
            )

        points = parse_log_points(times, values)
        payload = chart_payload(
            points,
            hours=hours,
            average_window=average_window,
            method=method,
            now=datetime.now(),
        )
        payload["sensor_id"] = sensor_id
        payload["sensor_name"] = sensor_name
        return web.json_response(payload)

    def _extract_series(self, raw, sensor_id):
        times, values = [], []
        if raw is None:
            return times, values
        if isinstance(raw, dict):
            if "time" in raw:
                times = raw.get("time") or []
                if sensor_id in raw:
                    values = raw.get(sensor_id) or []
                else:
                    values = raw.get("value") or []
                return times, values
            for key, block in raw.items():
                if isinstance(block, dict) and "time" in block:
                    return (
                        block.get("time") or [],
                        block.get("value") or block.get(key) or [],
                    )
        return times, values


def mount_sensor_chart(cbpi):
    """
    Mount the chart endpoint without going through plugin.register().

    CBPi's plugin.register() instantiates CBPiExtension subclasses immediately.
    Instantiating here keeps chart failures isolated from AveragingSensor
    registration and avoids treating the extension as a "plugin type".
    """
    SensorChartEndpoint(cbpi)
    logger.info("Registered SensorChartEndpoint (/sensorchart)")
