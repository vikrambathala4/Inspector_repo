import os
import platform
import tempfile
import unittest

import orchestrator


class TestOrchestrator(unittest.TestCase):

    def test_get_sbomgen_url(self):
        cpu_arch = platform.machine()
        os_name = platform.system()
        url = orchestrator.get_sbomgen_url(os_name, cpu_arch)

        if os_name == "Linux" and cpu_arch == "x86_64":
            expected = "https://amazon-inspector-sbomgen.s3.amazonaws.com/latest/linux/amd64/inspector-sbomgen.zip"
            self.assertEqual(url, expected)

        elif os_name == "Linux" and cpu_arch == "x86_64":
            expected = "https://amazon-inspector-sbomgen.s3.amazonaws.com/latest/linux/arm64/inspector-sbomgen.zip"
            self.assertEqual(url, expected)

        else:
            self.assertEqual(url, "")

    def test_install_sbomgen(self):

        os_name = platform.system()
        cpu_arch = platform.machine()

        if os_name != "Linux":
            return

        if cpu_arch != "x86_64" or cpu_arch != "arm64":
            return

        dst = os.path.join(tempfile.tempdir(), "inspector-sbomgen")
        result = orchestrator.install_sbomgen(dst)
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
