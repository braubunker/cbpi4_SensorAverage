"""Pure helpers for sample averaging and chart timeline windows (no cbpi import)."""

from __future__ import annotations

import statistics
from collections import deque
from datetime import datetime, timedelta
from typing import Deque, Iterable, List, Optional, Sequence, Tuple, Union

Number = Union[int, float]
NumberPoint = Tuple[datetime, float]


def parse_number(value) -> Optional[float]:
    """Convert a sensor/UI value to float, or None if missing/invalid."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def parse_positive_int(value, default: int, minimum: int = 1) -> int:
    """Parse a positive integer from UI props; fall back to default on error."""
    parsed = parse_number(value)
    if parsed is None:
        parsed = float(default)
    return max(minimum, int(parsed))


def parse_non_negative_int(value, default: int = 0) -> int:
    """Parse a non-negative integer from UI props."""
    parsed = parse_number(value)
    if parsed is None:
        parsed = float(default)
    return max(0, int(parsed))


def average(values: Sequence[float], method: str = "mean") -> Optional[float]:
    """Aggregate numbers with mean / median / min / max. Empty → None."""
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    key = (method or "mean").strip().lower()
    if key == "median":
        return float(statistics.median(nums))
    if key == "min":
        return float(min(nums))
    if key == "max":
        return float(max(nums))
    if hasattr(statistics, "fmean"):
        return float(statistics.fmean(nums))
    return float(statistics.mean(nums))


# Backwards-friendly alias used in docs / imports
aggregate = average


class SampleWindow:
    """Fixed-size FIFO of recent samples for a moving average."""

    def __init__(self, size: int):
        size = max(1, int(size))
        self.size = size
        self._samples: Deque[float] = deque(maxlen=size)

    def clear(self) -> None:
        self._samples.clear()

    def add(self, value: Number) -> None:
        self._samples.append(float(value))

    def __len__(self) -> int:
        return len(self._samples)

    @property
    def samples(self) -> List[float]:
        return list(self._samples)

    def is_full(self) -> bool:
        return len(self._samples) >= self.size

    def average(self, method: str = "mean") -> Optional[float]:
        return average(self.samples, method=method)


class TimelineAverager:
    """
    Collect samples on a timeline and compute a moving mean/median/...

    sample_interval / start_delay are stored for callers (sensor sleep);
    this class does not sleep itself.
    """

    def __init__(
        self,
        sample_count: int = 10,
        method: str = "mean",
        require_full_window: bool = False,
        sample_interval: float = 5.0,
        start_delay: float = 0.0,
    ):
        self.sample_interval = max(0.1, float(sample_interval))
        self.start_delay = max(0.0, float(start_delay))
        self.method = (method or "mean").strip().lower()
        if self.method not in ("mean", "median", "min", "max"):
            self.method = "mean"
        self.require_full_window = bool(require_full_window)
        self.window = SampleWindow(parse_positive_int(sample_count, 10, minimum=1))

    @classmethod
    def from_props(cls, props: dict) -> "TimelineAverager":
        props = props or {}
        # Accept both AverageCount (UI) and SampleCount (docs alias)
        count_raw = props.get("AverageCount", props.get("SampleCount", 10))
        sample_count = parse_positive_int(count_raw, 10, minimum=1)
        interval_raw = props.get("SampleInterval", 5)
        sample_interval = parse_number(interval_raw)
        if sample_interval is None or sample_interval <= 0:
            sample_interval = 5.0
        start_delay = parse_non_negative_int(props.get("StartDelay", 0), 0)
        method = str(
            props.get("AverageMethod", props.get("Method", "mean")) or "mean"
        )
        require = str(props.get("RequireFullWindow", "No") or "No").strip().lower()
        require_full = require in ("yes", "true", "1", "ja")
        return cls(
            sample_count=sample_count,
            method=method,
            require_full_window=require_full,
            sample_interval=float(sample_interval),
            start_delay=float(start_delay),
        )

    def reset(self) -> None:
        self.window.clear()

    def add_sample(self, value) -> Optional[float]:
        """Add a coerced sample if valid; return current aggregate (or None)."""
        sample = parse_number(value)
        if sample is None:
            return self.current()
        self.window.add(sample)
        return self.current()

    def current(self) -> Optional[float]:
        if len(self.window) == 0:
            return None
        if self.require_full_window and not self.window.is_full():
            return None
        return self.window.average(self.method)


def moving_average(
    points: Sequence[NumberPoint], window: int, method: str = "mean"
) -> List[NumberPoint]:
    """Return points where each value is averaged over the last `window` samples."""
    window = max(1, int(window or 1))
    if window == 1 or not points:
        return list(points)

    out: List[NumberPoint] = []
    buf: List[float] = []
    for ts, value in points:
        buf.append(value)
        if len(buf) > window:
            buf.pop(0)
        avg = average(buf, method)
        if avg is not None:
            out.append((ts, avg))
    return out


def filter_hours(
    points: Sequence[NumberPoint], hours: float, now: Optional[datetime] = None
) -> List[NumberPoint]:
    """Keep only points within the last `hours` from now."""
    hours = float(hours or 0)
    if hours <= 0:
        return list(points)
    now = now or datetime.now()
    cutoff = now - timedelta(hours=hours)
    return [(ts, v) for ts, v in points if ts >= cutoff]


def parse_log_points(times: Iterable, values: Iterable) -> List[NumberPoint]:
    """Parse CBPi log arrays (time + value) into datetime/float pairs."""
    points: List[NumberPoint] = []
    for raw_t, raw_v in zip(list(times), list(values)):
        value = parse_number(raw_v)
        if value is None:
            continue
        ts = raw_t
        if isinstance(ts, str):
            cleaned = ts.split("+")[0].split("Z")[0]
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
            ):
                try:
                    ts = datetime.strptime(cleaned, fmt)
                    break
                except ValueError:
                    continue
            else:
                try:
                    ts = datetime.fromisoformat(str(raw_t).replace("Z", ""))
                except ValueError:
                    continue
        elif not isinstance(ts, datetime):
            try:
                if hasattr(raw_t, "to_pydatetime"):
                    ts = raw_t.to_pydatetime()
                else:
                    ts = datetime.fromtimestamp(float(raw_t))
            except Exception:
                continue
        points.append((ts, value))
    return points


def chart_payload(
    points: Sequence[NumberPoint],
    hours: float = 24,
    average_window: int = 1,
    method: str = "mean",
    now: Optional[datetime] = None,
) -> dict:
    filtered = filter_hours(points, hours, now=now)
    smoothed = moving_average(filtered, average_window, method=method)
    return {
        "time": [ts.strftime("%Y-%m-%d %H:%M:%S") for ts, _ in smoothed],
        "value": [round(v, 4) for _, v in smoothed],
        "count": len(smoothed),
        "hours": hours,
        "average_window": max(1, int(average_window or 1)),
        "method": method or "mean",
    }
