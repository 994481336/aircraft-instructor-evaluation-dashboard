from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
import unittest

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
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


class PersonAverageUiTests(unittest.TestCase):
    def test_person_weighted_dashboard_and_source_record_selection(self):
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
        self.assertEqual(charts["overview_score_distribution"]["layout"]["xaxis"]["title"]["text"], "评估人数")
        self.assertEqual(charts["overview_unit_average"]["data"][0]["y"], ["东航"])
        person_select = next(item for item in at.selectbox if item.label == "选择教员")
        self.assertEqual(len(person_select.options), 2)
        original_select = next(item for item in at.selectbox if item.label == "查看原始评分记录")
        self.assertEqual(len(original_select.options), 3)
        original_select.set_value(2).run(timeout=60)
        self.assertFalse(at.exception)
        current = next(item.value for item in at.markdown if 'class="metric-label">本次模拟机得分' in item.value)
        self.assertIn("80.0", current)
        personal = next(item.value for item in at.markdown if 'class="metric-label">个人模拟机均分' in item.value)
        self.assertIn("70.0", personal)
        next(item for item in at.selectbox if item.label == "技术等级").set_value("型别教员").run(timeout=60)
        self.assertFalse(at.exception)
        next(item for item in at.radio if item.label == "展示模式").set_value("按具体机型").run(timeout=60)
        next(item for item in at.selectbox if item.label == "具体机型").set_value("A320").run(timeout=60)
        self.assertFalse(at.exception)
        next(item for item in at.selectbox if item.label == "公司").set_value("东航").run(timeout=60)
        self.assertFalse(at.exception)
        metrics = next(item.value for item in at.markdown if 'class="metric-label">人员平均分' in item.value)
        self.assertIn("80.0", metrics)


if __name__ == "__main__":
    unittest.main()
