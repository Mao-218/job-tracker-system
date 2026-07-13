# ============================
# File: display.py
# 终端 Unicode 表格渲染模块
# 纯 stdlib 实现，无需 prettytable
# ============================

import shutil
from models import DISPLAY_COL_WIDTHS, FIELD_NAMES, STATUS_LIST

# Unicode 制表符（用于绘制表格边框）
_H = "\u2500"   # ─
_V = "\u2502"   # │
_TL = "\u250c"  # ┌
_TR = "\u2510"  # ┐
_BL = "\u2514"  # └
_BR = "\u2518"  # ┘
_TM = "\u252c"  # ┬
_ML = "\u251c"  # ├
_MR = "\u2524"  # ┤
_BM = "\u2534"  # ┴
_MM = "\u253c"  # ┼


def visible_len(s):
    """计算字符串在终端中的实际显示宽度（中文字符算2格）"""
    count = 0
    for ch in s:
        if ord(ch) > 127:
            count += 2
        else:
            count += 1
    return count


def pad_cn(text, width):
    """按显示宽度左对齐填充空格"""
    pad = width - visible_len(text)
    if pad < 0:
        pad = 0
    return text + " " * pad


def fmt_cell(text, width):
    """
    按指定宽度截断或原样返回单格文本
    超出宽度的末尾用 … 替代
    """
    if width <= 0:
        if visible_len(text) > 40:
            return text[:20] + ".."
        return text
    if visible_len(text) > width:
        out = ""
        for ch in text:
            nv = visible_len(out + ch)
            if nv > width - 1:
                out += "\u2026"   # 省略号 …
                break
            out += ch
        return pad_cn(out, width)
    return pad_cn(text, width)


def _border_line(widths, left, mid, right):
    """构建表格边框横线（带连接符）"""
    parts = [left]
    for i, w in enumerate(widths):
        parts.append(_H * (w + 2))
        parts.append(mid if i < len(widths) - 1 else right)
    return "".join(parts)


def _data_row(cells, widths):
    """构建表格数据行"""
    parts = [_V]
    for i, cell in enumerate(cells):
        parts.append(" " + cell + " ")
        parts.append(_V)
    return "".join(parts)


def print_table(records, fields=None, title=None):
    """
    打印格式化表格

    参数:
        records: list[dict]  — 每条记录对应一个字典
        fields:  要显示的字段列表，默认全部 13 个字段
        title:   可选的表格标题
    """
    if not records:
        print()
        print("  │ (暂无数据) │")
        print()
        return

    if fields is None:
        fields = FIELD_NAMES

    # 筛选有宽度配置的字段
    widths = []
    show_fields = []
    for f in fields:
        w = DISPLAY_COL_WIDTHS.get(f, 20)
        widths.append(w)
        show_fields.append(f)

    if not show_fields:
        return

    # 准备数据行
    rows = []
    for rec in records:
        row = []
        for f in show_fields:
            val = str(rec.get(f, ""))
            row.append(fmt_cell(val, DISPLAY_COL_WIDTHS.get(f, 20)))
        rows.append(row)

    # 表头
    header = [fmt_cell(f, w) for f, w in zip(show_fields, widths)]
    term_w = shutil.get_terminal_size().columns

    if title:
        print()
        print(f"  === {title} ===")
        print()

    top = _border_line(widths, _TL, _TM, _TR)
    if visible_len(top) > term_w:
        # 表格超出终端宽度时降级为无边框简化版
        _simple_table(header, rows, widths)
        return

    # 输出完整 Unicode 边框表格
    print(_border_line(widths, _TL, _TM, _TR))    # 顶部边框
    print(_data_row(header, widths))               # 表头行
    print(_border_line(widths, _ML, _MM, _MR))    # 表头分隔线
    for idx, row in enumerate(rows):
        print(_data_row(row, widths))              # 数据行
        if idx < len(rows) - 1:
            print(_border_line(widths, _ML, _MM, _MR))  # 行分隔线
    print(_border_line(widths, _BL, _BM, _BR))    # 底部边框
    print(f"  共 {len(records)} 条记录")
    print()


def _simple_table(header, rows, widths):
    """终端宽度不足时使用的简化无边框版"""
    sep = "  "
    hdr_str = sep.join(h for h in header)
    print("  " + hdr_str)
    print("  " + "-" * min(visible_len(hdr_str), 80))
    for row in rows:
        line = sep.join(r for r in row)
        print("  " + line)
    print(f"  共 {len(rows)} 条记录")
    print()


def print_status_menu():
    """打印 16 种状态及其编号（每行4列）"""
    cols = 4
    for i, s in enumerate(STATUS_LIST):
        print(f"    [{i+1:2d}] {s}", end="")
        if (i + 1) % cols == 0:
            print()
    if len(STATUS_LIST) % cols != 0:
        print()


def print_record_detail(rec):
    """打印单条记录的详细信息（带Unicode边框）"""
    print()
    print("  " + _TL + _H * 58 + _TR)
    for k, v in rec.items():
        print(f"  {_V} {k:10s}: {v}")
    print("  " + _BL + _H * 58 + _BR)
    print()