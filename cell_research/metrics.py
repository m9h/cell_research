"""Independent progress measures; no metric is a test of consciousness."""

from collections import Counter, defaultdict, deque


def measure(values, reverse=False):
    values = list(values)
    n = len(values)
    if n == 0:
        raise ValueError("cannot measure an empty array")
    ordered = sorted(values, reverse=reverse)
    ranks = defaultdict(deque)
    for i, value in enumerate(ordered):
        ranks[value].append(i)
    displacement = sum(abs(i - ranks[v].popleft()) for i, v in enumerate(values))
    wrong = (lambda a, b: a < b) if reverse else (lambda a, b: a > b)
    adjacent = sum(wrong(a, b) for a, b in zip(values, values[1:]))
    inversions = sum(wrong(values[i], values[j]) for i in range(n) for j in range(i + 1, n))
    return {
        "adjacent_errors": adjacent,
        "sortedness_percent": 100 * (n - adjacent) / n,
        "inversions": inversions,
        "rank_displacement": displacement,
    }


def aggregation(labels):
    """Fraction of adjacent pairs with equal labels (NOT the paper's cell metric)."""
    return (
        sum(a == b for a, b in zip(labels, labels[1:])) / (len(labels) - 1)
        if len(labels) > 1
        else 1.0
    )


def shuffled_baseline(labels):
    """Exact expected adjacent-pair aggregation under a uniform label permutation."""
    n = len(labels)
    return sum(k * (k - 1) for k in Counter(labels).values()) / (n * (n - 1)) if n > 1 else 1.0


def metric_history(result):
    return [
        measure([result.config.values[i] for i in order], reverse=result.config.reverse)
        for order in result.orders()
    ]
