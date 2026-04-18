"""
LLC4320 vertical grid — cell-center depths in metres (positive = deeper).

Source: MITgcm 90-level standard configuration used by ECCO LLC4320.
RC file from ECCO production grid documentation.
Range: 5 m (surface) to 6625 m (abyssal). 90 levels total.

NOTE: An earlier version of data_access_llc4320.py in this project had
DEPTH_LEVELS that reached ~9845 m — this was incorrect. The values below
are the authoritative mapping from OpenVisus z-index → physical depth.
Verify with notebooks/01_verify_openvisus.py if in doubt.
"""

import numpy as np

DEPTH_LEVELS_M: np.ndarray = np.array([
      5.0,   15.0,   25.0,   35.0,   45.0,   55.0,   65.0,   75.0,   85.0,   95.0,
    105.0,  115.0,  125.0,  135.0,  145.0,  155.0,  165.0,  175.0,  185.0,  195.0,
    205.0,  215.0,  225.0,  235.0,  245.0,  255.0,  275.0,  295.0,  315.0,  335.0,
    355.0,  380.0,  415.0,  455.0,  495.0,  540.0,  590.0,  640.0,  695.0,  755.0,
    820.0,  890.0,  965.0, 1045.0, 1130.0, 1220.0, 1315.0, 1415.0, 1520.0, 1630.0,
   1750.0, 1875.0, 2000.0, 2125.0, 2250.0, 2375.0, 2500.0, 2625.0, 2750.0, 2875.0,
   3000.0, 3125.0, 3250.0, 3375.0, 3500.0, 3625.0, 3750.0, 3875.0, 4000.0, 4125.0,
   4250.0, 4375.0, 4500.0, 4625.0, 4750.0, 4875.0, 5000.0, 5125.0, 5250.0, 5375.0,
   5500.0, 5625.0, 5750.0, 5875.0, 6000.0, 6125.0, 6250.0, 6375.0, 6500.0, 6625.0,
], dtype=np.float64)

assert len(DEPTH_LEVELS_M) == 90, "Must have exactly 90 depth levels"


def depth_to_z_index(depth_m: float) -> int:
    """Return the z-index (0-based) of the depth level nearest to depth_m."""
    return int(np.argmin(np.abs(DEPTH_LEVELS_M - depth_m)))


def z_index_to_depth(z: int) -> float:
    """Return the cell-centre depth in metres for a given z-index."""
    return float(DEPTH_LEVELS_M[z])


def depth_range_to_z_indices(depth_min_m: float, depth_max_m: float) -> tuple[int, int]:
    """Return (z_start, z_end) inclusive z-index range covering [depth_min_m, depth_max_m]."""
    z_start = int(np.searchsorted(DEPTH_LEVELS_M, depth_min_m, side="left"))
    z_end = int(np.searchsorted(DEPTH_LEVELS_M, depth_max_m, side="right")) - 1
    z_start = max(0, min(z_start, 89))
    z_end = max(z_start, min(z_end, 89))
    return z_start, z_end
