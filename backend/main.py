import os
import sys

# Ensure both backend root and project root are in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(backend_dir)
for p in [backend_dir, parent_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.main import app

__all__ = ["app"]
