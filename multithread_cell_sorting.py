"""Compatibility entry point; prefer `cell-sorting run` for new experiments."""
import sys
from cell_research.cli import main

if __name__ == "__main__":
    main(["run", "--scheduler", "threaded", *sys.argv[1:]])
