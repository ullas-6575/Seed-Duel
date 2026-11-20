"""A small Pygame board that renders state produced by the headless engine."""

from __future__ import annotations

from dataclasses import dataclass
from math import sin

import pygame

from seed_duel.model import Event, GameState, Phase
from seed_duel.rules import (
    apply_protected_choice, apply_select_pit, begin_turn, initial_state,
    end_round_after_later_cycle, legal_actions, round_earnings, settle_round,
)
from seed_duel.ai.greedy import (
    choose_move as choose_greedy_move,
    choose_protected_choice as choose_greedy_protected_choice,
)
from seed_duel.ai.mcts import (
    recommend_move as recommend_mcts_move,
    recommend_protected_choice as recommend_mcts_protected_choice,
)
from seed_duel.ai.minimax import (
    Recommendation,
    recommend_move,
    recommend_protected_choice,
)


BACKGROUND = (244, 238, 224)
PANEL = (255, 251, 242)
BROWN = (71, 43, 25)
GOLD = (150, 88, 38)
GOLD_LIGHT = (209, 143, 69)
GREEN = (71, 151, 101)
RED = (177, 77, 61)
TEXT = (43, 31, 23)
MUTED = (111, 91, 73)
FELT = (207, 220, 196)
SEED_DARK = (111, 47, 24)
SEED_BASE = (201, 99, 42)
SEED_LIGHT = (245, 164, 78)
ADVISOR = (54, 116, 190)

AI_LEVEL_ALGORITHMS = {
    "easy": "greedy",
    "medium": "mcts",
    "hard": "minimax",
}
AI_NAMES = {
    "greedy": "Greedy",
    "mcts": "MCTS",
    "minimax": "Minimax Alpha-Beta",
}
AI_SHORT_NAMES = {
    "greedy": "Greedy",
    "mcts": "MCTS",
    "minimax": "Minimax AB",
}
AI_MATCHUPS = (
    ("mcts", "minimax"),
    ("greedy", "mcts"),
    ("greedy", "minimax"),
)


@dataclass(frozen=True, slots=True)
class PitView:
    index: int
    center: tuple[int, int]
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class AnimationStep:
    """One UI-only playback step reconstructed from a rules event."""

    before: GameState
    after: GameState
    event: Event
    duration_ms: int
    source_index: int | None = None
    target_index: int | None = None


class SeedDuelApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Seed Duel")
        self.screen = pygame.display.set_mode((1100, 720))
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.SysFont("arial", 32, bold=True)
        self.font = pygame.font.SysFont("arial", 20)
        self.small_font = pygame.font.SysFont("arial", 16)
        self.state = initial_state()
        self.display_state = self.state
        self.advice: Recommendation | None = recommend_move(self.state)
        self.game_started = False
        self.menu_page = "mode"
        self.menu_history: list[str] = []
        self.previous_menu_page = "mode"
        self.ai_level: str | None = None
        self.ai_matchup: tuple[str, str] | None = None
        self.events: list[Event] = []
        self.animation_steps: list[AnimationStep] = []
        self.current_step: AnimationStep | None = None
        self.step_started_at = 0
        self.animation_message = ""
        self.message = "Player 1: choose a highlighted pit."
        self.round_scores = [0, 0]
        self.draw_offer = False
        self.round_choice_offer: str | None = None
        self.loop_choice_offer = False
        self.loop_avoid_state: GameState | None = None
        self.loop_previous_choice: bool | None = None
        self.loop_dialog_message = ""
        self.game_over = False
        self.running = True
        self.pits = self._make_pit_views()
        self.two_player_rect = pygame.Rect(300, 300, 500, 70)
        self.ai_opponent_rect = pygame.Rect(300, 390, 500, 70)
        self.ai_vs_ai_rect = pygame.Rect(300, 480, 500, 70)
        self.easy_rect = pygame.Rect(300, 260, 500, 65)
        self.medium_rect = pygame.Rect(300, 345, 500, 65)
        self.hard_rect = pygame.Rect(300, 430, 500, 65)
        self.back_rect = pygame.Rect(300, 515, 500, 50)
        self.back_game_rect = pygame.Rect(650, 29, 85, 42)
        self.resign_rect = pygame.Rect(743, 29, 145, 42)
        self.restart_rect = pygame.Rect(896, 29, 160, 42)
        self.settle_rect = pygame.Rect(863, 620, 193, 42)
        self.draw_rect = pygame.Rect(863, 620, 193, 42)
        self.end_game_rect = pygame.Rect(855, 620, 98, 42)
        self.continue_rect = pygame.Rect(963, 620, 102, 42)
        self.accept_draw_rect = pygame.Rect(855, 620, 98, 42)
        self.decline_draw_rect = pygame.Rect(963, 620, 102, 42)
        self.loop_avoid_rect = pygame.Rect(330, 405, 205, 48)
        self.loop_settle_rect = pygame.Rect(565, 405, 205, 48)

    @staticmethod
    def _make_pit_views() -> tuple[PitView, ...]:
        positions: dict[int, tuple[int, int]] = {}
        for offset, index in enumerate(range(5)):
            positions[index] = (160 + offset * 138, 465)
        for offset, index in enumerate(range(9, 4, -1)):
            positions[index] = (160 + offset * 138, 240)
        return tuple(
            PitView(index, center, pygame.Rect(center[0] - 58, center[1] - 58, 116, 116))
            for index, center in positions.items()
        )

    def run(self) -> None:
        while self.running:
            self._handle_events()
            self._advance_animation()
            self._draw()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and not self.game_started:
                self._handle_menu_key(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)

    def _handle_menu_key(self, key: int) -> None:
        if self.menu_page == "mode":
            if key == pygame.K_1:
                self._start_game()
            elif key == pygame.K_2:
                self._open_menu_page("level")
            elif key == pygame.K_3:
                self._open_menu_page("matchup")
        elif key == pygame.K_ESCAPE or key == pygame.K_0:
            self._go_back()
        elif key in (pygame.K_1, pygame.K_2, pygame.K_3):
            index = key - pygame.K_1
            if self.menu_page == "matchup":
                self._start_game(ai_matchup=AI_MATCHUPS[index])
            else:
                self._start_game(("easy", "medium", "hard")[index])

    def _handle_menu_click(self, pos: tuple[int, int]) -> None:
        if self.menu_page == "mode":
            if self.two_player_rect.collidepoint(pos):
                self._start_game()
            elif self.ai_opponent_rect.collidepoint(pos):
                self._open_menu_page("level")
            elif self.ai_vs_ai_rect.collidepoint(pos):
                self._open_menu_page("matchup")
        elif self.back_rect.collidepoint(pos):
            self._go_back()
        elif self.easy_rect.collidepoint(pos):
            if self.menu_page == "matchup":
                self._start_game(ai_matchup=AI_MATCHUPS[0])
            else:
                self._start_game("easy")
        elif self.medium_rect.collidepoint(pos):
            if self.menu_page == "matchup":
                self._start_game(ai_matchup=AI_MATCHUPS[1])
            else:
                self._start_game("medium")
        elif self.hard_rect.collidepoint(pos):
            if self.menu_page == "matchup":
                self._start_game(ai_matchup=AI_MATCHUPS[2])
            else:
                self._start_game("hard")

    def _open_menu_page(self, page: str) -> None:
        self.menu_history.append(self.menu_page)
        self.menu_page = page

    def _go_back(self) -> None:
        if self.menu_history:
            self.menu_page = self.menu_history.pop()

    def _start_game(
        self,
        ai_level: str | None = None,
        ai_matchup: tuple[str, str] | None = None,
    ) -> None:
        self.previous_menu_page = self.menu_page
        self.ai_level = ai_level
        self.ai_matchup = ai_matchup
        self.game_started = True
        self.state = initial_state()
        self.display_state = self.state
        self.advice = recommend_move(self.state)
        self.events = []
        self.animation_steps = []
        self.current_step = None
        self.message = "Player 1: choose a highlighted pit."
        self.round_scores = [0, 0]
        self.draw_offer = False
        self.round_choice_offer = None
        self.loop_choice_offer = False
        self.loop_avoid_state = None
        self.loop_previous_choice = None
        self.loop_dialog_message = ""
        self.game_over = False
        if self._algorithm_for_player(self.state.player) is not None:
            self._play_ai_turn()

    def _return_to_menu(self, page: str, clear_history: bool = False) -> None:
        self.game_started = False
        self.menu_page = page
        self.ai_level = None
        self.ai_matchup = None
        if clear_history:
            self.menu_history.clear()
        self.state = initial_state()
        self.display_state = self.state
        self.advice = recommend_move(self.state)
        self.events = []
        self.animation_steps = []
        self.current_step = None
        self.loop_choice_offer = False
        self.loop_avoid_state = None
        self.loop_previous_choice = None
        self.loop_dialog_message = ""

    def _algorithm_for_player(self, player: int) -> str | None:
        if self.ai_matchup is not None:
            return self.ai_matchup[player]
        if self.ai_level is not None and player == 1:
            return AI_LEVEL_ALGORITHMS[self.ai_level]
        return None

    def _player_name(self, player: int) -> str:
        algorithm = self._algorithm_for_player(player)
        return (
            f"P{player + 1} {AI_SHORT_NAMES[algorithm]}"
            if algorithm is not None
            else f"Player {player + 1}"
        )

    def _handle_click(self, pos: tuple[int, int]) -> None:
        if not self.game_started:
            self._handle_menu_click(pos)
            return
        if self.restart_rect.collidepoint(pos):
            self._start_game(self.ai_level, self.ai_matchup)
            return
        if self.back_game_rect.collidepoint(pos):
            self._return_to_menu(self.previous_menu_page)
            return
        if self.resign_rect.collidepoint(pos):
            self._return_to_menu("mode", clear_history=True)
            return
        if self.game_over:
            return
        if self.current_step or self.animation_steps:
            return
        if self.loop_choice_offer:
            if self.loop_avoid_rect.collidepoint(pos):
                self._resolve_later_loop_offer(avoid=True)
            elif self.loop_settle_rect.collidepoint(pos):
                self._resolve_later_loop_offer(avoid=False)
            return
        if self.draw_offer:
            if self.accept_draw_rect.collidepoint(pos):
                self.game_over = True
                self.draw_offer = False
                self.message = "Draw agreed by both players. Press Restart to play again."
            elif self.decline_draw_rect.collidepoint(pos):
                self.draw_offer = False
                self.message = "Draw declined. Continue playing."
            return
        if self.round_choice_offer is not None:
            if self.accept_draw_rect.collidepoint(pos):
                choice = self.round_choice_offer
                self.round_choice_offer = None
                self._apply_round_choice(choice)
            elif self.decline_draw_rect.collidepoint(pos):
                self.round_choice_offer = None
                self.message = "Choice declined. Select End Game or Continue again."
            return
        if (
            self.state.phase in (Phase.SELECT, Phase.DROP_SKIP)
            and self._algorithm_for_player(self.state.player) is not None
        ):
            return
        if self.state.phase is Phase.SELECT and self.draw_rect.collidepoint(pos):
            if self.ai_level:
                self.game_over = True
                self.message = "Draw agreed. Press Restart to play again."
            else:
                self.draw_offer = True
                self.message = f"Player {self.state.player + 1} proposed a draw. Player {2 - self.state.player}: agree or decline."
            return
        if (self.state.phase is Phase.ROUND_END and self.state.terminal_reason != "settled"
                and self.settle_rect.collidepoint(pos)):
            self._settle_current_round()
            return
        if self.state.terminal_reason == "settled":
            choice = "end" if self.end_game_rect.collidepoint(pos) else "continue" if self.continue_rect.collidepoint(pos) else None
            if choice:
                if self.ai_level or self.ai_matchup:
                    self._apply_round_choice(choice)
                else:
                    self.round_choice_offer = choice
                    self.message = f"Player {2 - self.state.player}: agree to {('end the game' if choice == 'end' else 'continue')}?"
            return
        if self.state.phase is Phase.DROP_SKIP:
            drop: bool
            if self.accept_draw_rect.collidepoint(pos):
                before = self.state
                drop = True
            elif self.decline_draw_rect.collidepoint(pos):
                before = self.state
                drop = False
            else:
                return
            self.state, events = apply_protected_choice(self.state, drop=drop)
            if before.round_number > 1:
                self.loop_avoid_state = before
                self.loop_previous_choice = drop
                self._open_later_loop_dialog_if_available()
            self.events.extend(events)
            self._queue_turn_animation(before, self.state, events)
            self.animation_message = (
                self.loop_dialog_message
                if self.loop_choice_offer
                else "Protected pit encountered: choose Drop or Skip."
                if self.state.phase is Phase.DROP_SKIP
                else f"Player {self.state.player + 1}: choose a highlighted pit."
            )
            return
        if self.state.phase is not Phase.SELECT:
            return
        for pit in self.pits:
            if pit.rect.collidepoint(pos):
                self.loop_avoid_state = None
                self.loop_previous_choice = None
                before = self.state
                self.state, new_events = apply_select_pit(self.state, pit.index, auto_protected=False)
                self.advice = None
                self.events.extend(new_events)
                if new_events and new_events[0].kind == "IllegalAction":
                    self.message = "Choose one of your highlighted non-empty pits."
                    self.display_state = self.state
                elif self.state.phase is Phase.DROP_SKIP:
                    self._queue_turn_animation(before, self.state, new_events)
                    self.animation_message = "Protected pit encountered: choose Drop or Skip."
                elif self.state.phase is Phase.ROUND_END:
                    self._queue_turn_animation(before, self.state, new_events)
                    self.animation_message = "Round ended. Click Settle Round to calculate final totals."
                else:
                    self._queue_turn_animation(before, self.state, new_events)
                    self.animation_message = f"Player {self.state.player + 1}: choose a highlighted pit."
                return

    def _apply_round_choice(self, choice: str) -> None:
        if choice == "end":
            self.game_over = True
            p1, p2 = self.round_scores
            self.message = (f"Game drawn: {p1} - {p2}. Press Restart to play again." if p1 == p2 else
                            f"Player {1 if p1 > p2 else 2} wins: {p1} - {p2}. Press Restart to play again.")
            return
        self.state = self.state.evolve(
            phase=Phase.SELECT, terminal_reason=None,
            round_number=self.state.round_number + 1,
        )
        self.state, _ = begin_turn(self.state)
        self.display_state = self.state
        self.advice = recommend_move(self.state)
        self.events = []
        self.message = f"Round {self.state.round_number}: Player {self.state.player + 1}, choose a highlighted pit."
        if (
            self.state.phase is Phase.SELECT
            and self._algorithm_for_player(self.state.player) is not None
        ):
            self._play_ai_turn()

    def _settle_current_round(self) -> None:
        self.state, new_events = settle_round(self.state)
        self.display_state = self.state
        self.events.extend(new_events)
        totals = dict(new_events[0].data)
        p1, p2 = int(totals["player1"]), int(totals["player2"])
        self.round_scores[0] += p1
        self.round_scores[1] += p2
        self.loop_choice_offer = False
        self.loop_avoid_state = None
        self.loop_previous_choice = None
        self.loop_dialog_message = ""
        if self.state.phase is Phase.GAME_END:
            self.game_over = True
            self.message = (
                f"Draw: {self.state.terminal_reason}."
                if self.state.winner is None
                else f"Player {self.state.winner + 1} wins by {self.state.terminal_reason}."
            )
        else:
            self.message = (
                f"Round settled: {p1} - {p2}. End the game or continue. "
                f"Series: {self.round_scores[0]} - {self.round_scores[1]}."
            )

    def _open_later_loop_dialog_if_available(self) -> None:
        if (
            not self.state.loop_resolution_available
            or self.loop_avoid_state is None
            or self.loop_previous_choice is None
        ):
            return
        p1, p2 = round_earnings(self.state)
        alternate_drop = not self.loop_previous_choice
        alternate = "Drop" if alternate_drop else "Skip"
        alternate_state, _ = apply_protected_choice(
            self.loop_avoid_state, drop=alternate_drop
        )
        alternate_p1, alternate_p2 = round_earnings(alternate_state)
        self.loop_choice_offer = True
        self.loop_dialog_message = (
            f"Later-round loop detected. Settling now gives P1 {p1} and P2 {p2}. "
            f"Alternate {alternate} currently projects P1 {alternate_p1} and "
            f"P2 {alternate_p2}. Try it, or end and settle this round?"
        )
        self.message = self.loop_dialog_message

    def _resolve_later_loop_offer(self, *, avoid: bool) -> None:
        if not self.loop_choice_offer:
            return
        if avoid:
            checkpoint = self.loop_avoid_state
            previous_choice = self.loop_previous_choice
            if checkpoint is None or previous_choice is None:
                return
            alternate = not previous_choice
            self.loop_choice_offer = False
            self.loop_dialog_message = ""
            before = checkpoint
            self.state, events = apply_protected_choice(checkpoint, drop=alternate)
            self.events.append(
                Event.create(
                    "LoopAvoidanceSelected",
                    action="drop" if alternate else "skip",
                )
            )
            self.events.extend(events)
            self.loop_avoid_state = checkpoint
            self.loop_previous_choice = alternate
            self._open_later_loop_dialog_if_available()
            self._queue_turn_animation(before, self.state, events)
            self.animation_message = (
                self.loop_dialog_message
                if self.loop_choice_offer
                else "Protected pit encountered: choose Drop or Skip."
                if self.state.phase is Phase.DROP_SKIP
                else f"Alternate {'Drop' if alternate else 'Skip'} avoided the loop. "
                     f"Player {self.state.player + 1}: choose a highlighted pit."
            )
            self.message = f"Trying alternate {'Drop' if alternate else 'Skip'}..."
            return

        self.loop_choice_offer = False
        self.state, end_events = end_round_after_later_cycle(self.state)
        self.events.extend(end_events)
        self.display_state = self.state
        self._settle_current_round()

    def _queue_turn_animation(self, before: GameState, final: GameState, events: tuple[Event, ...]) -> None:
        """Build visual frames from engine events without reimplementing rules."""
        working = before
        steps: list[AnimationStep] = []
        for event in events:
            data = dict(event.data)
            if event.kind == "PitSelected":
                steps.append(AnimationStep(working, working, event, 180, target_index=int(data["index"])))
            elif event.kind == "SeedsPickedUp":
                index, amount = int(data["index"]), int(data["amount"])
                pits = list(working.pits)
                pits[index] = 0
                after = working.evolve(pits=tuple(pits), hand=amount, cursor=index)
                steps.append(AnimationStep(working, after, event, 260, source_index=index))
                working = after
            elif event.kind == "SeedDropped":
                target = int(data["index"])
                pits = list(working.pits)
                pits[target] += 1
                after = working.evolve(pits=tuple(pits), hand=working.hand - 1, cursor=target)
                steps.append(AnimationStep(working, after, event, 210, working.cursor, target))
                working = after
            elif event.kind == "ProtectedPitEncountered":
                target = int(data["index"])
                after = working.evolve(phase=Phase.DROP_SKIP, pending_protected=target)
                steps.append(AnimationStep(working, after, event, 180, target_index=target))
                working = after
            elif event.kind in ("ProtectedPitDropped", "ProtectedPitSkipped"):
                target = int(data["index"])
                pits = list(working.pits)
                hand = working.hand
                if event.kind == "ProtectedPitDropped":
                    pits[target] += 1
                    hand -= 1
                after = working.evolve(pits=tuple(pits), hand=hand, cursor=target,
                                       phase=Phase.SELECT, pending_protected=None)
                steps.append(AnimationStep(working, after, event, 210, working.cursor, target))
                working = after
            elif event.kind == "SeedsCaptured":
                index, amount, player = int(data["index"]), int(data["amount"]), int(data["player"])
                if index < 0 or amount == 0:
                    continue
                pits, captured = list(working.pits), list(working.captured)
                pits[index] = 0
                captured[player] += amount
                after = working.evolve(pits=tuple(pits), captured=tuple(captured))
                steps.append(AnimationStep(working, after, event, 360, source_index=index))
                working = after

        self.display_state = before
        self.animation_steps = steps
        self.current_step = None
        self.step_started_at = 0

    def _advance_animation(self) -> None:
        now = pygame.time.get_ticks()
        if self.current_step is None and self.animation_steps:
            self.current_step = self.animation_steps.pop(0)
            self.step_started_at = now
            return
        if self.current_step and now - self.step_started_at >= self.current_step.duration_ms:
            self.display_state = self.current_step.after
            self.current_step = None
            if not self.animation_steps:
                self.display_state = self.state
                if (
                    not self.loop_choice_offer
                    and self._algorithm_for_player(self.state.player) is not None
                    and self.state.phase in (Phase.SELECT, Phase.DROP_SKIP)
                ):
                    self._play_ai_turn()
                else:
                    self.advice = recommend_move(self.state)
                    self.message = self.animation_message

    def _play_ai_turn(self) -> None:
        algorithm = self._algorithm_for_player(self.state.player)
        if algorithm is None:
            return
        before = self.state
        acting_player = self.state.player
        decision_text: str
        if self.state.phase is Phase.DROP_SKIP:
            if algorithm == "greedy":
                drop = choose_greedy_protected_choice(self.state)
            elif algorithm == "mcts":
                choice = recommend_mcts_protected_choice(self.state, iterations=250)
                drop = choice.drop if choice else None
            else:
                choice = recommend_protected_choice(self.state, depth=4)
                drop = choice.drop if choice else None
            if drop is None:
                return
            self.state, events = apply_protected_choice(self.state, drop=drop)
            decision_text = "Drop" if drop else "Skip"
        else:
            if algorithm == "greedy":
                pit_index = choose_greedy_move(self.state)
            elif algorithm == "mcts":
                result = recommend_mcts_move(self.state, iterations=250)
                pit_index = result.pit_index if result else None
            else:
                result = recommend_move(self.state, depth=4)
                pit_index = result.pit_index if result else None
            if pit_index is None:
                return
            self.state, events = apply_select_pit(
                self.state, pit_index, auto_protected=False
            )
            decision_text = f"pit {pit_index + 1}"

        self.events.extend(events)
        self.advice = None
        if self.state.phase is Phase.ROUND_END:
            self.animation_message = "Round ended. Click Settle Round to calculate final totals."
        elif self.state.phase is Phase.DROP_SKIP:
            self.animation_message = (
                f"{self._player_name(self.state.player)} is evaluating Drop versus Skip..."
            )
        else:
            next_algorithm = self._algorithm_for_player(self.state.player)
            self.animation_message = (
                f"{self._player_name(self.state.player)} is thinking..."
                if next_algorithm is not None
                else f"Player {self.state.player + 1}: choose a highlighted pit."
            )
        self._queue_turn_animation(before, self.state, events)
        self.message = (
            f"{self._player_name(acting_player)} chose {decision_text}."
        )

    def _draw(self) -> None:
        self.screen.fill(BACKGROUND)
        if not self.game_started:
            self._draw_start_menu()
            return
        self._draw_header()
        self._draw_board()
        self._draw_event_panel()
        self._draw_footer()
        self._draw_later_loop_dialog()

    def _draw_start_menu(self) -> None:
        title = self.title_font.render("SEED DUEL", True, BROWN)
        self.screen.blit(title, title.get_rect(center=(550, 155)))
        if self.menu_page == "mode":
            prompt = "Choose a game mode  (1, 2 or 3)"
            options = (
                (self.two_player_rect, "Human vs Human"),
                (self.ai_opponent_rect, "Human vs AI"),
                (self.ai_vs_ai_rect, "AI vs AI"),
            )
        elif self.menu_page == "level":
            prompt = "Choose AI difficulty  (1, 2 or 3)"
            options = (
                (self.easy_rect, "Easy  —  Greedy"),
                (self.medium_rect, "Medium  —  Monte Carlo Tree Search"),
                (self.hard_rect, "Hard  —  Minimax"),
                (self.back_rect, "Back  (Esc or 0)"),
            )
        else:
            prompt = "Choose an AI matchup  (1, 2 or 3)"
            options = (
                (self.easy_rect, "MCTS vs Minimax Alpha-Beta"),
                (self.medium_rect, "Greedy vs MCTS"),
                (self.hard_rect, "Greedy vs Minimax Alpha-Beta"),
                (self.back_rect, "Back  (Esc or 0)"),
            )
        text = self.font.render(prompt, True, MUTED)
        self.screen.blit(text, text.get_rect(center=(550, 220)))
        for rect, label in options:
            pygame.draw.rect(self.screen, BROWN, rect, border_radius=12)
            self._center_text(label, rect, self.font, PANEL)

    def _draw_header(self) -> None:
        self.screen.blit(self.title_font.render("SEED DUEL", True, BROWN), (42, 28))
        mode = (
            f"{AI_NAMES[self.ai_matchup[0]]} vs {AI_NAMES[self.ai_matchup[1]]}"
            if self.ai_matchup is not None
            else "Human vs AI"
            if self.ai_level is not None
            else "Human vs Human"
        )
        self.screen.blit(
            self.small_font.render(
                f"Round {self.state.round_number} • {mode}", True, MUTED
            ),
            (44, 69),
        )
        pygame.draw.rect(self.screen, BROWN, self.back_game_rect, border_radius=10)
        self._center_text("Back", self.back_game_rect, self.small_font, PANEL)
        pygame.draw.rect(self.screen, RED, self.resign_rect, border_radius=10)
        self._center_text("Resign & Leave", self.resign_rect, self.small_font, PANEL)
        pygame.draw.rect(self.screen, BROWN, self.restart_rect, border_radius=10)
        self._center_text("Restart", self.restart_rect, self.font, PANEL)

    def _draw_board(self) -> None:
        board = pygame.Rect(40, 120, 790, 430)
        pygame.draw.rect(self.screen, (190, 174, 148), board.move(0, 6), border_radius=24)
        pygame.draw.rect(self.screen, FELT, board, border_radius=24)
        pygame.draw.rect(self.screen, (141, 160, 123), board, 2, border_radius=24)
        self._text(self._player_name(1).upper(), (69, 145), self.font, RED)
        self._text(self._player_name(0).upper(), (69, 505), self.font, GREEN)
        legal = set(legal_actions(self.display_state)) if not self.current_step and not self.animation_steps else set()
        for pit in self.pits:
            is_legal = pit.index in legal
            is_recommended = self.advice is not None and pit.index == self.advice.pit_index and not self.current_step
            self._draw_pit(pit, self.display_state.pits[pit.index], is_legal, is_recommended)
            self._center_text(str(pit.index + 1), pygame.Rect(pit.rect.x, pit.rect.y + 8, pit.rect.width, 20), self.small_font, PANEL)
            owner = self.display_state.owner_of(pit.index)
            marker = pygame.Rect(pit.center[0] - 22, pit.rect.y - 13, 44, 20)
            pygame.draw.rect(self.screen, GREEN if owner == 0 else RED, marker, border_radius=8)
            label = f"P{owner + 1}{' L' if self.display_state.is_protected(pit.index) else ''}"
            self._center_text(label, marker, self.small_font, PANEL)
        self._draw_flying_seed()

    def _draw_event_panel(self) -> None:
        panel = pygame.Rect(855, 120, 210, 475)
        pygame.draw.rect(self.screen, PANEL, panel, border_radius=20)
        self._text("GAME STATUS", (875, 145), self.font, BROWN)
        player_text = f"{self._player_name(self.display_state.player)} is playing..." if self.current_step else (
            "Game complete" if self.display_state.phase is Phase.GAME_END else
            "Choose Drop or Skip" if self.display_state.phase is Phase.DROP_SKIP else
            "Round complete" if self.display_state.phase is Phase.ROUND_END else
            f"{self._player_name(self.display_state.player)}'s turn"
        )
        self._text(player_text, (875, 182), self.small_font, TEXT)
        self._text(f"P1 captured: {self.display_state.captured[0]}", (875, 222), self.small_font, GREEN)
        self._text(f"P2 captured: {self.display_state.captured[1]}", (875, 248), self.small_font, RED)
        self._text(f"Seeds total: {self.display_state.seed_total()} / {self.display_state.initial_total}", (875, 285), self.small_font, TEXT)
        self._text(f"Reserves: {self.display_state.reserves[0]} / {self.display_state.reserves[1]}", (875, 307), self.small_font, TEXT)
        territory = tuple(sum(self.display_state.owner_of(i) == player for i in range(len(self.display_state.pits)))
                          for player in (0, 1))
        self._text(f"Pits owned: {territory[0]} / {territory[1]}", (875, 329), self.small_font, TEXT)
        if self.advice and not self.current_step:
            self._text(f"AI suggests: Pit {self.advice.pit_index + 1}", (875, 351), self.small_font, ADVISOR)
            self._text(f"Minimax score: {self.advice.score}", (875, 373), self.small_font, MUTED)
        pygame.draw.line(self.screen, GOLD, (875, 394), (1044, 394), 2)
        self._text("Latest events", (875, 411), self.small_font, BROWN)
        recent = self.events[-8:] or [Event.create("WaitingForMove")]
        for row, event in enumerate(recent):
            self._text(self._event_text(event.kind, dict(event.data)), (875, 434 + row * 19), self.small_font, MUTED)

    def _draw_footer(self) -> None:
        message_rect = pygame.Rect(40, 585, 790, 95)
        pygame.draw.rect(self.screen, PANEL, message_rect, border_radius=18)
        self._wrapped_text(self.message, message_rect.inflate(-30, -22), self.font, TEXT)
        if self.state.phase is Phase.ROUND_END and self.state.terminal_reason != "settled":
            pygame.draw.rect(self.screen, BROWN, self.settle_rect, border_radius=10)
            self._center_text("Settle Round", self.settle_rect, self.font, PANEL)
        elif self.state.terminal_reason == "settled" and not self.game_over:
            buttons = (((self.accept_draw_rect, "Agree"), (self.decline_draw_rect, "Decline"))
                       if self.round_choice_offer is not None else
                       ((self.end_game_rect, "End Game"), (self.continue_rect, "Continue")))
            for rect, label in buttons:
                pygame.draw.rect(self.screen, BROWN, rect, border_radius=10)
                self._center_text(label, rect, self.small_font, PANEL)
        elif (
            self.state.phase in (Phase.SELECT, Phase.DROP_SKIP)
            and not self.game_over
            and self._algorithm_for_player(self.state.player) is None
        ):
            if self.draw_offer:
                buttons = ((self.accept_draw_rect, "Agree"), (self.decline_draw_rect, "Decline"))
            elif self.state.phase is Phase.DROP_SKIP:
                buttons = ((self.accept_draw_rect, "Drop"), (self.decline_draw_rect, "Skip"))
            else:
                buttons = ((self.draw_rect, "Propose Draw"),)
            for rect, label in buttons:
                pygame.draw.rect(self.screen, BROWN, rect, border_radius=10)
                self._center_text(label, rect, self.small_font, PANEL)

    def _draw_later_loop_dialog(self) -> None:
        if (
            not self.loop_choice_offer
            or self.current_step is not None
            or self.animation_steps
        ):
            return
        shade = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        shade.fill((20, 12, 8, 150))
        self.screen.blit(shade, (0, 0))
        dialog = pygame.Rect(285, 230, 530, 255)
        pygame.draw.rect(self.screen, PANEL, dialog, border_radius=20)
        pygame.draw.rect(self.screen, GOLD, dialog, 3, border_radius=20)
        self._center_text(
            "LATER-ROUND LOOP DETECTED",
            pygame.Rect(dialog.x + 20, dialog.y + 20, dialog.width - 40, 34),
            self.font,
            BROWN,
        )
        self._wrapped_text(
            self.loop_dialog_message,
            pygame.Rect(dialog.x + 34, dialog.y + 67, dialog.width - 68, 95),
            self.small_font,
            TEXT,
        )
        alternate = "Skip" if self.loop_previous_choice else "Drop"
        buttons = (
            (self.loop_avoid_rect, f"Try {alternate}"),
            (self.loop_settle_rect, "End & Settle"),
        )
        for rect, label in buttons:
            pygame.draw.rect(self.screen, BROWN, rect, border_radius=10)
            self._center_text(label, rect, self.small_font, PANEL)

    def _draw_pit(self, pit: PitView, count: int, is_legal: bool, is_recommended: bool) -> None:
        """Draw a deep, inset wooden well rather than a flat coloured oval."""
        shadow = pit.rect.move(0, 10)
        pygame.draw.ellipse(self.screen, (20, 13, 9), shadow)
        pygame.draw.ellipse(self.screen, GREEN if is_legal else (69, 40, 22), pit.rect)
        if is_recommended:
            pulse = 3 + int((sin(pygame.time.get_ticks() / 170) + 1) * 2)
            pygame.draw.ellipse(self.screen, ADVISOR, pit.rect.inflate(pulse * 2, pulse * 2), pulse)

        outer_rim = pit.rect.inflate(-7, -8)
        pygame.draw.ellipse(self.screen, (177, 101, 45) if is_legal else GOLD, outer_rim)
        middle_rim = outer_rim.inflate(-10, -14)
        pygame.draw.ellipse(self.screen, (103, 54, 26), middle_rim)
        well = pygame.Rect(middle_rim.x + 7, middle_rim.y + 19, middle_rim.width - 14, middle_rim.height - 35)
        pygame.draw.ellipse(self.screen, (25, 15, 10), well)
        floor = well.inflate(-10, -14)
        floor.y += 6
        pygame.draw.ellipse(self.screen, (47, 27, 16), floor)
        pygame.draw.arc(self.screen, (239, 171, 91), outer_rim, 3.35, 5.95, 3)
        pygame.draw.arc(self.screen, (37, 20, 12), well, 0.0, 3.14, 3)

        self._draw_pit_seeds(floor, count)
        badge = pygame.Rect(pit.center[0] - 17, pit.center[1] + 19, 34, 22)
        pygame.draw.rect(self.screen, (33, 20, 13), badge, border_radius=10)
        self._center_text(str(count), badge, self.small_font, (255, 239, 207))

    def _draw_pit_seeds(self, inner: pygame.Rect, count: int) -> None:
        if count == 0:
            return
        offsets = ((0, 10), (-15, 4), (15, 4), (-8, -8), (8, -8), (-23, -7), (23, -7), (0, -17))
        shown = min(count, len(offsets))
        for dx, dy in offsets[:shown]:
            x, y = inner.centerx + dx, inner.centery + dy
            pygame.draw.ellipse(self.screen, (34, 18, 11), pygame.Rect(x - 7, y - 3, 15, 11))
            pygame.draw.ellipse(self.screen, SEED_DARK, pygame.Rect(x - 7, y - 6, 14, 10))
            pygame.draw.ellipse(self.screen, SEED_BASE, pygame.Rect(x - 6, y - 7, 13, 9))
            pygame.draw.ellipse(self.screen, SEED_LIGHT, pygame.Rect(x - 3, y - 6, 5, 3))

    def _draw_flying_seed(self) -> None:
        step = self.current_step
        if not step or step.event.kind != "SeedDropped" or step.source_index is None or step.target_index is None:
            return
        elapsed = pygame.time.get_ticks() - self.step_started_at
        progress = min(1.0, elapsed / step.duration_ms)
        source = self._pit_by_index(step.source_index).center
        target = self._pit_by_index(step.target_index).center
        x = int(source[0] + (target[0] - source[0]) * progress)
        y = int(source[1] + (target[1] - source[1]) * progress - 42 * sin(progress * 3.14159))
        pygame.draw.ellipse(self.screen, (31, 18, 11), pygame.Rect(x - 8, y - 2, 18, 13))
        pygame.draw.ellipse(self.screen, SEED_DARK, pygame.Rect(x - 9, y - 7, 18, 13))
        pygame.draw.ellipse(self.screen, SEED_BASE, pygame.Rect(x - 8, y - 8, 17, 12))
        pygame.draw.ellipse(self.screen, SEED_LIGHT, pygame.Rect(x - 4, y - 7, 7, 4))

    def _pit_by_index(self, index: int) -> PitView:
        return next(pit for pit in self.pits if pit.index == index)

    def _event_text(self, kind: str, data: dict[str, int | str]) -> str:
        if kind == "SeedDropped":
            return f"Drop → pit {int(data['index']) + 1}"
        if kind == "SeedsPickedUp":
            return f"Pick up {data['amount']} from {int(data['index']) + 1}"
        if kind == "SeedsCaptured":
            if int(data["index"]) < 0 or int(data["amount"]) == 0:
                return "No capture (empty target)"
            return f"Capture {data['amount']} from {int(data['index']) + 1}"
        if kind == "ProtectedPitEncountered":
            return f"Protected pit {int(data['index']) + 1}: drop or skip"
        if kind == "ProtectedPitDropped":
            return f"Drop into protected pit {int(data['index']) + 1}"
        if kind == "ProtectedPitSkipped":
            return f"Skip protected pit {int(data['index']) + 1}"
        if kind == "OwnershipChanged":
            return f"Pit {int(data['index']) + 1} transfers to P{int(data['owner']) + 1}"
        if kind == "PitReclaimed":
            return f"P{int(data['owner']) + 1} reclaims pit {int(data['index']) + 1}"
        if kind == "CycleDetected":
            if data.get("outcome") == "turn_ended":
                return "Chosen path repeated; current turn ends"
            return "Checkpoint repeated; round ends"
        if kind == "LoopAvoidanceSelected":
            return f"Try alternate {str(data['action']).title()}"
        if kind == "PositionRepeated":
            return "Position repeated; round ends"
        if kind == "PitSelected":
            return f"Select pit {int(data['index']) + 1}"
        return kind.replace("_", " ")

    def _text(self, text: str, pos: tuple[int, int], font: pygame.font.Font, color: tuple[int, int, int]) -> None:
        self.screen.blit(font.render(text, True, color), pos)

    def _center_text(self, text: str, rect: pygame.Rect, font: pygame.font.Font, color: tuple[int, int, int]) -> None:
        rendered = font.render(text, True, color)
        self.screen.blit(rendered, rendered.get_rect(center=rect.center))

    def _wrapped_text(self, text: str, rect: pygame.Rect, font: pygame.font.Font, color: tuple[int, int, int]) -> None:
        words, lines, current = text.split(), [], ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if font.size(candidate)[0] <= rect.width:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        for row, line in enumerate(lines[:3]):
            self._text(line, (rect.x, rect.y + row * 27), font, color)


def run() -> None:
    SeedDuelApp().run()
