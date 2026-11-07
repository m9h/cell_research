"""Execute every tutorial in fresh kernels; write reviewed outputs separately."""

import argparse
import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/executed-notebooks"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    target = args.output.resolve()
    target.mkdir(parents=True, exist_ok=True)
    runtime = root / "outputs" / "jupyter-runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("JUPYTER_RUNTIME_DIR", str(runtime))
    os.environ.setdefault("IPYTHONDIR", str(runtime / "ipython"))
    os.environ.setdefault("MPLCONFIGDIR", str(runtime / "matplotlib"))
    for source in sorted((root / "examples").glob("*.ipynb")):
        notebook = nbformat.read(source, as_version=4)
        # Execute afresh even when the source contains committed outputs.
        for cell in notebook.cells:
            if cell.cell_type == "code":
                cell.outputs = []
                cell.execution_count = None
        NotebookClient(
            notebook,
            timeout=180,
            kernel_name="python3",
            resources={"metadata": {"path": str(root)}},
        ).execute()
        nbformat.write(notebook, target / source.name)
        print(f"Executed {source.name}", flush=True)


if __name__ == "__main__":
    main()
