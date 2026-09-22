import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { FakeWebSocket } from './testUtils/FakeWebSocket'

beforeEach(() => {
  localStorage.clear()
  FakeWebSocket.instances = []
  vi.stubGlobal('WebSocket', FakeWebSocket)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function startGameAndOpen() {
  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))
  act(() => {
    FakeWebSocket.instances.at(-1)!.emit('open')
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

    expect(screen.getByRole('button', { name: 'Pause' })).toBeInTheDocument()
  })

  it('shows an inline retry message when the connection fails, and retrying opens a new socket', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
    fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))
    act(() => {
      FakeWebSocket.instances[0].emit('close')
    })

    expect(screen.getByText("Couldn't connect — your settings are unchanged, try again")).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Start Game' })).not.toBeDisabled()

    fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))

    expect(FakeWebSocket.instances).toHaveLength(2)
  })

  it('opens the Settings overlay from Playing on Pause, and closes it back to Playing', () => {
    render(<App />)
    startGameAndOpen()

    fireEvent.click(screen.getByRole('button', { name: 'Pause' }))
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Pause' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    expect(screen.queryByText('Settings')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Pause' })).toBeInTheDocument()
  })

  it('navigates from Playing to Replay and back', () => {
    render(<App />)
    startGameAndOpen()

    fireEvent.click(screen.getByRole('button', { name: 'Replay' }))
    expect(screen.getByText('Replay')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByRole('button', { name: 'Pause' })).toBeInTheDocument()
  })

  it('shows the connection-lost modal when the socket closes unexpectedly during Playing', () => {
    render(<App />)
    startGameAndOpen()

    act(() => {
      FakeWebSocket.instances.at(-1)!.emit('close')
    })

    expect(screen.getByText("This game can't be resumed")).toBeInTheDocument()
  })

  it('dismisses an open Settings overlay once the connection-lost modal appears', () => {
    render(<App />)
    startGameAndOpen()
    fireEvent.click(screen.getByRole('button', { name: 'Pause' }))
    expect(screen.getByText('Settings')).toBeInTheDocument()

    act(() => {
      FakeWebSocket.instances.at(-1)!.emit('close')
    })

    expect(screen.queryByText('Settings')).not.toBeInTheDocument()
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
})
