from __future__ import annotations

import unittest

import pandas as pd

from analysis import score_distribution, score_text, subject_loss, summary_metrics, top_deductions, type_briefing_segments
from company import canonical_company
from normalizer import normalize
from data_loader import ParsedBundle


class ScoringTests(unittest.TestCase):
    def setUp(self):
        ratings = pd.DataFrame([
            {
                "记录ID": "1", "姓名": "甲", "所属单位": "单位A", "机型类别": "波音", "模拟机总分": 92,
                "科目小计合计": 92, "训前总分": 95, "失分": 8, "总扣分": -8, "数据质量": "正常",
                "模拟机科目得分": {"科目一": 20, "科目二": 19, "科目三": 18}, "训前科目得分": {},
            },
        ])
        deductions = pd.DataFrame([
            {"记录ID": "1", "姓名": "甲", "科目名称": "科目一", "评分项目": "决策偏差", "扣分标准": "-2分", "扣分值": -2, "失分": 2, "规则状态": "已识别"},
            {"记录ID": "1", "姓名": "甲", "科目名称": "科目二", "评分项目": "下滑线", "扣分标准": "-6分", "扣分值": -6, "失分": 6, "规则状态": "已识别"},
        ])
        self.data = normalize(ParsedBundle(pd.DataFrame(), ratings, deductions, pd.DataFrame()))

    def test_metrics_and_loss_rank(self):
        metrics = summary_metrics(self.data.ratings, self.data.deductions)
        self.assertEqual(metrics["评估人数"], 1)
        self.assertEqual(metrics["平均模拟机得分"], 92)
        self.assertEqual(metrics["扣分事件"], 2)
        self.assertEqual(top_deductions(self.data.deductions, 1).iloc[0]["总失分"], 6)
        self.assertEqual(subject_loss(self.data.deductions).iloc[0]["科目名称"], "科目二")

    def test_distribution_has_bins(self):
        distribution = score_distribution(self.data.ratings)
        self.assertEqual(int(distribution["评分记录数"].sum()), 1)

    def test_briefing_distinguishes_people_from_scoring_records(self):
        rows = pd.DataFrame([
            {"记录ID": "1", "姓名": "甲", "所属单位": "东航", "机型": "A320", "机型类别": "空客", "模拟机总分": 70.0},
            {"记录ID": "2", "姓名": "甲", "所属单位": "东航", "机型": "A320", "机型类别": "空客", "模拟机总分": 80.0},
            {"记录ID": "3", "姓名": "乙", "所属单位": "东航", "机型": "A320", "机型类别": "空客", "模拟机总分": 90.0},
        ])
        segment = type_briefing_segments(rows)[0][1]
        metrics = summary_metrics(segment, pd.DataFrame())
        self.assertEqual(metrics["评估人数"], 2)
        self.assertEqual(metrics["评分记录"], 3)
        self.assertEqual(metrics["平均模拟机得分"], 80.0)
        self.assertEqual(int(score_distribution(segment)["评分记录数"].sum()), 3)

    def test_briefing_is_not_limited_to_eastern_airlines(self):
        rows = pd.DataFrame([
            {"记录ID": "1", "姓名": "甲", "所属单位": "东航飞行总队", "机型": "C919", "机型类别": "国产民机", "模拟机总分": 84.0},
            {"记录ID": "2", "姓名": "乙", "所属单位": "东航飞行总队", "机型": "C919", "机型类别": "国产民机", "模拟机总分": 84.5},
            {"记录ID": "3", "姓名": "丙", "所属单位": "东航", "机型": "A320", "机型类别": "空客", "模拟机总分": 91.0},
            {"记录ID": "4", "姓名": "丁", "所属单位": "山东航空", "机型": "B737", "机型类别": "波音", "模拟机总分": 88.0},
        ])
        segments = type_briefing_segments(rows)
        self.assertEqual([name for name, _ in segments], ["一、国产民机 C919", "二、空客机型", "三、波音机型"])
        self.assertEqual(len(segments[0][1]), 2)
        self.assertEqual(score_text(segments[0][1]["模拟机总分"].mean()), "84.3")

    def test_company_aliases_are_grouped_without_assuming_affiliates(self):
        aliases = {
            "东航": "东航", "东航北分": "东航", "东航北京分公司": "东航",
            "厦航": "厦门航空", "厦门航空有限公司": "厦门航空",
            "山航": "山东航空", "山东航空股份有限公司": "山东航空",
            "福航": "福州航空", "福州航空": "福州航空",
            "上海吉祥航空股份有限公司": "吉祥航空", "吉祥航空": "吉祥航空",
            "青岛航空股份有限公司": "青岛航空", "青岛航空": "青岛航空",
            "上航": "上海航空",
        }
        for raw_name, expected in aliases.items():
            self.assertEqual(canonical_company(raw_name), expected)
        self.assertNotEqual(canonical_company("上航"), canonical_company("东航"))


if __name__ == "__main__":
    unittest.main()
