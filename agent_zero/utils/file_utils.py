# agent_zero/utils/file_utils.py
import os
import errno
import shutil

def ensure_directory_exists(path: str) -> bool:
    """
    Ensures that a directory exists. If it doesn't, it attempts to create it.

    Args:
        path (str): The path to the directory.

    Returns:
        bool: True if the directory exists or was successfully created, False otherwise.
    """
    if not path:
        print("Error: No path provided to ensure_directory_exists.")
        return False
    try:
        os.makedirs(path, exist_ok=True)
        # print(f"Directory '{path}' ensured.") # Verbose, uncomment for debugging
        return True
    except OSError as e:
        if e.errno != errno.EEXIST:
            print(f"Error creating directory '{path}': {e}")
            return False
        # Directory already exists, which is fine.
        return True
    except Exception as e:
        print(f"An unexpected error occurred while ensuring directory '{path}': {e}")
        return False

def construct_path(*args: str) -> str:
    """
    Constructs a normalized path from path segments.

    Args:
        *args: Path segments to join.

    Returns:
        str: The normalized, absolute path.
    """
    return os.path.abspath(os.path.join(*args))

import re # Ensure re is at the top if not already

def sanitize_filename(filename: str, replacement_char: str = '_') -> str:
    """
    Sanitizes a string to be used as a filename by replacing or removing invalid characters.

    Args:
        filename (str): The proposed filename.
        replacement_char (str): Character to replace invalid characters with.
                                If empty, invalid characters are removed.

    Returns:
        str: A sanitized filename.
    """
    if not filename:
        return "default_filename"

    # Characters invalid in Windows and/or Linux/macOS filenames
    # Note: This list can be expanded based on specific needs or target filesystems.
    invalid_chars_list = r'<>:"/\|?* ' + "".join(map(chr, range(32))) # Includes control characters and space

    # First pass: replace invalid characters or remove them
    if replacement_char:
        sanitized = "".join(replacement_char if c in invalid_chars_list else c for c in filename)
        # Second pass: squeeze multiple replacement_chars into one
        sanitized = re.sub(f'{re.escape(replacement_char)}+', replacement_char, sanitized)
    else:
        # If replacement_char is empty, remove invalid characters directly
        sanitized = "".join(c for c in filename if c not in invalid_chars_list)

    # Limit length (optional, but good practice)
    # This should happen *after* sanitization and squeezing
    max_len = 200 # Common filesystem limit is 255, being conservative
    if len(sanitized) > max_len:
        # Try to preserve extension if present
        name, ext = os.path.splitext(sanitized)
        if ext and len(ext) < 10 and len(ext) > 1: # Basic check for a reasonable extension like .txt, .jpeg
            name = name[:max_len - len(ext)]
            sanitized = name + ext
        else: # No apparent extension or very short/long extension, just truncate
            sanitized = sanitized[:max_len]

    if not sanitized and filename: # If all characters were invalid and removed, but original filename was not empty
        return "sanitized_filename" # or consider returning a fixed default like "untitled"
    elif not sanitized and not filename: # Original was empty, already returned "default_filename"
        pass # Covered by initial check

    return sanitized

def get_project_root() -> str:
    """
    Finds the project root directory. Assumes the script is within 'agent_zero'
    or a subdirectory of 'agent_zero', and '0README.txt' is at the root.
    This is a heuristic and might need adjustment based on deployment structure.
    """
    current_dir = os.path.abspath(os.path.dirname(__file__)) # agent_zero/utils
    # Navigate up until '0README.txt' is found or we hit the filesystem root
    # Max two levels up from 'agent_zero/utils' (i.e., 'agent_zero/' then project root)
    for _ in range(3):
        if os.path.exists(os.path.join(current_dir, "0README.txt")):
            return current_dir
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir: # Reached filesystem root
            break
        current_dir = parent_dir

    # Fallback if 0README.txt not found by this heuristic (e.g., if called from outside project structure)
    # This might happen if the utils are used as a library elsewhere.
    # In a container context, /app is often the root.
    if os.path.exists("/app/0README.txt"):
        return "/app"

    print("Warning: Could not robustly determine project root based on '0README.txt'. Falling back to CWD or utils parent.")
    # If running scripts directly, CWD might be the project root.
    # Otherwise, assume one level above 'utils' is 'agent_zero', and one above that is root.
    utils_parent = os.path.dirname(os.path.abspath(os.path.dirname(__file__))) # agent_zero
    project_root_candidate = os.path.dirname(utils_parent) # one level above agent_zero
    if os.path.exists(os.path.join(project_root_candidate, "0README.txt")):
        return project_root_candidate
    return os.getcwd()


