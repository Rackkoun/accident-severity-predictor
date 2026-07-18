"""
Functions for checking if a file or folder exists
"""

from pathlib import Path


def check_existing_file(file_path: str | Path) -> bool:
    """Check if a file already exists. If it does, ask if we want to overwrite it."""
    file_path = Path(file_path)
    if file_path.is_file():
        while True:
            response = input(f"File {file_path.name} already exists. Do you want to overwrite it? (y/n): ")
            if response.lower() == 'y':
                return True
            elif response.lower() == 'n':
                return False
            else:
                print("Invalid response. Please enter 'y' or 'n'.")
    else:
        return True
    
    
def check_existing_folder(folder_path: str | Path) -> bool:
    """Check if a folder already exists. If it doesn't, ask if we want to create it."""
    folder_path = Path(folder_path)
    if folder_path.is_dir() == False :
        while True:
            response = input(f"{folder_path.name} doesn't exists. Do you want to create it? (y/n): ")
            if response.lower() == 'y':
                return True
            elif response.lower() == 'n':
                return False
            else:
                print("Invalid response. Please enter 'y' or 'n'.")
    else:
        return False