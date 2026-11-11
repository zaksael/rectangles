import { render, screen, within } from '@testing-library/react'
import { onTestFinished, vi } from 'vitest'
import { readCss } from './styles'
import { makeGame } from '../fixtures/gameFixtures'
import type { GameWireState, RecentTurn } from '../../game/gameTypes'
import type { GameError, GameState } from '../../hooks/useGameSocket'
import { PlayingScreen } from '../../screens/PlayingScreen'

export function makeState(overrides: Parameters<typeof makeGame>[0] = {}): GameState {
  return { game: makeGame(overrides), series: null }
}

export const scoreTable = () => screen.getByRole('table', { name: 'Score' })

export const scoreRow = (label: string) => within(scoreTable()).getByRole('row', { name: new RegExp(`^${label}( |$)`) })

export const rowCells = (label: string) => within(scoreRow(label)).getAllByRole('cell')

export const rowValues = (label: string) => rowCells(label).map((c) => c.textContent)

export function renderScreen(
  state: GameState | null,
  sendAction = vi.fn(),
  error: GameError | null = null,
  onNewGame = vi.fn(),
  botSeat?: number,
) {
  render(
    <PlayingScreen
      state={state}
      error={error}
      sendAction={sendAction}
      onOpenSettings={vi.fn()}
      onNewGame={onNewGame}
      botSeat={botSeat}
    />,
  )
  return sendAction
}

export const gameOverTurn = { currentPlayerId: 1, turnState: 'gameOver' as const, lastRoll: null, legalPlacements: [], recentTurns: [] }

export function gameOverState() {
  const game = makeGame({ turn: gameOverTurn, gameOver: { history: null, reason: 'boardFull', playerId: null, winner: 1 } })
  game.players['1'].score = { ...game.players['1'].score, totalArea: 158, totalScore: 158 }
  game.players['2'].score = { ...game.players['2'].score, totalArea: 141, totalScore: 141 }
  return { game, series: null }
}

export const renderVsBot = (state: GameState) => renderScreen(state, vi.fn(), null, vi.fn(), 2)

export const deadRoll = (consecutiveSkips: number) => {
  const game = makeGame({ board: { size: 3, skipLimit: 5 }, turn: { recentTurns: [], currentPlayerId: 1, turnState: 'skipped', lastRoll: [3, 4], legalPlacements: [] } })
  game.players['1'].board.consecutiveSkips = consecutiveSkips
  return game
}

// jsdom skips the imported stylesheet, so tests that assert computed style inject the real files, the shared tokens first as in the bundle.
export function injectPlayingCss() {
  const style = document.createElement('style')
  style.textContent = `${readCss('tokens.css')}\n${readCss('PlayingScreen.css')}`
  document.head.append(style)
  onTestFinished(() => style.remove())
}

export const keyboardState = () =>
  makeState({
    board: { size: 5, skipLimit: 5 },
    turn: { recentTurns: [],
      currentPlayerId: 1,
      turnState: 'choosingPlacement',
      lastRoll: [2, 1],
      legalPlacements: [{ width: 2, height: 1, topLefts: [[0, 0], [0, 1]] }],
    },
  })

export const rerollState = (canReroll: boolean, turnState: 'choosingPlacement' | 'skipped' | 'choosingWildcard' = 'choosingPlacement') => {
  const state = makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState, lastRoll: [3, 4], legalPlacements: [] } })
  state.game.houseRules.reroll = { enabled: true, canReroll }
  return state
}

export function renderPlaying(state: GameState) {
  const props = { error: null, sendAction: vi.fn(), onOpenSettings: vi.fn(), onNewGame: vi.fn() }
  const view = render(<PlayingScreen state={state} {...props} />)
  return (next: GameState) => view.rerender(<PlayingScreen state={next} {...props} />)
}

export function specialRules(rules: Partial<Pick<GameWireState['houseRules'], 'prize' | 'pitfall' | 'steal'>>) {
  return { ...makeGame().houseRules, ...rules }
}

export const zeroParts = { area: 0, prize: 0, pitfall: 0, steal: 0, enclosure: 0 }

export function recentTurn(
  turn: number,
  playerId: 1 | 2,
  placed: [number, number] | null,
  points: number,
  wildcardOriginalRoll: [number, number] | null = null,
): RecentTurn {
  return {
    turn,
    playerId,
    roll: [2, 2],
    placed: placed && { topLeft: [0, 0], width: placed[0], height: placed[1] },
    wildcardOriginalRoll,
    score: { '1': 0, '2': 0 },
    breakdown: { '1': zeroParts, '2': zeroParts },
    points,
  }
}

export const moves = () => within(screen.getByRole('log', { name: 'Moves' })).queryAllByRole('listitem')

export const movesState = (recentTurns: RecentTurn[], turnState: GameWireState['turn']['turnState'] = 'awaitingRoll', currentPlayerId = 1) =>
  makeState({ turn: { currentPlayerId, turnState, lastRoll: turnState === 'awaitingRoll' ? null : [2, 3], legalPlacements: [], recentTurns } })

// The board is an application region while it takes placement keys, and a group otherwise.
export const getBoard = () => screen.queryByRole('application', { name: / board$/ }) ?? screen.getByRole('group', { name: / board$/ })
