import { useRef, useState } from 'react'
import type { GameAction, GameWireState } from './gameTypes'

const UNSET = Symbol('unset')

function computeTopLeft(cell: [number, number], dims: [number, number], boardSize: number): [number, number] {
  const [row, col] = cell
  const [width, height] = dims
  const r = Math.max(0, Math.min(row - Math.floor(height / 2), boardSize - height))
  const c = Math.max(0, Math.min(col - Math.floor(width / 2), boardSize - width))
  return [r, c]
}

function pickInitialDims(
  lastRoll: [number, number],
  legalPlacements: GameWireState['turn']['legalPlacements'],
): [number, number] | null {
  const [a, b] = lastRoll
  const isLegalOrientation = (w: number, h: number) => legalPlacements.some((p) => p.width === w && p.height === h)
  if (isLegalOrientation(a, b)) return [a, b]
  if (isLegalOrientation(b, a)) return [b, a]
  return null
}

export function usePlacementInput(game: GameWireState | null, sendAction: (action: GameAction) => void) {
  const [dims, setDims] = useState<[number, number] | null>(null)
  const [hoveredCell, setHoveredCell] = useState<[number, number] | null>(null)
  const turnState = game?.turn.turnState
  const lastRoll = game?.turn.lastRoll

  const rollKey = lastRoll ? `${turnState}:${lastRoll[0]},${lastRoll[1]}` : (turnState ?? null)
  const prevRollKeyRef = useRef<string | null | typeof UNSET>(UNSET)
  if (prevRollKeyRef.current !== rollKey) {
    prevRollKeyRef.current = rollKey
    setDims(
      game && turnState === 'choosingPlacement' && lastRoll ? pickInitialDims(lastRoll, game.turn.legalPlacements) : null,
    )
    setHoveredCell(null)
  }

  function rotate() {
    setDims((prev) => (prev ? [prev[1], prev[0]] : prev))
  }

  function handleCellHover(cell: [number, number]) {
    setHoveredCell(cell)
  }

  const previewTopLeft = game && dims && hoveredCell ? computeTopLeft(hoveredCell, dims, game.board.size) : null

  function place(cell: [number, number]) {
    if (!game || !dims) return
    const topLeft = computeTopLeft(cell, dims, game.board.size)
    const [width, height] = dims
    const entry = game.turn.legalPlacements.find((p) => p.width === width && p.height === height)
    const isLegal = entry?.topLefts.some(([r, c]) => r === topLeft[0] && c === topLeft[1]) ?? false
    if (isLegal) {
      sendAction({ type: 'place', topLeft, width, height })
    }
  }

  function handleCellTap(cell: [number, number], pointerType: string) {
    if (pointerType !== 'touch') {
      place(cell)
      return
    }
    const isSameCell = hoveredCell?.[0] === cell[0] && hoveredCell?.[1] === cell[1]
    if (isSameCell) {
      place(cell)
      setHoveredCell(null)
    } else {
      setHoveredCell(cell)
    }
  }

  return { dims, rotate, previewTopLeft, handleCellHover, handleCellTap }
}
