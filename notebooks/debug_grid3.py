"""Empirical coastline feature detection to determine lat/lon mapping."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from data_access_llc4320 import cache_load, get_db, NX, NY

data = cache_load('test_global_surface_q8')
n_lat, n_lon = data.shape
print(f"Data shape: {data.shape}")
scale = NX / n_lon  # 16x
print(f"Downscale factor: {scale}")

# ---------------------------------------------------------------
# Strategy: for specific longitudes, find the land/ocean
# transitions along y. Compare to known coastline latitudes.
# ---------------------------------------------------------------

def find_transitions(col_data):
    """Find y-pixels where data transitions between land (0) and ocean (nonzero)."""
    transitions = []
    for i in range(1, len(col_data)):
        was_land = col_data[i-1] == 0
        is_land = col_data[i] == 0
        if was_land != is_land:
            kind = "land->ocean" if was_land else "ocean->land"
            transitions.append((i, kind))
    return transitions

# Check columns at several known longitudes
# Assuming LON_MIN=0, LON_MAX=360 (this seems correct from earlier tests)
test_lons = {
    0: "Prime Meridian (Gulf of Guinea/Europe)",
    20: "East Africa / Mediterranean",
    77: "India west coast",
    140: "Japan / Australia",
    -80: "Americas (Florida/Caribbean)",
    -40: "Mid-Atlantic / Brazil",
}

print("\n=== Land/ocean transitions at known longitudes ===")
for lon_deg, desc in test_lons.items():
    col_idx = int(((lon_deg % 360) / 360) * n_lon) % n_lon
    col = data[:, col_idx]
    trans = find_transitions(col)
    print(f"\nLon={lon_deg}° ({desc}), col={col_idx}")
    for y, kind in trans:
        print(f"  y={y:>4} (frac={y/n_lat:.3f}) {kind}")

# ---------------------------------------------------------------
# Now use the LIVE server to do the reverse: read at specific
# lat/lon at full resolution to find the actual pixel coordinates
# ---------------------------------------------------------------
print("\n\n=== Full-resolution server checks ===")
print("Looking for known features at specific lat/lon:")

db = get_db("theta")

# Read narrow strips at specific latitudes across the full longitude range
# to find where land (0) vs ocean transitions happen
# This tells us: at a given LATITUDE, what x-pixel shows the expected pattern

# Approach: for a known lon/lat point, read at multiple y-pixels to find
# where the point transitions from ocean to land

# Test: Cape of Good Hope (18.5°E, -34.4°S)
# This is a distinctive point. Just south of it (-35°S, 18°E) should be ocean.
# Just at it (-34°S, 18°E) could be land or coast.
# Just north of it (-33°S, 18°E) should be land.
print("\n--- Searching for Cape of Good Hope (18.5°E, -34.4°S) ---")
x_capetown = int((18.5 / 360) * NX)  # = 888
print(f"  x={x_capetown} (lon=18.5°E)")

# Read a vertical strip at x=888, all y values, surface only
# Can't read all y at once, so sample every 100 pixels
for y_test in range(0, NY, 200):
    val = db.db.read(time=0, x=[x_capetown, x_capetown+1],
                     y=[y_test, y_test+1], z=[0,1], quality=0)
    v = val.ravel()[0]
    if abs(v) > 0.001:
        status = f"OCEAN ({v:.1f}°C)"
    else:
        status = "LAND"
    # Only print near transitions
    if y_test % 1000 == 0 or y_test < 200:
        print(f"  y={y_test:>6}: {status}")

# Better: read at finer spacing near expected transitions
print("\n--- Fine search: lon=18.5°E, scanning y for Cape of Good Hope ---")
# Cape of Good Hope is at ~34.4°S. Let's find it.
for y_test in range(3000, 6000, 50):
    val = db.db.read(time=0, x=[x_capetown, x_capetown+1],
                     y=[y_test, y_test+1], z=[0,1], quality=0)
    v = val.ravel()[0]
    if abs(v) > 0.001:
        status = f"OCEAN ({v:>6.1f}°C)"
    else:
        status = "LAND"
    print(f"  y={y_test:>6}: {status}")

# Test: Strait of Gibraltar (lon=-5.6°, lat=36°N)
print("\n--- Fine search: lon=-5.6° (354.4°E), scanning y for Gibraltar ---")
x_gib = int((354.4 / 360) * NX)
print(f"  x={x_gib} (lon=-5.6°)")
for y_test in range(5000, 9000, 100):
    val = db.db.read(time=0, x=[x_gib, x_gib+1],
                     y=[y_test, y_test+1], z=[0,1], quality=0)
    v = val.ravel()[0]
    if abs(v) > 0.001:
        status = f"OCEAN ({v:>6.1f}°C)"
    else:
        status = "LAND"
    print(f"  y={y_test:>6}: {status}")

# Test: Tip of Florida (lon=-80°, lat=25°N)
print("\n--- Fine search: lon=-80° (280°E), scanning y for Florida ---")
x_fla = int((280 / 360) * NX)
print(f"  x={x_fla} (lon=-80°)")
for y_test in range(5000, 9000, 100):
    val = db.db.read(time=0, x=[x_fla, x_fla+1],
                     y=[y_test, y_test+1], z=[0,1], quality=0)
    v = val.ravel()[0]
    if abs(v) > 0.001:
        status = f"OCEAN ({v:>6.1f}°C)"
    else:
        status = "LAND"
    print(f"  y={y_test:>6}: {status}")
