import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { ErrorBoundary } from './ErrorBoundary'

beforeEach(() => {
  // React reports a caught render error through console.error; keep the run quiet.
  vi.spyOn(console, 'error').mockImplementation(() => {})
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

function Boom(): never {
  throw new Error('render failed')
}

test('a screen that throws while rendering is replaced by the recovery card, not a blank page', () => {
  render(
    <ErrorBoundary>
      <Boom />
    </ErrorBoundary>,
  )

  expect(screen.getByRole('heading', { name: 'Something Went Wrong' })).toBeInTheDocument()
  expect(screen.getByText('The page stopped working. Reload to start again.')).toBeInTheDocument()
})

test('Reload is the one action, and it reloads the page', () => {
  const reload = vi.fn()
  vi.stubGlobal('location', { reload })
  render(
    <ErrorBoundary>
      <Boom />
    </ErrorBoundary>,
  )

  expect(screen.getAllByRole('button')).toHaveLength(1)
  fireEvent.click(screen.getByRole('button', { name: 'Reload' }))

  expect(reload).toHaveBeenCalledTimes(1)
})

test('children that render fine are shown untouched', () => {
  render(
    <ErrorBoundary>
      <p>all good</p>
    </ErrorBoundary>,
  )

  expect(screen.getByText('all good')).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Something Went Wrong' })).not.toBeInTheDocument()
})
