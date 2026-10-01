import type { GameWireState } from '../gameTypes'
import { noBreak } from '../noBreak'
import { useAutoOpenDialog } from '../useAutoOpenDialog'


const SELF_ENCLOSED_PENALTY_PER_CELL = 1 // fixed on the server, not sent on the wire or configurable per-game

interface ModifierRow {
  label: string
  note: (game: GameWireState) => string
  enabled: (game: GameWireState) => boolean
  value: (game: GameWireState, id: '1' | '2') => number
}

const MODIFIER_ROWS: ModifierRow[] = [
  {
    label: 'Prize',
    note: (game) => `+${game.houseRules.prize.points} per captured cell`,
    enabled: (game) => game.houseRules.prize.enabled,
    value: (game, id) => game.players[id].houseRules.prize.captured * game.houseRules.prize.points,
  },
  {
    label: 'Pitfall',
    note: (game) => `−${game.houseRules.pitfall.points} per captured cell`,
    enabled: (game) => game.houseRules.pitfall.enabled,
    value: (game, id) => -(game.players[id].houseRules.pitfall.captured * game.houseRules.pitfall.points),
  },
  {
    label: 'Steal',
    note: (game) => `±${game.houseRules.steal.points} per capture, zero-sum`,
    // Zero-sum: each capture adds to the capturer and docks the opponent by the same
    // amount, so a player's net is their own captures minus the opponent's, in points.
    enabled: (game) => game.houseRules.steal.enabled,
    value: (game, id) => {
      const opponent = id === '1' ? '2' : '1'
      const { captured: own } = game.players[id].houseRules.steal
      const { captured: theirs } = game.players[opponent].houseRules.steal
      return (own - theirs) * game.houseRules.steal.points
    },
  },
  {
    label: 'Enclosure',
    note: () => `−${SELF_ENCLOSED_PENALTY_PER_CELL} per sealed-in cell`,
    enabled: (game) => game.houseRules.selfEnclosedPenalty.enabled,
    value: (game, id) => -(game.players[id].houseRules.selfEnclosedPenalty.cells * SELF_ENCLOSED_PENALTY_PER_CELL),
  },
]

function formatSigned(value: number): string | number {
  return value < 0 ? `−${-value}` : value
}

const key = (id: number) => String(id) as '1' | '2'

interface Swing {
  label: string
  size: number
}

