# Seed Duel: AI implementation and experiments

## 1. Build agents in this order

1. Seeded random legal agent: validates the action interface.
2. Greedy/heuristic baseline: evaluates legal successors.
3. Minimax with alpha-beta and a decision budget.
4. Full-game Drop/Skip support using the same action interface.
5. Optional fuzzy scoring and MCTS, after the core is stable.

### Current implementation

The initial Round-1 implementation provides `seed_duel.ai.recommend_move(state, depth=3)`. It uses minimax with alpha-beta pruning and returns a deterministic recommended legal starting pit, score, searched depth and node count. The Pygame UI displays this as an advisor: the recommended pit receives a blue pulsing ring, but the human can still select any legal pit. It is not yet an autonomous AI player or an experiment runner.

Easy/Medium/Hard are product labels to calibrate experimentally. Do not claim MCTS is inherently stronger than minimax or that a weighted score is automatically fuzzy logic.

## 2. One shared agent interface

Proposed interface:

```python
choose_action(state, legal_actions, budget, rng) -> AgentDecision
```

Return a legal action plus optional diagnostics: nodes visited, depth completed, elapsed time and estimated value. Never let an agent directly edit the live board. Use a seeded RNG for reproducible experiments.

In Round 1, each chosen starting pit leads to a deterministic sequence until the next turn or round end. In later rounds, the same turn may contain several player decisions. `run_to_decision` must stop at each Drop/Skip encounter instead of silently choosing a default branch.

## 3. Baselines and evaluation

Start with a transparent score from a fixed player's perspective:

`value = w1 * seed_balance + w2 * legal_start_balance + w3 * territory_balance`

Suggested definitions:

- Seed balance: captured + reserves + seeds in currently owned pits, minus the opponent's corresponding total, evaluated at hand-empty checkpoints.
- Legal-start balance: number of legal starting pits for each player, evaluated only where that measure is meaningful.
- Territory balance: current owned-pit count difference, used in full-game mode.

The seed-ownership estimate is heuristic: a normal pit's seeds are not guaranteed income before settlement. Do not count captured/reserved seeds twice. At mid-turn decision states with seeds in hand, use an explicitly documented heuristic for those states or a bounded continuation; do not silently treat the hand as zero.

At a true game terminal, use a win/loss value whose magnitude exceeds all possible nonterminal heuristic values. A one-round terminal uses the confirmed standalone outcome. Keep the root player's perspective consistent throughout search.

Choose initial weights manually, write them in configuration and tune on separate positions. Report final weights and avoid testing only on the same positions used for tuning.

## 4. Minimax and alpha-beta

### Round 1

- Expand legal starting pits.
- Use the engine to resolve the complete turn, including capture and the deterministic cycle rule.
- Search the resulting opponent state, or evaluate a terminal round result.
- Count depth in completed turns and report that convention.
- Order promising moves first for better pruning.
- Use iterative deepening so a budget expiry can return the best fully completed iteration.

### Full game

- Expand `SelectPit`, `DropProtected` or `SkipProtected` according to the phase.
- Keep maximizing/minimizing according to the actual acting player.
- Do **not** switch perspective or negate a score simply because a new Drop/Skip node appears; the same player is still acting.
- Decrement turn-depth only when a turn completes.
- Add an independent decision/node/time budget so many same-turn choices cannot exhaust resources.
- Use confirmed round-transition rules before evaluating a multi-round successor.

First test minimax against exhaustive small-depth search on tiny boards. At the same depth and evaluation, alpha-beta must return the same value as unpruned minimax. Equal-value tie choices may differ if tie-breaking differs.

## 5. Cycle handling in search

Round 1 repeated complete checkpoints terminate through the agreed round rule. For later rounds, a path repeating under one action policy is not proof that every action loops. The 28-batch fixture has a five-batch escape.

For exact forced-loop analysis in a fixed turn, model reachable complete decision states as a finite graph. Mark turn-ending states and determine which nodes can reach an ending. A fully explored reachable region with no terminating route supports a forced-loop conclusion. If exploration hits a budget, return unknown.

This is reachability by the acting player during one turn, not alternating minimax at every seed drop. Whole-match repetition across turns/rounds is a separate D06 policy.

Keep engineering cutoffs distinct from actual game outcomes. An MCTS rollout cutoff may use a heuristic estimate; it must not be recorded as a real game win/draw unless the agreed game rules say so.

## 6. Optional fuzzy logic

To claim fuzzy logic, implement and document:

- Named inputs such as immediate capture potential, opponent mobility and territory benefit.
- Membership functions and their numeric domains.
- A small interpretable rule base.
- An aggregation and output/defuzzification method.
- An example showing input values, memberships, fired rules and resulting score.

Compare the fuzzy agent with a plain weighted heuristic. Do not add fuzzy logic solely as a label in the presentation.

## 7. Optional MCTS

Implement selection, expansion, simulation and backpropagation. Define reward consistently from the root player's perspective; selection must respect which player controls a decision. Consecutive Drop/Skip nodes can belong to the same player.

Use the real engine for transitions, legal actions and terminal detection. Cap rollout computation and report how nonterminal cutoffs are evaluated. Track visits and mean values. Test terminal reward signs and ownership before running large experiments.

## 8. Fair experiments

Start with a small smoke run. For a final comparison, a practical target is at least 30 paired matches per agent pair per configuration, if the time budget allows. A pair swaps player sides/starting roles under the same configuration and random seed. Report the actual sample size, not the target.

Use reproducible configurations: default 5 × 4, a smaller debugging board, and selected midgame fixtures. For identical deterministic agents, repeated identical initial games do not provide independent evidence; use varied valid starting states and report how they were generated.

Record:

| Field | Purpose |
| --- | --- |
| Commit, rule version, configuration, seed | Reproduce a match |
| Agent and parameters for each side | Know exactly what was compared |
| Decision budget and machine | Interpret timing fairly |
| Wins, losses, draws, unfinished/unknown | Avoid hiding incomplete matches |
| Seed difference / territory difference | Describe outcome beyond win rate |
| Median and p95 decision time | Assess responsiveness |
| Nodes, completed depth or rollouts | Explain search effort |
| Cycle events and illegal-action count | Check robustness |

Use equal wall-clock decision budgets for a primary comparison. You may add fixed-depth/node experiments, but label the different conditions. Exclude rendering time from search timing and report that choice.

## 9. Report conclusions honestly

Explain what the measured results support, on which boards and under which budget. If MCTS loses, report that result and discuss sample budget or evaluation limitations. Never fabricate a performance table before running the matches.

AI is ready when it returns legal actions for every tested phase, does not corrupt state, remains bounded in time, reproduces seeded runs and beats or meaningfully compares with the documented baseline.
