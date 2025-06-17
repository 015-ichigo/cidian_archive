import meshio
import vtk
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor


def meshio_to_vtk_unstructured_grid(mesh):
    print("all right")
    """将 meshio 读取的数据转换为 vtkUnstructuredGrid，支持 tetra 和 triangle"""
    points = vtk.vtkPoints()
    for p in mesh.points:
        points.InsertNextPoint(p[:3])

    ugrid = vtk.vtkUnstructuredGrid()
    ugrid.SetPoints(points)


    # 添加 tetra 四面体
    if "tetra" in mesh.cells_dict:
        for cell in mesh.cells_dict["tetra"]:
            tetra = vtk.vtkTetra()
            for i in range(4):
                tetra.GetPointIds().SetId(i, cell[i])
            ugrid.InsertNextCell(tetra.GetCellType(), tetra.GetPointIds())

    # 添加 triangle 面片
    if "triangle" in mesh.cells_dict:
        for cell in mesh.cells_dict["triangle"]:
            triangle = vtk.vtkTriangle()
            for i in range(3):
                triangle.GetPointIds().SetId(i, cell[i])
            ugrid.InsertNextCell(triangle.GetCellType(), triangle.GetPointIds())

    return ugrid


class SimpleMeshViewer(QWidget):
    def __init__(self, mesh_filename, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        layout.addWidget(self.vtk_widget)

        self.renderer = vtk.vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()




    def set_vtk_grid(self, vtk_grid):
        mapper = vtk.vtkDataSetMapper()
        mapper.SetInputData(vtk_grid)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)


        self.renderer.AddActor(actor)
        self.renderer.ResetCamera()
        self.renderer.SetBackground(0.1, 0.1, 0.2)
