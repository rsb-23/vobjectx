import datetime as dt

TEST_FILE_DIR = "tests/test_files"

two_hours = dt.timedelta(hours=2)


def get_test_file(path):
    """
    Helper function to open and read test files.
    """
    filepath = f"{TEST_FILE_DIR}/{path}"
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    return text
