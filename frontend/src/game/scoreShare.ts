// The share of the score bar that goes to player 1, in percent.
// Both at or below zero (a loss): the other player's loss over both losses, so the smaller loss gets the larger share.
// One below zero: it gets none. Otherwise score over total; 0 - 0 splits evenly.
export const scoreShare = (a: number, b: number): number => {
  if (a <= 0 && b <= 0 && a + b < 0) return (100 * -b) / -(a + b)
  if (a < 0) return 0
  if (b < 0) return 100
  return a + b === 0 ? 50 : (100 * a) / (a + b)
}
