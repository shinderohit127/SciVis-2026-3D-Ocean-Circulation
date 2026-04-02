"""
data_access_llc4320.py — Data access module for ECCO LLC4320 ocean dataset.

Provides functions to:
  - Connect to the LLC4320 OpenVisus endpoints (theta, salt, w)
  - Query 2D slices (single depth level) and 3D subvolumes
  - Convert between lat/lon and grid pixel coordinates
  - Cache results as .npy files for offline use

Dataset properties:
  - Full grid: 17280 x 12960 x 90 (x=lon, y=lat, z=depth)
  - Resolution: 1/48° horizontal (~2 km), 90 non-uniform depth levels
  - Temporal: hourly, 10312 timesteps (Sep 2011 – Nov 2012)
  - Variables: theta (°C), salt (g/kg), w (m/s)

Usage:
    from data_access_llc4320 import get_db, read_surface, read_cross_section, ...
"""

import numpy as np
import os
import openvisuspy as ovp

# =============================================================================
# CONSTANTS
# =============================================================================

# OpenVisus endpoints
URLS = {
    "theta": "pelican://osg-htc.org/nasa/nsdf/climate1/llc4320/idx/theta/theta_llc4320_x_y_depth.idx",
    "salt":  "pelican://osg-htc.org/nasa/nsdf/climate1/llc4320/idx/salt/salt_llc4320_x_y_depth.idx",
    "w":     "pelican://osg-htc.org/nasa/nsdf/climate2/llc4320/idx/w/w_llc4320_x_y_depth.idx",
}

# Grid dimensions (full resolution)
NX = 17280  # longitude
NY = 12960  # latitude
NZ = 90     # depth levels

# Coordinate mapping (will be verified empirically with coastline overlay)
# These are initial estimates — the LLC4320 OpenVisus grid is on a regular
# lat-lon projection. Exact bounds need verification.
# Based on the grid: 17280 pixels / 48 per degree = 360° longitude
# The latitude range is trickier — LLC4320 covers ~-80°S to ~+80°N
LON_MIN = 0.0       # left edge of pixel x=0
LON_MAX = 360.0     # right edge of pixel x=17279
LAT_MIN = -90.0     # bottom edge of pixel y=0  (will refine)
LAT_MAX = 90.0      # top edge of pixel y=12959 (will refine)

# Derived: degrees per pixel
DLON = (LON_MAX - LON_MIN) / NX  # ~0.02083° = 1/48°
DLAT = (LAT_MAX - LAT_MIN) / NY  # approximate, needs verification

# LLC4320 depth levels (meters, approximate)
# Source: MITgcm LLC4320 documentation
# 90 levels, non-uniform spacing (dense near surface)
DEPTH_LEVELS = np.array([
    1.0,    2.0,    3.1,    4.3,    5.6,    7.0,    8.6,   10.3,   12.2,   14.2,
   16.5,   19.0,   21.7,   24.8,   28.1,   31.8,   35.9,   40.3,   45.2,   50.6,
   56.5,   63.0,   70.2,   78.1,   86.8,   96.5,  107.1,  118.9,  132.0,  146.5,
  162.5,  180.1,  199.5,  220.9,  244.4,  270.2,  298.5,  329.5,  363.3,  400.2,
  440.4,  484.0,  531.4,  582.7,  638.2,  698.1,  762.7,  832.2,  906.9,  987.1,
 1073.0, 1164.9, 1263.0, 1367.5, 1478.6, 1596.5, 1721.3, 1853.2, 1992.2, 2138.5,
 2292.1, 2453.1, 2621.5, 2797.3, 2980.5, 3171.1, 3369.0, 3574.3, 3786.8, 4006.6,
 4233.5, 4467.6, 4708.8, 4957.0, 5212.2, 5474.3, 5743.3, 6019.1, 6301.7, 6591.0,
 6887.0, 7189.6, 7498.8, 7814.6, 8136.9, 8465.7, 8801.0, 9142.7, 9490.9, 9845.4,
])

# North Atlantic bounding box (the focus region)
NA_LON_MIN, NA_LON_MAX = -60.0, 0.0   # 60°W to 0°E
NA_LAT_MIN, NA_LAT_MAX = 0.0, 70.0    # 0°N to 70°N

