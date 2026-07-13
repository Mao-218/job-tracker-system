"""
main.py - 秋招求职进度管理命令行工具入口

使用方式：python main.py
依赖  ：Python 标准库 + pytesseract + Pillow（OCR功能需要）
"""

import os
import sys
from datetime import datetime

from models import FIELD_NAMES, STATUS_LIST, validate_status, normalize_score
from display import print_table, print_status_menu, print_record_detail
from storage import (load_all, add_record, delete_record, update_record,
                     filter_records, search_records, save_all)
from statistics import print_summary, calculate_match_score, load_resume_file
from extensions import ocr_import_from_image, auto_score_position


# ============================================================
# 辅助输入函数
# ============================================================

def input_str(prompt, default="", required=False):
    """输入字符串，支持默认值与必填校验"""
    while True:
        prompt_text = prompt
        if default:
            prompt_text += f"（默认: {default}）"
        prompt_text += ": "
        val = input(prompt_text).strip()
        if not val:
            if default:
                return default
            if required:
                print("  [提示] 该项不能为空，请重新输入。")
                continue
            return ""
        return val


def input_int(prompt, min_v=None, max_v=None):
    """输入整数，带范围校验"""
    while True:
        val = input(prompt + ": ").strip()
        if not val:
            return None
        try:
            v = int(val)
            if min_v is not None and v < min_v:
                print(f"  [提示] 输入不能小于 {min_v}，请重新输入。")
                continue
            if max_v is not None and v > max_v:
                print(f"  [提示] 输入不能大于 {max_v}，请重新输入。")
                continue
            return v
        except ValueError:
            print("  [提示] 请输入有效整数。")


def input_date(prompt, default=""):
    """输入日期，格式 YYYY-MM-DD"""
    if not default:
        default = datetime.now().strftime("%Y-%m-%d")
    while True:
        val = input(f"{prompt}（默认 {default}）: ").strip()
        if not val:
            return default
        try:
            datetime.strptime(val, "%Y-%m-%d")
            return val
        except ValueError:
            print("  [提示] 日期格式错误，应为 YYYY-MM-DD（如 2026-07-13）。")


def input_status():
    """从固定 16 种状态列表中强制选择（禁止自由输入）"""
    print()
    print("  请选择当前进度状态：")
    print_status_menu()
    while True:
        sel = input_int("  请输入状态编号", min_v=1, max_v=len(STATUS_LIST))
        if sel is None:
            print("  [提示] 请选择一个有效编号。")
            continue
        return STATUS_LIST[sel - 1]


def input_record():
    """交互式输入一条完整的求职记录"""
    print()
    print("  === 新增求职记录 ===")
    rec = {}
    rec["公司名称"] = input_str("  公司名称", required=True)
    rec["岗位名称"] = input_str("  岗位名称", required=True)
    rec["岗位链接"] = input_str("  岗位链接（URL）")
    rec["投递日期"] = input_date("  投递日期")
    rec["投递渠道"] = input_str("  投递渠道", default="官网")
    rec["当前进度状态"] = input_status()
    rec["面试时间"] = input_str("  面试时间")
    rec["地点"] = input_str("  地点")
    rec["期望薪资"] = input_str("  期望薪资")
    rec["标签"] = input_str("  标签（多个用逗号分隔）")
    score_raw = input_str("  岗位适配得分（0-100）")
    rec["岗位适配得分"] = normalize_score(score_raw)
    rec["JD原文"] = input_str("  JD原文（可多行，用 | 分隔）")
    rec["备注"] = input_str("  备注")
    return rec


def select_record(records):
    """让用户从记录列表中选一条，返回 (index, record)"""
    if not records:
        print("  [提示] 当前没有可选的记录。")
        return None, None
    print()
    idx = input_int(f"  请输入记录编号 (1-{len(records)})",
                    min_v=1, max_v=len(records))
    if idx is None:
        return None, None
    return idx - 1, records[idx - 1]


# ============================================================
# 菜单功能实现
# ============================================================

def menu_add():
    """① 新增投递记录"""
    rec = input_record()
    if add_record(rec):
        print()
        print(f"  [成功] 已添加: {rec['公司名称']} - {rec['岗位名称']}")
    else:
        print("  [失败] 添加记录失败")


