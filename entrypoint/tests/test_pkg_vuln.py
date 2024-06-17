import json
import os
import unittest

from entrypoint import pkg_vuln


def read_test_file(file: str) -> str:
    file_contents = ""
    with open(file, "r") as f:
        file_contents = f.read()
    return file_contents


class ConverterTestCase(unittest.TestCase):

    def test_get_pkg_vulns(self):
        test_file = "tests/test_data/artifacts/containers/dockerfile_checks/inspector-scan-cdx.json"
        inspector_scan = get_scan_body(test_file)
        vulns_dict = inspector_scan["vulnerabilities"]
        vulns = pkg_vuln.get_pkg_vulns(vulns_dict)
        self.assertTrue(vulns is not None)
        self.assertTrue(len(vulns) > 0)
        for v in vulns:
            self.assertTrue("IN-DOCKERFILE" not in v["id"])
        return

    def test_vulns_to_obj(self):
        test_files = [
            "tests/test_data/artifacts/containers/dockerfile_checks/inspector-scan-cdx.json",
            "tests/test_data/artifacts/containers/dockerfile_checks/inspector-scan-cdx-no-components.json",
            "tests/test_data/artifacts/containers/dockerfile_checks/inspector-scan-cdx-no-vulns.json",
            "tests/test_data/artifacts/containers/dockerfile_checks/inspector-scan-cdx-dockerfile-only.json",
        ]
        for test_file in test_files:
            with open(test_file, "r") as f:
                inspector_scan = json.load(f)
                vulns = pkg_vuln.vulns_to_obj(inspector_scan)
                self.assertTrue(vulns != None)

    def test_post_github_step_summary_no_vulns(self):

        markdown_dst_path = "/tmp/inspector.md"
        cleanup_stale_markdown_report(markdown_dst_path)

        zero_vuln_summary_md = pkg_vuln.to_markdown(vulns=None,
                                                    artifact_name="test_image:latest",
                                                    artifact_type="container",
                                                    artifact_hash="null",
                                                    build_id="null",
                                                    criticals="0",
                                                    highs="0",
                                                    mediums="0",
                                                    lows="0",
                                                    others="0")

        expected_list = ["| Critical | 0|",
                         "| High     | 0|",
                         "| Medium   | 0|",
                         "| Low      | 0|",
                         "| Other    | 0|",
                         ]
        for expected in expected_list:
            self.assertIn(expected, zero_vuln_summary_md)
        cleanup_stale_markdown_report(markdown_dst_path)


def get_scan_body(test_file):
    # test_file = "tests/test_data/artifacts/containers/dockerfile_checks/inspector-scan-cdx.json"
    inspector_scan = read_test_file(test_file)
    inspector_scan_dict = json.loads(inspector_scan)
    scan_body = inspector_scan_dict["sbom"]
    pkg_vuln.fatal_assert(scan_body != None, "expected JSON with key 'sbom' but it was not found")
    return scan_body


def cleanup_stale_markdown_report(path):
    try:
        os.remove(path)
    except:
        return


if __name__ == '__main__':
    unittest.main()
