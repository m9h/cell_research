"""Command-line entry point for recorded runs, replay, and guided experiments."""

import argparse
import json
from pathlib import Path
import random

from .experiment import Config, replay, run


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    experiment = commands.add_parser("run", help="record one experiment")
    experiment.add_argument("--values", nargs="+", type=int)
    experiment.add_argument("--size", type=int, default=20)
    experiment.add_argument(
        "--algorithm", "--cell_type", choices=["bubble", "insertion", "selection"], default="bubble"
    )
    experiment.add_argument(
        "--mix",
        nargs="+",
        choices=["bubble", "insertion", "selection"],
        help="balanced mixture, shuffled independently of values",
    )
    experiment.add_argument("--seed", type=int, default=0)
    defects = experiment.add_mutually_exclusive_group()
    defects.add_argument(
        "--frozen", type=int, default=0, help="number of distinct frozen identities"
    )
    defects.add_argument("--frozen-ids", type=int, nargs="+", help="zero-based initial identities")
    experiment.add_argument("--frozen-mode", choices=["passive", "immovable"], default="passive")
    experiment.add_argument(
        "--scheduler", choices=["random", "round_robin", "threaded"], default="random"
    )
    experiment.add_argument("--max-steps", type=int, default=50_000)
    experiment.add_argument("--max-seconds", type=float, default=30, help="threaded wall-clock cap")
    experiment.add_argument("--reverse", action="store_true")
    experiment.add_argument("--output", type=Path, default=Path("outputs/run"))
    playback = commands.add_parser("replay", help="verify a recording, including threaded runs")
    playback.add_argument("directory", type=Path)
    examples = commands.add_parser(
        "examples", help="generate figures, a GIF, and controlled study data"
    )
    examples.add_argument(
        "--example", choices=["all", "progress", "damage", "clustering"], default="all"
    )
    examples.add_argument("--trials", type=int, default=20)
    examples.add_argument("--output", type=Path, default=Path("outputs/examples"))
    return cli


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    try:
        if args.command == "run":
            values = args.values if args.values is not None else list(range(args.size))
            if args.values is None:
                random.Random(f"{args.seed}:values").shuffle(values)
            labels = [args.algorithm]
            if args.mix:
                labels = [args.mix[i % len(args.mix)] for i in range(len(values))]
                random.Random(f"{args.seed}:labels").shuffle(labels)
            frozen = args.frozen_ids
            if frozen is None:
                frozen = sorted(
                    random.Random(f"{args.seed}:frozen").sample(range(len(values)), args.frozen)
                )
            result = run(
                Config(
                    values,
                    labels,
                    args.seed,
                    frozen,
                    args.frozen_mode,
                    args.scheduler,
                    args.max_steps,
                    args.max_seconds,
                    args.reverse,
                )
            )
            result.save(args.output)
            print(json.dumps(result.summary(), indent=2))
        elif args.command == "replay":
            result = replay(args.directory)
            print(f"Replay verified: {len(result.events)} attempts, {result.termination}")
        else:
            from .studies import clustering_study, damage_study, progress_demo
            import matplotlib.pyplot as plt

            if args.example in ("all", "progress"):
                progress_demo(args.output / "progress")
                plt.close("all")
            if args.example in ("all", "damage"):
                damage_study(args.output / "damage", trials=args.trials)
                plt.close("all")
            if args.example in ("all", "clustering"):
                clustering_study(args.output / "clustering", trials=args.trials)
                plt.close("all")
            print(f"Examples written to {args.output.resolve()}")
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        cli.error(str(exc))
