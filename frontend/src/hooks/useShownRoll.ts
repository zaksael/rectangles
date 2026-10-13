import { useState } from 'react'

interface ShownRoll {
  values: [number, number]
  owner: '1' | '2'
}

// The wire clears the roll once a piece is placed; keep the last one on screen (the caller dims it) until the next roll. Nobody is to
// move once the game is over, so the roll goes then, and the next round does not open on it.
export function useShownRoll(roll: [number, number] | null, owner: '1' | '2', gameOver: boolean): ShownRoll | null {
  const [shown, setShown] = useState<ShownRoll | null>(null)
  const next = gameOver ? null : roll ? { values: roll, owner } : shown
  // Set during render so the first paint already shows the roll; the equality check keeps the update from repeating.
  const changed = next !== shown && (!next || !shown || next.owner !== shown.owner || next.values[0] !== shown.values[0] || next.values[1] !== shown.values[1])
  if (changed) setShown(next)
  return next
}
