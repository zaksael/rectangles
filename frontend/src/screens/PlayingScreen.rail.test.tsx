import { screen, within } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { makeGame } from '../dev/fixtures/gameFixtures'
import { makeState, moves, movesState, recentTurn, renderScreen, rowCells, rowValues, scoreRow, scoreTable, specialRules } from '../dev/testUtils/playingScreenHarness'

test('each score column header names its player in a span that carries the name for the reserved bold width', () => {
  renderScreen(makeState())

  const names = screen.getAllByRole('columnheader').map((h) => h.querySelector<HTMLElement>('.score-name'))
  expect(names.map((n) => n?.textContent)).toEqual(['Player 1', 'Player 2'])
  expect(names.map((n) => n?.getAttribute('data-name'))).toEqual(['Player 1', 'Player 2'])
})

test('highlights the current player in the turn indicator', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 2, turnState: 'choosingPlacement', lastRoll: [3, 4], legalPlacements: [] } }))

  expect(screen.getByRole('columnheader', { name: 'Player 1' })).not.toHaveClass('current')
  expect(screen.getByRole('columnheader', { name: 'Player 2' })).toHaveClass('current')
})

test('the turn block carries the mover\'s player class', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  expect(document.querySelector('.rail-turn')).toHaveClass('p2')
})

test('the turn block carries no player class at game over', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 2, turnState: 'gameOver', lastRoll: null, legalPlacements: [] } }))

  const turn = document.querySelector('.rail-turn') as HTMLElement
  expect(turn).not.toHaveClass('p1')
  expect(turn).not.toHaveClass('p2')
})

test('the rail opens with the Game title and the Menu button', () => {
  renderScreen(makeState())

  const title = screen.getByRole('heading', { name: 'Game' })
  expect(within(title.parentElement as HTMLElement).getByRole('button', { name: 'Menu' })).toBeInTheDocument()
})

test('the score table has a column per player, with the mover marked', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  expect(within(scoreTable()).getAllByRole('columnheader').map((h) => h.textContent)).toEqual(['Player 1', 'Player 2'])
  expect(screen.getByRole('columnheader', { name: 'Player 2' })).toHaveAttribute('aria-current', 'true')
  expect(screen.getByRole('columnheader', { name: 'Player 1' })).not.toHaveAttribute('aria-current')
})

test('each column header carries the player\'s dot', () => {
  renderScreen(makeState())

  for (const name of ['Player 1', 'Player 2']) {
    expect(screen.getByRole('columnheader', { name }).querySelector('.dot')).toBeInTheDocument()
  }
})

test('the Area row shows each player\'s territory', () => {
  const game = makeGame()
  game.players['1'].score = { ...game.players['1'].score, totalScore: 12, breakdown: { ...game.players['1'].score.breakdown, area: 9 } }
  game.players['2'].score = { ...game.players['2'].score, totalScore: 7, breakdown: { ...game.players['2'].score.breakdown, area: 5 } }
  renderScreen({ game, series: null })

  expect(rowValues('Area')).toEqual(['9', '5'])
})

test('the Skips row counts skips left against the limit, and marks one skip from the limit', () => {
  const game = makeGame({ board: { size: 3, skipLimit: 5 } })
  game.players['1'].board.consecutiveSkips = 4
  game.players['2'].board.consecutiveSkips = 2
  renderScreen({ game, series: null })

  expect(rowValues('Skips')).toEqual(['1 / 5', '3 / 5'])
  expect(rowCells('Skips')[0]).toHaveClass('last-skip')
  expect(rowCells('Skips')[1]).not.toHaveClass('last-skip')
})

test('the In reach row shows the empty cells each player can still reach', () => {
  const game = makeGame()
  game.players['1'].score.potential = { area: 31, prize: { points: 0 } }
  game.players['2'].score.potential = { area: 24, prize: { points: 0 } }
  renderScreen({ game, series: null })

  expect(rowValues('In reach')).toEqual(['31', '24'])
})

test('the In reach row is explained by a line under it that the row header is described by', () => {
  renderScreen({ game: makeGame(), series: null })

  const note = 'Cells each could still build on; counts overlap'
  expect(screen.getByText(note)).toBeVisible()
  expect(screen.getByRole('rowheader', { name: 'In reach' })).toHaveAccessibleDescription(note)
})

test('the score table uses the shared score-table style', () => {
  renderScreen(makeState())

  expect(scoreTable()).toHaveClass('score-table')
})

test.each([
  ['illegalPlacement', 'That piece can’t go there — try another spot.'],
  ['invalidAction', 'You can’t do that right now — finish your current step.'],
  ['protocolVersionMismatch', 'This game is out of date — reload the page.'],
  ['illegalWildcardValue', 'That number can’t be placed — pick another.'],
  ['malformedMessage', 'Something went wrong — try again.'],
] as const)('shows friendly toast text for a %s server error', (reason, text) => {
  renderScreen(makeState(), vi.fn(), { reason, message: 'raw server text' })

  expect(screen.getByRole('status')).toHaveTextContent(text)
})

