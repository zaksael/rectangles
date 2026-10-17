import type { GameWireState } from './gameTypes'
import { noBreak } from './noBreak'

export function formatSigned(value: number): string | number {
  return value < 0 ? `−${-value}` : value
}

export const key = (id: number) => String(id) as '1' | '2'

export function nameOf(game: GameWireState, id: number) {
  return noBreak(game.players[key(id)].name)
}

export function reasonText(game: GameWireState): string | null {
  const { reason, playerId } = game.gameOver
  if (reason === 'boardFull') return 'no room left to build'
  if (reason === null || playerId === null) return null
  const name = nameOf(game, playerId)
  if (reason === 'playerBlocked') return `${name} had no legal move left`
  if (reason === 'skipLimit') {
    const { skipLimit } = game.board
    return `${name} hit the skip limit (${skipLimit} of ${skipLimit})`
  }
  return `${name} surrendered`
}
