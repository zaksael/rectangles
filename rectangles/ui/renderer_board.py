from __future__ import annotations

import pygame

from .. import constants
from ..constants import CellKind
from ..game import Game, TurnState
from ..models import Rectangle
from . import colors, layout
from .state import UIState


class BoardMixin:
    def _draw_grid_cells(self, game: Game) -> None:
        for r in range(game.board.size):
            for c in range(game.board.size):
                rect = layout.cell_rect(r, c, game.board.size)
                pygame.draw.rect(self.screen, colors.EMPTY_CELL_COLOR, rect)
                pygame.draw.rect(self.screen, colors.GRID_LINE_COLOR, rect, width=1)

    def _draw_board(self, game: Game) -> None:
        self._draw_grid_cells(game)

        self._draw_prize_cells(game)
        self._draw_pitfall_cells(game)
        self._draw_obstacles(game)

        for player in game.players.values():
            color = constants.PLAYER_COLORS[player.id]
            border = constants.PLAYER_BORDER_COLORS[player.id]
            for piece in player.pieces:
                rect = layout.piece_rect(piece.top_left, piece.width, piece.height, game.board.size)
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, border, rect, width=3)

        self._draw_last_move_highlight(game)
        self._draw_prize_capture_highlight(game)
        self._draw_walls(game)

        pygame.draw.rect(self.screen, (150, 150, 150), layout.board_rect(game.board.size), width=2)

    def _last_placed_rect(self, game: Game, upto: int | None = None) -> Rectangle | None:
        history = game.history if upto is None else game.history[:upto]
        return next((record.placed for record in reversed(history) if record.placed is not None), None)

    def _draw_last_move_highlight(self, game: Game, upto: int | None = None) -> None:
        last_placed = self._last_placed_rect(game, upto)
        if last_placed is None:
            return
        rect = layout.piece_rect(
            last_placed.top_left, last_placed.width, last_placed.height, game.board.size
        ).inflate(4, 4)
        pygame.draw.rect(self.screen, colors.LAST_MOVE_HIGHLIGHT_COLOR, rect, width=3)

    def _captured_prize_cells(self, game: Game, upto: int | None = None) -> frozenset[tuple[int, int]]:
        last_placed = self._last_placed_rect(game, upto)
        if last_placed is None:
            return frozenset()
        return game.board.cells_of_kind(CellKind.PRIZE).intersection(last_placed.cells())

    def _draw_prize_capture_highlight(self, game: Game, upto: int | None = None) -> None:
        px = layout.cell_px(game.board.size)
        for r, c in self._captured_prize_cells(game, upto):
            center = layout.cell_rect(r, c, game.board.size).center
            pygame.draw.circle(self.screen, colors.PRIZE_COLOR, center, px // 2 - 5, width=4)

    def _draw_walls(self, game: Game) -> None:
        size = game.board.size
        px = layout.cell_px(size)
        for edge in game.board.wall_edges:
            a, b = tuple(edge)
            (r1, c1), (r2, c2) = (a, b) if a <= b else (b, a)
            if r1 == r2:
                # Horizontally adjacent cells (c1 < c2): vertical boundary line between them.
                x = layout.cell_rect(r1, c2, size).left
                top = layout.cell_rect(r1, c1, size).top
                pygame.draw.line(self.screen, colors.WALL_LINE_COLOR, (x, top), (x, top + px), width=4)
            else:
                # Vertically adjacent cells (r1 < r2): horizontal boundary line between them.
                y = layout.cell_rect(r2, c1, size).top
                left = layout.cell_rect(r1, c1, size).left
                pygame.draw.line(self.screen, colors.WALL_LINE_COLOR, (left, y), (left + px, y), width=4)

    def _draw_prize_cells(self, game: Game, upto: int | None = None) -> None:
        covered = (
            None if upto is None else {cell for rect in self._placed_upto(game, upto) for cell in rect.cells()}
        )
        px = layout.cell_px(game.board.size)
        for r, c in game.board.cells_of_kind(CellKind.PRIZE):
            is_covered = (r, c) in covered if covered is not None else game.board.owner_at(r, c) is not None
            if is_covered:
                continue
            cx, cy = layout.cell_rect(r, c, game.board.size).center
            half = px // 4
            points = [(cx - half, cy - half), (cx - half, cy + half), (cx + half, cy)]
            pygame.draw.polygon(self.screen, colors.PRIZE_COLOR, points)

    def _draw_pitfall_cells(self, game: Game, upto: int | None = None) -> None:
        # Same covered-check shape as _draw_prize_cells - a pitfall is capturable
        # like a prize (not a permanent blocker like an obstacle), so its
        # marker disappears once a piece covers it.
        covered = (
            None if upto is None else {cell for rect in self._placed_upto(game, upto) for cell in rect.cells()}
        )
        px = layout.cell_px(game.board.size)
        for r, c in game.board.cells_of_kind(CellKind.PITFALL):
            is_covered = (r, c) in covered if covered is not None else game.board.owner_at(r, c) is not None
            if is_covered:
                continue
            cx, cy = layout.cell_rect(r, c, game.board.size).center
            half = px // 4
            pygame.draw.line(self.screen, colors.PITFALL_CELL_COLOR, (cx - half, cy - half), (cx + half, cy + half), width=4)
            pygame.draw.line(self.screen, colors.PITFALL_CELL_COLOR, (cx - half, cy + half), (cx + half, cy - half), width=4)

    def _draw_obstacles(self, game: Game) -> None:
        for r, c in game.board.obstacle_cells:
            pygame.draw.rect(self.screen, colors.OBSTACLE_COLOR, layout.cell_rect(r, c, game.board.size))

    def _draw_coverable_cells(self, game: Game, ui_state: UIState) -> None:
        if ui_state.current_dims is None:
            return
        w, h = ui_state.current_dims
        legal_top_lefts = game.legal_cache.get((w, h), set())
        if not legal_top_lefts:
            return

        covered: set[tuple[int, int]] = set()
        for r0, c0 in legal_top_lefts:
            for r in range(r0, r0 + h):
                for c in range(c0, c0 + w):
                    covered.add((r, c))

        px = layout.cell_px(game.board.size)
        overlay = pygame.Surface((px, px), pygame.SRCALPHA)
        overlay.fill(colors.COVERABLE_CELL_COLOR)
        for r, c in covered:
            self.screen.blit(overlay, layout.cell_rect(r, c, game.board.size).topleft)

    def _draw_ghost(self, ui_state: UIState, board_size: int) -> None:
        w, h = ui_state.current_dims
        rect = layout.piece_rect(ui_state.hover_top_left, w, h, board_size)
        overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        overlay.fill(colors.GHOST_LEGAL_COLOR if ui_state.hover_legal else colors.GHOST_ILLEGAL_COLOR)
        self.screen.blit(overlay, rect.topleft)
        pygame.draw.rect(self.screen, (30, 30, 30), rect, width=2)

    def _status_banner_message(self, game: Game) -> str | None:
        if game.state == TurnState.CHOOSING_WILDCARD:
            return f"Wildcard roll! {game.current_player.name} may change one number"
        if game.state == TurnState.SKIPPED:
            return f"{game.current_player.name} skipped - no legal placement!"
        return None

    def _draw_status_banner(self, game: Game) -> None:
        message = self._status_banner_message(game)
        if message is None:
            return
        text_surf = self.font.render(message, True, (255, 255, 255))
        banner_rect = text_surf.get_rect().inflate(48, 28)
        # Centered on the full board square (not just the current board_size's
        # smaller rect), so it stays on-screen and in the same spot regardless
        # of which board size is selected.
        banner_rect.center = (layout.BOARD_PX // 2, layout.BOARD_PX // 2)
        overlay = pygame.Surface(banner_rect.size, pygame.SRCALPHA)
        overlay.fill(colors.STATUS_BANNER_BG_COLOR)
        self.screen.blit(overlay, banner_rect.topleft)
        pygame.draw.rect(self.screen, colors.LAST_MOVE_HIGHLIGHT_COLOR, banner_rect, width=2, border_radius=8)
        self.screen.blit(text_surf, text_surf.get_rect(center=banner_rect.center))
