"""Portable locations for historical analysis scripts (data is not bundled)."""

import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("CELL_SORTING_DATA_DIR", "csv")).expanduser().resolve()
FIGURE_DIR = (
    Path(os.environ.get("CELL_SORTING_FIGURE_DIR", "outputs/legacy-figures")).expanduser().resolve()
)
