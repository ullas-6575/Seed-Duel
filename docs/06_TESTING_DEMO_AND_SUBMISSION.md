# Seed Duel: testing, demo and final submission

Use these fixtures as acceptance criteria. Arrays use 0-based engine path order, with display labels equal to index + 1. Check file 02 for unresolved decisions before encoding additional cases.

## 1. Test layers

| Layer | What to check |
| --- | --- |
| Rule unit tests | Pickup, one-seed drop, capture, ownership, reserves |
| State-machine tests | Turn continuation, next player, terminal phase |
| Regression fixtures | The exact boards below |
| Invariant/property tests | Conservation, nonnegative counts, no illegal protected pickup |
| Integration | Engine event stream and UI final snapshot agree |
| AI | Legal actions, unchanged inputs, budgets, score perspective |
| Manual release | Install, all modes, restart, resize, quit, demo |

Run focused tests while implementing a feature, then the complete suite before merging a rule change or tagging a release. Fix a reported bug with a minimal replay and regression test.

## 2. Essential exact fixtures

### T01: ordinary Round 1 turn

Initial board: `[4,4,4,4,4,4,4,4,4,4]`. P1 starts at index 0 (display pit 1). All pits normal, captures/reserves zero.

Expected sequence:

1. Pick up 4 from index 0.
2. Drop into indices 1,2,3,4; hand reaches zero.
3. Inspect index 5, pick up its 4 seeds for relay.
4. Drop into indices 6,7,8,9.
5. Index 0 is empty; capture 5 from index 1.
6. End P1's turn. P2 can play.

Expected board: `[0,0,5,5,5,0,5,5,5,5]`. Captures `[5,0]`, hand 0, reserves `[0,0]`. Exactly 8 individual seed drops and 2 pickups. Total remains 40 after every event.

### T02: forced Round 1 loop

Checkpoint board: `[1,0,2,1,2,1,0,2,1,0]`; current player P1; next pickup index 4; hand 0; all pits normal. Captures `[16,14]`, reserves `[0,0]`.

After exactly **40 sowing batches and 70 individual seed drops**, the same board and next-pickup index return at the same phase/player. End the round without a new capture.

Bottom row sum = 6, top row sum = 4. Settlement produces final totals `[22,18]`, board all zero, total 40. Verify settlement is not applied twice.

### T03: incoming player has no seeds

Board `[0,0,0,0,0,2,1,3,0,4]`, incoming player P1, captures `[18,12]`, reserves zero, hand zero. P1 cannot start. End round and give the remaining 10 seeds to P2: totals `[18,22]`.

### T04: all-empty terminal snapshot

Board all zero, captures `[24,16]`, reserves zero, hand zero. No transfer occurs; final totals stay `[24,16]`. This is a terminal-state fixture, not a claim about the move sequence that produced it.

### T05: first transition example

Settled funds `[26,14]`, five original pits per player, fill cost 4. Use a fixture-specific approved ordering that leaves index 5 unfilled for P2.

Expected donation 2 from P1 to P2; board `[4,4,4,4,4,0,4,4,4,4]`; reserves `[4,0]`; index 5 owned by P1 and protected; P1 owns 6 pits, P2 owns 4. Board36 + reserve4 = 40. Treat the general ordering as D02, not as confirmed by this fixture.

### T06: independent Drop/Skip branches

After picking up index 4 in T05: board `[4,4,4,4,0,0,4,4,4,4]`, hand4, reserves `[4,0]`; next destination index5 is protected.

- DROP: index5 becomes1, hand3; next normal drop at index6 makes it5, hand2.
- SKIP from the original checkpoint: index5 stays0, hand4; next normal drop at index6 makes it5, hand3.

Reset to the same original checkpoint before comparing branches. A future encounter must prompt a fresh choice.

### T07: protected relay bypass

Board `[1,1,1,2,1,8,3,1,1,1]`; protected index5 belongs to P1; captures `[8,8]`; reserves `[4,0]`; hand0. Last drop was index4.

Pass index5 without removing its8 seeds. Pick up the3 from index6 into the hand; index6 becomes0. The same turn continues and total stays40.

### T08: protected capture bypass

Board `[1,1,1,2,0,8,3,1,1,2]`; P2 acting; protected index5 owned by P1; captures `[8,8]`; reserves `[4,0]`; hand0. Last drop was index3.

Index4 is empty. The capture target index5 is protected, so capture3 from normal index6. Captures become `[8,11]`, index6 becomes0, protected index5 remains8. End P2's turn.

### T09: avoidable later-round loop

Board `[3,1,0,1,0,0,2,1,0,0]`; P1 acting; next pickup index1; hand0. Indices5 and9 are protected and owned by P1. Captures `[12,12]`, reserves `[8,0]`.

