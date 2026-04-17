"""
02_cache_north_atlantic.py — Cache North Atlantic data for all visualizations.

Run with: conda activate ocean && python notebooks/02_cache_north_atlantic.py

Caches:
  - Surface temperature & salinity maps (NA region)
  - Vertical cross-sections at key latitudes (30°N, 50°N, 60°N)
  - Horizontal depth slices at key depths (0, 100, 500, 1000, 2000, 4000m)
  - 3D subvolume for PyVista rendering
  - Coordinate arrays (lon, lat, depth) for each cached dataset
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
from data_access_llc4320 import (
    get_db, read_surface, read_depth_slice, read_cross_section_lat,
    read_volume, read_depth_profile, mask_land, print_data_summary,
    cache_save, cache_load, cache_or_fetch,
    lon_to_x, lat_to_y, x_to_lon, y_to_lat,
    DEPTH_LEVELS, NX, NY, NZ, DLON, DLAT, LON_MIN, LAT_MIN,
)

# ─────────────────────────────────────────────────────────────
# North Atlantic bounds (correct pixel range, no wraparound)
# -60°W to 0°E → 300°E to 360°E in [0,360] system → pixels 14400 to 17280
# 0°N to 70°N → pixels 6480 to 11520
# ─────────────────────────────────────────────────────────────
NA_X_MIN = lon_to_x(-60.0)   # 14400
NA_X_MAX = NX                 # 17280 (right edge, NOT lon_to_x(0) which gives 0)
NA_Y_MIN = lat_to_y(0.0)     # 6480
NA_Y_MAX = lat_to_y(70.0)    # 11520

print(f"North Atlantic pixel bounds: x=[{NA_X_MIN}, {NA_X_MAX}], y=[{NA_Y_MIN}, {NA_Y_MAX}]")
print(f"  = lon [{x_to_lon(NA_X_MIN):.1f}°, {x_to_lon(NA_X_MAX-1):.1f}°]")
print(f"  = lat [{y_to_lat(NA_Y_MIN):.1f}°, {y_to_lat(NA_Y_MAX-1):.1f}°]")
print()

# Resolution settings
SURFACE_QUALITY = -6    # moderate resolution for 2D maps
CROSS_QUALITY = -6      # moderate for cross-sections
VOLUME_QUALITY = -9     # coarser for 3D volume (still large)

# Timestep (using t=0 = first available, Sep 2011)
TIME = 0


def make_coord_arrays(data_shape, x_start, x_end, y_start, y_end):
    """Create lon/lat arrays matching a fetched data array's shape."""
    n_lat, n_lon = data_shape[-2], data_shape[-1]
    lons = LON_MIN + np.linspace(x_start, x_end, n_lon, endpoint=False) * DLON
    lats = LAT_MIN + np.linspace(y_start, y_end, n_lat, endpoint=False) * DLAT
    # Convert to [-180, 180]
    lons = np.where(lons > 180, lons - 360, lons)
    return lons, lats


# =================================================================
# 1. SURFACE MAPS
# =================================================================
def cache_surface_maps():
    print("=" * 60)
    print("1. SURFACE MAPS (theta + salt)")
    print("=" * 60)

    for var in ["theta", "salt"]:
        name = f"na_surface_{var}"
        data = cache_load(name)
        if data is not None:
            print(f"  Already cached: {name} {data.shape}")
            continue

        print(f"  Fetching NA surface {var} (quality={SURFACE_QUALITY})...")
        data = read_surface(
            var, time=TIME, quality=SURFACE_QUALITY,
            x_range=(NA_X_MIN, NA_X_MAX), y_range=(NA_Y_MIN, NA_Y_MAX),
        )
        print_data_summary(data, f"  {name}")
        cache_save(name, data)

    # Save coordinate arrays (from one of the fetched arrays)
    if cache_load("na_surface_lons") is None:
        sample = cache_load("na_surface_theta")
        lons, lats = make_coord_arrays(sample.shape, NA_X_MIN, NA_X_MAX, NA_Y_MIN, NA_Y_MAX)
        cache_save("na_surface_lons", lons)
        cache_save("na_surface_lats", lats)
        print(f"  Coords: lons [{lons.min():.1f}, {lons.max():.1f}], lats [{lats.min():.1f}, {lats.max():.1f}]")

    print()


