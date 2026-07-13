# app.py - Flask Web 求职管理平台入口
# 启动：pip install flask  →  python app.py  →  浏览器访问 http://127.0.0.1:5000

import io
import os
import csv
import json
import tempfile
from datetime import datetime

from flask import (Flask, render_template, request, redirect,
                   url_for, flash, session, Response)

# 复用现有模块
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from storage import (load_all, add_record, update_record, delete_record,
                     filter_records, search_records, save_all)
from models import FIELD_NAMES, STATUS_LIST, normalize_score, CSV_ENCODING
from statistics import count_by_status, count_by_group, conversion_stats
from extensions import auto_score_position, ocr_import_from_image, SKILL_KEYWORDS

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()  # 用于 session 签名

PER_PAGE = 15  # 每页显示记录数


# ════════════════════════════════════════════════════════════
#  辅助函数
# ════════════════════════════════════════════════════════════

def _form_to_record(form):
    """从 Flask request.form 构建记录字典"""
    rec = {}
    for field in FIELD_NAMES:
        val = form.get(field, "").strip()
        if field == "岗位适配得分":
            val = normalize_score(val)
        rec[field] = val
    return rec


def _record_from_ocr(image_path):
    """对图片执行 OCR 并返回预填充记录"""
    result = ocr_import_from_image(image_path)
    if result:
        return result[0]
    return {}


def _get_pagination(records, page):
    """分页计算，返回 (page_records_with_index, page, total_pages, total)"""
    total = len(records)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    page_records = records[start:end]
    # 返回带绝对索引的记录列表
    page_data = [(start + i, rec) for i, rec in enumerate(page_records)]
    return page_data, page, total_pages, total


# ════════════════════════════════════════════════════════════
#  首页 - 投递记录列表（分页）
# ════════════════════════════════════════════════════════════

@app.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    keyword = request.args.get("keyword", "").strip()
    status_filter = request.args.get("status", "").strip()

    records = load_all()

    # 搜索/筛选
    if keyword:
        records = search_records(keyword)
    if status_filter:
        records = filter_records("当前进度状态", status_filter)

    page_data, current_page, total_pages, total = _get_pagination(records, page)

    return render_template(
        "index.html",
        page_data=page_data,
        page=current_page,
        total_pages=total_pages,
        total=total,
        keyword=keyword,
        status_filter=status_filter,
        status_list=STATUS_LIST,
    )


# ════════════════════════════════════════════════════════════
#  新增投递记录（手工 + OCR 图片上传）
# ════════════════════════════════════════════════════════════

@app.route("/add", methods=["GET", "POST"])
def add():
    prefill = {}

    # 从 session 读取 OCR 预填充数据
    if "ocr_prefill" in session:
        prefill = session.pop("ocr_prefill")
        flash("OCR 识别完成，请确认并修改以下信息。", "info")

    if request.method == "POST":
        action = request.form.get("action", "")

        # ── OCR 图片上传 ──────────────────────────────
        if action == "ocr_upload":
            file = request.files.get("ocr_image")
            if file and file.filename:
                try:
                    suffix = os.path.splitext(file.filename)[1] or ".png"
                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                        file.save(tmp.name)
                        tmp_path = tmp.name

                    ocr_record = _record_from_ocr(tmp_path)
                    os.unlink(tmp_path)  # 删除临时文件

                    if ocr_record:
                        session["ocr_prefill"] = ocr_record
                        return redirect(url_for("add"))
                    else:
                        flash("OCR 未能识别出有效信息，请确认图片内容。", "warning")
                except Exception as e:
                    flash(f"OCR 处理失败: {e}", "danger")
            else:
                flash("请先选择图片文件。", "warning")
            return redirect(url_for("add"))

        # ── 手工提交 ──────────────────────────────────
        if action == "manual_submit":
            rec = _form_to_record(request.form)
            if not rec.get("公司名称") or not rec.get("岗位名称"):
                flash("公司名称和岗位名称为必填项！", "danger")
                return render_template("add.html", prefill=rec)
            rec["投递日期"] = rec.get("投递日期") or datetime.now().strftime("%Y-%m-%d")
            rec["投递渠道"] = rec.get("投递渠道") or "官网"
            rec["当前进度状态"] = rec.get("当前进度状态") or "已投递"
            if add_record(rec):
                flash(f"✅ 已添加: {rec['公司名称']} - {rec['岗位名称']}", "success")
                return redirect(url_for("index"))
            else:
                flash("保存失败，请重试。", "danger")

    return render_template("add.html", prefill=prefill, status_list=STATUS_LIST)


