#!/usr/bin/env python3
"""
批量文件管理工具

功能：
  1. 自定义后缀名（可多个，如 .snrj,.mp4）
  2. 目标后缀名（可选）
  3. 操作目录
  4. 目标目录

模式：
  - 3个参数（无目标后缀名）：仅按自定义后缀移动文件，不改编号、不改后缀
  - 4个参数（有目标后缀名）：先全局升序编号重命名 → 移动 → 改后缀
"""

import os
import sys
import shutil
from pathlib import Path


# ── 输入处理 ──────────────────────────────────────────────

def input_custom_exts():
    """输入自定义后缀名，逗号分隔，支持带/不带点"""
    raw = input("请输入自定义后缀名（逗号分隔，例如 .snrj,.mp4）：").strip()
    if not raw:
        print("错误：自定义后缀名不能为空")
        sys.exit(1)
    exts = []
    for e in raw.split(","):
        e = e.strip()
        if not e.startswith("."):
            e = "." + e
        exts.append(e.lower())
    return exts


def input_target_ext():
    """输入目标后缀名（可选）"""
    raw = input("请输入目标后缀名（直接回车表示不修改后缀）：").strip()
    if not raw:
        return None
    if not raw.startswith("."):
        raw = "." + raw
    return raw.lower()


def input_dir(prompt):
    """输入目录路径并校验"""
    while True:
        d = input(prompt).strip().strip('"').strip("'")
        if not d:
            print("错误：目录不能为空")
            continue
        p = Path(d)
        if not p.exists():
            print(f"提示：目录 '{d}' 不存在，将自动创建")
            break
        if not p.is_dir():
            print(f"错误：'{d}' 不是目录")
            continue
        break
    return d


# ── 核心逻辑 ──────────────────────────────────────────────

def find_files(directory, exts):
    """递归查找 directory 下所有扩展名在 exts 中的文件"""
    matched = []
    root = Path(directory)
    for f in root.rglob("*"):
        if f.is_file() and f.suffix.lower() in exts:
            matched.append(f)
    return sorted(matched, key=lambda x: str(x))


def rename_with_sequence(directory):
    """
    对 directory 下所有文件做升序编号重命名
    格式：{序号}{原扩展名}，序号从1开始，步长1，补零到统一宽度
    例如：001.snrj, 002.snrj, ..., 010.mp4
    """
    root = Path(directory)
    all_files = sorted(root.rglob("*"), key=lambda x: str(x))
    files_only = [f for f in all_files if f.is_file()]

    if not files_only:
        print("  没有找到文件需要重命名")
        return {}

    # 确定补零宽度
    width = len(str(len(files_only)))

    # 记录旧路径 -> 新路径的映射
    rename_map = {}

    for idx, old_path in enumerate(files_only, start=1):
        new_name = f"{idx:0{width}}" + old_path.suffix
        new_path = old_path.parent / new_name

        if old_path == new_path:
            continue

        if new_path.exists():
            continue

        try:
            old_path.rename(new_path)
            rename_map[str(old_path)] = str(new_path)
            print(f"  [{idx:0{width}}] {old_path.name} -> {new_name}")
        except Exception as e:
            print(f"  重命名失败 {old_path.name}: {e}")

    return rename_map


def move_files(source_dir, dest_dir, exts):
    """
    将 source_dir 中符合 exts 的文件移动到 dest_dir
    返回移动的文件列表
    """
    src = Path(source_dir)
    dst = Path(dest_dir)
    dst.mkdir(parents=True, exist_ok=True)

    matched = find_files(source_dir, exts)

    if not matched:
        print(f"  在 '{source_dir}' 中没有找到扩展名为 {exts} 的文件")
        return []

    moved = []
    for f in matched:
        dest_file = dst / f.name
        # 如果目标文件已存在，加序号避免覆盖
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
            print(f"  移动: {f.name} -> {dest_file.name}")
        except Exception as e:
            print(f"  移动失败 {f.name}: {e}")

    return moved


def change_extension(directory, old_exts, new_ext):
    """
    将 directory 下所有扩展名在 old_exts 中的文件改为 new_ext
    """
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
                    print(f"  改后缀: {f.name} -> {new_name}")
                except Exception as e:
                    print(f"  改后缀失败 {f.name}: {e}")

    print(f"\n  共修改了 {changed} 个文件的后缀名")
    return changed


# ── 主流程 ────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("       批量文件管理工具")
    print("=" * 60)
    print()

    # 1. 输入自定义后缀名
    custom_exts = input_custom_exts()
    print(f"  自定义后缀名: {', '.join(custom_exts)}")
    print()

    # 2. 输入目标后缀名（可选）
    target_ext = input_target_ext()
    if target_ext:
        print(f"  目标后缀名: {target_ext}")
        mode = "编号+移动+改后缀"
    else:
        print("  目标后缀名: (不修改)")
        mode = "仅移动"
    print()

    # 3. 输入操作目录
    source_dir = input_dir("请输入需要操作的目录：")
    print()

    # 4. 输入目标目录
    dest_dir = input_dir("请输入要移动到的目录：")
    print()

    print("-" * 60)
    print(f"  模式: {mode}")
    print(f"  源目录: {source_dir}")
    print(f"  目标目录: {dest_dir}")
    print("-" * 60)
    print()

    # 确认
    confirm = input("确认执行？(y/n)：").strip().lower()
    if confirm != "y":
        print("已取消")
        return

    print()

    if mode == "仅移动":
        # 纯移动模式
        print("[步骤1/1] 移动文件...")
        moved = move_files(source_dir, dest_dir, custom_exts)
        print(f"\n完成！共移动 {len(moved)} 个文件到 '{dest_dir}'")

    else:
        # 编号 + 移动 + 改后缀模式
        # 步骤1: 升序编号重命名
        print("[步骤1/3] 升序编号重命名...")
        rename_with_sequence(source_dir)
        print()

        # 步骤2: 移动文件
        print("[步骤2/3] 移动文件...")
        moved = move_files(source_dir, dest_dir, custom_exts)
        print()

        # 步骤3: 改后缀名
        print("[步骤3/3] 修改后缀名...")
        change_extension(dest_dir, custom_exts, target_ext)
        print()

        print(f"完成！共移动 {len(moved)} 个文件到 '{dest_dir}'")

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
