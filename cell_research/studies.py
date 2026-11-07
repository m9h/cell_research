"""Controlled experiments used by the notebooks and command-line examples."""

from dataclasses import replace
import csv
import json
from pathlib import Path
import random

from .experiment import Config, run
from .metrics import aggregation, shuffled_baseline


def _write_rows(path, rows):
    with Path(path).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _check_size(trials, n):
    if trials < 2 or n < 3:
        raise ValueError("studies require at least two trials and three cells")


def _wilson(successes, n):
    z = 1.959963984540054
    p = successes / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denominator
    return center - half, center + half


def damage_study(output, trials=20, n=12, seed=17, scheduler="random"):
    """Paired initial arrays, policy seeds, and frozen identities across conditions."""
    import matplotlib.pyplot as plt

    _check_size(trials, n)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for trial in range(trials):
        rng = random.Random(f"{seed}:damage:{trial}")
        values = list(range(n))
        rng.shuffle(values)
        frozen = sorted(rng.sample(range(n), 2))
        for condition in ("intact", "passive", "immovable"):
            config = Config(
                values,
                seed=seed + trial,
                frozen_ids=[] if condition == "intact" else frozen,
                frozen_mode="passive" if condition == "intact" else condition,
                scheduler=scheduler,
            )
            result = run(config)
            result.save(output / f"trial-{trial:03d}-{condition}")
            rows.append(
                {
                    "trial": trial,
                    "condition": condition,
                    "termination": result.termination,
                    "attempts": len(result.events),
                    "swaps": result.summary()["swaps"],
                    "final_inversions": result.summary()["metrics"]["inversions"],
                }
            )
    _write_rows(output / "trials.csv", rows)
    conditions = ("intact", "passive", "immovable")
    summary = []
    for condition in conditions:
        selected = [r for r in rows if r["condition"] == condition]
        successes = sum(r["termination"] == "sorted" for r in selected)
        lo, hi = _wilson(successes, trials)
        summary.append(
            {
                "condition": condition,
                "trials": trials,
                "sorted": successes,
                "stuck": sum(r["termination"] == "stuck" for r in selected),
                "limited": sum(r["termination"].endswith("limit") for r in selected),
                "success_rate": successes / trials,
                "ci95_low": lo,
                "ci95_high": hi,
            }
        )
    _write_rows(output / "summary.csv", summary)
    fig, ax = plt.subplots(figsize=(8, 4), constrained_layout=True)
    rates = [s["success_rate"] for s in summary]
    ax.bar(conditions, rates, color=["#24747d", "#ba673b", "#7160a4"])
    ax.errorbar(
        conditions,
        rates,
        yerr=[
            [max(0, r - s["ci95_low"]) for r, s in zip(rates, summary)],
            [max(0, s["ci95_high"] - r) for r, s in zip(rates, summary)],
        ],
        fmt="none",
        color="black",
        capsize=5,
    )
    ax.set(
        ylim=(0, 1.08),
        ylabel="Fraction fully sorted",
        xlabel="Defect condition",
        title=f"Damage changes reachability | {trials} paired trials | 95% Wilson intervals",
    )
    fig.savefig(output / "damage.png", dpi=150)
    return {"figure": fig, "summary": summary, "rows": rows}


def _curve(result, labels, grid):
    import numpy as np

    orders = result.orders()
    values = [aggregation([labels[i] for i in order]) for order in orders]
    return np.interp(grid, np.linspace(0, 1, len(values)), values)


