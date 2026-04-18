"""
02_density_prototype.py — Week 1-2: thermohaline decomposition prototype.

Run from the repo root:
    conda activate thalassa-backend
    python notebooks/02_density_prototype.py

What this produces:
  1. Density ρ (kg/m³) via TEOS-10: SP→SA, θ→CT, then gsw.rho(SA, CT, p).
  2. Thermal density contribution: α * ΔCT (where α = thermal expansion coeff).
  3. Haline density contribution: β * ΔSA (where β = haline contraction coeff).
  4. Compensation index: measure of where thermal and haline effects cancel.
  5. Stratification: ∂ρ/∂z (density gradient with depth).

Figures saved to figures/:
  02a_ts_diagram_with_density.png   — T-S diagram coloured by ρ, with σ₀ contours
  02b_thermal_haline_contributions.png — Depth profiles of thermal vs haline ρ contributions
  02c_compensation_map.png           — Surface compensation index over North Atlantic
  02d_stratification_profiles.png    — N² (Brunt-Väisälä frequency squared) profiles

All computations use the cached North Atlantic T-S profiles (505 profiles × 90 depth
levels). No OpenVisus connection required to run this script.

Validation targets from published literature:
  - North Atlantic Deep Water (NADW): ρ ≈ 1027.7–1027.9 kg/m³, S≈34.9, T≈2–4°C
  - Antarctic Intermediate Water (AAIW): ρ ≈ 1027.2–1027.4 kg/m³, S≈34.2–34.6, T≈2–6°C
  - North Atlantic Surface Water (subtropical gyre): ρ ≈ 1024–1026 kg/m³
  - Stratification: strong N² in thermocline (50–500m), weak below 1000m

metric_version: v0.1.0
"""

import os, sys, logging
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import gsw

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / "cache"
FIGURES_DIR = REPO_ROOT / "figures"
FIGURES_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(REPO_ROOT / "thalassa" / "backend"))

from data_access.depth_levels import DEPTH_LEVELS_M

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

METRIC_VERSION = "v0.1.0"


# =============================================================================
# Load cached data
# =============================================================================

def load_cache() -> dict:
    """Load the cached North Atlantic T-S profiles from prior OpenVisus runs."""
    required = {
        "theta": CACHE_DIR / "na_ts_theta.npy",   # (n_profiles, 90)
        "salt":  CACHE_DIR / "na_ts_salt.npy",
        "lats":  CACHE_DIR / "na_ts_lats.npy",
        "lons":  CACHE_DIR / "na_ts_lons.npy",
    }
    cache = {}
    for key, path in required.items():
        if not path.exists():
            raise FileNotFoundError(
                f"Cache file missing: {path}\n"
                "Run notebooks/02_cache_north_atlantic.py first."
            )
        cache[key] = np.load(path)
        log.info("Loaded %s: shape=%s", key, cache[key].shape)

    n_profiles, n_depths = cache["theta"].shape
    assert n_depths == 90, f"Expected 90 depth levels, got {n_depths}"
    log.info("Loaded %d North Atlantic profiles × %d depth levels", n_profiles, n_depths)
    return cache


# =============================================================================
# TEOS-10 density derivation (the scientific core of THALASSA)
# =============================================================================

