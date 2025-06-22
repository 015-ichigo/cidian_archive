import meshio
import vtk
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication, QLabel
from PyQt6.QtCore import Qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import sys
import os


def meshio_to_vtk_unstructured_grid(mesh):
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


def load_vtk_file(filename):
    """加载VTK文件"""
    try:
        # 首先尝试使用meshio读取
        try:
            mesh = meshio.read(filename)
            return meshio_to_vtk_unstructured_grid(mesh)
        except:
            # 如果meshio失败，尝试使用VTK原生读取器
            reader = None
            file_ext = os.path.splitext(filename)[1].lower()

            if file_ext == '.vtk':
                reader = vtk.vtkUnstructuredGridReader()
            elif file_ext == '.vtu':
                reader = vtk.vtkXMLUnstructuredGridReader()
            elif file_ext == '.vtp':
                reader = vtk.vtkXMLPolyDataReader()
            elif file_ext == '.ply':
                reader = vtk.vtkPLYReader()
            elif file_ext == '.stl':
                reader = vtk.vtkSTLReader()

            if reader:
                reader.SetFileName(filename)
                reader.Update()
                return reader.GetOutput()
            else:
                print(f"不支持的文件格式: {file_ext}")
                return None

    except Exception as e:
        print(f"加载文件 {filename} 失败: {e}")
        return None


class MultiMeshViewer(QWidget):
    def __init__(self, mesh_path, parent=None):
        super().__init__(parent)

        # 设置窗口标题和大小
        self.setWindowTitle("多VTK文件查看器 - 按1-5键切换显示")
        self.setGeometry(100, 100, 800, 600)

        # 创建布局
        layout = QVBoxLayout(self)

        # 添加提示标签
        self.info_label = QLabel("当前显示: 所有模型 | 按键盘1-5切换单个模型，按0显示所有模型")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)

        # 创建VTK组件
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        layout.addWidget(self.vtk_widget)

        self.renderer = vtk.vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()

        # 存储网格数据和对应的actor
        self.vtk_grids = []
        self.actors = []
        self.mesh_filenames = [
            os.path.join(mesh_path,"vtk_model/bone.vtk"),
            os.path.join(mesh_path, "vtk_model/csf.vtk"),
            os.path.join(mesh_path, "vtk_model/scalp.vtk"),
            os.path.join(mesh_path, "vtk_model/gray_matter.vtk"),
            os.path.join(mesh_path, "vtk_model/white_matter.vtk"),
        ]

        # 定义不同的颜色
        self.colors = [
            (1.0, 0.0, 0.0),  # 红色
            (0.0, 1.0, 0.0),  # 绿色
            (0.0, 0.0, 1.0),  # 蓝色
            (1.0, 1.0, 0.0),  # 黄色
            (1.0, 0.0, 1.0),  # 品红色
        ]

        # 加载所有VTK文件
        self.load_all_meshes()

        # 设置键盘事件处理
        self.setup_keyboard_interaction()

        # 初始显示所有模型
        self.show_all_models()

        # 设置背景色
        self.renderer.SetBackground(0.1, 0.1, 0.2)

    def load_all_meshes(self):
        """加载所有网格文件"""
        print("开始加载VTK文件...")

        for i, filename in enumerate(self.mesh_filenames):
            if not os.path.exists(filename):
                print(f"文件不存在: {filename}")
                self.vtk_grids.append(None)
                self.actors.append(None)
                continue

            print(f"加载文件 {i + 1}/5: {filename}")
            vtk_grid = load_vtk_file(filename)

            if vtk_grid is not None:
                self.vtk_grids.append(vtk_grid)

                # 创建mapper和actor
                mapper = vtk.vtkDataSetMapper()
                mapper.SetInputData(vtk_grid)

                actor = vtk.vtkActor()
                actor.SetMapper(mapper)

                # 设置颜色
                #if i < len(self.colors):
                #    actor.GetProperty().SetColor(self.colors[i])

                # 设置透明度以便在组合显示时能看到内部结构
                #actor.GetProperty().SetOpacity(0.7)

                self.actors.append(actor)
                print(f"成功加载: {filename}")
            else:
                self.vtk_grids.append(None)
                self.actors.append(None)
                print(f"加载失败: {filename}")

    def setup_keyboard_interaction(self):
        """设置键盘交互"""

        # 创建键盘事件观察器
        def keypress_callback(obj, event):
            key = self.interactor.GetKeySym()

            if key == '0':
                self.show_all_models()
            elif key in ['1', '2', '3', '4', '5']:
                index = int(key) - 1
                self.show_single_model(index)

        self.interactor.AddObserver('KeyPressEvent', keypress_callback)

    def clear_renderer(self):
        """清空渲染器"""
        self.renderer.RemoveAllViewProps()

    def show_all_models(self):
        """显示所有模型"""
        self.clear_renderer()

        count = 0
        for i, actor in enumerate(self.actors):
            if actor is not None:
                # 设置透明度以便观察组合效果
                #actor.GetProperty().SetOpacity(0.6)
                self.renderer.AddActor(actor)
                count += 1

        self.info_label.setText(f"当前显示: 所有模型 ({count}个) | 按键盘1-5切换单个模型，按0显示所有模型")

        if count > 0:
            self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()

    def show_single_model(self, index):
        """显示单个模型"""
        if index >= len(self.actors) or self.actors[index] is None:
            print(f"模型 {index + 1} 不存在或加载失败")
            return

        self.clear_renderer()

        # 设置不透明度
        self.actors[index].GetProperty().SetOpacity(1.0)
        self.renderer.AddActor(self.actors[index])

        if(index ==0):
            filename = "骨骼"
        elif(index ==1):
            filename = "脑脊液"
        elif(index ==2):
            filename = "头皮"
        elif(index ==3):
            filename = "灰质"
        elif(index ==4):
            filename = "白质"
        self.info_label.setText(f"当前显示: 模型 {index + 1} ({filename}) | 按键盘1-5切换单个模型，按0显示所有模型")

        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()

    def keyPressEvent(self, event):
        """处理Qt键盘事件（备用方案）"""
        key = event.key()

        if key == Qt.Key.Key_0:
            self.show_all_models()
        elif Qt.Key.Key_1 <= key <= Qt.Key.Key_5:
            index = key - Qt.Key.Key_1
            self.show_single_model(index)

        super().keyPressEvent(event)


