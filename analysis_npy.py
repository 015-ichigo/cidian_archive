import os
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scipy.interpolate import griddata

# --------------------------------------------------------------
# TMS Electric Field Analysis
# --------------------------------------------------------------
# This script loads precomputed .npy electric field data for various
# head tissues, computes summary statistics, and visualizes both
# distribution and spatial patterns in 2D/3D.
# Data files should reside in the same directory as this script.
# Empty datasets and interpolation errors are handled gracefully.
# 3D scatter is oriented to face the voxel with maximum E-field.
# --------------------------------------------------------------

def load_field_data(path: str) -> np.ndarray:
    """
    Load electric field data from a .npy file.
    Returns empty array if missing or malformed.
    """
    if not os.path.isfile(path):
        print(f"Warning: Data file not found: {path}")
        return np.empty((0, 4))
    data = np.load(path)
    if data.ndim != 2 or data.shape[1] != 4:
        print(f"Warning: Unexpected data shape in {path}: {data.shape}")
        return np.empty((0, 4))
    return data


def compute_statistics(field: np.ndarray) -> dict:
    """
    Compute basic statistics of the electric field magnitudes.
    Returns NaN for empty data.
    """
    e_vals = field[:, 3]
    if e_vals.size == 0:
        return {k: np.nan for k in ('min', 'max', 'mean', 'std')}
    return {
        'min': np.min(e_vals),
        'max': np.max(e_vals),
        'mean': np.mean(e_vals),
        'std': np.std(e_vals),
    }


def plot_histogram(data: dict, bins: int = 50) -> None:
    """
    Plot overlapping histograms of E-field across tissue types.
    Skips empty datasets.
    """
    plt.figure(figsize=(8, 5))
    plotted = False
    for label, arr in data.items():
        if arr.size == 0:
            print(f"Skipping histogram for {label}: no data.")
            continue
        plt.hist(arr[:, 3], bins=bins, alpha=0.5, density=False, label=label)
        plotted = True
    if not plotted:
        print("No data available for histogram.")
        return
    plt.xlabel('E-field magnitude (V/m)')
    plt.ylabel('Voxel count')
    plt.title('Electric Field Distribution across Tissues')
    plt.legend()
    plt.tight_layout()
    #plt.show()


def plot_3d_scatter(field: np.ndarray, title: str, subsample: int = 5000) -> None:
    """
    3D scatter of E-field values at spatial voxels.
    Skips empty datasets. Uses rainbow colormap for E-field.
    The view is oriented to center on the maximum E-field voxel.
    """
    if field.size == 0:
        print(f"Skipping 3D scatter for {title}: no data.")
        return
    # Subsample for performance
    n_points = min(subsample, field.shape[0])
    indices = np.random.choice(field.shape[0], n_points, replace=False)
    sample = field[indices]

    # Determine max-field voxel from full dataset for orientation
    max_idx = np.argmax(field[:, 3])
    focal = field[max_idx, :3]

    # Compute center of sample cloud
    center = np.mean(sample[:, :3], axis=0)
    vec = focal - center
    # Spherical angles: elevation and azimuth
    r = np.linalg.norm(vec)
    if r > 0:
        elev = np.degrees(np.arcsin(vec[2] / r))
        azim = np.degrees(np.arctan2(vec[1], vec[0]))
    else:
        elev, azim = 30, 45  # default view

    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, projection='3d')
    sc = ax.scatter(
        sample[:, 0], sample[:, 1], sample[:, 2],
        c=sample[:, 3], cmap='jet', s=1, marker='o'
    )
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label('E-field (V/m)')

    # Set orientation
    ax.view_init(elev=elev, azim=azim)

    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    ax.set_zlabel('Z (mm)')
    ax.set_title(title)
    plt.tight_layout()
    #plt.show()


def plot_cross_section(field: np.ndarray,
                       axis: str = 'z',
                       coord: float = 0.0,
                       grid_size: int = 300) -> None:
    """
    Interpolated 2D heatmap of E-field on an orthogonal slice.
    Skips if no slice points found or interpolation fails.
    """
    if field.size == 0:
        print("Skipping cross-section: no data.")
        return
    axis = axis.lower()
    axes_map = {'x': 0, 'y': 1, 'z': 2}
    if axis not in axes_map:
        print("Invalid axis for cross-section. Use 'x', 'y', or 'z'.")
        return
    i = axes_map[axis]

    tol = (np.max(field[:, i]) - np.min(field[:, i])) / grid_size
    slice_pts = field[np.abs(field[:, i] - coord) < tol]
    if slice_pts.shape[0] == 0:
        print(f"Skipping cross-section at {axis}={coord:.2f}: no nearby voxels.")
        return

    dims = [0, 1, 2]
    dims.remove(i)
    xi, yi, zi = slice_pts[:, dims[0]], slice_pts[:, dims[1]], slice_pts[:, 3]

    xi_lin = np.linspace(np.min(xi), np.max(xi), grid_size)
    yi_lin = np.linspace(np.min(yi), np.max(yi), grid_size)
    X, Y = np.meshgrid(xi_lin, yi_lin)

    try:
        Z = griddata((xi, yi), zi, (X, Y), method='cubic')
    except Exception as e:
        print(f"Cubic interpolation failed at {axis}={coord:.2f}: {e}")
        print("Falling back to linear interpolation...")
        try:
            Z = griddata((xi, yi), zi, (X, Y), method='linear')
        except Exception as e2:
            print(f"Linear interpolation also failed: {e2}")
            return

    plt.figure(figsize=(6, 5))
    plt.imshow(Z.T,
               extent=(xi_lin[0], xi_lin[-1], yi_lin[0], yi_lin[-1]),
               origin='lower',
               aspect='auto')
    plt.xlabel(f"{['X','Y','Z'][dims[0]]} (mm)")
    plt.ylabel(f"{['X','Y','Z'][dims[1]]} (mm)")
    plt.title(f"Cross-section at {axis} = {coord:.2f} mm")
    plt.colorbar(label='E-field (V/m)')
    plt.tight_layout()
    #plt.show()


def run_analysis(base_dir):

    file_map = {
        'Scalp':       'e_scalp.npy',
        'CSF':         'e_csf.npy',
        'Gray Matter': 'e_gray_matter.npy',
        'White Matter':'e_white_matter.npy',
    }

    tissues = {}
    missing = []
    for name, fname in file_map.items():
        arr = load_field_data(os.path.join(base_dir, fname))
        if arr.size == 0:
            missing.append(name)
        tissues[name] = arr
    if missing:
        print(f"Warning: Missing data for: {', '.join(missing)}")

    print("=== Electric Field Summary (V/m) ===")
    for name, arr in tissues.items():
        stats = compute_statistics(arr)
        print(f"{name:12s}: min={stats['min']:.3e}, max={stats['max']:.3e}, "
              f"mean={stats['mean']:.3e}, std={stats['std']:.3e}")

    plot_histogram(tissues)
    for name, arr in tissues.items():
        plot_3d_scatter(arr, title=f"{name} E-field (3D)")
    gray = tissues.get('Gray Matter', np.empty((0,4)))
    if gray.size > 0:
        mid_z = 0.5 * (np.min(gray[:, 2]) + np.max(gray[:, 2]))
        plot_cross_section(gray, axis='z', coord=mid_z)


