# ============================
# File: statistics.py
# 数据统计、转化率、各状态计数柱状图分析
# ============================
from docx import Document
import PyPDF2
#可以读取word和PDF
from models import STATUS_LIST, STATUS_GROUPS
from storage import load_all


def count_by_status():
    """统计每个状态的记录数量，返回 (counts_dict, total)"""
    records = load_all()
    counts = {s: 0 for s in STATUS_LIST}
    for r in records:
        s = r.get("当前进度状态", "")
        if s in counts:
            counts[s] += 1
    return counts, len(records)


def count_by_group():
    """按阶段分组统计，返回 (group_counts, total)"""
    records = load_all()
    counts = {}
    for group_name, statuses in STATUS_GROUPS.items():
        cnt = sum(1 for r in records
                  if r.get("当前进度状态", "") in statuses)
        counts[group_name] = cnt
    return counts, len(records)


def conversion_stats():
    """
    计算各阶段转化率及关键指标

    返回:
        stats: dict — 各阶段统计 + 综合指标
        total: int  — 投递总数
    """
    records = load_all()
    total = len(records)
    if total == 0:
        return {}, total

    stats = {}
    for group_name, statuses in STATUS_GROUPS.items():
        cnt = sum(1 for r in records
                  if r.get("当前进度状态", "") in statuses)
        stats[group_name] = {
            "count": cnt,
            "ratio": f"{cnt / total * 100:.1f}%" if total > 0 else "0%",
        }

    # 关键指标
    offer_cnt = sum(1 for r in records
                    if r.get("当前进度状态", "") == "收到offer")
    has_interview_cnt = sum(
        1 for r in records
        if r.get("当前进度状态", "") in (
            "待一面", "一面完成", "待二面", "二面完成", "HR面"
        )
    )
    terminated = sum(
        1 for r in records
        if r.get("当前进度状态", "") in (
            "简历挂", "笔试挂", "一面挂", "二面挂", "拒绝offer"
        )
    )

    stats["综合"] = {
        "offer率": f"{offer_cnt / total * 100:.1f}%" if total > 0 else "0%",
        "面试率": f"{has_interview_cnt / total * 100:.1f}%" if total > 0 else "0%",
        "已终止": terminated,
    }

    return stats, total


def print_summary():
    """打印完整的统计汇总信息到终端"""
    counts, total = count_by_status()
    print()
    print(f"  === 投递数据统计汇总 ===")
    print(f"  投递总数: {total}")
    print()
    print("  --- 各状态数量分布 ---")
    for s in STATUS_LIST:
        c = counts[s]
        bar = "#" * c if c <= 60 else "#" * 60 + f" (+{c - 60})"
        print(f"    {s:8s} : {c:3d}  {bar}")

    grp, _ = count_by_group()
    print()
    print("  --- 各阶段分布 ---")
    for g, c in grp.items():
        pct = f"{c / total * 100:.1f}%" if total > 0 else "0%"
        print(f"    {g:6s} : {c:3d} ({pct})")

    stats, _ = conversion_stats()
    if "综合" in stats:
        s = stats["综合"]
        print()
        print("  --- 综合转化率 ---")
        print(f"    面试率 : {s.get('面试率', 'N/A')}")
        print(f"    Offer率: {s.get('offer率', 'N/A')}")
        print(f"    已终止 : {s.get('已终止', 0)}")
    print()
def calculate_match_score(resume_text: str, jd_text: str) -> tuple[int, list, list]:
    """
    简历 <--> JD 关键词匹配打分
    :param resume_text: 简历文本
    :param jd_text: 岗位JD文本
    :return: (分数, 匹配技能列表, 缺失技能列表)
    """
    # =========【重点！在这里填入你自己的求职技能词库，根据你的岗位修改！】=========
    skill_keywords = {
        "Python", "Flask", "CSV", "数据分析", "项目管理", "硬件", "硬件测试",
        "需求梳理", "进度管理", "沟通协调", "OCR", "Tesseract", "调试", "文档编写"
    }
    # ==========================================================================

    # 统一小写清洗文本
    resume_low = resume_text.lower()
    jd_low = jd_text.lower()

    # 提取JD内出现的所有技能需求
    jd_skills = [s for s in skill_keywords if s.lower() in jd_low]
    if len(jd_skills) == 0:
        return 0, [], []

    # 筛选简历里具备的技能
    matched = [s for s in jd_skills if s.lower() in resume_low]
    missing = [s for s in jd_skills if s.lower() not in resume_low]

    # 计算得分
    score = int(len(matched) / len(jd_skills) * 100)
    return score, matched, missing


def load_resume_from_txt(filepath: str) -> str:
    """读取txt简历文件"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"读取简历失败：{e}")
        return ""
def calculate_match_score(resume_text: str, jd_text: str) -> tuple[int, list, list]:
    """
    简历 <--> JD 关键词匹配打分
    :param resume_text: 简历文本
    :param jd_text: 岗位JD文本
    :return: (分数, 匹配技能列表, 缺失技能列表)
    """
    # =========【重点！在这里填入你求职方向技能词库，按需修改！】=========
    skill_keywords = {
        "Python", "Flask", "CSV", "数据分析", "项目管理", "硬件", "硬件测试",
        "需求梳理", "进度管理", "沟通协调", "OCR", "Tesseract", "调试", "文档编写"
    }
    # ==========================================================================

    # 统一小写清洗文本
    resume_low = resume_text.lower()
    jd_low = jd_text.lower()

    # 提取JD内出现的所有技能需求
    jd_skills = [s for s in skill_keywords if s.lower() in jd_low]
    if len(jd_skills) == 0:
        return 0, [], []

    # 筛选简历里具备的技能
    matched = [s for s in jd_skills if s.lower() in resume_low]
    missing = [s for s in jd_skills if s.lower() not in resume_low]

    # 计算得分
    score = int(len(matched) / len(jd_skills) * 100)
    return score, matched, missing


def load_resume_file(filepath: str) -> str:
    """
    自动识别后缀：支持 .txt / .docx / .pdf 简历读取
    """
    filepath = filepath.strip()
    lower_path = filepath.lower()
    text = ""
    try:
        if lower_path.endswith(".txt"):
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()

        elif lower_path.endswith(".docx"):
            doc = Document(filepath)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)

        elif lower_path.endswith(".pdf"):
            with open(filepath, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        else:
            print("❌ 不支持的文件格式！仅支持 txt / docx / pdf")
            return ""
    except Exception as e:
        print(f"❌ 文件读取失败：{str(e)}")
        return ""
    return text.strip()
