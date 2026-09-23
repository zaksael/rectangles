import type { GameWireState } from '../gameTypes'
import { useAutoOpenDialog } from '../useAutoOpenDialog'

const ROWS = [
  ['Territory', 'totalArea'],
  ['Final score', 'totalScore'],
] as const

function nameOf(game: GameWireState, id: number) {
  return game.players[String(id) as '1' | '2'].name
}

function reasonText(game: GameWireState): string | null {
  const { reason, playerId } = game.gameOver
  if (reason === 'boardFull') return 'Board settled'
  if (reason === null || playerId === null) return null
  const name = nameOf(game, playerId)
  if (reason === 'playerBlocked') return `${name} boxed in`
  if (reason === 'skipLimit') return `${name} skipped out (${game.board.skipLimit}/${game.board.skipLimit})`
  return `${name} surrendered`
}

export function GameOverOverlay({ game }: { game: GameWireState }) {
  const dialogRef = useAutoOpenDialog()
  const { winner } = game.gameOver
  const reason = reasonText(game)
  const headline = winner === null ? 'Tied' : `${nameOf(game, winner)} wins`

  return (
    // Escape has no dismiss action here, so cancel is suppressed.
    <dialog className="modal game-over" ref={dialogRef} onCancel={(e) => e.preventDefault()} aria-labelledby="gameover-title">
      {reason && <p className="reason">{reason}</p>}
      <h2 id="gameover-title">
        {winner !== null && <span className={`dot p${winner}`} />}
        {headline}
      </h2>
      <table className="breakdown">
        <thead>
          <tr>
            <th />
            <th>
              <span className="swatch p1" />
              P1
            </th>
            <th>
              <span className="swatch p2" />
              P2
            </th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map(([label, key]) => (
            <tr key={key} className={key === 'totalScore' ? 'total' : undefined}>
              <td>{label}</td>
              <td>{game.players['1'].score[key]}</td>
              <td>{game.players['2'].score[key]}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </dialog>
  )
}
