from __future__ import annotations

import unittest

import pandas as pd

from normalizer import ensure_columns


class QualityTests(unittest.TestCase):
    def test_missing_columns_are_filled(self):
        data = ensure_columns(pd.DataFrame({"姓名": ["甲"]}), {"机型": "未识别机型", "数据质量": "待复核"})
        self.assertEqual(data.iloc[0]["机型"], "未识别机型")
        self.assertEqual(data.iloc[0]["数据质量"], "待复核")


if __name__ == "__main__":
    unittest.main()