def menu_list_all():
    """② 查看全部投递列表"""
    records = load_all()
    print()
    print(f"  === 全部投递记录 ({len(records)} 条) ===")
    print()
    if records:
        print_table(records)


def menu_filter():
    """③ 按状态 / 标签 / 关键词筛选"""
    print()
    print("  === 筛选投递记录 ===")
    print("    1. 按当前进度状态筛选")
    print("    2. 按标签筛选")
    print("    3. 按关键词搜索")
    print("    0. 返回上级菜单")
    choice = input_int("  请选择筛选方式", min_v=0, max_v=3)
    if choice == 1:
        print()
        print("  请选择状态：")
        print_status_menu()
        sel = input_int("  请输入状态编号", min_v=1, max_v=len(STATUS_LIST))
        if sel:
            status = STATUS_LIST[sel - 1]
            filtered = filter_records("当前进度状态", status)
            print_table(filtered, title=f"筛选结果: 状态 = {status}")
    elif choice == 2:
        tag = input_str("  请输入标签关键字")
        if tag:
            all_recs = load_all()
            filtered = [r for r in all_recs if tag in r.get("标签", "")]
            print_table(filtered, title=f"筛选结果: 标签包含 [{tag}]")
    elif choice == 3:
        kw = input_str("  请输入搜索关键词")
        if kw:
            filtered = search_records(kw)
            print_table(filtered, title=f"搜索结果: 包含 [{kw}]")


def menu_update():
    """④ 修改某条记录进度"""
    records = load_all()
    if not records:
        print("  [提示] 当前没有记录可修改。")
        return
    print_table(records, title="当前所有记录")
    idx, rec = select_record(records)
    if rec is None:
        return
    print()
    print(f"  正在修改: #{idx + 1} {rec.get('公司名称', '')} - "
          f"{rec.get('岗位名称', '')}")
    print("  （直接回车跳过不修改的字段）")
    print()
    new_rec = {}
    new_rec["公司名称"] = input_str("  公司名称", default=rec.get("公司名称", ""))
    new_rec["岗位名称"] = input_str("  岗位名称", default=rec.get("岗位名称", ""))
    new_rec["岗位链接"] = input_str("  岗位链接", default=rec.get("岗位链接", ""))
    new_rec["投递日期"] = input_date("  投递日期",
                                      default=rec.get("投递日期", ""))
    new_rec["投递渠道"] = input_str("  投递渠道", default=rec.get("投递渠道", ""))
    print()
    print("  当前状态:", rec.get("当前进度状态", ""))
    new_rec["当前进度状态"] = input_status()
    new_rec["面试时间"] = input_str("  面试时间", default=rec.get("面试时间", ""))
    new_rec["地点"] = input_str("  地点", default=rec.get("地点", ""))
    new_rec["期望薪资"] = input_str("  期望薪资", default=rec.get("期望薪资", ""))
    new_rec["标签"] = input_str("  标签", default=rec.get("标签", ""))
    score_raw = input_str("  岗位适配得分（0-100）",
                          default=rec.get("岗位适配得分", ""))
    new_rec["岗位适配得分"] = normalize_score(score_raw)
    new_rec["JD原文"] = input_str("  JD原文", default=rec.get("JD原文", ""))
    new_rec["备注"] = input_str("  备注", default=rec.get("备注", ""))
    if update_record(idx, new_rec):
        print(f"  [成功] 记录 #{idx + 1} 已更新。")
    else:
        print("  [失败] 更新记录失败")


def menu_delete():
    """⑤ 删除记录"""
    records = load_all()
    if not records:
        print("  [提示] 当前没有记录可删除。")
        return
    print_table(records, title="当前所有记录")
    idx, rec = select_record(records)
    if rec is None:
        return
    confirm = input(f"  确认删除 [{rec.get('公司名称', '')} - "
                    f"{rec.get('岗位名称', '')}]? (y/N): ").strip().lower()
    if confirm != "y":
        print("  已取消删除。")
        return
    if delete_record(idx):
        print(f"  [成功] 已删除 #{idx + 1}")
    else:
        print("  [失败] 删除失败")


