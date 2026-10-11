from __future__ import annotations

from io import BytesIO
import unittest

from openpyxl import Workbook, load_workbook

from data_loader import FAMILY_AIRBUS, FAMILY_BOEING, META_ALIASES, find_column, negative_parts, parse_workbook


def sample_workbook(model: str = "B747") -> bytes:
    workbook = Workbook()
    workbook.active.title = "工作表1"
    sheet = workbook.create_sheet("评估数据")
    headers = [
        "提交时间", "填写ID", "被评估人姓名", "评估日期", "所属单位", "机型", "技术等级",
        "总飞行时间", "本机型经历时间", "评估员姓名", "单科总得分", "教员双盲训前讲评总得分",
        "决策偏差", "喊话偏差", "单科总得分2", "教员双盲模拟机评估总得分",
    ]
    sheet.append(headers)
    sheet.append([
        "2026-08-21", "id-1", "测试教员", "2026-08-20", "测试单位", "B747", "型别教员",
        8000, 1600, "测试评估员", 20, 95, "无异常（不扣分）", "未喊出中断（-2分）", 18, 98,
    ])
    output = BytesIO()
    workbook.save(output)
    sheet.cell(row=2, column=6).value = model
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def boeing_layout_workbook() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    headers = [
        "提交时间", "填写ID", "答题时间(秒)", "提交者", "被评估人姓名", "评估日期", "所属单位", "机型", "技术等级",
        "总飞行时间", "本机型经历时间", "评估员姓名", "决策偏差", "综合考评", "其他",
        "讲评要点1：中断决策要点（5分）", "讲评要点2：口令与分工（5分）", "讲评要点3：中断动作要点（5分）", "讲评要点4：中断起飞对飞机系统的影响（5分）",
        "单科总得分", "教员双盲训前讲评总得分", "教员双盲模拟机评估总得分", "单科总得分2", "拉平高修正动作", "单科总得分3",
    ]
    sheet.append(headers)
    sheet.append([
        "2026-08-21", "id-b", 100, "测试提交者", "波音教员", "2026-08-20", "测试单位", "B747", "型别教员",
        8000, 1600, "测试评估员", "三红一白（-1分）", "无异常（不扣分）", "技术性复飞减20",
        "两项均有（+5分）", "两项均有（+5分）", "两项均有（+5分）", "两项均有（+5分）", 20, 95, 80, 15,
        "接地姿态控制不当（-2分）", 18,
    ])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


