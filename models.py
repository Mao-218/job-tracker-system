# ============================
# File: models.py
# 数据常量、投递状态枚举、字段定义
# ============================

# 全部 13 个字段（同时也是 CSV 列名）
FIELD_NAMES = [
    "公司名称", "岗位名称", "岗位链接", "投递日期", "投递渠道",
    "当前进度状态", "面试时间", "地点", "期望薪资", "标签",
    "JD原文", "岗位适配得分", "备注",
]

# 表格显示时各字段的最大字符宽度（中文算2格）
# width <= 0 表示自动截断为 40 字符 + "…"
DISPLAY_COL_WIDTHS = {
    "公司名称": 22, "岗位名称": 26, "投递日期": 12, "投递渠道": 10,
    "当前进度状态": 14, "面试时间": 14, "地点": 14, "期望薪资": 12,
    "标签": 16, "岗位适配得分": 10, "备注": 22,
}

# 严格限定的 16 种求职进度状态
STATUS_LIST = [
    "已投递",           # 已投递但无后续反馈
    "简历筛选中",       # HR/系统正在筛选简历
    "简历挂",           # 简历筛选未通过
    "待笔试",           # 等待参加笔试
    "笔试完成",         # 笔试已提交
    "笔试挂",           # 笔试未通过
    "待一面",           # 等待第一轮面试
    "一面完成",         # 一面已结束
    "一面挂",           # 一面未通过
    "待二面",           # 等待第二轮面试
    "二面完成",         # 二面已结束
    "二面挂",           # 二面未通过
    "HR面",             # HR 面试环节
    "OC沟通",           # Offer Call 沟通中
    "收到offer",        # 已收到正式 Offer
    "拒绝offer",        # 已拒绝 Offer
]

# 按阶段分组（用于统计归类）
STATUS_GROUPS = {
    "前期": ["已投递", "简历筛选中"],
    "简历挂": ["简历挂"],
    "笔试": ["待笔试", "笔试完成", "笔试挂"],
    "面试": ["待一面", "一面完成", "一面挂",
             "待二面", "二面完成", "二面挂", "HR面"],
    "终局": ["OC沟通", "收到offer", "拒绝offer"],
}

# CSV 路径与编码
CSV_FILE = "applications.csv"
CSV_ENCODING = "utf-8-sig"   # 带 BOM，Excel 直接打开不乱码
DATE_FORMAT = "%Y-%m-%d"


def validate_status(status):
    """校验状态是否在允许列表中"""
    return status in STATUS_LIST


def normalize_score(score_str):
    """
    规范化得分字段，保证为 0-100 整数或空字符串
    非法输入返回空字符串
    """
    if not score_str or not score_str.strip():
        return ""
    try:
        v = int(float(score_str.strip()))
        return str(max(0, min(100, v)))
    except (ValueError, TypeError):
        return ""


def column_index(name):
    """根据字段名获取在 FIELD_NAMES 中的索引"""
    return FIELD_NAMES.index(name)