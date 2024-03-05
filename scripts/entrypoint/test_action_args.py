import unittest

import action_args


class TestActionArguments(unittest.TestCase):

    def test_init_cli_args(self):
        os_args = ["entrypoint.py", "container", "alpine:latest", "/tmp/sbom.json", "/tmp/inspector_scan.json"]
        action_args.init_cli_args(os_args)
        self.assertEqual(action_args.ARTIFACT_TYPE, os_args[1])
        self.assertEqual(action_args.ARTIFACT_PATH, os_args[2])
        self.assertEqual(action_args.OUTPUT_SBOM_PATH, os_args[3])
        self.assertEqual(action_args.OUTPUT_INSPECTOR_SCAN_PATH, os_args[4])


if __name__ == '__main__':
    unittest.main()