- Always SKIP protected pits during sowing: the same checkpoint returns after **28 batches**.
- From the same starting checkpoint, take DROP when reached: the first four batches match the SKIP path; batch5 drops one seed from index4 into protected index5. Index6 is then empty, so capture2 from index7 and end the turn.

Final board for the terminating branch: `[0,1,2,1,0,1,0,0,1,0]`, captures `[14,12]`, reserves `[8,0]`, hand0. Board6 + captures26 + reserve8 = 40.

This proves the SKIP-policy cycle is avoidable in this fixture. It does not prove all later-round loops have an escape.

### T10: settlement ownership and reserve

Use board `[1,1,1,2,0,8,3,1,1,2]`, protected index5 owned by P1, captures `[8,8]`, reserves `[4,0]`, valid round-end phase.

P1 collects bottom5 + protected8 =13. P2 collects7. Next-round available funds: P1 `8+13+4=25`, P2 `8+7=15`. Clear board and transfer old live accounts without duplication.

### T11: winner predicate

Construct an ownership state where P1 owns all original P2 pits. Expect P1 full-game victory and no new round. With even one original P2 pit still owned by P2, this particular victory predicate is false. A predicate test does not establish how the ownership state is reached.

## 3. Additional edge tests

- Invalid, opponent, empty and protected starting selections leave state unchanged.
- One seed, wraparound and multiple full laps work.
- Consecutive protected pits do not consume seeds on SKIP.
- DROP into a protected pit can empty the hand correctly.
- No eligible normal target returns an explicit rule/terminal result, never an infinite traversal.
- Same board with a different cursor/player/phase is not the same complete checkpoint.
- A resource-limit result is not mislabeled as a proven loop.
- UI step and auto playback produce identical final states.
- Restart during AI thinking discards stale results.
- Search does not modify its input state or sibling branches.
- Accepted D01–D08 decisions each receive positive and boundary examples.
- Settlement and setup remain conservative and cannot run twice accidentally.

## 4. Demo plan: approximately 8–10 minutes

1. Introduce the problem, names, course and actual delivered scope.
2. Show T01 step by step: pickup, individual drops, relay, capture, turn end.
3. Show one no-move round ending and the T02 forced loop; fast-forward repetitive batches.
4. Show one-round scoring versus whole-game victory.
5. If implemented, show T05 redistribution, protected ownership and T06 choices.
6. Show the T09 SKIP loop and terminating DROP alternative.
7. Let the human play against AI and explain one selected move.
8. Show the real benchmark table and state the limitations.

Use fixtures for predictable demonstrations and say they are fixtures. Also demonstrate a real playable session. Keep a recording as backup if permitted, but do not present a recording as live play.

## 5. Final report structure

- Problem and project objective.
- Confirmed rules, scope and unresolved/omitted features.
- State representation, architecture and event-based animation.
- Implemented algorithms with pseudocode and actual parameters.
- Cycle handling and the two contrasting fixtures.
- Test method and evidence, including seed conservation.
- Experimental setup, actual results and interpretation.
- Limitations, future work and actual contribution statement.
- References for algorithms or external code/assets actually used.

Do not claim MCTS, fuzzy logic or full-game support if only planned. Include citations in the report after consulting the sources you actually use.

## 6. Release checklist

- [ ] Rule version frozen; no unresolved decision is silently active.
- [ ] Relevant automated tests pass.
- [ ] Source launches from a clean checkout on both teammates' machines.
- [ ] Tested Python and dependency versions recorded.
- [ ] Install/run/test instructions verified verbatim.
- [ ] Every advertised mode works, including game-over and restart.
- [ ] AI decisions are bounded and legal.
- [ ] Benchmark files include seeds, budgets, version and sample size.
- [ ] No absolute developer-machine paths or missing assets.
- [ ] Report, presentation and code describe the same delivered scope.
- [ ] Both members rehearse the demo and viva.
- [ ] Submission archive is opened and tested after packaging.
- [ ] Follow the teacher's required naming, upload method and deadline.

Suggested final package: source, tested requirements, six updated guides, tests/fixtures, report, PPTX, benchmark summary and any permitted demo recording. Add a runnable executable only if needed and tested.

## 7. Viva questions both members should answer

Why does an empty next pit end a turn rather than necessarily a round? Why must the hand enter the conservation equation? Why are owner and physical row different fields? What state is hashed for a cycle? Why is a 28-batch repetition not forced? How does alpha-beta preserve minimax's value? Why do same-player Drop/Skip nodes not alternate the minimax role? How were the agents compared fairly? Which full-game rules or features remain unimplemented?
