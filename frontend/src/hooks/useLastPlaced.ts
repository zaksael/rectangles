import { useState } from 'react'
import type { GameWireState } from '../game/gameTypes'

interface PieceCounts {
  '1': number
  '2': number
}

// The wire has no "last move" field, so spot it by whose piece count grew. Returns that piece's top-left
// (pieces never overlap, so it identifies the piece). It stays put through skips and only changes when a
// new piece lands, so memoized consumers stay stable.
export function useLastPlaced(game: GameWireState | null | undefined): [number, number] | null {
  const [counts, setCounts] = useState<PieceCounts | null>(null)
  const [last, setLast] = useState<[number, number] | null>(null)
  if (game) {
    const now = { '1': game.players['1'].board.pieces.length, '2': game.players['2'].board.pieces.length }
    // Compared with the counts last seen, set during render so the mark is right on the same paint.
    if (counts === null || now['1'] !== counts['1'] || now['2'] !== counts['2']) {
      setCounts(now)
      if (counts) {
        for (const id of ['1', '2'] as const) {
          if (now[id] > counts[id]) {
            const pieces = game.players[id].board.pieces
            setLast(pieces[pieces.length - 1]!.topLeft)
          }
        }
      }
    }
  }
  return last
}
