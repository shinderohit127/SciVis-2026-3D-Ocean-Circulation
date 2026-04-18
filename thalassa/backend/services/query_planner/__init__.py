"""
Query planner service — skeleton.

Responsibilities (Weeks 3-4):
- Estimate payload cost for a given ROI / time / depth / quality budget.
- Choose OpenVisus quality level (negative int: -15 coarse → 0 full resolution).
- Route requests to cache or live OpenVisus fetch.
- Log cost estimates for latency benchmarking (PRD §9.1).
"""
