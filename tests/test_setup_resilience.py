"""setup() must register AveragingSensor even when the chart mount fails."""

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import cbpi4_SensorAverage


class _FakePlugin:
    def __init__(self):
        self.registered = []

    def register(self, name, clazz):
        self.registered.append((name, clazz))


def test_setup_isolates_chart_failure():
    fake_sensor = type("AveragingSensor", (), {})
    plugin = _FakePlugin()
    cbpi = MagicMock()
    cbpi.plugin = plugin

    sensor_module = ModuleType("cbpi4_SensorAverage.averaging_sensor")
    sensor_module.AveragingSensor = fake_sensor

    chart_module = ModuleType("cbpi4_SensorAverage.chart_endpoint")

    def boom(_cbpi):
        raise RuntimeError("static path / duplicate subapp")

    chart_module.mount_sensor_chart = boom

    with patch.dict(
        sys.modules,
        {
            "cbpi4_SensorAverage.averaging_sensor": sensor_module,
            "cbpi4_SensorAverage.chart_endpoint": chart_module,
        },
    ):
        # Chart failure must not abort setup after the sensor was registered.
        cbpi4_SensorAverage.setup(cbpi)

    assert plugin.registered == [("AveragingSensor", fake_sensor)]


def test_setup_reraises_sensor_failure():
    plugin = _FakePlugin()
    cbpi = MagicMock()
    cbpi.plugin = plugin

    sensor_module = ModuleType("cbpi4_SensorAverage.averaging_sensor")

    class BoomSensor:
        pass

    def register_fail(name, clazz):
        raise RuntimeError("parse props failed")

    plugin.register = register_fail
    sensor_module.AveragingSensor = BoomSensor

    with patch.dict(
        sys.modules,
        {"cbpi4_SensorAverage.averaging_sensor": sensor_module},
    ):
        try:
            cbpi4_SensorAverage.setup(cbpi)
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "parse props failed" in str(exc)
