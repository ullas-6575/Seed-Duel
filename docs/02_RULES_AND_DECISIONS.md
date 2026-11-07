# Seed Duel: rules and decision register

This file is the rule authority for the proposed implementation. It distinguishes the agreed discussion from implementation choices that still need confirmation. Changing a rule requires changing its tests and rule-version identifier.

## 1. Board convention

For the default 5-pit-per-player board:

- Engine indices 0–4 are P1's original bottom row, traversed left to right.
- Indices 5–9 are P2's original top row, traversed right to left.
- The path is `0,1,2,3,4,5,6,7,8,9,0,...` for both players.
- Display labels are index + 1. The top row appears visually as `10,9,8,7,6`.
- Every pit begins with 4 seeds in Round 1; total game seeds = 40.
- Keep physical row, current owner and protected/conquered status as distinct data.

Use `2 * pits_per_player * initial_seeds_per_pit` for the initial seed total. Configuration stays fixed within a match.

## 2. Agreed turn behavior

1. The player selects a nonempty normal pit on their own playable side.
2. Pick up all its seeds. Set its count to zero and put those seeds in the hand.
3. Move along the ring, dropping exactly one seed into each ordinary destination.
4. After the hand becomes empty, inspect the next eligible normal pit.
5. If it contains seeds, pick them up and continue the **same turn**.
6. If it is empty, capture from the following eligible normal pit, then end the turn.
7. Captured seeds go into the current player's captured account, not their hand.

When capture's normal target is itself empty, the historical discussion did not settle whether to capture zero or search farther. Decision D01 below must settle this. Never silently skip ordinary empty capture targets.

## 3. Agreed conquered-pit behavior

- A conquered pit stays in its original physical position but has a different owner.
- During sowing, every encounter offers a fresh **DROP** or **SKIP** choice.
- DROP deposits one seed and reduces the hand by one.
- SKIP advances past that pit without reducing the hand.
- Neither player can pick up its seeds to start a turn, continue relay, or capture.
- Relay inspection and capture targeting pass protected pits to the next eligible normal pit.
- At round settlement its owner receives all seeds there, regardless of who deposited them.

If the last seed is dropped into a protected pit, inspect the subsequent eligible normal pit as usual. A protected pit is not treated as an ordinary empty pit. Encountering several protected pits requires passing them correctly; sowing choices remain independent for each.

## 4. Round endings

### No starting move

When the next player's turn is due and their own normal playable pits contain no seeds, end the round. Do not endlessly skip that player's turn. An all-empty board is a special terminal case with nothing to collect.

### Deterministic Round 1 cycle

Check a complete checkpoint immediately before each pickup, with hand = 0. If that checkpoint repeats within the same turn under deterministic Round 1 rules, stop the turn and end the round without inventing a new capture.

Use board counts, position/next pickup, phase, player and rule-relevant state. A matching board alone is not sufficient. Reset turn-local repetition history at a new turn.

### Later rounds

A repeated state under a particular Drop/Skip policy does **not** prove a forced loop. The verified 28-batch fixture in file 06 has a terminating alternative. Later-round forced-loop termination and handling of deliberate repeated choices remain a policy decision, D06.

A computation limit may pause analysis and return `UNKNOWN` or a diagnostic. It is not evidence of a forced loop and must not silently award a winner.

## 5. Settlement and conservation

During play:

`sum(board) + hand + sum(captured) + sum(reserves) = initial_total`

Every term is nonnegative. Account for the hand even during animation and decision prompts.

At a valid hand-empty round boundary:

1. Add each pit's remaining seeds to its current owner's round earnings.
2. Clear that pit.
3. Add the owner's captured seeds exactly once.
4. Add previous reserve exactly once to create next-round available funds.
5. Move funds into board, new reserve and donations during setup; do not retain a duplicate spendable earnings account.

Historical scores can be logged, but they are not another pool of seeds. Settlement must run only once.

## 6. Agreed transition examples

These are valid examples, not a complete general later-round algorithm.

| Step, 5 pits × 4 seeds | P1 | P2 |
| --- | --- | --- |
| Round 1 earnings | 26 | 14 |
| P1 donates remainder `26 mod 4 = 2` | 24 | 16 |
| Refill original normal pits | 20 seeds in 5 pits | 16 seeds in 4 pits |
| Carry reserve | 4 | 0 |
| Ownership | 5 original pits + 1 conquered pit | 4 pits |

The conquered pit starts empty: 36 board seeds + 4 reserve = 40. The example chooses display pit 6 as the unfilled pit for illustration; the general pit selection rule is D02.

The earlier 7 × 5 example follows the same reasoning: 42/28, donate 2, refill 35/30, reserve 5/0, conquer one pit, 65 board + 5 reserve = 70.

Reserve persists: if Round 2 allocates 36 active seeds and P1 has 4 reserved, then round earnings 18/18 lead to available funds 22/18. Reserve is not an optional bonus created at settlement.

## 7. Victory and mode boundaries

Full-game victory: a player conquers all original opponent pits. A player leading in seeds after one round has not automatically won the full game.

Proposed core-mode result: compare final round seed totals; equal totals are a draw. Confirm D07 before release.

The general relationship between existing conquered territory, refilling, lost territory and possible reclamation must be resolved before the full-game mode is enabled.

## 8. Decisions to record together

| ID | Decision | Proposed starting point / constraint | Blocks |
| --- | --- | --- | --- |
| D01 | Normal capture target empty | Recommend capture zero and end turn; not yet confirmed | Core capture edge case |
| D02 | Which pits refill or become conquered? | Select a deterministic order or explicit player choice | Redistribution |
| D03 | Can conquered pits be reclaimed? | No assumed answer | Full-game transitions |
| D04 | How does setup work with existing conquests on either side? | Specify exact priority, costs, protection lifetime and ownership updates | Full-game match |
| D05 | First player and next-round starter | Recommend fixed P1 in demos; fair alternation in experiments | Play/reproducibility |
| D06 | Later forced loops, voluntary looping, whole-match repetition | Specify separate outcomes; resource limits are not proofs | Full-game termination |
| D07 | Standalone result and draws | Recommend final seed total; tie = draw | Core result screen |
| D08 | Donation generalization and setup ties | Validate formula for all admitted states; preserve every seed | Full-game setup |

For each accepted decision record: chosen rule, example, both reviewers, date, affected tests and new `rule_version`. Until then, label the relevant mode provisional or unavailable. Do not interpret this guide's recommendations as already approved childhood rules.

## 9. Decision record template

```text
ID:
Chosen behavior:
Reason:
Small before/after board example:
Accepted by:
Date:
Tests added/changed:
Rule version:
```
