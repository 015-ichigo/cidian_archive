import numpy as np
from simnibs.mesh_tools.mesh_io import read_msh
import os

# 1. 读取网格
mesh_path = 'tms_simu/ernie_TMS_1-0001_Magstim_70mm_Fig8_scalar.msh'
mesh = read_msh(mesh_path)

# 2. 组织标签映射（请按模型实际标签确认）
TISSUE_TAGS = {
    'white_matter': 1,
    'gray_matter': 2,
    'csf': 3,
    'bone': 4,
    'scalp': 5
}

# 3. 计算所有单元重心和电场
centers = mesh.elements_baricenters()[:]  # (n_elm, 3)
emag = mesh.field['magnE'][:]  # (n_elm,)

# 4. 为每个组织生成 (N,4) 数组并保存
out_dir = 'npy_outputs'
os.makedirs(out_dir, exist_ok=True)

for name, tag in TISSUE_TAGS.items():
    # 4.1 构造掩码，筛选该组织单元
    mask = (mesh.elm.tag1 == tag)

    # 4.2 取出对应单元的重心和电场
    coords = centers[mask]  # (Ni,3)
    fields = emag[mask].reshape(-1, 1)  # (Ni,1)

    # 4.3 合并为 (Ni,4)
    data = np.hstack((coords, fields))

    # 4.4 保存为 .npy
    fname = os.path.join(out_dir, f'e_{name}.npy')
    np.save(fname, data)
    print(f"Saved {coords.shape[0]} entries for {name} → {fname}")
