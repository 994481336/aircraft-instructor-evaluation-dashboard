from __future__ import annotations

import unittest

import pandas as pd

from analysis import score_distribution, subject_loss, summary_metrics, top_deductions
from normalizer import normalize
from data_loader import ParsedBundle


class ScoringTests(unittest.TestCase):
    def setUp(self):
        ratings = pd.DataFrame([
            {
                "记录ID": "1", "姓名": "甲", "所属单位": "单位A", "机型类别": "波音", "模拟机总分": 92,
                "计算模拟机总分": 92, "训前总分": 95, "失分": 8, "总扣分": -8, "数据质量": "正常",
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
        self.assertEqual(int(distribution["人数"].sum()), 1)


if __name__ == "__main__":
    unittest.main()