# =================================================================
# 2. VERTICAL CROSS-SECTIONS
# =================================================================
def cache_cross_sections():
    print("=" * 60)
    print("2. VERTICAL CROSS-SECTIONS")
    print("=" * 60)

    latitudes = [30.0, 50.0, 60.0]  # key transects

    for lat in latitudes:
        for var in ["theta", "salt"]:
            name = f"na_cross_{var}_{int(lat)}N"
            data = cache_load(name)
            if data is not None:
                print(f"  Already cached: {name} {data.shape}")
                continue

            print(f"  Fetching cross-section at {lat}°N, {var} (quality={CROSS_QUALITY})...")
            data = read_cross_section_lat(
                var, lat=lat, time=TIME, quality=CROSS_QUALITY,
                x_range=(NA_X_MIN, NA_X_MAX),
            )
            print_data_summary(data, f"  {name}")
            cache_save(name, data)

    # Save cross-section lon coordinates
    if cache_load("na_cross_lons") is None:
        sample = cache_load("na_cross_theta_30N")
        n_lon = sample.shape[1]
        lons = LON_MIN + np.linspace(NA_X_MIN, NA_X_MAX, n_lon, endpoint=False) * DLON
        lons = np.where(lons > 180, lons - 360, lons)
        cache_save("na_cross_lons", lons)
        print(f"  Cross-section lons: [{lons.min():.1f}, {lons.max():.1f}], n={len(lons)}")

    print()


# =================================================================
# 3. HORIZONTAL DEPTH SLICES
# =================================================================
def cache_depth_slices():
    print("=" * 60)
    print("3. HORIZONTAL DEPTH SLICES")
    print("=" * 60)

    target_depths_m = [0, 100, 500, 1000, 2000, 4000]

    for depth_m in target_depths_m:
        # Find closest depth level
        z_idx = int(np.argmin(np.abs(DEPTH_LEVELS - depth_m)))
        actual_depth = DEPTH_LEVELS[z_idx]

        for var in ["theta", "salt"]:
            name = f"na_depth_{var}_{depth_m}m"
            data = cache_load(name)
            if data is not None:
                print(f"  Already cached: {name} {data.shape}")
                continue

            print(f"  Fetching {var} at ~{depth_m}m (level {z_idx}, actual {actual_depth:.0f}m, quality={SURFACE_QUALITY})...")
            data = read_depth_slice(
                var, depth_level=z_idx, time=TIME, quality=SURFACE_QUALITY,
                x_range=(NA_X_MIN, NA_X_MAX), y_range=(NA_Y_MIN, NA_Y_MAX),
            )
            print_data_summary(data, f"  {name}")
            cache_save(name, data)

    print()


# =================================================================
# 4. 3D SUBVOLUME (for PyVista)
# =================================================================
def cache_volume():
    print("=" * 60)
    print("4. 3D VOLUME (for PyVista)")
    print("=" * 60)

    for var in ["theta", "salt"]:
        name = f"na_volume_{var}"
        data = cache_load(name)
        if data is not None:
            print(f"  Already cached: {name} {data.shape}")
            continue

        print(f"  Fetching NA volume {var} (quality={VOLUME_QUALITY})... this may take a minute.")
        data = read_volume(
            var, time=TIME, quality=VOLUME_QUALITY,
            x_range=(NA_X_MIN, NA_X_MAX), y_range=(NA_Y_MIN, NA_Y_MAX),
            z_range=(0, NZ),
        )
        print_data_summary(data, f"  {name}")
        cache_save(name, data)

    # Save volume coordinate arrays
    if cache_load("na_volume_lons") is None:
        sample = cache_load("na_volume_theta")
        n_depth, n_lat, n_lon = sample.shape
        lons = LON_MIN + np.linspace(NA_X_MIN, NA_X_MAX, n_lon, endpoint=False) * DLON
        lons = np.where(lons > 180, lons - 360, lons)
        lats = LAT_MIN + np.linspace(NA_Y_MIN, NA_Y_MAX, n_lat, endpoint=False) * DLAT
        # Depth: map z indices to actual depths
        z_indices = np.linspace(0, NZ - 1, n_depth)
        depths = np.interp(z_indices, np.arange(NZ), DEPTH_LEVELS)

        cache_save("na_volume_lons", lons)
        cache_save("na_volume_lats", lats)
        cache_save("na_volume_depths", depths)
        print(f"  Volume shape: {sample.shape}")
        print(f"  Lons: [{lons.min():.1f}, {lons.max():.1f}], n={len(lons)}")
        print(f"  Lats: [{lats.min():.1f}, {lats.max():.1f}], n={len(lats)}")
        print(f"  Depths: [{depths.min():.0f}, {depths.max():.0f}]m, n={len(depths)}")

    print()


