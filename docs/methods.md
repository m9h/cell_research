# Model, measurements, and interpretation

## Provenance and supported scope

Starting point: Zhangtaining/cell_research at
`1fd2bd5921c1f6b423a71f691d5189106a8a1020`.
The runner instantiates the bubble, insertion, and selection classes in that
repository, with the repairs listed below. It uses one always-active group and
disables visualization during moves. Group merging and sleeping, deprecated merge
sort, and multidimensional experiments are outside this runner's scope.

The scheduler is part of the model. Matching the paper's name for an algorithm
does not guarantee matching its dynamics or figures. Record software version,
configuration, seeds, scheduler, frozen identities and mode, stopping rule, and
measurement definition when reporting results.

## Repairs and extensions

1. Bubble and insertion `should_move()` now include legal swaps with passive frozen
   neighbors. Previously the stop predicate excluded these while the execution
   predicate allowed them. The shared legacy stop check acquires the array lock
   and also treats sleeping/moving cells as unfinished.
2. Legacy frozen-cell selection uses sampling without replacement and validates
   the requested count. New recordings contain exact, stable frozen identities.
3. Constructor defaults no longer share mutable histories or counters across
   instances. The runner explicitly shares these only within an experiment.
4. The stale command-line entry point forwards to a bounded runner with current
   constructor arguments. Deprecated merge is not exposed by that command.
5. A runtime `frozen_mode` makes passive versus immovable behavior explicit in the
   common swap method. The upstream default behavior is passive; previously the
   code contained a commented condition for refusing movement of frozen targets.
6. Insertion's prefix sentinels now use infinities, including after a frozen cell,
   supporting negative values and descending order. Its explicit frozen-cell
   prefix reset is preserved and is part of the model, not an emergent discovery.
7. Selection retains the upstream nonlocal ideal-position search, skipping
   frozen targets and attempting a swap when appropriate. Descending order scans
   from the opposite end while retaining the smaller-value comparison. The stop
   predicate counts pointer advances as progress, even when no swap occurs.
8. Moves use exception-safe lock contexts. Policy RNG objects are injectable;
   legacy callers retain the global random module, while the new runner uses
   separate seeded streams per identity.

These fixes change some trajectories and terminal states. Do not interpret the
new results as validating or invalidating published effect sizes without a
separate historical replication.

## Rule details

- **Bubble:** choose left or right with equal probability; swap adjacent values
  when their order is wrong. Choosing a blocked or absent neighbor is a no-op.
- **Insertion:** consider the left neighbor when the prefix passes its order
  check. A frozen cell resets that check. Moves remain adjacent.
- **Selection:** compare with an internal ideal-position pointer, advancing it
  past unsuitable targets. Swaps may be nonadjacent. Pointer steps must be included
  when deciding whether the system can still make progress.

Cells carry their value, policy, RNG stream, and frozen status as they move.
Cell IDs are initial array indices and remain stable even with duplicate values.
An immovable frozen cell cannot be swapped, but nonlocal selection moves can
cross its position. All cells in a run use the same sorting direction.

## Metrics

- **Adjacent errors:** number of neighboring pairs in the wrong order.
- **Sortedness:** `100 * (n - adjacent_errors) / n`, retaining the upstream
  convention that the first cell contributes one correctly ordered cell.
- **Inversions:** number of wrong-order pairs across the entire array.
- **Rank displacement:** sum of absolute distances to sorted ranks. Equal-valued
  occurrences are matched in order, so duplicate values incur no arbitrary
  identity penalty. This is Spearman footrule-style displacement, not a
  correlation coefficient.
- **Aggregation:** fraction of adjacent pairs whose labels agree. This differs
  from the paper's cell-based aggregation definition. For a uniform random
  permutation of labels with counts `n_k`, the exact expected value is
  `sum(n_k * (n_k - 1)) / (n * (n - 1))`.

Every correcting adjacent bubble swap reduces inversions by exactly one, although
adjacent errors may increase. The first notebook demonstrates this explicitly.
That observation limits what a dip in neighboring-order sortedness alone can
establish about planning or delayed gratification.

The new activation count includes no-op activations and selection pointer steps.
It is not a count of comparisons. The legacy `compare_and_swap_count` measures
availability checks, not all primitive reads; it is not used to claim efficiency.
Figures of progress use successful swaps and include the initial state.

## Controls and uncertainty

Damage trials share initial arrays, policy seeds, and requested frozen identities
between conditions. Random and round-robin schedules include frozen identities,
so paired runs receive the same activation-stream prefix. Threads exclude frozen
workers and cannot share a guaranteed schedule between conditions. Outcomes at a
limit remain reported; they are not silently treated as stuck or excluded.
Success intervals are marginal 95% Wilson binomial intervals; they do not by
themselves test a paired difference between conditions.

Clustering compares:

1. Mixed bubble/insertion/selection policies, labeled by actual policy.
2. The *same mixed trajectories* with labels shuffled across cell identities,
   preserving label counts. Each trial records that permutation.
3. Bubble-only trajectories carrying the same arbitrary labels as condition 1.

Initial values, labels, and policy/scheduling seeds are paired across conditions
where applicable. Two scheduler families run by default. Every run's termination
is saved. The x axis interpolates each trajectory onto 101 points across its
observed successful swaps, even if it did not finish sorting. This alignment can
change the appearance of transients and does not equate physical times.

Bands are pointwise 95% bootstrap intervals over independent trial seeds (2,000
resamples), not simultaneous confidence bands. Summary contrasts use each trial's
mean difference across those 101 points and a paired bootstrap. They measure
average excess aggregation, not peak clustering. A small trial count is suitable
for learning; check sensitivity to sample size, alignment, label counts, and
policy mixtures before drawing broader conclusions.

## Replay and limits

A recording stores the configuration and ordered actor IDs, swap outcomes,
post-swap identity order, and pointer updates. Replaying uses the recorded order
with fresh per-cell RNG streams, checking each event and the final summary.
Threaded trajectories can therefore be replayed even though their OS scheduling
cannot be regenerated from the seed. Replay does not reproduce elapsed time;
the recorded wall-clock stop is treated as an external event.

The current format is version 1. Exact replay assumes the same package version
and compatible Python RNG behavior. The dependency lock targets Python 3.12 for
the executed examples. For archival research, preserve the fork commit as well
as the output directory. A complete trace scales with the number of activations;
start with small arrays and bounded runs.