test("marks only the current player's column with aria-current", () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  expect(screen.getByRole('columnheader', { name: 'Player 1' })).not.toHaveAttribute('aria-current')
  expect(screen.getByRole('columnheader', { name: 'Player 2' })).toHaveAttribute('aria-current', 'true')
})

test('mid-game, the header marks the player whose turn it is', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))
  expect(document.querySelector('[aria-current]')).toHaveTextContent('Player 2')
})

const rowHeaders = () => within(scoreTable()).getAllByRole('rowheader').map((h) => h.textContent)

test('the rule rows carry the special-cell marks: each enabled rule, in rule order, with its mark and what a capture is worth', () => {
  renderScreen(
    makeState({
      board: { size: 5, skipLimit: 5 },
      houseRules: specialRules({
        steal: { enabled: true, cells: [[4, 0]], points: 10 },
        prize: { enabled: true, cells: [[0, 4]], points: 10 },
        pitfall: { enabled: true, cells: [[2, 2]], points: 10 },
      }),
    }),
  )

  expect(rowHeaders().filter((h) => /Prize|Pitfall|Steal/.test(h!))).toEqual(['Prize +10', 'Pitfall −10', 'Steal ±10'])
  expect(scoreRow('Pitfall −10')).toBeInTheDocument()
  for (const kind of ['prize', 'pitfall', 'steal']) {
    const mark = document.querySelector(`.score-table th .rule-mark.board-cell.${kind}`)
    expect(mark).toHaveAttribute('aria-hidden', 'true')
  }
  expect(screen.queryByRole('list', { name: 'Special cells' })).not.toBeInTheDocument()
})

test('a rule row reads its own point value, and only the rules that are on have a row', () => {
  renderScreen(
    makeState({
      houseRules: specialRules({
        prize: { enabled: true, cells: [[0, 2]], points: 7 },
        pitfall: { enabled: false, cells: [[1, 1]], points: 3 },
      }),
    }),
  )

  expect(rowHeaders().filter((h) => /Prize|Pitfall|Steal/.test(h!))).toEqual(['Prize +7'])
})

test('with no special-cell rule on there is no mark or value in the table', () => {
  renderScreen(makeState())

  expect(document.querySelector('.score-table .rule-mark')).toBeNull()
  expect(rowHeaders()).toEqual(['Area', 'In reach', 'Skips'])
})

// A game with each scoring rule on and a breakdown that sums to the total on the score bar.
function breakdownGame(on: { prize?: boolean; pitfall?: boolean; steal?: boolean; enclosure?: boolean }) {
  const game = makeGame()
  game.houseRules.prize = { ...game.houseRules.prize, enabled: !!on.prize }
  game.houseRules.pitfall = { ...game.houseRules.pitfall, enabled: !!on.pitfall }
  game.houseRules.steal = { ...game.houseRules.steal, enabled: !!on.steal }
  game.houseRules.selfEnclosedPenalty = { enabled: !!on.enclosure }
  game.players['1'].score = { ...game.players['1'].score, totalScore: 14, breakdown: { area: 18, prize: 5, pitfall: -3, steal: 4, enclosure: -10 } }
  game.players['2'].score = { ...game.players['2'].score, totalScore: 6, breakdown: { area: 14, prize: 0, pitfall: -3, steal: -4, enclosure: -1 } }
  return { game, series: null }
}

test('each scoring rule that is on gets a row after Area, in the order Prize, Pitfall, Steal, Enclosure, with signed values', () => {
  renderScreen(breakdownGame({ prize: true, pitfall: true, steal: true, enclosure: true }))

  const labels = rowHeaders().map((h) => h!.replace(/ [+−±]\d+$/, '')) // a special-cell row's label ends with its value
  expect(labels).toEqual(['Area', 'Prize', 'Pitfall', 'Steal', 'Enclosure', 'In reach', 'Skips'])
  expect(rowValues('Prize')).toEqual(['+5', '0'])
  expect(rowValues('Pitfall')).toEqual(['−3', '−3'])
  expect(rowValues('Steal')).toEqual(['+4', '−4'])
  expect(rowValues('Enclosure')).toEqual(['−10', '−1'])
})

test.each([
  ['Prize', { pitfall: true, steal: true, enclosure: true }],
  ['Pitfall', { prize: true, steal: true, enclosure: true }],
  ['Steal', { prize: true, pitfall: true, enclosure: true }],
  ['Enclosure', { prize: true, pitfall: true, steal: true }],
] as const)('a rule that is off leaves no %s row', (label, on) => {
  renderScreen(breakdownGame(on))

  expect(within(scoreTable()).queryByRole('rowheader', { name: label })).not.toBeInTheDocument()
})

test('with no scoring rule on the table is just Area above the resources', () => {
  renderScreen(breakdownGame({}))

  expect(within(scoreTable()).getAllByRole('rowheader').map((h) => h.textContent)).toEqual(['Area', 'In reach', 'Skips'])
})

test('a rule row that adds nothing is dimmed, and one that adds points is not', () => {
  renderScreen(breakdownGame({ prize: true }))

  const [p1, p2] = rowCells('Prize')
  expect(p1).not.toHaveClass('zero')
  expect(p2).toHaveClass('zero')
})

