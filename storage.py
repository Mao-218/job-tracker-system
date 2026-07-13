# ============================
# File: storage.py
# CSV 本地持久化存储，实现增删改查 CRUD
# 编码：utf-8-sig（带 BOM，Excel 直接打开不乱码）
# ============================

import csv
import os
from models import FIELD_NAMES, CSV_FILE, CSV_ENCODING


def _get_path():
    """获取 CSV 文件在项目目录下的完整路径"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), CSV_FILE)


def load_all():
    """从 CSV 文件加载所有记录，返回 list[dict]"""
    records = []
    path = _get_path()
    if not os.path.exists(path):
        return records
    try:
        with open(path, "r", encoding=CSV_ENCODING, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
    except Exception as e:
        print(f"  [错误] 读取 CSV 失败: {e}")
    return records


def save_all(records):
    """将全部记录列表覆盖写入 CSV 文件"""
    path = _get_path()
    try:
        with open(path, "w", encoding=CSV_ENCODING, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELD_NAMES)
            writer.writeheader()
            for rec in records:
                # 保证所有字段都存在，缺失的填空字符串
                clean = {k: rec.get(k, "") for k in FIELD_NAMES}
                writer.writerow(clean)
        return True
    except Exception as e:
        print(f"  [错误] 写入 CSV 失败: {e}")
        return False


def add_record(record):
    """新增一条求职记录"""
    records = load_all()
    records.append(record)
    return save_all(records)


def delete_record(index):
    """
    按索引删除记录（0-based）
    返回 True 表示成功，False 表示索引越界
    """
    records = load_all()
    if index < 0 or index >= len(records):
        return False
    records.pop(index)
    return save_all(records)


def update_record(index, record):
    """更新指定索引的记录"""
    records = load_all()
    if index < 0 or index >= len(records):
        return False
    records[index] = record
    return save_all(records)


def filter_records(key, value):
    """按字段精确匹配筛选（如 "当前进度状态" == "已投递"）"""
    records = load_all()
    if not value:
        return records
    return [r for r in records if r.get(key, "") == value]


def search_records(keyword):
    """按关键词在所有字段中做不区分大小写的模糊搜索"""
    records = load_all()
    keyword = keyword.strip().lower()
    if not keyword:
        return records
    result = []
    for r in records:
        for v in r.values():
            if keyword in v.strip().lower():
                result.append(r)
                break
    return result


def get_record_count():
    """获取记录总数"""
    return len(load_all())