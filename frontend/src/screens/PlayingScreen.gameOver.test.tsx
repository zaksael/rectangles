import { fireEvent, render, screen, within } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { makeGame, makeSeries } from '../dev/fixtures/gameFixtures'
import type { GameState } from '../hooks/useGameSocket'
import { PlayingScreen } from './PlayingScreen'
import { gameOverState, gameOverTurn, makeState, renderScreen, rowValues } from '../dev/testUtils/playingScreenHarness'

test('game over shows a dialog with the end reason and the winner', () => {
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { history: null, reason: 'boardFull', playerId: null, winner: 1 } }))

  const dialog = screen.getByRole('dialog')
  expect(within(dialog).getByText('no room left to build')).toBeInTheDocument()
  expect(within(dialog).getByRole('heading', { name: 'Player\u00a01 wins on score' })).toBeInTheDocument()
})

test('no game-over dialog while the game is in progress', () => {
  renderScreen(makeState())
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})

test('the game-over dialog offers New Game', () => {
  const onNewGame = vi.fn()
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { history: null, reason: 'boardFull', playerId: null, winner: 1 } }), vi.fn(), null, onNewGame)

  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'New Game' }))

  expect(onNewGame).toHaveBeenCalledTimes(1)
})

test('View Board hides the result dialog and turns the rail\'s turn block into the result', () => {
  renderScreen(gameOverState())

  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'View Board' }))

  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  const bar = screen.getByRole('region', { name: 'Game result' })
  expect(bar).toHaveTextContent('Player 1 wins on score')
  expect(screen.getByRole('img', { name: 'Score: Player 1 158, Player 2 141' })).toBeInTheDocument()
  expect(screen.getByRole('group', { name: / board$/ })).toBeInTheDocument()
})

test('Escape on the result dialog shows the board, and View Result brings the dialog back', () => {
  renderScreen(gameOverState())

  fireEvent(screen.getByRole('dialog'), new Event('cancel', { cancelable: true }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

  fireEvent.click(within(screen.getByRole('region', { name: 'Game result' })).getByRole('button', { name: 'View Result' }))
  expect(screen.getByRole('dialog')).toBeInTheDocument()
  expect(screen.queryByRole('region', { name: 'Game result' })).not.toBeInTheDocument()
})

test('the result bar offers New Game', () => {
  const onNewGame = vi.fn()
  renderScreen(gameOverState(), vi.fn(), null, onNewGame)
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'View Board' }))

  fireEvent.click(within(screen.getByRole('region', { name: 'Game result' })).getByRole('button', { name: 'New Game' }))

  expect(onNewGame).toHaveBeenCalledTimes(1)
})

test('there is no Replay button mid-game; Replay is only reachable from the game-over dialog', () => {
  renderScreen(makeState())
  expect(screen.queryByRole('button', { name: 'Replay' })).not.toBeInTheDocument()
})

test('there is no turn status line once the game is over', () => {
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { history: null, reason: 'boardFull', playerId: null, winner: 1 } }))

  expect(screen.queryByTestId('turn-status')).not.toBeInTheDocument()
})

type GameOver = GameState['game']['gameOver']

function resultBar(gameOver: GameOver, tweak: (game: GameState['game']) => void = () => {}) {
  const game = makeGame({ turn: gameOverTurn, gameOver })
  tweak(game)
  renderScreen({ game, series: null })
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'View Board' }))
  return screen.getByRole('region', { name: 'Game result' })
}

test('the result bar names who surrendered', () => {
  const bar = resultBar({ history: null, reason: 'surrender', playerId: 2, winner: 1 })
  expect(within(bar).getByText('Player 2 surrendered')).toBeInTheDocument()
})

test('the result bar states no reason when the board simply settled', () => {
  const bar = resultBar({ history: null, reason: 'boardFull', playerId: null, winner: 1 })
  expect(within(bar).queryByText(/no room left to build/)).not.toBeInTheDocument()
})

test.each([
  ['playerBlocked', 1, 'Player 1 had no legal move left'],
  ['skipLimit', 2, 'Player 2 hit the skip limit (5 of 5)'],
] as const)('the result bar names the player for a %s ending', (reason, playerId, text) => {
  const bar = resultBar({ history: null, reason, playerId, winner: 3 - playerId })
  expect(within(bar).getByText(text)).toBeInTheDocument()
})

test('the end reason sits under the outcome, in the same block', () => {
  const bar = resultBar({ history: null, reason: 'playerBlocked', playerId: 1, winner: 2 })
  const reason = within(bar).getByText('Player 1 had no legal move left')
  expect(reason.previousElementSibling).toHaveTextContent('Player 2 wins on score')
})

test('a tie ended by the skip limit still names the reason on the bar', () => {
  const bar = resultBar({ history: null, reason: 'skipLimit', playerId: 1, winner: null })
  expect(within(bar).getByText('Tied')).toBeInTheDocument()
  expect(within(bar).getByText('Player 1 hit the skip limit (5 of 5)')).toBeInTheDocument()
})

