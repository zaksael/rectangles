import { useMemo, useRef, useState } from 'react'
import type { GameAction, GameWireState } from './gameTypes'

const UNSET = Symbol('unset')

function computeTopLeft(cell: [number, number], dims: [number, number], boardSize: number): [number, number] {
  const [row, col] = cell
  const [width, height] = dims
  const r = Math.max(0, Math.min(row - Math.floor(height / 2), boardSize - height))
  const c = Math.max(0, Math.min(col - Math.floor(width / 2), boardSize - width))
  return [r, c]
}

function findLegalEntry(
  dims: [number, number],
  legalPlacements: GameWireState['turn']['legalPlacements'],
): GameWireState['turn']['legalPlacements'][number] | undefined {
  const [width, height] = dims
  return legalPlacements.find((p) => p.width === width && p.height === height)
}

function isLegalTopLeft(
  topLeft: [number, number],
  dims: [number, number],
  legalPlacements: GameWireState['turn']['legalPlacements'],
): boolean {
  const entry = findLegalEntry(dims, legalPlacements)
  return entry?.topLefts.some(([r, c]) => r === topLeft[0] && c === topLeft[1]) ?? false
}

function computeCoverableCells(
  dims: [number, number],
  legalPlacements: GameWireState['turn']['legalPlacements'],
): [number, number][] {
  const [width, height] = dims
  const entry = findLegalEntry(dims, legalPlacements)
  if (!entry) return []
  const covered = new Set<string>()
  const cells: [number, number][] = []
  for (const [r0, c0] of entry.topLefts) {
    for (let r = r0; r < r0 + height; r++) {
      for (let c = c0; c < c0 + width; c++) {
        const key = `${r},${c}`
        if (!covered.has(key)) {
          covered.add(key)
          cells.push([r, c])
        }
      }
    }
  }
  return cells
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
  const [previewSource, setPreviewSource] = useState<'hover' | 'touch' | null>(null)
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
    setPreviewSource(null)
  }

  function rotate() {
    setDims((prev) => (prev ? [prev[1], prev[0]] : prev))
  }

  function handleCellHover(cell: [number, number]) {
    setHoveredCell(cell)
    setPreviewSource('hover')
  }

  const legalPlacements = game?.turn.legalPlacements
  const coverableCells = useMemo(
    () => (dims && legalPlacements ? computeCoverableCells(dims, legalPlacements) : []),
    [dims, legalPlacements],
  )

  const previewTopLeft = game && dims && hoveredCell ? computeTopLeft(hoveredCell, dims, game.board.size) : null
  const previewIsLegal = game && dims && previewTopLeft ? isLegalTopLeft(previewTopLeft, dims, game.turn.legalPlacements) : false
  const previewKind: 'legal' | 'danger' | 'pending' | null = !previewTopLeft ? null : previewSource === 'touch' ? 'pending' : previewIsLegal ? 'legal' : 'danger'

  function place(cell: [number, number]) {
    if (!game || !dims) return
    const topLeft = computeTopLeft(cell, dims, game.board.size)
    const [width, height] = dims
    if (isLegalTopLeft(topLeft, dims, game.turn.legalPlacements)) {
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
      setPreviewSource(null)
    } else {
      setHoveredCell(cell)
      setPreviewSource('touch')
    }
  }

  return { dims, rotate, previewTopLeft, previewKind, coverableCells, handleCellHover, handleCellTap }
}
