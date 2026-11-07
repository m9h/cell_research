from dataclasses import replace
from itertools import permutations
import json
import random
import subprocess
import sys
import threading

import pytest

from cell_research.experiment import Config, Engine, replay, run
from cell_research.metrics import aggregation, measure, metric_history, shuffled_baseline
from modules.multithread.BubbleSortCell import BubbleSortCell
from modules.multithread.MultiThreadCell import CellStatus
from modules.multithread.StatusProbe import StatusProbe
from modules.multithread.experiment_utils import freeze_cells, no_cells_should_move


@pytest.mark.parametrize("policy", ["bubble", "insertion", "selection"])
@pytest.mark.parametrize("scheduler", ["random", "round_robin"])
@pytest.mark.parametrize("reverse", [False, True])
def test_small_permutations_sort_and_preserve_identities(policy, scheduler, reverse):
    for values in permutations([-2, 0, 3, 4]):
        r = run(Config(list(values), [policy], scheduler=scheduler, reverse=reverse))
        assert r.termination == "sorted"
        assert r.final_values == sorted(values, reverse=reverse)
        assert all(sorted(order) == list(range(4)) for order in r.orders())


@pytest.mark.parametrize("policy", ["bubble", "insertion", "selection"])
def test_duplicate_and_negative_values(policy):
    for reverse in (False, True):
        r = run(Config([3, -2, 3, -2, 0], [policy], reverse=reverse))
        assert r.final_values == sorted(r.config.values, reverse=reverse)


@pytest.mark.parametrize("policy", ["bubble", "insertion"])
def test_passive_frozen_neighbor_is_legal_and_not_stopped(policy):
    engine = Engine(Config([2, 1], [policy], frozen_ids=[0]))
    assert engine.cells[1].should_move()
    assert not no_cells_should_move(engine.cells)
    r = run(engine.config)
    assert r.termination == "sorted"
    assert r.final_order == [1, 0]


@pytest.mark.parametrize("policy", ["bubble", "insertion", "selection"])
def test_immovable_identity_never_moves(policy):
    r = run(Config([4, 2, 3, 1], [policy], frozen_ids=[1], frozen_mode="immovable"))
    assert all(order[1] == 1 for order in r.orders())


def test_frozen_cells_sample_without_replacement():
    engine = Engine(Config(list(range(10))))
    for count in (0, 2, 10):
        cells = Engine(engine.config).cells
        chosen = freeze_cells(cells, count, random.Random(0))
        assert len(set(chosen)) == count
        assert sum(c.status == CellStatus.FREEZE for c in cells) == count
    with pytest.raises(ValueError):
        freeze_cells(engine.cells, 11)


def test_default_counters_and_history_are_not_shared():
    def cell():
        return BubbleSortCell(0, 1, threading.Lock(), (0, 1), [], (0, 1), (1, 1), StatusProbe())

    first, second = cell(), cell()
    first.export_steps.append([2, 1])
    first.swapping_count[0] += 1
    assert second.export_steps == []
    assert second.swapping_count == [0]
    a, b = Engine(Config([2, 1])), Engine(Config([2, 1]))
    assert a.cells[0].export_steps is a.cells[1].export_steps
    assert a.cells[0].export_steps is not b.cells[0].export_steps


def test_progress_metrics_disagree_as_expected():
    before, after = measure([2, 4, 1, 3]), measure([2, 1, 4, 3])
    assert (before["adjacent_errors"], after["adjacent_errors"]) == (1, 2)
    assert (before["inversions"], after["inversions"]) == (3, 2)
    assert measure([-5, -5, 100])["rank_displacement"] == 0
    assert measure([3, 1, 1])["rank_displacement"] == 4


def test_bubble_inversions_are_monotone_even_with_passive_damage():
    r = run(Config([5, 2, 4, 1, 3], frozen_ids=[2]))
    history = metric_history(r)
    assert all(b["inversions"] == a["inversions"] - 1 for a, b in zip(history, history[1:]))


def test_termination_distinguishes_stuck_from_limits():
    assert run(Config([1, 2], max_steps=0)).termination == "sorted"
    assert run(Config([2, 1], max_steps=0)).termination == "step_limit"
    assert run(Config([2, 1], frozen_ids=[0, 1])).termination == "stuck"
    assert run(Config([2, 1], frozen_ids=[0], frozen_mode="immovable")).termination == "stuck"
    assert run(Config([2, 1], scheduler="threaded", max_seconds=1e-12)).termination == "time_limit"


def test_deterministic_reproduction_and_global_rng_isolation():
    config = Config([5, 1, 3, 2, 4], ["bubble", "selection", "insertion", "bubble", "selection"])
    random.seed(123)
    state = random.getstate()
    a, b = run(config), run(config)
    assert a.events == b.events
    assert a.summary() == b.summary()
    assert random.getstate() == state


@pytest.mark.parametrize("scheduler", ["random", "round_robin", "threaded"])
@pytest.mark.parametrize("mode", ["passive", "immovable"])
def test_event_replay_including_threaded_mixtures(tmp_path, scheduler, mode):
    r = run(
        Config(
            [5, 1, 3, 2, 4],
            ["bubble", "selection", "insertion", "bubble", "selection"],
            scheduler=scheduler,
            frozen_ids=[2],
            frozen_mode=mode,
        )
    )
    r.save(tmp_path)
    reproduced = replay(tmp_path)
    assert r.events == reproduced.events
    assert r.summary() == reproduced.summary()
    assert not any(t.name.startswith("sorting-cell-") for t in threading.enumerate())


def test_replay_detects_tampering_and_save_refuses_overwrite(tmp_path):
    r = run(Config([3, 2, 1]))
    r.save(tmp_path)
    with pytest.raises(FileExistsError):
        r.save(tmp_path)
    path = tmp_path / "events.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    events[0]["swaps"] = 99
    path.write_text("\n".join(json.dumps(e) for e in events))
    with pytest.raises(ValueError, match="diverged"):
        replay(tmp_path)


def test_shuffle_baseline_matches_exhaustive_permutations():
    labels = ["a", "a", "b", "b"]
    actual = sum(aggregation(p) for p in permutations(labels)) / 24
    assert actual == pytest.approx(shuffled_baseline(labels))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"values": []},
        {"frozen_ids": [0, 0]},
        {"frozen_ids": [99]},
        {"algorithms": ["unknown"]},
        {"scheduler": "bad"},
        {"max_steps": -1},
        {"max_seconds": float("nan")},
        {"max_seconds": float("inf")},
    ],
)
def test_invalid_configs(kwargs):
    with pytest.raises(ValueError):
        replace(Config([2, 1]), **kwargs)


def test_compatibility_command_runs_and_terminates(tmp_path):
    process = subprocess.run(
        [
            sys.executable,
            "multithread_cell_sorting.py",
            "--cell_type=bubble",
            "--values",
            "2",
            "1",
            "--output",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["termination"] == "sorted"
