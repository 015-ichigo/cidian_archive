import meshio
import vtk
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import os
import glob
import numpy as np
from vtkmodules.util.numpy_support import numpy_to_vtk



os.environ['VTK_SILENCE_GET_VOID_POINTER_WARNINGS'] = '1'
os.environ['VTK_DEBUG_LEAKS'] = '0'

# 2. 禁用VTK警告和错误输出
vtk.vtkObject.GlobalWarningDisplayOff()
output = vtk.vtkFileOutputWindow()
output.SetFileName("NUL")
vtk.vtkOutputWindow.SetInstance(output)



def load_all_data(npy_dir):
    # 优先查找 e_gray_matter.npy
    gray_matter_file = os.path.join(npy_dir, 'e_gray_matter.npy')
    white_matter_file = os.path.join(npy_dir, 'e_white_matter.npy')

    files = []
    if os.path.exists(gray_matter_file):
        files.append(gray_matter_file)
    elif os.path.exists(white_matter_file):
        files.append(white_matter_file)
    else:
        # 如果两个特定文件都不存在，回退到原来的逻辑
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

    coords = np.vstack(coords_list)
    e_vals = np.concatenate(e_list)
    return coords, e_vals


def meshio_to_vtk_unstructured_grid_max(mesh,npy_dir):
    print(npy_dir)
    points = vtk.vtkPoints()
    for p in mesh.points:
        points.InsertNextPoint(p[:3])
    base_id = points.GetNumberOfPoints()

    ugrid = vtk.vtkUnstructuredGrid()
    print("11111")
    coords, e_vals = load_all_data(npy_dir)
    print(coords,e_vals)
    pidlist = [points.InsertNextPoint(p[:3]) for p in coords]
    ugrid.SetPoints(points)

    for i, p in enumerate(coords):
        vertex = vtk.vtkVertex()
        vertex.GetPointIds().SetId(0, pidlist[i])
        ugrid.InsertNextCell(vertex.GetCellType(), vertex.GetPointIds())

    if "tetra" in mesh.cells_dict:
        for cell in mesh.cells_dict["tetra"]:
            tetra = vtk.vtkTetra()
            for i in range(4):
                tetra.GetPointIds().SetId(i, cell[i])
            ugrid.InsertNextCell(tetra.GetCellType(), tetra.GetPointIds())

    if "triangle" in mesh.cells_dict:
        for cell in mesh.cells_dict["triangle"]:
            triangle = vtk.vtkTriangle()
            for i in range(3):
                triangle.GetPointIds().SetId(i, cell[i])
            ugrid.InsertNextCell(triangle.GetCellType(), triangle.GetPointIds())

    total_points = points.GetNumberOfPoints()
    full_vals = np.zeros(total_points)
    full_vals[base_id:] = e_vals
    vtk_array = numpy_to_vtk(full_vals, deep=True)
    vtk_array.SetName("e")
    ugrid.GetPointData().AddArray(vtk_array)
    ugrid.GetPointData().SetScalars(vtk_array)

    return ugrid


class MeshViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        layout.addWidget(self.vtk_widget)

        self.renderer = vtk.vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()

        # 初始化设置
        self.renderer.GetRenderWindow().SetAlphaBitPlanes(1)
        self.renderer.GetRenderWindow().SetMultiSamples(0)
        self.renderer.SetUseDepthPeeling(True)
        self.renderer.SetMaximumNumberOfPeels(100)
        self.renderer.SetOcclusionRatio(0.1)
        self.renderer.SetBackground(0.1, 0.1, 0.2)

    def load_mesh(self, mesh_filename,npy_dir):
        """通过文件名加载网格"""
        mesh = meshio.read(mesh_filename)
        vtk_grid = meshio_to_vtk_unstructured_grid_max(mesh,npy_dir)
        self.set_vtk_grid_max(vtk_grid)

    def set_vtk_grid_max(self, vtk_grid):
        """直接设置VTK网格数据"""
        # 清除旧的actors
        self.renderer.RemoveAllViewProps()

        mapper = vtk.vtkDataSetMapper()
        mapper.SetInputData(vtk_grid)
        mapper.SelectColorArray("e")
        mapper.SetScalarRange(vtk_grid.GetPointData().GetScalars().GetRange())
        mapper.SetColorModeToMapScalars()
        mapper.ScalarVisibilityOn()

        lut = vtk.vtkLookupTable()
        lut.SetNumberOfTableValues(256)
        min_val, max_val = vtk_grid.GetPointData().GetScalars().GetRange()
        lut.SetTableRange(min_val, max_val * 0.3)
        lut.Build()

        for i in range(256):
            t = i / 255.0
            if t < 0.05:
                r, g, b = 1.0, 1.0, 1.0
                t = 0.2
            elif t < 0.5:
                f = (t - 0.05) / 0.45
                r = g = f
                b = 1.0 - f
                t = 1
            else:
                f = (t - 0.5) / 0.5
                r = 1.0
                g = 1.0 - f
                b = 0.0
                t = 1
            lut.SetTableValue(i, r, g, b, t)

        mapper.SetLookupTable(lut)
        mapper.SetUseLookupTableScalarRange(True)

        scalar_bar = vtk.vtkScalarBarActor()
        scalar_bar.SetLookupTable(lut)
        scalar_bar.SetTitle("Object Type")
        scalar_bar.SetNumberOfLabels(4)

        # 自定义颜色条位置和样式
        scalar_bar.SetPosition(0.02, 0.1)  # 左侧
        scalar_bar.SetWidth(0.08)
        scalar_bar.SetHeight(0.8)

        # 设置文本属性
        scalar_bar.GetTitleTextProperty().SetColor(1, 1, 1)
        scalar_bar.GetTitleTextProperty().SetFontSize(18)
        scalar_bar.GetTitleTextProperty().SetBold(True)
        scalar_bar.GetLabelTextProperty().SetColor(1, 1, 1)
        scalar_bar.GetLabelTextProperty().SetFontSize(14)

        # 设置颜色条方向为垂直
        scalar_bar.SetOrientationToVertical()

        self.renderer.AddActor2D(scalar_bar)


        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetOpacity(1)
        actor.GetProperty().SetInterpolationToPhong()
        actor.GetProperty().BackfaceCullingOff()

        self.renderer.AddActor(actor)
        self.renderer.ResetCamera()