# ════════════════════════════════════════════════════════════
#  修改投递记录
# ════════════════════════════════════════════════════════════

@app.route("/edit/<int:idx>", methods=["GET", "POST"])
def edit(idx):
    records = load_all()
    if idx < 0 or idx >= len(records):
        flash("记录不存在。", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        rec = _form_to_record(request.form)
        rec["投递日期"] = rec.get("投递日期") or records[idx].get("投递日期", "")
        if update_record(idx, rec):
            flash(f"✅ 记录 #{idx + 1} 已更新。", "success")
            return redirect(url_for("index"))
        else:
            flash("更新失败。", "danger")

    return render_template("edit.html", record=records[idx], idx=idx, status_list=STATUS_LIST)


# ════════════════════════════════════════════════════════════
#  删除投递记录
# ════════════════════════════════════════════════════════════

@app.route("/delete/<int:idx>", methods=["POST"])
def delete(idx):
    records = load_all()
    if 0 <= idx < len(records):
        name = records[idx].get("公司名称", "")
        pos = records[idx].get("岗位名称", "")
        if delete_record(idx):
            flash(f"✅ 已删除: {name} - {pos}", "success")
        else:
            flash("删除失败。", "danger")
    else:
        flash("记录不存在。", "danger")
    return redirect(url_for("index"))


# ════════════════════════════════════════════════════════════
#  JD 岗位适配度打分
# ════════════════════════════════════════════════════════════

@app.route("/score/<int:idx>")
def score(idx):
    records = load_all()
    if idx < 0 or idx >= len(records):
        flash("记录不存在。", "danger")
        return redirect(url_for("index"))
    result = auto_score_position(records[idx])
    return render_template("score.html", record=records[idx], idx=idx, result=result)


@app.route("/score/<int:idx>/save", methods=["POST"])
def score_save(idx):
    records = load_all()
    if 0 <= idx < len(records):
        records[idx]["岗位适配得分"] = request.form.get("score", "")
        if save_all(records):
            flash("✅ 得分已保存。", "success")
        else:
            flash("保存失败。", "danger")
    return redirect(url_for("index"))


# ════════════════════════════════════════════════════════════
#  数据统计页面
# ════════════════════════════════════════════════════════════

@app.route("/statistics")
def statistics():
    counts, total = count_by_status()
    groups, _ = count_by_group()
    conv_stats, _ = conversion_stats()

    # 序列化为 JSON 供 Chart.js 使用
    status_labels = [s for s in STATUS_LIST]
    status_values = [counts.get(s, 0) for s in STATUS_LIST]

    group_labels = list(groups.keys())
    group_values = [groups.get(g, 0) for g in group_labels]

    # 漏斗数据：简历占比 → 笔试占比 → 面试占比 → offer 占比
    funnel_data = {}
    if total > 0:
        for g, c in groups.items():
            funnel_data[g] = {"count": c, "pct": round(c / total * 100, 1)}

    # 综合指标
    composite = conv_stats.get("综合", {})

    return render_template(
        "statistics.html",
        total=total,
        status_labels_json=json.dumps(status_labels, ensure_ascii=False),
        status_values_json=json.dumps(status_values),
        group_labels_json=json.dumps(group_labels, ensure_ascii=False),
        group_values_json=json.dumps(group_values),
        funnel_data=funnel_data,
        composite=composite,
        status_list=STATUS_LIST,
        counts=counts,
    )


# ════════════════════════════════════════════════════════════
#  导出 CSV（Excel 打开不乱码）
# ════════════════════════════════════════════════════════════

@app.route("/export")
def export_csv():
    records = load_all()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=FIELD_NAMES)
    writer.writeheader()
    for rec in records:
        writer.writerow({k: rec.get(k, "") for k in FIELD_NAMES})
    # utf-8-sig 带 BOM，Excel 直接打开不乱码
    bytes_output = output.getvalue().encode("utf-8-sig")
    return Response(
        bytes_output,
        mimetype="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": "attachment; filename=applications_export.csv"},
    )


# ════════════════════════════════════════════════════════════
#  启动
# ════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("""
============================
秋招求职进度管理平台  v1.0
启动地址： http://127.0.0.1:5000
============================
""")
    app.run(debug=False)
