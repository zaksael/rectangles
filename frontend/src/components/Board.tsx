import type { CSSProperties, ReactElement } from 'react'
import type { GameWireState } from '../gameTypes'
import './Board.css'

const CELL = 44

interface BoardProps {
  game: GameWireState
}

function cellKey(row: number, col: number): string {
  return `${row},${col}`
}

export function Board({ game }: BoardProps) {
  const { size } = game.board
  const { obstacles, prize, pitfall, steal, walls } = game.houseRules

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
          className="piece-outline"
          style={{ left: col * CELL, top: row * CELL, width: piece.width * CELL, height: piece.height * CELL }}
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
      cells.push(<div key={key} className={classes.join(' ')} data-cell={key} />)
    }
  }

  const wallEls = walls.enabled
    ? walls.edges.map(([[r1, c1], [r2, c2]], i) => {
        const style: CSSProperties =
          r1 === r2
            ? { left: Math.max(c1, c2) * CELL - 2.5, top: r1 * CELL, width: 5, height: CELL }
            : { left: c1 * CELL, top: Math.max(r1, r2) * CELL - 2.5, width: CELL, height: 5 }
        return <div key={i} className="wall" style={style} />
      })
    : []

  return (
    <div
      className="board"
      role="grid"
      aria-label={`${size}×${size} board`}
      style={{ gridTemplateColumns: `repeat(${size}, ${CELL}px)`, gridTemplateRows: `repeat(${size}, ${CELL}px)` }}
    >
      {cells}
      {wallEls}
      {outlines}
    </div>
  )
}
