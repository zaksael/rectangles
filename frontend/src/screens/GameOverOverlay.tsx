import type { GameWireState, PlayerState } from '../gameTypes'
import { noBreak } from '../noBreak'
import { useAutoOpenDialog } from '../useAutoOpenDialog'

const SCORE_ROWS = [['Territory', 'totalArea']] as const
const FINAL_ROW = ['Final score', 'totalScore'] as const

function deduction(player: PlayerState, points: number): string | number {
  const total = player.houseRules.pitfall.captured * points
  return total > 0 ? `−${total}` : 0
}

function nameOf(game: GameWireState, id: number) {
  return noBreak(game.players[String(id) as '1' | '2'].name)
}

function reasonText(game: GameWireState): string | null {
  const { reason, playerId } = game.gameOver
  if (reason === 'boardFull') return 'board settled'
  if (reason === null || playerId === null) return null
  const name = nameOf(game, playerId)
  if (reason === 'playerBlocked') return `${name} boxed in`
  if (reason === 'skipLimit') {
    const { skipLimit } = game.board
    return `${name} hit the skip limit (${skipLimit} of ${skipLimit})`
  }
  return `${name} surrendered`
}

export function GameOverOverlay({ game, onNewGame }: { game: GameWireState; onNewGame: () => void }) {
  const dialogRef = useAutoOpenDialog()
  const { winner, reason: endReason } = game.gameOver
  const detail = reasonText(game)
  const headline = winner === null ? 'Tied' : `${nameOf(game, winner)} wins${endReason === 'surrender' ? '' : ' on score'}`

  return (
    // Escape has no dismiss action here, so cancel is suppressed.
    <dialog className="modal game-over" ref={dialogRef} onCancel={(e) => e.preventDefault()} aria-labelledby="gameover-title">
      {detail && <p className="reason">Game ended: {detail}</p>}
      <h2 id="gameover-title">
        {winner !== null && <span className={`dot p${winner}`} aria-hidden="true" />}
        {headline}
      </h2>
      <table className="breakdown">
        <thead>
          <tr>
            <th scope="col">
              <span className="visually-hidden">Score</span>
            </th>
            {(['1', '2'] as const).map((id) => (
              <th key={id} scope="col">
                <span className={`swatch p${id}`} aria-hidden="true" />
                {nameOf(game, Number(id))}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {SCORE_ROWS.map(([label, key]) => (
            <tr key={key}>
              <th scope="row">{label}</th>
              <td>{game.players['1'].score[key]}</td>
              <td>{game.players['2'].score[key]}</td>
            </tr>
          ))}
          {game.houseRules.prize.enabled && (
            <tr>
              <th scope="row">Prize</th>
              <td>{game.players['1'].houseRules.prize.captured * game.houseRules.prize.points}</td>
              <td>{game.players['2'].houseRules.prize.captured * game.houseRules.prize.points}</td>
            </tr>
          )}
          {game.houseRules.pitfall.enabled && (
            <tr>
              <th scope="row">Pitfall</th>
              <td className="negative">{deduction(game.players['1'], game.houseRules.pitfall.points)}</td>
              <td className="negative">{deduction(game.players['2'], game.houseRules.pitfall.points)}</td>
            </tr>
          )}
          <tr className="total">
            <th scope="row">{FINAL_ROW[0]}</th>
            <td>{game.players['1'].score[FINAL_ROW[1]]}</td>
            <td>{game.players['2'].score[FINAL_ROW[1]]}</td>
          </tr>
        </tbody>
      </table>
      <div className="actions">
        <button className="btn secondary" onClick={onNewGame} autoFocus>
          New Game
        </button>
      </div>
    </dialog>
  )
}
