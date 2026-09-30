import type { GameWireState } from '../gameTypes'
import { noBreak } from '../noBreak'
import { useAutoOpenDialog } from '../useAutoOpenDialog'

const SCORE_ROWS = [['Territory', 'totalArea']] as const
const FINAL_ROW = ['Final score', 'totalScore'] as const

const SELF_ENCLOSED_PENALTY_PER_CELL = 1 // fixed on the server, not sent on the wire or configurable per-game

interface ModifierRow {
  label: string
  enabled: (game: GameWireState) => boolean
  value: (game: GameWireState, id: '1' | '2') => number
}

const MODIFIER_ROWS: ModifierRow[] = [
  {
    label: 'Prize',
    enabled: (game) => game.houseRules.prize.enabled,
    value: (game, id) => game.players[id].houseRules.prize.captured * game.houseRules.prize.points,
  },
  {
    label: 'Pitfall',
    enabled: (game) => game.houseRules.pitfall.enabled,
    value: (game, id) => -(game.players[id].houseRules.pitfall.captured * game.houseRules.pitfall.points),
  },
  {
    label: 'Steal',
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

function storyText(game: GameWireState, rows: ModifierRow[], margin: number | null, swing: Swing | null): string | null {
  if (margin === null) return null
  const comeback = comebackClause(game, rows)
  if (comeback) return `by ${margin} points. ${comeback}`
  return swing ? `by ${margin} points. Biggest swing: ${swing.label}, ${swing.size}.` : `by ${margin} points`
}

export function GameOverOverlay({ game, onNewGame }: { game: GameWireState; onNewGame: () => void }) {
  const dialogRef = useAutoOpenDialog()
  const { winner, reason: endReason } = game.gameOver
  const detail = reasonText(game)
  const rows = MODIFIER_ROWS.filter((row) => row.enabled(game))
  const margin = scoreMargin(game)
  const swing = margin === null ? null : biggestSwing(game, rows, margin)
  const story = storyText(game, rows, margin, swing)
  const headline = winner === null ? 'Tied' : `${nameOf(game, winner)} wins${endReason === 'surrender' ? '' : ' on score'}`

  return (
    // Escape has no dismiss action here, so cancel is suppressed.
    <dialog className="modal game-over" ref={dialogRef} onCancel={(e) => e.preventDefault()} aria-labelledby="gameover-title" aria-describedby={story ? 'gameover-story' : undefined}>
      {detail && <p className="reason">Game ended: {detail}</p>}
      <h2 id="gameover-title">
        {winner !== null && <span className={`dot p${winner}`} aria-hidden="true" />}
        {headline}
      </h2>
      {story && (
        <p className="game-over-story" id="gameover-story">
          {story}
        </p>
      )}
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
          {rows.map((row) => (
            <tr key={row.label}>
              <th scope="row">
                {row.label}
                {swing?.label === row.label && <span className="game-over-swing-tag">Biggest swing</span>}
              </th>
              {(['1', '2'] as const).map((id) => {
                const value = row.value(game, id)
                return (
                  <td key={id} className={value < 0 ? 'negative' : undefined}>
                    {formatSigned(value)}
                  </td>
                )
              })}
            </tr>
          ))}
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
