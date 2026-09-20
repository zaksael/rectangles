import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { FakeWebSocket } from './testUtils/FakeWebSocket'

beforeEach(() => {
  FakeWebSocket.instances = []
  vi.stubGlobal('WebSocket', FakeWebSocket)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('shows Mode Select by default, with a Start Game action', () => {
    render(<App />)
    expect(screen.getByRole('button', { name: 'Start Game' })).toBeInTheDocument()
  })

  it('navigates from Mode Select to Playing on Start Game', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))

    expect(screen.getByText('Playing')).toBeInTheDocument()
  })

  it('opens the Settings overlay from Playing on Pause, and closes it back to Playing', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))

    fireEvent.click(screen.getByRole('button', { name: 'Pause' }))
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByText('Playing')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    expect(screen.queryByText('Settings')).not.toBeInTheDocument()
    expect(screen.getByText('Playing')).toBeInTheDocument()
  })

  it('navigates from Playing to Replay and back', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))

    fireEvent.click(screen.getByRole('button', { name: 'Replay' }))
    expect(screen.getByText('Replay')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByText('Playing')).toBeInTheDocument()
  })

  it('shows the connection-lost modal when the socket closes unexpectedly during Playing', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))

    act(() => {
      FakeWebSocket.instances[0].emit('close')
    })

    expect(screen.getByText("This game can't be resumed")).toBeInTheDocument()
  })

  it('dismisses an open Settings overlay once the connection-lost modal appears', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))
    fireEvent.click(screen.getByRole('button', { name: 'Pause' }))
    expect(screen.getByText('Settings')).toBeInTheDocument()

    act(() => {
      FakeWebSocket.instances[0].emit('close')
    })

    expect(screen.queryByText('Settings')).not.toBeInTheDocument()
    expect(screen.getByText("This game can't be resumed")).toBeInTheDocument()
  })

  it('returns to Mode Select from the connection-lost modal on New Game', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))
    act(() => {
      FakeWebSocket.instances[0].emit('close')
    })

    fireEvent.click(screen.getByRole('button', { name: 'New Game' }))

    expect(screen.getByRole('button', { name: 'Start Game' })).toBeInTheDocument()
  })
})
