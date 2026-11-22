"""A small Pygame board that renders state produced by the headless engine."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from math import exp, hypot, pi, sin

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


BACKGROUND = (252, 244, 232)
PANEL = (255, 252, 247)
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
# Product calibration: Medium stays deliberately below the deeper Hard search.
MCTS_UI_ITERATIONS = 20
MINIMAX_UI_DEPTH = 5
MAX_HINTS_PER_ROUND = 3
PROMPT_NOTICE_MS = 1400
BOARD_RECT = pygame.Rect(40, 120, 790, 430)
PLAYER_LABEL_POSITIONS = {
    0: (69, 365),
    1: (69, 140),
}
ACCOUNT_PIT_CENTERS = {
    0: (910, 274),
    1: (1010, 274),
}


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


def _synthesize_chime(
    notes: tuple[tuple[float, int], ...],
    sample_rate: int,
    channels: int,
    volume: float = 0.35,
) -> bytes:
    """Synthesize a soft 16-bit signed PCM chime from (frequency_hz, duration_ms) notes."""
    samples = array("h")
    amplitude = int(32767 * volume)
    for frequency, duration_ms in notes:
        total = max(1, int(sample_rate * duration_ms / 1000))
        attack = max(1, int(sample_rate * 0.008))
        for i in range(total):
            t = i / sample_rate
            env = min(1.0, i / attack) * exp(-4.5 * i / total)
            wave = (
                0.82 * sin(2.0 * pi * frequency * t)
                + 0.18 * sin(4.0 * pi * frequency * t)
            )
            sample = max(-32767, min(32767, int(amplitude * env * wave)))
            for _ in range(channels):
                samples.append(sample)
    return samples.tobytes()


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
        self.advice: Recommendation | None = None
        self.hints_remaining = [MAX_HINTS_PER_ROUND, MAX_HINTS_PER_ROUND]
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
        self.sound_enabled = True
        self._sounds: dict[str, pygame.mixer.Sound] = self._init_notification_sounds()
        self.prompt_notice_kind: str | None = None
        self.prompt_notice_until = 0
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
        self.sound_rect = pygame.Rect(472, 29, 42, 42)
        self.hint_rect = pygame.Rect(522, 29, 120, 42)
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
    def _init_notification_sounds() -> dict[str, pygame.mixer.Sound]:
        """Create subtle built-in chimes without requiring external audio files."""
        try:
            mixer_info = pygame.mixer.get_init()
            if mixer_info is None:
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
                mixer_info = pygame.mixer.get_init()
            if mixer_info is None or mixer_info[1] != -16:
                return {}
            sample_rate, _, channels = mixer_info
            play_sound = pygame.mixer.Sound(
                buffer=_synthesize_chime(((659.25, 90), (880.0, 150)), sample_rate, channels)
            )
            drop_skip_sound = pygame.mixer.Sound(
                buffer=_synthesize_chime(
                    ((783.99, 80), (1046.50, 80), (783.99, 140)),
                    sample_rate,
                    channels,
                )
            )
            play_sound.set_volume(0.5)
            drop_skip_sound.set_volume(0.6)
            return {"play": play_sound, "drop_skip": drop_skip_sound}
        except pygame.error:
            return {}

    def _notify_human_prompt(self, kind: str) -> None:
        """Notify a human player with sound and a brief visual highlight."""
        self.prompt_notice_kind = kind
        self.prompt_notice_until = pygame.time.get_ticks() + PROMPT_NOTICE_MS
        if not self.sound_enabled:
            return
        sound = self._sounds.get(kind)
        if sound is not None:
            try:
                sound.play()
            except pygame.error:
                pass

    def _clear_human_prompt_notice(self) -> None:
        self.prompt_notice_kind = None
        self.prompt_notice_until = 0

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
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                self.sound_enabled = not self.sound_enabled
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
        self.advice = None
        self.hints_remaining = [MAX_HINTS_PER_ROUND, MAX_HINTS_PER_ROUND]
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
        self._clear_human_prompt_notice()
        if self._algorithm_for_player(self.state.player) is not None:
            self._play_ai_turn()
        elif self.state.phase is Phase.SELECT:
            self._notify_human_prompt("play")

    def _return_to_menu(self, page: str, clear_history: bool = False) -> None:
        self.game_started = False
        self.menu_page = page
        self.ai_level = None
        self.ai_matchup = None
        if clear_history:
            self.menu_history.clear()
        self.state = initial_state()
        self.display_state = self.state
        self.advice = None
        self.hints_remaining = [MAX_HINTS_PER_ROUND, MAX_HINTS_PER_ROUND]
        self.events = []
        self.animation_steps = []
        self.current_step = None
        self.loop_choice_offer = False
        self.loop_avoid_state = None
        self.loop_previous_choice = None
        self.loop_dialog_message = ""
        self._clear_human_prompt_notice()

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
        if self.sound_rect.collidepoint(pos):
            self.sound_enabled = not self.sound_enabled
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
        if self._can_request_hint() and self.hint_rect.collidepoint(pos):
            self._request_ai_hint()
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
            self._clear_human_prompt_notice()
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
                else:
                    self._clear_human_prompt_notice()
                    if self.state.phase is Phase.DROP_SKIP:
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
        self.advice = None
        self.hints_remaining = [MAX_HINTS_PER_ROUND, MAX_HINTS_PER_ROUND]
        self.events = []
        self.message = f"Round {self.state.round_number}: Player {self.state.player + 1}, choose a highlighted pit."
        if (
            self.state.phase is Phase.SELECT
            and self._algorithm_for_player(self.state.player) is not None
        ):
            self._play_ai_turn()
        elif self.state.phase is Phase.SELECT:
            self._notify_human_prompt("play")

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
        self._clear_human_prompt_notice()
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
                duration = min(1050, 480 + amount * 65)
                steps.append(AnimationStep(working, after, event, duration, source_index=index))
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
                    self.advice = None
                    self.message = self.animation_message
                    if (
                        not self.game_over
                        and not self.loop_choice_offer
                        and self._algorithm_for_player(self.state.player) is None
                    ):
                        if self.state.phase is Phase.DROP_SKIP:
                            self._notify_human_prompt("drop_skip")
                        elif self.state.phase is Phase.SELECT:
                            self._notify_human_prompt("play")

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
                choice = recommend_mcts_protected_choice(
                    self.state, iterations=MCTS_UI_ITERATIONS
                )
                drop = choice.drop if choice else None
            else:
                choice = recommend_protected_choice(
                    self.state, depth=MINIMAX_UI_DEPTH
                )
                drop = choice.drop if choice else None
            if drop is None:
                return
            self.state, events = apply_protected_choice(self.state, drop=drop)
            self._clear_human_prompt_notice()
            decision_text = "Drop" if drop else "Skip"
        else:
            if algorithm == "greedy":
                pit_index = choose_greedy_move(self.state)
            elif algorithm == "mcts":
                result = recommend_mcts_move(
                    self.state, iterations=MCTS_UI_ITERATIONS
                )
                pit_index = result.pit_index if result else None
            else:
                result = recommend_move(self.state, depth=MINIMAX_UI_DEPTH)
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
        self._draw_status_panel()
        self._draw_flying_seed()
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
        self._draw_sound_button()
        if self._can_request_hint():
            self._draw_hint_button()
        pygame.draw.rect(self.screen, BROWN, self.back_game_rect, border_radius=10)
        self._center_text("Back", self.back_game_rect, self.small_font, PANEL)
        pygame.draw.rect(self.screen, RED, self.resign_rect, border_radius=10)
        self._center_text("Resign & Leave", self.resign_rect, self.small_font, PANEL)
        pygame.draw.rect(self.screen, BROWN, self.restart_rect, border_radius=10)
        self._center_text("Restart", self.restart_rect, self.font, PANEL)

    def _can_request_hint(self) -> bool:
        return (
            self.game_started
            and not self.game_over
            and not self.current_step
            and not self.animation_steps
            and not self.draw_offer
            and self.round_choice_offer is None
            and not self.loop_choice_offer
            and self.state.phase is Phase.SELECT
            and self._algorithm_for_player(self.state.player) is None
        )

    def _request_ai_hint(self) -> None:
        if not self._can_request_hint():
            return
        if self.advice is not None:
            return
        player = self.state.player
        if self.hints_remaining[player] <= 0:
            self.message = f"Player {player + 1}: no AI suggestions left this round."
            return
        recommendation = recommend_move(self.state)
        if recommendation is None:
            return
        self.advice = recommendation
        self.hints_remaining[player] -= 1
        remaining = self.hints_remaining[player]
        self.message = (
            f"AI suggests Pit {recommendation.pit_index + 1} "
            f"({remaining} suggestion{'s' if remaining != 1 else ''} left this round)."
        )

    def _draw_sound_button(self) -> None:
        bg = BROWN if self.sound_enabled else MUTED
        pygame.draw.rect(self.screen, bg, self.sound_rect, border_radius=10)
        cx, cy = self.sound_rect.center
        # Draw a compact speaker icon.
        speaker = [
            (cx - 10, cy - 4),
            (cx - 5, cy - 4),
            (cx + 1, cy - 9),
            (cx + 1, cy + 9),
            (cx - 5, cy + 4),
            (cx - 10, cy + 4),
        ]
        pygame.draw.polygon(self.screen, PANEL, speaker)
        if self.sound_enabled:
            pygame.draw.arc(
                self.screen, PANEL, pygame.Rect(cx + 1, cy - 6, 8, 12), -1.0, 1.0, 2
            )
            pygame.draw.arc(
                self.screen, PANEL, pygame.Rect(cx + 3, cy - 9, 11, 18), -1.0, 1.0, 2
            )
        else:
            pygame.draw.line(self.screen, (245, 164, 150), (cx + 4, cy - 5), (cx + 12, cy + 5), 2)
            pygame.draw.line(self.screen, (245, 164, 150), (cx + 12, cy - 5), (cx + 4, cy + 5), 2)

    def _draw_hint_button(self) -> None:
        remaining = self.hints_remaining[self.state.player]
        active = self.advice is not None
        bg = ADVISOR if active else (GOLD if remaining > 0 else MUTED)
        pygame.draw.rect(self.screen, bg, self.hint_rect, border_radius=10)
        # Draw lightbulb icon on the left side of the button
        cx = self.hint_rect.x + 24
        cy = self.hint_rect.centery - 3
        bulb_color = (255, 232, 110) if (remaining > 0 or active) else (210, 200, 185)
        pygame.draw.circle(self.screen, bulb_color, (cx, cy), 8)
        pygame.draw.rect(self.screen, bulb_color, pygame.Rect(cx - 4, cy + 5, 8, 5), border_radius=2)
        pygame.draw.rect(self.screen, BROWN, pygame.Rect(cx - 4, cy + 10, 8, 3), border_radius=1)
        if remaining > 0 or active:
            for dx1, dy1, dx2, dy2 in (
                (0, -11, 0, -14),
                (-9, -8, -11, -10),
                (9, -8, 11, -10),
                (-11, 0, -14, 0),
                (11, 0, 14, 0),
            ):
                pygame.draw.line(self.screen, bulb_color, (cx + dx1, cy + dy1), (cx + dx2, cy + dy2), 2)
        text_rect = pygame.Rect(self.hint_rect.x + 40, self.hint_rect.y, self.hint_rect.width - 44, self.hint_rect.height)
        self._center_text(f"Hint {remaining}/{MAX_HINTS_PER_ROUND}", text_rect, self.small_font, PANEL)

    def _draw_board(self) -> None:
        board = BOARD_RECT
        pygame.draw.rect(self.screen, (190, 174, 148), board.move(0, 6), border_radius=24)
        pygame.draw.rect(self.screen, FELT, board, border_radius=24)
        pygame.draw.rect(self.screen, (141, 160, 123), board, 2, border_radius=24)
        self._text(self._player_name(1).upper(), PLAYER_LABEL_POSITIONS[1], self.font, RED)
        self._text(self._player_name(0).upper(), PLAYER_LABEL_POSITIONS[0], self.font, GREEN)
        legal = set(legal_actions(self.display_state)) if not self.current_step and not self.animation_steps else set()
        self._draw_protected_chains()
        for pit in self.pits:
            is_legal = pit.index in legal
            is_recommended = self.advice is not None and pit.index == self.advice.pit_index and not self.current_step
            draw_pit, count = self._capture_pit_frame(
                pit, self.display_state.pits[pit.index]
            )
            self._draw_pit(draw_pit, count, is_legal, is_recommended)
            self._center_text(str(pit.index + 1), pygame.Rect(pit.rect.x, pit.rect.y + 8, pit.rect.width, 20), self.small_font, PANEL)
            owner = self.display_state.owner_of(pit.index)
            marker = pygame.Rect(pit.center[0] - 22, pit.rect.y - 13, 44, 20)
            pygame.draw.rect(self.screen, GREEN if owner == 0 else RED, marker, border_radius=8)
            if self.display_state.is_protected(pit.index):
                self._center_text(
                    f"P{owner + 1}",
                    pygame.Rect(marker.x, marker.y, 27, marker.height),
                    self.small_font,
                    PANEL,
                )
                self._draw_lock_icon((marker.right - 9, marker.centery + 1))
            else:
                self._center_text(f"P{owner + 1}", marker, self.small_font, PANEL)
    def _capture_progress(self) -> float:
        if not self.current_step or self.current_step.duration_ms <= 0:
            return 0.0
        elapsed = pygame.time.get_ticks() - self.step_started_at
        return min(1.0, max(0.0, elapsed / self.current_step.duration_ms))

    def _capture_pit_frame(self, pit: PitView, count: int) -> tuple[PitView, int]:
        """Return the shaking capture pit and its visually remaining seeds."""
        step = self.current_step
        if (
            not step
            or step.event.kind != "SeedsCaptured"
            or step.source_index != pit.index
        ):
            return pit, count
        progress = self._capture_progress()
        shake_phase = min(1.0, progress / 0.38)
        shake = int(sin(shake_phase * 10 * 3.14159) * 7 * (1.0 - shake_phase))
        amount = int(dict(step.event.data).get("amount", 0))
        departed = min(amount, int(amount * min(1.0, progress / 0.9)))
        center = (pit.center[0] + shake, pit.center[1])
        return (
            PitView(pit.index, center, pit.rect.move(shake, 0)),
            max(0, count - departed),
        )

    def _draw_lock_icon(self, center: tuple[int, int]) -> None:
        """Draw a compact padlock inside a protected pit's owner badge."""
        cx, cy = center
        pygame.draw.arc(
            self.screen,
            (255, 236, 174),
            pygame.Rect(cx - 4, cy - 8, 8, 9),
            3.14159,
            6.28318,
            2,
        )
        pygame.draw.rect(
            self.screen,
            (255, 220, 116),
            pygame.Rect(cx - 5, cy - 3, 10, 9),
            border_radius=2,
        )
        pygame.draw.circle(self.screen, BROWN, (cx, cy + 1), 1)

    def _draw_protected_chains(self) -> None:
        """Link adjacent protected pits with visible metal chain links."""
        count = len(self.display_state.pits)
        for index in range(count):
            following = (index + 1) % count
            if not (
                self.display_state.is_protected(index)
                and self.display_state.is_protected(following)
                and self.display_state.owner_of(index)
                == self.display_state.owner_of(following)
            ):
                continue
            start = self._pit_by_index(index).center
            end = self._pit_by_index(following).center
            dx, dy = end[0] - start[0], end[1] - start[1]
            distance = hypot(dx, dy)
            if distance <= 96:
                continue
            ux, uy = dx / distance, dy / distance
            visible_length = distance - 96
            links = max(2, int(visible_length / 13))
            chain_start = (
                int(start[0] + ux * 48),
                int(start[1] + uy * 48),
            )
            chain_end = (
                int(end[0] - ux * 48),
                int(end[1] - uy * 48),
            )
            pygame.draw.line(
                self.screen, (76, 77, 78), chain_start, chain_end, 4
            )
            for link in range(links + 1):
                travel = 48 + visible_length * link / links
                point = (
                    int(start[0] + ux * travel),
                    int(start[1] + uy * travel),
                )
                color = (104, 105, 106) if link % 2 else (164, 166, 168)
                pygame.draw.circle(self.screen, (58, 59, 60), point, 6, 3)
                pygame.draw.circle(self.screen, color, point, 5, 2)

    def _draw_status_panel(self) -> None:
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
        for player in (0, 1):
            self._draw_account_pit(player, self.display_state.captured[player])
        pygame.draw.line(self.screen, GOLD, (875, 316), (1044, 316), 2)
        self._text(f"Seeds total: {self.display_state.seed_total()} / {self.display_state.initial_total}", (875, 337), self.small_font, TEXT)
        self._text(f"Reserves: {self.display_state.reserves[0]} / {self.display_state.reserves[1]}", (875, 363), self.small_font, TEXT)
        territory = tuple(sum(self.display_state.owner_of(i) == player for i in range(len(self.display_state.pits)))
                          for player in (0, 1))
        self._text(f"Pits owned: {territory[0]} / {territory[1]}", (875, 389), self.small_font, TEXT)
        if self.advice and not self.current_step:
            self._text(f"AI suggests: Pit {self.advice.pit_index + 1}", (875, 427), self.small_font, ADVISOR)
            self._text(f"Minimax score: {self.advice.score}", (875, 451), self.small_font, MUTED)

    def _draw_account_pit(self, player: int, count: int) -> None:
        """Draw one player's captured-seed account as a compact receiving pit."""
        center = ACCOUNT_PIT_CENTERS[player]
        color = GREEN if player == 0 else RED
        label_rect = pygame.Rect(center[0] - 47, 215, 94, 22)
        self._center_text(f"P{player + 1} ACCOUNT", label_rect, self.small_font, color)

        outer = pygame.Rect(center[0] - 39, center[1] - 28, 78, 56)
        pygame.draw.ellipse(self.screen, (34, 21, 14), outer.move(0, 5))
        pygame.draw.ellipse(self.screen, color, outer)
        rim = outer.inflate(-6, -6)
        pygame.draw.ellipse(self.screen, GOLD_LIGHT, rim)
        well = rim.inflate(-9, -11)
        pygame.draw.ellipse(self.screen, (37, 22, 14), well)
        floor = well.inflate(-7, -8)
        floor.y += 3
        pygame.draw.ellipse(self.screen, (52, 30, 17), floor)
        self._draw_pit_seeds(floor, count)

        badge = pygame.Rect(center[0] - 16, center[1] + 10, 32, 19)
        pygame.draw.rect(self.screen, (33, 20, 13), badge, border_radius=9)
        self._center_text(str(count), badge, self.small_font, (255, 239, 207))

    def _draw_footer(self) -> None:
        message_rect = pygame.Rect(40, 585, 790, 95)
        pygame.draw.rect(self.screen, PANEL, message_rect, border_radius=18)
        now = pygame.time.get_ticks()
        human_drop_skip = (
            self.state.phase is Phase.DROP_SKIP
            and not self.game_over
            and not self.current_step
            and not self.animation_steps
            and self._algorithm_for_player(self.state.player) is None
        )
        if human_drop_skip:
            border_width = 3 if int(now / 260) % 2 == 0 else 2
            pygame.draw.rect(self.screen, GOLD_LIGHT, message_rect, border_width, border_radius=18)
        elif self.prompt_notice_kind == "play" and now < self.prompt_notice_until:
            pygame.draw.rect(self.screen, GREEN, message_rect, 3, border_radius=18)
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
                button_bg = BROWN
            elif self.state.phase is Phase.DROP_SKIP:
                buttons = ((self.accept_draw_rect, "Drop"), (self.decline_draw_rect, "Skip"))
                button_bg = GOLD
            else:
                buttons = ((self.draw_rect, "Propose Draw"),)
                button_bg = BROWN
            for rect, label in buttons:
                pygame.draw.rect(self.screen, button_bg, rect, border_radius=10)
                if human_drop_skip:
                    pygame.draw.rect(self.screen, GOLD_LIGHT, rect, 2, border_radius=10)
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
        if not step or step.source_index is None:
            return
        progress = self._capture_progress()
        source = self._pit_by_index(step.source_index).center
        if step.event.kind == "SeedDropped" and step.target_index is not None:
            target = self._pit_by_index(step.target_index).center
            self._draw_seed_flight(source, target, progress, 42)
            return
        if step.event.kind != "SeedsCaptured":
            return
        data = dict(step.event.data)
        amount = int(data.get("amount", 0))
        player = int(data.get("player", 0))
        shown = min(amount, 10)
        for seed in range(shown):
            delay = seed * 0.045
            local_progress = (progress - delay) / max(0.01, 1.0 - delay)
            if 0.0 <= local_progress <= 1.0:
                offset = ((seed % 3 - 1) * 7, (seed % 2) * 5 - 2)
                seed_source = (source[0] + offset[0], source[1] + offset[1])
                self._draw_seed_flight(
                    seed_source,
                    ACCOUNT_PIT_CENTERS[player],
                    local_progress,
                    80 + (seed % 3) * 10,
                )

    def _draw_seed_flight(
        self,
        source: tuple[int, int],
        target: tuple[int, int],
        progress: float,
        arc_height: int,
    ) -> None:
        x = int(source[0] + (target[0] - source[0]) * progress)
        y = int(source[1] + (target[1] - source[1]) * progress - arc_height * sin(progress * 3.14159))
        pygame.draw.ellipse(self.screen, (31, 18, 11), pygame.Rect(x - 8, y - 2, 18, 13))
        pygame.draw.ellipse(self.screen, SEED_DARK, pygame.Rect(x - 9, y - 7, 18, 13))
        pygame.draw.ellipse(self.screen, SEED_BASE, pygame.Rect(x - 8, y - 8, 17, 12))
        pygame.draw.ellipse(self.screen, SEED_LIGHT, pygame.Rect(x - 4, y - 7, 7, 4))

    def _pit_by_index(self, index: int) -> PitView:
        return next(pit for pit in self.pits if pit.index == index)

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
