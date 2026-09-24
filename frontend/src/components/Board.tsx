import { memo, type CSSProperties, type FocusEventHandler, type KeyboardEventHandler, type MouseEvent, type PointerEvent, type ReactElement } from 'react'
import type { GameWireState } from '../gameTypes'
import './Board.css'

// A grid box, in cells. The stylesheet turns it into pixels from --cell, which fits the viewport.
function gridBox(row: number, col: number, width?: number, height?: number): CSSProperties {
  return { '--r': row, '--c': col, '--w': width, '--h': height } as CSSProperties
}

interface BoardProps {
  game: GameWireState
  previewTopLeft?: [number, number] | null
  previewDims?: [number, number] | null
  previewKind?: 'legal' | 'danger' | 'pending' | null
  coverableCells?: [number, number][]
  lastPlaced?: [number, number] | null
  onCellHover?: (cell: [number, number]) => void
  onCellTap?: (cell: [number, number], pointerType: string) => void
  // Keyboard play: giving onKeyDown makes the board a single tab stop.
  onKeyDown?: KeyboardEventHandler
  onFocus?: FocusEventHandler
  describedBy?: string
}

function cellKey(row: number, col: number): string {
  return `${row},${col}`
}

// The cells, walls and piece outlines only change with the game state, so hovering
// (which just moves the preview) doesn't rebuild the whole grid.
const BoardLayers = memo(function BoardLayers({
  game,
  coverableCells,
  lastPlaced,
}: {
  game: GameWireState
  coverableCells?: [number, number][]
  lastPlaced?: BoardProps['lastPlaced']
}) {
  const { size } = game.board
  const { obstacles, prize, pitfall, steal, walls } = game.houseRules
  const coverableSet = new Set((coverableCells ?? []).map(([r, c]) => cellKey(r, c)))

  const owners = new Map<string, number>()
  const outlines: ReactElement[] = []
  for (const playerId of ['1', '2'] as const) {
    for (const piece of game.players[playerId].board.pieces) {
      const [row, col] = piece.topLeft
      for (let r = row; r < row + piece.height; r++) {
        for (let c = col; c < col + piece.width; c++) {
          owners.set(cellKey(r, c), piece.owner)
        }
      }
      outlines.push(
        <div
          key={`${playerId}-${cellKey(row, col)}`}
          className={row === lastPlaced?.[0] && col === lastPlaced[1] ? 'piece-outline last' : 'piece-outline'}
          style={gridBox(row, col, piece.width, piece.height)}
        />,
      )
    }
  }

  const obstacleCells = new Set(obstacles.enabled ? obstacles.cells.map(([r, c]) => cellKey(r, c)) : [])

  const specialCells = new Map<string, 'prize' | 'pitfall' | 'steal'>()
  for (const [kind, rule] of [
    ['prize', prize],
    ['pitfall', pitfall],
    ['steal', steal],
  ] as const) {
    if (rule.enabled) {
      for (const [r, c] of rule.cells) {
        specialCells.set(cellKey(r, c), kind)
      }
    }
  }

  const cells = []
  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      const key = cellKey(r, c)
      const owner = owners.get(key)
      const classes = ['board-cell']
      if (owner === 1) classes.push('p1-fill')
      else if (owner === 2) classes.push('p2-fill')
      else if (obstacleCells.has(key)) classes.push('obstacle')
      const special = specialCells.get(key)
      if (special) classes.push(special)
      if (coverableSet.has(key)) classes.push('coverable')
      cells.push(
        <div
          key={key}
          className={classes.join(' ')}
          data-cell={key}
        />,
      )
    }
  }

  // A wall sits on the boundary between two cells: a column boundary is vertical, a row boundary horizontal.
  const wallEls = walls.enabled
    ? walls.edges.map(([[r1, c1], [r2, c2]], i) =>
        r1 === r2 ? (
          <div key={i} className="wall wall-v" style={gridBox(r1, Math.max(c1, c2))} />
        ) : (
          <div key={i} className="wall wall-h" style={gridBox(Math.max(r1, r2), c1)} />
        ),
      )
    : []

  return (
    <>
      {cells}
      {wallEls}
      {outlines}
    </>
  )
})

function cellFromEvent(target: EventTarget): [number, number] | null {
  const key = (target as HTMLElement).closest('[data-cell]')?.getAttribute('data-cell')
  if (!key) return null
  const [r, c] = key.split(',').map(Number)
  return [r, c]
}

export function Board({
  game,
  previewTopLeft,
  previewDims,
  previewKind,
  coverableCells,
  lastPlaced,
  onCellHover,
  onCellTap,
  onKeyDown,
  onFocus,
  describedBy,
}: BoardProps) {
  const { size } = game.board

  return (
    <div
      className="board"
      role="grid"
      aria-label={`${size}×${size} board`}
      aria-describedby={describedBy}
      tabIndex={onKeyDown ? 0 : undefined}
      onKeyDown={onKeyDown}
      onFocus={onFocus}
      style={{ '--n': size } as CSSProperties}
      // One delegated handler per event instead of a closure on every cell.
      onMouseOver={(e: MouseEvent) => {
        const cell = cellFromEvent(e.target)
        if (cell) onCellHover?.(cell)
      }}
      onPointerUp={(e: PointerEvent) => {
        const cell = cellFromEvent(e.target)
        if (cell) onCellTap?.(cell, e.pointerType)
      }}
    >
      <BoardLayers game={game} coverableCells={coverableCells} lastPlaced={lastPlaced} />
      {previewTopLeft && previewDims && (
        <div
          className={`preview ${previewKind}`}
          style={gridBox(previewTopLeft[0], previewTopLeft[1], previewDims[0], previewDims[1])}
        />
      )}
    </div>
  )
}
