import unittest
import os
import sys
import shutil
import json

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from agent_zero.file_utils import FileUtils

class TestFileUtils(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up a temporary directory for test files."""
        cls.test_dir = os.path.abspath("temp_file_utils_tests")
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir) # Clean up if exists from previous failed run
        os.makedirs(cls.test_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        """Remove the temporary test directory."""
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    def test_sanitize_filename(self):
        # pathvalidate.sanitize_filename default behavior removes invalid chars by default.
        # On Windows, '/' and '?' are invalid. '!' is valid.
        # So "test/file!name?.txt" -> "testfile!name.txt"
        self.assertEqual(FileUtils.sanitize_filename("test/file!name?.txt", platform="Windows"), "testfile!name.txt")

        # On Linux, for a single filename component:
        # '/' is invalid, '!' is valid, '?' is valid.
        # sanitize_filename("test/file!name?.txt", platform="Linux") -> "testfile!name?.txt"
        self.assertEqual(FileUtils.sanitize_filename("test/file!name?.txt", platform="Linux"), "testfile!name?.txt")

        self.assertEqual(FileUtils.sanitize_filename("COM1", platform="Windows"), "COM1_") # Reserved name, pathvalidate appends '_'
        self.assertEqual(FileUtils.sanitize_filename(" valid name "), " valid name ") # pathvalidate keeps leading/trailing spaces
        self.assertEqual(FileUtils.sanitize_filename(""), "")

    def test_sanitize_filepath(self):
        # pathvalidate.sanitize_filepath normalizes ".."
        # Input: "/usr/local/bin/../file?.txt"
        # On Linux, '?' is a valid char in a filename. So it should be preserved.
        # Normalized & Sanitized on Linux: "/usr/local/file?.txt"

        sanitized_linux_style = FileUtils.sanitize_filepath("/usr/local/bin/../file?.txt", platform="linux")
        self.assertEqual(sanitized_linux_style, "/usr/local/file?.txt") # '?' is valid on Linux

        # Test for Windows-like behavior
        # Input: "C:/Users/name/Documents/bin/../file*<>.doc"
        # On Windows: '/' -> '\', 'bin/..' normalizes out. Invalid chars * < > are removed (default replacement is empty string).
        # Expected: "C:\Users\name\Documents\file.doc"
        sanitized_windows_style = FileUtils.sanitize_filepath("C:/Users/name/Documents/bin/../file*<>.doc", platform="windows")
        self.assertEqual(sanitized_windows_style, "C:\\Users\\name\\Documents\\file.doc")
        self.assertFalse("*" in sanitized_windows_style or "<" in sanitized_windows_style or ">" in sanitized_windows_style or "bin" in sanitized_windows_style)


    def test_secure_join_valid(self):
        safe_path = FileUtils.secure_join(self.test_dir, "subdir", "safe_file.txt")
        # self.test_dir is already absolute.
        expected_path = os.path.join(self.test_dir, "subdir", "safe_file.txt")
        self.assertEqual(safe_path, expected_path) # secure_join now returns absolute path
        # Ensure the directory was not created by secure_join itself, only path computed
        self.assertFalse(os.path.exists(os.path.dirname(safe_path)))


    def test_secure_join_traversal_attempt(self):
        with self.assertRaisesRegex(ValueError, "Path traversal attempt detected"):
            FileUtils.secure_join(self.test_dir, "..", "outside_file.txt")

        # Test the new check for absolute paths in subsequent components
        with self.assertRaisesRegex(ValueError, "Absolute path component .* not allowed"):
            abs_evil_path = os.path.abspath(os.path.join(self.test_dir, "..", "evil.txt")) # This path is outside test_dir
            FileUtils.secure_join(self.test_dir, abs_evil_path) # Should be caught by isabs check

        with self.assertRaisesRegex(ValueError, "Absolute path component .* not allowed"):
            FileUtils.secure_join(self.test_dir, "/another/absolute/path.txt") # Direct absolute path

        with self.assertRaisesRegex(ValueError, "Base directory cannot be empty"):
            FileUtils.secure_join("", "some_file.txt")


    def test_write_and_read_text_file(self):
        file_path = FileUtils.secure_join(self.test_dir, "text_rw_test.txt")
        content = "Hello, Agent Zero!\nLine two.\nSpecial chars: áéíóúñ"

        self.assertTrue(FileUtils.write_text_file(file_path, content, ensure_directory=True))
        self.assertTrue(os.path.exists(file_path))

        read_content = FileUtils.read_text_file(file_path)
        self.assertEqual(read_content, content)

    def test_write_and_read_text_file_subdir(self):
        file_path = FileUtils.secure_join(self.test_dir, "rw_subdir", "text_rw_test_subdir.txt")
        content = "Content in a subdirectory."

        self.assertTrue(FileUtils.write_text_file(file_path, content, ensure_directory=True))
        self.assertTrue(os.path.exists(file_path))
        self.assertTrue(os.path.exists(os.path.dirname(file_path))) # Check subdir creation

        read_content = FileUtils.read_text_file(file_path)
        self.assertEqual(read_content, content)


    def test_read_non_existent_text_file(self):
        file_path = FileUtils.secure_join(self.test_dir, "non_existent_text.txt")
        self.assertIsNone(FileUtils.read_text_file(file_path))

    def test_write_and_read_json_file(self):
        file_path = FileUtils.secure_join(self.test_dir, "json_rw_test.json")
        data = {"name": "Agent 0", "version": 0.1, "features": ["RAG", "Self-Play"], "unicode": "áéíóúñ"}

        self.assertTrue(FileUtils.write_json_file(file_path, data, ensure_directory=True))
        self.assertTrue(os.path.exists(file_path))

        read_data = FileUtils.read_json_file(file_path)
        self.assertEqual(read_data, data)

    def test_read_malformed_json_file(self):
        file_path = FileUtils.secure_join(self.test_dir, "malformed.json")
        # Write intentionally malformed JSON (missing comma)
        FileUtils.write_text_file(file_path, '{"name": "Test" "version": 1.0}', ensure_directory=True)
        self.assertIsNone(FileUtils.read_json_file(file_path))

    def test_read_non_existent_json_file(self):
        file_path = FileUtils.secure_join(self.test_dir, "non_existent_json.json")
        self.assertIsNone(FileUtils.read_json_file(file_path))

    def test_ensure_directory_false(self):
        # Test write_text_file with ensure_directory=False for a path where dir doesn't exist
        file_path = os.path.join(self.test_dir, "new_dir_not_created", "file.txt")
        self.assertFalse(os.path.exists(os.path.dirname(file_path))) # Ensure dir doesn't exist

        # This should fail because the directory is not created
        # Depending on OS, it might raise FileNotFoundError or similar IOError
        # FileUtils.write_text_file catches IOError and returns False
        self.assertFalse(FileUtils.write_text_file(file_path, "test", ensure_directory=False))
        self.assertFalse(os.path.exists(file_path))


if __name__ == '__main__':
    unittest.main()
