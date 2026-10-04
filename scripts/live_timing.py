"""Physical UART frame-start metrics; not AES core or host latency."""
import math


def frame_metrics(acquisition, expected):
    rate = acquisition.get("sample_rate_hz")
    baud = acquisition.get("baud")
    if not isinstance(rate, (int, float)) or not math.isfinite(rate) or rate <= 0:
        raise ValueError("actual AD2 sample rate unavailable")
    if not isinstance(baud, int) or baud <= 0:
        raise ValueError("UART baud unavailable")
    starts = [acquisition.get(label + "_frame_start_samples")
              for label in ("reference", "cipher")]
    for series in starts:
        if not isinstance(series, list) or len(series) != expected:
            raise ValueError("frame timestamps incomplete")
        if any(type(value) is not int or value < 0 for value in series):
            raise ValueError("invalid frame timestamp")
        if any(a >= b for a, b in zip(series, series[1:])):
            raise ValueError("frame timestamps not strictly increasing")
    offsets = [b - a for a, b in zip(*starts)]
    if min(offsets) < 0:
        raise ValueError("output frame precedes paired input")
    ordered = sorted(offsets)
    # Nearest-rank percentiles: reproducible even for short captures.
    percentile = lambda p: ordered[max(0, math.ceil(p * expected) - 1)] / rate * 1e6
    durations = [(s[-1] - s[0]) / rate + 10 / baud for s in starts]
    return {"measurement": "GPS start-bit edge to paired FPGA start-bit edge",
            "sample_rate_hz": rate, "sample_period_us": 1e6 / rate,
            "edge_difference_quantization_bound_us": 1e6 / rate,
            "percentile_method": "nearest-rank", "paired_bytes": expected,
            "delay_p50_us": percentile(0.50), "delay_p95_us": percentile(0.95),
            "delay_max_us": max(offsets) / rate * 1e6,
            "reference_span_seconds": durations[0], "output_span_seconds": durations[1],
            "reference_bytes_per_second": expected / durations[0],
            "output_bytes_per_second": expected / durations[1],
            "note": "Includes UART reception and forwarding; not AES computation latency. "
                    "Spans end with one nominal 8N1 character, not a measured stop-bit edge."}
