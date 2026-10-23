from __future__ import annotations

import unittest

import pandas as pd

from aircraft import canonical_model
from analysis import type_briefing_segments
from data_loader import ParsedBundle
from normalizer import normalize


class AircraftGroupingTests(unittest.TestCase):
    def test_briefing_numbers_only_visible_categories(self):
        rows = pd.DataFrame([
            {"机型": "A320", "机型类别": "空客"},
            {"机型": "B787", "机型类别": "波音"},
            {"机型": "X999", "机型类别": "未识别"},
        ])
        self.assertEqual([title for title, _ in type_briefing_segments(rows.iloc[[0]])], ["一、空客机型"])
        self.assertEqual([title for title, _ in type_briefing_segments(rows.iloc[[1]])], ["一、波音机型"])
        self.assertEqual([title for title, _ in type_briefing_segments(rows.iloc[[2]])], ["一、未识别类别"])
        self.assertEqual([title for title, _ in type_briefing_segments(rows.iloc[:2])], ["一、空客机型", "二、波音机型"])
        self.assertEqual([title for title, _ in type_briefing_segments(rows)], ["一、空客机型", "二、波音机型", "三、未识别类别"])

    def test_model_sections_use_continuous_chinese_numbers(self):
        rows = pd.DataFrame([{"统计机型": f"机型{i:02}", "机型类别": "波音"} for i in range(1, 22)])
        sections = type_briefing_segments(rows, "按具体机型")
        self.assertEqual(sections[0][0], "一、机型01")
        self.assertEqual(sections[9][0], "十、机型10")
        self.assertEqual(sections[10][0], "十一、机型11")
        self.assertEqual(sections[19][0], "二十、机型20")
        self.assertEqual(sections[20][0], "二十一、机型21")
        self.assertEqual(type_briefing_segments(rows.iloc[[20]], "按具体机型")[0][0], "一、机型21")

    def test_model_aliases_and_unspecified_values(self):
        for raw in ("B737", "B737-800", "737-800", "B738", "B737 MAX8"):
            self.assertEqual(canonical_model(raw, "波音"), "B737")
        for raw in ("B787", "波音787", "787"):
            self.assertEqual(canonical_model(raw, "波音"), "B787")
        self.assertEqual(canonical_model("777", "波音"), "B777")
        self.assertEqual(canonical_model("A320-200", "空客"), "A320")
        self.assertEqual(canonical_model("A330", "空客"), "A330")
        self.assertEqual(canonical_model("空客", "空客"), "空客（机型未明确）")
        self.assertEqual(canonical_model("ARJ", "国产民机"), "国产民机（机型未明确）")
        self.assertEqual(canonical_model("787", "未识别"), "787")

    def test_both_modes_keep_all_records_and_separate_models(self):
        rows = pd.DataFrame([
            {"记录ID": "1", "机型": "B737-800", "机型类别": "波音"},
            {"记录ID": "2", "机型": "B738", "机型类别": "波音"},
            {"记录ID": "3", "机型": "波音787", "机型类别": "波音"},
            {"记录ID": "4", "机型": "C919", "机型类别": "国产民机"},
            {"记录ID": "5", "机型": "C909", "机型类别": "国产民机"},
            {"记录ID": "6", "机型": "空客", "机型类别": "空客"},
        ])
        categories = type_briefing_segments(rows)
        models = type_briefing_segments(rows, "按具体机型")
        self.assertEqual(sum(len(part) for _, part in categories), len(rows))
        self.assertEqual(sum(len(part) for _, part in models), len(rows))
        self.assertEqual(len(next(part for title, part in categories if title.endswith("国产民机"))), 2)
        model_parts = {title.split("、", 1)[1]: part for title, part in models}
        self.assertEqual(len(model_parts["B737"]), 2)
        self.assertEqual(len(model_parts["B787"]), 1)
        self.assertIn("空客（机型未明确）", model_parts)

    def test_normalization_keeps_source_and_aligns_deduction_filter(self):
        row = {"记录ID": "1", "机型": "737-800", "机型类别": "波音"}
        data = normalize(ParsedBundle(pd.DataFrame(), pd.DataFrame([row]), pd.DataFrame([row]), pd.DataFrame()))
        self.assertEqual(data.ratings.iloc[0]["机型"], "737-800")
        self.assertEqual(data.ratings.iloc[0]["统计机型"], "B737")
        self.assertEqual(data.deductions.iloc[0]["统计机型"], "B737")


if __name__ == "__main__":
    unittest.main()
