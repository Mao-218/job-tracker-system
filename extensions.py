"""
extensions.py - 扩展接口：OCR识别导入 + 技能打分 + 预留功能

本地依赖包路径：python_packages/ 下的 pytesseract
"""

import sys as _sys
import os as _os
import re

_pkg_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "python_packages")
if _os.path.isdir(_pkg_dir) and _pkg_dir not in _sys.path:
    _sys.path.insert(0, _pkg_dir)
del _sys, _pkg_dir       # 保留 _os（函数中会用到）


# ============================================================
# 个人技能关键词库（内置，共8项）
# ============================================================
SKILL_KEYWORDS = [
    "新能源", "电机", "硬件项目管理", "嵌入式",
    "Python", "仿真", "硬件测试", "硬件PM",
]


# ════════════════════════════════════════════════════════════
#  OCR 截图识别导入
# ════════════════════════════════════════════════════════════

def _parse_ocr_text(ocr_text):
    """
    对 OCR 识别出的原始文本进行智能字段提取。

    扫描公司名称、岗位名称、工作地点及 JD 职责描述，
    返回包含预填充值的 dict。
    处理常见格式：带冒号/空格分隔、无分隔符后缀匹配等。
    """
    if not ocr_text or not ocr_text.strip():
        return {"公司名称": "", "岗位名称": "", "地点": "", "JD原文": ""}

    lines = [l.strip() for l in ocr_text.split("\n") if l.strip()]
    full = ocr_text.strip()
    result = {"公司名称": "", "岗位名称": "", "地点": "", "JD原文": ""}

    # ── 1. 提取公司名称 ──────────────────────────────
    for pat in [
        r"(?:公司名称|用人单位|雇主|招聘公司)[\s:：]*([^\n]{1,40})",
    ]:
        m = re.search(pat, full)
        if m:
            name = m.group(1).strip().rstrip("，, ")
            if name:
                result["公司名称"] = name
                break

    # 若显式标签未匹配，尝试匹配 "XX有限公司/集团/股份" 模式
    if not result["公司名称"]:
        m = re.search(
            r"([\u4e00-\u9fff]{2,}(?:科技有限公司|技术有限公司|"
            r"信息技术有限公司|网络科技有限公司|实业有限公司|"
            r"有限公?司|集团|股份|股份公司))",
            full,
        )
        if m:
            result["公司名称"] = m.group(1).strip()

    # ── 2. 提取岗位名称 ──────────────────────────────
    for pat in [
        r"(?:招聘岗位|岗位名称|职位名称|招聘职位|岗位|职位)"
        r"[\s:：]*([^\n]{1,40})",
    ]:
        m = re.search(pat, full)
        if m:
            pos = m.group(1).strip().rstrip("，, ")
            if pos:
                result["岗位名称"] = pos
                break

    # 后缀兜底：找包含常见职位关键词的行
    if not result["岗位名称"]:
        job_suffix = [
            "工程师", "开发", "经理", "专员", "主管",
            "实习生", "助理", "总监", "设计师", "运营",
        ]
        for line in lines:
            if len(line) > 25 or "公司" in line or re.search(r"^[\d.、)\-]", line):
                continue
            for suffix in job_suffix:
                if suffix in line:
                    result["岗位名称"] = line[:30]
                    break
            if result["岗位名称"]:
                break

    # ── 3. 提取工作地点 ──────────────────────────────
    for pat in [
        r"(?:工作地点|工作地址|上班地点|工作城市|所在城市|"
        r"办公地点|地点|城市|地址)[\s:：]*([^\n]{1,30})",
    ]:
        m = re.search(pat, full)
        if m:
            loc = m.group(1).strip().rstrip("，, ")
            if loc:
                result["地点"] = loc
                break

    # ── 4. 提取 JD 岗位职责原文 ──────────────────────
    jd_starts = [
        "岗位职责", "职位描述", "工作内容", "工作职责",
        "岗位要求", "任职要求", "工作描述", "岗位描述",
        "职责描述",
    ]
    jd_ends = [
        "任职要求", "福利待遇", "薪酬福利", "薪资福利",
        "公司介绍", "投递方式", "应聘方式", "联系方式",
        "公司简介",
    ]

    start_idx = -1
    for kw in jd_starts:
        idx = full.find(kw)
        if idx != -1:
            start_idx = idx
            break

    if start_idx != -1:
        end_idx = len(full)
        for kw in jd_ends:
            idx = full.find(kw, start_idx + len(kw))
            if idx != -1 and idx < end_idx:
                end_idx = idx
        result["JD原文"] = full[start_idx:end_idx].strip()
    else:
        result["JD原文"] = full[:600].strip()

    return result