def menu_statistics():
    """⑥ 数据统计汇总"""
    print_summary()


def menu_export_excel():
    """⑦ 导出全部数据为 CSV（UTF-8 with BOM 编码）"""
    records = load_all()
    if not records:
        print("  [提示] 没有数据可导出。")
        return
    import csv as csv_module
    from models import CSV_ENCODING
    export_csv = "export_applications.csv"
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), export_csv)
    try:
        with open(path, "w", encoding=CSV_ENCODING, newline="") as f:
            writer = csv_module.DictWriter(f, fieldnames=FIELD_NAMES)
            writer.writeheader()
            for rec in records:
                writer.writerow({k: rec.get(k, "") for k in FIELD_NAMES})
        print(f"  [成功] 数据已导出到: {export_csv}")
        print("  请用 Excel/WPS 直接打开此 CSV 文件（UTF-8 with BOM 编码）")
    except Exception as e:
        print(f"  [错误] 导出失败: {e}")


def menu_ocr():
    """
    【8】图片OCR识别导入岗位

    用户输入本地招聘截图路径 → Tesseract OCR 识别 →
    智能提取公司/岗位/地点/JD → 人工确认修改 → 保存
    """
    print()
    print("  === 图片OCR识别导入岗位 ===")
    print()
    print("  支持的格式: .png .jpg .jpeg .bmp .tiff")
    print()

    image_path = input_str("  请输入招聘截图路径", required=True)
    if not image_path:
        return
    if not os.path.exists(image_path):
        print(f"  [错误] 文件不存在: {image_path}")
        return

    records = ocr_import_from_image(image_path)
    if not records:
        print()
        print("  [提示] 未能从图片中提取到有效投递信息。")
        print("  可能原因：")
        print("    1. 图片内容不包含招聘信息")
        print("    2. Tesseract OCR 引擎未安装")
        print("    3. 中文语言包未安装")
        return

    extracted = records[0]

    print()
    print("  ╔═══════════════════════════════════════════════╗")
    print("  ║     OCR 识别字段预览（可修改）               ║")
    print("  ╚═══════════════════════════════════════════════╝")
    print()
    print(f"    公司名称: {extracted.get('公司名称') or '（未识别）'}")
    print(f"    岗位名称: {extracted.get('岗位名称') or '（未识别）'}")
    print(f"    工作地点: {extracted.get('地点') or '（未识别）'}")
    jd_preview = (extracted.get('JD原文') or '（未识别）')[:80]
    print(f"    JD摘要: {jd_preview}")
    print()

    confirm = input("  是否基于以上信息创建投递记录？(Y/n): ").strip().lower()
    if confirm == "n":
        print("  已取消导入。")
        return

    # 逐字段人工确认/修改
    print()
    print("  === 请确认/修改以下字段（回车跳过保持原值） ===")
    print()
    rec = {}
    rec["公司名称"] = input_str("  公司名称", default=extracted.get("公司名称", ""))
    rec["岗位名称"] = input_str("  岗位名称", default=extracted.get("岗位名称", ""))
    rec["岗位链接"] = input_str("  岗位链接（URL）")
    rec["投递日期"] = input_date("  投递日期")
    rec["投递渠道"] = input_str("  投递渠道", default="截图导入")
    print()
    print("  请选择当前进度状态（默认: 已投递）：")
    rec["当前进度状态"] = input_status()
    rec["面试时间"] = input_str("  面试时间")
    rec["地点"] = input_str("  地点", default=extracted.get("地点", ""))
    rec["期望薪资"] = input_str("  期望薪资")
    rec["标签"] = input_str("  标签（多个用逗号分隔）")
    score_raw = input_str("  岗位适配得分（0-100）")
    rec["岗位适配得分"] = normalize_score(score_raw)
    rec["JD原文"] = input_str("  JD原文", default=extracted.get("JD原文", ""))
    rec["备注"] = input_str("  备注", default="来自OCR截图导入")

    if add_record(rec):
        print()
        print(f"  ✅ [成功] OCR导入完成: {rec['公司名称']} - {rec['岗位名称']}")
    else:
        print("  ❌ [失败] 保存记录失败")