# =================================================================
# 5. DEPTH PROFILES (for T-S diagram)
# =================================================================
def cache_ts_profiles():
    print("=" * 60)
    print("5. T-S PROFILES (sampled grid for T-S diagram)")
    print("=" * 60)

    # Sample a grid of depth profiles across the NA region
    # We'll use moderate spacing to get ~200-400 profiles
    name = "na_ts_profiles"
    data = cache_load(name)
    if data is not None:
        print(f"  Already cached: {name} {data.shape}")
        return

    # Sample every ~2° in lat and lon
    sample_lats = np.arange(5, 70, 2)
    sample_lons = np.arange(-55, -1, 2)

    profiles_theta = []
    profiles_salt = []
    profile_lons = []
    profile_lats = []

    total = len(sample_lats) * len(sample_lons)
    count = 0

    for lat in sample_lats:
        for lon in sample_lons:
            count += 1
            if count % 50 == 0:
                print(f"  Progress: {count}/{total}")
            try:
                t_prof = read_depth_profile("theta", lon=lon, lat=lat, time=TIME, quality=-6)
                s_prof = read_depth_profile("salt", lon=lon, lat=lat, time=TIME, quality=-6)

                # Skip land points (all zeros)
                if np.all(t_prof == 0) or np.all(s_prof == 0):
                    continue

                profiles_theta.append(t_prof)
                profiles_salt.append(s_prof)
                profile_lons.append(lon)
                profile_lats.append(lat)
            except Exception as e:
                print(f"  Warning: failed at ({lat}°N, {lon}°E): {e}")

    profiles_theta = np.array(profiles_theta)  # shape: (n_profiles, 90)
    profiles_salt = np.array(profiles_salt)
    profile_lons = np.array(profile_lons)
    profile_lats = np.array(profile_lats)

    print(f"  Got {len(profiles_theta)} ocean profiles out of {total} sample points")

    cache_save("na_ts_theta", profiles_theta)
    cache_save("na_ts_salt", profiles_salt)
    cache_save("na_ts_lons", profile_lons)
    cache_save("na_ts_lats", profile_lats)

    print()


# =================================================================
# MAIN
# =================================================================
if __name__ == "__main__":
    print("North Atlantic Data Caching")
    print(f"Region: 60°W–0°E, 0°N–70°N")
    print(f"Timestep: {TIME}")
    print()

    cache_surface_maps()
    cache_cross_sections()
    cache_depth_slices()
    cache_volume()
    cache_ts_profiles()

    # Summary
    print("=" * 60)
    print("CACHING COMPLETE — Summary of cached files:")
    print("=" * 60)
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "cache")
    total_mb = 0
    for f in sorted(os.listdir(cache_dir)):
        if f.endswith(".npy"):
            size = os.path.getsize(os.path.join(cache_dir, f)) / (1024 * 1024)
            total_mb += size
            print(f"  {f:40s} {size:8.1f} MB")
    print(f"  {'TOTAL':40s} {total_mb:8.1f} MB")
