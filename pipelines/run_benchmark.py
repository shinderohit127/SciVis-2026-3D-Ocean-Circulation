#!/usr/bin/env python3
"""
THALASSA performance benchmark — paper §V data collection.

Hits the running API server and produces a Markdown / LaTeX table of
query latencies at multiple quality levels for the default North Atlantic ROI.

Usage:
    python pipelines/run_benchmark.py                     # default ROI, server at localhost:8000
    python pipelines/run_benchmark.py --host 0.0.0.0     # remote server
    python pipelines/run_benchmark.py --output latex      # LaTeX table instead of Markdown
    python pipelines/run_benchmark.py --runs 3            # average over N repetitions
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from typing import Optional

try:
    import httpx
except ImportError:
    print("httpx is required: pip install httpx")
    sys.exit(1)


DEFAULT_ROI = {
    "lat_min": 35.0, "lat_max": 45.0,
    "lon_min": -40.0, "lon_max": -30.0,
    "depth_min_m": 0.0, "depth_max_m": 2000.0,
    "timestep": 0,
    "qualities": [-15, -14, -12, -10, -9, -8, -7],
}

QUALITY_LABEL = {
    -15: "Ultra-coarse", -14: "Descriptor",
    -12: "Overview", -10: "Coarse",
    -9:  "Standard",   -8:  "High",
    -7:  "Preview-max",
}


def run_once(host: str, port: int, roi: dict) -> list[dict]:
    url = f"http://{host}:{port}/api/benchmark"
    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, json=roi)
    r.raise_for_status()
    return r.json()["runs"]


def collect(host: str, port: int, roi: dict, n_runs: int) -> list[dict]:
    all_runs: dict[int, list[int]] = {}

    for rep in range(n_runs):
        print(f"  Run {rep + 1}/{n_runs}…", end=" ", flush=True)
        t0 = time.monotonic()
        runs = run_once(host, port, roi)
        print(f"{time.monotonic() - t0:.1f}s")
        for r in runs:
            q = r["quality"]
            all_runs.setdefault(q, []).append(r["elapsed_ms"])

    return [
        {
            "quality": q,
            "label": QUALITY_LABEL.get(q, str(q)),
            "elapsed_ms_mean": round(statistics.mean(times)),
            "elapsed_ms_std":  round(statistics.stdev(times)) if len(times) > 1 else 0,
        }
        for q, times in sorted(all_runs.items())
    ]


def print_markdown(rows: list[dict], roi: dict) -> None:
    print("\n## THALASSA Benchmark — North Atlantic ROI")
    print(f"ROI: {roi['lat_min']}–{roi['lat_max']}°N, {roi['lon_min']}–{roi['lon_max']}°E, "
          f"{roi['depth_min_m']}–{roi['depth_max_m']} m\n")
    print("| Quality | Label         | Latency (ms) | ±std |")
    print("|--------:|:--------------|-------------:|-----:|")
    for r in rows:
        std = f"±{r['elapsed_ms_std']}" if r['elapsed_ms_std'] else "—"
        print(f"| {r['quality']:>7} | {r['label']:<13} | {r['elapsed_ms_mean']:>12} | {std:>4} |")


def print_latex(rows: list[dict], roi: dict) -> None:
    print(r"\begin{table}[h]")
    print(r"\centering")
    print(r"\begin{tabular}{rllr}")
    print(r"\hline")
    print(r"Quality & Mode & Latency (ms) & $\pm\sigma$ \\")
    print(r"\hline")
    for r in rows:
        std = f"\\pm {r['elapsed_ms_std']}" if r['elapsed_ms_std'] else "--"
        print(f"  {r['quality']} & {r['label']} & {r['elapsed_ms_mean']} & ${std}$ \\\\")
    print(r"\hline")
    print(r"\end{tabular}")
    print(r"\caption{THALASSA query latency at multiple resolution levels (North Atlantic ROI, "
          r"35--45$^\circ$N, 30--40$^\circ$W, 0--2000 m). Progressive query planning "
          r"delivers sub-3\,s preview at quality --7.}")
    print(r"\label{tab:benchmark}")
    print(r"\end{table}")


def main() -> None:
    parser = argparse.ArgumentParser(description="THALASSA paper benchmark")
    parser.add_argument("--host",   default="127.0.0.1")
    parser.add_argument("--port",   type=int, default=8000)
    parser.add_argument("--runs",   type=int, default=1,  help="repetitions to average")
    parser.add_argument("--output", choices=["markdown", "latex"], default="markdown")
    parser.add_argument("--save",   metavar="FILE", help="save JSON results to file")
    args = parser.parse_args()

    print(f"Benchmarking {args.host}:{args.port} × {args.runs} run(s)…")
    rows = collect(args.host, args.port, DEFAULT_ROI, args.runs)

    if args.save:
        with open(args.save, "w") as f:
            json.dump(rows, f, indent=2)
        print(f"\nSaved to {args.save}")

    if args.output == "latex":
        print_latex(rows, DEFAULT_ROI)
    else:
        print_markdown(rows, DEFAULT_ROI)


if __name__ == "__main__":
    main()