def menu_jd_score():
    """
    【9】岗位JD适配度打分
    选中已有投递记录，支持粘贴简历 / 上传docx/pdf/txt简历，自动匹配评分，可保存得分
    """
    records = load_all()
    if not records:
        print(" [提示] 当前没有记录可打分。")
        return
    print_table(records, title="当前所有记录")
    idx, rec = select_record(records)
    if rec is None:
        return

    jd_text = rec.get("JD原文", "").strip()
    if not jd_text:
        print("\n❌ 该记录【JD原文】为空，无法进行匹配打分！")
        input("\n按回车返回菜单...")
        return

    print(f"\n===== 正在分析：{rec.get('公司名称', '')} - {rec.get('岗位名称', '')} =====")
    print("\n请选择简历录入方式：")
    print("1 - 直接粘贴简历文字")
    print("2 - 上传简历文件（支持 *.txt / *.docx / *.pdf）")
    mode = input("输入1或2：").strip()

    resume_content = ""
    if mode == "1":
        print("\n请粘贴简历内容（输入完成后单独一行输入 #end 结束）：")
        lines = []
        while True:
            line = input()
            if line.strip() == "#end":
                break
            lines.append(line)
        resume_content = "\n".join(lines)
    elif mode == "2":
        path = input("请输入简历完整文件路径：").strip()
        resume_content = load_resume_file(path)
        if not resume_content:
            print("❌ 简历文件读取失败或内容为空！")
            input("\n按回车返回菜单...")
            return
    else:
        print("❌ 选项输入错误！")
        input("\n按回车返回菜单...")
        return

    # 自动计算匹配分数
    score, matched_skills, missing_skills = calculate_match_score(resume_content, jd_text)

    print("\n==================== 匹配结果 ====================")
    print(f"目标岗位：{rec.get('公司名称')} {rec.get('岗位名称')}")
    print(f"自动匹配得分：【{score} / 100】")
    print(f"✅ 匹配技能：{matched_skills}")
    print(f"❌ 缺失技能：{missing_skills}")
    print("==================================================")

    save_opt = input("\n是否将本次分数保存到此投递记录？(y/n)：").strip().lower()
    if save_opt == "y":
        rec["岗位适配得分"] = str(score)
        save_all(records)
        print("✅ 分数保存成功！")

    input("\n按回车返回主菜单...")



def menu_exit():
    """退出程序"""
    print()
    print("  感谢使用秋招求职进度管理工具，祝 Offer 多多！")
    print()
    sys.exit(0)


# ============================================================
# 主菜单定义与循环（10 项功能）
# ============================================================

MENU_ITEMS = [
    ("新增投递记录", menu_add),
    ("查看全部投递列表", menu_list_all),
    ("按状态/岗位标签筛选投递", menu_filter),
    ("修改某条记录进度", menu_update),
    ("删除记录", menu_delete),
    ("数据统计汇总", menu_statistics),
    ("导出全部数据为Excel", menu_export_excel),
    ("图片OCR识别导入岗位", menu_ocr),
    ("岗位JD适配度打分", menu_jd_score),
    ("退出程序", menu_exit),
]


def show_menu():
    """打印主菜单"""
    os.system("cls" if os.name == "nt" else "clear")
    print()
    print("  " + "=" * 54)
    print("    秋招求职进度管理工具 v1.0")
    print("  " + "=" * 54)
    print()
    for i, (label, _) in enumerate(MENU_ITEMS, 1):
        print(f"    [{i}] {label}")
    print()


def main():
    """主程序入口：循环展示菜单直到用户退出"""
    while True:
        try:
            show_menu()
            choice = input_int(f"  请输入功能编号 (1-{len(MENU_ITEMS)})",
                               min_v=1, max_v=len(MENU_ITEMS))
            if choice is None:
                continue
            MENU_ITEMS[choice - 1][1]()
            if choice != len(MENU_ITEMS):
                input()
        except KeyboardInterrupt:
            menu_exit()
        except EOFError:
            menu_exit()
        except Exception as e:
            print(f"  [错误] 程序异常: {e}")
            print("  请检查输入后重试。")
            input()


if __name__ == "__main__":
    main()