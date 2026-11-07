"""Shared setup and termination helpers for the original experiment scripts."""

import random

from .MultiThreadCell import CellStatus


def freeze_cells(cells, count, rng=None):
    """Freeze exactly count distinct cells, returning their identities."""
    if not 0 <= count <= len(cells):
        raise ValueError("frozen count must be between zero and the number of cells")
    selected = (rng or random).sample(cells, count)
    for cell in selected:
        cell.set_cell_to_freeze()
    return [cell.threadID for cell in selected]


def no_cells_should_move(cells):
    """Check one coherent state; should_move includes internal pointer progress."""
    if not cells:
        return True
    with cells[0].lock:
        return not any(
            c.status in (CellStatus.SLEEP, CellStatus.MOVING)
            or (c.status == CellStatus.ACTIVE and c.should_move())
            for c in cells
        )
