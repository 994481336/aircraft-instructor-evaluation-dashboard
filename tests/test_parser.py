from __future__ import annotations

from io import BytesIO
import unittest

from openpyxl import Workbook

from data_loader import FAMILY_BOEING, parse_workbook


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
