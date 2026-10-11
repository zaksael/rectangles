import { act, fireEvent, render, screen } from '@testing-library/react'
import { useEffect, useState } from 'react'
import { afterEach, expect, test, vi } from 'vitest'
import { NarrowWindowGate } from './NarrowWindowGate'

const setWidth = (width: number) => {
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: width })
  act(() => {
    window.dispatchEvent(new Event('resize'))
  })
}

afterEach(() => setWidth(1400))

function Counter() {
  const [n, setN] = useState(0)
  return <button onClick={() => setN(n + 1)}>{`count ${n}`}</button>
}

test('below 1320px the screen gives way to the notice, naming the minimum and the live width', () => {
  setWidth(1024)
  render(
    <NarrowWindowGate screen="Playing">
      <Counter />
    </NarrowWindowGate>,
  )
  expect(screen.getByRole('status')).toHaveTextContent('Window too narrow')
  expect(screen.getByRole('heading', { name: 'Widen the Window' })).toBeTruthy()
  expect(screen.getByRole('status')).toHaveTextContent(
    'Playing needs a window at least 1320px wide, and yours is 1024px. Widen it to carry on: your game is paused where it was and nothing is lost.',
  )
  expect(screen.queryByRole('button', { name: 'count 0' })).toBeNull() // hidden from the accessibility tree and the eye
  expect(screen.getByText('count 0', { selector: 'button' })).not.toBeVisible()
})

test('at exactly 1320px the screen shows and there is no notice', () => {
  setWidth(1320)
  render(
    <NarrowWindowGate screen="Playing">
      <Counter />
    </NarrowWindowGate>,
  )
  expect(screen.queryByRole('status')).toBeNull()
  expect(screen.getByRole('button', { name: 'count 0' })).toBeVisible()
  setWidth(1319)
  expect(screen.getByRole('status')).toHaveTextContent('yours is 1319px')
})

test('the notice follows the window as it is resized, and Replay has its own advice', () => {
  setWidth(1180)
  render(
    <NarrowWindowGate screen="Replay">
      <Counter />
    </NarrowWindowGate>,
  )
  expect(screen.getByRole('status')).toHaveTextContent(
    'Replay needs a window at least 1320px wide, and yours is 1180px. Widen it to watch the replay: it stays on the turn you were on.',
  )
  setWidth(1250)
  expect(screen.getByRole('status')).toHaveTextContent('yours is 1250px')
  setWidth(1320)
  expect(screen.queryByRole('status')).toBeNull()
})

test('the screen keeps its own state through a narrow spell', () => {
  setWidth(1400)
  render(
    <NarrowWindowGate screen="Playing">
      <Counter />
    </NarrowWindowGate>,
  )
  fireEvent.click(screen.getByRole('button', { name: 'count 0' }))
  setWidth(900)
  setWidth(1400)
  expect(screen.getByRole('button', { name: 'count 1' })).toBeVisible()
})

function KeyListener({ onKey }: { onKey: () => void }) {
  useEffect(() => {
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onKey])
  return null
}

test('while narrow a key never reaches the hidden screen\'s window listeners, and it does again once wide', () => {
  const onKey = vi.fn()
  setWidth(1000)
  render(
    <NarrowWindowGate screen="Playing">
      <KeyListener onKey={onKey} />
    </NarrowWindowGate>,
  )
  fireEvent.keyDown(document.body, { key: 'd' })
  fireEvent.keyDown(window, { key: 'd' }) // a key aimed at the window itself shares the listeners' target
  expect(onKey).not.toHaveBeenCalled()
  setWidth(1400)
  fireEvent.keyDown(document.body, { key: 'd' })
  expect(onKey).toHaveBeenCalledTimes(1)
})
