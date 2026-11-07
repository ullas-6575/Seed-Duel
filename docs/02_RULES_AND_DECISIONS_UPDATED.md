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

If the normal capture target is empty, the current player's turn ends immediately and 0 seeds are added to that player's captured account. Do not search farther for another capture target.

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

### Later rounds — provisional policy, not yet finalized

A repeated state under a particular Drop/Skip policy does **not** prove that every available choice loops. The proposed approach is to detect repetition on the actual chosen path and end the **current turn only**, without automatically ending the whole round. The round then continues with the next player. AI search should consider alternative Drop/Skip choices so it can avoid a voluntary loop where possible.

The user has said this proposal looks good, but D06 is explicitly **not finalized**. A computation limit may pause analysis and return `UNKNOWN` or a diagnostic. It is not evidence of a forced loop and must not silently award a winner.

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

The conquered pit starts empty: 36 board seeds + 4 reserve = 40. Pits are refilled in the agreed distribution order. Any pit that cannot be filled is locked/conquered one by one, proceeding from the applicable side. The precise traversal/side-priority for all board layouts still needs a worked example before implementation.

The earlier 7 × 5 example follows the same reasoning: 42/28, donate 2, refill 35/30, reserve 5/0, conquer one pit, 65 board + 5 reserve = 70.

Reserve persists: if Round 2 allocates 36 active seeds and P1 has 4 reserved, then round earnings 18/18 lead to available funds 22/18. Reserve is not an optional bonus created at settlement.

## 7. Victory, round order and mode boundaries

- **Full-game victory:** a player wins by conquering all original pits of the opponent. Winning one round by seeds alone does not win the full game.
- **One-round mode:** the player who captured more seeds wins; equal captured-seed totals mean a draw.
- **Next-round starter:** the player who moved second in the previous round starts the next round (alternating starter).
- **Recapture:** conquered pits may be reclaimed in a later round (D03 = A). The exact setup mechanism by which a reclaimed pit is refilled and ownership changes must follow the finalized redistribution algorithm.
- **Existing conquered pits:** they remain conquered and locked in subsequent round setups (D04 = A), unless and until reclaimed under the recapture rule. They remain protected during play. The exact interaction between the locked-pit setup rule and recapture needs a concrete worked example before coding.

## 8. Donation and redistribution decisions

- If one player is stronger by round earnings, that player donates their **entire remainder** after filling as many of their own pits as possible: `remainder = available_seeds % seeds_per_pit`.
- Add the donation to the weaker player's available seeds before filling their pits.
- If the weaker player still cannot fill a pit, the unfilled pit is locked/conquered one by one according to the agreed distribution order.
- Any seeds left with the stronger player after donation are carried as that player's reserve into the next round.
- If round earnings are equal, neither player is designated stronger; no donation is made. Remaining seeds stay with their respective players as reserve, subject to seed conservation.
- The exact traversal order for selecting unfilled pits, and the interaction with already-conquered pits/recapture, still needs a worked example.

## 9. Decision status register

| ID | Decision | Status / accepted behavior | Blocks / notes |
| --- | --- | --- | --- |
| D01 | Normal capture target empty | **AGREED:** current player's turn ends; add 0 captured seeds | Add empty-target test |
| D02 | Which pits refill or become conquered? | **PARTLY AGREED:** refill in distribution order; unfilled pits are locked/conquered one by one from the applicable side | Exact side/traversal priority needs a worked example |
| D03 | Can conquered pits be reclaimed? | **AGREED: YES** | Recapture mechanism must be specified alongside setup |
| D04 | Existing conquered pits in later setup | **AGREED:** remain conquered and locked | Reconcile with D03 recapture through an explicit example |
| D05 | Next-round starter | **AGREED:** previous round's second player starts next round | Test alternation over several rounds |
| D06 | Later-round cycle handling | **PROVISIONAL:** repeated actual path ends current turn only; round continues; AI should consider alternative choices | User likes proposal but will finalize later; do not treat as final rule |
| D07 | One-round winner and draw | **AGREED:** more captured seeds wins; equal totals = draw | Result-screen test |
| D08 | Donation and redistribution | **AGREED:** stronger player donates entire remainder; if weaker still cannot fill a pit, it is conquered; equal earnings means no stronger player/no donation | Need edge-case examples and exact pit order |

For each accepted decision record: chosen rule, example, both reviewers, date, affected tests and new `rule_version`. Until then, label unresolved mechanics provisional or unavailable. Do not interpret recommendations as agreed rules unless marked **AGREED**.

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
