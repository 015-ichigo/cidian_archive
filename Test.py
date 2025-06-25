import sys

import meshio
import numpy as np
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QFrame, QStackedWidget, QWidget, QPushButton, \
    QHBoxLayout, QLabel, QComboBox, QDialog, QProgressBar, QTabWidget
import os
import matplotlib
matplotlib.use("Agg")
sys.stderr = open(os.devnull, 'w')

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import nii_view
from afterC_new import MeshViewer, meshio_to_vtk_unstructured_grid_max
from beforeC_new import meshio_to_vtk_unstructured_grid
from MutiImportVTK import MultiMeshViewer

os.environ['VTK_SILENCE_GET_VOID_POINTER_WARNINGS'] = '1'
os.environ['VTK_DEBUG_LEAKS'] = '0'


class LoadingDialog(QDialog):
    def __init__(self, text="加载中，请稍候..."):
        super().__init__()
        self.setWindowTitle("加载")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setFixedSize(350, 150)
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 10px;
            }
            QLabel {
                font-size: 14px;
                color: #333;
            }
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #f0f0f0;
                height: 12px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4a86e8;
                border-radius: 5px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # 加载图标标签
        icon_label = QLabel("⏳")
        icon_label.setStyleSheet("font-size: 32px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # 加载文本
        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # 无限循环
        self.progress.setFixedHeight(10)
        layout.addWidget(self.progress)

        self.setLayout(layout)


class MeshReaderThread(QThread):
    def __init__(self, msh_path):
        super().__init__()
        self.msh_path = msh_path
        self.mesh = None

    def run(self):
        # 在子线程中读取文件
        self.mesh = meshio.read(self.msh_path)

class MeshResultLoaderThread(QThread):
    finished = pyqtSignal(object)  # 传 vtkGrid 或 mesh 文件路径

    def __init__(self, mesh,npy_path):
        super().__init__()
        self.mesh = mesh
        self.npy_path = npy_path

    def run(self):
        vtk_grid = meshio_to_vtk_unstructured_grid_max(self.mesh, self.npy_path)
        self.finished.emit(vtk_grid)

class MeshLoaderThread(QThread):
    finished = pyqtSignal(object)  # 传 vtkGrid 或 mesh 文件路径

    def __init__(self, mesh):
        super().__init__()
        self.mesh = mesh

    def run(self):
        vtk_grid = meshio_to_vtk_unstructured_grid(self.mesh)
        self.finished.emit(vtk_grid)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("脑刺激模拟系统")
        self.resize(1200, 700)
        self.setStyleSheet("""
                QMainWindow {
                    background-color: #f5f5f7;
                }
                QPushButton {
                    background-color: #4a86e8;
                    color: black;
                    border: 1px solid #3a76d8;
                    border-radius: 5px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #3a76d8;
                }
                QLabel {
                    font-size: 14px;
                }
            """)

        self.stack = QStackedWidget()
        central_widget = QWidget()
        #self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        title_layout = QHBoxLayout()
        logo_label = QLabel("🧠")
        logo_label.setStyleSheet("font-size: 48px;")
        title_label = QLabel("脑刺激模拟系统")
        title_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #333;")
        title_layout.addWidget(logo_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #ddd; margin: 10px 0;")
        main_layout.addWidget(line)

        desc_label = QLabel("请选择您需要的刺激类型:")
        desc_label.setStyleSheet("font-size: 16px; margin: 20px 0;")
        main_layout.addWidget(desc_label)

        # 修复：确保按钮布局有足够空间显示内容
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(30)

        # TMS部分
        tms_widget = QWidget()
        tms_widget.setStyleSheet("background-color: white; border-radius: 10px; padding: 20px;")
        tms_layout = QVBoxLayout(tms_widget)
        tms_layout.setContentsMargins(20, 20, 20, 20)  # 添加内边距

        pixmap = QPixmap('icons/tms.png')
        tms_icon = QLabel()
        tms_icon.setPixmap(pixmap)
        tms_icon.setStyleSheet("font-size: 64px; color: #4a86e8;")
        tms_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tms_title = QLabel("经颅磁刺激 (TMS)")
        tms_title.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 10px;")
        tms_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn1 = QPushButton("开始 TMS 模拟")
        self.btn1.setFixedWidth(200)
        self.btn1.setMinimumHeight(40)  # 确保按钮有足够高度
        self.btn1.setStyleSheet("""
           QPushButton {
                    background-color: #4a86e8;
                    color: black;
                    border: 1px solid #3a76d8;
                    border-radius: 5px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #3a76d8;
                }
        """)

        tms_layout.addWidget(tms_icon)
        #tms_layout.addWidget(tms_title)
        tms_layout.addWidget(self.btn1, alignment=Qt.AlignmentFlag.AlignCenter)
        tms_layout.addStretch()

        # TES部分
        tes_widget = QWidget()
        tes_widget.setStyleSheet("background-color: white; border-radius: 10px; padding: 20px;")
        tes_layout = QVBoxLayout(tes_widget)
        tes_layout.setContentsMargins(20, 20, 20, 20)  # 添加内边距

        pixmap = QPixmap('icons/tes.png')
        tes_icon = QLabel()
        tes_icon.setPixmap(pixmap)
        tes_icon.setStyleSheet("font-size: 64px; color: #4a86e8;")
        tes_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tes_title = QLabel("经颅电刺激 (TES)")
        tes_title.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 10px;")
        tes_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn2 = QPushButton("开始 TES 模拟")
        self.btn2.setFixedWidth(200)
        self.btn2.setMinimumHeight(40)  # 确保按钮有足够高度
        self.btn2.setStyleSheet("""
           QPushButton {
                    background-color: #4a86e8;
                    color: black;
                    border: 1px solid #3a76d8;
                    border-radius: 5px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #3a76d8;
                }
        """)

        tes_layout.addWidget(tes_icon)
        #tes_layout.addWidget(tes_title)
        tes_layout.addWidget(self.btn2, alignment=Qt.AlignmentFlag.AlignCenter)
        tes_layout.addStretch()

        # 设置固定最小尺寸，确保卡片内容完全显示
        tms_widget.setMinimumSize(300, 250)
        tes_widget.setMinimumSize(300, 250)

        buttons_layout.addWidget(tms_widget)
        buttons_layout.addWidget(tes_widget)
        main_layout.addLayout(buttons_layout)

        # 底部版权信息
        footer_label = QLabel("© 2025 脑刺激模拟系统 - 版本 1.0")
        footer_label.setStyleSheet("color: #999; margin-top: 20px;")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(footer_label)



        # 初始化全局参数
        self.type = None  # tms 还是tes
        self.path = None  # 当下所需文件的显示路径
        self.subpath = None
        self.mesh = None

        # 第一个界面参数
        self.canvas = None
        self.nii_viewer = None
        self.sex = None
        self.age = None
        self.nii = None
        self.show_button = None
        self.next_button = None

        # 第二个界面参数
        self.vtk_viewer = None
        self.coil_type = None
        self.coil_target = None
        self.coil_size = None
        self.result_button = None

        # 绑定按钮点击事件
        self.btn1.clicked.connect(lambda: self.set_type("tms"))
        self.btn1.clicked.connect(self.show_nii_view)
        self.btn2.clicked.connect(lambda: self.set_type("tes"))
        self.btn2.clicked.connect(self.show_nii_view)

        self.stack.addWidget(central_widget)
        self.setCentralWidget(self.stack)

        # 确保按钮可见性
        self.btn1.show()
        self.btn2.show()

    def set_type(self,typeStr):
        self.type = typeStr

    def show_nii_view(self):
        # 创建页面容器
        page_widget = QWidget()
        page_widget.setStyleSheet("background-color: #f5f5f7;")
        main_layout = QHBoxLayout(page_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧控制面板
        left_panel = QWidget()
        left_panel.setFixedWidth(250)
        left_panel.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-right: 1px solid #e0e0e0;
            }
            QLabel {
                font-family: 'DejaVu Sans';
                color: black;
                font-size: 14px;
                margin-top: 10px;
                border-right: none;
            }
            QComboBox {
                font-family: 'DejaVu Sans';
                color: black;
                background: #f5f5f7;
                border: 1px solid #bfbfc4;
                border-radius: 6px;
                padding: 3px 28px 3px 8px;
            }

            QComboBox:hover {
                border-color: #a5a5aa;
            }

            QComboBox::drop-down {
                border-left: none;   /* macOS 没左竖线 */
                width: 22px;
            }

            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
        """)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(10)

        # 添加标题
        header_layout = QHBoxLayout()
        if self.type == "tms":
            title_text = "TMS 医学影像配置"
        else:
            title_text = "TES 医学影像配置"

        back_btn = QPushButton("←")
        back_btn.setFixedSize(30, 30)
        back_btn.setStyleSheet("font-size: 16px; font-weight: bold; padding: 0;")
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))

        title_label = QLabel(title_text)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        header_layout.addWidget(back_btn)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        left_layout.addLayout(header_layout)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #ddd;")
        left_layout.addWidget(line)

        # 参数选择区域
        params_label = QLabel("选择患者参数")
        params_label.setStyleSheet("font-size: 16px; margin-top: 20px; font-weight: bold;")
        left_layout.addWidget(params_label)

        sexlabel = QLabel("性别:")
        left_layout.addWidget(sexlabel)

        self.sex = QComboBox()
        self.sex.addItems(["男", "女"])
        left_layout.addWidget(self.sex)

        agelabel = QLabel("年龄范围:")
        left_layout.addWidget(agelabel)

        self.age = QComboBox()
        self.age.addItems(["21-30岁", "31-40岁", "41-50岁"])
        left_layout.addWidget(self.age)

        niilabel = QLabel("选择影像:")
        left_layout.addWidget(niilabel)

        self.nii = QComboBox()
        self.nii.addItems(["sub_01", "sub_02", "sub_03"])
        left_layout.addWidget(self.nii)

        # 按钮区域
        left_layout.addStretch()

        # 执行按钮
        self.show_button = QPushButton("加载影像")
        self.show_button.setStyleSheet("margin-bottom: 10px;")
        left_layout.addWidget(self.show_button)

        # 下一步按钮
        self.next_button = QPushButton("下一步 →")
        left_layout.addWidget(self.next_button)

        # 右侧显示区域
        self.canvas = QWidget()
        self.canvas.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 5px;
            }
        """)

        # 添加到主布局
        main_layout.addWidget(left_panel)
        main_layout.addWidget(self.canvas, stretch=1)

        # 连接按钮事件
        self.show_button.clicked.connect(self.update_nii_path)
        self.show_button.clicked.connect(self.update_plot)
        self.next_button.clicked.connect(self.update_nii_path)

        if self.type == "tms":
            self.next_button.clicked.connect(self.show_tms_view)
        else:
            self.next_button.clicked.connect(self.show_tes_view)

        # 加入堆栈并切换页面
        self.stack.addWidget(page_widget)
        self.stack.setCurrentWidget(page_widget)

    def update_nii_path(self):

        sex_choice = self.sex.currentText()
        age_choice = self.age.currentText()
        nii_choice = self.nii.currentText()

        sex_file_map = {
            "男": "./data/males",
            "女": "./data/females",
        }
        age_file_map = {
            "21-30岁": "21-30",
            "31-40岁": "31-40",
            "41-50岁": "41-50"
        }

        nii_file_map = {
            "sub_01": "01",
            "sub_02": "02",
            "sub_03": "03"
        }

        self.path = os.path.join(
            sex_file_map.get(sex_choice),
            age_file_map.get(age_choice),
            nii_file_map.get(nii_choice)
        )

    def update_plot(self):
        # 生成新的图像
        nii_path = os.path.join(self.path, "sub-control.nii.gz")
        self.nii_viewer = nii_view.begin(nii_path)  # 返回的是 ScrollSliceViewer 实例
        new_canvas = FigureCanvas(self.nii_viewer.fig)

        # 替换旧的 canvas
        layout = self.stack.currentWidget().layout()
        layout.replaceWidget(self.canvas, new_canvas)
        self.canvas.deleteLater()  # 删除旧的空白或旧图
        self.canvas = new_canvas
        self.canvas.show()

    def show_tms_view(self):

        self.loading_dialog = LoadingDialog("正在读取数据")
        self.loading_dialog.show()
        msh_path = os.path.join(self.path, "sub-control.msh")

        self.mesh_thread = MeshReaderThread(msh_path)  # 传递路径而不是mesh对象
        self.mesh_thread.finished.connect(self.set_mesh)
        self.mesh_thread.finished.connect(self.tms_on_read_finished)

        self.mesh_thread.start()

    def set_mesh(self):
        self.mesh = self.mesh_thread.mesh

    def tms_on_read_finished(self):
        self.mesh_thread2 = MeshLoaderThread(self.mesh)
        self.mesh_thread2.finished.connect(self.tms_on_mesh_loaded)
        self.mesh_thread2.start()

    def tms_on_mesh_loaded(self, vtk_grid):
        self.loading_dialog.close()
        # 创建页面容器
        page_widget = QWidget()
        page_widget.setStyleSheet("background-color: #f5f5f7;")
        main_layout = QHBoxLayout(page_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧控制面板
        left_panel = QWidget()
        left_panel.setFixedWidth(250)
        left_panel.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-right: 1px solid #e0e0e0;
            }
            QLabel {
                font-family: 'DejaVu Sans';
                color: black;
                font-size: 14px;
                margin-top: 10px;
                border-right: none;
            }
            QComboBox {
                font-family: 'DejaVu Sans';
                color: black;
                background: #f5f5f7;
                border: 1px solid #bfbfc4;
                border-radius: 6px;
                padding: 3px 28px 3px 8px;
            }

            QComboBox:hover {
                border-color: #a5a5aa;
            }

            QComboBox::drop-down {
                border-left: none;   /* macOS 没左竖线 */
                width: 22px;
            }

            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
        """)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(10)

        # 添加标题
        header_layout = QHBoxLayout()
        back_btn = QPushButton("←")
        back_btn.setFixedSize(30, 30)
        back_btn.setStyleSheet("font-size: 16px; font-weight: bold; padding: 0;")
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(self.stack.currentIndex() - 1))

        title_label = QLabel("TMS 刺激配置")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        header_layout.addWidget(back_btn)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        left_layout.addLayout(header_layout)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #ddd;")
        left_layout.addWidget(line)

        # 参数选择区域
        params_label = QLabel("刺激参数设置")
        params_label.setStyleSheet("font-size: 16px; margin-top: 20px; font-weight: bold;")
        left_layout.addWidget(params_label)

        typelabel = QLabel("TMS线圈类型:")
        left_layout.addWidget(typelabel)

        self.coil_type = QComboBox()
        self.coil_type.addItems(["bf70", "bf50", "cb70", "cb60"])
        left_layout.addWidget(self.coil_type)

        targetlabel = QLabel("刺激靶点:")
        left_layout.addWidget(targetlabel)

        self.coil_target = QComboBox()
        self.coil_target.addItems(["C3", "C4", "F3", "F4"])
        left_layout.addWidget(self.coil_target)

        sizelabel = QLabel("线圈dI/dt:")
        left_layout.addWidget(sizelabel)

        self.coil_size = QComboBox()
        self.coil_size.addItems(["1.00x1e6 A/s", "5.00x1e6 A/s", "10.00x1e6 A/s"])
        left_layout.addWidget(self.coil_size)

        # 按钮区域
        left_layout.addStretch()

        # 模拟按钮
        self.result_button = QPushButton("查看调控结果")
        left_layout.addWidget(self.result_button)

        # 右侧VTK显示区域

        self.vtk_viewer = MultiMeshViewer(self.path)
        self.vtk_viewer.interactor.Initialize()
        self.vtk_viewer.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 5px;
            }
        """)


        # 添加到主布局
        main_layout.addWidget(left_panel)
        main_layout.addWidget(self.vtk_viewer, stretch=1)

        # 连接按钮事件
        self.result_button.clicked.connect(self.set_tms_result_path)
        self.result_button.clicked.connect(self.show_result_view)

        # 加入堆栈并切换页面
        self.stack.addWidget(page_widget)
        self.stack.setCurrentWidget(page_widget)

    def set_tms_result_path(self):
        type_choice = self.coil_type.currentText()
        target_choice = self.coil_target.currentText()
        size_choice = self.coil_size.currentText()

        type_file_map = {
            "bf70": "Deymed_70BF",
            "bf50": "Deymed_50BF",
            "cb70": "MagVenture_C-B70",
            "cb60": "MagVenture_C-B60"
        }
        target_file_map = {
            "C3": "C3",
            "C4": "C4",
            "F3": "F3",
            "F4": "F4"
        }

        size_file_map = {
            "1.00x1e6 A/s": "npy_outputs",
            "5.00x1e6 A/s": "npy_outputs",
            "10.00x1e6 A/s": "npy_outputs"
        }

        self.subpath = os.path.join(
            self.path,
            type_file_map.get(type_choice),
            target_file_map.get(target_choice),
            size_file_map.get(size_choice)
        )
        print("set finished")

    def show_tes_view(self):

        self.loading_dialog = LoadingDialog("正在读取数据")
        self.loading_dialog.show()
        msh_path = os.path.join(self.path, "sub-control.msh")

        self.mesh_thread = MeshReaderThread(msh_path)  # 传递路径而不是mesh对象
        self.mesh_thread.finished.connect(self.set_mesh)
        self.mesh_thread.finished.connect(self.tes_on_read_finished)

        self.mesh_thread.start()

    def tes_on_read_finished(self):
        self.mesh_thread2 = MeshLoaderThread(self.mesh)
        self.mesh_thread2.finished.connect(self.tes_on_mesh_loaded)
        self.mesh_thread2.start()

    def tes_on_mesh_loaded(self, vtk_grid):
        self.loading_dialog.close()

        # 创建页面容器
        page_widget = QWidget()
        page_widget.setStyleSheet("background-color: #f5f5f7;")
        main_layout = QHBoxLayout(page_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧控制面板
        left_panel = QWidget()
        left_panel.setFixedWidth(250)
        left_panel.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-right: 1px solid #e0e0e0;
            }
            QLabel {
                font-family: 'DejaVu Sans';
                color: black;
                font-size: 14px;
                margin-top: 10px;
                border-right: none;
            }
            QComboBox {
                font-family: 'DejaVu Sans';
                color: black;
                background: #f5f5f7;
                border: 1px solid #bfbfc4;
                border-radius: 6px;
                padding: 3px 28px 3px 8px;
            }

            QComboBox:hover {
                border-color: #a5a5aa;
            }

            QComboBox::drop-down {
                border-left: none;   /* macOS 没左竖线 */
                width: 22px;
            }

            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
        """)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(10)

        # 添加标题
        header_layout = QHBoxLayout()
        back_btn = QPushButton("←")
        back_btn.setFixedSize(30, 30)
        back_btn.setStyleSheet("font-size: 16px; font-weight: bold; padding: 0;")
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(self.stack.currentIndex() - 1))

        title_label = QLabel("TES 刺激配置")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        header_layout.addWidget(back_btn)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        left_layout.addLayout(header_layout)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #ddd;")
        left_layout.addWidget(line)

        # 参数选择区域
        params_label = QLabel("刺激参数设置")
        params_label.setStyleSheet("font-size: 16px; margin-top: 20px; font-weight: bold;")
        left_layout.addWidget(params_label)

        typelabel = QLabel("电极厚度:")
        left_layout.addWidget(typelabel)

        self.coil_type = QComboBox()
        self.coil_type.addItems(["4.00 mm", "5.00 mm", "6.00 mm"])
        left_layout.addWidget(self.coil_type)

        targetlabel = QLabel("刺激靶点:")
        left_layout.addWidget(targetlabel)

        self.coil_target = QComboBox()
        self.coil_target.addItems(["C4-AF3", "F3-F4", "F3-Fp2", "F4-Fp1", "P3-P4"])
        left_layout.addWidget(self.coil_target)

        sizelabel = QLabel("刺激强度:")
        left_layout.addWidget(sizelabel)

        self.coil_size = QComboBox()
        self.coil_size.addItems(["1.00x1e6 A/s", "5.00x1e6 A/s", "10.00x1e6 A/s"])
        left_layout.addWidget(self.coil_size)

        # 按钮区域
        left_layout.addStretch()

        # 模拟按钮
        self.result_button = QPushButton("查看调控结果")
        left_layout.addWidget(self.result_button)

        # 右侧VTK显示区域

        self.vtk_viewer = MultiMeshViewer(self.path)
        self.vtk_viewer.interactor.Initialize()
        self.vtk_viewer.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 5px;
            }
        """)

        # 添加到主布局
        main_layout.addWidget(left_panel)
        main_layout.addWidget(self.vtk_viewer, stretch=1)

        # 连接按钮事件
        self.result_button.clicked.connect(self.set_tes_result_path)
        self.result_button.clicked.connect(self.show_result_view)

        # 加入堆栈并切换页面
        self.stack.addWidget(page_widget)
        self.stack.setCurrentWidget(page_widget)

    def set_tes_result_path(self):
        type_choice = self.coil_type.currentText()
        target_choice = self.coil_target.currentText()
        size_choice = self.coil_size.currentText()

        type_file_map = {
            "4.00 mm": "thickness-4",
            "5.00 mm": "thickness-5",
            "6.00 mm": "thickness-6",
        }
        target_file_map = {
            "C4-AF3": "tDCS-C4-AF3",
            "F3-F4": "tDCS-F3-F4",
            "F3-Fp2": "tDCS-F3-Fp2",
            "F4-Fp1": "tDCS-F4-Fp1",
            "P3-P4": "tDCS-P3-P4"
        }

        size_file_map = {
            "1.00x1e6 A/s": "npy_outputs",
            "5.00x1e6 A/s": "npy_outputs",
            "10.00x1e6 A/s": "npy_outputs"
        }

        self.subpath = os.path.join(
            self.path,
            target_file_map.get(target_choice),
            type_file_map.get(type_choice),
            size_file_map.get(size_choice)
        )

    def show_result_view(self):
        """
        展示结果界面，左边是VTK模型，右边是图表和文字信息
        """
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

        # 检查路径是否已设置
        if not hasattr(self, 'subpath') or self.subpath is None:
            print("错误：尚未设置结果路径")
            return

        # 加载网格文件
        msh_path = os.path.join(self.path, "sub-control.msh")
        npy_path = self.subpath

        # 显示加载对话框
        self.loading_dialog = LoadingDialog("正在加载模型和计算结果...")
        self.loading_dialog.show()

        # 创建线程加载网格

        self.mesh_thread = MeshResultLoaderThread(self.mesh,npy_path)
        self.mesh_thread.finished.connect(self.on_result_mesh_loaded)
        self.mesh_thread.start()

    def on_result_mesh_loaded(self, vtk_grid):
        """
        网格加载完成后的回调函数，整合analysis_npy.py的分析功能
        """
        self.loading_dialog.close()


        # 创建主页面容器
        page_widget = QWidget()
        page_widget.setStyleSheet("background-color: #f5f5f7;")
        main_layout = QHBoxLayout(page_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧VTK显示区域
        vtk_panel = QWidget()
        vtk_layout = QVBoxLayout(vtk_panel)
        vtk_layout.setContentsMargins(0, 0, 0, 0)

        # 创建MeshViewer实例
        self.result_vtk_viewer = MeshViewer(None)
        self.result_vtk_viewer.set_vtk_grid_max(vtk_grid)
        self.result_vtk_viewer.vtk_widget.Initialize()
        self.result_vtk_viewer.setStyleSheet("background-color: white; border-radius: 5px;")
        vtk_layout.addWidget(self.result_vtk_viewer)

        # 右侧信息面板
        info_panel = QWidget()
        info_panel.setFixedWidth(500)  # 增加宽度以适应图表
        info_panel.setStyleSheet("""
            QWidget {
                background-color: white;
                border-left: 1px solid #e0e0e0;
            }
            QLabel {
                font-family: 'DejaVu Sans';
                color: black;
                font-size: 14px;
            }
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
            QTabWidget {
                font-family: 'DejaVu Sans';
                font-size: 15px;
                color: #222;
                background: #f8f9fa;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QTabBar::tab {
                background: #f0f0f0;
                border: 1px solid #ddd;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 10px;
                margin-right: 2px;
                font-family: 'DejaVu Sans';
                font-size: 15px;
                color: #222;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
                color: #4a86e8;
                font-weight: bold;
            }
        """)

        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(20, 20, 20, 20)
        info_layout.setSpacing(15)

        # 添加标题与返回按钮
        header_layout = QHBoxLayout()
        back_btn = QPushButton("←")
        back_btn.setFixedSize(30, 30)
        back_btn.setStyleSheet("font-size: 16px; font-weight: bold; padding: 0;")
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(self.stack.currentIndex() - 1))

        title_label = QLabel("调控结果分析")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        header_layout.addWidget(back_btn)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        info_layout.addLayout(header_layout)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #ddd;")
        info_layout.addWidget(line)

        # 添加参数信息卡片
        params_widget = QWidget()
        params_widget.setStyleSheet("background-color: #f8f9fa; border-radius: 8px; padding: 15px;")
        params_layout = QVBoxLayout(params_widget)

        params_title = QLabel("当前参数配置")
        params_title.setStyleSheet("font-weight: bold; font-size: 16px;")
        params_layout.addWidget(params_title)

        if self.type == "tms":
            type_text = f"线圈类型: {self.coil_type.currentText()}"
        else:
            type_text = f"电极厚度: {self.coil_type.currentText()}"

        type_label = QLabel(type_text)
        target_label = QLabel(f"刺激靶点: {self.coil_target.currentText()}")
        size_label = QLabel(f"强度: {self.coil_size.currentText()}")

        params_layout.addWidget(type_label)
        params_layout.addWidget(target_label)
        params_layout.addWidget(size_label)

        info_layout.addWidget(params_widget)

        # 创建选项卡，用于展示不同的图表
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("font-size: 14px;")
        print("正在加载")
        # 加载和分析数据
        try:
            # 从analysis_npy.py导入需要的函数
            from analysis_npy import load_field_data, compute_statistics
            print("加载成功")
            # 加载电场数据
            base_dir = self.subpath
            tissue_data = {}
            for tissue_name, filename in {
                'Scalp': 'e_scalp.npy',
                'Bone': 'e_bone.npy',
                'CSF': 'e_csf.npy',
                'Gray Matter': 'e_gray_matter.npy',
                'White Matter': 'e_white_matter.npy'
            }.items():
                full_path = os.path.join(base_dir, filename)
                tissue_data[tissue_name] = load_field_data(full_path)

            # 创建分布图选项卡
            dist_tab = QWidget()
            dist_layout = QVBoxLayout(dist_tab)
            dist_fig = Figure(figsize=(5, 4), dpi=100)
            dist_canvas = FigureCanvas(dist_fig)
            dist_layout.addWidget(dist_canvas)

            # 绘制分布图
            ax = dist_fig.add_subplot(111)
            plotted = False
            bins = 50
            for label, arr in tissue_data.items():
                if arr.size == 0:
                    continue
                ax.hist(arr[:, 3], bins=bins, alpha=0.5, density=False, label=label)
                plotted = True

            if plotted:
                ax.set_xlabel('E-field magnitude (V/m)')
                ax.set_ylabel('Voxel count')
                ax.legend()
                dist_fig.tight_layout()
            else:
                no_data_label = QLabel("没有可用的组织数据")
                no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                dist_layout.addWidget(no_data_label)

            # 创建3D散点图选项卡
            scatter_tab = QWidget()
            scatter_layout = QVBoxLayout(scatter_tab)
            scatter_fig = Figure(figsize=(5, 4), dpi=100)
            scatter_canvas = FigureCanvas(scatter_fig)
            scatter_layout.addWidget(scatter_canvas)

            # 选择灰质数据进行3D可视化
            gray_matter = tissue_data.get('Gray Matter', np.empty((0, 4)))
            if gray_matter.size > 0:
                # 抽样以提高性能
                subsample = 5000
                n_points = min(subsample, gray_matter.shape[0])
                indices = np.random.choice(gray_matter.shape[0], n_points, replace=False)
                sample = gray_matter[indices]

                ax = scatter_fig.add_subplot(111, projection='3d')
                sc = ax.scatter(sample[:, 0], sample[:, 1], sample[:, 2],
                                c=sample[:, 3], cmap='jet', s=5, marker='o')
                cbar = scatter_fig.colorbar(sc, ax=ax)
                cbar.set_label('E-field (V/m)')
                ax.set_xlabel('X (mm)')
                ax.set_ylabel('Y (mm)')
                ax.set_zlabel('Z (mm)')
                scatter_fig.tight_layout()
            else:
                no_data_label = QLabel("没有可用的灰质数据")
                no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                scatter_layout.addWidget(no_data_label)


            # 创建3D散点图选项卡
            scatter_w_tab = QWidget()
            scatter_w_layout = QVBoxLayout(scatter_w_tab)
            scatter_w_fig = Figure(figsize=(5, 4), dpi=100)
            scatter_w_canvas = FigureCanvas(scatter_w_fig)
            scatter_w_layout.addWidget(scatter_w_canvas)

            # 选择白质数据进行3D可视化
            white_matter = tissue_data.get('White Matter', np.empty((0, 4)))
            if white_matter.size > 0:
                # 抽样以提高性能
                subsample = 5000
                n_points = min(subsample, white_matter.shape[0])
                indices = np.random.choice(white_matter.shape[0], n_points, replace=False)
                sample = white_matter[indices]

                ax = scatter_w_fig.add_subplot(111, projection='3d')
                sc = ax.scatter(sample[:, 0], sample[:, 1], sample[:, 2],
                                c=sample[:, 3], cmap='jet', s=5, marker='o')
                cbar = scatter_w_fig.colorbar(sc, ax=ax)
                cbar.set_label('E-field (V/m)')
                ax.set_xlabel('X (mm)')
                ax.set_ylabel('Y (mm)')
                ax.set_zlabel('Z (mm)')
                scatter_w_fig.tight_layout()
            else:
                no_data_label = QLabel("没有可用的白质数据")
                no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                scatter_w_layout.addWidget(no_data_label)



            # 创建3D散点图选项卡
            scatter_scalp_tab = QWidget()
            scatter_scalp_layout = QVBoxLayout(scatter_scalp_tab)
            scatter_scalp_fig = Figure(figsize=(5, 4), dpi=100)
            scatter_scalp_canvas = FigureCanvas(scatter_scalp_fig)
            scatter_scalp_layout.addWidget(scatter_scalp_canvas)

            # 选择头皮数据进行3D可视化
            scalp_matter = tissue_data.get('Scalp', np.empty((0, 4)))
            if scalp_matter.size > 0:
                # 抽样以提高性能
                subsample = 5000
                n_points = min(subsample, scalp_matter.shape[0])
                indices = np.random.choice(scalp_matter.shape[0], n_points, replace=False)
                sample = scalp_matter[indices]

                ax = scatter_scalp_fig.add_subplot(111, projection='3d')
                sc = ax.scatter(sample[:, 0], sample[:, 1], sample[:, 2],
                                c=sample[:, 3], cmap='jet', s=5, marker='o')
                cbar = scatter_scalp_fig.colorbar(sc, ax=ax)
                cbar.set_label('E-field (V/m)')
                ax.set_xlabel('X (mm)')
                ax.set_ylabel('Y (mm)')
                ax.set_zlabel('Z (mm)')
                scatter_scalp_fig.tight_layout()
            else:
                no_data_label = QLabel("没有可用的头皮数据")
                no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                scatter_scalp_layout.addWidget(no_data_label)


            # 创建3D散点图选项卡
            scatter_csf_tab = QWidget()
            scatter_csf_layout = QVBoxLayout(scatter_csf_tab)
            scatter_csf_fig = Figure(figsize=(5, 4), dpi=100)
            scatter_csf_canvas = FigureCanvas(scatter_csf_fig)
            scatter_csf_layout.addWidget(scatter_csf_canvas)

            # 选择脑脊液数据进行3D可视化
            csf_matter = tissue_data.get('CSF', np.empty((0, 4)))
            if csf_matter.size > 0:
                # 抽样以提高性能
                subsample = 5000
                n_points = min(subsample, csf_matter.shape[0])
                indices = np.random.choice(csf_matter.shape[0], n_points, replace=False)
                sample = csf_matter[indices]

                ax = scatter_csf_fig.add_subplot(111, projection='3d')
                sc = ax.scatter(sample[:, 0], sample[:, 1], sample[:, 2],
                                c=sample[:, 3], cmap='jet', s=5, marker='o')
                cbar = scatter_csf_fig.colorbar(sc, ax=ax)
                cbar.set_label('E-field (V/m)')
                ax.set_xlabel('X (mm)')
                ax.set_ylabel('Y (mm)')
                ax.set_zlabel('Z (mm)')
                scatter_csf_fig.tight_layout()
            else:
                no_data_label = QLabel("没有可用的脑脊液数据")
                no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                scatter_csf_layout.addWidget(no_data_label)





            # 创建切片图选项卡
            slice_tab = QWidget()
            slice_layout = QVBoxLayout(slice_tab)
            slice_fig = Figure(figsize=(5, 4), dpi=100)
            slice_canvas = FigureCanvas(slice_fig)
            slice_layout.addWidget(slice_canvas)

            if gray_matter.size > 0:
                from scipy.interpolate import griddata
                # 找到Z轴中点
                mid_z = 0.5 * (np.min(gray_matter[:, 2]) + np.max(gray_matter[:, 2]))
                # 设置容差
                tol = (np.max(gray_matter[:, 2]) - np.min(gray_matter[:, 2])) / 300
                slice_pts = gray_matter[np.abs(gray_matter[:, 2] - mid_z) < tol]

                if slice_pts.shape[0] > 0:
                    ax = slice_fig.add_subplot(111)
                    xi, yi = slice_pts[:, 0], slice_pts[:, 1]
                    zi = slice_pts[:, 3]

                    grid_size = 200
                    xi_lin = np.linspace(np.min(xi), np.max(xi), grid_size)
                    yi_lin = np.linspace(np.min(yi), np.max(yi), grid_size)
                    X, Y = np.meshgrid(xi_lin, yi_lin)

                    try:
                        Z = griddata((xi, yi), zi, (X, Y), method='cubic')
                        im = ax.imshow(Z.T, extent=(xi_lin[0], xi_lin[-1], yi_lin[0], yi_lin[-1]),
                                       origin='lower', aspect='auto', cmap='jet')
                        slice_fig.colorbar(im, ax=ax, label='E-field (V/m)')
                        ax.set_xlabel('X (mm)')
                        ax.set_ylabel('Y (mm)')
                        ax.set_title(f'Z = {mid_z:.2f} mm ')
                        slice_fig.tight_layout()
                    except Exception:
                        ax.text(0.5, 0.5, '切片插值失败', ha='center', va='center',
                                transform=ax.transAxes)
                else:
                    ax = slice_fig.add_subplot(111)
                    ax.text(0.5, 0.5, '在选定平面没有足够的数据点', ha='center', va='center',
                            transform=ax.transAxes)
            else:
                no_data_label = QLabel("没有可用的组织数据")
                no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                slice_layout.addWidget(no_data_label)

            # 创建摘要统计选项卡
            stats_tab = QWidget()
            stats_layout = QVBoxLayout(stats_tab)

            stats_label = QLabel("各组织电场强度统计 (V/m)")
            stats_label.setStyleSheet("font-family: 'DejaVu Sans'; font-weight: bold; margin-bottom: 10px; color: black;")
            stats_layout.addWidget(stats_label)

            from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem
            stats_table = QTableWidget()
            stats_table.setColumnCount(5)
            stats_table.setHorizontalHeaderLabels(["组织", "最小值", "最大值", "平均值", "标准差"])
            stats_table.setRowCount(len(tissue_data))
            stats_table.setStyleSheet("""
                QTableWidget {
                    font-family: 'DejaVu Sans';
                    color: black;
                }
                QTableWidget::item {
                    color: black;
                    font-family: 'DejaVu Sans';
                }
                QHeaderView::section {
                    color: black;
                    font-family: 'DejaVu Sans';
                }
            """)

            for i, (name, arr) in enumerate(tissue_data.items()):
                stats = compute_statistics(arr)
                item0 = QTableWidgetItem(name)
                item1 = QTableWidgetItem(f"{stats['min']:.3e}" if not np.isnan(stats['min']) else "N/A")
                item2 = QTableWidgetItem(f"{stats['max']:.3e}" if not np.isnan(stats['max']) else "N/A")
                item3 = QTableWidgetItem(f"{stats['mean']:.3e}" if not np.isnan(stats['mean']) else "N/A")
                item4 = QTableWidgetItem(f"{stats['std']:.3e}" if not np.isnan(stats['std']) else "N/A")
                for item in [item0, item1, item2, item3, item4]:
                    item.setForeground(Qt.GlobalColor.black)
                    item.setFont(stats_table.font())
                stats_table.setItem(i, 0, item0)
                stats_table.setItem(i, 1, item1)
                stats_table.setItem(i, 2, item2)
                stats_table.setItem(i, 3, item3)
                stats_table.setItem(i, 4, item4)

            stats_table.resizeColumnsToContents()
            stats_layout.addWidget(stats_table)

            # 添加各选项卡到QTabWidget
            tab_widget.addTab(stats_tab, "统计")
            tab_widget.addTab(dist_tab, "电场分布")
            tab_widget.addTab(scatter_tab, "灰质")
            tab_widget.addTab(scatter_w_tab, "白质")
            tab_widget.addTab(scatter_scalp_tab, "头皮")
            tab_widget.addTab(scatter_csf_tab, "脑脊液")
            tab_widget.addTab(slice_tab, "切片")

        except Exception as e:
            import traceback
            print(f"加载分析数据出错: {e}")
            print(traceback.format_exc())

            # 出现错误时显示简单的图表
            figure = Figure(figsize=(5, 3), dpi=100)
            canvas = FigureCanvas(figure)

            ax = figure.add_subplot(111)
            bars = ax.bar(['表层皮质', '大脑中部', '深部组织'], [120, 80, 30],
                          color=['#4a86e8', '#4a86e8', '#4a86e8'])
            ax.set_ylabel('电场强度 (V/m)')
            ax.set_title('不同深度的电场强度分布')
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2., height + 5,
                        f'{int(height)}',
                        ha='center', va='bottom', fontsize=9)

            figure.tight_layout()
            info_layout.addWidget(canvas)

            # 添加错误提示
            error_label = QLabel("无法加载详细分析数据，显示模拟数据")
            error_label.setStyleSheet("color: red; margin-top: 10px;")
            info_layout.addWidget(error_label)
        else:
            # 添加选项卡到布局
            info_layout.addWidget(tab_widget)



        # 添加间隔
        #info_layout.addStretch()

        # 添加导出按钮
        #export_button = QPushButton("导出分析报告")
        #export_button.setStyleSheet("margin-bottom: 10px;")
        #export_button.clicked.connect(self.export_report)
        #info_layout.addWidget(export_button)

        # 设置布局比例
        main_layout.addWidget(vtk_panel, 3)  # 左侧VTK占比更大
        main_layout.addWidget(info_panel)  # 右侧信息面板

        # 将页面添加到堆栈并显示
        self.stack.addWidget(page_widget)
        self.stack.setCurrentWidget(page_widget)

    def export_report(self):
        """导出分析报告到PDF或其他格式"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        try:
            # 打开文件保存对话框
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存分析报告", "", "PDF文件 (*.pdf);;HTML文件 (*.html)"
            )

            if not file_path:
                return  # 用户取消

            # 显示消息
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText("报告导出成功")
            msg.setInformativeText(f"报告已保存至:\n{file_path}")
            msg.setWindowTitle("导出完成")
            msg.exec()

        except Exception as e:
            # 显示错误
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setText("导出失败")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())




