# Self-sorting arrays: reproducible experiments

This fork of [Zhangtaining/cell_research](https://github.com/Zhangtaining/cell_research)
adds a supported experiment runner, repairs several implementation issues, and
provides three guided notebooks for studying sorting as a model of morphogenesis.
It accompanies Zhang, Goldstein, and Levin's
[sorting study](https://arxiv.org/abs/2401.05375), discussed in Levin's
[Ingressing Minds](https://www.mdpi.com/2409-9287/11/5/161).

The experiments investigate observable behavior, robustness, and measurement.
They are not tests for consciousness or evidence of nonphysical causation.
These are new controlled experiments using repaired code, **not reproductions
of the paper's numerical figures**. See [model and measurement notes](docs/methods.md).

## Install

Python 3.10 or later. The simulation and replay commands use only the standard
library. Plotting and notebooks are optional.

```sh
git clone https://github.com/m9h/cell_research.git
cd cell_research
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[examples,dev]'
```

Alternatively, reproduce the checked-in dependency resolution with uv:

```sh
uv sync --locked --python 3.12 --extra examples --extra dev
source .venv/bin/activate
```

## First experiment

```sh
cell-sorting run --values 2 4 1 3 --seed 2 --output outputs/first
cell-sorting replay outputs/first
```

The output directory contains `result.json` (configuration, exact cell identities,
metrics, provenance, and termination reason) and `events.jsonl` (ordered cell
activations, pointer updates, and swaps). Replay re-executes the policies and checks
every event and the final summary. Existing recordings are never silently overwritten;
choose a fresh output directory for each run.

## Guided examples

| Notebook | Experiment | What to examine |
| --- | --- | --- |
| [01: What counts as progress?](examples/01_progress.ipynb) | Animate an array and compare three progress metrics | A local setback can coincide with global progress |
| [02: What does damage mean?](examples/02_damage.ipynb) | Paired intact, passive-frozen, and immovable-frozen runs | Distinguish successful repair, inaccessible targets, and run limits |
| [03: Why do algotypes cluster?](examples/03_clustering.ipynb) | Mixed policies versus shuffled labels and a single-policy control | Effect size, uncertainty, and sensitivity to scheduling |

```sh
jupyter lab examples/
```

The notebooks include executed outputs. Run all cells to create a fresh output
directory and interact with the animation. To generate the figures and raw data
without Jupyter:

```sh
MPLBACKEND=Agg cell-sorting examples --trials 20 --output outputs/examples
```

This produces a progress GIF and plot, a damage plot with success intervals,
and clustering plots for two schedulers with bootstrap intervals. Individual
recordings, labels, curves, and CSV summaries accompany the figures. Defaults are
small enough for a laptop; these are educational studies rather than powered
replication studies.

## Damage and mixtures

```sh
# IDs are initial indices, not values or changing array positions.
cell-sorting run --values 2 1 --frozen-ids 0 --frozen-mode passive --output outputs/passive
cell-sorting run --values 2 1 --frozen-ids 0 --frozen-mode immovable --output outputs/immovable

# Select exactly two distinct identities; record them in result.json.
cell-sorting run --size 30 --frozen 2 --seed 17 --output outputs/damaged

# Balanced labels shuffled independently of the initial values.
cell-sorting run --size 30 --mix bubble insertion selection --seed 29 --output outputs/mixed
```

**Passive** cells cannot initiate swaps but other cells can move them.
**Immovable** cells cannot initiate swaps or be moved. Selection cells can swap
nonadjacent positions, so they can cross a frozen barrier; bubble and insertion
cells exchange adjacent positions only. Insertion explicitly resets its prefix
check at frozen cells. These rule differences matter when interpreting recovery.

## Scheduling and termination

```sh
cell-sorting run --values 4 1 3 2 --scheduler round_robin --output outputs/round-robin
cell-sorting run --values 4 1 3 2 --scheduler threaded --max-seconds 10 --output outputs/threaded
cell-sorting replay outputs/threaded
```

All three schedulers call the same repaired `move()` methods:

- `random`: seeded uniform sampling of stable cell IDs, including frozen IDs.
- `round_robin`: cyclic activation of stable cell IDs, including frozen IDs.
- `threaded`: one OS thread per active cell identity; ordering is not reproducible
  from a seed alone. Its recorded order is replayable.

Policy randomness has a separate seeded stream per cell. A run stops as `sorted`,
`stuck`, `step_limit`, or `time_limit`. The wall-clock limit applies only to threaded
runs; deterministic runs use the activation limit. Stuck means no legal policy
action or pointer advance remains under the current rules, not mathematical
impossibility under every conceivable sorting algorithm.

## Python API

```python
from cell_research.experiment import Config, run
from cell_research.metrics import metric_history

result = run(Config([3, 1, 2], algorithms=["bubble"], seed=42))
print(result.termination, result.final_values)
print(metric_history(result))
```

## Validation

```sh
python -m pytest -q
ruff check cell_research tests scripts modules/multithread/experiment_utils.py
python scripts/execute_notebooks.py --output outputs/executed-notebooks
```

Tests cover the confirmed regressions, exhaustive four-element permutations,
duplicates and negative values, immovable identities, monotone bubble inversions,
mixtures, termination, replay (including threaded logs), tamper detection, and
small complete studies. [Validation details](docs/validation.md) include the run
used to prepare the committed notebook outputs.

## Historical code and changes

The upstream baseline is commit `1fd2bd5921c1f6b423a71f691d5189106a8a1020`.
The original sorting classes remain under `modules/multithread/` and are reused
by the new runner. [Changes and model differences](docs/methods.md) document all
policy-related repairs. Git history retains the unmodified upstream version.

`multithread_cell_sorting.py --cell_type=bubble` now forwards to the supported
threaded runner. Other root scripts, `analysis/`, and `multi_dimentions/` remain
historical exploratory code, not supported entry points or a complete reproduction
pipeline. Some require external historical data or additional ML dependencies.
The supported runner does not depend on Tk or these analysis scripts.

For legacy analyses, install `.[legacy]` and configure paths rather than editing
the original author's home directory:

```sh
export CELL_SORTING_DATA_DIR=/path/to/historical/npy-data
export CELL_SORTING_FIGURE_DIR=/path/to/figures
mkdir -p "$CELL_SORTING_FIGURE_DIR"
```

The default legacy locations are `csv/` and `outputs/legacy-figures/`, relative to
the working directory. The old Spearman-distance helper assumes values are ranks
`0..n-1`; the new rank-displacement metric handles arbitrary integer values and ties.
No upstream license file was present; this fork does not assert a new license over
the original authors' code.