# Cache directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")

# =============================================================================
# DATABASE CONNECTIONS (lazy-loaded singletons)
# =============================================================================

_databases = {}


def get_db(variable="theta"):
    """Get (or create) an OpenVisus database connection for the given variable."""
    if variable not in URLS:
        raise ValueError(f"Unknown variable '{variable}'. Choose from: {list(URLS.keys())}")
    if variable not in _databases:
        print(f"Connecting to LLC4320 {variable} dataset...")
        _databases[variable] = ovp.LoadDataset(URLS[variable])
        print(f"  Connected. Dimensions: {_databases[variable].getLogicBox()}")
    return _databases[variable]


def get_dataset_info(variable="theta"):
    """Print metadata about the dataset."""
    db = get_db(variable)
    box = db.getLogicBox()
    print(f"Variable: {variable}")
    print(f"Logic box: {box}")
    print(f"Dimensions: {box[1][0]} x {box[1][1]} x {box[1][2]}")
    print(f"Timesteps: {len(db.getTimesteps())}")
    print(f"Field: {db.getField().name}")
    return box


# =============================================================================
# COORDINATE CONVERSION
# =============================================================================

def lon_to_x(lon):
    """Convert longitude (degrees) to pixel x-coordinate.

    Handles both [0,360] and [-180,180] conventions.
    """
    # Normalize to [0, 360)
    lon_normalized = lon % 360.0
    x = (lon_normalized - LON_MIN) / DLON
    return int(np.clip(x, 0, NX - 1))


def lat_to_y(lat):
    """Convert latitude (degrees) to pixel y-coordinate."""
    y = (lat - LAT_MIN) / DLAT
    return int(np.clip(y, 0, NY - 1))


def x_to_lon(x):
    """Convert pixel x-coordinate to longitude (degrees)."""
    lon = LON_MIN + x * DLON
    # Convert to [-180, 180] range
    if lon > 180:
        lon -= 360
    return lon


def y_to_lat(y):
    """Convert pixel y-coordinate to latitude (degrees)."""
    return LAT_MIN + y * DLAT


def get_lon_array(x_start, x_end, n_pixels):
    """Get array of longitudes for a pixel range."""
    x_indices = np.linspace(x_start, x_end, n_pixels, endpoint=False)
    lons = LON_MIN + x_indices * DLON
    # Convert to [-180, 180]
    lons = np.where(lons > 180, lons - 360, lons)
    return lons


def get_lat_array(y_start, y_end, n_pixels):
    """Get array of latitudes for a pixel range."""
    y_indices = np.linspace(y_start, y_end, n_pixels, endpoint=False)
    return LAT_MIN + y_indices * DLAT


def get_na_pixel_bounds():
    """Get pixel coordinates for the North Atlantic bounding box."""
    x_min = lon_to_x(NA_LON_MIN)
    x_max = lon_to_x(NA_LON_MAX)
    y_min = lat_to_y(NA_LAT_MIN)
    y_max = lat_to_y(NA_LAT_MAX)

    # Handle wraparound if needed (when lon range crosses 0/360 boundary)
    if x_min > x_max:
        print(f"Warning: longitude range crosses grid boundary. x_min={x_min}, x_max={x_max}")

    return x_min, x_max, y_min, y_max


def depth_to_z(depth_m):
    """Find the closest depth level index for a given depth in meters."""
    idx = np.argmin(np.abs(DEPTH_LEVELS - depth_m))
    return idx


# =============================================================================
# DATA READING
# =============================================================================

def read_surface(variable="theta", time=0, quality=-6, x_range=None, y_range=None):
    """Read a 2D surface map (depth level 0).

    Args:
        variable: "theta", "salt", or "w"
        time: timestep index (0-10311)
        quality: resolution level (-15=coarsest, 0=full). -6 is good for exploration.
        x_range: (x_min, x_max) pixel range, or None for full extent
        y_range: (y_min, y_max) pixel range, or None for full extent

    Returns:
        2D numpy array (lat, lon)
    """
    db = get_db(variable)
    kwargs = dict(time=time, z=[0, 1], quality=quality)
    if x_range:
        kwargs["x"] = list(x_range)
    if y_range:
        kwargs["y"] = list(y_range)

    data = db.db.read(**kwargs)
    return data[0, :, :]  # squeeze depth dimension


