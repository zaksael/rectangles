import { renderHook } from '@testing-library/react'
import { expect, test } from 'vitest'
import { useShownRoll } from './useShownRoll'

type Props = { roll: [number, number] | null; owner: '1' | '2'; gameOver: boolean }
const render = (initialProps: Props) => renderHook((props: Props) => useShownRoll(props.roll, props.owner, props.gameOver), { initialProps })

test('nothing is shown before the first roll', () => {
  expect(render({ roll: null, owner: '1', gameOver: false }).result.current).toBeNull()
})

test('a roll is shown with its owner', () => {
  expect(render({ roll: [3, 5], owner: '2', gameOver: false }).result.current).toEqual({ values: [3, 5], owner: '2' })
})

test('the roll stays on screen, with its owner, once the wire clears it', () => {
  const { result, rerender } = render({ roll: [3, 5], owner: '1', gameOver: false })

  rerender({ roll: null, owner: '2', gameOver: false })

  expect(result.current).toEqual({ values: [3, 5], owner: '1' })
})

test('a new roll replaces the last one', () => {
  const { result, rerender } = render({ roll: [3, 5], owner: '1', gameOver: false })
  rerender({ roll: null, owner: '2', gameOver: false })

  rerender({ roll: [1, 2], owner: '2', gameOver: false })

  expect(result.current).toEqual({ values: [1, 2], owner: '2' })
})

test('the game ending clears it, and the next game does not open on it', () => {
  const { result, rerender } = render({ roll: [3, 5], owner: '1', gameOver: false })

  rerender({ roll: null, owner: '1', gameOver: true })
  expect(result.current).toBeNull()

  rerender({ roll: null, owner: '1', gameOver: false })
  expect(result.current).toBeNull()
})
