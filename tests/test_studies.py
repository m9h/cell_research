import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from cell_research.studies import damage_study, clustering_study, progress_demo
from cell_research.experiment import replay


def test_progress_demo_exports_and_replays(tmp_path):
    demo = progress_demo(tmp_path)
    assert (tmp_path / "progress.gif").stat().st_size > 0
    assert replay(tmp_path / "run").summary() == demo["result"].summary()
    plt.close("all")


def test_damage_records_actual_counts_and_all_outcomes(tmp_path):
    result = damage_study(tmp_path, trials=2, n=4)
    assert len(result["rows"]) == 6
    assert all(r["sorted"] + r["stuck"] + r["limited"] == 2 for r in result["summary"])
    for directory in tmp_path.glob("trial-*"):
        r = replay(directory)
        assert len(r.config.frozen_ids) == (0 if directory.name.endswith("intact") else 2)
    plt.close("all")


def test_clustering_controls_are_recorded_with_paired_intervals(tmp_path):
    result = clustering_study(tmp_path, trials=2, n=6)
    assert len(result["summary"]) == 4
    assert all(s["ci95_low"] <= s["mean_difference"] <= s["ci95_high"] for s in result["summary"])
    assert len(list(tmp_path.glob("*-labels.json"))) == 4
    for directory in tmp_path.iterdir():
        if directory.is_dir():
            replay(directory)
    plt.close("all")
