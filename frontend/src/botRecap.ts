import type { GameWireState } from './gameTypes'

export interface BotRecap {
  rerolls: number
  chose: number | null
  placed: [number, number] | null
  skipped: boolean
}

const EMPTY: BotRecap = { rerolls: 0, chose: null, placed: null, skipped: false }

// Folds one state-to-state step into the running recap of the bot's turn: it starts when the turn
// passes to the bot, grows with each of its steps, and is dropped once the human acts or the game ends.
export function stepBotRecap(recap: BotRecap | null, prev: GameWireState, next: GameWireState, bot: 1 | 2): BotRecap | null {
  if (next.turn.turnState === 'gameOver') return null
  const botActing = prev.turn.currentPlayerId === bot
  if (!botActing) return next.turn.currentPlayerId === bot ? EMPTY : null
  const before = prev.players[String(bot) as '1' | '2']
  const after = next.players[String(bot) as '1' | '2']
  const grown = after.board.pieces.length > before.board.pieces.length
  const piece = after.board.pieces[after.board.pieces.length - 1]
  const rerolled = Math.max(0, after.houseRules.reroll.used - before.houseRules.reroll.used)
  // Leaving a wildcard pick without spending a reroll means the bot chose the value (the roll may then be unplayable).
  const pickedIndex = prev.turn.turnState === 'choosingWildcard' && next.turn.turnState !== 'choosingWildcard' && rerolled === 0 ? prev.houseRules.wildcard.editableIndex : null
  return {
    rerolls: (recap ?? EMPTY).rerolls + rerolled,
    chose: pickedIndex !== null && next.turn.lastRoll ? next.turn.lastRoll[pickedIndex] : (recap ?? EMPTY).chose,
    placed: grown ? [piece.width, piece.height] : (recap ?? EMPTY).placed,
    skipped: (recap ?? EMPTY).skipped || after.board.consecutiveSkips > before.board.consecutiveSkips,
  }
}

export function describeBotRecap(name: string, recap: BotRecap): string | null {
  const parts = [
    recap.rerolls === 0 ? null : recap.rerolls === 1 ? 'rerolled' : recap.rerolls === 2 ? 'rerolled twice' : `rerolled ${recap.rerolls} times`,
    recap.chose === null ? null : `chose ${recap.chose}`,
    recap.placed && `placed ${recap.placed[0]} × ${recap.placed[1]}`,
    recap.skipped ? 'skipped' : null,
  ].filter(Boolean)
  return parts.length === 0 ? null : `${name} ${parts.join(', ')}`
}
