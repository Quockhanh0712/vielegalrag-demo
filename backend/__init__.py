# Backend package
# Add parent directory to path to allow 'backend.xxx' imports when running from backend/ folder
import sys
from pathlib import Path

# This makes 'from backend.config import settings' work from any subdirectory
_parent_dir = str(Path(__file__).parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)
