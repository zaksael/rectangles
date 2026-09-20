import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

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
})