test('once the game is over, the table marks no current player and draws both dots filled', () => {
  renderScreen(gameOverState())
  expect(document.querySelector('[aria-current]')).toBeNull()
  expect(document.querySelector('.score-table .current')).toBeNull()
  expect(screen.getAllByRole('columnheader').map((h) => h.classList.contains('over'))).toEqual([true, true])
})

test('in board view the rail keeps its score table and Moves list beside the result', () => {
  const bar = resultBar({ history: null, reason: 'boardFull', playerId: null, winner: 1 })
  expect(bar).toBeInTheDocument()
  expect(screen.getByRole('table', { name: 'Score' })).toBeInTheDocument()
  expect(screen.getByRole('log', { name: 'Moves' })).toBeInTheDocument()
})

test('the result sits in the turn block\'s reserved slots: the headline in the status box, the reason under it, the actions in the action row', () => {
  const bar = resultBar({ history: null, reason: 'skipLimit', playerId: 2, winner: 1 })

  expect(bar).toHaveClass('rail-turn')
  expect(within(bar.querySelector('.rail-instr') as HTMLElement).getByText('Player 1 wins on score')).toBeInTheDocument()
  expect(within(bar.querySelector('.rail-instr') as HTMLElement).getByText('Player 2 hit the skip limit (5 of 5)')).toBeInTheDocument()
  expect(bar.querySelector('.rail-dice')).not.toBeNull()
  expect(within(bar.querySelector('.rail-actions') as HTMLElement).getAllByRole('button')).toHaveLength(2)
})

test('with the result dialog open, the table still shows both players', () => {
  renderScreen(gameOverState())
  expect(screen.getAllByRole('columnheader')).toHaveLength(2)
})

test('View Result brings the dialog back, and View Board swaps it for the result in the rail again', () => {
  renderScreen(gameOverState())
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'View Board' }))
  expect(screen.getByRole('table', { name: 'Score' })).toBeInTheDocument()

  fireEvent.click(within(screen.getByRole('region', { name: 'Game result' })).getByRole('button', { name: 'View Result' }))
  expect(screen.getByRole('dialog')).toBeInTheDocument()
  expect(screen.queryByRole('region', { name: 'Game result' })).not.toBeInTheDocument()

  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'View Board' }))
  expect(screen.getByRole('region', { name: 'Game result' })).toBeInTheDocument()
})

test('the score bar keeps the real score, Player 1 first, even when the winner trails after a surrender', () => {
  const bar = resultBar({ history: null, reason: 'surrender', playerId: 2, winner: 1 }, (game) => {
    game.players['1'].score = { ...game.players['1'].score, totalScore: 120 }
    game.players['2'].score = { ...game.players['2'].score, totalScore: 158 }
  })
  expect(screen.getByRole('img', { name: 'Score: Player 1 120, Player 2 158' })).toBeInTheDocument()
  expect(bar).not.toHaveTextContent(/by \d+ point/)
})

test('focus lands on View Result in the bar after View Board', () => {
  const bar = resultBar({ history: null, reason: 'boardFull', playerId: null, winner: 1 })
  expect(within(bar).getByRole('button', { name: 'View Result' })).toHaveFocus()
})

test('focus lands on View Result in the bar after Escape', () => {
  renderScreen(gameOverState())
  fireEvent(screen.getByRole('dialog'), new Event('cancel', { cancelable: true }))
  expect(within(screen.getByRole('region', { name: 'Game result' })).getByRole('button', { name: 'View Result' })).toHaveFocus()
})

test('the bar shows total score and the table territory when modifiers make them differ', () => {
  resultBar({ history: null, reason: 'boardFull', playerId: null, winner: 1 }, (game) => {
    game.players['1'].score = { ...game.players['1'].score, totalScore: 162, breakdown: { ...game.players['1'].score.breakdown, area: 152 } }
    game.players['2'].score = { ...game.players['2'].score, totalScore: 141, breakdown: { ...game.players['2'].score.breakdown, area: 141 } }
  })
  expect(rowValues('Area')).toEqual(['152', '141'])
  expect(screen.getByRole('img', { name: 'Score: Player 1 162, Player 2 141' })).toBeInTheDocument()
})

test('in series play a caption gives the round and the running series score', () => {
  renderScreen({ ...makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }), series: makeSeries({ gamesPlayed: 1, scores: { '1': 18, '2': 14 } }) })

  expect(screen.getByRole('heading', { name: 'Round 2 of 3' })).toBeInTheDocument()
  expect(screen.getByText('Series 18 – 14')).toBeInTheDocument()
})

