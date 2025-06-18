import os
import glob
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


def load_all_data(npy_dir):
    """
    加载 npy_dir 下所有 e_*.npy 文件，
    返回形如 (M,3) 的坐标数组 coords 和 (M,) 的电场强度数组 e_vals。
    """
    files = sorted(glob.glob(os.path.join(npy_dir, 'e_*.npy')))
    if not files:
        raise FileNotFoundError(f"No e_*.npy files found in {npy_dir}")
    coords_list = []
    e_list = []
    for f in files:
        data = np.load(f)
        if data.size == 0:
            continue
        coords_list.append(data[:, :3])
        e_list.append(data[:, 3])
    # 合并所有组织
    coords = np.vstack(coords_list)  # (M,3)
    e_vals = np.concatenate(e_list)  # (M,)
    return coords, e_vals


def plot_combined(coords, e_vals, cmap='viridis', s=1, out_png='combined_e_fields.png'):
    """
    在一张 3D 散点图中绘制所有坐标，颜色由电场强度决定。
    """
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection='3d')

    sc = ax.scatter(
        coords[:, 0], coords[:, 1], coords[:, 2],
        c=e_vals, cmap=cmap, s=s, marker='o', alpha=0.6
    )
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    ax.set_zlabel('Z (mm)')
    ax.set_title('All Tissues Electric Field Distribution')

    # 添加统一 colorbar
    cbar = plt.colorbar(sc, ax=ax, fraction=0.03, pad=0.1)
    cbar.set_label('Electric Field Strength (V/m)')

    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    print(f"Saved combined figure to {out_png}")
    plt.show()


if __name__ == '__main__':
    npy_directory = 'npy_outputs'  # 你的 npy 文件夹
    coords, e_vals = load_all_data(npy_directory)
    plot_combined(coords, e_vals)
