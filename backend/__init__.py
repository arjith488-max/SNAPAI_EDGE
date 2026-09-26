"""
SnapAI Edge - Backend Package
"""
import sys
from pathlib import Path

# Ensure the backend directory is in sys.path so submodules can be resolved
# whether run from project root (e.g. backend.main:app) or within backend/
backend_dir = str(Path(__file__).resolve().parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
