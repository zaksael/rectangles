import type { GameWireState } from './gameTypes'

// The top-left of the last piece placed, read from the recent turns (pieces never overlap, so it identifies the piece).
// A skip leaves the mark where it was; only a run of skips longer than the recent turns kept on the wire loses it.
export function lastPlacedTopLeft(game: GameWireState | null | undefined): [number, number] | null {
  return game?.turn.recentTurns.findLast((turn) => turn.placed)?.placed?.topLeft ?? null
}
