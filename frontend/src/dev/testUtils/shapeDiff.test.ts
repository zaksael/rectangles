import { expect, test } from 'vitest'
import { shapeDiff } from './shapeDiff'

test('equal key structures differ in nothing, whatever the values', () => {
  expect(shapeDiff({ a: 1, b: { c: [1, 2] } }, { a: 9, b: { c: [7] } })).toEqual([])
})

test('a key the server does not send, and one it sends extra, are each named with their path', () => {
  expect(shapeDiff({ a: { x: 1 } }, { a: { x: 1, y: 2 } })).toEqual(['$.a.y: in the TS shape, not sent by the server'])
  expect(shapeDiff({ a: { x: 1, z: 3 } }, { a: { x: 1 } })).toEqual(['$.a.z: sent by the server, not in the TS shape'])
})

test('arrays are compared by their first element', () => {
  expect(shapeDiff({ list: [{ id: 1, extra: true }] }, { list: [{ id: 1 }] })).toEqual(['$.list[].extra: sent by the server, not in the TS shape'])
})

test('a null or an empty array ends the walk, since there is nothing below to compare', () => {
  expect(shapeDiff({ a: null, b: [] }, { a: { deep: 1 }, b: [{ deep: 1 }] })).toEqual([])
  expect(shapeDiff({ a: { deep: 1 }, b: [{ deep: 1 }] }, { a: null, b: [] })).toEqual([])
})
