from __future__ import annotations

import unittest

import pandas as pd

from analysis import company_summary, person_score_frame, score_distribution, subject_summary, summary_metrics, type_briefing, unit_summary


def ratings() -> pd.DataFrame:
    return pd.DataFrame([
        {"记录ID": "1", "姓名": "张三", "所属单位": "东航", "机型": "B737", "机型类别": "波音", "模拟机总分": 60, "训前总分": 70, "失分": 40, "模拟机科目得分": {"科目一": 8}},
        {"记录ID": "2", "姓名": "张三", "所属单位": "东航北分", "机型": "B737", "机型类别": "波音", "模拟机总分": 70, "训前总分": 80, "失分": 30, "模拟机科目得分": {"科目一": 10}},
        {"记录ID": "3", "姓名": "张三", "所属单位": "东航", "机型": "B737", "机型类别": "波音", "模拟机总分": 80, "训前总分": 90, "失分": 20, "模拟机科目得分": {"科目一": 12}},
        {"记录ID": "4", "姓名": "李四", "所属单位": "东航", "机型": "B737", "机型类别": "波音", "模拟机总分": 90, "训前总分": 100, "失分": 10, "模拟机科目得分": {"科目一": 20}},
    ])


class PersonAverageTests(unittest.TestCase):
    def test_unequal_record_counts_produce_equal_person_weights(self):
        source = ratings()
        before = source.copy(deep=True)
        people = person_score_frame(source).set_index("姓名")
        self.assertEqual(people.loc["张三", "模拟机总分"], 70)
        self.assertEqual(people.loc["张三", "评分记录"], 3)
        self.assertEqual(people.loc["李四", "模拟机总分"], 90)
        company = company_summary(source).iloc[0]
        self.assertEqual(company["平均分"], 80)
        self.assertEqual(company["评估人数"], 2)
        self.assertEqual(company["评分记录"], 4)
        metrics = summary_metrics(source, pd.DataFrame())
        self.assertEqual(metrics["平均模拟机得分"], 80)
        self.assertEqual(metrics["最高分"], 90)
        self.assertEqual(metrics["最低分"], 70)
        self.assertEqual(metrics["平均失分"], 20)
        self.assertEqual(metrics["评分记录"], 4)
        distribution = score_distribution(source).set_index("分数区间")
        self.assertEqual(distribution["评估人数"].sum(), 2)
        self.assertEqual(distribution.loc["<80", "评估人数"], 1)
        self.assertEqual(distribution.loc["90-94", "评估人数"], 1)
        brief = type_briefing(source).iloc[0]
        self.assertEqual(brief["平均模拟机得分"], 80)
        self.assertEqual(brief["平均训前讲评"], 90)
        subject = subject_summary(source).iloc[0]
        self.assertEqual(subject["平均分"], 15)
        self.assertEqual(subject["评估人数"], 2)
        # Raw units get their own person averages, not company averages of units.
        units = unit_summary(source).set_index("所属单位")
        self.assertEqual(units.loc["东航", "平均分"], 80)
        pd.testing.assert_frame_equal(source, before)

    def test_same_name_in_different_companies_is_not_merged(self):
        source = pd.DataFrame([
            {"姓名": "同名", "所属单位": "东航", "模拟机总分": 60},
            {"姓名": "同名", "所属单位": "厦航", "模拟机总分": 90},
        ])
        self.assertEqual(len(person_score_frame(source)), 2)
        self.assertEqual(summary_metrics(source, pd.DataFrame())["评估人数"], 2)
        self.assertEqual(company_summary(source)["平均分"].tolist(), [90, 60])

    def test_missing_scores_are_excluded_but_real_zero_is_preserved(self):
        source = pd.DataFrame([
            {"姓名": "甲", "所属单位": "东航", "模拟机总分": 0},
            {"姓名": "甲", "所属单位": "东航", "模拟机总分": "缺失"},
            {"姓名": "乙", "所属单位": "东航", "模拟机总分": 100},
            {"姓名": "丙", "所属单位": "东航", "模拟机总分": None},
        ])
        metrics = summary_metrics(source, pd.DataFrame())
        self.assertEqual(metrics["平均模拟机得分"], 50)
        self.assertEqual(metrics["评估人数"], 3)
        self.assertEqual(metrics["有效评分人数"], 2)
        self.assertEqual(score_distribution(source)["评估人数"].sum(), 2)
        source["模拟机总分"] = None
        self.assertIsNone(summary_metrics(source, pd.DataFrame())["平均模拟机得分"])
        self.assertEqual(score_distribution(source)["评估人数"].sum(), 0)

    def test_model_filter_is_applied_before_person_averaging(self):
        source = ratings()
        source = pd.concat([source, pd.DataFrame([{
            "记录ID": "5", "姓名": "张三", "所属单位": "东航", "机型": "B787", "机型类别": "波音", "模拟机总分": 10,
        }])], ignore_index=True)
        self.assertEqual(company_summary(source[source["机型"] == "B737"]).iloc[0]["平均分"], 80)
        self.assertEqual(company_summary(source[source["机型"] == "B787"]).iloc[0]["平均分"], 10)

    def test_fractional_person_scores_are_not_rounded_before_binning(self):
        source = pd.DataFrame([
            {"姓名": "甲", "所属单位": "东航", "模拟机总分": 79.99},
            {"姓名": "甲", "所属单位": "东航", "模拟机总分": 80},
            {"姓名": "乙", "所属单位": "东航", "模拟机总分": 100.005},
        ])
        self.assertAlmostEqual(person_score_frame(source).iloc[0]["模拟机总分"], 79.995)
        distribution = score_distribution(source).set_index("分数区间")
        self.assertEqual(distribution.loc["<80", "评估人数"], 1)
        self.assertEqual(distribution.loc[">100", "评估人数"], 1)
        self.assertAlmostEqual(company_summary(source).iloc[0]["平均分"], 90)

    def test_empty_frames_have_stable_schema(self):
        source = pd.DataFrame()
        self.assertTrue(person_score_frame(source).empty)
        self.assertTrue(company_summary(source).empty)
        self.assertTrue(subject_summary(source).empty)
        self.assertTrue(score_distribution(source).empty)
        self.assertIsNone(summary_metrics(source, pd.DataFrame())["平均模拟机得分"])


if __name__ == "__main__":
    unittest.main()
