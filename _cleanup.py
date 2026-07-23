#!/usr/bin/env python3
import os
files = [
    "_full_test.py",
    "_restore_gui.py",
    "_insert_methods.py",
    "_add_ext_tags.py",
    "_fix_indent.py",
    "_check_cls.py",
    "_check_indent2.py",
    "_check_indent3.py",
    "_patch_rename.py",
]
for f in files:
    p = os.path.join(r"D:\临时", f)
    if os.path.exists(p):
        os.remove(p)
        print(f"已删除: {f}")
print("清理完成")
