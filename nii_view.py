#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interactive_nifti_scroll_viewer_mip_orientations.py

交互式 NIfTI 浏览器：支持轴向/冠状/矢状切片 + 第四象限展示不同方向的最大强度投影 (MIP)。
"""

import os
import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt



def load_nifti(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"文件未找到: {path}")
    img = nib.load(path)
    data = img.get_fdata(caching='unchanged')
    return data, img.affine


class ScrollSliceViewer:
    def __init__(self, data):
        self.data = data
        self.idx = [data.shape[0] // 2,
                    data.shape[1] // 2,
                    data.shape[2] // 2]
        self.dim_map = {0: 2, 1: 1, 2: 0}
        self.mip_axis = 2  # 初始方向为轴向 (Z)

        self.fig, axes = plt.subplots(2, 2, figsize=(10, 10))
        self.axes = axes.flatten()
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)

        self._setup_display()
        plt.tight_layout()
        #plt.show()

    def _setup_display(self):
        ax0 = self.axes[0]
        self.axial_im = ax0.imshow(
            np.rot90(self.data[:, :, self.idx[2]]),
            cmap='gray', interpolation='nearest'
        )
        ax0.set_title(f'Axial (Z={self.idx[2]})')
        ax0.axis('off')

        ax1 = self.axes[1]
        self.coronal_im = ax1.imshow(
            np.rot90(self.data[:, self.idx[1], :]),
            cmap='gray', interpolation='nearest'
        )
        ax1.set_title(f'Coronal (Y={self.idx[1]})')
        ax1.axis('off')

        ax2 = self.axes[2]
        self.sagittal_im = ax2.imshow(
            np.rot90(self.data[self.idx[0], :, :]),
            cmap='gray', interpolation='nearest'
        )
        ax2.set_title(f'Sagittal (X={self.idx[0]})')
        ax2.axis('off')

        ax3 = self.axes[3]
        mip = np.max(self.data, axis=self.mip_axis)
        self.mip_im = ax3.imshow(
            np.rot90(mip), cmap='gray', interpolation='nearest'
        )
        ax3.set_title(self._mip_title())
        ax3.axis('off')

    def on_scroll(self, event):
        step = 1 if event.button == 'up' else -1
        for idx_ax, ax in enumerate(self.axes[:4]):
            if event.inaxes == ax:
                if idx_ax == 3:
                    # 在第四象限切换不同方向的 MIP
                    self.mip_axis = (self.mip_axis + step) % 3
                    self._update_mip()
                    self.fig.canvas.draw_idle()
                    break
                else:
                    dim = self.dim_map[idx_ax]
                    self.idx[dim] = np.clip(
                        self.idx[dim] + step,
                        0, self.data.shape[dim] - 1
                    )
                    self._update_slice(idx_ax)
                    self.fig.canvas.draw_idle()
                    break

    def _update_slice(self, ax_idx):
        if ax_idx == 0:
            self.axial_im.set_data(
                np.rot90(self.data[:, :, self.idx[2]])
            )
            self.axes[0].set_title(f'Axial (Z={self.idx[2]})')
        elif ax_idx == 1:
            self.coronal_im.set_data(
                np.rot90(self.data[:, self.idx[1], :])
            )
            self.axes[1].set_title(f'Coronal (Y={self.idx[1]})')
        else:
            self.sagittal_im.set_data(
                np.rot90(self.data[self.idx[0], :, :])
            )
            self.axes[2].set_title(f'Sagittal (X={self.idx[0]})')

    def _update_mip(self):
        mip = np.max(self.data, axis=self.mip_axis)
        self.mip_im.set_data(np.rot90(mip))
        self.axes[3].set_title(self._mip_title())

    def _mip_title(self):
        axis_names = {0: "Sagittal MIP (X-axis)", 1: "Coronal MIP (Y-axis)", 2: "Axial MIP (Z-axis)"}
        return axis_names[self.mip_axis]


def begin(path):
    data, _ = load_nifti(path)
    return ScrollSliceViewer(data)
