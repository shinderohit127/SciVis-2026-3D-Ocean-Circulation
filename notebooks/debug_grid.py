"""Debug script to find correct lat/lon mapping for LLC4320 OpenVisus grid."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np
from data_access_llc4320 import cache_load

data = cache_load('test_global_surface_q8')
n_lat, n_lon = data.shape
print(f"Data shape: {data.shape}")

def to_pixel(lon, lat, lon_min=0, lon_max=360, lat_min=-90, lat_max=90):
    px = int(((lon % 360 - lon_min) / (lon_max - lon_min)) * n_lon)
    py = int(((lat - lat_min) / (lat_max - lat_min)) * n_lat)
    return max(0, min(px, n_lon-1)), max(0, min(py, n_lat-1))

test_points = [
    (-40, 30,  "ocean", "Mid-Atlantic"),
    (-80, 25,  "ocean", "Gulf of Mexico"),
    (-90, 30,  "land",  "Louisiana"),
    (0,   50,  "ocean", "English Channel"),
    (20,  0,   "land",  "Congo Africa"),
    (75,  20,  "ocean", "Arabian Sea"),
    (78,  20,  "land",  "India west"),
    (150, -25, "ocean", "Coral Sea"),
    (135, -25, "land",  "Central Australia"),
    (-70, -35, "ocean", "S Atlantic Argentina"),
    (30,  -5,  "land",  "E Africa Tanzania"),
    (140, 40,  "ocean", "Sea of Japan"),
    (-20, 65,  "ocean", "Iceland area"),
    (10,  45,  "land",  "N Italy"),
    (105, 15,  "ocean", "S China Sea"),
    (-50, -5,  "land",  "NE Brazil"),
]

# Test current mapping: LON=[0,360], LAT=[-90,90]
print("\n=== Current mapping: LON=[0,360], LAT=[-90,90] ===")
mm = 0
for lon, lat, expected, desc in test_points:
    px, py = to_pixel(lon, lat, 0, 360, -90, 90)
    val = data[py, px]
    actual = "land" if val == 0 else "ocean"
    ok = "OK" if actual == expected else "WRONG"
    if ok == "WRONG": mm += 1
    print(f"  {lon:>6},{lat:>4} -> px={px:>4},py={py:>4}  val={val:>7.2f}  {expected:>5}->{actual:>5}  {ok:>5}  {desc}")
print(f"  MISMATCHES: {mm}/{len(test_points)}")

# Try alternative lat ranges
for lat_min, lat_max in [(-80, 80), (-85, 85), (-90, 80), (-80, 90), (-70, 70)]:
    mm = 0
    for lon, lat, expected, desc in test_points:
        if lat < lat_min or lat > lat_max:
            continue
        px, py = to_pixel(lon, lat, 0, 360, lat_min, lat_max)
        val = data[py, px]
        actual = "land" if val == 0 else "ocean"
        if actual != expected:
            mm += 1
    print(f"  LAT=[{lat_min},{lat_max}]: {mm} mismatches")

# Now try to find the actual lat bounds empirically
# Strategy: find where the tropical warm band is (should be ~0-10°N)
# The warmest row should be near the equator
row_means = np.array([np.nanmean(np.where(data[r] != 0, data[r], np.nan)) for r in range(n_lat)])
warmest_row = np.nanargmax(row_means)
print(f"\nWarmest row: y={warmest_row} (frac={warmest_row/n_lat:.3f})")
print(f"  If LAT=[-90,90]: lat = {-90 + warmest_row/n_lat * 180:.1f}")
print(f"  If LAT=[-80,80]: lat = {-80 + warmest_row/n_lat * 160:.1f}")
print(f"  Expected: ~5-10°N (thermal equator)")

# Find the southernmost and northernmost ocean pixels
for c in [0, n_lon//4, n_lon//2, 3*n_lon//4]:
    col = data[:, c]
    ocean = np.where(col != 0)[0]
    if len(ocean) > 0:
        print(f"  Col {c}: ocean y=[{ocean[0]}, {ocean[-1]}]")
        print(f"    If LAT=[-90,90]: [{-90 + ocean[0]/n_lat*180:.1f}, {-90 + ocean[-1]/n_lat*180:.1f}]")
        print(f"    If LAT=[-80,80]: [{-80 + ocean[0]/n_lat*160:.1f}, {-80 + ocean[-1]/n_lat*160:.1f}]")

# Direct test: read a few points from the LIVE server to check
print("\n=== Live server spot checks ===")
try:
    from data_access_llc4320 import get_db, NX, NY
    db = get_db("theta")

    # Read at full res specific pixels and compare with what we expect
    # The data dimensions are (z, y, x) = (90, 12960, 17280)
    # If lon=0° is x=0, then x=8640 = 180°E (dateline)
    # Read a single surface point at known locations

    # Test: read the pixel that SHOULD be mid-Atlantic (lon=-40, lat=30)
    # With LON=[0,360]: x = 320/360 * 17280 = 15360
    # With LAT=[-90,90]: y = 120/180 * 12960 = 8640
    for test_lon, test_lat, desc in [(-40, 30, "Mid-Atlantic"), (20, 0, "Congo"), (135, -25, "Australia")]:
        x_pix = int(((test_lon % 360) / 360) * NX)
        y_pix = int(((test_lat + 90) / 180) * NY)
        val = db.db.read(time=0, x=[x_pix, x_pix+1], y=[y_pix, y_pix+1], z=[0,1], quality=0)
        print(f"  {desc} ({test_lon},{test_lat}): x={x_pix}, y={y_pix}, val={val.ravel()[0]:.2f}")
except Exception as e:
    print(f"  Server check failed: {e}")
