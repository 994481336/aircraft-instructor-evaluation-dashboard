from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import patch

from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest

from test_parser import sample_workbook


def unequal_scores_workbook() -> bytes:
    workbook = load_workbook(BytesIO(sample_workbook("A320")))
    sheet = workbook["评估数据"]
    template = [cell.value for cell in sheet[2]]
    sheet.delete_rows(2)
    for index, (name, unit, score) in enumerate([
        ("张三", "东航", 60), ("张三", "东航北分", 70),
        ("张三", "东航", 80), ("李四", "东航", 90),
    ], start=1):
        row = template.copy()
        row[1], row[2], row[4], row[9], row[15] = f"anonymous-{index}", name, unit, f"评估员{index}", score
        row[10], row[11] = index * 2, index * 20
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


class PersonAverageUiTests(unittest.TestCase):
    def test_live_update_with_stale_analysis_module_still_starts_and_averages(self):
        legacy = ModuleType("analysis")
        # A live Streamlit worker can keep the pre-person-aggregation module.
        # New UI imports must not depend on newly added names in that object.
        with patch.dict(sys.modules, {"analysis": legacy, "instructor_statistics": ModuleType("instructor_statistics")}):
            self.assertFalse(hasattr(legacy, "company_summary"))
            with self.assertRaises(ImportError):
                exec("from analysis import company_summary", {})
            at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
            self.assertFalse(at.exception)
            at.get("file_uploader")[0].upload("匿名热更新测试.xlsx", unequal_scores_workbook()).run(timeout=60)
            self.assertFalse(at.exception)
            metrics = next(item.value for item in at.markdown if 'class="metric-label">人员平均分' in item.value)
            self.assertIn("80.0", metrics)
            people = next(table.value for table in at.dataframe if "个人模拟机均分" in table.value.columns)
            self.assertEqual(len(people), 2)

    def test_person_weighted_dashboard_filters_and_deleted_pages(self):
        at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
        at.get("file_uploader")[0].upload("匿名空客测试.xlsx", unequal_scores_workbook()).run(timeout=60)
        self.assertFalse(at.exception)
        people = next(table.value for table in at.dataframe if "个人模拟机均分" in table.value.columns)
        self.assertEqual(len(people), 2)
        self.assertEqual(people.set_index("姓名").loc["张三", "个人模拟机均分"], 70)
        self.assertEqual(people["评分记录"].sum(), 4)
        metrics = next(item.value for item in at.markdown if 'class="metric-label">人员平均分' in item.value)
        self.assertIn("80.0", metrics)
        charts = {chart.proto.id.rsplit("-", 1)[-1]: json.loads(chart.proto.spec) for chart in at.get("plotly_chart")}
        self.assertEqual(charts["overview_score_distribution_simulator"]["layout"]["xaxis"]["title"]["text"], "评估人数")
        self.assertEqual(charts["overview_unit_average_simulator"]["data"][0]["y"], ["东航"])
        self.assertEqual([tab.label for tab in at.tabs], ["机型简报", "总览驾驶舱"])
        self.assertFalse(any(item.label in {"选择教员", "选择科目下钻", "查看原始评分记录"} for item in at.selectbox))
        next(item for item in at.selectbox if item.label == "技术等级").set_value("型别教员").run(timeout=60)
        self.assertFalse(at.exception)
        next(item for item in at.radio if item.label == "展示模式").set_value("按具体机型").run(timeout=60)
        next(item for item in at.selectbox if item.label == "具体机型").set_value("A320").run(timeout=60)
        self.assertFalse(at.exception)
        next(item for item in at.selectbox if item.label == "公司").set_value("东航").run(timeout=60)
        self.assertFalse(at.exception)
        metrics = next(item.value for item in at.markdown if 'class="metric-label">人员平均分' in item.value)
        self.assertIn("80.0", metrics)

    def test_briefing_mode_has_independent_scores_subjects_and_exports(self):
        at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
        at.get("file_uploader")[0].upload("匿名双评分测试.xlsx", unequal_scores_workbook()).run(timeout=60)
        next(item for item in at.radio if item.label == "分析内容").set_value("训前讲评").run(timeout=60)
        self.assertFalse(at.exception)
        metrics = next(item.value for item in at.markdown if 'class="metric-label">人员平均分' in item.value)
        self.assertIn("60.0", metrics)
        people = next(table.value for table in at.dataframe if "个人讲评均分" in table.value.columns)
        self.assertEqual(people.set_index("姓名").loc["张三", "个人讲评均分"], 40)
        self.assertNotIn("个人模拟机均分", people.columns)
        self.assertNotIn("个人平均失分", people.columns)
        subject = next(table.value for table in at.dataframe if "科目名称" in table.value.columns and "平均分" in table.value.columns)
        self.assertEqual(subject.iloc[0]["平均分"], 6)
        charts = {chart.proto.id.rsplit("-", 1)[-1]: json.loads(chart.proto.spec) for chart in at.get("plotly_chart")}
        self.assertIn("overview_score_distribution_briefing", charts)
        self.assertNotIn("overview_top_deductions", charts)
        self.assertTrue(all("模拟机" not in chart["layout"]["title"]["text"] for chart in charts.values()))
        self.assertTrue(all("讲评" in button.label for button in at.get("download_button")))
        records = next(table.value for table in at.dataframe if "训前总分" in table.value.columns)
        self.assertEqual(records["训前总分"].tolist(), [20, 40, 60, 80])
        self.assertNotIn("模拟机总分", records.columns)
        next(item for item in at.radio if item.label == "展示模式").set_value("按具体机型").run(timeout=60)
        next(item for item in at.selectbox if item.label == "具体机型").set_value("A320").run(timeout=60)
        next(item for item in at.selectbox if item.label == "公司").set_value("东航").run(timeout=60)
        self.assertFalse(at.exception)
        next(item for item in at.radio if item.label == "分析内容").set_value("模拟机表现").run(timeout=60)
        self.assertFalse(at.exception)
        metrics = next(item.value for item in at.markdown if 'class="metric-label">人员平均分' in item.value)
        self.assertIn("80.0", metrics)

    def test_missing_briefing_does_not_fall_back_to_simulator(self):
        workbook = load_workbook(BytesIO(unequal_scores_workbook()))
        for row in workbook["评估数据"].iter_rows(min_row=2):
            row[10].value = None
            row[11].value = None
        output = BytesIO()
        workbook.save(output)
        at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
        at.get("file_uploader")[0].upload("无讲评测试.xlsx", output.getvalue()).run(timeout=60)
        next(item for item in at.radio if item.label == "分析内容").set_value("训前讲评").run(timeout=60)
        self.assertFalse(at.exception)
        self.assertEqual(len(at.get("plotly_chart")), 0)
        self.assertTrue(any("不使用另一套分数替代" in item.value for item in at.info))


if __name__ == "__main__":
    unittest.main()
