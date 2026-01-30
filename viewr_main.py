import os
import tkinter as tk
from tkinter import ttk
import pydicom
import numpy as np
from PIL import Image, ImageTk

class DICOMViewerApp:
  def __init__(self, root):
    self.root = root
    self.root.title("DICOM Viewer Pro (Ver.1)")

    # --- データ管理変数 ---
    current_dir = os.getcwd()
    self.dicom_folder = os.path.join(
        current_dir, "DICOM_Folder")

    self.slices = []
    self.pixel_array = None
    self.aspect_ratio = 1.0

    # 現在の座標
    self.cur_z = 0
    self.cur_y = 0
    self.cur_x = 0

    # 初期値保持用
    self.init_z = 0
    self.init_y = 0
    self.init_x = 0
    self.init_wl = 40
    self.init_ww = 400

    # 表示設定
    self.wl = self.init_wl
    self.ww = self.init_ww
    self.view_mode = "Coronal"
    self.show_crosshair = True

    # ズーム・パン管理
    self.view_params = {
        "axial": {"scale": 1.0, "offset_x": 0, "offset_y": 0},
        "sub": {"scale": 1.0, "offset_x": 0, "offset_y": 0}
    }

    self.drag_start = {"x": 0, "y": 0}

    # --- GUI構築 ---
    self.setup_ui()

    # 起動時に読み込み
    self.load_dicom_series(self.dicom_folder)

  def setup_ui(self):
    self.notebook = ttk.Notebook(self.root)
    self.notebook.pack(fill=tk.BOTH, expand=True)

    # Tab 1: Viewer
    self.tab_viewer = tk.Frame(self.notebook)
    self.notebook.add(self.tab_viewer, text="Viewer")
    self.setup_viewer_tab(self.tab_viewer)

    # Tab 2: Metadata
    self.tab_metadata = tk.Frame(self.notebook)
    self.notebook.add(self.tab_metadata, text="Full Metadata")
    self.setup_metadata_tab(self.tab_metadata)

  def setup_viewer_tab(self, parent):
    paned = tk.PanedWindow(parent, orient=tk.HORIZONTAL)
    paned.pack(fill=tk.BOTH, expand=True)

    # === 左側: 画像エリア ===
    self.view_frame = tk.Frame(paned, bg="#333")  # 背景を少し暗く
    paned.add(self.view_frame, minsize=600)

    self.view_frame.columnconfigure(0, weight=1)
    self.view_frame.columnconfigure(1, weight=1)
    self.view_frame.rowconfigure(0, weight=1)

    # --- Axial Frame ---
    self.frame_axial = tk.Frame(self.view_frame, bg="black")
    self.frame_axial.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

    header_axial = tk.Frame(self.frame_axial, bg="black")
    header_axial.pack(fill=tk.X, padx=2, pady=2)
    tk.Label(header_axial, text="Axial (Z-Axis)", fg="#8888ff",
             bg="black", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
    tk.Button(header_axial, text="Reset View", font=("Arial", 7),
              command=lambda: self.reset_single_view("axial")).pack(side=tk.RIGHT)

    self.canvas_axial = tk.Canvas(self.frame_axial, bg="black")
    self.canvas_axial.pack(fill=tk.BOTH, expand=True)

    # --- Sub View Frame ---
    self.frame_sub = tk.Frame(self.view_frame, bg="black")
    self.frame_sub.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)

    header_sub = tk.Frame(self.frame_sub, bg="black")
    header_sub.pack(fill=tk.X, padx=2, pady=2)
    self.label_sub = tk.Label(header_sub, text="Coronal (Y-Axis)",
                              fg="#88ff88", bg="black", font=("Arial", 10, "bold"))
    self.label_sub.pack(side=tk.LEFT)
    tk.Button(header_sub, text="Reset View", font=("Arial", 7),
              command=lambda: self.reset_single_view("sub")).pack(side=tk.RIGHT)

    self.canvas_sub = tk.Canvas(self.frame_sub, bg="black")
    self.canvas_sub.pack(fill=tk.BOTH, expand=True)

    # イベントバインド
    for cv, name in [(self.canvas_axial, "axial"), (self.canvas_sub, "sub")]:
      cv.bind("<Control-MouseWheel>", lambda e,
              n=name: self.on_mouse_wheel(e, n))
      cv.bind("<Control-Button-4>", lambda e,
              n=name: self.on_mouse_wheel(e, n, 120))
      cv.bind("<Control-Button-5>", lambda e,
              n=name: self.on_mouse_wheel(e, n, -120))
      cv.bind("<ButtonPress-1>", lambda e,
              n=name: self.on_drag_start(e, n))
      cv.bind("<B1-Motion>", lambda e, n=name: self.on_drag_motion(e, n))

    # === 右側: コントロールパネル ===
    control_panel = tk.Frame(paned, width=380)
    paned.add(control_panel, minsize=380)

    # 1. Info
    info_frame = tk.LabelFrame(control_panel, text="Basic Info")
    info_frame.pack(fill=tk.X, padx=5, pady=5)
    self.txt_info = tk.Text(info_frame, height=10,
                            width=40, font=("Consolas", 9))
    self.txt_info.pack(padx=5, pady=5, fill=tk.BOTH)

    # 2. Controls
    op_frame = tk.LabelFrame(control_panel, text="Controls")
    op_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    tk.Button(op_frame, text="Switch Sagittal <-> Coronal",
              command=self.toggle_view).pack(fill=tk.X, pady=5)

    self.btn_crosshair = tk.Button(op_frame, text="Hide Crosshair" if self.show_crosshair else "Show Crosshair",
                                   command=self.toggle_crosshair, bg="#ddd")
    self.btn_crosshair.pack(fill=tk.X, pady=5)

    # Slider Helper
    def create_control_group(parent_frame, label_text, slider_cmd, reset_cmd, from_, to_, fg_color="black"):
      frame = tk.Frame(parent_frame)
      frame.pack(fill=tk.X, pady=5)
      top_row = tk.Frame(frame)
      top_row.pack(fill=tk.X)
      tk.Label(top_row, text=label_text, width=18, anchor="w",
               fg=fg_color, font=("Arial", 9, "bold")).pack(side=tk.LEFT)

      entry_var = tk.StringVar()
      entry = tk.Entry(top_row, textvariable=entry_var, width=8)
      entry.pack(side=tk.LEFT, padx=5)
      entry.bind("<Return>", lambda e: slider_cmd(entry_var.get()))

      tk.Button(top_row, text="Reset", command=reset_cmd,
                font=("Arial", 8)).pack(side=tk.LEFT, padx=5)

      slider = tk.Scale(frame, from_=from_, to=to_, orient=tk.HORIZONTAL,
                        command=lambda v: self.sync_entry_from_slider(v, entry_var, slider_cmd))
      slider.pack(fill=tk.X)
      return slider, entry_var

    # Sliders (軸色に合わせてラベルも色付け)
    # Z軸 = Blue
    self.slider_z, self.var_z = create_control_group(
        op_frame, "Axial Slice (Z):", self.on_z_change_req, self.reset_z, 0, 100, fg_color="blue")

    frame_sub = tk.Frame(op_frame)
    frame_sub.pack(fill=tk.X, pady=5)
    top_sub = tk.Frame(frame_sub)
    top_sub.pack(fill=tk.X)
    # Y軸=Green, X軸=Red
    self.label_slider_sub = tk.Label(
        top_sub, text="Coronal Slice (Y):", width=18, anchor="w", fg="green", font=("Arial", 9, "bold"))
    self.label_slider_sub.pack(side=tk.LEFT)
    self.var_sub = tk.StringVar()
    entry_sub = tk.Entry(top_sub, textvariable=self.var_sub, width=8)
    entry_sub.pack(side=tk.LEFT, padx=5)
    entry_sub.bind(
        "<Return>", lambda e: self.on_sub_change_req(self.var_sub.get()))
    tk.Button(top_sub, text="Reset", command=self.reset_sub,
              font=("Arial", 8)).pack(side=tk.LEFT, padx=5)
    self.slider_sub = tk.Scale(frame_sub, from_=0, to=100, orient=tk.HORIZONTAL,
                               command=lambda v: self.sync_entry_from_slider(v, self.var_sub, self.on_sub_change_req))
    self.slider_sub.pack(fill=tk.X)

    self.slider_wl, self.var_wl = create_control_group(
        op_frame, "Window Level (WL):", self.on_wl_change_req, self.reset_wl, -1000, 3000)
    self.slider_ww, self.var_ww = create_control_group(
        op_frame, "Window Width (WW):", self.on_ww_change_req, self.reset_ww, 1, 5000)

    tk.Button(op_frame, text="Reset Zoom/Pan All",
              command=self.reset_zoom_all).pack(pady=10)

  def setup_metadata_tab(self, parent):
    columns = ("Tag", "Name", "VR", "Value")
    self.tree = ttk.Treeview(parent, columns=columns, show="headings")
    self.tree.heading("Tag", text="Tag ID")
    self.tree.heading("Name", text="Description")
    self.tree.heading("VR", text="VR")
    self.tree.heading("Value", text="Value")
    self.tree.column("Tag", width=100)
    self.tree.column("Name", width=200)
    self.tree.column("VR", width=50)
    self.tree.column("Value", width=300)

    v_scroll = ttk.Scrollbar(
        parent, orient=tk.VERTICAL, command=self.tree.yview)
    h_scroll = ttk.Scrollbar(
        parent, orient=tk.HORIZONTAL, command=self.tree.xview)
    self.tree.configure(yscrollcommand=v_scroll.set,
                        xscrollcommand=h_scroll.set)
    v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
    self.tree.pack(fill=tk.BOTH, expand=True)

  def sync_entry_from_slider(self, val, str_var, command_func):
    try:
      f_val = float(val)
      if f_val.is_integer(): str_var.set(str(int(f_val)))
      else: str_var.set(str(f_val))
      command_func(val, from_slider=True)
    except: pass

  def load_dicom_series(self, folder_path):
    if not os.path.exists(folder_path):
      self.txt_info.delete(1.0, tk.END); self.txt_info.insert(tk.END, "Folder not found."); return
    files = [os.path.join(folder_path, f)
             for f in os.listdir(folder_path) if f.endswith('.dcm')]
    if not files:
      self.txt_info.delete(1.0, tk.END); self.txt_info.insert(tk.END, "No DICOM files."); return

    try:
      self.slices = [pydicom.dcmread(f) for f in files]
      self.slices.sort(key=lambda x: float(x.ImagePositionPatient[2]))
    except Exception as e:
      self.txt_info.delete(1.0, tk.END); self.txt_info.insert(tk.END, f"Error: {e}"); return

    img_shape = self.slices[0].pixel_array.shape
    self.pixel_array = np.zeros(
        (len(self.slices), img_shape[0], img_shape[1]), dtype=np.float32)

    for i, s in enumerate(self.slices):
      slope = getattr(s, 'RescaleSlope', 1)
      intercept = getattr(s, 'RescaleIntercept', 0)
      self.pixel_array[i, :, :] = s.pixel_array * slope + intercept

    try:
      thick = float(self.slices[0].SliceThickness)
      spacing = float(self.slices[0].PixelSpacing[0])
      self.aspect_ratio = thick / spacing
    except: self.aspect_ratio = 1.0

    self.z_dim, self.y_dim, self.x_dim = self.pixel_array.shape
    self.init_z = self.z_dim // 2
    self.init_y = self.y_dim // 2
    self.init_x = self.x_dim // 2

    if 'WindowCenter' in self.slices[0]:
      wc = self.slices[0].WindowCenter
      self.init_wl = float(wc) if isinstance(
          wc, (float, int, str)) else float(wc[0])
    else: self.init_wl = 40
    if 'WindowWidth' in self.slices[0]:
      ww = self.slices[0].WindowWidth
      self.init_ww = float(ww) if isinstance(
          ww, (float, int, str)) else float(ww[0])
    else: self.init_ww = 400

    self.cur_z, self.cur_y, self.cur_x = self.init_z, self.init_y, self.init_x
    self.wl, self.ww = self.init_wl, self.init_ww

    self.slider_z.config(to=self.z_dim - 1)
    self.update_sub_slider_range()
    min_val, max_val = float(np.min(self.pixel_array)), float(
        np.max(self.pixel_array))
    self.slider_wl.config(from_=min_val, to=max_val)

    self.display_dicom_info()
    self.reset_z(); self.reset_sub(); self.reset_wl(
    ); self.reset_ww(); self.reset_zoom_all()
    self.update_metadata_list(self.slices[0])
    self.update_views()

  def display_dicom_info(self):
    if not self.slices: return
    ds = self.slices[0]
    def get_tag(tag, default="N/A"): return str(getattr(ds,
                                                        tag, default)).replace('^', ' ')
    info_text = f"Size     : {ds.Columns} x {ds.Rows}\n"
    info_text += f"Slices   : {len(self.slices)}\n"
    info_text += f"Thickness: {get_tag('SliceThickness')} mm\n"
    info_text += f"Spacing  : {ds.PixelSpacing[0]:.3f} mm\n"
    info_text += "-" * 25 + "\n"
    info_text += f"Name     : {get_tag('PatientName')}\n"
    info_text += f"ID       : {get_tag('PatientID')}\n"
    info_text += f"Modality : {get_tag('Modality')}\n"
    info_text += f"Date     : {get_tag('StudyDate')}\n"
    self.txt_info.delete(1.0, tk.END); self.txt_info.insert(
        tk.END, info_text)

  def update_metadata_list(self, dataset):
    for item in self.tree.get_children(): self.tree.delete(item)
    for elem in dataset.iterall():
      tag_str = f"{elem.tag.group:04X},{elem.tag.element:04X}"
      val = str(elem.value)
      if len(val) > 100: val = val[:100] + "..."
      self.tree.insert("", tk.END, values=(
          tag_str, elem.name, elem.VR, val))

  def toggle_view(self):
    if self.view_mode == "Coronal":
      self.view_mode = "Sagittal"
      self.label_sub.config(text="Sagittal (X-Axis)", fg="red")
      self.label_slider_sub.config(text="Sagittal Slice (X):", fg="red")
    else:
      self.view_mode = "Coronal"
      self.label_sub.config(text="Coronal (Y-Axis)", fg="green")
      self.label_slider_sub.config(text="Coronal Slice (Y):", fg="green")
    self.update_sub_slider_range()
    self.reset_sub()
    self.reset_zoom_all()
    self.update_views()

  def toggle_crosshair(self):
    self.show_crosshair = not self.show_crosshair
    self.btn_crosshair.config(
        text="Hide Crosshair" if self.show_crosshair else "Show Crosshair")
    self.update_views()

  def update_sub_slider_range(self):
    if self.pixel_array is None: return
    if self.view_mode == "Coronal": self.slider_sub.config(
        to=self.y_dim - 1)
    else: self.slider_sub.config(to=self.x_dim - 1)

  # --- Handlers ---
  def on_z_change_req(self, val, from_slider=False):
    try:
      v = max(0, min(int(float(val)), self.z_dim - 1))
      self.cur_z = v
      if not from_slider: self.slider_z.set(v)
      self.var_z.set(str(v))
      self.update_views()
    except: pass

  def on_sub_change_req(self, val, from_slider=False):
    try:
      limit = (self.y_dim if self.view_mode ==
               "Coronal" else self.x_dim) - 1
      v = max(0, min(int(float(val)), limit))
      if self.view_mode == "Coronal": self.cur_y = v
      else: self.cur_x = v
      if not from_slider: self.slider_sub.set(v)
      self.var_sub.set(str(v))
      self.update_views()
    except: pass

  def on_wl_change_req(self, val, from_slider=False):
    try:
      v = float(val); self.wl = v;
      if not from_slider: self.slider_wl.set(v)
      self.var_wl.set(str(int(v))); self.update_views()
    except: pass

  def on_ww_change_req(self, val, from_slider=False):
    try:
      v = float(val); v = 1 if v < 1 else v; self.ww = v
      if not from_slider: self.slider_ww.set(v)
      self.var_ww.set(str(int(v))); self.update_views()
    except: pass

  def reset_z(self): self.on_z_change_req(self.init_z)
  def reset_sub(self): self.on_sub_change_req(
      self.init_y if self.view_mode == "Coronal" else self.init_x)

  def reset_wl(self): self.on_wl_change_req(self.init_wl)
  def reset_ww(self): self.on_ww_change_req(self.init_ww)

  # --- Zoom & Pan ---
  def reset_zoom_all(self):
    self.view_params = {"axial": {"scale": 1.0, "offset_x": 0.0, "offset_y": 0.0},
                        "sub": {"scale": 1.0, "offset_x": 0.0, "offset_y": 0.0}}
    self.update_views()

  def reset_single_view(self, view_name):
    self.view_params[view_name] = {
        "scale": 1.0, "offset_x": 0.0, "offset_y": 0.0}
    self.update_views()

  def on_drag_start(self, event, view_name): self.drag_start = {
      "x": event.x, "y": event.y}

  def on_drag_motion(self, event, view_name):
    dx, dy = event.x - self.drag_start["x"], event.y - self.drag_start["y"]
    self.view_params[view_name]["offset_x"] += dx
    self.view_params[view_name]["offset_y"] += dy
    self.drag_start = {"x": event.x, "y": event.y}
    self.update_views()

  def on_mouse_wheel(self, event, view_name, delta=None):
    if delta is None: delta = event.delta
    scale_factor = 1.1 if delta > 0 else 0.9
    params = self.view_params[view_name]
    old_scale, new_scale = params["scale"], params["scale"] * scale_factor
    if new_scale < 0.3: new_scale = 0.3
    if new_scale > 1.7: new_scale = 1.7

    canvas = self.canvas_axial if view_name == "axial" else self.canvas_sub
    cw, ch = canvas.winfo_width(), canvas.winfo_height()
    params["offset_x"] = event.x - \
        (event.x - params["offset_x"] - (cw / 2)) * \
        (new_scale / old_scale) - (cw / 2)
    params["offset_y"] = event.y - \
        (event.y - params["offset_y"] - (ch / 2)) * \
        (new_scale / old_scale) - (ch / 2)
    params["scale"] = new_scale
    self.update_views()

  def apply_window(self, img_array):
    lower, upper = self.wl - (self.ww / 2), self.wl + (self.ww / 2)
    img = np.clip(img_array, lower, upper)
    if upper == lower: upper += 1
    img = (img - lower) / (upper - lower) * 255
    return img.astype(np.uint8)

  def draw_image_on_canvas(self, pil_image, canvas, view_name, crosshair=None, v_col="cyan", h_col="cyan", is_anamorphic=False):
    params = self.view_params[view_name]
    canvas_w, canvas_h = canvas.winfo_width(), canvas.winfo_height()
    if canvas_w <= 1: canvas_w, canvas_h = 400, 400

    orig_w, orig_h = pil_image.size
    aspect_mult = self.aspect_ratio if is_anamorphic else 1.0
    base_scale = min(canvas_w / orig_w, canvas_h / (orig_h * aspect_mult))
    final_scale = base_scale * params["scale"]

    new_w, new_h = int(orig_w * final_scale), int(orig_h *
                                                  aspect_mult * final_scale)
    img_resized = pil_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
    if is_anamorphic: img_resized = img_resized.transpose(
        Image.Transpose.FLIP_TOP_BOTTOM)

    tk_img = ImageTk.PhotoImage(img_resized)
    cx, cy = (canvas_w // 2) + \
        params["offset_x"], (canvas_h // 2) + params["offset_y"]

    canvas.delete("all")
    canvas.create_image(cx, cy, anchor=tk.CENTER, image=tk_img)

    # Draw Crosshair with specific colors
    if self.show_crosshair and crosshair:
      val_x, val_y = crosshair
      # Vertical Line
      if val_x is not None:
        offset_x = (val_x - orig_w / 2) * final_scale
        line_x = cx + offset_x
        canvas.create_line(line_x, 0, line_x, canvas_h,
                           fill=v_col, dash=(4, 4), width=1)

      # Horizontal Line
      if val_y is not None:
        if is_anamorphic:
          offset_y = ((orig_h - 1 - val_y) - orig_h / 2) * \
              final_scale * aspect_mult
        else:
          offset_y = (val_y - orig_h / 2) * final_scale * aspect_mult
        line_y = cy + offset_y
        canvas.create_line(0, line_y, canvas_w, line_y,
                           fill=h_col, dash=(4, 4), width=1)

    return tk_img

  def update_views(self):
    if self.pixel_array is None: return

    # --- Axial (Z fixed) ---
    # 縦軸=Sagittal(X-Red), 横軸=Coronal(Y-Green)
    axial_data = self.pixel_array[self.cur_z, :, :]
    axial_img = Image.fromarray(self.apply_window(axial_data))
    self.tk_axial = self.draw_image_on_canvas(axial_img, self.canvas_axial, "axial",
                                              crosshair=(
                                                  self.cur_x, self.cur_y),
                                              v_col="red", h_col="green", is_anamorphic=False)

    # --- Sub View ---
    if self.view_mode == "Coronal":
      # Coronal (Y fixed): 縦軸=Sagittal(X-Red), 横軸=Axial(Z-Blue)
      sub_data = self.pixel_array[:, self.cur_y, :]
      sub_img = Image.fromarray(self.apply_window(sub_data))
      self.tk_sub = self.draw_image_on_canvas(sub_img, self.canvas_sub, "sub",
                                              crosshair=(
                                                  self.cur_x, self.cur_z),
                                              v_col="red", h_col="blue", is_anamorphic=True)
    else:
      # Sagittal (X fixed): 縦軸=Coronal(Y-Green), 横軸=Axial(Z-Blue)
      sub_data = self.pixel_array[:, :, self.cur_x]
      sub_img = Image.fromarray(self.apply_window(sub_data))
      self.tk_sub = self.draw_image_on_canvas(sub_img, self.canvas_sub, "sub",
                                              crosshair=(
                                                  self.cur_y, self.cur_z),
                                              v_col="green", h_col="blue", is_anamorphic=True)

if __name__ == "__main__":
  root = tk.Tk()
  root.geometry("1100x700")
  app = DICOMViewerApp(root)
  root.mainloop()
