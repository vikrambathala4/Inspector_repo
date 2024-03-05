import json
import logging
import os
import re
import unittest

import inspector_parser


def get_inspector_json(file):
    inspector_json = ""
    with open(file, "r") as f:
        inspector_json = json.load(f)
    return inspector_json


class TestInspectorParser(unittest.TestCase):

    def test_get_summarized_findings(self):
        test_files = self.get_inspector_scan_file_paths()
        for file in test_files:
            with open(file, "r") as f:
                inspector_scan = json.load(f)
                findings = inspector_parser.get_summarized_findings(inspector_scan)
                if findings == None:
                    continue

            inspector_parser.print_summarized_findings_as_table(findings)
            #inspector_parser.print_summarized_findings(findings)

    def get_inspector_scan_file_paths(self):
        test_data = os.path.join("test_data", "inspector_scans")
        files = os.listdir(test_data)
        test_files = []
        for file in files:
            file = os.path.join(test_data, file)
            test_files.append(file)
        return test_files

    def test_get_findings(self):
        test_files = self.get_inspector_scan_file_paths()
        for file in test_files:
            with open(file, "r") as f:
                inspector_scan = json.load(f)
                findings = inspector_parser.get_findings(inspector_scan)
                self.assertIsNotNone(findings)
                self.assertEqual(findings["specVersion"], "1.5")
                self.assertEqual(findings["bomFormat"], "CycloneDX")

                # every CycloneDX serial number must conform to this REGEX
                # https://cyclonedx.org/docs/1.5/json/#serialNumber
                serial_pattern = r'^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                self.assertTrue(bool(re.match(serial_pattern, findings["serialNumber"])))

    def test_get_vulnerabilities(self):
        test_files = self.get_inspector_scan_file_paths()
        for file in test_files:
            with open(file, "r") as f:
                inspector_scan = json.load(f)
                findings = inspector_parser.get_findings(inspector_scan)
                vulns = inspector_parser.get_vulnerabilities(findings)
                if vulns is not None:
                    for v in vulns:
                        self.assertTrue(len(v["id"]) > 0)
                        self.assertTrue(len(v["bom-ref"]) > 0)


if __name__ == '__main__':
    unittest.main()
