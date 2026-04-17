"""
05_pyvista_3d.py — 3D ocean visualization with PyVista.

Run with: conda activate ocean && python notebooks/05_pyvista_3d.py

Produces:
  - Temperature isosurface renders (5°C, 10°C, 15°C, 20°C)
  - Volume rendering of temperature
  - 3D cross-section slices
  - Combined multi-isosurface scene

All renders are off-screen (no display needed) — saves PNGs to figures/.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pyvista as pv
import cmocean
import matplotlib.pyplot as plt

from data_access_llc4320 import cache_load, mask_land, DEPTH_LEVELS, NZ

FIGURES_DIR = os.path.join(os.path.dirname(__file__), "..", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

# Off-screen rendering for WSL/headless
pv.OFF_SCREEN = True
# Start virtual display if available
try:
    pv.start_xvfb()
except Exception:
    pass


def build_structured_grid(theta_vol, lons, lats, depths):
    """Build a PyVista StructuredGrid from the cached volume data.

    The LLC4320 volume has shape (n_depth, n_lat, n_lon).
    We create a 3D grid with:
      - x = longitude
      - y = latitude
      - z = -depth (negative because depth goes downward)

    The depth axis is scaled to make the visualization readable,
    since the ocean is ~5km deep but ~3000km wide.
    """
    n_depth, n_lat, n_lon = theta_vol.shape

    # Depth scaling factor: exaggerate vertical dimension
    # Ocean aspect ratio is ~500:1 (width:depth), so we scale up depth
    depth_scale = 0.01  # 1m depth = 0.01 degree equivalent

    # Create 3D coordinate arrays
    lon_3d = np.zeros((n_depth, n_lat, n_lon))
    lat_3d = np.zeros((n_depth, n_lat, n_lon))
    z_3d = np.zeros((n_depth, n_lat, n_lon))

    for k in range(n_depth):
        lon_3d[k, :, :] = lons[np.newaxis, :]
        lat_3d[k, :, :] = lats[:, np.newaxis]
        z_3d[k, :, :] = -depths[k] * depth_scale

    # PyVista StructuredGrid expects points in (x, y, z) order
    # Dimensions must be (n_lon, n_lat, n_depth) for the grid
    grid = pv.StructuredGrid(
        lon_3d.transpose(2, 1, 0),   # x = lon
        lat_3d.transpose(2, 1, 0),   # y = lat
        z_3d.transpose(2, 1, 0),     # z = -depth (scaled)
    )

    # Add temperature as point data
    # Transpose to match StructuredGrid point ordering (Fortran-order)
    grid.point_data["Temperature"] = theta_vol.transpose(2, 1, 0).ravel(order="F")

    return grid


def build_uniform_grid(theta_vol, lons, lats, depths):
    """Build a PyVista ImageData (uniform grid) — simpler, faster for isosurfaces.

    Uses a uniform grid approximation. Good enough for visualization
    since we're already at reduced resolution.
    """
    n_depth, n_lat, n_lon = theta_vol.shape

    # Mask land values → NaN
    vol = theta_vol.astype(np.float32).copy()
    vol[vol == 0] = np.nan

    grid = pv.ImageData(
        dimensions=(n_lon, n_lat, n_depth),
        spacing=(
            (lons[-1] - lons[0]) / max(n_lon - 1, 1),  # dx
            (lats[-1] - lats[0]) / max(n_lat - 1, 1),   # dy
            1.0,  # dz (uniform, we'll label depth separately)
        ),
        origin=(lons[0], lats[0], 0),
    )

    # Add data — ImageData uses (x, y, z) = (lon, lat, depth) ordering
    grid.point_data["Temperature"] = vol.transpose(2, 1, 0).ravel(order="F")

    return grid


def render_isosurfaces(grid, iso_values, figname="3d_isosurfaces.png"):
    """Render multiple temperature isosurfaces in a single scene."""
    pl = pv.Plotter(off_screen=True, window_size=(1920, 1080))
    pl.set_background("white")

    # Color map: warm colors for warm isosurfaces, cool for cold
    colors = {
        5: "#2166ac",    # cold — blue
        10: "#67a9cf",   # cool — light blue
        15: "#fddbc7",   # warm — light orange
        20: "#ef8a62",   # hot — orange
        25: "#b2182b",   # very hot — red
    }

    for iso_val in iso_values:
        try:
            iso = grid.contour([iso_val], scalars="Temperature")
            if iso.n_points > 0:
                color = colors.get(iso_val, "#999999")
                opacity = 0.35 if iso_val in [10, 15] else 0.5
                pl.add_mesh(iso, color=color, opacity=opacity,
                           label=f"{iso_val}°C", smooth_shading=True)
                print(f"  Isosurface {iso_val}°C: {iso.n_points} points")
        except Exception as e:
            print(f"  Warning: isosurface {iso_val}°C failed: {e}")

    # Add bounding box and axes
    pl.add_bounding_box(color="gray", line_width=1)
    pl.add_axes(xlabel="Lon", ylabel="Lat", zlabel="Depth Level")

    # Camera position: looking from southeast, slightly above
    pl.camera_position = "iso"
    pl.camera.azimuth = -30
    pl.camera.elevation = 25

    # Add legend
    pl.add_legend(bcolor="white", face=None, size=(0.15, 0.15))

    path = os.path.join(FIGURES_DIR, figname)
    pl.screenshot(path, scale=2)
    print(f"  Saved: {path}")
    pl.close()


def render_volume(grid, figname="3d_volume.png"):
    """Volume render of temperature."""
    pl = pv.Plotter(off_screen=True, window_size=(1920, 1080))
    pl.set_background("white")

    # Need to replace NaN for volume rendering
    vol_data = grid.point_data["Temperature"].copy()
    vol_data[np.isnan(vol_data)] = 0

    grid_clean = grid.copy()
    grid_clean.point_data["Temperature"] = vol_data

    # Create opacity transfer function
    # Low opacity for land (0°C) and mid-range temps, high for extremes
    opacity = [0.0, 0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7]

    pl.add_volume(grid_clean, scalars="Temperature",
                  cmap="turbo", opacity=opacity,
                  shade=True,
                  clim=[2, 30])

    pl.add_bounding_box(color="gray")
    pl.add_axes(xlabel="Lon", ylabel="Lat", zlabel="Depth Level")
    pl.camera_position = "iso"
    pl.camera.azimuth = -30
    pl.camera.elevation = 25

    path = os.path.join(FIGURES_DIR, figname)
    pl.screenshot(path, scale=2)
    print(f"  Saved: {path}")
    pl.close()


def render_orthogonal_slices(grid, figname="3d_slices.png"):
    """Render three orthogonal slice planes through the volume."""
    pl = pv.Plotter(off_screen=True, window_size=(1920, 1080))
    pl.set_background("white")

    bounds = grid.bounds
    x_mid = (bounds[0] + bounds[1]) / 2
    y_mid = (bounds[2] + bounds[3]) / 2
    z_mid = (bounds[4] + bounds[5]) / 2

    # Depth slice (horizontal, z=constant)
    try:
        z_slice = grid.slice(normal="z", origin=(x_mid, y_mid, z_mid))
        if z_slice.n_points > 0:
            pl.add_mesh(z_slice, scalars="Temperature", cmap="turbo",
                       clim=[2, 30], show_scalar_bar=False)
    except Exception as e:
        print(f"  z-slice failed: {e}")

    # Latitude slice (y=constant)
    try:
        y_slice = grid.slice(normal="y", origin=(x_mid, y_mid, z_mid))
        if y_slice.n_points > 0:
            pl.add_mesh(y_slice, scalars="Temperature", cmap="turbo",
                       clim=[2, 30], show_scalar_bar=False)
    except Exception as e:
        print(f"  y-slice failed: {e}")

    # Longitude slice (x=constant)
    try:
        x_slice = grid.slice(normal="x", origin=(x_mid, y_mid, z_mid))
        if x_slice.n_points > 0:
            pl.add_mesh(x_slice, scalars="Temperature", cmap="turbo",
                       clim=[2, 30], show_scalar_bar=True,
                       scalar_bar_args={"title": "Temperature (°C)"})
    except Exception as e:
        print(f"  x-slice failed: {e}")

    pl.add_bounding_box(color="gray", line_width=1)
    pl.add_axes(xlabel="Lon", ylabel="Lat", zlabel="Depth Level")
    pl.camera_position = "iso"
    pl.camera.azimuth = -45
    pl.camera.elevation = 30

    path = os.path.join(FIGURES_DIR, figname)
    pl.screenshot(path, scale=2)
    print(f"  Saved: {path}")
    pl.close()


def render_layered_view(grid, figname="3d_layers.png"):
    """Show the ocean as stacked horizontal slices at key depths,
    revealing the layered thermal structure."""
    pl = pv.Plotter(off_screen=True, window_size=(1920, 1080))
    pl.set_background("white")

    bounds = grid.bounds
    x_mid = (bounds[0] + bounds[1]) / 2
    y_mid = (bounds[2] + bounds[3]) / 2
    n_z = grid.dimensions[2]

    # Slice at multiple depth levels
    depth_fractions = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]
    for frac in depth_fractions:
        z_val = bounds[4] + frac * (bounds[5] - bounds[4])
        try:
            slc = grid.slice(normal="z", origin=(x_mid, y_mid, z_val))
            if slc.n_points > 0:
                pl.add_mesh(slc, scalars="Temperature", cmap="turbo",
                           clim=[2, 30], opacity=0.8,
                           show_scalar_bar=(frac == 0.5))
        except Exception:
            pass

    pl.add_bounding_box(color="gray", line_width=1)
    pl.add_axes(xlabel="Lon", ylabel="Lat", zlabel="Depth Level")
    pl.camera_position = "iso"
    pl.camera.azimuth = -30
    pl.camera.elevation = 35

    path = os.path.join(FIGURES_DIR, figname)
    pl.screenshot(path, scale=2)
    print(f"  Saved: {path}")
    pl.close()


# =================================================================
# MAIN
# =================================================================
if __name__ == "__main__":
    print("Building 3D visualizations with PyVista...")
    print()

    # Load cached volume
    theta_vol = cache_load("na_volume_theta")
    lons = cache_load("na_volume_lons")
    lats = cache_load("na_volume_lats")
    depths = cache_load("na_volume_depths")

    if theta_vol is None:
        print("ERROR: Run 02_cache_north_atlantic.py first!")
        sys.exit(1)

    print(f"Volume shape: {theta_vol.shape}")
    print(f"Lons: [{lons.min():.1f}, {lons.max():.1f}], n={len(lons)}")
    print(f"Lats: [{lats.min():.1f}, {lats.max():.1f}], n={len(lats)}")
    print(f"Depths: [{depths.min():.0f}, {depths.max():.0f}]m, n={len(depths)}")

    # Build the PyVista grid (uniform approximation)
    print("\nBuilding ImageData grid...")
    grid = build_uniform_grid(theta_vol, lons, lats, depths)
    print(f"Grid: {grid.dimensions}, {grid.n_points} points")

    # 1. Isosurfaces
    print("\n--- Rendering isosurfaces ---")
    render_isosurfaces(grid, [5, 10, 15, 20], figname="3d_isosurfaces.png")

    # 2. Orthogonal slices
    print("\n--- Rendering orthogonal slices ---")
    render_orthogonal_slices(grid, figname="3d_slices.png")

    # 3. Layered depth view
    print("\n--- Rendering layered depth view ---")
    render_layered_view(grid, figname="3d_layers.png")

    # 4. Volume rendering (may be slow)
    print("\n--- Rendering volume ---")
    try:
        render_volume(grid, figname="3d_volume.png")
    except Exception as e:
        print(f"  Volume rendering failed (this is common on some systems): {e}")
        print("  Skipping — isosurfaces are the primary 3D output.")

    print("\nDone! Check figures/ directory.")
