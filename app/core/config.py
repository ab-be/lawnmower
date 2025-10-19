import os
from pathlib import Path

#-----------------------------------------
# Files paths
#-----------------------------------------
CURRENT_FILE_PATH = Path(os.path.abspath(__file__))
CORE_DIR = CURRENT_FILE_PATH.parent
PROJECT_ROOT = CORE_DIR.parent
FRONTEND_BUILD_DIR = PROJECT_ROOT / "dist"
DATA_DIR = PROJECT_ROOT / "data"
