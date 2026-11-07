"""Bounded, replayable execution of the original single-group cell policies.

The scheduler is an experimental variable. Seeded and threaded execution both
call the same cell.move methods; neither is an exact recreation of the paper's
operating-system schedule or its historical analysis pipeline.
"""

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import random
import threading
import time
from types import SimpleNamespace

from modules.multithread.BubbleSortCell import BubbleSortCell
from modules.multithread.CellGroup import GroupStatus
from modules.multithread.InsertionSortCell import InsertionSortCell
from modules.multithread.MultiThreadCell import CellStatus
from modules.multithread.SelectionSortCell import SelectionSortCell
from modules.multithread.StatusProbe import StatusProbe
from . import __version__

UPSTREAM_COMMIT = "1fd2bd5921c1f6b423a71f691d5189106a8a1020"
POLICIES = {
    "bubble": BubbleSortCell,
    "insertion": InsertionSortCell,
    "selection": SelectionSortCell,
}
SCHEMA_VERSION = 1


@dataclass
class Config:
    values: list[int]
    algorithms: list[str] = field(default_factory=lambda: ["bubble"])
    seed: int = 0
    frozen_ids: list[int] = field(default_factory=list)
    frozen_mode: str = "passive"
    scheduler: str = "random"
    max_steps: int = 50_000
    max_seconds: float = 30.0
    reverse: bool = False

    def __post_init__(self):
        self.values = list(self.values)
        self.algorithms = list(self.algorithms)
        self.frozen_ids = list(self.frozen_ids)
        if not self.values or any(type(v) is not int for v in self.values):
            raise ValueError("values must be a nonempty sequence of integers")
        if len(self.algorithms) == 1:
            self.algorithms *= len(self.values)
        if len(self.algorithms) != len(self.values) or any(
            a not in POLICIES for a in self.algorithms
        ):
            raise ValueError("provide one algorithm or one per cell: bubble, insertion, selection")
        if len(set(self.frozen_ids)) != len(self.frozen_ids) or any(
            type(i) is not int or not 0 <= i < len(self.values) for i in self.frozen_ids
        ):
            raise ValueError("frozen IDs must be distinct, zero-based initial cell indices")
        if self.frozen_mode not in ("passive", "immovable"):
            raise ValueError("frozen_mode must be passive or immovable")
        if self.scheduler not in ("random", "round_robin", "threaded"):
            raise ValueError("scheduler must be random, round_robin, or threaded")
        if type(self.max_steps) is not int or self.max_steps < 0:
            raise ValueError("max_steps must be a nonnegative integer")
        if not 0 < self.max_seconds < float("inf"):
            raise ValueError("max_seconds must be finite and positive")


