import json
import os
import unittest

from entrypoint import pkg_vuln


class TestMarkdown(unittest.TestCase):

    def test_json_to_csv(self):
        test_dir = "tests/test_data/scans/"
        file_list = os.listdir(test_dir)
        for file in file_list:
            path = os.path.join(test_dir, file)

            inspector_scan_json = {}
            with open(path, 'r') as f:
                inspector_scan_json = json.load(f)

            vulns = pkg_vuln.vulns_to_obj(inspector_scan_json)
            if not vulns:
                continue

            for v in vulns:
                self.assertTrue(v.vuln_id != "")
                self.assertTrue(v.severity != "")
                self.assertTrue(v.published != "")
                self.assertTrue(v.modified != "")
                self.assertTrue(v.description != "")
                self.assertTrue(v.installed_ver != "")
                self.assertTrue(v.fixed_ver != "")
                self.assertTrue(v.pkg_path != "")
                self.assertTrue(v.epss_score != "")
                self.assertTrue(v.exploit_available != "")
                self.assertTrue(v.exploit_last_seen != "")
                self.assertTrue(v.cwes != "")

            as_markdown = pkg_vuln.to_markdown(vulns)
            self.assertIsNotNone(as_markdown)
            self.assertTrue(as_markdown != "")

            pkg_vuln.post_github_step_summary(as_markdown)


if __name__ == "__main__":
    unittest.main()