if __name__ == '__main__':
    print("--- File Utils Test ---")

    # Test ensure_directory_exists
    print("\nTesting ensure_directory_exists...")
    test_dir_1 = "temp_test_dir_1"
    test_dir_2 = "temp_test_dir_nested/level2"

    print(f"Ensuring '{test_dir_1}'...")
    ensure_directory_exists(test_dir_1)
    assert os.path.exists(test_dir_1) and os.path.isdir(test_dir_1), f"Directory {test_dir_1} not created."
    print(f"Ensuring '{test_dir_2}' (nested)...")
    ensure_directory_exists(test_dir_2)
    assert os.path.exists(test_dir_2) and os.path.isdir(test_dir_2), f"Directory {test_dir_2} not created."

    # Clean up test directories
    if os.path.exists(test_dir_1): shutil.rmtree(test_dir_1)
    if os.path.exists("temp_test_dir_nested"): shutil.rmtree("temp_test_dir_nested")
    print("Test directories cleaned up.")

    # Test construct_path
    print("\nTesting construct_path...")
    path1 = construct_path("dir1", "dir2", "file.txt")
    print(f"Constructed path: {path1}")
    # Basic assertion: check if it's absolute
    assert os.path.isabs(path1), "Constructed path is not absolute."

    # Test sanitize_filename
    print("\nTesting sanitize_filename...")
    filenames_to_test = {
        "valid_filename.txt": "valid_filename.txt",
        "file with spaces.doc": "file_with_spaces.doc", # Now that space is invalid
        "fi:le*na?me<>.csv": "fi_le_na_me_.csv", # Corrected expectation
        "/path/to/some/file.log": "_path_to_some_file.log", # / replaced, .log preserved
        "a" * 300 + ".txt": ("a" * (200 - 4)) + ".txt", # name part is 196 'a's
        "": "default_filename",
        None: "default_filename",
        " leading_and_trailing_spaces ": "_leading_and_trailing_spaces_",
        "file\twith\ncontrol\rchars.dat": "file_with_control_chars.dat" # control chars become _
    }
    for original, expected in filenames_to_test.items():
        call_input = original if original is not None else ""
        sanitized = sanitize_filename(call_input)
        print(f"Original: '{original}' -> Sanitized: '{sanitized}' (Expected: '{expected}')")
        if original is not None:
             assert sanitized == expected, f"Sanitization failed for '{original}'. Got '{sanitized}', expected '{expected}'"

    # Test sanitize_filename with removal (replacement_char="")
    # When replacement_char is empty, invalid characters are simply removed.
    # The re.sub part is skipped if replacement_char is empty.
    sanitized_remove_input = "fi:le*na?me<>.csv"
    sanitized_remove_expected = "filename.csv" # :,*,?,<,> removed, . preserved
    sanitized_remove = sanitize_filename(sanitized_remove_input, replacement_char="")
    print(f"Original: '{sanitized_remove_input}' -> Sanitized (remove): '{sanitized_remove}' (Expected: '{sanitized_remove_expected}')")
    assert sanitized_remove == sanitized_remove_expected, f"Sanitization with removal failed for '{sanitized_remove_input}'. Got '{sanitized_remove}', expected '{sanitized_remove_expected}'"

    sanitized_remove_spaces_input = " file with spaces .doc"
    sanitized_remove_spaces_expected = "filewithspaces.doc" # spaces removed
    sanitized_remove_spaces = sanitize_filename(sanitized_remove_spaces_input, replacement_char="")
    print(f"Original: '{sanitized_remove_spaces_input}' -> Sanitized (remove spaces): '{sanitized_remove_spaces}' (Expected: '{sanitized_remove_spaces_expected}')")
    assert sanitized_remove_spaces == sanitized_remove_spaces_expected, f"Sanitization with removal of spaces failed for '{sanitized_remove_spaces_input}'."


    # Test get_project_root
    print("\nTesting get_project_root...")
    # This test is heuristic. We expect it to find the root where 0README.txt is.
    # Create a dummy 0README.txt in the current dir for a predictable test outcome if one isn't found higher up.
    # However, the provided code structure implies 0README.txt is at the actual project root.
    # The function's logic tries to find it by going up from agent_zero/utils.

    # To make this test more robust without actually creating files outside the test run,
    # we'll rely on the existing structure.
    # Assuming this script is run from where it lives (agent_zero/utils/file_utils.py)
    # or from the project root (e.g. python -m agent_zero.utils.file_utils)

    # Heuristic: The project root should contain 'agent_zero' directory.
    project_root = get_project_root()
    print(f"Determined project root: {project_root}")
    assert os.path.exists(os.path.join(project_root, "0README.txt")), \
        f"0README.txt not found at determined project root '{project_root}'. Test this from project root or ensure 0README.txt is correctly placed relative to agent_zero/utils."
    assert os.path.isdir(os.path.join(project_root, "agent_zero")), \
        f"'agent_zero' directory not found at determined project root '{project_root}'."


    print("\nFile Utils test finished.")
