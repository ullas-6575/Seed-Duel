# Seed Duel rules

This document records the implemented rules for the current game.

## Board and ownership

- The default board has ten pits and forty seeds. Engine indices 0–4 are P1's physical row; 5–9 are P2's physical row. Sowing follows indices in ascending cyclic order.
- Each pit has a permanent physical row, a current owner, and a protected flag. Ownership changes only at settlement.
- Normal pits owned by the current player are legal starting pits. Protected pits cannot be picked up, relayed from, or captured.

## Turn and protected-pit actions

Pick up all seeds in a legal pit, sow one at a time, and relay from the next eligible normal pit when it contains seeds. When that pit is empty, capture from the following eligible normal pit and end the turn. An empty capture target awards zero seeds.

Every time sowing reaches a protected pit, a human chooses:

- **Drop:** put one seed in the protected pit and reduce the hand by one.
- **Skip:** advance past the pit without reducing the hand.

Each protected-pit encounter is a separate choice. Inspection and capture pass protected pits. The AI currently chooses Drop automatically.

## Round endings and repetition

A round ends when the next player has no legal starting pit, the board is empty, a hand-empty checkpoint repeats within a turn, or a complete position repeats across turns. The in-turn key includes board, ownership, protection, accounts, player, and cursor. The between-turn key includes board, ownership, protection, captures, reserves, player, and next starter.

After settlement, a previously settled complete position is a draw. The implementation detects repetition on the actual path; it does not prove that all alternate Drop/Skip routes also loop.

## Settlement

At a round boundary, each player's pool is their captures, reserve, and all seeds in pits they own, including protected pits. Before ordinary refills, an original owner may reclaim captured pits in ascending index order by spending four seeds for each. Reclaimed pits become normal. Then refill remaining owned pits in ascending pit-index order, four seeds per pit. If the pool cannot fill an owned pit, transfer that empty pit to the other player. It is protected while owned by the opponent. Unspent seeds remain in that player's reserve. There is no donation.

Settlement runs once. Captures reset to zero after they enter the pool, and the seed total remains conserved across board, hand, captures, and reserves.

## Game result and round choice

- A player who owns all ten pits wins immediately after settlement.
- If neither player has a legal move after settlement, the player with more owned pits wins; equal territory is a draw.
- Otherwise, players can end the game by agreement or continue into the prepared next round. The next round starter alternates.
- A draw can be proposed during a round. The other human may agree or decline; an AI opponent agrees automatically.

## Known AI limit

The AI evaluates pit selections with the existing greedy, MCTS, and minimax strategies. At protected pits it automatically chooses Drop; it does not search the alternative Skip route. Repetition detection covers the path actually played and is not an exhaustive proof over alternate routes.