class ParserTests(unittest.TestCase):
    def test_reordered_airbus_reads_both_blocks_with_late_metadata(self):
        workbook = Workbook()
        sheet = workbook.active
        columns = {
            1: "提交时间", 2: "填写ID", 3: "答题时间(秒)", 4: "被评估人姓名",
            5: "评估日期", 6: "所属单位", 7: "技术等级",
            8: "总飞行时间(已删除)", 9: "本机型经历时间(已删除)", 10: "评估员姓名",
            11: "决策偏差", 12: "喊话偏差", 39: "仪表转目视飞行", 57: "综合考评",
            58: "总扣分(已删除)", 59: "总飞行时间", 60: "本机型经历时间",
            61: "提交者", 62: "机型", 63: "备注：", 71: "其他",
            72: "讲评要点1：中断决策要点（5分）", 76: "单科总得分",
            81: "单科总得分12", 86: "单科总得分10", 89: "单科总得分11",
            92: "单科总得分5", 93: "教员双盲训前讲评总得分",
            94: "单科总扣分(已删除)", 98: "单科总得分7",
            99: "教员双盲模拟机评估总得分", 100: "单科总得分6",
            101: "单科总得分2", 102: "单科总得分3", 103: "单科总得分4",
            104: "拉平高修正动作", 113: "复飞决策与程序", 114: "单科总得分8",
        }
        sheet.append([columns.get(i, f"未命名列_{i}") for i in range(1, 115)])
        values = {
            2: "anonymous-1", 3: 100, 4: "测试教员", 5: "2026-10-11", 6: "测试单位",
            7: "型别教员", 8: -999, 9: -999, 10: "测试评估员",
            11: "无异常（不扣分）", 12: "未喊出中断（-4分）",
            39: "三红一白（-1分）,无异常（不扣分）", 57: "技术性复飞（-10分）",
            58: -999, 59: 8000, 60: 1600, 61: "提交者-9", 62: "A320",
            63: "-99分", 71: "无异常（不扣分）", 72: "两项均有（+5分）",
            93: 95, 94: -999, 99: 78,
            104: "无异常（不扣分）,未及时修正高度（-2分）", 113: "未及时复飞（-3分）",
        }
        values.update({i: 20 for i in (76, 81, 86, 89, 92)})
        values.update({i: 13 for i in (98, 100, 101, 102, 103, 114)})
        sheet.append([values.get(i) for i in range(1, 115)])
        output = BytesIO()
        workbook.save(output)
        _, ratings, deductions, _, _ = parse_workbook(output.getvalue(), "空客导出测试.xlsx")
        self.assertEqual(ratings.iloc[0]["机型"], "A320")
        self.assertEqual(ratings.iloc[0]["模拟机总分"], 78)
        self.assertEqual(ratings.iloc[0]["训前总分"], 95)
        self.assertEqual(len(ratings.iloc[0]["模拟机科目得分"]), 6)
        self.assertEqual(len(ratings.iloc[0]["训前科目得分"]), 5)
        self.assertEqual(ratings.iloc[0]["失分"], 20)
        self.assertEqual(set(deductions["原始列号"]), {12, 39, 57, 104, 113})
        self.assertEqual(deductions["失分"].sum(), 20)

    def test_mixed_no_deduction_text_keeps_explicit_negative_parts(self):
        cases = {
            "无异常（不扣分）": [],
            "三红一白（-1分）,无异常（不扣分）": [-1.0],
            "无异常（不扣分）；技术性复飞（－10分）": [-10.0],
            "无异常（不扣分）,偏差（−1.5分）,其他（-2分）": [-1.5, -2.0],
            "无异常（不扣分）,技术性复飞减20": [-20.0],
            "两项均有（+5分）": [],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(negative_parts(text), expected)

    def test_model_at_bj_overrides_earlier_deleted_metadata(self):
        workbook = load_workbook(BytesIO(sample_workbook()))
        sheet = workbook["评估数据"]
        sheet.cell(row=1, column=6).value = "机型(已删除)"
        sheet.cell(row=1, column=9).value = "本机型经历时间(已删除)"
        sheet.cell(row=1, column=62).value = "机型"
        sheet.cell(row=2, column=62).value = "A330"
        output = BytesIO()
        workbook.save(output)
        _, ratings, deductions, _, _ = parse_workbook(output.getvalue(), "导出表.xlsx")
        self.assertEqual(ratings.iloc[0]["机型"], "A330")
        self.assertEqual(ratings.iloc[0]["机型类别"], FAMILY_AIRBUS)
        self.assertEqual(set(deductions["机型"]), {"A330"})
        self.assertEqual(ratings.iloc[0]["模拟机总分"], 98)
        self.assertEqual(ratings.iloc[0]["失分"], 2)

    def test_model_header_does_not_match_experience_time(self):
        self.assertIsNone(find_column(["本机型经历时间(已删除)", "本机型经历时间"], META_ALIASES["机型"]))
        self.assertEqual(find_column(["本机型经历时间", "飞机型号"], META_ALIASES["机型"]), "飞机型号")

    def test_skips_blank_sheet_and_extracts_deduction(self):
        summary, ratings, deductions, quality, columns = parse_workbook(sample_workbook(), "波音测试.xlsx")
        self.assertEqual(summary["工作表"], "评估数据")
        self.assertEqual(summary["评估人数"], 1)
        self.assertEqual(ratings.iloc[0]["机型类别"], FAMILY_BOEING)
        self.assertEqual(ratings.iloc[0]["失分"], 2)
        self.assertNotIn("科目小计合计", ratings.columns)
        self.assertEqual(len(deductions), 1)
        self.assertEqual(deductions.iloc[0]["规则状态"], "已识别")
        self.assertFalse(quality.empty)
        self.assertGreater(len(columns), 10)

    def test_unknown_model_is_flagged(self):
        payload = sample_workbook("X999")
        summary, ratings, _, quality, _ = parse_workbook(payload, "未知机型.xlsx")
        self.assertEqual(ratings.iloc[0]["机型类别"], "未识别")
        self.assertIn("未识别机型规则", quality.iloc[0]["问题"])

    def test_boeing_layout_reads_simulator_deductions_before_and_after_briefing(self):
        summary, ratings, deductions, quality, _ = parse_workbook(boeing_layout_workbook(), "波音布局测试.xlsx")
        self.assertEqual(summary["评估人数"], 1)
        self.assertEqual(ratings.iloc[0]["失分"], 23)
        self.assertEqual(int((deductions["失分"] > 0).sum()), 3)
        self.assertEqual(set(deductions["科目名称"]), {"模拟机表现"})
        self.assertTrue(quality.empty or (quality["状态"] == "正常").all())


if __name__ == "__main__":
    unittest.main()
