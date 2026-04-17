"""
03_cross_section.py — Vertical cross-section visualization.

Run with: conda activate ocean && python notebooks/03_cross_section.py

Produces publication-quality figures showing temperature and salinity
structure vs. depth along North Atlantic transects.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import cmocean

from data_access_llc4320 import (
    cache_load, mask_land, print_data_summary, DEPTH_LEVELS, NZ,
)

FIGURES_DIR = os.path.join(os.path.dirname(__file__), "..", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)


def plot_cross_section(theta, salt, lons, lat_label,
                       depth_limit=5000, figname=None):
    """Plot a vertical cross-section: temperature fill + salinity contours.

    Args:
        theta: 2D array (depth, lon), temperature in °C
        salt: 2D array (depth, lon), salinity in g/kg
        lons: 1D array of longitudes
        lat_label: string label for the latitude (e.g., "30°N")
        depth_limit: max depth to display (meters)
        figname: filename to save (or None for no save)
    """
    # Mask land values
    theta_m = mask_land(theta.copy())
    salt_m = mask_land(salt.copy())

    # Build depth axis — the data has NZ=90 depth levels but the fetched
    # array may be subsampled. Map array rows to actual depths.
    n_depth, n_lon = theta_m.shape
    if n_depth == NZ:
        depths = DEPTH_LEVELS
    else:
        # Interpolate depth levels for subsampled data
        z_indices = np.linspace(0, NZ - 1, n_depth)
        depths = np.interp(z_indices, np.arange(NZ), DEPTH_LEVELS)

    # Trim to depth limit
    depth_mask = depths <= depth_limit
    depths_plot = depths[depth_mask]
    theta_plot = theta_m[depth_mask, :]
    salt_plot = salt_m[depth_mask, :]

    # Create figure with two panels (side-by-side)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7), sharey=True)

    # --- Temperature panel ---
    lon_grid, depth_grid = np.meshgrid(lons, depths_plot)

    # Temperature colormap levels
    t_min, t_max = np.nanmin(theta_plot), np.nanmax(theta_plot)
    t_levels = np.linspace(max(t_min, 0), min(t_max, 30), 25)

    cf1 = ax1.contourf(lon_grid, depth_grid, theta_plot,
                       levels=t_levels, cmap=cmocean.cm.thermal, extend="both")
    # Add contour lines
    t_contour_levels = np.arange(0, 31, 2)
    cs1 = ax1.contour(lon_grid, depth_grid, theta_plot,
                      levels=t_contour_levels, colors="k", linewidths=0.4, alpha=0.5)
    ax1.clabel(cs1, inline=True, fontsize=7, fmt="%.0f°C")

    cb1 = plt.colorbar(cf1, ax=ax1, shrink=0.8, pad=0.02)
    cb1.set_label("Temperature (°C)", fontsize=11)
    ax1.set_title(f"Temperature at {lat_label}", fontsize=13, fontweight="bold")
    ax1.set_xlabel("Longitude (°E)", fontsize=11)
    ax1.set_ylabel("Depth (m)", fontsize=11)

    # --- Salinity panel ---
    s_min, s_max = np.nanmin(salt_plot), np.nanmax(salt_plot)
    s_levels = np.linspace(max(s_min, 33), min(s_max, 37.5), 25)

    cf2 = ax2.contourf(lon_grid, depth_grid, salt_plot,
                       levels=s_levels, cmap=cmocean.cm.haline, extend="both")
    s_contour_levels = np.arange(33, 38, 0.2)
    cs2 = ax2.contour(lon_grid, depth_grid, salt_plot,
                      levels=s_contour_levels, colors="k", linewidths=0.4, alpha=0.5)
    ax2.clabel(cs2, inline=True, fontsize=7, fmt="%.1f")

    cb2 = plt.colorbar(cf2, ax=ax2, shrink=0.8, pad=0.02)
    cb2.set_label("Salinity (g/kg)", fontsize=11)
    ax2.set_title(f"Salinity at {lat_label}", fontsize=13, fontweight="bold")
    ax2.set_xlabel("Longitude (°E)", fontsize=11)

    # Shared y-axis formatting
    for ax in (ax1, ax2):
        ax.invert_yaxis()
        ax.set_ylim(depth_limit, 0)
        ax.tick_params(labelsize=10)
        ax.grid(True, alpha=0.15, linestyle="--")

        # Mark key oceanographic depths
        for d, label in [(200, "Mixed layer"), (1000, "Thermocline base")]:
            if d <= depth_limit:
                ax.axhline(d, color="gray", linestyle=":", alpha=0.4, linewidth=0.8)

    fig.suptitle(f"North Atlantic Vertical Cross-Section — {lat_label}",
                 fontsize=15, fontweight="bold", y=1.02)
    fig.tight_layout()

    if figname:
        path = os.path.join(FIGURES_DIR, figname)
        fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
        print(f"Saved: {path}")
    plt.close()


def plot_combined_cross_section(theta, salt, lons, lat_label,
                                depth_limit=5000, figname=None):
    """Single-panel cross-section: temperature fill + salinity contour overlay.

    This is the publication figure — temperature as the primary variable
    with salinity contours overlaid to show the relationship.
    """
    theta_m = mask_land(theta.copy())
    salt_m = mask_land(salt.copy())

    n_depth, n_lon = theta_m.shape
    if n_depth == NZ:
        depths = DEPTH_LEVELS
    else:
        z_indices = np.linspace(0, NZ - 1, n_depth)
        depths = np.interp(z_indices, np.arange(NZ), DEPTH_LEVELS)

    depth_mask = depths <= depth_limit
    depths_plot = depths[depth_mask]
    theta_plot = theta_m[depth_mask, :]
    salt_plot = salt_m[depth_mask, :]

    lon_grid, depth_grid = np.meshgrid(lons, depths_plot)

    fig, ax = plt.subplots(figsize=(14, 6))

    # Temperature fill
    t_min, t_max = np.nanmin(theta_plot), np.nanmax(theta_plot)
    t_levels = np.linspace(max(t_min, 0), min(t_max, 30), 30)
    cf = ax.contourf(lon_grid, depth_grid, theta_plot,
                     levels=t_levels, cmap=cmocean.cm.thermal, extend="both")

    # Salinity contours
    s_contour_levels = np.arange(34.0, 37.0, 0.2)
    cs = ax.contour(lon_grid, depth_grid, salt_plot,
                    levels=s_contour_levels, colors="white", linewidths=0.7, alpha=0.8)
    ax.clabel(cs, inline=True, fontsize=7, fmt="%.1f psu",
              colors="white")

    cb = plt.colorbar(cf, ax=ax, shrink=0.85, pad=0.02)
    cb.set_label("Temperature (°C)", fontsize=12)

    ax.invert_yaxis()
    ax.set_ylim(depth_limit, 0)
    ax.set_xlabel("Longitude (°E)", fontsize=12)
    ax.set_ylabel("Depth (m)", fontsize=12)
    ax.set_title(f"North Atlantic Meridional Cross-Section at {lat_label}\n"
                 f"Temperature (color) + Salinity Contours (white lines, psu)",
                 fontsize=13, fontweight="bold")
    ax.tick_params(labelsize=10)
    ax.grid(True, alpha=0.1, linestyle="--")

    # Annotate ocean layers
    ax.annotate("Surface / Mixed Layer", xy=(lons.mean(), 50),
                fontsize=9, color="white", ha="center", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", fc="black", alpha=0.3))
    if depth_limit >= 1500:
        ax.annotate("NADW", xy=(lons.mean(), 2500),
                    fontsize=9, color="white", ha="center", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", fc="black", alpha=0.3))

    fig.tight_layout()
    if figname:
        path = os.path.join(FIGURES_DIR, figname)
        fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
        print(f"Saved: {path}")
    plt.close()


# =================================================================
# MAIN
# =================================================================
if __name__ == "__main__":
    print("Building cross-section figures...")

    # Load cross-section coordinates
    lons = cache_load("na_cross_lons")
    if lons is None:
        print("ERROR: Run 02_cache_north_atlantic.py first!")
        sys.exit(1)

    # Generate figures for each transect latitude
    for lat_val in [30, 50, 60]:
        theta = cache_load(f"na_cross_theta_{lat_val}N")
        salt = cache_load(f"na_cross_salt_{lat_val}N")

        if theta is None or salt is None:
            print(f"  Skipping {lat_val}°N — data not cached yet")
            continue

        print(f"\n--- {lat_val}°N transect ---")
        print_data_summary(mask_land(theta), f"  theta_{lat_val}N")
        print_data_summary(mask_land(salt), f"  salt_{lat_val}N")

        # Side-by-side panels
        plot_cross_section(theta, salt, lons, f"{lat_val}°N",
                           depth_limit=5000,
                           figname=f"cross_section_{lat_val}N.png")

        # Combined (publication figure)
        plot_combined_cross_section(theta, salt, lons, f"{lat_val}°N",
                                   depth_limit=5000,
                                   figname=f"cross_combined_{lat_val}N.png")

        # Upper ocean zoom (0-1000m) to show thermocline detail
        plot_cross_section(theta, salt, lons, f"{lat_val}°N (upper ocean)",
                           depth_limit=1000,
                           figname=f"cross_section_{lat_val}N_upper.png")

    print("\nDone! Check figures/ directory.")