def clustering_study(output, trials=20, n=18, seed=29, schedulers=("random", "round_robin")):
    """Mixed policies, shuffled-label and single-policy controls, paired by trial."""
    import matplotlib.pyplot as plt
    import numpy as np

    _check_size(trials, n)
    if not schedulers or len(set(schedulers)) != len(schedulers):
        raise ValueError("provide distinct schedulers")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    grid = np.linspace(0, 1, 101)
    fig, axes = plt.subplots(
        1,
        len(schedulers),
        figsize=(7 * len(schedulers), 4.5),
        squeeze=False,
        constrained_layout=True,
    )
    rows, summaries, curve_records = [], [], {}
    for ax, scheduler in zip(axes[0], schedulers):
        curves = {"mixed": [], "shuffled_labels": [], "single_policy": []}
        for trial in range(trials):
            rng = random.Random(f"{seed}:clustering:{trial}")
            values = list(range(n))
            rng.shuffle(values)
            labels = [["bubble", "insertion", "selection"][i % 3] for i in range(n)]
            rng.shuffle(labels)
            shuffled = labels.copy()
            rng.shuffle(shuffled)
            config = Config(values, algorithms=labels, seed=seed + trial, scheduler=scheduler)
            mixed = run(config)
            single = run(replace(config, algorithms=["bubble"]))
            mixed.save(output / f"{scheduler}-trial-{trial:03d}-mixed")
            single.save(output / f"{scheduler}-trial-{trial:03d}-single")
            curves["mixed"].append(_curve(mixed, labels, grid))
            curves["shuffled_labels"].append(_curve(mixed, shuffled, grid))
            curves["single_policy"].append(_curve(single, labels, grid))
            (output / f"{scheduler}-trial-{trial:03d}-labels.json").write_text(
                json.dumps({"labels_by_id": labels, "shuffled_labels_by_id": shuffled}, indent=2)
                + "\n"
            )
            for name, result in (("mixed", mixed), ("single_policy", single)):
                rows.append(
                    {
                        "scheduler": scheduler,
                        "trial": trial,
                        "condition": name,
                        "termination": result.termination,
                        "swaps": result.summary()["swaps"],
                    }
                )
        baseline = shuffled_baseline(labels)
        boot = np.random.default_rng(seed).integers(0, trials, size=(2000, trials))
        curve_records[scheduler] = {}
        for name, color in zip(curves, ("#24747d", "#ba673b", "#7160a4")):
            array = np.asarray(curves[name])
            mean = array.mean(axis=0)
            lo, hi = np.percentile(array[boot].mean(axis=1), [2.5, 97.5], axis=0)
            ax.plot(grid, mean, label=name.replace("_", " "), color=color)
            ax.fill_between(grid, lo, hi, color=color, alpha=0.15)
            curve_records[scheduler][name] = array.tolist()
        for control in ("shuffled_labels", "single_policy"):
            delta = (np.asarray(curves["mixed"]) - np.asarray(curves[control])).mean(axis=1)
            lo, hi = np.percentile(delta[boot].mean(axis=1), [2.5, 97.5])
            summaries.append(
                {
                    "scheduler": scheduler,
                    "contrast": f"mixed - {control}",
                    "trials": trials,
                    "mean_difference": float(delta.mean()),
                    "ci95_low": float(lo),
                    "ci95_high": float(hi),
                }
            )
        ax.axhline(baseline, color="#555555", linestyle=":", label="exact shuffle expectation")
        ax.set(
            title=f"{scheduler} | {trials} trials",
            xlabel="Fraction of observed swaps",
            ylabel="Fraction of equal-label adjacent pairs",
            ylim=(0, 1),
        )
        ax.legend(fontsize=9)
    fig.suptitle("Do sorting policies cluster? Pointwise 95% bootstrap intervals")
    fig.savefig(output / "clustering.png", dpi=150)
    _write_rows(output / "trials.csv", rows)
    _write_rows(output / "summary.csv", summaries)
    (output / "curves.json").write_text(
        json.dumps({"grid": grid.tolist(), "curves": curve_records}) + "\n"
    )
    return {"figure": fig, "summary": summaries, "rows": rows}


def progress_demo(output):
    from .plotting import animate_run, plot_run

    output = Path(output)
    result = run(Config([2, 4, 1, 3], seed=2))
    result.save(output / "run")
    figure = plot_run(result)
    figure.savefig(output / "progress.png", dpi=150)
    animation = animate_run(result)
    animation.save(output / "progress.gif", writer="pillow", fps=3)
    return {"result": result, "figure": figure, "animation": animation}
