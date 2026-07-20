"""
Utility function to read pd csv file
"""
from pathlib import Path
import pandas as pd

def load_csv(path: str | Path) -> pd.DataFrame:
    """read csv file"""
    return pd.read_csv(path, sep=";", low_memory=False)