test('the Moves list is a log named Moves that is not announced', () => {
  renderScreen(movesState([]))

  expect(screen.getByRole('log', { name: 'Moves' })).toHaveAttribute('aria-live', 'off')
})

test('the rows run newest first, the turn in progress on top, each with turn number, player, what happened and signed points', () => {
  renderScreen(movesState([recentTurn(1, 1, [2, 3], 6), recentTurn(2, 2, null, 0), recentTurn(3, 1, [4, 4], -3)], 'awaitingRoll', 2))

  expect(moves().map((row) => row.textContent)).toEqual([
    '4Player 2Waiting to roll…',
    '3Player 1Placed 4 × 4−3',
    '2Player 2No legal move, skipped',
    '1Player 1Placed 2 × 3+6',
  ])
})

test('the turn in progress is a tinted live row', () => {
  renderScreen(movesState([recentTurn(1, 1, [2, 3], 6)]))

  expect(moves()[0]).toHaveClass('live')
  expect(moves()[1]).not.toHaveClass('live')
})

test.each([
  ['awaitingRoll', 'Waiting to roll…'],
  ['choosingWildcard', 'Wildcard roll, picking…'],
] as const)('the live row reads by turn state (%s)', (turnState, text) => {
  renderScreen(movesState([], turnState))

  expect(within(moves()[0]!).getByText(text)).toBeInTheDocument()
})

test('a dead roll that a reroll could still discard has a live row while the player decides', () => {
  const state = movesState([], 'skipped')
  state.game.houseRules.reroll = { enabled: true, canReroll: true }
  renderScreen(state)

  expect(within(moves()[0]!).getByText('No legal move, deciding…')).toBeInTheDocument()
})

test('a dead roll the server already recorded is one row, not also a live row', () => {
  renderScreen(movesState([recentTurn(1, 1, [2, 3], 6), recentTurn(2, 2, null, 0)], 'skipped', 2))

  expect(moves().map((row) => row.textContent)).toEqual(['2Player 2No legal move, skipped', '1Player 1Placed 2 × 3+6'])
})

test('while placing, the live row names the piece being placed', () => {
  renderScreen(movesState([], 'choosingPlacement'))

  expect(moves()[0]).toHaveTextContent(/Placing \d+ × \d+…/)
})

test('a wildcard turn names the roll that was edited', () => {
  renderScreen(movesState([recentTurn(1, 1, [6, 6], 36, [3, 3])]))

  expect(within(moves()[1]!).getByText('Placed 6 × 6, wildcard (rolled 3·3)')).toBeInTheDocument()
})

test('the list shows the live row and the last three turns, no more', () => {
  const turns = [1, 2, 3, 4, 5, 6].map((n) => recentTurn(n, n % 2 ? 1 : 2, [1, n], n))
  renderScreen(movesState(turns))

  expect(moves()).toHaveLength(4)
  expect(moves().map((row) => row.firstChild?.textContent)).toEqual(['7', '6', '5', '4'])
})

test('once the game is over there is no live row and the last four turns show', () => {
  const turns = [1, 2, 3, 4, 5, 6].map((n) => recentTurn(n, n % 2 ? 1 : 2, [1, n], n))
  renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'gameOver', lastRoll: null, legalPlacements: [], recentTurns: turns }, gameOver: { history: null, reason: 'boardFull', playerId: null, winner: 1 } }))

  expect(moves().map((row) => row.firstChild?.textContent)).toEqual(['6', '5', '4', '3'])
  expect(document.querySelector('.move.live')).toBeNull()
})

test('before any move the list says nothing has been played', () => {
  renderScreen(movesState([]))

  expect(screen.getByText('Nothing played yet')).toBeInTheDocument()
})

test('a bar above the score table names both scores and splits by their share', () => {
  const game = makeGame()
  game.players['1'].score = { ...game.players['1'].score, totalScore: 12 }
  game.players['2'].score = { ...game.players['2'].score, totalScore: 8 }
  renderScreen({ game, series: null })

  const bar = screen.getByRole('img', { name: 'Score: Player 1 12, Player 2 8' })
  expect([...bar.querySelectorAll<HTMLElement>('.score-bar-seg')].map((s) => s.style.width)).toEqual(['60%', '40%'])
})

test('with both scores negative the bar still shows both numbers, the smaller loss with the larger share', () => {
  const game = makeGame()
  game.players['1'].score = { ...game.players['1'].score, totalScore: -4 }
  game.players['2'].score = { ...game.players['2'].score, totalScore: -1 }
  renderScreen({ game, series: null })

  const bar = screen.getByRole('img', { name: 'Score: Player 1 −4, Player 2 −1' })
  expect([...bar.querySelectorAll<HTMLElement>('.score-bar-num')].map((n) => n.textContent)).toEqual(['−4', '−1'])
  expect([...bar.querySelectorAll<HTMLElement>('.score-bar-seg')].map((s) => s.style.width)).toEqual(['20%', '80%'])
})
