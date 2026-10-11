import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { FakeWebSocket } from './testUtils/FakeWebSocket'
import type { HistoryEntry } from './gameTypes'
import { makeGame, makeSeries, reach } from './fixtures/gameFixtures'

beforeEach(() => {
  localStorage.clear()
  FakeWebSocket.instances = []
  vi.stubGlobal('WebSocket', FakeWebSocket)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

it('shows the key badges while Shift is held, from the first screen on', () => {
  render(<App />)

  fireEvent.keyDown(window, { key: 'Shift' })

  expect(document.documentElement).toHaveAttribute('data-shift')
})

function startGameAndOpen() {
  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))
  act(() => {
    FakeWebSocket.instances.at(-1)!.emit('open')
  })
}

function sendState() {
  act(() => {
    FakeWebSocket.instances.at(-1)!.emit('message', { type: 'state', game: makeGame(), series: null })
  })
}

describe('App', () => {
  it('shows Mode Select by default, with a Start Game action', () => {
    render(<App />)
    expect(screen.getByRole('button', { name: 'Start Game' })).toBeInTheDocument()
  })

  it('does not open a socket before Start Game is clicked', () => {
    render(<App />)
    expect(FakeWebSocket.instances).toHaveLength(0)
  })

  it('shows a disabled "Connecting…" button after Start Game, before the socket opens', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
    fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))

    expect(screen.getByRole('button', { name: 'Connecting…' })).toBeDisabled()
  })

  it('navigates from Mode Select to Playing once the socket opens', () => {
    render(<App />)

    startGameAndOpen()

    expect(screen.getByRole('button', { name: 'Menu' })).toBeInTheDocument()
  })

  it('shows an inline retry message when the connection fails, and retrying opens a new socket', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
    fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))
    act(() => {
      FakeWebSocket.instances[0].emit('close')
    })

    expect(screen.getByText('Couldn’t connect — your settings are unchanged, try again')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Start Game' })).not.toBeDisabled()

    fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))

    expect(FakeWebSocket.instances).toHaveLength(2)
  })

  it('opens the Menu overlay from Playing on Menu, and closes it back to Playing', () => {
    render(<App />)
    startGameAndOpen()
    sendState()

    fireEvent.click(screen.getByRole('button', { name: 'Menu' }))
    expect(screen.getByRole('heading', { name: 'Menu' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Menu' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Resume' }))
    expect(screen.queryByRole('heading', { name: 'Menu' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Menu' })).toBeInTheDocument()
  })

  it('shows the connection-lost modal when the socket closes unexpectedly during Playing', () => {
    render(<App />)
    startGameAndOpen()

    act(() => {
      FakeWebSocket.instances.at(-1)!.emit('close')
    })

    expect(screen.getByText("This game can't be resumed")).toBeInTheDocument()
  })

  it('dismisses an open Menu overlay once the connection-lost modal appears', () => {
    render(<App />)
    startGameAndOpen()
    sendState()
    fireEvent.click(screen.getByRole('button', { name: 'Menu' }))
    expect(screen.getByRole('heading', { name: 'Menu' })).toBeInTheDocument()

    act(() => {
      FakeWebSocket.instances.at(-1)!.emit('close')
    })

    expect(screen.queryByRole('heading', { name: 'Menu' })).not.toBeInTheDocument()
    expect(screen.getByText("This game can't be resumed")).toBeInTheDocument()
  })

  it('returns to a clean Mode Select from the connection-lost modal on New Game', () => {
    render(<App />)
    startGameAndOpen()
    act(() => {
      FakeWebSocket.instances.at(-1)!.emit('close')
    })

    fireEvent.click(screen.getByRole('button', { name: 'New Game' }))

    expect(screen.getByRole('button', { name: 'Start Game' })).not.toBeDisabled()
    expect(screen.queryByText("Couldn't connect — your settings are unchanged, try again")).not.toBeInTheDocument()
  })

  it('returns to Mode Select from the game-over dialog on one New Game click, even when the socket closes asynchronously', () => {
    render(<App />)
    startGameAndOpen()
    // Real sockets report `close` some time after `close()` is called, not synchronously.
    FakeWebSocket.instances.at(-1)!.close = () => {}
    act(() => {
      FakeWebSocket.instances.at(-1)!.emit('message', {
        protocolVersion: 1,
        type: 'state',
        game: makeGame({
          turn: { currentPlayerId: 1, turnState: 'gameOver', lastRoll: null, legalPlacements: [] },
          gameOver: { reason: 'boardFull', playerId: null, winner: 1, history: [] },
        }),
        series: null,
      })
    })

    fireEvent.click(screen.getByRole('button', { name: 'New Game' }))

    expect(screen.getByRole('button', { name: 'Start Game' })).toBeInTheDocument()
  })

  function finishedSeries(isComplete: boolean) {
    render(<App />)
    startGameAndOpen()
    act(() => {
      FakeWebSocket.instances.at(-1)!.emit('message', {
        protocolVersion: 1,
        type: 'state',
        game: makeGame({
          turn: { currentPlayerId: 1, turnState: 'gameOver', lastRoll: null, legalPlacements: [] },
          gameOver: { reason: 'boardFull', playerId: null, winner: 1, history: [] },
        }),
        series: makeSeries({ gamesPlayed: 3, isComplete, winner: isComplete ? 1 : null }),
      })
    })
  }

  it('comes back from a round card\'s Replay to that round card', () => {
    finishedSeries(false)

    fireEvent.click(screen.getByRole('button', { name: /^Replay/ }))
    expect(screen.getByRole('heading', { name: 'Replay' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Back' }))

    expect(screen.getByRole('button', { name: /Next Round/ })).toBeInTheDocument()
  })

  it('comes back from the series result\'s Replay Last Round to the series result, not the last round', () => {
    finishedSeries(true)

    fireEvent.click(screen.getByRole('button', { name: /Series Result/ }))
    fireEvent.click(screen.getByRole('button', { name: /^Replay Last Round/ }))
    expect(screen.getByRole('heading', { name: 'Replay' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Back' }))

    expect(screen.getByRole('heading', { name: /wins the series/ })).toBeInTheDocument()
  })

  it('opens Replay from the game-over dialog, and Back returns to that dialog', () => {
    render(<App />)
    startGameAndOpen()
    act(() => {
      FakeWebSocket.instances.at(-1)!.emit('message', {
        protocolVersion: 1,
        type: 'state',
        game: makeGame({
          turn: { currentPlayerId: 1, turnState: 'gameOver', lastRoll: null, legalPlacements: [] },
          gameOver: { reason: 'boardFull', playerId: null, winner: 1, history: [] },
        }),
        series: null,
      })
    })

    fireEvent.click(screen.getByRole('button', { name: /^Replay/ }))
    expect(screen.getByRole('heading', { name: 'Replay' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Replay/ })).toBeInTheDocument()
  })

  it('swaps Playing and then Replay for the narrow-window notice below 1320px, and brings them back when widened', () => {
    const setWidth = (width: number) => {
      Object.defineProperty(window, 'innerWidth', { configurable: true, value: width })
      act(() => {
        window.dispatchEvent(new Event('resize'))
      })
    }
    render(<App />)
    startGameAndOpen()
    act(() => {
      FakeWebSocket.instances.at(-1)!.emit('message', {
        protocolVersion: 1,
        type: 'state',
        game: makeGame({
          turn: { currentPlayerId: 1, turnState: 'gameOver', lastRoll: null, legalPlacements: [] },
          gameOver: { reason: 'boardFull', playerId: null, winner: 1, history: [] },
        }),
        series: null,
      })
    })

    setWidth(1100)
    expect(screen.getByRole('status')).toHaveTextContent('Playing needs a window at least 1320px wide, and yours is 1100px')
    setWidth(1400)
    fireEvent.click(screen.getByRole('button', { name: /^Replay/ }))
    setWidth(1100)
    expect(screen.getByRole('status')).toHaveTextContent('Replay needs a window at least 1320px wide, and yours is 1100px')
    setWidth(1400)
    expect(screen.queryByText(/needs a window at least/)).toBeNull()
    expect(screen.getByRole('heading', { name: 'Replay' })).toBeVisible()
  })

  it("hands the Vs Bot seat to Playing so the human's Roll button is hidden on the bot turn", () => {
    vi.useFakeTimers()
    render(<App />)
    startGameAndOpen()
    const broadcast = (currentPlayerId: number) =>
      act(() => {
        FakeWebSocket.instances.at(-1)!.emit('message', {
          protocolVersion: 1,
          type: 'state',
          game: makeGame({ turn: { currentPlayerId, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }),
          series: null,
        })
      })

    broadcast(1)
    expect(screen.getByRole('button', { name: 'Roll' })).toBeEnabled()

    broadcast(2)
    act(() => vi.advanceTimersByTime(500)) // state broadcasts are paced, so the second one lands after the delay
    expect(screen.queryByRole('button', { name: 'Roll' })).not.toBeInTheDocument()
    vi.useRealTimers()
  })
})

describe('App replay analysis', () => {
  const zero = { area: 0, prize: 0, pitfall: 0, steal: 0, enclosure: 0 }
  const oneMove: HistoryEntry = {
    playerId: 1, roll: [1, 1], placed: { topLeft: [0, 0], width: 1, height: 1 }, wildcardOriginalRoll: null,
    score: { '1': 1, '2': 0 }, breakdown: { '1': { ...zero, area: 1 }, '2': zero }, potential: reach(0, 0),
  }
  const sent = () => FakeWebSocket.instances.at(-1)!.sent
  const requests = () => sent().filter((m) => (m as { type: string }).type === 'requestAnalysis')

  function gameOverAndReplay() {
    render(<App />)
    startGameAndOpen()
    act(() => {
      FakeWebSocket.instances.at(-1)!.emit('message', {
        protocolVersion: 1,
        type: 'state',
        game: makeGame({
          turn: { currentPlayerId: 1, turnState: 'gameOver', lastRoll: null, legalPlacements: [] },
          gameOver: { reason: 'boardFull', playerId: null, winner: 1, history: [oneMove] },
        }),
        series: null,
      })
    })
    fireEvent.click(screen.getByRole('button', { name: /^Replay/ }))
  }
  const backAndReopen = () => {
    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    fireEvent.click(screen.getByRole('button', { name: /^Replay/ }))
  }
  const answer = () =>
    act(() => {
      FakeWebSocket.instances.at(-1)!.emit('message', {
        protocolVersion: 1,
        type: 'analysis',
        turns: [{ turn: 1, axis: 'prize', chosen: 0, best: 10, topLeft: [0, 0], width: 1, height: 1 }],
      })
    })

  it('asks the server for the analysis when Replay opens, and shows it once it arrives', () => {
    gameOverAndReplay()
    expect(requests()).toHaveLength(1)
    expect(screen.getByRole('status')).toHaveTextContent('Checking for better moves…')

    answer()
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))

    expect(screen.getByText('Scored 0 this turn (best possible: 10, Prize)')).toBeInTheDocument()
  })

  it('does not ask again when Replay is reopened', () => {
    gameOverAndReplay()
    answer()

    backAndReopen()

    expect(requests()).toHaveLength(1)
  })

  it('keeps Show Better Option on across leaving and reopening Replay', () => {
    gameOverAndReplay()
    answer()
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    fireEvent.click(screen.getByRole('button', { name: 'Show Better Option' }))
    expect(screen.getByRole('button', { name: 'Show Better Option' })).toHaveAttribute('aria-pressed', 'true')

    backAndReopen()
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))

    expect(screen.getByRole('button', { name: 'Show Better Option' })).toHaveAttribute('aria-pressed', 'true')
  })
})
