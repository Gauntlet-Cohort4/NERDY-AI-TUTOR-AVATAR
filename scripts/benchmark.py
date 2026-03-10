"""Automated latency benchmarking script.

Simulates N conversation turns against the pipeline and outputs a
latency report with per-stage breakdown, percentiles, and threshold
compliance.

Usage:
    python scripts/benchmark.py [--turns N] [--seed SEED]

The script does NOT require a live agent; it generates synthetic
latency samples from realistic distributions so the report can be
produced in CI without external API keys.
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Sequence

# Allow importing from the agent package without installation.
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "agent"))

from src.metrics import MetricsCollector  # noqa: E402
from src.types import TurnMetrics  # noqa: E402

# ── Latency thresholds (milliseconds) ──────────────────────────────────────

THRESHOLD_E2E_P95_MS = 1_500.0  # 95th-percentile end-to-end must be under 1.5 s
THRESHOLD_TTFT_MEAN_MS = 600.0  # Mean LLM time-to-first-token under 600 ms
THRESHOLD_TTS_TTFB_MEAN_MS = 300.0  # Mean TTS time-to-first-byte under 300 ms


# ── Synthetic latency sampler ───────────────────────────────────────────────

def _sample_latency(mean: float, std: float, lo: float, hi: float) -> float:
    """Draw a non-negative latency sample from a clipped normal distribution."""
    return max(lo, min(hi, random.gauss(mean, std)))


def _simulate_turn(turn_number: int) -> TurnMetrics:
    """Return a synthetic TurnMetrics object mimicking realistic pipeline timing."""
    stt_ms = _sample_latency(mean=180.0, std=40.0, lo=60.0, hi=500.0)
    llm_ttft_ms = _sample_latency(mean=420.0, std=120.0, lo=100.0, hi=1_200.0)
    llm_total_ms = llm_ttft_ms + _sample_latency(mean=300.0, std=80.0, lo=50.0, hi=900.0)
    tts_ttfb_ms = _sample_latency(mean=190.0, std=50.0, lo=50.0, hi=600.0)
    avatar_render_ms = _sample_latency(mean=80.0, std=20.0, lo=20.0, hi=300.0)
    total_e2e_ms = stt_ms + llm_ttft_ms + tts_ttfb_ms + avatar_render_ms

    return TurnMetrics(
        turn_number=turn_number,
        stt_ms=round(stt_ms, 1),
        llm_ttft_ms=round(llm_ttft_ms, 1),
        llm_total_ms=round(llm_total_ms, 1),
        tts_ttfb_ms=round(tts_ttfb_ms, 1),
        avatar_render_ms=round(avatar_render_ms, 1),
        total_e2e_ms=round(total_e2e_ms, 1),
        full_response_ms=round(llm_total_ms + tts_ttfb_ms, 1),
        tokens_generated=int(_sample_latency(mean=60.0, std=20.0, lo=10.0, hi=200.0)),
        response_text=f"[simulated turn {turn_number}]",
    )


# ── Statistics helpers ──────────────────────────────────────────────────────

def _percentile(sorted_values: list[float], pct: float) -> float:
    """Return the p-th percentile (0–100) of a pre-sorted list."""
    if not sorted_values:
        return 0.0
    idx = max(0, int(len(sorted_values) * pct / 100) - 1)
    return sorted_values[min(idx, len(sorted_values) - 1)]


def _pct_below(values: list[float], threshold: float) -> float:
    return round(sum(1 for v in values if v < threshold) / len(values) * 100, 1) if values else 0.0


def _stats(values: list[float]) -> dict:
    s = sorted(values)
    mean = statistics.mean(s) if s else 0.0
    median = statistics.median(s) if s else 0.0
    p95 = _percentile(s, 95)
    p99 = _percentile(s, 99)
    return {
        "mean": round(mean, 1),
        "median": round(median, 1),
        "p95": round(p95, 1),
        "p99": round(p99, 1),
        "min": round(min(s), 1) if s else 0.0,
        "max": round(max(s), 1) if s else 0.0,
    }


# ── Report rendering ────────────────────────────────────────────────────────

def _col(value: object, width: int, align: str = ">") -> str:
    return f"{value:{align}{width}}"


def _print_table(headers: Sequence[str], rows: Sequence[Sequence[object]], col_width: int = 12) -> None:
    sep = "+" + "+".join("-" * (col_width + 2) for _ in headers) + "+"
    header_row = "|" + "|".join(f" {_col(h, col_width)} " for h in headers) + "|"
    print(sep)
    print(header_row)
    print(sep)
    for row in rows:
        print("|" + "|".join(f" {_col(v, col_width)} " for v in row) + "|")
    print(sep)


def _print_report(collector: MetricsCollector, elapsed_wall_s: float) -> bool:
    """Print full benchmark report. Returns True if all thresholds pass."""
    turns = collector.turn_metrics
    n = len(turns)

    stt_vals = [t.stt_ms for t in turns]
    ttft_vals = [t.llm_ttft_ms for t in turns]
    tts_vals = [t.tts_ttfb_ms for t in turns]
    e2e_vals = [t.total_e2e_ms for t in turns]

    stt_s = _stats(stt_vals)
    ttft_s = _stats(ttft_vals)
    tts_s = _stats(tts_vals)
    e2e_s = _stats(e2e_vals)

    print("\n" + "=" * 74)
    print(f"  NERDY AI TUTOR — LATENCY BENCHMARK REPORT  ({n} turns simulated)")
    print("=" * 74)
    print(f"  Wall-clock time: {elapsed_wall_s:.2f}s  |  Avg throughput: {n / elapsed_wall_s:.1f} turns/s")
    print()

    headers = ["Stage", "Mean (ms)", "Median", "P95", "P99", "Min", "Max"]
    rows = [
        ["STT",        stt_s["mean"],  stt_s["median"],  stt_s["p95"],  stt_s["p99"],  stt_s["min"],  stt_s["max"]],
        ["LLM TTFT",   ttft_s["mean"], ttft_s["median"], ttft_s["p95"], ttft_s["p99"], ttft_s["min"], ttft_s["max"]],
        ["TTS TTFB",   tts_s["mean"],  tts_s["median"],  tts_s["p95"],  tts_s["p99"],  tts_s["min"],  tts_s["max"]],
        ["E2E Total",  e2e_s["mean"],  e2e_s["median"],  e2e_s["p95"],  e2e_s["p99"],  e2e_s["min"],  e2e_s["max"]],
    ]
    _print_table(headers, rows, col_width=11)

    print()
    print("  Threshold Compliance")
    print("  " + "-" * 50)

    thresholds = [
        ("E2E P95 < 1500 ms",       e2e_s["p95"],   THRESHOLD_E2E_P95_MS),
        ("LLM TTFT mean < 600 ms",  ttft_s["mean"], THRESHOLD_TTFT_MEAN_MS),
        ("TTS TTFB mean < 300 ms",  tts_s["mean"],  THRESHOLD_TTS_TTFB_MEAN_MS),
    ]

    all_pass = True
    for label, actual, limit in thresholds:
        passed = actual < limit
        all_pass = all_pass and passed
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}]  {label:35s}  actual={actual:.1f} ms  limit={limit:.0f} ms")

    print()
    print("  Percentile Buckets (E2E)")
    print(f"    < 500 ms : {_pct_below(e2e_vals, 500):5.1f}%")
    print(f"    < 1000 ms: {_pct_below(e2e_vals, 1000):5.1f}%")
    print(f"    < 1500 ms: {_pct_below(e2e_vals, 1500):5.1f}%")
    print()

    summary = collector.session_summary()
    if summary:
        print(f"  MetricsCollector session_summary: {summary}")
    print("=" * 74 + "\n")

    return all_pass


# ── Entry point ─────────────────────────────────────────────────────────────

def run_benchmark(n_turns: int, seed: int | None = None) -> bool:
    """Simulate `n_turns` conversation turns and print report.

    Returns True if all latency thresholds are met.
    """
    if seed is not None:
        random.seed(seed)

    collector = MetricsCollector(session_id="benchmark")

    print(f"Running {n_turns}-turn benchmark simulation...")
    wall_start = time.monotonic()

    for turn_number in range(1, n_turns + 1):
        metrics_event = _simulate_turn(turn_number)
        # Feed into MetricsCollector via a lightweight adapter object so the
        # collector's on_metrics() handler extracts fields using getattr().
        collector.on_metrics(_MetricsEventAdapter(metrics_event))

    elapsed = time.monotonic() - wall_start
    return _print_report(collector, elapsed)


class _MetricsEventAdapter:
    """Thin wrapper that exposes TurnMetrics fields using the attribute names
    expected by MetricsCollector.on_metrics() (seconds, not milliseconds)."""

    def __init__(self, turn: TurnMetrics) -> None:
        self.stt_duration = turn.stt_ms / 1_000.0
        self.llm_ttft = turn.llm_ttft_ms / 1_000.0
        self.tts_ttfb = turn.tts_ttfb_ms / 1_000.0
        self.e2e_duration = turn.total_e2e_ms / 1_000.0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Nerdy AI Tutor latency benchmark")
    parser.add_argument(
        "--turns",
        type=int,
        default=20,
        metavar="N",
        help="Number of conversation turns to simulate (default: 20)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="SEED",
        help="Random seed for reproducible results",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    passed = run_benchmark(n_turns=args.turns, seed=args.seed)
    sys.exit(0 if passed else 1)
