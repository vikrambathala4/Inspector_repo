import os
import tempfile
import unittest

import downloader


class TestDownloader(unittest.TestCase):

    def test_download_file(self):
        # setup test inputs
        urls = [
            "https://amazon-inspector-sbomgen.s3.amazonaws.com/latest/linux/amd64/inspector-sbomgen.zip",
            "https://amazon-inspector-sbomgen.s3.amazonaws.com/latest/linux/arm64/inspector-sbomgen.zip"
        ]
        tmp_dir = tempfile.gettempdir()
        dst = os.path.join(tmp_dir, "inspector-sbomgen.zip")

        for each_url in urls:
            self.assertTrue(downloader.download_file(each_url, dst))
            os.remove(dst)


if __name__ == '__main__':
    unittest.main()