def compute_density_fields(theta_profiles: np.ndarray, salt_profiles: np.ndarray,
                           lats: np.ndarray) -> dict:
    """
    Compute density and thermohaline decomposition fields using TEOS-10 (gsw).

    Steps:
      1. SP (practical salinity) → SA (absolute salinity) via gsw.SA_from_SP
      2. θ (potential temperature) → CT (conservative temperature) via gsw.CT_from_pt
      3. Pressure from depth via gsw.p_from_z (z must be negative = metres above datum)
      4. Density: ρ = gsw.rho(SA, CT, p)
      5. Thermal expansion: α = gsw.alpha(SA, CT, p)
         Haline contraction: β = gsw.beta(SA, CT, p)
      6. Reference state: profile-mean SA and CT (representing the "background")
      7. Thermal contribution: Δρ_T = -ρ₀ · α · (CT - CT_ref)
         Haline contribution: Δρ_S = ρ₀ · β · (SA - SA_ref)
      8. Compensation index: CI = |Δρ_T| / (|Δρ_T| + |Δρ_S| + ε)
         CI → 1: density dominated by salinity (T and S compensate in T contribution)
         CI → 0: density dominated by salinity alone
         NOTE: this is a simplified linear compensation index; see PRD §7.1.

    Args:
        theta_profiles: (n_profiles, 90) potential temperature in °C
        salt_profiles:  (n_profiles, 90) practical salinity in g/kg
        lats:           (n_profiles,) latitude in degrees (for SA conversion)

    Returns:
        dict with keys:
          SA, CT, pressure, rho, sigma0, alpha, beta,
          rho_thermal, rho_haline, compensation_index,
          N2_squared, depth_m
    """
    n_profiles, n_z = theta_profiles.shape
    depths = DEPTH_LEVELS_M  # (90,) metres, positive down

    # Broadcast latitude to (n_profiles, n_z) for gsw calls that need it
    lat_2d = np.broadcast_to(lats[:, np.newaxis], (n_profiles, n_z))

    # Pressure from depth (gsw expects negative z = metres ABOVE sea surface)
    z_negative = -depths   # (90,) negative values
    # p_from_z(z, lat) → pressure in dbar; broadcast z and lat
    p_grid = gsw.p_from_z(
        np.broadcast_to(z_negative[np.newaxis, :], (n_profiles, n_z)),
        lat_2d,
    )  # (n_profiles, 90)

    # Longitude placeholder: SA_from_SP also needs longitude for small SAAR correction
    # Use 0°E as a reasonable NA midpoint placeholder (error < 0.01 g/kg)
    lon_placeholder = np.zeros_like(lat_2d)

    # SP → SA
    SA = gsw.SA_from_SP(salt_profiles, p_grid, lon_placeholder, lat_2d)

    # θ → CT
    CT = gsw.CT_from_pt(SA, theta_profiles)

    # In-situ density
    rho = gsw.rho(SA, CT, p_grid)

    # Potential density anomaly σ₀ (referenced to surface pressure, p=0)
    sigma0 = gsw.sigma0(SA, CT)

    # Thermal expansion and haline contraction coefficients
    alpha = gsw.alpha(SA, CT, p_grid)    # 1/°C
    beta  = gsw.beta(SA, CT, p_grid)     # kg/g

    # Reference state: column mean (valid ocean points only)
    valid_mask = (theta_profiles != 0) & (salt_profiles > 1)
    SA_ref = np.where(valid_mask, SA, np.nan)
    CT_ref = np.where(valid_mask, CT, np.nan)
    SA_ref = np.nanmean(SA_ref, axis=1, keepdims=True)  # (n_profiles, 1)
    CT_ref = np.nanmean(CT_ref, axis=1, keepdims=True)

    # Linear density contributions (first-order Taylor expansion)
    rho_ref = np.nanmean(np.where(valid_mask, rho, np.nan), axis=1, keepdims=True)
    rho_thermal = -rho_ref * alpha * (CT - CT_ref)   # temperature drives density down when warm
    rho_haline  =  rho_ref * beta  * (SA - SA_ref)   # salinity drives density up when salty

    # Compensation index (0 = temperature dominates, 1 = salinity dominates compensation)
    abs_T = np.abs(rho_thermal)
    abs_S = np.abs(rho_haline)
    compensation_index = abs_S / (abs_T + abs_S + 1e-10)

    # Stratification: N² = -(g/ρ) dρ/dz  (s⁻²)
    # gsw.Nsquared computes along axis=1 (depth), returning shape (n_profiles, n_z-1).
    # axis=0 is the profile dimension — must specify axis=1 explicitly.
    N2, _p_mid = gsw.Nsquared(SA, CT, p_grid, lat=lat_2d, axis=1)
    # Pad last depth level to restore (n_profiles, n_z) shape
    N2_full = np.concatenate([N2, N2[:, -1:]], axis=1)

    return {
        "SA": SA, "CT": CT, "pressure": p_grid,
        "rho": rho, "sigma0": sigma0,
        "alpha": alpha, "beta": beta,
        "rho_thermal": rho_thermal, "rho_haline": rho_haline,
        "compensation_index": compensation_index,
        "N2_squared": N2_full,
        "depth_m": depths,
        "metric_version": METRIC_VERSION,
    }


