import sys
from types import ModuleType
import unittest
from unittest.mock import patch

import statistics_runtime


class StatisticsRuntimeTests(unittest.TestCase):
    def test_ignores_cached_named_module_and_reuses_exact_source_version(self):
        with patch.dict(sys.modules, {"instructor_statistics": ModuleType("instructor_statistics")}):
            current = statistics_runtime.load_statistics()
            self.assertTrue(callable(current.company_summary))
            self.assertIs(current, statistics_runtime.load_statistics())

    def test_changed_source_gets_fresh_module_in_same_process(self):
        versions = []
        try:
            for value in (1, 2):
                with patch.object(statistics_runtime.Path, "read_bytes", return_value=f"runtime_test_version = {value}\n".encode()):
                    module = statistics_runtime.load_statistics()
                    versions.append(module)
                    self.assertEqual(module.runtime_test_version, value)
            self.assertNotEqual(versions[0].__name__, versions[1].__name__)
        finally:
            for module in versions:
                sys.modules.pop(module.__name__, None)


if __name__ == "__main__":
    unittest.main()
