import type { HistoryEntry } from './gameTypes'

// The total area (w x h of every roll) a player was dealt; a wildcard roll counts its original dice, since editing the number is a choice.
export function rolledArea(history: HistoryEntry[], playerId: number): number {
  return history.filter((entry) => entry.playerId === playerId).reduce((sum, entry) => {
    const [a, b] = entry.wildcardOriginalRoll ?? entry.roll
    return sum + a * b
  }, 0)
}
