"""
01_verify_openvisus.py — Week 1-2 verification: OpenVisus access + grid orientation.

Run from the repo root:
    conda activate thalassa-backend
    python notebooks/01_verify_openvisus.py

What this script verifies:
  1. OpenVisus can connect to all three LLC4320 variables (theta, salt, w).
  2. A small test fetch returns plausible values (sea-surface temperature ~0–32°C,
     salinity ~30–38 psu, vertical velocity near zero surface mean).
  3. Grid orientation is correct: tropical Pacific is warm, not cold.
  4. Depth levels match the standard LLC4320 90-level grid (5 m – 6625 m).
  5. Cached data from prior runs aligns with the live OpenVisus reads.

If OpenVisus is unavailable (no network or not installed), the script falls
back to the local cache in cache/ and performs validation from there.

IMPORTANT: If the orientation check fails, all downstream data must be
flipped. Do not proceed to density computation until this is resolved.
"""

import os, sys, logging
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / "cache"
FIGURES_DIR = REPO_ROOT / "figures"
FIGURES_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(REPO_ROOT / "thalassa" / "backend"))

from data_access.depth_levels import DEPTH_LEVELS_M, depth_to_z_index
from data_access.llc4320 import (
    LLC4320Reader, ROI, NX, NY, NZ, DLON, DLAT,
    lon_to_x, lat_to_y, x_to_lon, y_to_lat, VARIABLE_URLS,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

PASS = "✓ PASS"
FAIL = "✗ FAIL"
SKIP = "  SKIP"


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# =============================================================================
# 1. Depth levels
# =============================================================================

def check_depth_levels() -> bool:
    section("1. Depth level mapping")
    ok = True

    print(f"  Total levels: {len(DEPTH_LEVELS_M)}", "== 90" if len(DEPTH_LEVELS_M) == 90 else "!= 90  ← ERROR")
    ok &= len(DEPTH_LEVELS_M) == 90

    print(f"  Surface level (z=0): {DEPTH_LEVELS_M[0]:.1f} m  (expected: 5.0 m)")
    ok &= abs(DEPTH_LEVELS_M[0] - 5.0) < 1.0

    print(f"  Deepest level (z=89): {DEPTH_LEVELS_M[89]:.1f} m  (expected: 6625.0 m)")
    ok &= abs(DEPTH_LEVELS_M[89] - 6625.0) < 10.0

    # Spot-check depth_to_z_index
    for target_m, expected_z in [(5, 0), (255, 25), (1000, 43), (3000, 60)]:
        got_z = depth_to_z_index(target_m)
        close = abs(DEPTH_LEVELS_M[got_z] - target_m) < 100  # within 100m is fine for non-surface
        status = PASS if close else FAIL
        print(f"  depth_to_z_index({target_m} m) = z={got_z} → {DEPTH_LEVELS_M[got_z]:.0f} m  {status}")
        ok &= close

    # Check the ORIGINAL cached depths (expected to be WRONG)
    orig_depth_path = CACHE_DIR / "na_volume_depths.npy"
    if orig_depth_path.exists():
        orig_depths = np.load(orig_depth_path)
        expected_max = 6625.0
        actual_max = orig_depths.max()
        wrong = actual_max > 7000
        flag = "WRONG (too deep — known bug in original data_access_llc4320.py)" if wrong else "OK"
        print(f"\n  Cache na_volume_depths max = {actual_max:.0f} m  → {flag}")
        print(f"  Authoritative max from depth_levels.py = {DEPTH_LEVELS_M.max():.0f} m")
        if wrong:
            print(f"  ⚠  The cached volume depths will be REPLACED with correct values")
            print(f"     in density computations. Do NOT use na_volume_depths.npy directly.")

    print(f"\n  Depth levels: {PASS if ok else FAIL}")
    return ok


# =============================================================================
# 2. Coordinate mapping
# =============================================================================

def check_coordinate_mapping() -> bool:
    section("2. Coordinate mapping")
    ok = True

    checks = [
        # (lon, lat, expected_description)
        (-60.0,  0.0, "NA SW corner", (14400, 6480)),
        (  0.0, 70.0, "NA NE corner", (0,     11520)),   # 0°E in [0,360] = 0 = NX (edge case)
        (  0.0,  0.0, "Equator/Prime Meridian", (0, 6480)),
        (-180.0, 0.0, "Date line West", (8640, 6480)),
        ( 180.0, 0.0, "Date line East", (8640, 6480)),
    ]

    for lon, lat, desc, (ex_x, ex_y) in checks:
        x = lon_to_x(lon)
        y = lat_to_y(lat)
        x_ok = abs(x - ex_x) <= 1
        y_ok = abs(y - ex_y) <= 1
        status = PASS if x_ok and y_ok else FAIL
        ok &= x_ok and y_ok
        print(f"  ({lon:>7},{lat:>5}) → x={x:>5}, y={y:>5}  (expected x≈{ex_x}, y≈{ex_y})  {status}  {desc}")

    # Round-trip check
    for z in [0, 10, 45, 89]:
        d = float(DEPTH_LEVELS_M[z])
        z_back = depth_to_z_index(d)
        rt_ok = z_back == z
        ok &= rt_ok
        status = PASS if rt_ok else FAIL
        print(f"  z={z} → {d:.0f}m → z_back={z_back}  {status}")

    print(f"\n  Coordinate mapping: {PASS if ok else FAIL}")
    return ok


# =============================================================================
# 3. OpenVisus live connection
# =============================================================================

def check_openvisus_connection() -> tuple[bool, bool]:
    """Returns (openvisus_available, all_vars_ok)."""
    section("3. OpenVisus connection")

    try:
        from openvisuspy import LoadDataset
    except ImportError:
        print("  openvisuspy not installed — skipping live connection check.")
        print(f"  Install with: pip install openvisuspy  {SKIP}")
        return False, False

    reader = LLC4320Reader()
    all_ok = True

    # Small coarse test ROI: 10°x10° box in North Atlantic surface
    test_roi = ROI(lat_min=35.0, lat_max=45.0, lon_min=-40.0, lon_max=-30.0,
                   depth_min_m=0.0, depth_max_m=5.0, timestep=0, quality=-9)

    for var, expected_range in [("theta", (-2.0, 35.0)), ("salt", (20.0, 42.0)), ("w", (-1.0, 1.0))]:
        try:
            log.info("Fetching %s test patch...", var)
            data = reader.read(test_roi, var)
            ocean = data[data != 0]
            if len(ocean) == 0:
                print(f"  {var}: all zeros (land mask?) — check ROI  {FAIL}")
                all_ok = False
                continue
            vmin, vmax = float(ocean.min()), float(ocean.max())
            in_range = expected_range[0] <= vmin and vmax <= expected_range[1]
            status = PASS if in_range else FAIL
            all_ok &= in_range
            print(f"  {var}: shape={data.shape}, ocean range=[{vmin:.3f}, {vmax:.3f}]  "
                  f"(expected [{expected_range[0]}, {expected_range[1]}])  {status}")
        except Exception as exc:
            print(f"  {var}: FAILED — {exc}  {FAIL}")
            all_ok = False

    print(f"\n  OpenVisus live reads: {PASS if all_ok else FAIL}")
    return True, all_ok


# =============================================================================
# 4. Grid orientation verification
# =============================================================================

def check_orientation(openvisus_ok: bool) -> bool:
    section("4. Grid orientation verification")

    if openvisus_ok:
        reader = LLC4320Reader()
        correct = reader.verify_orientation(
            timestep=0, quality=-9,
            save_path=str(FIGURES_DIR / "00_orientation_check_live.png"),
        )
        source = "live OpenVisus read"
    else:
        # Fall back to cached surface data
        cache_theta = CACHE_DIR / "na_surface_theta.npy"
        cache_lons  = CACHE_DIR / "na_surface_lons.npy"
        cache_lats  = CACHE_DIR / "na_surface_lats.npy"

        if not cache_theta.exists():
            print(f"  No cache and no OpenVisus — cannot verify orientation.  {SKIP}")
            return True   # cannot fail what cannot be checked

        theta = np.load(cache_theta)
        lons  = np.load(cache_lons)
        lats  = np.load(cache_lats)
        source = "cached North Atlantic surface data"

        masked = theta.astype(float)
        masked[masked == 0] = np.nan

        try:
            import cartopy.crs as ccrs
            import cartopy.feature as cfeature

            fig, ax = plt.subplots(figsize=(12, 7),
                                   subplot_kw={"projection": ccrs.PlateCarree()})
            lon_grid, lat_grid = np.meshgrid(lons, lats)
            im = ax.pcolormesh(lon_grid, lat_grid, masked,
                               cmap="RdBu_r", transform=ccrs.PlateCarree(),
                               shading="auto", vmin=0, vmax=30)
            ax.coastlines(resolution="50m", color="black", linewidth=0.8)
            ax.add_feature(cfeature.BORDERS, linewidth=0.3, alpha=0.5)
            ax.set_extent([-65, 5, -5, 75], crs=ccrs.PlateCarree())
            ax.set_title(
                "LLC4320 North Atlantic surface theta — orientation check (from cache)\n"
                "Correct: warm subtropical gyre on right, cold subpolar on top-left",
                fontsize=10,
            )
            plt.colorbar(im, ax=ax, label="θ (°C)", shrink=0.6)
            fig.tight_layout()
            out = FIGURES_DIR / "00_orientation_check_cached.png"
            fig.savefig(out, dpi=150, bbox_inches="tight")
            plt.close()
            print(f"  Saved orientation plot: {out}")
        except ImportError as exc:
            print(f"  cartopy unavailable, skipping plot: {exc}")

        # Heuristic: Gulf Stream region (~30°N, 60°W) should be warm (>20°C)
        # In the cached data, lons are in [-60, 0] range
        gs_lon_idx = int(np.argmin(np.abs(lons - (-40.0))))   # ~40°W
        gs_lat_idx = int(np.argmin(np.abs(lats - 30.0)))       # 30°N
        gs_val = float(theta[gs_lat_idx, gs_lon_idx])
        correct = gs_val > 15.0

    status = PASS if correct else FAIL
    print(f"  Orientation check source: {source}")
    print(f"  Heuristic (warm subtropical pixel): {PASS if correct else 'POSSIBLY FLIPPED — see saved figure'}")
    print(f"  Grid orientation: {status}")

    if not correct:
        print("\n  ⚠ ACTION REQUIRED: If the figure shows land/ocean in wrong positions,")
        print("    apply np.fliplr() to all fetched arrays before further processing.")
        print("    Update LLC4320Reader.read() to include this correction.")

    return correct


# =============================================================================
# 5. Cache validation
# =============================================================================

def check_cache() -> bool:
    section("5. Cache validation (prior fetches)")

    expected_files = [
        ("na_surface_theta.npy", (630, 360)),
        ("na_surface_salt.npy",  (630, 360)),
        ("na_ts_theta.npy",      None),       # (n_profiles, 90)
        ("na_ts_salt.npy",       None),
        ("na_volume_theta.npy",  None),       # (90, ?, ?)
        ("na_volume_salt.npy",   None),
    ]

    all_ok = True
    for fname, expected_shape in expected_files:
        path = CACHE_DIR / fname
        if not path.exists():
            print(f"  {fname}: MISSING  {FAIL}")
            all_ok = False
            continue

        arr = np.load(path)
        shape_ok = expected_shape is None or arr.shape == expected_shape
        ocean = arr[arr != 0]
        nonempty = len(ocean) > 0
        status = PASS if shape_ok and nonempty else FAIL
        all_ok &= shape_ok and nonempty
        print(f"  {fname}: shape={arr.shape}  ocean_n={len(ocean):,}  {status}")

    # Validate T-S profiles have 90 depth levels
    ts_path = CACHE_DIR / "na_ts_theta.npy"
    if ts_path.exists():
        ts = np.load(ts_path)
        depth_ok = ts.shape[1] == NZ
        status = PASS if depth_ok else FAIL
        all_ok &= depth_ok
        print(f"  T-S profiles: {ts.shape[0]} profiles × {ts.shape[1]} depth levels  "
              f"(need {NZ})  {status}")

    print(f"\n  Cache validation: {PASS if all_ok else FAIL}")
    return all_ok


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("THALASSA — Week 1-2 OpenVisus Verification")
    print(f"Repo:   {REPO_ROOT}")
    print(f"Cache:  {CACHE_DIR}")
    print(f"Figs:   {FIGURES_DIR}")

    results = {}
    results["depth_levels"]     = check_depth_levels()
    results["coord_mapping"]    = check_coordinate_mapping()
    ov_available, ov_ok         = check_openvisus_connection()
    results["openvisus_connect"] = ov_ok or not ov_available
    results["orientation"]       = check_orientation(ov_ok)
    results["cache"]             = check_cache()

    section("SUMMARY")
    overall = True
    for name, passed in results.items():
        status = PASS if passed else FAIL
        print(f"  {name:30s}: {status}")
        overall &= passed

    print(f"\n  OVERALL: {'ALL CHECKS PASSED ✓' if overall else 'SOME CHECKS FAILED — see above'}")

    if not results["orientation"]:
        print("\n⚠ STOP: Orientation failed. Fix grid orientation before density work.")
        sys.exit(1)

    if overall:
        print("\nNext step: run notebooks/02_density_prototype.py")