def ocr_import_from_image(image_path=None):
    """
    读取本地招聘截图，通过 Tesseract OCR 识别并智能提取字段，
    返回预填充的求职记录列表（当前返回 1 条或空列表）。

    依赖:
        - Tesseract OCR 引擎（需单独安装，支持简体中文）
        - Python 包 pytesseract + Pillow
    参数:
        image_path: str — 图片文件路径（.png/.jpg/.bmp/.tiff）
    返回:
        list[dict]: 预填充的求职记录列表
    """
    if not image_path:
        print("  [错误] 未提供图片路径。")
        return []

    if not _os.path.exists(image_path):
        print(f"  [错误] 文件不存在: {image_path}")
        return []

    # 检测 Tesseract 是否已安装
    try:
        import subprocess
        subprocess.run(
            ["tesseract", "--version"],
            capture_output=True, timeout=10,
        )
    except Exception:
        print()
        print("  [错误] 未检测到 Tesseract OCR 引擎。")
        print("  请先安装 Tesseract（安装步骤见下方说明）：")
        print("  1. 下载: https://github.com/UB-Mannheim/tesseract/wiki")
        print("  2. 安装时勾选中文简体语言包")
        print("  3. 将安装目录加入系统环境变量 Path")
        print()
        return []

    # 执行 OCR 识别
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(image_path)
        ocr_text = ""
        for lang in ["chi_sim+eng", "chi_sim", "eng"]:
            try:
                ocr_text = pytesseract.image_to_string(
                    img, lang=lang, config="--psm 6"
                )
                if ocr_text.strip():
                    break
            except Exception:
                continue

    except ImportError as e:
        print(f"  [错误] OCR 依赖包未安装: {e}")
        print("  请执行: pip install pytesseract Pillow")
        return []
    except Exception as e:
        print(f"  [OCR 识别失败] {e}")
        return []

    if not ocr_text or not ocr_text.strip():
        print("  [提示] OCR 未能识别出文字，请确认图片清晰度与内容。")
        return []

    # 智能提取字段
    fields = _parse_ocr_text(ocr_text)

    print()
    print("  ┌────── OCR 识别结果 ──────────────────────────┐")
    print(f"  │  公司名称: {fields['公司名称'] or '（未识别）'}")
    print(f"  │  岗位名称: {fields['岗位名称'] or '（未识别）'}")
    print(f"  │  工作地点: {fields['地点'] or '（未识别）'}")
    jd_preview = (fields['JD原文'][:60] or '（未识别）')
    print(f"  │  JD摘要: {jd_preview}")
    print("  └──────────────────────────────────────────────┘")

    record = {
        "公司名称": fields.get("公司名称", ""),
        "岗位名称": fields.get("岗位名称", ""),
        "岗位链接": "",
        "投递日期": "",
        "投递渠道": "截图导入",
        "当前进度状态": "已投递",
        "面试时间": "",
        "地点": fields.get("地点", ""),
        "期望薪资": "",
        "标签": "",
        "JD原文": fields.get("JD原文", ""),
        "岗位适配得分": "",
        "备注": "",
    }
    return [record]


# ════════════════════════════════════════════════════════════
#  预留接口：JD文本分析 / Web同步 / Excel导入
# ════════════════════════════════════════════════════════════

def analyze_jd_match(jd_text, resume_keywords=None):
    """【预留】JD 文本匹配度分析"""
    print()
    print("  [预留] JD 文本匹配度分析功能尚未完整实现。")
    print("  该函数框架已预留于 extensions.py，后续可接入。")
    print()
    return {"score": 0, "matched_keywords": [], "suggestions": []}


def sync_to_web(records=None):
    """【预留】将本地求职数据同步到 Web 端"""
    print()
    print("  [预留] Web 对接功能尚未完整实现。")
    print()
    return False


def import_from_excel(filepath):
    """【预留】从 Excel 文件导入投递记录"""
    print()
    print("  [预留] Excel 导入功能尚未完整实现。")
    print()
    return []


# ════════════════════════════════════════════════════════════
#  岗位适配度自动打分（已实现）
# ════════════════════════════════════════════════════════════

def auto_score_position(record):
    """
    基于个人技能关键词库对岗位进行适配度打分。
    扫描 JD原文 + 岗位名称 + 标签，返回 0~100 分及详细清单。

    参数:
        record: dict — 单条求职记录
    返回:
        dict: score / total / matched / missing / matched_count
    """
    jd_text = (record.get("JD原文") or "")
    pos_name = (record.get("岗位名称") or "")
    tags = (record.get("标签") or "")
    search_text = f"{jd_text} {pos_name} {tags}"

    if not search_text.strip():
        return {
            "score": 0,
            "total": len(SKILL_KEYWORDS),
            "matched": [],
            "missing": list(SKILL_KEYWORDS),
            "matched_count": 0,
        }

    search_text_lower = search_text.lower()
    total = len(SKILL_KEYWORDS)
    matched_skills = []
    missing_skills = []

    for skill in SKILL_KEYWORDS:
        if skill.lower() in search_text_lower:
            matched_skills.append(skill)
        else:
            missing_skills.append(skill)

    matched_count = len(matched_skills)
    score = round(matched_count / total * 100) if total > 0 else 0

    return {
        "score": score,
        "total": total,
        "matched": matched_skills,
        "missing": missing_skills,
        "matched_count": matched_count,
    }