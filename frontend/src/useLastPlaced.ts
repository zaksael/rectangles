import { useRef } from 'react'
import type { GameWireState } from './gameTypes'

// The wire has no "last move" field, so spot it by whose piece count grew. Returns that piece's top-left
// (pieces never overlap, so it identifies the piece). It stays put through skips and only changes when a
// new piece lands, so memoized consumers stay stable.
export function useLastPlaced(game: GameWireState | null | undefined): [number, number] | null {
  const countsRef = useRef<Record<string, number> | null>(null)
  const lastRef = useRef<[number, number] | null>(null)
  if (game) {
    const counts = { '1': game.players['1'].board.pieces.length, '2': game.players['2'].board.pieces.length }
    const prev = countsRef.current
    if (prev) {
      for (const id of ['1', '2'] as const) {
        if (counts[id] > prev[id]) {
          const pieces = game.players[id].board.pieces
          lastRef.current = pieces[pieces.length - 1].topLeft
        }
      }
    }
    countsRef.current = counts
  }
  return lastRef.current
}
