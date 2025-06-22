import os
import json
import logging
import pathvalidate

logger = logging.getLogger(__name__)

class FileUtils:
    """
    Provides utility functions for secure and cross-platform file system operations.
    """

    @staticmethod
    def sanitize_filename(filename: str, platform: str = "auto") -> str:
        """
        Sanitizes a filename to remove or replace characters that are problematic for file systems.

        Args:
            filename (str): The original filename.
            platform (str): The target platform ("auto", "Windows", "Linux", "macOS").
                            "auto" attempts to detect the current OS.

        Returns:
            str: A sanitized filename.
        """
        try:
            return pathvalidate.sanitize_filename(filename, platform=platform)
        except Exception as e:
            logger.error(f"Error sanitizing filename '{filename}': {e}", exc_info=True)
            # Fallback to a very basic sanitization if pathvalidate fails unexpectedly
            return "".join(c if c.isalnum() or c in (' ', '.', '_', '-') else '_' for c in filename).strip()


    @staticmethod
    def sanitize_filepath(filepath: str, platform: str = "auto") -> str:
        """
        Sanitizes a full filepath.

        Args:
            filepath (str): The original filepath.
            platform (str): The target platform.

        Returns:
            str: A sanitized filepath.
        """
        try:
            return pathvalidate.sanitize_filepath(filepath, platform=platform)
        except Exception as e:
            logger.error(f"Error sanitizing filepath '{filepath}': {e}", exc_info=True)
            # Fallback for path part if pathvalidate fails
            parts = filepath.replace('\\', '/').split('/')
            sanitized_parts = [FileUtils.sanitize_filename(part, platform) for part in parts[:-1]]
            sanitized_parts.append(FileUtils.sanitize_filename(parts[-1], platform))
            return os.path.join(*sanitized_parts)


    @staticmethod
    def secure_join(base: str, *paths: str) -> str:
        """
        Securely joins path components, ensuring the resulting path is under the base directory.
        Also sanitizes each path component.

        Args:
            base (str): The base directory.
            *paths (str): Path components to join.

        Returns:
            str: The joined and sanitized path.

        Raises:
            ValueError: If a path component is invalid or tries to escape the base directory.
        """
        if not base:
            raise ValueError("Base directory cannot be empty for secure_join.")

        # Sanitize and normalize the base path first
        # realpath resolves symlinks and normalizes, which is good for security checks
        # but ensure the base path itself is valid before resolving
        try:
            # Sanitize before attempting to make it absolute or resolve, as it might contain invalid chars
            # However, pathvalidate might not like absolute paths for "sanitize_filepath" if not careful
            # For base, we primarily care it's a legit directory string
            if not os.path.isabs(base):
                 base = os.path.abspath(FileUtils.sanitize_filepath(base))
            else: # if already abs, sanitize carefully
                 base = FileUtils.sanitize_filepath(base)

            if not os.path.isdir(base): # Check if base exists and is a dir, or could be created
                 # This check might be too strict if we expect to create the base later.
                 # For now, let's assume base should ideally exist or be creatable without traversal.
                 pass # os.makedirs below will handle creation if needed.

        except pathvalidate.ValidationError as e:
            logger.error(f"Invalid base path provided to secure_join: {base}, Error: {e}")
            raise ValueError(f"Invalid base path: {base}, Error: {e}") from e
        except Exception as e: # Catch other OS errors
            logger.error(f"Error processing base path '{base}': {e}", exc_info=True)
            raise ValueError(f"Error with base path: {base}, Error: {e}") from e


        # Sanitize each subsequent path component
        # Also, ensure no path component in *paths is absolute
        sanitized_paths = []
        for p_orig in paths:
            p_str = str(p_orig)
            if os.path.isabs(p_str):
                raise ValueError(f"Absolute path component '{p_str}' not allowed in secure_join subsequent paths.")
            sanitized_paths.append(FileUtils.sanitize_filename(p_str))

        # Join the sanitized components
        # os.path.join handles OS-specific separators
        prospective_path = os.path.join(base, *sanitized_paths)

        # Normalize the prospective path (e.g., collapses ../, ./, double slashes)
        normalized_path = os.path.normpath(prospective_path)

        # Final check: Ensure the normalized path is still within the intended base directory
        # This is a critical security check against path traversal (e.g., '../../etc/passwd')
        # os.path.commonpath can be used, or check if realpath(normalized_path) starts with realpath(base)

        # Using os.path.abspath to resolve any relative segments properly before comparison
        abs_base = os.path.abspath(base)
        abs_normalized_path = os.path.abspath(normalized_path)

        if os.path.commonprefix([abs_normalized_path, abs_base]) != abs_base:
            logger.error(f"Path traversal attempt detected or resolved path outside base. Base: '{abs_base}', Attempted: '{abs_normalized_path}'")
            raise ValueError("Path traversal attempt detected: resultant path is outside the base directory.")

        return abs_normalized_path # Return the absolute, normalized, and validated path

    @staticmethod
    def read_text_file(filepath: str, encoding: str = "utf-8") -> str | None:
        """
        Reads content from a text file.

        Args:
            filepath (str): The path to the file.
            encoding (str): The file encoding.

        Returns:
            str | None: The file content as a string, or None if an error occurs.
        """
        try:
            # Filepath should be sanitized before calling this, or use secure_join to construct it
            with open(filepath, "r", encoding=encoding) as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"File not found: {filepath}")
            return None
        except IOError as e:
            logger.error(f"IOError reading file {filepath}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error reading file {filepath}: {e}", exc_info=True)
            return None

    @staticmethod
    def write_text_file(filepath: str, content: str, encoding: str = "utf-8", ensure_directory: bool = True) -> bool:
        """
        Writes content to a text file. Creates the directory if it doesn't exist.

        Args:
            filepath (str): The path to the file.
            content (str): The content to write.
            encoding (str): The file encoding.
            ensure_directory (bool): If True, creates the directory path if it doesn't exist.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Filepath should be sanitized, or use secure_join to construct it
            if ensure_directory:
                dir_name = os.path.dirname(filepath)
                if dir_name: # Ensure dir_name is not empty (e.g. for files in current dir)
                    os.makedirs(dir_name, exist_ok=True)

            with open(filepath, "w", encoding=encoding) as f:
                f.write(content)
            logger.debug(f"Successfully wrote to file: {filepath}")
            return True
        except IOError as e:
            logger.error(f"IOError writing to file {filepath}: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error writing to file {filepath}: {e}", exc_info=True)
            return False

    @staticmethod
    def read_json_file(filepath: str, encoding: str = "utf-8") -> dict | list | None:
        """
        Reads content from a JSON file.

        Args:
            filepath (str): The path to the JSON file.
            encoding (str): The file encoding.

        Returns:
            dict | list | None: The parsed JSON content, or None if an error occurs.
        """
        content = FileUtils.read_text_file(filepath, encoding)
        if content is None:
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSONDecodeError reading file {filepath}: {e}", exc_info=True)
            return None

    @staticmethod
    def write_json_file(filepath: str, data: dict | list, encoding: str = "utf-8", indent: int = 2, ensure_directory: bool = True) -> bool:
        """
        Writes data to a JSON file.

        Args:
            filepath (str): The path to the JSON file.
            data (dict | list): The data to write.
            encoding (str): The file encoding.
            indent (int): JSON indentation level.
            ensure_directory (bool): If True, creates the directory path if it doesn't exist.


        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            content = json.dumps(data, indent=indent, ensure_ascii=False)
            return FileUtils.write_text_file(filepath, content, encoding, ensure_directory)
        except TypeError as e:
            logger.error(f"TypeError during JSON serialization for {filepath}: {e}", exc_info=True)
            return False

    # Placeholder for encryption - to be detailed if/when needed
    @staticmethod
    def encrypt_file(filepath: str, key: bytes, output_filepath: str = None) -> bool:
        logger.warning("Encryption function is a placeholder and not implemented.")
        # Example: Use Fernet from cryptography.fernet
        # 1. Read file content
        # 2. Encrypt content
        # 3. Write encrypted content to output_filepath or overwrite
        return False

    @staticmethod
    def decrypt_file(filepath: str, key: bytes, output_filepath: str = None) -> bool:
        logger.warning("Decryption function is a placeholder and not implemented.")
        # Example: Use Fernet
        # 1. Read encrypted file
        # 2. Decrypt content
        # 3. Write decrypted content to output_filepath or overwrite
        return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # Setup a temporary test directory
    test_dir = "temp_file_utils_test_dir"
    os.makedirs(test_dir, exist_ok=True)

    base_test_dir = os.path.abspath(test_dir)

    logger.info("--- Testing FileUtils ---")

    # Test sanitize_filename
    logger.info(f"Sanitized 'test/file!name?.txt': {FileUtils.sanitize_filename('test/file!name?.txt')}")
    logger.info(f"Sanitized 'CON.txt' (Windows): {FileUtils.sanitize_filename('CON.txt', platform='Windows')}")

    # Test secure_join
    try:
        safe_path = FileUtils.secure_join(base_test_dir, "subdir", "safe_file.txt")
        logger.info(f"Securely joined path: {safe_path}")
        assert base_test_dir in safe_path # Basic check

        unsafe_path_attempt = FileUtils.secure_join(base_test_dir, "..", "outside_file.txt")
        logger.error(f"Secure_join allowed path traversal (UNEXPECTED): {unsafe_path_attempt}")
    except ValueError as e:
        logger.info(f"Successfully caught path traversal attempt: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during secure_join test: {e}", exc_info=True)


    # Test write_text_file and read_text_file
    text_file_path = FileUtils.secure_join(base_test_dir, "test_text_file.txt")
    text_content = "Hello, Agent Zero!\nThis is a test."
    if FileUtils.write_text_file(text_file_path, text_content):
        logger.info(f"Text file written: {text_file_path}")
        read_content = FileUtils.read_text_file(text_file_path)
        if read_content == text_content:
            logger.info("Text file read back successfully and content matches.")
        else:
            logger.error(f"Text file content mismatch. Expected:\n{text_content}\nGot:\n{read_content}")
    else:
        logger.error(f"Failed to write text file: {text_file_path}")

    # Test write_json_file and read_json_file
    json_file_path = FileUtils.secure_join(base_test_dir, "data", "test_json_file.json") # Test subdir creation
    json_data = {"name": "Agent Zero", "version": "0.1", "status": "testing", "nested": {"key": "value"}}
    if FileUtils.write_json_file(json_file_path, json_data):
        logger.info(f"JSON file written: {json_file_path}")
        read_data = FileUtils.read_json_file(json_file_path)
        if read_data == json_data:
            logger.info("JSON file read back successfully and data matches.")
        else:
            logger.error(f"JSON file data mismatch. Expected:\n{json_data}\nGot:\n{read_data}")
    else:
        logger.error(f"Failed to write JSON file: {json_file_path}")

    # Test non-existent file read
    non_existent_path = FileUtils.secure_join(base_test_dir, "non_existent.txt")
    logger.info(f"Attempting to read non-existent file: {non_existent_path}")
    assert FileUtils.read_text_file(non_existent_path) is None
    logger.info("Reading non-existent file handled correctly (returned None).")

    # Clean up test directory
    try:
        import shutil
        shutil.rmtree(test_dir)
        logger.info(f"Cleaned up test directory: {test_dir}")
    except Exception as e:
        logger.error(f"Error cleaning up test directory {test_dir}: {e}")

    logger.info("--- FileUtils tests completed ---")
