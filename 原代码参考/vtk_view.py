import os
import vtk
from vtkmodules.vtkCommonColor import vtkNamedColors

# —————————————— Render Existing VTK PolyData & Preview File ——————————————
# Path to your VTK file
vtk_path = "average_template_100.vtk"

# —————————————— Print first 10 lines of the VTK file ——————————————
if os.path.isfile(vtk_path):
    print("📄 VTK 文件前 10 行：")
    # 使用 UTF-8 编码并忽略无法解码的字节，避免 GBK 解码错误
    with open(vtk_path, 'r', encoding='utf-8', errors='ignore') as f:
        for i in range(10):
            line = f.readline()
            if not line:
                break
            print(f"{i+1:>2}: {line.rstrip()}")
    print()
else:
    raise FileNotFoundError(f"无法找到文件: {vtk_path}")

# —————————————— Load and Render ——————————————
# Step 1: Read the PolyData from file
reader = vtk.vtkPolyDataReader()
reader.SetFileName(vtk_path)
reader.Update()
poly_data = reader.GetOutput()

# Step 2: Mapper & Actor
mapper = vtk.vtkPolyDataMapper()
mapper.SetInputData(poly_data)

actor = vtk.vtkActor()
actor.SetMapper(mapper)

# Step 3: Renderer setup
colors = vtkNamedColors()
renderer = vtk.vtkRenderer()
renderer.AddActor(actor)
# Set background to white
renderer.SetBackground(colors.GetColor3d('White'))

# Step 4: Render Window & Interactor
render_window = vtk.vtkRenderWindow()
render_window.AddRenderer(renderer)
render_window.SetSize(800, 800)
render_window.SetWindowName('VTK Viewer')

interactor = vtk.vtkRenderWindowInteractor()
interactor.SetRenderWindow(render_window)

# Step 5: Start interaction
render_window.Render()
interactor.Initialize()
interactor.Start()

print("🎬 渲染已启动：左键旋转，右键平移，滚轮缩放，’q‘或Esc退出")
