"""Run D6: python -m tests.run. Expected failures are confirmed current bugs."""
import sys
import unittest


def main():
    suite = unittest.defaultTestLoader.discover("tests", pattern="test_*.py", top_level_dir=".")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped) - len(result.expectedFailures) - len(result.unexpectedSuccesses)
    print("PASS=%d EXPECTED_FAIL_CONFIRMED_BUG=%d MANUAL_ACCEPTANCE_REQUIRED=see tests/ACCEPTANCE.md" %
          (passed, len(result.expectedFailures)))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
