import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { FixtureApp } from './FixtureApp'

afterEach(cleanup)

test('renders the real Playing screen for a fixture and only logs an action', () => {
  const info = vi.spyOn(console, 'info').mockImplementation(() => {})
  render(<FixtureApp name="wildcard" />)
  fireEvent.click(screen.getByRole('button', { name: '3' }))
  expect(info).toHaveBeenCalledTimes(2) // one line when the fixture loads, one for the ignored action
  expect(info.mock.calls[1].join(' ')).toContain('chooseWildcard')
  info.mockRestore()
})
