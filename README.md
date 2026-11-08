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

## The mathematical model

The array is a small dynamical system. Each cell has a fixed value, a stable
identity, and a sorting policy (its **algotype**). Values and policies travel with
the cell when it moves. The changing arrangement is the observable state:

$$
x(t) = (v_{\pi_t(1)}, v_{\pi_t(2)}, \ldots, v_{\pi_t(n)}),
$$

where $v_i$ is identity $i$'s value and $\pi_t$ lists the identities in their current
order. Here $t$ counts discrete activations, not physical time. Every successful
move exchanges two identities, so the multiset of values is conserved. With
distinct identities there are $n!$ possible arrangements; equal values can make
different identity arrangements look identical.

The full state also contains internal variables, especially selection cells'
search pointers. Let $z_t$ denote that complete state, $a_t$ the identity selected
by the scheduler, and $\xi_t$ the policy's random choice. One activation is

$$
z_{t+1} = T_{a_t}(z_t;\xi_t).
$$

An activation can produce a swap, advance a pointer, or do nothing. This is an
asynchronous discrete system: it does not integrate differential equations, fit
weights, or minimize a loss supplied to the cells. The metrics below are
measurements made by the experimenter. With random scheduling, it can be viewed
as a stochastic process on the complete state; array values alone omit internal
information needed to predict the next transition. For exact computer replay,
the random streams and activation order also matter.

For ascending sorting, the policies implement these different transition rules:

| Policy | Information used | Possible action |
| --- | --- | --- |
| Bubble | One randomly chosen immediate neighbor | Exchange an inverted adjacent pair |
| Insertion | Its left neighbor and an order check over the preceding prefix | Exchange with the left neighbor when the prefix check permits it |
| Selection | Its own search pointer and the cell at that position | Advance the pointer or exchange potentially nonadjacent cells |

