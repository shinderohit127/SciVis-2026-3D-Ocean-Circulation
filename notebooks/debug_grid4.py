"""Find the correct lat/lon mapping by matching row-level land patterns
to known geographic features at specific latitudes."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from data_access_llc4320 import cache_load, NX, NY

data = cache_load('test_global_surface_q8')
n_y, n_x = data.shape
scale = NX / n_x  # 16
pix_per_deg_x = n_x / 360.0  # 3 pixels per degree longitude
print(f"Data shape: {data.shape}, scale={scale}, pix/deg_lon={pix_per_deg_x:.1f}")

def row_land_mask(row_idx):
    """Return boolean array: True=land, False=ocean for a row."""
    return data[row_idx, :] == 0

def row_land_signature(row_idx):
    """Return list of (start_lon, end_lon) for each land mass in this row."""
    mask = row_land_mask(row_idx)
    lands = []
    in_land = False
    for i in range(n_x):
        if mask[i] and not in_land:
            in_land = True
            start = i
        elif not mask[i] and in_land:
            in_land = False
            width_deg = (i - start) / pix_per_deg_x
            if width_deg > 2:  # ignore tiny islands
                lon_start = start / pix_per_deg_x
                lon_end = i / pix_per_deg_x
                lands.append((lon_start, lon_end, width_deg))
    if in_land:
        width_deg = (n_x - start) / pix_per_deg_x
        if width_deg > 2:
            lands.append((start / pix_per_deg_x, 360, width_deg))
    return lands

# Print land signatures for every 10th row
print("\n=== Land signatures for all rows (wide land masses only) ===")
for row in range(0, n_y, 20):
    lands = row_land_signature(row)
    mean_temp = np.nanmean(np.where(data[row] != 0, data[row], np.nan))
    n_land = np.sum(data[row] == 0)
    if lands:
        desc = " | ".join([f"{s:.0f}-{e:.0f}({w:.0f})" for s, e, w, in lands])
        print(f"  row {row:>4} (frac={row/n_y:.3f}): mean_T={mean_temp:>5.1f}C  land%={100*n_land/n_x:>4.0f}%  lands: {desc}")

# Now check the face boundary rows specifically
print("\n=== Face boundaries ===")
face_boundaries = [int(4320/scale), int(8640/scale)]
for fb in face_boundaries:
    for offset in [-2, -1, 0, 1, 2]:
        row = fb + offset
        if 0 <= row < n_y:
            vals = data[row, :]
            ocean = vals[vals != 0]
            if len(ocean) > 0:
                print(f"  row {row}: mean_T={ocean.mean():.1f}, min={ocean.min():.1f}, max={ocean.max():.1f}, land%={100*np.sum(vals==0)/n_x:.0f}%")
            else:
                print(f"  row {row}: ALL LAND")

# Identify specific latitudes by their distinctive land patterns
# Reference: at lat=0 (equator), lon=0-360, the land masses should be:
# - Africa: ~10°-42° (covers ~30° of longitude at equator)
# - Indonesia: ~95-140° (islands, might show as multiple small land masses)
# - South America: ~280-310° (Amazon region)
#
# At lat=30N:
# - North Africa/Sahara: ~0-30° (Morocco/Algeria)
# - Mediterranean: ~30° (gap)
# - Middle East: ~35-55°
# - Iran/India: ~55-90°
# - Pacific gap: ~120-240° (no land)
# - Mexico: ~240-260° (or 120W-100W)
# - US: ~260-280°
# - Atlantic gap: ~280-360°

print("\n=== Temperature at face boundary rows ===")
# Check if there's a discontinuity at the face boundaries
for fb in face_boundaries:
    print(f"\nFace boundary at row {fb} (full_res y={int(fb*scale)}):")
    for row in range(max(0,fb-5), min(n_y, fb+5)):
        vals = data[row, :]
        ocean = vals[vals != 0]
        if len(ocean) > 0:
            # Sample a few specific columns
            samples = [data[row, int(n_x*f)] for f in [0.0, 0.25, 0.5, 0.75]]
            sample_str = " ".join([f"{v:.1f}" for v in samples])
            print(f"  row {row}: mean={ocean.mean():.1f}  samples=[{sample_str}]")
        else:
            print(f"  row {row}: ALL LAND")

# Also check the column pattern for identifying longitude mapping
# At lon=0 (Prime Meridian), going from y=0 upward:
# The first land should be Antarctica (~-70S), then ocean, then Gulf of Guinea
# coast of Africa (~5N), then Sahara/Morocco/Spain (up to ~43N), then Atlantic
print("\n=== Column at x=0 (should be lon=0° = Prime Meridian) ===")
col0 = data[:, 0]
for row in range(0, n_y, 10):
    v = col0[row]
    status = "LAND" if v == 0 else f"OCEAN({v:.1f}C)"
    # Only print near transitions
    if row == 0 or row >= n_y-1:
        print(f"  row {row}: {status}")
    elif (col0[max(0,row-1)] == 0) != (v == 0):
        print(f"  row {row}: {status} *** TRANSITION ***")

# Generate a diagnostic figure: data with face boundary lines
print("\n=== Generating diagnostic figure ===")
data_masked = data.astype(float)
data_masked[data_masked == 0] = np.nan

fig, ax = plt.subplots(figsize=(16, 10))
im = ax.imshow(data_masked, origin="lower", cmap="turbo", aspect="auto")
plt.colorbar(im, ax=ax, label="Temperature (C)")

# Draw face boundaries
for fb in face_boundaries:
    ax.axhline(fb, color="red", linewidth=2, linestyle="--", label=f"Face boundary y={int(fb*scale)}")

# Mark the warmest row
ax.axhline(533, color="cyan", linewidth=1, linestyle=":", label="Warmest row")

ax.set_title("LLC4320 Surface Temp with Face Boundaries")
ax.set_xlabel("x pixel")
ax.set_ylabel("y pixel")
ax.legend(loc="upper right")

fig.savefig(os.path.join(os.path.dirname(__file__), "..", "figures", "debug_face_boundaries.png"),
            dpi=150, bbox_inches="tight")
plt.close()
print("Saved: figures/debug_face_boundaries.png")
