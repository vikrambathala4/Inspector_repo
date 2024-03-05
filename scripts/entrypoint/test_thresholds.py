import json
import unittest

import thresholds


class TestThresholds(unittest.TestCase):

    def test_print_vulnerabilities(self):
        with open("test_data/scan.json", "r") as f:
            data = json.load(f)
            thresholds.print_vulnerabilities(data)


if __name__ == '__main__':
    unittest.main()
