#!/usr/bin/env python3
"""检查 _scan_source_directory 的缩进位置"""
with open(r"D:\临时\batch_manage_gui.py", "r", encoding="utf-8") as f:
    content = f.read()

# 找到 _scan_source_directory 的位置
idx = content.find("def _scan_source_directory(self):")
if idx == -1:
    print("ERROR: 找不到 _scan_source_directory")
else:
    # 看前面的缩进
    start = content.rfind("\n", 0, idx)
    indent_start = idx - content.rfind("\n", 0, idx)
    line_before = content[start:idx]
    print(f"前一行到函数名的内容: {repr(line_before)}")
    
    # 找最近的 class 定义
    class_idx = content.rfind("class BatchManageGUI", 0, idx)
    print(f"最近 class 在位置 {class_idx}")
    
    # 判断是否缩进正确
    if class_idx > 0:
        lines_between = content[class_idx + len("class BatchManageGUI") : idx]
        last_line = lines_between.strip().split("\n")[-1] if lines_between.strip() else ""
        print(f"class 和函数之间的最后一行: {repr(last_line)}")
        
        # 如果中间只有 def，说明函数可能不在类内
        has_def = "def " in lines_between[lines_between.rfind("def ", -len(lines_between)):] if len(lines_between) < 200 else ""
        print(f"中间有 def: {has_def}")
