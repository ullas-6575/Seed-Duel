"""A small Pygame board that renders state produced by the headless engine."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from seed_duel.model import Event, GameState, Phase
from seed_duel.rules import apply_select_pit, initial_state, legal_actions, settle_round


BACKGROUND = (244, 238, 224)
PANEL = (255, 251, 242)
BROWN = (85, 55, 37)
GOLD = (205, 153, 65)
GOLD_LIGHT = (235, 199, 129)
GREEN = (74, 128, 85)
RED = (170, 77, 66)
TEXT = (46, 35, 28)
MUTED = (116, 98, 82)


@dataclass(frozen=True, slots=True)
class PitView:
    index: int
    center: tuple[int, int]
    rect: pygame.Rect


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
        self.events: list[Event] = []
        self.message = "Player 1: choose a highlighted pit."
        self.running = True
        self.pits = self._make_pit_views()
        self.restart_rect = pygame.Rect(896, 29, 160, 42)
        self.settle_rect = pygame.Rect(863, 620, 193, 42)

    @staticmethod
    def _make_pit_views() -> tuple[PitView, ...]:
        positions: dict[int, tuple[int, int]] = {}
        for offset, index in enumerate(range(5)):
            positions[index] = (210 + offset * 150, 465)
        for offset, index in enumerate(range(9, 4, -1)):
            positions[index] = (210 + offset * 150, 240)
        return tuple(
            PitView(index, center, pygame.Rect(center[0] - 58, center[1] - 58, 116, 116))
            for index, center in positions.items()
        )

    def run(self) -> None:
        while self.running:
            self._handle_events()
            self._draw()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)

    def _handle_click(self, pos: tuple[int, int]) -> None:
        if self.restart_rect.collidepoint(pos):
            self.state = initial_state()
            self.events = []
            self.message = "Player 1: choose a highlighted pit."
            return
        if self.state.phase is Phase.ROUND_END and self.settle_rect.collidepoint(pos):
            self.state, new_events = settle_round(self.state)
            self.events.extend(new_events)
            p1, p2 = self.state.captured
            if p1 == p2:
                self.message = f"Round draw: {p1} - {p2}. Press Restart to play again."
            else:
                winner = 1 if p1 > p2 else 2
                self.message = f"Player {winner} wins: {p1} - {p2}. Press Restart to play again."
            return
        if self.state.phase is not Phase.SELECT:
            return
        for pit in self.pits:
            if pit.rect.collidepoint(pos):
                self.state, new_events = apply_select_pit(self.state, pit.index)
                self.events.extend(new_events)
                if new_events and new_events[0].kind == "IllegalAction":
                    self.message = "Choose one of your highlighted non-empty pits."
                elif self.state.phase is Phase.ROUND_END:
                    self.message = "Round ended. Click Settle Round to calculate final totals."
                else:
                    self.message = f"Player {self.state.player + 1}: choose a highlighted pit."
                return

    def _draw(self) -> None:
        self.screen.fill(BACKGROUND)
        self._draw_header()
        self._draw_board()
        self._draw_event_panel()
        self._draw_footer()

    def _draw_header(self) -> None:
        self.screen.blit(self.title_font.render("SEED DUEL", True, BROWN), (42, 28))
        self.screen.blit(self.small_font.render("Round 1 • Relay sowing and capture", True, MUTED), (44, 69))
        pygame.draw.rect(self.screen, BROWN, self.restart_rect, border_radius=10)
        self._center_text("Restart", self.restart_rect, self.font, PANEL)

    def _draw_board(self) -> None:
        pygame.draw.rect(self.screen, PANEL, pygame.Rect(40, 120, 790, 430), border_radius=24)
        self._text("PLAYER 2", (69, 145), self.font, RED)
        self._text("PLAYER 1", (69, 505), self.font, GREEN)
        legal = set(legal_actions(self.state))
        for pit in self.pits:
            is_legal = pit.index in legal
            pygame.draw.ellipse(self.screen, GOLD_LIGHT if is_legal else GOLD, pit.rect)
            pygame.draw.ellipse(self.screen, GREEN if is_legal else BROWN, pit.rect, 4)
            self._center_text(str(pit.index + 1), pygame.Rect(pit.rect.x, pit.rect.y + 13, pit.rect.width, 26), self.small_font, BROWN)
            self._center_text(str(self.state.pits[pit.index]), pygame.Rect(pit.rect.x, pit.rect.y + 43, pit.rect.width, 45), self.title_font, TEXT)

    def _draw_event_panel(self) -> None:
        panel = pygame.Rect(855, 120, 210, 475)
        pygame.draw.rect(self.screen, PANEL, panel, border_radius=20)
        self._text("GAME STATUS", (875, 145), self.font, BROWN)
        player_text = "Round complete" if self.state.phase is Phase.ROUND_END else f"Player {self.state.player + 1}'s turn"
        self._text(player_text, (875, 182), self.small_font, TEXT)
        self._text(f"P1 captured: {self.state.captured[0]}", (875, 222), self.small_font, GREEN)
        self._text(f"P2 captured: {self.state.captured[1]}", (875, 248), self.small_font, RED)
        self._text(f"Seeds total: {self.state.seed_total()} / {self.state.initial_total}", (875, 285), self.small_font, TEXT)
        pygame.draw.line(self.screen, GOLD, (875, 322), (1044, 322), 2)
        self._text("Latest events", (875, 341), self.small_font, BROWN)
        recent = self.events[-8:] or [Event.create("WaitingForMove")]
        for row, event in enumerate(recent):
            self._text(self._event_text(event.kind, dict(event.data)), (875, 370 + row * 25), self.small_font, MUTED)

    def _draw_footer(self) -> None:
        message_rect = pygame.Rect(40, 585, 790, 95)
        pygame.draw.rect(self.screen, PANEL, message_rect, border_radius=18)
        self._wrapped_text(self.message, message_rect.inflate(-30, -22), self.font, TEXT)
        if self.state.phase is Phase.ROUND_END:
            pygame.draw.rect(self.screen, BROWN, self.settle_rect, border_radius=10)
            self._center_text("Settle Round", self.settle_rect, self.font, PANEL)

    def _event_text(self, kind: str, data: dict[str, int | str]) -> str:
        if kind == "SeedDropped":
            return f"Drop → pit {int(data['index']) + 1}"
        if kind == "SeedsPickedUp":
            return f"Pick up {data['amount']} from {int(data['index']) + 1}"
        if kind == "SeedsCaptured":
            return f"Capture {data['amount']} from {int(data['index']) + 1}"
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