def read_depth_slice(variable="theta", depth_level=0, time=0, quality=-6,
                     x_range=None, y_range=None):
    """Read a 2D horizontal slice at a specific depth level.

    Args:
        variable: "theta", "salt", or "w"
        depth_level: depth level index (0-89). Use depth_to_z() to convert from meters.
        time: timestep index
        quality: resolution level
        x_range, y_range: pixel ranges

    Returns:
        2D numpy array (lat, lon)
    """
    db = get_db(variable)
    kwargs = dict(time=time, z=[depth_level, depth_level + 1], quality=quality)
    if x_range:
        kwargs["x"] = list(x_range)
    if y_range:
        kwargs["y"] = list(y_range)

    data = db.db.read(**kwargs)
    return data[0, :, :]


def read_cross_section_lat(variable="theta", y_pixel=None, lat=None, time=0,
                           quality=-6, x_range=None):
    """Read a vertical cross-section at a fixed latitude (all depths).

    Args:
        variable: "theta", "salt", or "w"
        y_pixel: y pixel coordinate (specify this OR lat, not both)
        lat: latitude in degrees (converted to y pixel)
        time: timestep index
        quality: resolution level
        x_range: (x_min, x_max) pixel range

    Returns:
        2D numpy array (depth, lon) — shape (90, n_lon)
    """
    if lat is not None:
        y_pixel = lat_to_y(lat)
    if y_pixel is None:
        raise ValueError("Must specify either y_pixel or lat")

    db = get_db(variable)
    kwargs = dict(time=time, y=[y_pixel, y_pixel + 1], quality=quality)
    if x_range:
        kwargs["x"] = list(x_range)

    data = db.db.read(**kwargs)
    # Shape: (depth, 1, lon) → squeeze lat dimension
    return data[:, 0, :]


def read_cross_section_lon(variable="theta", x_pixel=None, lon=None, time=0,
                           quality=-6, y_range=None):
    """Read a vertical cross-section at a fixed longitude (all depths).

    Args:
        variable: "theta", "salt", or "w"
        x_pixel: x pixel coordinate (specify this OR lon, not both)
        lon: longitude in degrees (converted to x pixel)
        time: timestep index
        quality: resolution level
        y_range: (y_min, y_max) pixel range

    Returns:
        2D numpy array (depth, lat) — shape (90, n_lat)
    """
    if lon is not None:
        x_pixel = lon_to_x(lon)
    if x_pixel is None:
        raise ValueError("Must specify either x_pixel or lon")

    db = get_db(variable)
    kwargs = dict(time=time, x=[x_pixel, x_pixel + 1], quality=quality)
    if y_range:
        kwargs["y"] = list(y_range)

    data = db.db.read(**kwargs)
    # Shape: (depth, lat, 1) → squeeze lon dimension
    return data[:, :, 0]


def read_volume(variable="theta", time=0, quality=-9,
                x_range=None, y_range=None, z_range=None):
    """Read a 3D subvolume.

    Args:
        variable: "theta", "salt", or "w"
        time: timestep index
        quality: resolution level. Use -9 or lower for volumes (they're large!)
        x_range: (x_min, x_max) pixel range
        y_range: (y_min, y_max) pixel range
        z_range: (z_min, z_max) depth level range, e.g. (0, 90) for all depths

    Returns:
        3D numpy array (depth, lat, lon)
    """
    db = get_db(variable)
    kwargs = dict(time=time, quality=quality)
    if x_range:
        kwargs["x"] = list(x_range)
    if y_range:
        kwargs["y"] = list(y_range)
    if z_range:
        kwargs["z"] = list(z_range)

    data = db.db.read(**kwargs)
    return data


