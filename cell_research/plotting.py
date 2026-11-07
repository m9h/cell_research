"""Optional plotting utilities; importing the simulator needs no plotting stack."""

from .metrics import metric_history


def plot_run(result):
    import matplotlib.pyplot as plt

    history = metric_history(result)
    fig, axes = plt.subplots(3, 1, figsize=(9, 7), sharex=True, constrained_layout=True)
    for ax, key, label, color in zip(
        axes,
        ("adjacent_errors", "inversions", "rank_displacement"),
        ("Neighbor-order errors", "All-pairs inversions", "Rank displacement"),
        ("#ad4c32", "#24747d", "#625096"),
    ):
        ax.plot([h[key] for h in history], color=color, marker=".", linewidth=1.5)
        ax.set_ylabel(label)
        ax.grid(alpha=0.15)
    axes[-1].set_xlabel("Successful swaps (initial state = 0)")
    fig.suptitle(
        f"Progress depends on the measure | {result.config.scheduler} | {result.termination}"
    )
    return fig


def animate_run(result, max_frames=100):
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    import numpy as np

    orders = result.orders()
    indices = np.unique(np.linspace(0, len(orders) - 1, min(len(orders), max_frames), dtype=int))
    fig, ax = plt.subplots(figsize=(9, 3.5), constrained_layout=True)
    colors = {"bubble": "#24747d", "insertion": "#ba673b", "selection": "#7160a4"}

    def draw(frame):
        ax.clear()
        order = orders[indices[frame]]
        values = [result.config.values[i] for i in order]
        bars = ax.bar(
            range(len(order)), values, color=[colors[result.config.algorithms[i]] for i in order]
        )
        span = max(values) - min(values) or 1
        ax.set_ylim(min(0, min(values)) - 0.15 * span, max(0, max(values)) + 0.25 * span)
        for bar, identity, value in zip(bars, order, values):
            frozen = identity in result.config.frozen_ids
            if frozen:
                bar.set_edgecolor("#b52222")
                bar.set_linewidth(3)
                bar.set_hatch("//")
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value,
                f"{value}{'*' if frozen else ''}",
                ha="center",
                va="bottom",
                fontsize=9,
            )
        ax.set_xlabel("Array position | * = frozen identity")
        ax.set_ylabel("Value")
        ax.set_title(f"Swap {indices[frame]} / {len(orders) - 1} | {result.config.frozen_mode}")
        return list(bars)

    return FuncAnimation(fig, draw, frames=len(indices), interval=180, blit=False)
