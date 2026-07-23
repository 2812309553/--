#!/usr/bin/env python3
import sys, importlib.util
sys.path.insert(0, r"D:\临时")
spec = importlib.util.spec_from_file_location("bg", r"D:\临时\batch_manage_gui.py")
bg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bg)
methods = [m for m in dir(bg.BatchManageGUI) if not m.startswith("__")]
print("BatchManageGUI 方法:")
for m in sorted(methods):
    print(f"  {m}")
has_scan = hasattr(bg.BatchManageGUI, "_scan_source_directory")
has_click = hasattr(bg.BatchManageGUI, "_on_ext_tag_click")
has_drop = hasattr(bg.BatchManageGUI, "_on_drop_source")
print()
print(f"Has _scan_source_directory: {has_scan}")
print(f"Has _on_ext_tag_click: {has_click}")
print(f"Has _on_drop_source: {has_drop}")