“Cell-based” therefore does not imply that every policy has strictly local
information or motion. Insertion reads a prefix, and selection can exchange
distant cells. Frozen-cell exceptions also belong to the explicit rules; see
[the implementation details](docs/methods.md#rule-details).

The target is an ordered arrangement, $x_1\leq x_2\leq\cdots\leq x_n$. The runner
stops when it reaches that target. This global success check is not a signal
used by an individual cell to choose its move. For descending experiments,
reverse the inequalities and use descending target ranks below.

### Three different meanings of progress

Write $\mathbf{1}[P]$ for 1 when statement $P$ is true and 0 otherwise. All formulas
here describe ascending order and use one-based positions for readability;
recorded cell IDs remain zero-based.

**Adjacent errors** count only immediate neighbors:

$$
A(x) = \sum_{i=1}^{n-1}\mathbf{1}[x_i>x_{i+1}],
\qquad S(x)=100\left(1-\frac{A(x)}{n}\right).
$$

$S$ is this codebase's historical **sortedness percentage**. Its denominator is
$n$, even though there are $n-1$ adjacent pairs, so a strictly decreasing array
has sortedness $100/n$, not zero. It is neither the percentage of cells at their
final positions nor the percentage of correctly ordered pairs across the array.
Both $A=0$ and $S=100$ mean the array is sorted.

**Inversions** count *all* out-of-order pairs:

$$
I(x) = \sum_{1\leq i<j\leq n}\mathbf{1}[x_i>x_j].
$$

For distinct values, $0\leq I\leq n(n-1)/2$. Equal values do not form inversions.
For adjacent exchanges, $I$ is also the minimum number of such exchanges needed
to sort the values. Every successful correcting bubble swap reduces $I$ by
exactly one: swapping adjacent $a>b$ removes their inversion, while their total
pairwise contribution with every other cell is unchanged. Thus $I$ is a discrete
descent function for bubble swaps. This statement concerns successful swaps;
activations that do nothing leave it unchanged. It is not a claim that every
policy or damaged mixture always reaches the target.

**Rank displacement** measures total distance from sorted positions:

$$
D(x) = \sum_{i=1}^{n}|i-r_i|,
$$

where $r_i$ is the sorted destination rank assigned to the value at position $i$.
For ties, occurrences are matched in their current order to the available equal
value slots in sorted order. For example, `[2, 1, 1]` receives destination ranks
`[3, 1, 2]`, giving $D=2+1+1=4$. This avoids penalizing arbitrary identity order
among equal values. $D$ is a Spearman-footrule-style distance, not a correlation
coefficient or a count of swaps.

The first notebook makes the distinction concrete:

| Arrangement | Adjacent errors $A$ | Sortedness $S$ | Inversions $I$ | Displacement $D$ |
| --- | ---: | ---: | ---: | ---: |
| `[2, 4, 1, 3]` | 1 | 75% | 3 | 6 |
| `[2, 1, 4, 3]` | 2 | 50% | 2 | 4 |
| `[2, 1, 3, 4]` | 1 | 75% | 1 | 2 |
| `[1, 2, 3, 4]` | 0 | 100% | 0 | 0 |

The first swap exchanges 4 and 1. It improves the global pair ordering while
creating two neighboring descents in place of one. A dip in $S$ alone therefore
does not establish planning or a sacrifice of overall progress: the conclusion
depends on the observable. The plots show the initial state and each successful
swap; the event log also retains activations without swaps.

### Damage changes which states are reachable

Freezing cells changes the allowed transitions $T$, not the sorted target.
With `[2, 1]`, freezing identity 0 (value 2) in passive mode still lets the active
value 1 initiate a correcting swap. In immovable mode neither cell can exchange
with the frozen identity, making the sorted target unreachable.

More generally, with adjacent-only motion, immovable cells separate the array
into segments: values cannot cross those positions. If an immovable value or a
segment's multiset cannot match the corresponding portion of the sorted target,
global sorting is impossible under those constraints. Nonadjacent selection
swaps can cross a barrier, so this segment argument does not apply unchanged to
mixed policies. Even when a target is reachable under some hypothetical sequence
of exchanges, the implemented policies may not find it. That is why `stuck`,
`sorted`, and run limits are recorded separately.

The damage notebook estimates success probability with $\hat p=k/m$, where $k$
of $m$ trials sort successfully. Its 95% Wilson intervals describe uncertainty
over sampled trials, not uncertainty about whether a particular array is sorted.
Matched trials use the same starting arrangement and seeds across damage
conditions. These marginal intervals alone do not test the paired difference.

### Clustering needs a chance baseline

Let $\ell_i$ be the algotype label at position $i$. The examples measure
**adjacent-pair aggregation**:

$$
C(\ell)=\frac{1}{n-1}\sum_{i=1}^{n-1}\mathbf{1}[\ell_i=\ell_{i+1}],
\qquad
\mathbb E_{\mathrm{shuffle}}[C]
=\frac{\sum_k n_k(n_k-1)}{n(n-1)},\quad n>1.
$$

Here $n_k$ is the number of identities carrying label $k$. The expectation follows
by drawing two identities without replacement: there are $n(n-1)$ ordered pairs
and $n_k(n_k-1)$ same-label pairs of type $k$. With three labels occurring six
times each, the chance baseline is $5/17\approx0.294$, not exactly $1/3$.
For a single cell the implementation defines aggregation and its baseline as 1.
This pair-based metric differs from the original paper's cell-based aggregation
measure; its numbers must not be compared directly with the paper's figures.

An increase in $C$ is not by itself evidence that policies prefer their own type.
The third notebook compares actual policy labels with shuffled labels on the
**same trajectories**, and with arbitrary labels on bubble-only trajectories.
Labels travel with identities in every case. It repeats the experiment under
random and round-robin scheduling because activation order can affect clustering.

The plotted bands are pointwise 95% bootstrap intervals over independent trials.
Each curve is aligned by the fraction of its observed successful swaps, rather
than elapsed time. Paired summary contrasts average the curve difference over
that normalized trajectory and bootstrap those trial-level differences. They
measure average excess aggregation, not peak clustering or biological causation.
See [controls and uncertainty](docs/methods.md#controls-and-uncertainty) for the
precise comparison and its limitations.

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

## License

The original additions in this fork are available under the [MIT license](LICENSE),
copyright 2026 Morgan Hough. See [LICENSING.md](LICENSING.md) for the covered files
and the distinction between new contributions and inherited code.

No upstream license file was present at the recorded baseline. The original
sorting implementation remains subject to its authors' rights; the MIT grant for
our additions does not make the combined repository entirely MIT licensed.