@dataclass
class Result:
    config: Config
    events: list[dict]
    final_order: list[int]
    termination: str

    @property
    def final_values(self):
        return [self.config.values[i] for i in self.final_order]

    def orders(self):
        """Initial order followed by each successful swap, using stable cell IDs."""
        return [list(range(len(self.config.values)))] + [
            e["order"] for e in self.events if e["swaps"]
        ]

    def summary(self):
        from .metrics import measure

        return {
            "schema_version": SCHEMA_VERSION,
            "package_version": __version__,
            "upstream_commit": UPSTREAM_COMMIT,
            "config": asdict(self.config),
            "termination": self.termination,
            "attempts": len(self.events),
            "swaps": sum(e["swaps"] for e in self.events),
            "final_order": self.final_order,
            "final_values": self.final_values,
            "metrics": measure(self.final_values, reverse=self.config.reverse),
        }

    def save(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        # Refuse accidental replacement of a previously recorded experiment.
        if (directory / "result.json").exists() or (directory / "events.jsonl").exists():
            raise FileExistsError(f"experiment already exists in {directory}")
        with (directory / "events.jsonl").open("w") as stream:
            for event in self.events:
                stream.write(json.dumps(event, sort_keys=True) + "\n")
        (directory / "result.json").write_text(json.dumps(self.summary(), indent=2) + "\n")
        return directory


class Engine:
    def __init__(self, config):
        self.config = Config(**asdict(config))
        self.lock = threading.RLock()
        self.probe = StatusProbe()
        self.cells = []
        self.events = []
        self.timed_out = False
        self.swapping_count = [0]
        self.export_steps = []
        n = len(config.values)
        group = SimpleNamespace(group_id=0, status=GroupStatus.ACTIVE)
        for i, (value, algorithm) in enumerate(zip(config.values, config.algorithms)):
            cell = POLICIES[algorithm](
                i,
                value,
                self.lock,
                (i, 1),
                self.cells,
                (0, 1),
                (n - 1, 1),
                self.probe,
                disable_visualization=True,
                swapping_count=self.swapping_count,
                export_steps=self.export_steps,
                reverse_direction=config.reverse,
            )
            cell.group = group
            cell.frozen_mode = config.frozen_mode
            # Separate streams: changing the scheduler does not consume policy draws.
            cell.rng = random.Random(f"{config.seed}:cell:{i}")
            if i in config.frozen_ids:
                cell.set_cell_to_freeze()
            self.cells.append(cell)
        self.by_id = {c.threadID: c for c in self.cells}

    def reason(self):
        values = [c.value for c in self.cells]
        if values == sorted(values, reverse=self.config.reverse):
            return "sorted"
        if not any(c.status == CellStatus.ACTIVE and c.should_move() for c in self.cells):
            return "stuck"
        if len(self.events) >= self.config.max_steps:
            return "step_limit"
        if self.timed_out:
            return "time_limit"
        return None

    def step(self, actor_id):
        with self.lock:
            if self.reason() is not None:
                return None
            before = self.probe.swap_count
            cell = self.by_id[actor_id]
            if cell.status == CellStatus.ACTIVE:
                cell.move()
            swaps = self.probe.swap_count - before
            event = {
                "step": len(self.events) + 1,
                "actor_id": actor_id,
                "swaps": swaps,
                "ideal_position": list(cell.ideal_position) if cell.ideal_position else None,
            }
            if swaps:
                event["order"] = [c.threadID for c in self.cells]
            self.events.append(event)
            return event

    def result(self):
        reason = self.reason()
        if reason is None:
            raise ValueError("experiment has not terminated")
        return Result(self.config, self.events, [c.threadID for c in self.cells], reason)


def run(config):
    engine = Engine(config)
    if config.scheduler != "threaded":
        schedule = random.Random(f"{config.seed}:schedule")
        while engine.reason() is None:
            actor = (
                schedule.randrange(len(config.values))
                if config.scheduler == "random"
                else len(engine.events) % len(config.values)
            )
            engine.step(actor)
        return engine.result()

    # Each worker owns one cell identity, like the original implementation.
    # The outer lock makes terminal checks and event recording atomic with moves.
    deadline = time.monotonic() + config.max_seconds
    errors = []

    def worker(actor):
        try:
            while True:
                with engine.lock:
                    if errors:
                        return
                    if time.monotonic() >= deadline:
                        engine.timed_out = True
                    if engine.reason() is not None:
                        return
                    engine.step(actor)
                time.sleep(0)  # Yield; wall-clock speed is not an algorithmic metric.
        except Exception as exc:
            with engine.lock:
                errors.append(exc)

    workers = [
        threading.Thread(target=worker, args=(i,), name=f"sorting-cell-{i}")
        for i in range(len(config.values))
        if i not in config.frozen_ids
    ]
    for thread in workers:
        thread.start()
    for thread in workers:
        thread.join()
    if errors:
        raise RuntimeError("cell worker failed") from errors[0]
    return engine.result()


def replay(directory):
    """Re-execute the recorded actor order, checking every event and final summary."""
    directory = Path(directory)
    saved = json.loads((directory / "result.json").read_text())
    if saved.get("schema_version") != SCHEMA_VERSION or saved.get("package_version") != __version__:
        raise ValueError("unsupported recording version")
    engine = Engine(Config(**saved["config"]))
    for line in (directory / "events.jsonl").read_text().splitlines():
        expected = json.loads(line)
        actual = engine.step(expected["actor_id"])
        if actual != expected:
            raise ValueError(f"replay diverged at step {expected.get('step')}")
    # Wall-clock expiry is external to the policy dynamics and cannot be rerun.
    engine.timed_out = saved["termination"] == "time_limit"
    result = engine.result()
    if result.summary() != saved:
        raise ValueError("replay final summary does not match recording")
    return result
