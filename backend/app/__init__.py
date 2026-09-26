"""
SnapAI Edge - App Compatibility Package
Allows imports such as `from app.ai...` as requested in the specification.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path if not present
backend_dir = str(Path(__file__).parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import ai

__all__ = ["ai"]