# =============================================================================
# Figure 1: T-S diagram with density contours
# =============================================================================

def plot_ts_density(theta_profiles, salt_profiles, fields: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # ── Left: T-S scatter coloured by σ₀ ──────────────────────────────────────
    ax = axes[0]
    valid = (theta_profiles != 0) & (salt_profiles > 1)
    t_v = theta_profiles[valid]
    s_v = salt_profiles[valid]
    sigma0_v = fields["sigma0"][valid]
    depth_v = np.tile(DEPTH_LEVELS_M, theta_profiles.shape[0]).reshape(theta_profiles.shape)[valid]

    sc = ax.scatter(s_v, t_v, c=sigma0_v, cmap="viridis_r", s=1.5, alpha=0.3,
                    edgecolors="none", vmin=24, vmax=28)
    plt.colorbar(sc, ax=ax, label="σ₀ (kg/m³ − 1000)", shrink=0.8)

    # Overlay density contours on the grid
    s_arr = np.linspace(s_v.min() - 0.3, s_v.max() + 0.3, 200)
    t_arr = np.linspace(t_v.min() - 1.0, t_v.max() + 1.0, 200)
    S_g, T_g = np.meshgrid(s_arr, t_arr)
    sigma_g = gsw.sigma0(S_g, T_g)
    density_levels = np.arange(23, 29, 0.5)
    cs = ax.contour(S_g, T_g, sigma_g, levels=density_levels,
                    colors="gray", linewidths=0.6, alpha=0.7)
    ax.clabel(cs, inline=True, fontsize=7, fmt="σ₀=%.1f")

    # Water mass annotations
    water_masses = {
        "NADW":  dict(s=(34.8, 35.1), t=(1.5, 4.0),  color="#2196F3"),
        "AAIW":  dict(s=(34.0, 34.7), t=(2.0, 6.0),  color="#4CAF50"),
        "Surf":  dict(s=(35.0, 37.5), t=(15.0, 30.0), color="#F44336"),
    }
    from matplotlib.patches import FancyBboxPatch
    for name, wm in water_masses.items():
        s0, s1 = wm["s"]; t0, t1 = wm["t"]
        if s1 < s_v.min() or s0 > s_v.max() or t1 < t_v.min() or t0 > t_v.max():
            continue
        ax.add_patch(FancyBboxPatch((s0, t0), s1-s0, t1-t0,
                     boxstyle="round,pad=0.02", lw=1.5, ec=wm["color"],
                     fc="none", ls="--", alpha=0.8))
        ax.text((s0+s1)/2, t1 - 0.2*(t1-t0), name, ha="center", va="top",
                fontsize=8, fontweight="bold", color=wm["color"])

    ax.set_xlabel("Absolute Salinity SA (g/kg)", fontsize=12)
    ax.set_ylabel("Conservative Temperature CT (°C)", fontsize=12)
    ax.set_title(f"T-S Diagram — North Atlantic\nσ₀ isopycnals (gray), water masses annotated\nmetric_version={METRIC_VERSION}", fontsize=10)
    ax.grid(True, alpha=0.2, ls="--")

    # ── Right: T-S coloured by depth ──────────────────────────────────────────
    ax = axes[1]
    sc2 = ax.scatter(s_v, t_v, c=depth_v, cmap="cmo.deep" if _has_cmocean() else "Blues",
                     s=1.5, alpha=0.25, edgecolors="none",
                     norm=mcolors.LogNorm(vmin=5, vmax=6625))
    plt.colorbar(sc2, ax=ax, label="Depth (m)", shrink=0.8)
    cs2 = ax.contour(S_g, T_g, sigma_g, levels=density_levels,
                     colors="gray", linewidths=0.5, alpha=0.5)
    ax.clabel(cs2, inline=True, fontsize=6, fmt="%.1f")

    ax.set_xlabel("Absolute Salinity SA (g/kg)", fontsize=12)
    ax.set_ylabel("Conservative Temperature CT (°C)", fontsize=12)
    ax.set_title("T-S Diagram — coloured by depth\n(isopycnals in gray)", fontsize=10)
    ax.grid(True, alpha=0.2, ls="--")

    fig.suptitle("THALASSA: Thermohaline Phase Space — North Atlantic", fontsize=14, fontweight="bold")
    fig.tight_layout()
    path = FIGURES_DIR / "02a_ts_diagram_with_density.png"
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()
    log.info("Saved: %s", path)


# =============================================================================
# Figure 2: Thermal vs haline contribution profiles
# =============================================================================

def plot_contribution_profiles(fields: dict, theta_profiles: np.ndarray,
                               salt_profiles: np.ndarray, lats: np.ndarray) -> None:
    depths = DEPTH_LEVELS_M
    valid_mask = (theta_profiles != 0) & (salt_profiles > 1)

    # Select latitude bands
    bands = [
        ("Tropical 0–20°N",   (0, 20)),
        ("Subtropical 20–45°N", (20, 45)),
        ("Subpolar 45–70°N",  (45, 70)),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(16, 8), sharey=True)

    for ax, (label, (lat_lo, lat_hi)) in zip(axes, bands):
        bmask = (lats >= lat_lo) & (lats < lat_hi)
        if bmask.sum() == 0:
            continue
        vm = valid_mask[bmask]  # (n_band, 90)

        rho_T = np.where(vm, fields["rho_thermal"][bmask], np.nan)
        rho_S = np.where(vm, fields["rho_haline"][bmask],  np.nan)
        ci    = np.where(vm, fields["compensation_index"][bmask], np.nan)
        N2    = np.where(vm, fields["N2_squared"][bmask],  np.nan)
        n2_mean = np.nanmean(np.abs(N2), axis=0)

        rho_T_mean = np.nanmean(rho_T, axis=0)
        rho_S_mean = np.nanmean(rho_S, axis=0)
        ci_mean    = np.nanmean(ci,    axis=0)

        ax.plot(rho_T_mean, depths, color="#E53935", lw=2, label="ΔρT (thermal)")
        ax.plot(rho_S_mean, depths, color="#1E88E5", lw=2, label="ΔρS (haline)")
        ax.axvline(0, color="black", lw=0.6, ls="--", alpha=0.5)

        ax2 = ax.twiny()
        ax2.plot(ci_mean, depths, color="#43A047", lw=1.5, ls=":", label="Compensation index")
        ax2.set_xlim(0, 1)
        ax2.set_xlabel("Compensation index (0=T-driven, 1=S-driven)", fontsize=8, color="#43A047")
        ax2.tick_params(colors="#43A047")

        ax.set_ylim(6625, 0)  # depth increases downward
        ax.set_xlabel("Density contribution (kg/m³)", fontsize=10)
        ax.set_title(f"{label}\n({bmask.sum()} profiles)", fontsize=10, fontweight="bold")
        ax.grid(True, alpha=0.2, ls="--")
        if ax is axes[0]:
            ax.set_ylabel("Depth (m)", fontsize=11)
            ax.legend(loc="lower right", fontsize=8)

    fig.suptitle(
        "THALASSA: Thermal vs Haline Density Contributions by Latitude Band\n"
        f"North Atlantic, metric_version={METRIC_VERSION}",
        fontsize=12, fontweight="bold",
    )
    fig.tight_layout()
    path = FIGURES_DIR / "02b_thermal_haline_contributions.png"
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()
    log.info("Saved: %s", path)


# =============================================================================
# Figure 3: Compensation index map
# =============================================================================

def plot_compensation_map(fields: dict, theta_profiles: np.ndarray,
                          salt_profiles: np.ndarray, lats: np.ndarray,
                          lons_cache: np.ndarray) -> None:
    """
    Map the depth-mean compensation index at each profile location.
    High CI → salinity is the dominant density driver.
    Low CI  → temperature is the dominant density driver.
    """
    valid_mask = (theta_profiles != 0) & (salt_profiles > 1)
    # Depth-mean CI for each profile (mean over 50–1000m)
    z_50m   = np.argmin(np.abs(DEPTH_LEVELS_M - 50))
    z_1000m = np.argmin(np.abs(DEPTH_LEVELS_M - 1000))

    ci_slice = np.where(valid_mask[:, z_50m:z_1000m+1],
                        fields["compensation_index"][:, z_50m:z_1000m+1], np.nan)
    ci_mean = np.nanmean(ci_slice, axis=1)

    try:
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature

        fig, ax = plt.subplots(figsize=(12, 7),
                               subplot_kw={"projection": ccrs.PlateCarree()})
        sc = ax.scatter(lons_cache, lats, c=ci_mean, cmap="RdBu",
                        vmin=0, vmax=1, s=30, transform=ccrs.PlateCarree(),
                        edgecolors="none", alpha=0.85)
        ax.coastlines(resolution="50m", color="black", linewidth=0.7)
        ax.add_feature(cfeature.LAND, facecolor="lightgray", zorder=0)
        ax.set_extent([-65, 5, -5, 75], crs=ccrs.PlateCarree())
        plt.colorbar(sc, ax=ax, label="Compensation index (50–1000 m mean)\n0=temperature-driven   1=salinity-driven",
                     shrink=0.7)
        ax.set_title(
            f"Thermohaline Compensation Index — North Atlantic\n"
            f"metric_version={METRIC_VERSION}",
            fontsize=12, fontweight="bold",
        )
        fig.tight_layout()
        path = FIGURES_DIR / "02c_compensation_map.png"
        fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
        plt.close()
        log.info("Saved: %s", path)
    except ImportError:
        log.warning("cartopy not available — skipping compensation map")


# =============================================================================
# Figure 4: N² stratification profiles
# =============================================================================

def plot_stratification(fields: dict, theta_profiles: np.ndarray,
                        salt_profiles: np.ndarray, lats: np.ndarray) -> None:
    depths_mid = DEPTH_LEVELS_M   # aligned (we padded N2 to 90 levels)
    valid_mask = (theta_profiles != 0) & (salt_profiles > 1)

    bands = [
        ("Tropical 0–20°N",   (0, 20)),
        ("Subtropical 20–45°N", (20, 45)),
        ("Subpolar 45–70°N",  (45, 70)),
    ]
    colors = ["#E53935", "#FB8C00", "#1E88E5"]

    fig, (ax_full, ax_thermo) = plt.subplots(1, 2, figsize=(14, 8))

    for (label, (lat_lo, lat_hi)), color in zip(bands, colors):
        bmask = (lats >= lat_lo) & (lats < lat_hi)
        if bmask.sum() == 0:
            continue
        vm = valid_mask[bmask]
        N2 = np.where(vm, fields["N2_squared"][bmask], np.nan)
        N2_mean = np.nanmean(N2, axis=0)
        N2_p05 = np.nanpercentile(N2, 5,  axis=0)
        N2_p95 = np.nanpercentile(N2, 95, axis=0)

        for ax, zlim in [(ax_full, 6625), (ax_thermo, 1500)]:
            ax.plot(N2_mean, depths_mid, color=color, lw=2, label=label)
            ax.fill_betweenx(depths_mid, N2_p05, N2_p95, color=color, alpha=0.15)

    for ax, zlim, title in [
        (ax_full,   6625, "Full water column"),
        (ax_thermo, 1500, "Thermocline focus (0–1500 m)"),
    ]:
        ax.set_ylim(zlim, 0)
        ax.set_xlim(left=-1e-5)
        ax.axvline(0, color="black", lw=0.5, ls="--", alpha=0.5)
        ax.set_xlabel("N² (s⁻²)", fontsize=11)
        ax.set_title(title, fontsize=11)
        ax.grid(True, alpha=0.2, ls="--")
        ax.legend(fontsize=9)
        # Mark thermocline depth reference lines
        for d, lbl in [(50, "50m"), (200, "200m"), (500, "500m"), (1000, "1km")]:
            if d <= zlim:
                ax.axhline(d, color="gray", lw=0.4, ls=":", alpha=0.4)
                ax.text(ax.get_xlim()[1] * 0.98, d, lbl, va="center", ha="right",
                        fontsize=7, color="gray")

    ax_full.set_ylabel("Depth (m)", fontsize=11)
    fig.suptitle(
        f"THALASSA: Brunt-Väisälä Frequency N² — North Atlantic\n"
        f"shading = 5th–95th percentile  ·  metric_version={METRIC_VERSION}",
        fontsize=12, fontweight="bold",
    )
    fig.tight_layout()
    path = FIGURES_DIR / "02d_stratification_profiles.png"
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()
    log.info("Saved: %s", path)


# =============================================================================
# Validation against published literature
# =============================================================================

def validate_against_literature(fields: dict, theta_profiles: np.ndarray,
                                 salt_profiles: np.ndarray, lats: np.ndarray) -> bool:
    print("\n" + "=" * 60)
    print("  Validation against published T-S-ρ water mass properties")
    print("=" * 60)

    sigma0 = fields["sigma0"]
    valid = (theta_profiles != 0) & (salt_profiles > 1)
    SA = np.where(valid, fields["SA"], np.nan)
    CT = np.where(valid, fields["CT"], np.nan)
    sig = np.where(valid, sigma0, np.nan)

    # Select NADW depth range: 1500–4000 m
    z_1500 = np.argmin(np.abs(DEPTH_LEVELS_M - 1500))
    z_4000 = np.argmin(np.abs(DEPTH_LEVELS_M - 4000))

    nadw_SA  = np.nanmean(SA[:,  z_1500:z_4000+1])
    nadw_CT  = np.nanmean(CT[:,  z_1500:z_4000+1])
    nadw_sig = np.nanmean(sig[:, z_1500:z_4000+1])

    checks = []

    def check(name, got, lo, hi, unit=""):
        ok = lo <= got <= hi
        flag = "✓" if ok else "✗"
        print(f"  {flag} {name:35s}: {got:.3f} {unit:8s}  expected [{lo}, {hi}]")
        checks.append(ok)

    print("\n  NADW (1500–4000 m mean):")
    check("Absolute Salinity SA", nadw_SA, 34.6, 35.2, "g/kg")
    check("Conservative Temp CT", nadw_CT, 1.0, 5.0, "°C")
    check("σ₀", nadw_sig, 27.5, 28.0, "kg/m³−1000")

    # Surface subtropical gyre (20–45°N, 0–50m)
    z_50m = np.argmin(np.abs(DEPTH_LEVELS_M - 50))
    bmask = (lats >= 20) & (lats <= 45)
    if bmask.sum() > 0:
        surf_SA  = np.nanmean(SA[bmask,  :z_50m+1])
        surf_CT  = np.nanmean(CT[bmask,  :z_50m+1])
        surf_sig = np.nanmean(sig[bmask, :z_50m+1])
        print("\n  Subtropical surface water (20–45°N, 0–50m):")
        check("Absolute Salinity SA", surf_SA, 35.0, 37.5, "g/kg")
        check("Conservative Temp CT", surf_CT, 12.0, 28.0, "°C")
        check("σ₀", surf_sig, 24.0, 27.0, "kg/m³−1000")

    # AAIW-like water (typically appears in NA as 500–1000m, SA~34.2–34.7)
    z_500  = np.argmin(np.abs(DEPTH_LEVELS_M - 500))
    z_1000 = np.argmin(np.abs(DEPTH_LEVELS_M - 1000))
    aaiw_SA = np.nanmean(SA[:, z_500:z_1000+1])
    print("\n  Intermediate water (500–1000 m, all profiles):")
    check("Absolute Salinity SA", aaiw_SA, 33.8, 35.5, "g/kg")

    all_ok = all(checks)
    print(f"\n  Literature validation: {'PASS ✓' if all_ok else 'SOME CHECKS FAILED — review figures'}")
    return all_ok


# =============================================================================
# Helpers
# =============================================================================

def _has_cmocean() -> bool:
    try:
        import cmocean  # noqa
        return True
    except ImportError:
        return False


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("THALASSA — Week 1-2: Thermohaline Decomposition Prototype")
    print(f"metric_version: {METRIC_VERSION}")
    print(f"Repo: {REPO_ROOT}\n")

    # 1. Load cache
    print("Loading cached North Atlantic T-S profiles...")
    cache = load_cache()
    theta  = cache["theta"]   # (n_profiles, 90)
    salt   = cache["salt"]
    lats   = cache["lats"]    # (n_profiles,)
    lons   = cache["lons"]

    # Mask land points
    valid = (theta != 0) & (salt > 1)
    n_valid_total = valid.sum()
    print(f"  {theta.shape[0]} profiles, {n_valid_total:,} valid ocean data points\n")

    # 2. Compute density fields
    print("Computing TEOS-10 density and decomposition fields...")
    fields = compute_density_fields(theta, salt, lats)

    # Print summary statistics
    valid_mask = (theta != 0) & (salt > 1)
    rho_valid = fields["rho"][valid_mask]
    sig_valid = fields["sigma0"][valid_mask]
    print(f"  ρ range:    [{rho_valid.min():.3f}, {rho_valid.max():.3f}] kg/m³")
    print(f"  σ₀ range:   [{sig_valid.min():.3f}, {sig_valid.max():.3f}] kg/m³−1000")
    print(f"  α range:    [{fields['alpha'][valid_mask].min():.2e}, {fields['alpha'][valid_mask].max():.2e}] 1/°C")
    print(f"  β range:    [{fields['beta'][valid_mask].min():.2e}, {fields['beta'][valid_mask].max():.2e}] kg/g")
    print(f"  CI range:   [{fields['compensation_index'][valid_mask].min():.3f}, {fields['compensation_index'][valid_mask].max():.3f}]")
    print(f"  N² range:   [{fields['N2_squared'][valid_mask].min():.2e}, {fields['N2_squared'][valid_mask].max():.2e}] s⁻²\n")

    # 3. Figures
    print("Generating figures...")
    plot_ts_density(theta, salt, fields)
    plot_contribution_profiles(fields, theta, salt, lats)
    plot_compensation_map(fields, theta, salt, lats, lons)
    plot_stratification(fields, theta, salt, lats)

    # 4. Validation
    validate_against_literature(fields, theta, salt, lats)

    print(f"\nDone. Figures saved to: {FIGURES_DIR}")
    print("\nNext steps:")
    print("  - Review figures/02a–02d against physical expectations")
    print("  - Move compute_density_fields() into thalassa/backend/services/derived_metrics/")
    print("  - Wire up to /api/derived/density endpoint (Weeks 3–4)")
