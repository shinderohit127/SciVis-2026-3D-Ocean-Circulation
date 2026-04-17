"""Brute-force search for correct LLC4320 lat/lon mapping."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from data_access_llc4320 import cache_load

data = cache_load('test_global_surface_q8')
n_lat, n_lon = data.shape
print(f"Data shape: {data.shape}")

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
    (-70, -35, "ocean", "S Atlantic"),
    (30,  -5,  "land",  "E Africa"),
    (140, 40,  "ocean", "Sea of Japan"),
    (-20, 65,  "ocean", "Iceland area"),
    (10,  45,  "land",  "N Italy"),
    (105, 15,  "ocean", "S China Sea"),
    (-50, -5,  "land",  "NE Brazil"),
]


def count_matches(lon_min, lon_max, lat_min, lat_max):
    matches = 0
    total = 0
    for lon, lat, expected, desc in test_points:
        if lat < lat_min or lat > lat_max:
            continue
        total += 1
        px = int(((lon % 360 - lon_min) / (lon_max - lon_min)) * n_lon)
        py = int(((lat - lat_min) / (lat_max - lat_min)) * n_lat)
        px = max(0, min(px, n_lon - 1))
        py = max(0, min(py, n_lat - 1))
        val = data[py, px]
        actual = "land" if val == 0 else "ocean"
        if actual == expected:
            matches += 1
    return matches, total


# Sweep lat_min and lat_max (keep lon fixed at [0,360])
print("\n=== Sweeping latitude bounds ===")
best = (0, 0, 0, 0)
for lat_min_i in range(-90, -50):
    for lat_max_i in range(60, 91):
        m, t = count_matches(0, 360, lat_min_i, lat_max_i)
        if m > best[0]:
            best = (m, t, lat_min_i, lat_max_i)
            if m >= 14:
                print(f"  LAT=[{lat_min_i}, {lat_max_i}]: {m}/{t} matches")

print(f"\nBest: LAT=[{best[2]}, {best[3]}]: {best[0]}/{best[1]} matches")

# Now also try lon offsets
print("\n=== Sweeping lon offset + lat bounds ===")
best = (0, 0, 0, 0, 0)
for lon_off in range(-20, 21):
    for lat_min_i in range(-90, -50):
        for lat_max_i in range(60, 91):
            m, t = count_matches(lon_off, 360 + lon_off, lat_min_i, lat_max_i)
            if m > best[0]:
                best = (m, t, lon_off, lat_min_i, lat_max_i)

print(f"Best: LON=[{best[2]}, {360+best[2]}], LAT=[{best[3]}, {best[4]}]: {best[0]}/{best[1]} matches")

# Detail for best
lon_min_b, lon_max_b = best[2], 360 + best[2]
lat_min_b, lat_max_b = best[3], best[4]
print(f"\n=== Best mapping detail ===")
for lon, lat, expected, desc in test_points:
    if lat < lat_min_b or lat > lat_max_b:
        print(f"  {lon:>6},{lat:>4}  SKIPPED (out of lat range)  {desc}")
        continue
    px = int(((lon % 360 - lon_min_b) / (lon_max_b - lon_min_b)) * n_lon)
    py = int(((lat - lat_min_b) / (lat_max_b - lat_min_b)) * n_lat)
    px = max(0, min(px, n_lon - 1))
    py = max(0, min(py, n_lat - 1))
    val = data[py, px]
    actual = "land" if val == 0 else "ocean"
    ok = "OK" if actual == expected else "WRONG"
    print(f"  {lon:>6},{lat:>4} -> px={px:>4},py={py:>4}  val={val:>7.2f}  {expected:>5}->{actual:>5}  {ok}  {desc}")

# Generate a test plot with the best mapping
print("\n=== Generating test plot with best mapping ===")
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    data_masked = data.astype(float)
    data_masked[data_masked == 0] = np.nan

    lons = np.linspace(lon_min_b, lon_max_b, n_lon, endpoint=False)
    lats = np.linspace(lat_min_b, lat_max_b, n_lat, endpoint=False)
    lons_plot = np.where(lons > 180, lons - 360, lons)

    fig, ax = plt.subplots(figsize=(16, 8), subplot_kw={"projection": ccrs.PlateCarree()})
    lon_grid, lat_grid = np.meshgrid(lons_plot, lats)
    im = ax.pcolormesh(lon_grid, lat_grid, data_masked,
                       cmap="turbo", transform=ccrs.PlateCarree(), shading="auto")
    ax.coastlines(resolution="110m", color="black", linewidth=0.8)
    ax.set_global()
    plt.colorbar(im, ax=ax, label="Temperature (C)", shrink=0.6)
    ax.set_title(f"Test: LON=[{lon_min_b},{lon_max_b}], LAT=[{lat_min_b},{lat_max_b}]")
    fig.savefig(os.path.join(os.path.dirname(__file__), "..", "figures", "debug_best_mapping.png"),
                dpi=150, bbox_inches="tight")
    plt.close()
    print("Saved: figures/debug_best_mapping.png")
except Exception as e:
    print(f"Plot failed: {e}")
    import traceback
    traceback.print_exc()
