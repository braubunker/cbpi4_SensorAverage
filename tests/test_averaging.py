from datetime import datetime, timedelta

import pytest

from cbpi4_SensorAverage.averaging import (
    SampleWindow,
    TimelineAverager,
    average,
    chart_payload,
    filter_hours,
    moving_average,
    parse_log_points,
    parse_non_negative_int,
    parse_number,
    parse_positive_int,
)


def test_parse_number():
    assert parse_number(12.3) == 12.3
    assert parse_number("7,5") == 7.5
    assert parse_number("") is None
    assert parse_number(None) is None
    assert parse_number("x") is None


def test_parse_positive_int():
    assert parse_positive_int(None, 5) == 5
    assert parse_positive_int("3", 5) == 3
    assert parse_positive_int("0", 5, minimum=1) == 1
    assert parse_non_negative_int("-2", 0) == 0


def test_average_mean_median():
    assert average([1, 2, 3], "mean") == 2
    assert average([1, 2, 100], "median") == 2
    assert average([1, 9], "min") == 1
    assert average([1, 9], "max") == 9
    assert average([], "mean") is None


def test_sample_window_fifo():
    window = SampleWindow(3)
    window.add(1)
    window.add(2)
    window.add(3)
    assert window.is_full()
    assert window.samples == [1.0, 2.0, 3.0]
    window.add(4)
    assert window.samples == [2.0, 3.0, 4.0]
    assert window.average("mean") == pytest.approx(3.0)


def test_timeline_averager_partial_by_default():
    avg = TimelineAverager(sample_count=3, method="mean", require_full_window=False)
    assert avg.add_sample(10) == pytest.approx(10.0)
    assert avg.add_sample(20) == pytest.approx(15.0)


def test_timeline_averager_requires_full_window():
    avg = TimelineAverager(sample_count=3, method="mean", require_full_window=True)
    assert avg.add_sample(10) is None
    assert avg.add_sample(20) is None
    assert avg.add_sample(30) == pytest.approx(20.0)
    assert avg.add_sample(40) == pytest.approx(30.0)


def test_timeline_averager_skips_invalid():
    avg = TimelineAverager(sample_count=2, method="mean", require_full_window=True)
    assert avg.add_sample(None) is None
    assert avg.add_sample("bad") is None
    assert avg.add_sample(4) is None
    assert avg.add_sample(6) == pytest.approx(5.0)


def test_from_props_accepts_aliases():
    avg = TimelineAverager.from_props(
        {
            "SampleCount": "4",
            "SampleInterval": "15",
            "StartDelay": "2",
            "Method": "median",
            "RequireFullWindow": "Yes",
        }
    )
    assert avg.window.size == 4
    assert avg.sample_interval == 15.0
    assert avg.start_delay == 2.0
    assert avg.method == "median"
    assert avg.require_full_window is True

    avg2 = TimelineAverager.from_props(
        {"AverageCount": "8", "AverageMethod": "mean", "SampleInterval": "5"}
    )
    assert avg2.window.size == 8
    assert avg2.method == "mean"


def test_moving_average_window():
    now = datetime(2026, 10, 19, 12, 0, 0)
    points = [(now + timedelta(seconds=i), float(i)) for i in range(5)]
    out = moving_average(points, window=3, method="mean")
    assert len(out) == 5
    assert out[0][1] == 0
    assert out[2][1] == 1.0  # (0+1+2)/3


def test_filter_hours():
    now = datetime(2026, 10, 19, 12, 0, 0)
    points = [
        (now - timedelta(hours=30), 1.0),
        (now - timedelta(hours=2), 2.0),
        (now - timedelta(minutes=5), 3.0),
    ]
    filtered = filter_hours(points, hours=24, now=now)
    assert [v for _, v in filtered] == [2.0, 3.0]


def test_chart_payload():
    now = datetime(2026, 10, 19, 12, 0, 0)
    points = [(now - timedelta(minutes=i), float(i)) for i in range(10)]
    payload = chart_payload(points, hours=1, average_window=2, method="mean", now=now)
    assert payload["count"] == 10
    assert payload["hours"] == 1
    assert len(payload["time"]) == len(payload["value"])


def test_parse_log_points():
    times = ["2026-10-19 10:00:00", "2026-10-19 10:01:00"]
    values = ["12.5", "13"]
    points = parse_log_points(times, values)
    assert len(points) == 2
    assert points[0][1] == 12.5