def read_depth_profile(variable="theta", x_pixel=None, y_pixel=None,
                       lon=None, lat=None, time=0, quality=-6):
    """Read a vertical profile (all 90 depth levels) at a single point.

    Args:
        variable: "theta", "salt", or "w"
        x_pixel, y_pixel: pixel coordinates (or use lon, lat)
        lon, lat: geographic coordinates (converted to pixels)
        time: timestep index
        quality: resolution level

    Returns:
        1D numpy array (90,) — values at each depth level
    """
    if lon is not None:
        x_pixel = lon_to_x(lon)
    if lat is not None:
        y_pixel = lat_to_y(lat)

    db = get_db(variable)
    data = db.db.read(
        time=time,
        x=[x_pixel, x_pixel + 1],
        y=[y_pixel, y_pixel + 1],
        quality=quality,
    )
    # Shape: (90, 1, 1) → squeeze
    return data[:, 0, 0]


# =============================================================================
# CACHING
# =============================================================================

def cache_path(name):
    """Get the full path for a cache file."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{name}.npy")


def cache_save(name, array):
    """Save a numpy array to cache."""
    path = cache_path(name)
    np.save(path, array)
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"Cached: {path} ({array.shape}, {size_mb:.1f} MB)")


def cache_load(name):
    """Load a numpy array from cache, or return None if not cached."""
    path = cache_path(name)
    if os.path.exists(path):
        data = np.load(path)
        return data
    return None


def cache_or_fetch(name, fetch_fn):
    """Load from cache if available, otherwise fetch and cache.

    Args:
        name: cache key (without .npy extension)
        fetch_fn: callable that returns a numpy array

    Returns:
        numpy array
    """
    data = cache_load(name)
    if data is not None:
        print(f"Loaded from cache: {name} {data.shape}")
        return data

    print(f"Fetching: {name}...")
    data = fetch_fn()
    cache_save(name, data)
    return data


# =============================================================================
# CONVENIENCE: NORTH ATLANTIC READS
# =============================================================================

def read_na_surface(variable="theta", time=0, quality=-6):
    """Read surface data for the North Atlantic region."""
    x_min, x_max, y_min, y_max = get_na_pixel_bounds()
    return read_surface(variable, time=time, quality=quality,
                        x_range=(x_min, x_max), y_range=(y_min, y_max))


def read_na_cross_section(variable="theta", lat=30.0, time=0, quality=-6):
    """Read a vertical cross-section across the North Atlantic at a given latitude."""
    x_min, x_max, _, _ = get_na_pixel_bounds()
    return read_cross_section_lat(variable, lat=lat, time=time,
                                  quality=quality, x_range=(x_min, x_max))


def read_na_volume(variable="theta", time=0, quality=-9):
    """Read 3D volume for the North Atlantic region."""
    x_min, x_max, y_min, y_max = get_na_pixel_bounds()
    return read_volume(variable, time=time, quality=quality,
                       x_range=(x_min, x_max), y_range=(y_min, y_max),
                       z_range=(0, NZ))


# =============================================================================
# UTILITY
# =============================================================================

def mask_land(data, fill_value=0.0):
    """Mask land values (typically 0.0 in LLC4320) with NaN."""
    masked = data.astype(np.float64)
    masked[masked == fill_value] = np.nan
    return masked


def print_data_summary(data, name="data"):
    """Print summary statistics for a data array."""
    valid = data[~np.isnan(data)] if np.issubdtype(data.dtype, np.floating) else data[data != 0]
    print(f"{name}: shape={data.shape}, dtype={data.dtype}")
    if len(valid) > 0:
        print(f"  valid pixels: {len(valid)}/{data.size} ({100*len(valid)/data.size:.1f}%)")
        print(f"  range: [{valid.min():.3f}, {valid.max():.3f}]")
        print(f"  mean: {valid.mean():.3f}, std: {valid.std():.3f}")
    else:
        print(f"  WARNING: no valid data!")


# =============================================================================
# MODULE-LEVEL QUICK TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("LLC4320 Data Access Module — Quick Test")
    print("=" * 60)

    # Test connection
    info = get_dataset_info("theta")

    # Test surface read (very coarse for speed)
    print("\nFetching global surface temperature (quality=-8)...")
    surface = read_surface("theta", quality=-8)
    print_data_summary(surface, "Global surface theta")

    # Test North Atlantic bounds
    x_min, x_max, y_min, y_max = get_na_pixel_bounds()
    print(f"\nNorth Atlantic pixel bounds: x=[{x_min}, {x_max}], y=[{y_min}, {y_max}]")

    print("\nModule test complete.")