function nameOf(game: GameWireState, id: number) {
  return noBreak(game.players[key(id)].name)
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

function scoreMargin(game: GameWireState): number | null {
  const { winner, reason } = game.gameOver
  // A surrendered game's winner can trail on score, so there's no margin to state.
  if (winner === null || reason === 'surrender') return null
  const margin = game.players[key(winner)].score.totalScore - game.players[key(3 - winner)].score.totalScore
  return margin > 0 ? margin : null
}

// The modifier row whose gap between the players is largest, when it covers at least half the margin.
function biggestSwing(game: GameWireState, rows: ModifierRow[], margin: number): Swing | null {
  let best: Swing | null = null
  for (const row of rows) {
    const size = Math.abs(row.value(game, '1') - row.value(game, '2'))
    if (size > 0 && (best === null || size > best.size)) best = { label: row.label, size }
  }
  return best && best.size * 2 >= margin ? best : null
}

// A winner who trailed on territory is explained by the modifiers that went their way, not by the biggest swing.
function comebackClause(game: GameWireState, rows: ModifierRow[]): string | null {
  const { winner } = game.gameOver
  if (winner === null) return null
  const id = key(winner)
  const other = key(3 - winner)
  const trailedBy = game.players[other].score.totalArea - game.players[id].score.totalArea
  if (trailedBy <= 0) return null
  const turned = rows.filter((row) => row.value(game, id) > row.value(game, other)).map((row) => row.label)
  return turned.length ? `Trailed by ${trailedBy} on territory, won on ${new Intl.ListFormat('en-GB').format(turned)}.` : null
}

const pointsText = (n: number) => `${n} ${n === 1 ? 'point' : 'points'}`

function storyText(game: GameWireState, rows: ModifierRow[], margin: number | null, swing: Swing | null): string | null {
  if (margin === null) return null
  const comeback = comebackClause(game, rows)
  if (comeback) return `by ${pointsText(margin)}. ${comeback}`
  return swing ? `by ${pointsText(margin)}. Biggest swing: ${swing.label}, ${swing.size}.` : `by ${pointsText(margin)}`
}

function headlineText(game: GameWireState): string {
  const { winner, reason } = game.gameOver
  return winner === null ? 'Tied' : `${nameOf(game, winner)} wins${reason === 'surrender' ? '' : ' on score'}`
}

// What is left of the result while the player looks at the final board: the outcome, and a way back.
export function GameOverBar({ game, onViewResult, onNewGame }: { game: GameWireState; onViewResult: () => void; onNewGame: () => void }) {
  const reason = game.gameOver.reason === 'boardFull' ? null : reasonText(game)
  const score1 = game.players['1'].score.totalScore
  const score2 = game.players['2'].score.totalScore
  return (
    <div className="game-over-bar" role="region" aria-label="Game result">
      <div className="game-over-bar-text">
        <strong>
          <span className={`dot ${game.gameOver.winner === null ? 'tie' : `p${game.gameOver.winner}`}`} aria-hidden="true" />
          {headlineText(game)}
        </strong>
        {reason && <span className="game-over-bar-reason">{reason}</span>}
      </div>
      <span className="game-over-bar-score">
        <span aria-hidden="true">
          {score1} – {score2}
        </span>
        <span className="visually-hidden">{`${nameOf(game, 1)} ${score1}, ${nameOf(game, 2)} ${score2}`}</span>
      </span>
      <div className="game-over-bar-actions">
        <button className="btn secondary" onClick={onViewResult} autoFocus>
          View Result
        </button>
        <button className="btn secondary" onClick={onNewGame}>
          New Game
        </button>
      </div>
    </div>
  )
}

export function GameOverOverlay({ game, onNewGame, onViewBoard }: { game: GameWireState; onNewGame: () => void; onViewBoard: () => void }) {
  const dialogRef = useAutoOpenDialog()
  const { winner, reason: endReason } = game.gameOver
  const detail = reasonText(game)
  // An enabled rule nobody triggered carries no information, so its row is left out.
  const rows = MODIFIER_ROWS.filter((row) => row.enabled(game) && (row.value(game, '1') !== 0 || row.value(game, '2') !== 0))
  const margin = scoreMargin(game)
  const swing = margin === null ? null : biggestSwing(game, rows, margin)
  const story = storyText(game, rows, margin, swing)

  return (
    // Escape shows the board rather than dismissing the result, so the native close is suppressed.
    <dialog className="modal game-over" data-outcome={winner ?? 'tie'} ref={dialogRef} onCancel={(e) => {
        e.preventDefault()
        onViewBoard()
      }} aria-labelledby="gameover-title" aria-describedby={story ? 'gameover-story' : undefined}>
      {detail && <p className="reason">Game ended: {detail}</p>}
      <h2 id="gameover-title">
        {winner !== null && <span className={`dot p${winner}`} aria-hidden="true" />}
        {headlineText(game)}
      </h2>
      {story && (
        <p className="game-over-story" id="gameover-story">
          {story}
        </p>
      )}
      {endReason === 'surrender' && <p className="game-over-caption">Score at surrender</p>}
      <div className="game-over-scoreboard" role="group" aria-label="Final score">
        {(['1', '2'] as const).map((id) => (
          // The winner of a surrendered game can trail, so muting the lower total would contradict the headline.
          <div key={id} className={winner === null || endReason === 'surrender' || winner === Number(id) ? 'lead' : 'trail'}>
            <div className="who">
              <span className={`swatch p${id}`} aria-hidden="true" />
              {nameOf(game, Number(id))}
            </div>
            <div className="n">{game.players[id].score.totalScore}</div>
          </div>
        ))}
      </div>
      {rows.length > 0 && (
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
            <tr>
              <th scope="row">Territory</th>
              <td>{game.players['1'].score.totalArea}</td>
              <td>{game.players['2'].score.totalArea}</td>
            </tr>
            {rows.map((row) => (
              <tr key={row.label}>
                <th scope="row">
                  {row.label}
                  {swing?.label === row.label && <span className="game-over-swing-tag">Biggest swing</span>}
                  <span className="game-over-row-note">{row.note(game)}</span>
                </th>
                {(['1', '2'] as const).map((id) => {
                  const value = row.value(game, id)
                  return (
                    <td key={id} className={value < 0 ? 'negative' : value === 0 ? 'zero' : undefined}>
                      {formatSigned(value)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="actions">
        <button className="btn primary" onClick={onViewBoard} autoFocus>
          View Board
        </button>
        <button className="btn secondary" onClick={onNewGame}>
          New Game
        </button>
      </div>
    </dialog>
  )
}
