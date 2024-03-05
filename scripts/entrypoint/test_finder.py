import os
import shutil
import tempfile
import unittest

import downloader
import extractor
import finder

class TestFinder(unittest.TestCase):

    def test_find_sbomgen(self):
        # setup
        url = "https://amazon-inspector-sbomgen.s3.amazonaws.com/latest/linux/amd64/inspector-sbomgen.zip"
        path_to_zip_file = os.path.join(tempfile.gettempdir(), "inspector-sbomgen.zip")
        result = downloader.download_file(url, path_to_zip_file)
        self.assertTrue(result)

        tmp_dir = tempfile.gettempdir()
        extracted_contents_dir = os.path.join(tmp_dir, "inspector-sbomgen")
        result = extractor.extract_zip_file(path_to_zip_file, extracted_contents_dir)
        self.assertTrue(result)

        # test
        want = "inspector-sbomgen"
        got = finder.find_file_in_dir(want, extracted_contents_dir)
        self.assertTrue(got != "")
        self.assertEqual(want, os.path.basename(got))

        # tear down
        os.remove(path_to_zip_file)
        shutil.rmtree(extracted_contents_dir)
        return


if __name__ == '__main__':
    unittest.main()
