"""
04_ts_diagram.py — Temperature-Salinity diagram with density contours.

Run with: conda activate ocean && python notebooks/04_ts_diagram.py

Produces publication-quality T-S diagrams showing:
  - Temperature vs. salinity scatter, colored by depth
  - Density contours (isopycnals) computed with GSW library
  - Annotated water mass regions (NADW, AAIW, Surface Water, AABW)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import cmocean
import gsw

from data_access_llc4320 import cache_load, DEPTH_LEVELS, NZ

FIGURES_DIR = os.path.join(os.path.dirname(__file__), "..", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)


# =================================================================
# WATER MASS DEFINITIONS (from physical oceanography literature)
# =================================================================
WATER_MASSES = {
    "Surface Water": {
        "s_range": (34.5, 37.5), "t_range": (15, 30),
        "color": "#e74c3c", "depth": "0–200m",
    },
    "AAIW": {  # Antarctic Intermediate Water
        "s_range": (34.0, 34.6), "t_range": (2, 6),
        "color": "#2ecc71", "depth": "500–1000m",
    },
    "NADW": {  # North Atlantic Deep Water
        "s_range": (34.8, 35.1), "t_range": (1.5, 4),
        "color": "#3498db", "depth": "1500–4000m",
    },
    "AABW": {  # Antarctic Bottom Water
        "s_range": (34.6, 34.72), "t_range": (-0.5, 1.5),
        "color": "#9b59b6", "depth": "4000m+",
    },
}


def compute_density_grid(s_range=(33, 38), t_range=(-2, 32), n=200):
    """Compute potential density (sigma-0) on a regular S-T grid.

    Uses GSW (TEOS-10) to compute density from Absolute Salinity
    and Conservative Temperature. For the LLC4320 dataset, the variables
    are close enough to practical salinity and potential temperature
    that we can use them directly for visualization purposes.

    Returns:
        S_grid, T_grid: meshgrid arrays
        sigma0: potential density anomaly (kg/m³ - 1000)
    """
    S_arr = np.linspace(s_range[0], s_range[1], n)
    T_arr = np.linspace(t_range[0], t_range[1], n)
    S_grid, T_grid = np.meshgrid(S_arr, T_arr)

    # gsw.sigma0 expects SA (Absolute Salinity) and CT (Conservative Temperature)
    # For visualization, practical salinity ≈ absolute salinity (±0.2 g/kg)
    # and potential temperature ≈ conservative temperature
    sigma0 = gsw.sigma0(S_grid, T_grid)

    return S_grid, T_grid, sigma0


def plot_ts_diagram(theta_profiles, salt_profiles, profile_lats=None,
                    lat_range=None, title_suffix="", figname=None):
    """Plot a T-S diagram with density contours and water mass annotations.

    Args:
        theta_profiles: (n_profiles, n_depths) array of temperature
        salt_profiles: (n_profiles, n_depths) array of salinity
        profile_lats: optional (n_profiles,) array of latitudes for filtering
        lat_range: optional (lat_min, lat_max) to filter profiles
        title_suffix: extra text for the title
        figname: output filename
    """
    # Filter by latitude if requested
    if profile_lats is not None and lat_range is not None:
        mask = (profile_lats >= lat_range[0]) & (profile_lats <= lat_range[1])
        theta_profiles = theta_profiles[mask]
        salt_profiles = salt_profiles[mask]
        profile_lats = profile_lats[mask]
        print(f"  Filtered to {mask.sum()} profiles in lat range {lat_range}")

    n_profiles, n_depths = theta_profiles.shape

    # Map depth index to actual depth in meters
    if n_depths == NZ:
        depths = DEPTH_LEVELS
    else:
        z_indices = np.linspace(0, NZ - 1, n_depths)
        depths = np.interp(z_indices, np.arange(NZ), DEPTH_LEVELS)

    # Flatten all profiles into single arrays
    theta_flat = theta_profiles.ravel()
    salt_flat = salt_profiles.ravel()
    depth_flat = np.tile(depths, n_profiles)

    # Remove land/missing values (zeros or very low salinity)
    valid = (theta_flat != 0) & (salt_flat > 1) & np.isfinite(theta_flat) & np.isfinite(salt_flat)
    theta_v = theta_flat[valid]
    salt_v = salt_flat[valid]
    depth_v = depth_flat[valid]

    print(f"  T-S diagram: {len(theta_v)} valid points from {n_profiles} profiles")

    # Compute density grid for contours
    s_min, s_max = max(salt_v.min() - 0.5, 33), min(salt_v.max() + 0.5, 38)
    t_min, t_max = max(theta_v.min() - 1, -2), min(theta_v.max() + 1, 32)
    S_grid, T_grid, sigma0 = compute_density_grid(
        s_range=(s_min, s_max), t_range=(t_min, t_max)
    )

    # ── Figure ──
    fig, ax = plt.subplots(figsize=(10, 8))

    # Density contours (isopycnals)
    density_levels = np.arange(20, 30, 0.5)
    cs = ax.contour(S_grid, T_grid, sigma0,
                    levels=density_levels, colors="gray", linewidths=0.6, alpha=0.6)
    ax.clabel(cs, inline=True, fontsize=7, fmt="σ₀=%.1f")

    # Scatter plot: each point colored by depth
    sc = ax.scatter(salt_v, theta_v,
                    c=depth_v, cmap=cmocean.cm.deep,
                    s=1.5, alpha=0.3, edgecolors="none",
                    norm=matplotlib.colors.LogNorm(vmin=1, vmax=6000))

    cb = plt.colorbar(sc, ax=ax, shrink=0.8, pad=0.02)
    cb.set_label("Depth (m)", fontsize=12)
    cb.ax.invert_yaxis()

    # Water mass annotation boxes
    for name, wm in WATER_MASSES.items():
        s0, s1 = wm["s_range"]
        t0, t1 = wm["t_range"]
        # Only draw if within plot range
        if s1 < s_min or s0 > s_max or t1 < t_min or t0 > t_max:
            continue
        rect = mpatches.FancyBboxPatch(
            (s0, t0), s1 - s0, t1 - t0,
            boxstyle="round,pad=0.02",
            linewidth=1.5, edgecolor=wm["color"], facecolor="none",
            linestyle="--", alpha=0.8,
        )
        ax.add_patch(rect)
        # Label inside the box
        ax.text(
            (s0 + s1) / 2, t1 - 0.3 * (t1 - t0),
            f"{name}\n({wm['depth']})",
            ha="center", va="top", fontsize=8, fontweight="bold",
            color=wm["color"],
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.7),
        )

    ax.set_xlabel("Salinity (g/kg)", fontsize=13)
    ax.set_ylabel("Temperature (°C)", fontsize=13)
    ax.set_xlim(s_min, s_max)
    ax.set_ylim(t_min, t_max)
    ax.set_title(f"T-S Diagram — North Atlantic{title_suffix}\n"
                 f"({n_profiles} profiles, σ₀ isopycnal contours in gray)",
                 fontsize=14, fontweight="bold")
    ax.tick_params(labelsize=11)
    ax.grid(True, alpha=0.15, linestyle="--")

    fig.tight_layout()
    if figname:
        path = os.path.join(FIGURES_DIR, figname)
        fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
        print(f"  Saved: {path}")
    plt.close()


def plot_ts_by_latitude_bands(theta_profiles, salt_profiles, profile_lats,
                              figname=None):
    """Plot T-S diagrams for different latitude bands side by side.

    Shows how water mass properties change from tropics to subpolar regions.
    """
    bands = [
        (0, 20, "Tropical (0–20°N)"),
        (20, 45, "Subtropical (20–45°N)"),
        (45, 70, "Subpolar (45–70°N)"),
    ]

    n_depths = theta_profiles.shape[1]
    if n_depths == NZ:
        depths = DEPTH_LEVELS
    else:
        z_indices = np.linspace(0, NZ - 1, n_depths)
        depths = np.interp(z_indices, np.arange(NZ), DEPTH_LEVELS)

    # Density grid
    S_grid, T_grid, sigma0 = compute_density_grid(s_range=(33, 38), t_range=(-2, 32))

    fig, axes = plt.subplots(1, 3, figsize=(18, 7), sharey=True, sharex=True)

    for ax, (lat_lo, lat_hi, label) in zip(axes, bands):
        mask = (profile_lats >= lat_lo) & (profile_lats < lat_hi)
        t_sel = theta_profiles[mask]
        s_sel = salt_profiles[mask]

        t_flat = t_sel.ravel()
        s_flat = s_sel.ravel()
        d_flat = np.tile(depths, mask.sum())

        valid = (t_flat != 0) & (s_flat > 1) & np.isfinite(t_flat) & np.isfinite(s_flat)

        # Isopycnals
        density_levels = np.arange(22, 29, 0.5)
        cs = ax.contour(S_grid, T_grid, sigma0,
                        levels=density_levels, colors="gray", linewidths=0.5, alpha=0.5)
        ax.clabel(cs, inline=True, fontsize=6, fmt="%.1f")

        # Scatter
        sc = ax.scatter(
            s_flat[valid], t_flat[valid],
            c=d_flat[valid], cmap=cmocean.cm.deep,
            s=1.5, alpha=0.3, edgecolors="none",
            norm=matplotlib.colors.LogNorm(vmin=1, vmax=6000),
        )
        ax.set_title(f"{label}\n({mask.sum()} profiles)", fontsize=11, fontweight="bold")
        ax.set_xlabel("Salinity (g/kg)", fontsize=10)
        ax.grid(True, alpha=0.15, linestyle="--")
        ax.set_xlim(33.5, 37.5)
        ax.set_ylim(-1, 30)

        # Water mass boxes
        for name, wm in WATER_MASSES.items():
            s0, s1 = wm["s_range"]
            t0, t1 = wm["t_range"]
            rect = mpatches.FancyBboxPatch(
                (s0, t0), s1 - s0, t1 - t0,
                boxstyle="round,pad=0.02",
                linewidth=1.2, edgecolor=wm["color"], facecolor="none",
                linestyle="--", alpha=0.6,
            )
            ax.add_patch(rect)

    axes[0].set_ylabel("Temperature (°C)", fontsize=11)

    # Shared colorbar
    cbar_ax = fig.add_axes([0.92, 0.15, 0.015, 0.7])
    cb = plt.colorbar(sc, cax=cbar_ax)
    cb.set_label("Depth (m)", fontsize=11)
    cb.ax.invert_yaxis()

    fig.suptitle("T-S Diagrams by Latitude Band — North Atlantic",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout(rect=[0, 0, 0.91, 1])

    if figname:
        path = os.path.join(FIGURES_DIR, figname)
        fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
        print(f"  Saved: {path}")
    plt.close()


# =================================================================
# MAIN
# =================================================================
if __name__ == "__main__":
    print("Building T-S diagrams...")

    # Load cached profiles
    theta = cache_load("na_ts_theta")
    salt = cache_load("na_ts_salt")
    lats = cache_load("na_ts_lats")
    lons = cache_load("na_ts_lons")

    if theta is None:
        print("ERROR: Run 02_cache_north_atlantic.py first!")
        sys.exit(1)

    print(f"Loaded {theta.shape[0]} profiles, {theta.shape[1]} depth levels each")

    # 1. Full North Atlantic T-S diagram
    print("\n--- Full North Atlantic T-S ---")
    plot_ts_diagram(theta, salt, title_suffix=" (All Profiles)",
                    figname="ts_diagram_full.png")

    # 2. By latitude bands
    print("\n--- T-S by Latitude Bands ---")
    plot_ts_by_latitude_bands(theta, salt, lats,
                              figname="ts_diagram_bands.png")

    # 3. Subpolar focus (45-70°N) — where NADW forms
    print("\n--- Subpolar T-S (NADW formation region) ---")
    plot_ts_diagram(theta, salt, profile_lats=lats,
                    lat_range=(45, 70),
                    title_suffix=" — Subpolar (45–70°N)",
                    figname="ts_diagram_subpolar.png")

    print("\nDone! Check figures/ directory.")