test('after a round ends the caption counts that round and includes its points', () => {
  renderScreen({ ...gameOverState(), series: makeSeries({ gamesPlayed: 2, scores: { '1': 31, '2': 29 } }) })

  expect(screen.getByRole('heading', { name: 'Round 2 of 3' })).toBeInTheDocument()
  expect(screen.getByText('Series 31 – 29')).toBeInTheDocument()
})

test('a single game has no series caption', () => {
  renderScreen(makeState())

  expect(screen.getByRole('heading', { name: 'Game' })).toBeInTheDocument()
  expect(screen.queryByText(/^Series /)).not.toBeInTheDocument()
})

test('in a series, Next Round on the result dialog and on the bar sends continueSeries', () => {
  const sendAction = renderScreen({ ...gameOverState(), series: makeSeries() })

  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /Next Round/ }))
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /View Board/ }))
  const bar = screen.getByRole('region', { name: 'Game result' })
  expect(within(bar).queryByRole('button', { name: /New Game/ })).not.toBeInTheDocument()
  fireEvent.click(within(bar).getByRole('button', { name: /Next Round/ }))

  expect(sendAction).toHaveBeenCalledTimes(2)
  expect(sendAction).toHaveBeenNthCalledWith(1, { type: 'continueSeries' })
  expect(sendAction).toHaveBeenNthCalledWith(2, { type: 'continueSeries' })
})

test('a new round shows its own result dialog even after the last one was put away', () => {
  const props = { error: null, sendAction: vi.fn(), onOpenSettings: vi.fn(), onNewGame: vi.fn() }
  const { rerender } = render(<PlayingScreen {...props} state={{ ...gameOverState(), series: makeSeries() }} />)
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /View Board/ }))
  expect(screen.getByRole('region', { name: 'Game result' })).toBeInTheDocument()

  rerender(<PlayingScreen {...props} state={{ ...makeState(), series: makeSeries() }} />)
  rerender(<PlayingScreen {...props} state={{ ...gameOverState(), series: makeSeries({ gamesPlayed: 2 }) }} />)

  expect(screen.getByRole('dialog')).toBeInTheDocument()
  expect(screen.queryByRole('region', { name: 'Game result' })).not.toBeInTheDocument()
})

function lastRoundState() {
  const zero = { '1': 0, '2': 0 }
  const round = { area: zero, prizeCaptured: zero, pitfallCaptured: zero, stealCaptured: zero, total: { '1': 158, '2': 141 }, winner: 1 }
  const series = makeSeries({ gamesPlayed: 3, isComplete: true, winner: 1, scores: { '1': 459, '2': 440 }, rounds: [round, round, round] })
  return { ...gameOverState(), series }
}

test('Series Result on the last round opens the series card without sending anything, and New Game there starts over', () => {
  const onNewGame = vi.fn()
  const sendAction = renderScreen(lastRoundState(), vi.fn(), null, onNewGame)

  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /Series Result/ }))
  const dialog = screen.getByRole('dialog')
  expect(within(dialog).getByRole('heading', { name: /wins the series/ })).toBeInTheDocument()
  fireEvent.click(within(dialog).getByRole('button', { name: /New Game/ }))

  expect(sendAction).not.toHaveBeenCalled()
  expect(onNewGame).toHaveBeenCalledTimes(1)
})

test('View Board on the series card pins the series bar, and View Result brings the series card back', () => {
  renderScreen(lastRoundState())
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /Series Result/ }))
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /View Board/ }))

  const bar = screen.getByRole('region', { name: 'Series result' })
  expect(screen.getByText('Series 459 – 440')).toBeInTheDocument()
  fireEvent.click(within(bar).getByRole('button', { name: /View Result/ }))

  expect(within(screen.getByRole('dialog')).getByRole('heading', { name: /wins the series/ })).toBeInTheDocument()
})

const replayProps = (onReplay = vi.fn()) => ({ error: null, sendAction: vi.fn(), onOpenSettings: vi.fn(), onNewGame: vi.fn(), onReplay })

test('Replay on a series round card says it was opened from the round card', () => {
  const onReplay = vi.fn()
  render(<PlayingScreen {...replayProps(onReplay)} state={{ ...gameOverState(), series: makeSeries() }} />)
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /^Replay/ }))
  expect(onReplay).toHaveBeenCalledWith(false)
})

test('Replay Last Round on the series card says it was opened from the series card', () => {
  const onReplay = vi.fn()
  render(<PlayingScreen {...replayProps(onReplay)} state={lastRoundState()} />)
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /Series Result/ }))
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /^Replay Last Round/ }))
  expect(onReplay).toHaveBeenCalledWith(true)
})

test('coming back from Replay to a finished series, the series card can open straight away', () => {
  render(<PlayingScreen {...replayProps()} state={lastRoundState()} initialSeriesResultOpen />)
  expect(within(screen.getByRole('dialog')).getByRole('heading', { name: /wins the series/ })).toBeInTheDocument()
})
