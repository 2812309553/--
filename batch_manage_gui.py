#!/usr/bin/env python3
"""
批量文件管理工具 - GUI 版本
基于 tkinter，支持三种模式：
  1. 仅移动：目标后缀名不填，移动目录必填
  2. 仅改后缀：目标后缀名必填，移动目录不填
  3. 编号 + 移动 + 改后缀：两者都填
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import shutil
import json
import re
from pathlib import Path


# ============================================================
# 核心逻辑（与 batch_manage.py 保持一致）
# ============================================================

def find_files(directory, exts):
    matched = []
    root = Path(directory)
    for f in root.rglob("*"):
        if f.is_file() and f.suffix.lower() in exts:
            matched.append(f)
    return sorted(matched, key=lambda x: str(x))


def rename_matched_files(directory, exts):
    matched = find_files(directory, exts)
    if not matched:
        return []
    width = len(str(len(matched)))
    renamed = []
    for idx, old_path in enumerate(matched, start=1):
        new_name = f"{idx:0{width}}" + old_path.suffix
        new_path = old_path.parent / new_name
        if old_path == new_path or new_path.exists():
            continue
        try:
            old_path.rename(new_path)
            renamed.append((str(old_path), str(new_path)))
        except Exception:
            pass
    return renamed


def move_files(source_dir, dest_dir, exts):
    dst = Path(dest_dir)
    dst.mkdir(parents=True, exist_ok=True)
    matched = find_files(source_dir, exts)
    moved = []
    for f in matched:
        dest_file = dst / f.name
        if dest_file.exists():
            stem = f.stem
            suffix = f.suffix
            counter = 1
            while dest_file.exists():
                dest_file = dst / f"{stem}_{counter}{suffix}"
                counter += 1
        try:
            shutil.move(str(f), str(dest_file))
            moved.append(dest_file)
        except Exception:
            pass
    return moved


def change_extension(directory, old_exts, new_ext):
    root = Path(directory)
    changed = 0
    for f in root.rglob("*"):
        if f.is_file() and f.suffix.lower() in old_exts:
            new_name = f.stem + new_ext
            new_path = f.parent / new_name
            if f != new_path:
                try:
                    f.rename(new_path)
                    changed += 1
                except Exception:
                    pass
    return changed


# ============================================================
# 带占位符的 Entry 控件
# ============================================================

class PlaceholderEntry(ttk.Entry):
    """
    带浅灰色占位符文本的 Entry。
    - 获得焦点时隐藏占位符
    - 失去焦点且内容为空时恢复占位符
    - 用户输入了内容后不再显示占位符
    """

    def __init__(self, master, placeholder, **kwargs):
        super().__init__(master, **kwargs)
        self._placeholder = placeholder
        self._is_placeholder = True
        self._show_placeholder()
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Return>", self._on_enter)
        self.bind("<Tab>", self._on_tab)

    def _show_placeholder(self):
        self._is_placeholder = True
        self.config(foreground="#999")
        self.delete(0, tk.END)
        self.insert(0, self._placeholder)

    def _hide_placeholder(self):
        self._is_placeholder = False
        self.config(foreground="")
        self.delete(0, tk.END)

    def _on_focus_in(self, event):
        if self._is_placeholder:
            self._hide_placeholder()

    def _on_focus_out(self, event):
        if self.get().strip() == "":
            self._show_placeholder()

    def _on_enter(self, event):
        if self._is_placeholder or self.get().strip() == "":
            self._fill_placeholder()
        if hasattr(self, "_submit_cb") and self._submit_cb:
            self._submit_cb()

    def _on_tab(self, event):
        self._on_enter(event)

    def get_real_value(self):
        if self._is_placeholder:
            return ""
        return self.get()

    def set_value(self, value):
        if self._is_placeholder:
            self._hide_placeholder()
        self.delete(0, tk.END)
        if value:
            self.insert(0, value)

    def _fill_placeholder(self):
        self._is_placeholder = False
        self.config(foreground="")
        self.delete(0, tk.END)
        self.insert(0, self._placeholder)


# ============================================================
# 支持拖拽的 Entry
# ============================================================

class DroppableEntry(PlaceholderEntry):
    """支持拖拽文件夹的 Entry"""

    def __init__(self, master, placeholder, **kwargs):
        super().__init__(master, placeholder, **kwargs)
        try:
            self.drop_target_register(tk.DND_FILES)
            self.drag_bind("<Drop>", self._on_drop)
        except Exception:
            pass

    def _on_drop(self, event):
        paths = event.data
        if not paths:
            return
        matches = re.findall(r"{(.*?)}", paths)
        if matches:
            path = matches[0]
            p = Path(path)
            if p.is_dir():
                if self._is_placeholder:
                    self._hide_placeholder()
                self.delete(0, tk.END)
                self.insert(0, path)


# ============================================================
# 历史记录
# ============================================================

HISTORY_FILE = Path(__file__).parent / ".batch_manage_history.json"


# ============================================================
# 主 GUI
# ============================================================

class BatchManageGUI:
    DEFAULT_CUSTOM_EXTS = ".snrj,.mp4"
    DEFAULT_TARGET_EXT = ".zip"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("批量文件管理工具")
        self.root.geometry("560x440")
        self.root.resizable(False, False)
        self.root.configure(bg="#f5f5f5")

        self.history = {
           "custom_exts": "",
           "target_ext": "",
           "source_dir": "",
           "dest_dir": "",
            "do_rename": False,
       }

        self._build_ui()
        self._load_history()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=24)
        main.pack(fill=tk.BOTH, expand=True)

        # 标题
        ttk.Label(
            main,
            text="批量文件管理工具",
            font=("Microsoft YaHei", 16, "bold"),
            background="#f5f5f5",
        ).grid(row=0, column=0, columnspan=3, pady=(0, 18), sticky="w")

        # 1. 自定义后缀名
        ttk.Label(
            main, text="自定义后缀名:", background="#f5f5f5", font=("Microsoft YaHei", 10)
        ).grid(row=1, column=0, sticky="w", pady=5)
        self.entry_custom_exts = PlaceholderEntry(
            main, placeholder=self.DEFAULT_CUSTOM_EXTS, width=45
        )
        self.entry_custom_exts.grid(row=1, column=1, columnspan=2, pady=5, padx=(6, 0))
        self.entry_custom_exts._submit_cb = self._on_field_submit

        # 2. 目标后缀名
        ttk.Label(
            main, text="目标后缀名:", background="#f5f5f5", font=("Microsoft YaHei", 10)
        ).grid(row=2, column=0, sticky="w", pady=5)
        self.entry_target_ext = PlaceholderEntry(
            main, placeholder=self.DEFAULT_TARGET_EXT, width=45
        )
        self.entry_target_ext.grid(row=2, column=1, columnspan=2, pady=5, padx=(6, 0))
        self.entry_target_ext._submit_cb = self._on_field_submit

        # 3. 需要操作的目录
        ttk.Label(
            main, text="需要操作的目录:", background="#f5f5f5", font=("Microsoft YaHei", 10)
        ).grid(row=3, column=0, sticky="w", pady=5)
        frame_src = ttk.Frame(main)
        frame_src.grid(row=3, column=1, columnspan=2, pady=5, padx=(6, 0), sticky="ew")
        frame_src.columnconfigure(0, weight=1)

        self.entry_source_dir = DroppableEntry(
            frame_src, placeholder="", width=38
        )
        self.entry_source_dir.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_src = tk.Button(
            frame_src,
            text="\U0001F4C1",
            font=("Segoe UI Emoji", 12),
            bg="#e0e0e0",
            bd=1,
            relief=tk.RAISED,
            command=lambda: self._browse_dir(self.entry_source_dir),
            width=3,
        )
        btn_src.pack(side=tk.RIGHT, padx=(4, 0))

        # 4. 移动到的目录
        # 后缀统计标签区域（移至移动到的目录之前）
        self.ext_tags_frame = ttk.Frame(main)
        self.ext_tags_frame.grid(row=4, column=0, columnspan=3, pady=(6, 2), sticky="w")

        ttk.Label(
            main, text="移动到的目录:", background="#f5f5f5", font=("Microsoft YaHei", 10)
        ).grid(row=5, column=0, sticky="w", pady=5)
        frame_dst = ttk.Frame(main)
        frame_dst.grid(row=5, column=1, columnspan=2, pady=5, padx=(6, 0), sticky="ew")
        frame_dst.columnconfigure(0, weight=1)

        self.entry_dest_dir = DroppableEntry(
            frame_dst, placeholder="", width=38
        )
        self.entry_dest_dir.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_dst = tk.Button(
            frame_dst,
            text="\U0001F4C1",
            font=("Segoe UI Emoji", 12),
            bg="#e0e0e0",
            bd=1,
            relief=tk.RAISED,
            command=lambda: self._browse_dir(self.entry_dest_dir),
            width=3,
        )
        btn_dst.pack(side=tk.RIGHT, padx=(4, 0))

        # 模式提示
        # 编号复选框
        self.var_do_rename = tk.BooleanVar(value=False)
        ctrl_row = ttk.Frame(main)
        ctrl_row.grid(row=6, column=0, columnspan=3, pady=(2, 4), sticky="w")

        ttk.Checkbutton(
            ctrl_row,
            text="是否编号重命名",
            variable=self.var_do_rename,
            command=lambda: self._update_mode_hint(),
        ).pack(side=tk.LEFT)

        self.label_mode = ttk.Label(
            ctrl_row,
            text="模式：仅移动",
            background="#f5f5f5",
            foreground="#888",
            font=("Microsoft YaHei", 9),
        )
        self.label_mode.pack(side=tk.LEFT, padx=(15, 0))

        # 日志区
        log_box = ttk.LabelFrame(main, text="操作日志", padding=6)
        log_box.grid(row=7, column=0, columnspan=3, sticky="ew", pady=6)
        main.columnconfigure(1, weight=1)

        self.text_log = tk.Text(log_box, height=7, width=60, wrap=tk.WORD, font=("Consolas", 9))
        self.text_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(log_box, command=self.text_log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_log.config(yscrollcommand=scrollbar.set)

        # 按钮区
        btn_row = ttk.Frame(main)
        btn_row.grid(row=9, column=0, columnspan=3, pady=(4, 0))

        self.btn_execute = ttk.Button(
            btn_row, text="执 行", width=12, command=self._execute
        )
        self.btn_execute.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(btn_row, text="清除日志", width=10, command=self._clear_log).pack(side=tk.LEFT)

        # 绑定输入变化以更新模式提示
        for entry in [self.entry_custom_exts, self.entry_target_ext,
                      self.entry_source_dir, self.entry_dest_dir]:
            entry.bind("<KeyRelease>", lambda e: self._update_mode_hint())

        # 源目录变更时触发后缀统计（点击浏览按钮或手动输入后失去焦点时）
        self.entry_source_dir.bind("<FocusOut>", lambda e: self._on_focus_out_source())

    def _on_field_submit(self):
        pass

    def _on_focus_out_source(self):
        """焦点离开源目录输入框时触发后缀统计"""
        raw = self.entry_source_dir.get_real_value()
        if raw.strip():
            self._scan_source_directory()

    def _update_mode_hint(self):
        target = self.entry_target_ext.get_real_value().strip()
        dest = self.entry_dest_dir.get_real_value().strip()
        if target and dest:
            self.label_mode.config(text="模式：移动 + 改后缀", foreground="#2e7d32")
        elif target and not dest:
            self.label_mode.config(text="模式：仅改后缀", foreground="#e65100")
        elif dest:
            self.label_mode.config(text="模式：仅移动", foreground="#888")
        else:
            self.label_mode.config(text="模式：仅移动", foreground="#888")

    def _browse_dir(self, entry_widget):
        dir_path = filedialog.askdirectory(title="选择目录")
        if dir_path and entry_widget:
            entry_widget.set_value(dir_path)
            self._update_mode_hint()
            # 如果是源目录输入框，触发后缀统计
            if entry_widget is self.entry_source_dir:
                self._scan_source_directory()

    def _log(self, msg):
        self.text_log.insert(tk.END, msg + "\n")
        self.text_log.see(tk.END)

    def _clear_log(self):
        self.text_log.delete(1.0, tk.END)

    def _parse_custom_exts(self, raw):
        raw = raw.strip()
        if not raw:
            return None
        exts = []
        for e in raw.split(","):
            e = e.strip()
            if e:
                if not e.startswith("."):
                    e = "." + e
                exts.append(e.lower())
        return exts if exts else None

    def _parse_target_ext(self, raw):
        raw = raw.strip()
        if not raw:
            return None
        if not raw.startswith("."):
            raw = "." + raw
        return raw.lower()

    def _execute(self):
        custom_raw = self.entry_custom_exts.get_real_value()
        target_raw = self.entry_target_ext.get_real_value()
        source_raw = self.entry_source_dir.get_real_value()
        dest_raw = self.entry_dest_dir.get_real_value()

        custom_exts = self._parse_custom_exts(custom_raw)
        if not custom_exts:
            messagebox.showerror("错误", "自定义后缀名不能为空")
            return

        source_dir = source_raw.strip().strip('"').strip("'")
        if not source_dir:
            messagebox.showerror("错误", "需要操作的目录不能为空")
            return
        if not Path(source_dir).exists():
            messagebox.showerror("错误", f"目录不存在：{source_dir}")
            return

        target_ext = self._parse_target_ext(target_raw) if target_raw.strip() else None
        dest_dir = dest_raw.strip().strip('"').strip("'") if dest_raw.strip() else ""

        if dest_dir and not Path(dest_dir).exists():
            messagebox.showerror("错误", f"目标目录不存在：{dest_dir}")
            return

        # 复选框控制是否编号
        do_rename = self.var_do_rename.get()
        steps = []
        if dest_dir:
            steps.append("移动")
        if target_ext:
            steps.append("改后缀")

        if not steps:
            messagebox.showinfo("提示", "未选择任何操作，请至少填写目标目录或目标后缀名")
            self.btn_execute.config(state=tk.NORMAL)
            return

        mode_parts = []
        if do_rename:
            mode_parts.append("编号")
        mode_parts.extend(steps)
        mode_label = " + ".join(mode_parts)

        self.btn_execute.config(state=tk.DISABLED)
        self._clear_log()
        self._log(f"模式：{mode_label}")
        self._log(f"源目录：{source_dir}")
        exts_str = ", ".join(custom_exts)
        self._log(f"自定义后缀：{exts_str}")
        if target_ext:
            self._log(f"目标后缀：{target_ext}")
        if dest_dir:
            self._log(f"目标目录：{dest_dir}")
        step_count = len(steps)
        if do_rename:
            step_count += 1
        self._log("-" * 40)

        try:
            step_idx = 0
            if do_rename:
                step_idx += 1
                self._log(f"步骤 {step_idx}/{step_count}: 升序编号重命名...")
                renamed = rename_matched_files(source_dir, custom_exts)
                self._log(f"  重命名了 {len(renamed)} 个文件")

            for step_name in steps:
                step_idx += 1
                if step_name == "移动":
                    self._log(f"步骤 {step_idx}/{step_count}: 移动文件...")
                    moved = move_files(source_dir, dest_dir, custom_exts)
                    self._log(f"  移动了 {len(moved)} 个文件")
                elif step_name == "改后缀":
                    self._log(f"步骤 {step_idx}/{step_count}: 修改后缀名...")
                    target_dir = dest_dir if dest_dir else source_dir
                    changed = change_extension(target_dir, custom_exts, target_ext)
                    self._log(f"  修改了 {changed} 个文件的后缀")

            self._log("-" * 40)
            self._log("全部操作完成！")

            # 保存历史
            self.history["custom_exts"] = self.entry_custom_exts.get_real_value() if self.entry_custom_exts.get_real_value() else ""
            self.history["target_ext"] = self.entry_target_ext.get_real_value() if self.entry_target_ext.get_real_value() else ""
            self.history["source_dir"] = self.entry_source_dir.get()
            self.history["dest_dir"] = self.entry_dest_dir.get()
            self.history["do_rename"] = do_rename
            self._save_history()

            self.root.after(0, self._show_complete_dialog)

        except Exception as e:
            self._log(f"错误：{e}")
            messagebox.showerror("错误", str(e))
        finally:
            self.root.after(0, lambda: self.btn_execute.config(state=tk.NORMAL))

    def _show_complete_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("操作完成")
        dialog.geometry("320x180")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#f5f5f5")

        ttk.Label(
            dialog, text="操作完成！",
            font=("Microsoft YaHei", 14, "bold"),
            background="#f5f5f5",
        ).pack(pady=(20, 10))

        ttk.Label(
            dialog, text="文件已成功处理",
            background="#f5f5f5", font=("Microsoft YaHei", 10),
        ).pack()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=(15, 0))

        def on_continue():
            dialog.destroy()
            self._fill_from_history()

        def on_close():
            dialog.destroy()
            self.root.quit()

        ttk.Button(btn_frame, text="继 续", width=10, command=on_continue).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="关闭程序", width=10, command=on_close).pack(side=tk.LEFT, padx=10)

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

    def _fill_from_history(self):
        for key, entry in [
            ("custom_exts", self.entry_custom_exts),
            ("target_ext", self.entry_target_ext),
            ("source_dir", self.entry_source_dir),
            ("dest_dir", self.entry_dest_dir),
        ]:
            val = self.history.get(key, None)
            if val is not None and val != "":
                entry.set_value(val)
        # 回填编号复选框状态
        do_rename_val = self.history.get("do_rename", False)
        self.var_do_rename.set(do_rename_val)

    def _save_history(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_history(self):
        if not HISTORY_FILE.exists():
            return
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                self.history.update(loaded)
            self._fill_from_history()
        except Exception:
            pass


    def _on_drop_source(self, event):
        """处理拖拽到源目录输入框"""
        paths = getattr(event, "data", None)
        if paths is None:
            return
        import re
        matches = re.findall(r"{(.*?)}", paths)
        if matches:
            path = matches[0]
            p = Path(path)
            if p.is_dir():
                if self.entry_source_dir._is_placeholder:
                    self.entry_source_dir._hide_placeholder()
                self.entry_source_dir.delete(0, tk.END)
                self.entry_source_dir.insert(0, path)
                self._scan_source_directory()

    def _scan_source_directory(self):
        """扫描源目录，显示后缀名统计标签"""
        source_raw = self.entry_source_dir.get_real_value()
        source_dir = source_raw.strip().strip('"').strip("'")

        # 清除旧标签
        for widget in self.ext_tags_frame.winfo_children():
            widget.destroy()

        if not source_dir:
            return

        src_path = Path(source_dir)
        if not src_path.exists():
            return

        # 统计后缀名
        ext_counts = {}
        for f in src_path.rglob("*"):
            if f.is_file() and f.suffix.lower():
                ext = f.suffix.lower()
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

        if not ext_counts:
            return

        # 按文件名排序
        sorted_exts = sorted(ext_counts.items(), key=lambda x: x[0])

        for ext, count in sorted_exts:
            label_text = f"{ext}_{count}"
            tag_btn = tk.Button(
                self.ext_tags_frame,
                text=label_text,
                font=("Microsoft YaHei", 9),
                bg="#e0f0ff",
                fg="#0066cc",
                bd=1,
                relief=tk.RAISED,
                cursor="hand2",
                command=lambda e=ext: self._on_ext_tag_click(e),
            )
            tag_btn.pack(side=tk.LEFT, padx=(0, 6), pady=2)

    def _on_ext_tag_click(self, ext):
        """点击后缀统计标签，追加到自定义后缀名"""
        current = self.entry_custom_exts.get_real_value()
        current_stripped = current.strip()

        # 检查是否已存在
        existing_exts = [e.strip().lstrip(".") for e in current_stripped.split(",") if e.strip()]
        clean_ext = ext.lstrip(".")
        if clean_ext in existing_exts:
            return

        if current_stripped:
            new_value = current_stripped + "," + ext
        else:
            new_value = ext

        # 如果当前是占位符状态，先隐藏
        if self.entry_custom_exts._is_placeholder:
            self.entry_custom_exts._hide_placeholder()

        self.entry_custom_exts.delete(0, tk.END)
        self.entry_custom_exts.insert(0, new_value)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = BatchManageGUI()
    app.run()
