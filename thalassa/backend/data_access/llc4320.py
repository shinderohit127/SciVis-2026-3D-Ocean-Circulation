"""
LLC4320 dataset reader — OpenVisus wrapper for THALASSA.

Grid conventions (confirmed from debug_grid* scripts and prior caching runs):
  NX = 17280  — longitude axis (columns), [0°, 360°) convention
  NY = 12960  — latitude axis (rows), [-90°, 90°] convention
  NZ = 90     — depth levels (z=0 is surface, z=89 is ~6625 m)

OpenVisus quality parameter: negative integer, -15 is very coarse (~1/32768
resolution), 0 is full resolution. Typical choices:
  -6  → scale ≈ 8×   (good for regional ROIs, moderate latency)
  -9  → scale ≈ 64×  (fast preview of large regions)
  -12 → scale ≈ 512× (global coarse overview)

CRITICAL: LLC4320 raw reads may come back horizontally flipped depending on
the client environment. ALWAYS call verify_orientation() or run
notebooks/01_verify_openvisus.py before trusting a new subvolume.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from data_access.depth_levels import (
    DEPTH_LEVELS_M,
    depth_range_to_z_indices,
    depth_to_z_index,
    z_index_to_depth,
)

logger = logging.getLogger(__name__)

# ── Grid constants ─────────────────────────────────────────────────────────────

NX: int = 17280   # full-resolution longitude pixels
NY: int = 12960   # full-resolution latitude pixels
NZ: int = 90      # depth levels

LON_MIN: float = 0.0     # OpenVisus uses [0, 360) longitude
LON_MAX: float = 360.0
LAT_MIN: float = -90.0
LAT_MAX: float = 90.0

DLON: float = LON_MAX / NX   # ≈ 0.020833° per pixel
DLAT: float = (LAT_MAX - LAT_MIN) / NY  # ≈ 0.013889° per pixel

# Number of hourly timesteps: Sep 10 2011 – Nov 15 2012
N_TIMESTEPS: int = 10312

# ── Data URLs ──────────────────────────────────────────────────────────────────

VARIABLE_URLS: dict[str, str] = {
    "theta": "pelican://osg-htc.org/nasa/nsdf/climate1/llc4320/idx/theta/theta_llc4320_x_y_depth.idx",
    "salt":  "pelican://osg-htc.org/nasa/nsdf/climate1/llc4320/idx/salt/salt_llc4320_x_y_depth.idx",
    "w":     "pelican://osg-htc.org/nasa/nsdf/climate2/llc4320/idx/w/w_llc4320_x_y_depth.idx",
}

# ── Basin presets (pixel-space, full resolution) ───────────────────────────────

BASIN_PRESETS: dict[str, dict] = {
    "north_atlantic": {
        "lat": (0.0, 70.0), "lon": (-60.0, 0.0),
        # lon in [0,360]: 300°–360°; wraps to right edge so use x=(14400, NX)
        "x": (14400, NX), "y": (6480, 11520),
    },
    "southern_ocean": {
        "lat": (-80.0, -30.0), "lon": (-180.0, 180.0),
        "x": (0, NX), "y": (720, 4320),
    },
    "equatorial": {
        "lat": (-15.0, 15.0), "lon": (-180.0, 180.0),
        "x": (0, NX), "y": (5400, 7560),
    },
}


# ── Coordinate helpers ─────────────────────────────────────────────────────────

def lon_to_x(lon: float) -> int:
    """Longitude (any convention) → x pixel index. Uses [0, 360) internally."""
    return int(((lon % 360) / (LON_MAX - LON_MIN)) * NX) % NX


def lat_to_y(lat: float) -> int:
    """Latitude [-90, 90] → y pixel index."""
    return int(((lat - LAT_MIN) / (LAT_MAX - LAT_MIN)) * NY)


def x_to_lon(x: int) -> float:
    """x pixel → longitude in [0, 360)."""
    return LON_MIN + x * DLON


def y_to_lat(y: int) -> float:
    """y pixel → latitude in [-90, 90]."""
    return LAT_MIN + y * DLAT


def lon_lat_to_xy(lon: float, lat: float) -> tuple[int, int]:
    return lon_to_x(lon), lat_to_y(lat)


# ── ROI dataclass ──────────────────────────────────────────────────────────────

@dataclass
class ROI:
    """Geographic region of interest for a THALASSA query."""
    lat_min: float
    lat_max: float
    lon_min: float          # degrees, any convention (-180/180 or 0/360)
    lon_max: float
    depth_min_m: float = 0.0
    depth_max_m: float = 6625.0
    timestep: int = 0       # 0-based hourly index (0 = Sep 10 2011 00:00 UTC)
    quality: int = -6       # OpenVisus quality: -15 coarse → 0 full

    @classmethod
    def from_basin(cls, basin: str, timestep: int = 0, quality: int = -6,
                   depth_min_m: float = 0.0, depth_max_m: float = 6625.0) -> "ROI":
        preset = BASIN_PRESETS[basin]
        lat_min, lat_max = preset["lat"]
        lon_min, lon_max = preset["lon"]
        return cls(lat_min=lat_min, lat_max=lat_max, lon_min=lon_min, lon_max=lon_max,
                   depth_min_m=depth_min_m, depth_max_m=depth_max_m,
                   timestep=timestep, quality=quality)

    @property
    def x0(self) -> int:
        return lon_to_x(self.lon_min)

    @property
    def x1(self) -> int:
        x = lon_to_x(self.lon_max)
        # 0°E (=360°E) maps to x=0 due to modulo; treat as NX (right edge)
        return NX if x == 0 and self.lon_max >= 0 and self.lon_min < 0 else x

    @property
    def y0(self) -> int:
        return lat_to_y(self.lat_min)

    @property
    def y1(self) -> int:
        return lat_to_y(self.lat_max)

    @property
    def z0(self) -> int:
        return depth_to_z_index(self.depth_min_m)

    @property
    def z1(self) -> int:
        return depth_to_z_index(self.depth_max_m)

    def lon_array(self, n_x: int) -> np.ndarray:
        """Return longitude array matching a fetched array of width n_x, in [-180, 180]."""
        lons = LON_MIN + np.linspace(self.x0, self.x1, n_x, endpoint=False) * DLON
        return np.where(lons > 180, lons - 360, lons)

    def lat_array(self, n_y: int) -> np.ndarray:
        """Return latitude array matching a fetched array of height n_y."""
        return LAT_MIN + np.linspace(self.y0, self.y1, n_y, endpoint=False) * DLAT

    def depth_array(self, n_z: int) -> np.ndarray:
        """Return depth array matching n_z levels fetched from [z0, z1]."""
        z_indices = np.linspace(self.z0, self.z1, n_z)
        return np.interp(z_indices, np.arange(NZ), DEPTH_LEVELS_M)


# ── Main reader ────────────────────────────────────────────────────────────────

class LLC4320Reader:
    """
    Progressive reader for the LLC4320 dataset via OpenVisus IDX.

    Lazy-connects to each variable's URL on first access. Thread-unsafe;
    create one instance per worker/request context.

    Usage::

        reader = LLC4320Reader()
        roi = ROI.from_basin("north_atlantic", timestep=0, quality=-6,
                             depth_min_m=0, depth_max_m=500)
        theta = reader.read(roi, "theta")   # shape: (n_z, n_y, n_x)
        salt  = reader.read(roi, "salt")
    """

    def __init__(self) -> None:
        self._datasets: dict[str, object] = {}

    # ── Connection ──────────────────────────────────────────────────────────

    def _get_dataset(self, variable: str) -> object:
        if variable not in self._datasets:
            if variable not in VARIABLE_URLS:
                raise ValueError(f"Unknown variable '{variable}'. Must be one of {list(VARIABLE_URLS)}")
            url = VARIABLE_URLS[variable]
            logger.info("Connecting to OpenVisus: %s", url)
            try:
                from openvisuspy import LoadDataset
            except ImportError as exc:
                raise RuntimeError(
                    "openvisuspy is not installed. "
                    "Install it with: pip install openvisuspy"
                ) from exc
            self._datasets[variable] = LoadDataset(url)
            logger.info("Connected to %s", variable)
        return self._datasets[variable]

    # ── Read ─────────────────────────────────────────────────────────────────

    def read(self, roi: ROI, variable: str) -> np.ndarray:
        """
        Fetch a subvolume from OpenVisus.

        Returns ndarray of shape (n_z, n_y, n_x). Shape depends on quality and
        ROI extent. Land cells are zero-valued.

        Args:
            roi: Region of interest including timestep and quality.
            variable: One of 'theta', 'salt', 'w'.

        Returns:
            np.ndarray with shape (n_z, n_y, n_x).
        """
        db = self._get_dataset(variable)
        x0, x1 = roi.x0, roi.x1
        y0, y1 = roi.y0, roi.y1
        z0, z1 = roi.z0, roi.z1 + 1  # OpenVisus end is exclusive

        logger.debug(
            "Reading %s t=%d x=[%d,%d] y=[%d,%d] z=[%d,%d] q=%d",
            variable, roi.timestep, x0, x1, y0, y1, z0, z1, roi.quality,
        )
        try:
            data = db.read(
                time=roi.timestep,
                x=[x0, x1],
                y=[y0, y1],
                z=[z0, z1],
                quality=roi.quality,
            )
        except TypeError:
            # Some openvisuspy builds expose the dataset as .db
            data = db.db.read(
                time=roi.timestep,
                x=[x0, x1],
                y=[y0, y1],
                z=[z0, z1],
                quality=roi.quality,
            )

        data = np.asarray(data, dtype=np.float32)

        # Ensure 3D (z, y, x) even if a single depth level was returned
        if data.ndim == 2:
            data = data[np.newaxis, :, :]

        logger.debug("Read complete: shape=%s min=%.3f max=%.3f",
                     data.shape, float(np.nanmin(data)), float(np.nanmax(data)))
        return data

    def read_surface(self, variable: str, timestep: int = 0,
                     quality: int = -6,
                     lat_range: tuple[float, float] = (-90.0, 90.0),
                     lon_range: tuple[float, float] = (-180.0, 180.0)) -> np.ndarray:
        """Read the surface layer (z=0) over a lat/lon region."""
        roi = ROI(lat_min=lat_range[0], lat_max=lat_range[1],
                  lon_min=lon_range[0], lon_max=lon_range[1],
                  depth_min_m=0.0, depth_max_m=5.0,
                  timestep=timestep, quality=quality)
        data = self.read(roi, variable)
        return data[0]   # surface layer only, shape (n_y, n_x)

    def read_depth_slice(self, variable: str, depth_m: float,
                         timestep: int = 0, quality: int = -6,
                         lat_range: tuple[float, float] = (-90.0, 90.0),
                         lon_range: tuple[float, float] = (-180.0, 180.0)) -> np.ndarray:
        """Read a single horizontal depth slice nearest to depth_m."""
        z = depth_to_z_index(depth_m)
        actual_depth = z_index_to_depth(z)
        logger.info("Depth slice: requested %.0f m → level %d (%.0f m)", depth_m, z, actual_depth)
        roi = ROI(lat_min=lat_range[0], lat_max=lat_range[1],
                  lon_min=lon_range[0], lon_max=lon_range[1],
                  depth_min_m=actual_depth, depth_max_m=actual_depth,
                  timestep=timestep, quality=quality)
        data = self.read(roi, variable)
        return data[0]   # shape (n_y, n_x)

    # ── Orientation verification ──────────────────────────────────────────────

    def verify_orientation(self, timestep: int = 0, quality: int = -9,
                           save_path: Optional[str] = None) -> bool:
        """
        Fetch a coarse global surface temperature slice and overlay cartopy
        coastlines. Saves a diagnostic PNG and returns True if orientation
        appears correct.

        A correct orientation shows: Americas on the left, Europe/Africa in
        the centre-right, when longitude is plotted west-to-east.

        This MUST be called whenever you move to a new environment or
        openvisuspy version. The LLC4320 raw reads have been observed to
        come back horizontally flipped.
        """
        logger.info("Running orientation verification (quality=%d)...", quality)
        roi = ROI(lat_min=-80.0, lat_max=80.0,
                  lon_min=-180.0, lon_max=180.0,
                  depth_min_m=0.0, depth_max_m=5.0,
                  timestep=timestep, quality=quality)
        data = self.read(roi, "theta")
        surface = data[0]  # (n_y, n_x)

        n_y, n_x = surface.shape
        lons = np.linspace(-180.0, 180.0, n_x, endpoint=False)
        lats = np.linspace(-80.0, 80.0, n_y, endpoint=False)

        masked = surface.astype(float)
        masked[masked == 0] = np.nan

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import cartopy.crs as ccrs
            import cartopy.feature as cfeature

            fig, ax = plt.subplots(
                figsize=(16, 8),
                subplot_kw={"projection": ccrs.PlateCarree()},
            )
            lon_grid, lat_grid = np.meshgrid(lons, lats)
            ax.pcolormesh(lon_grid, lat_grid, masked,
                          cmap="RdBu_r", transform=ccrs.PlateCarree(), shading="auto",
                          vmin=-2, vmax=32)
            ax.coastlines(resolution="110m", color="black", linewidth=1.0)
            ax.add_feature(cfeature.BORDERS, linewidth=0.4, alpha=0.5)
            ax.set_global()
            ax.set_title(
                f"LLC4320 surface theta — orientation check (quality={quality}, t={timestep})\n"
                "Americas should be on left, Europe/Africa centre-right",
                fontsize=11,
            )
            out = save_path or "figures/00_orientation_check.png"
            import os; os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
            fig.savefig(out, dpi=150, bbox_inches="tight")
            plt.close()
            logger.info("Saved orientation plot: %s", out)
        except ImportError as exc:
            logger.warning("Could not generate orientation plot: %s", exc)

        # Heuristic check: tropical Pacific (lon ~-140°, lat ~5°) should be warm (>20°C)
        lon_pix = int((((-140) % 360) / 360) * n_x)
        lat_pix = int(((5 + 80) / 160) * n_y)
        lon_pix = max(0, min(lon_pix, n_x - 1))
        lat_pix = max(0, min(lat_pix, n_y - 1))
        pacific_val = float(surface[lat_pix, lon_pix])

        # If Pacific is cold and polar areas warm, we have a flip
        is_correct = pacific_val > 15.0
        status = "CORRECT" if is_correct else "POSSIBLY FLIPPED"
        logger.info(
            "Orientation check: tropical Pacific pixel value = %.1f°C → %s",
            pacific_val, status,
        )
        if not is_correct:
            logger.warning(
                "Grid orientation may be FLIPPED. "
                "Check figures/00_orientation_check.png and compare to coastlines. "
                "If flipped, apply np.fliplr() to all fetched arrays."
            )
        return is_correct
