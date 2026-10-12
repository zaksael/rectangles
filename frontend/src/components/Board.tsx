import { memo, type CSSProperties, type FocusEventHandler, type KeyboardEventHandler, type MouseEvent, type PointerEvent, type ReactElement } from 'react'
import type { GameWireState } from '../game/gameTypes'
import { specialCellKinds } from '../game/specialCells'
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
  // Replay's Show Better Option: the placement that would have ranked higher, outlined.
  betterOption?: { topLeft: [number, number]; width: number; height: number } | null
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

function wallKey(a: [number, number], b: [number, number]): string {
  return [cellKey(...a), cellKey(...b)].sort().join('|')
}

// Mirrors the engine's own self-enclosed detection: flood-fills each connected empty
// region and, if it never touches the board edge and borders exactly one player,
// marks every cell in it as enclosed by that player. The wire only sends a per-player
// count (not positions), so this is recomputed client-side from data already on hand.
function selfEnclosedOwners(
  size: number,
  owners: Map<string, number>,
  obstacleCells: Set<string>,
  wallEdges: [number, number][][],
): [number, number, 1 | 2][] {
  const wallSet = new Set(wallEdges.map(([a, b]) => wallKey(a, b)))
  const visited = new Set<string>()
  const result: [number, number, 1 | 2][] = []

  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      const startKey = cellKey(r, c)
      if (visited.has(startKey) || owners.has(startKey) || obstacleCells.has(startKey)) continue

      const region: [number, number][] = []
      const regionOwners = new Set<number>()
      let touchesEdge = false
      const queue: [number, number][] = [[r, c]]
      visited.add(startKey)

      while (queue.length) {
        const [cr, cc] = queue.shift()!
        region.push([cr, cc])
        for (const [nr, nc] of [
          [cr - 1, cc],
          [cr + 1, cc],
          [cr, cc - 1],
          [cr, cc + 1],
        ] as [number, number][]) {
          if (nr < 0 || nr >= size || nc < 0 || nc >= size) {
            touchesEdge = true
            continue
          }
          if (wallSet.has(wallKey([cr, cc], [nr, nc]))) continue
          const nKey = cellKey(nr, nc)
          const owner = owners.get(nKey)
          if (owner === undefined) {
            if (!obstacleCells.has(nKey) && !visited.has(nKey)) {
              visited.add(nKey)
              queue.push([nr, nc])
            }
          } else {
            regionOwners.add(owner)
          }
        }
      }

      if (!touchesEdge && regionOwners.size === 1) {
        const owner = [...regionOwners][0] as 1 | 2
        for (const [er, ec] of region) result.push([er, ec, owner])
      }
    }
  }
  return result
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
  const { obstacles, walls, selfEnclosedPenalty } = game.houseRules
  const coverableSet = new Set((coverableCells ?? []).map(([r, c]) => cellKey(r, c)))

  const owners = new Map<string, number>()
  const outlines: ReactElement[] = []
  let lastPlacedCells: [number, number][] | null = null
  for (const playerId of ['1', '2'] as const) {
    for (const piece of game.players[playerId].board.pieces) {
      const [row, col] = piece.topLeft
      const isLastPlaced = row === lastPlaced?.[0] && col === lastPlaced[1]
      if (isLastPlaced) lastPlacedCells = []
      for (let r = row; r < row + piece.height; r++) {
        for (let c = col; c < col + piece.width; c++) {
          owners.set(cellKey(r, c), piece.owner)
          if (isLastPlaced) lastPlacedCells!.push([r, c])
        }
      }
      outlines.push(
        <div
          key={`${playerId}-${cellKey(row, col)}`}
          className={isLastPlaced ? 'piece-outline last' : 'piece-outline'}
          style={gridBox(row, col, piece.width, piece.height)}
        />,
      )
    }
  }

  const obstacleCells = new Set(obstacles.enabled ? obstacles.cells.map(([r, c]) => cellKey(r, c)) : [])

  const enclosedOwners = selfEnclosedPenalty.enabled
    ? selfEnclosedOwners(size, owners, obstacleCells, walls.enabled ? walls.edges : [])
    : []

  const specialCells = specialCellKinds(game)

  // The most recent placement briefly rings whichever special cell(s) it just captured,
  // mirroring the Pygame renderer's last-move prize highlight - a marker alone isn't
  // enough of a signal for a capture that just happened. Applies to all three kinds
  // for consistency, even though the Pygame reference only ever did it for Prize.
  const captureRing: [number, number][] = []
  if (lastPlacedCells) {
    for (const [r, c] of lastPlacedCells) {
      if (specialCells.has(cellKey(r, c))) captureRing.push([r, c])
    }
  }

  // A player's starting corner stays marked until their first piece covers it.
  const startCells = new Map<string, '1' | '2'>()
  for (const id of ['1', '2'] as const) {
    const { startCorner, pieces } = game.players[id].board
    if (pieces.length === 0) startCells.set(cellKey(startCorner[0], startCorner[1]), id)
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
      // A capture is permanent once a piece covers the cell - the marker doesn't outlive it.
      const special = owner ? undefined : specialCells.get(key)
      if (special) classes.push(special)
      if (coverableSet.has(key)) classes.push('coverable')
      const start = startCells.get(key)
      if (start) classes.push(`start-p${start}`)
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

  // A separate overlay element, not a cell class - the marker itself uses ::before/::after
  // per kind (Steal uses both), so a shared ring class on the cell would collide with them.
  const ringEls = captureRing.map(([r, c]) => (
    <div key={cellKey(r, c)} className="capture-ring" data-cell={cellKey(r, c)} style={gridBox(r, c)} />
  ))

  // Neutral/empty cells that happen to be boxed in by only one player's territory -
  // hatched in that player's color, drawn on top rather than filled, since these
  // cells are never actually part of anyone's territory (GAME_SPEC §6.7).
  const hatchEls = enclosedOwners.map(([r, c, owner]) => (
    <div key={cellKey(r, c)} className={`enclosed-hatch p${owner}`} data-cell={cellKey(r, c)} style={gridBox(r, c)} />
  ))

  return (
    <>
      {cells}
      {wallEls}
      {outlines}
      {ringEls}
      {hatchEls}
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
  betterOption,
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
      role="group"
      aria-label={`${size}×${size} board`}
      aria-describedby={describedBy}
      tabIndex={onKeyDown ? 0 : undefined}
      onKeyDown={onKeyDown}
      onFocus={onFocus}
      // --mover tints the legal-move layers with whoever is placing.
      style={{ '--n': size, '--mover': game.turn.currentPlayerId === 1 ? 'var(--p1)' : 'var(--p2)' } as CSSProperties}
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
      {betterOption && <div className="better-option" style={gridBox(betterOption.topLeft[0], betterOption.topLeft[1], betterOption.width, betterOption.height)} />}
    </div>
  )
}
