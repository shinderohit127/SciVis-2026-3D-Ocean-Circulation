"""
01_connection_test.py — Verify LLC4320 data access and grid alignment.

Run with: conda activate ocean && python notebooks/01_connection_test.py

This script:
  1. Connects to the LLC4320 theta dataset
  2. Fetches a coarse global surface temperature map
  3. Plots it with cartopy coastlines to verify lat/lon alignment
  4. Fetches a depth profile at a known ocean point to verify 3D access
  5. Saves diagnostic figures to figures/

If the coastlines don't align, we need to adjust LAT_MIN/LAT_MAX/LON_MIN/LON_MAX
in data_access_llc4320.py.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for WSL

from data_access_llc4320 import (
    get_db, get_dataset_info, read_surface, read_depth_profile,
    mask_land, print_data_summary, DEPTH_LEVELS,
    LON_MIN, LON_MAX, LAT_MIN, LAT_MAX, DLON, DLAT, NX, NY,
    cache_save, cache_load, cache_or_fetch,
)

FIGURES_DIR = os.path.join(os.path.dirname(__file__), "..", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)


def test_1_connection():
    """Test basic connection and metadata."""
    print("=" * 60)
    print("TEST 1: Connection + Metadata")
    print("=" * 60)
    box = get_dataset_info("theta")
    print(f"Logic box: {box}")
    print()


def test_2_global_surface(quality=-8):
    """Fetch global surface temperature and plot with coastlines."""
    print("=" * 60)
    print(f"TEST 2: Global surface theta (quality={quality})")
    print("=" * 60)

    # Fetch (or load from cache)
    cache_name = f"test_global_surface_q{abs(quality)}"
    data = cache_or_fetch(cache_name, lambda: read_surface("theta", quality=quality))
    print_data_summary(data, "Raw surface theta")

    # Mask land
    data_masked = mask_land(data, fill_value=0.0)
    print_data_summary(data_masked, "Masked surface theta")

    # Plot WITHOUT cartopy first (raw pixel coords)
    fig, ax = plt.subplots(figsize=(14, 8))
    im = ax.imshow(data_masked, origin="lower", cmap="turbo", aspect="auto")
    plt.colorbar(im, ax=ax, label="Temperature (°C)")
    ax.set_title(f"LLC4320 Surface Temperature (raw pixels, quality={quality})")
    ax.set_xlabel("x pixel")
    ax.set_ylabel("y pixel")
    fig.savefig(os.path.join(FIGURES_DIR, "test_01_raw_pixels.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: test_01_raw_pixels.png")

    # Plot WITH cartopy coastlines
    try:
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature

        # Create lon/lat arrays based on our assumed mapping
        n_lat, n_lon = data_masked.shape
        lons = np.linspace(LON_MIN, LON_MAX, n_lon, endpoint=False)
        lats = np.linspace(LAT_MIN, LAT_MAX, n_lat, endpoint=False)

        # Convert lons to [-180, 180] for cartopy
        lons_shifted = np.where(lons > 180, lons - 360, lons)

        fig, ax = plt.subplots(
            figsize=(16, 8),
            subplot_kw={"projection": ccrs.PlateCarree()}
        )
        # Use pcolormesh for geographic plotting
        lon_grid, lat_grid = np.meshgrid(lons_shifted, lats)
        im = ax.pcolormesh(
            lon_grid, lat_grid, data_masked,
            cmap="turbo", transform=ccrs.PlateCarree(),
            shading="auto",
        )
        ax.coastlines(resolution="110m", color="black", linewidth=0.8)
        ax.add_feature(cfeature.BORDERS, linewidth=0.3, edgecolor="gray")
        ax.set_global()
        plt.colorbar(im, ax=ax, label="Temperature (°C)", shrink=0.6)
        ax.set_title(f"LLC4320 Surface Temperature with Coastlines (quality={quality})")
        fig.savefig(
            os.path.join(FIGURES_DIR, "test_02_coastline_overlay.png"),
            dpi=150, bbox_inches="tight"
        )
        plt.close()
        print(f"Saved: test_02_coastline_overlay.png")
        print(">>> CHECK THIS FIGURE: Do coastlines align with the data? <<<")

    except ImportError:
        print("Cartopy not available — skipping coastline overlay test")

    return data_masked


def test_3_depth_profile():
    """Fetch a depth profile at a known ocean point."""
    print()
    print("=" * 60)
    print("TEST 3: Depth profile at mid-Atlantic (30°N, 40°W)")
    print("=" * 60)

    # Mid-Atlantic point — should be deep ocean
    test_lon = -40.0
    test_lat = 30.0

    print(f"Fetching depth profile at ({test_lat}°N, {test_lon}°E)...")
    try:
        profile = read_depth_profile("theta", lon=test_lon, lat=test_lat, quality=-6)
        print_data_summary(profile, f"Depth profile at ({test_lat}°N, {test_lon}°)")

        # Plot temperature vs depth
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

        # Full depth range
        ax1.plot(profile, DEPTH_LEVELS, "b.-", linewidth=1.5, markersize=4)
        ax1.invert_yaxis()
        ax1.set_xlabel("Temperature (°C)")
        ax1.set_ylabel("Depth (m)")
        ax1.set_title(f"Temperature Profile at {test_lat}°N, {test_lon}°E")
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=200, color="gray", linestyle="--", alpha=0.5, label="Mixed layer (~200m)")
        ax1.axhline(y=1000, color="gray", linestyle=":", alpha=0.5, label="Thermocline base (~1000m)")
        ax1.legend(fontsize=8)

        # Upper ocean zoom (0-1000m)
        ax2.plot(profile[:50], DEPTH_LEVELS[:50], "r.-", linewidth=1.5, markersize=4)
        ax2.invert_yaxis()
        ax2.set_xlabel("Temperature (°C)")
        ax2.set_ylabel("Depth (m)")
        ax2.set_title(f"Upper Ocean (0-1000m)")
        ax2.grid(True, alpha=0.3)

        fig.suptitle("LLC4320 Depth Profile Test", fontsize=14)
        fig.tight_layout()
        fig.savefig(os.path.join(FIGURES_DIR, "test_03_depth_profile.png"), dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Saved: test_03_depth_profile.png")

        # Sanity check: surface should be warm, deep should be cold
        if profile[0] > 10 and profile[-1] < 5:
            print("✓ Profile looks physically reasonable (warm surface, cold deep)")
        elif profile[0] == 0.0:
            print("✗ Surface value is 0.0 — this point might be on land!")
        else:
            print(f"? Surface={profile[0]:.1f}°C, Deep={profile[-1]:.1f}°C — check if reasonable")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


def test_4_salt_surface(quality=-8):
    """Quick check that salinity data also works."""
    print()
    print("=" * 60)
    print("TEST 4: Surface salinity check")
    print("=" * 60)

    try:
        data = cache_or_fetch(
            f"test_salt_surface_q{abs(quality)}",
            lambda: read_surface("salt", quality=quality)
        )
        data_masked = mask_land(data, fill_value=0.0)
        print_data_summary(data_masked, "Surface salinity")

        fig, ax = plt.subplots(figsize=(14, 8))
        im = ax.imshow(data_masked, origin="lower", cmap="viridis", aspect="auto",
                        vmin=30, vmax=38)
        plt.colorbar(im, ax=ax, label="Salinity (g/kg)")
        ax.set_title(f"LLC4320 Surface Salinity (quality={quality})")
        fig.savefig(os.path.join(FIGURES_DIR, "test_04_salt_surface.png"), dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Saved: test_04_salt_surface.png")

        # Sanity: ocean salinity should be ~33-37
        valid = data_masked[~np.isnan(data_masked)]
        if len(valid) > 0 and 30 < np.nanmean(valid) < 40:
            print("✓ Salinity values look reasonable")
        else:
            print(f"? Mean salinity = {np.nanmean(valid):.1f} — check units")

    except Exception as e:
        print(f"ERROR fetching salinity: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("LLC4320 Connection Test")
    print("Working directory:", os.getcwd())
    print()

    test_1_connection()
    surface = test_2_global_surface(quality=-8)
    test_3_depth_profile()
    test_4_salt_surface(quality=-8)

    print()
    print("=" * 60)
    print("ALL TESTS COMPLETE")
    print("Check figures/ directory for output plots.")
    print("CRITICAL: Verify test_02_coastline_overlay.png for grid alignment!")
    print("=" * 60)
