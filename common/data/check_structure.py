"""
Functions for checking and creating expected dirs/files
"""

from pathlib import Path
from common.utils.logging import get_logger
from common.utils.paths import REQUIRED_DIRS

logger = get_logger(__name__)

def dir_exists(dir_path: str | Path) -> bool:
    """true if dir_path exists and is dir"""
    return Path(dir_path).is_dir()

def file_exists(file_path: str | Path) -> bool:
    """true if file_path exists and if is file"""
    return Path(file_path).is_file()


def create_dir(dir_path: str | Path) -> Path:
    """create dir if missing and return path"""
    dir_path = Path(dir_path)
    if not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {dir_path}")
    return dir_path


def ensure_directories(dirs: list[str | Path] = REQUIRED_DIRS) -> list[Path]:
    """create all dirs if missing"""
    return [create_dir(d) for d in dirs]
# def check_existing_file(file_path: str | Path) -> bool:
#     """Check if a file already exists. If it does, ask if we want to overwrite it."""
#     file_path = Path(file_path)
#     if file_path.is_file():
#         while True:
#             response = input(f"File {file_path.name} already exists. Do you want to overwrite it? (y/n): ")
#             if response.lower() == 'y':
#                 return True
#             elif response.lower() == 'n':
#                 return False
#             else:
#                 print("Invalid response. Please enter 'y' or 'n'.")
#     else:
#         return True
    
    
# def check_existing_folder(folder_path: str | Path) -> bool:
#     """Check if a folder already exists. If it doesn't, ask if we want to create it."""
#     folder_path = Path(folder_path)
#     if folder_path.is_dir() == False :
#         while True:
#             response = input(f"{folder_path.name} doesn't exists. Do you want to create it? (y/n): ")
#             if response.lower() == 'y':
#                 return True
#             elif response.lower() == 'n':
#                 return False
#             else:
#                 print("Invalid response. Please enter 'y' or 'n'.")
#     else:
#         return False