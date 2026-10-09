import { useState } from 'react'
import { Board } from '../components/Board'
import type { GameWireState, HistoryEntry, PieceState, ScoreParts } from '../gameTypes'
import { noBreak } from '../noBreak'
import { formatSigned, reasonText, SELF_ENCLOSED_PENALTY_PER_CELL } from './GameOverOverlay'
import './ReplayScreen.css'

// The board as it stood after the first `step` moves: the final game's rules and special cells, with only those pieces on it.
function gameAt(game: GameWireState, history: HistoryEntry[], step: number): GameWireState {
  const piecesOf = (id: 1 | 2): PieceState[] =>
    history.slice(0, step).flatMap((entry) => (entry.playerId === id && entry.placed ? [{ ...entry.placed, owner: id }] : []))
  const player = (id: 1 | 2) => ({ ...game.players[id], board: { ...game.players[id].board, pieces: piecesOf(id) } })
  return { ...game, players: { '1': player(1), '2': player(2) } }
}

const rollText = (roll: [number, number]) => roll.join(', ')

function moveText(game: GameWireState, entry: HistoryEntry): string {
  const name = noBreak(game.players[String(entry.playerId) as '1' | '2'].name)
  const { placed, wildcardOriginalRoll } = entry
  if (!placed) return `${name} skipped (rolled ${rollText(entry.roll)})`
  const [row, col] = placed.topLeft
  const wildcard = wildcardOriginalRoll ? ` (wildcard: rolled ${rollText(wildcardOriginalRoll)})` : ''
  return `${name} placed a ${placed.width}×${placed.height} rectangle at (${row}, ${col})${wildcard}`
}

const ZERO_PARTS: ScoreParts = { area: 0, prize: 0, pitfall: 0, steal: 0, enclosure: 0 }

// What the placing player's score parts gained or lost on this step, named the way the rules read.
function effectTexts(game: GameWireState, history: HistoryEntry[], step: number): string[] {
  const entry = history[step - 1]
  const me = String(entry.playerId) as '1' | '2'
  const opponent = noBreak(game.players[me === '1' ? '2' : '1'].name)
  const before = step === 1 ? ZERO_PARTS : history[step - 2].breakdown[me]
  const now = entry.breakdown[me]
  const gained = (part: keyof ScoreParts) => now[part] - before[part]
  const texts: string[] = []
  if (gained('prize') > 0) texts.push(`captures Prize (+${gained('prize')})`)
  if (gained('steal') > 0) texts.push(`captures Steal (+${gained('steal')}, ${opponent} −${gained('steal')})`)
  if (gained('pitfall') < 0) texts.push(`hits Pitfall (−${-gained('pitfall')})`)
  if (gained('enclosure') < 0) texts.push(`encloses ${-gained('enclosure') / SELF_ENCLOSED_PENALTY_PER_CELL} of its own cells (−${-gained('enclosure')})`)
  return texts
}

// The last step ends on why the game stopped; a surrender also says who won.
function endText(game: GameWireState): string | null {
  const reason = reasonText(game)
  const { winner } = game.gameOver
  return game.gameOver.reason === 'surrender' && winner !== null ? `${reason}, ${noBreak(game.players[String(winner) as '1' | '2'].name)} wins` : reason
}

function Caption({ game, history, step }: { game: GameWireState; history: HistoryEntry[]; step: number }) {
  const notes = step === 0 ? [] : [...effectTexts(game, history, step), step === history.length ? endText(game) : null].filter(Boolean)
  return (
    <p className="caption" data-testid="replay-caption" aria-live="polite">
      {step === 0 ? (
        <>
          <span className="step">Start of game</span>No moves played yet
        </>
      ) : (
        <>
          <span className="step">{`Turn ${step} of ${history.length}`}</span>
          {moveText(game, history[step - 1]) + (notes.length ? ` — ${notes.join(', ')}` : '')}
        </>
      )}
    </p>
  )
}

const RULE_ROWS = [
  { label: 'Prize', part: 'prize', on: (g: GameWireState) => g.houseRules.prize.enabled },
  { label: 'Pitfall', part: 'pitfall', on: (g: GameWireState) => g.houseRules.pitfall.enabled },
  { label: 'Steal', part: 'steal', on: (g: GameWireState) => g.houseRules.steal.enabled },
  { label: 'Enclosure', part: 'enclosure', on: (g: GameWireState) => g.houseRules.selfEnclosedPenalty.enabled },
] as const

const signed = (n: number) => (n > 0 ? `+${n}` : formatSigned(n))

// Each rule's share of both players' scores at the step, so the total can be read as a sum.
function ScoreTable({ game, history, step }: { game: GameWireState; history: HistoryEntry[]; step: number }) {
  const at = history[step - 1]
  const ids = ['1', '2'] as const
  return (
    <table className="breakdown">
      <caption className="visually-hidden">{`Score at ${step === 0 ? 'the start of the game' : `turn ${step}`}`}</caption>
      <thead>
        <tr>
          <td />
          {ids.map((id) => (
            <th key={id} scope="col">
              <span className={`dot p${id}`} aria-hidden="true" />
              {game.players[id].name}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr>
          <th scope="row">Area</th>
          {ids.map((id) => (
            <td key={id}>{at ? at.breakdown[id].area : 0}</td>
          ))}
        </tr>
        {RULE_ROWS.filter((row) => row.on(game)).map((row) => (
          <tr key={row.label}>
            <th scope="row">{row.label}</th>
            {ids.map((id) => {
              const value = at ? at.breakdown[id][row.part] : 0
              return (
                <td key={id} className={value === 0 ? 'zero' : undefined}>
                  {signed(value)}
                </td>
              )
            })}
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr>
          <th scope="row">Total</th>
          {ids.map((id) => (
            <td key={id}>{formatSigned(at ? at.score[id] : 0)}</td>
          ))}
        </tr>
      </tfoot>
    </table>
  )
}

export function ReplayScreen({ game, onBack }: { game: GameWireState; onBack: () => void }) {
  const history = game.gameOver.history ?? []
  const [step, setStep] = useState(0)
  const lastPlaced = history[step - 1]?.placed?.topLeft ?? null

  return (
    <div className="replay">
      <div className="board-wrap">
        <Board game={gameAt(game, history, step)} lastPlaced={lastPlaced} />
      </div>
      <div className="rail">
        <div className="rail-head">
          <h1 className="rail-title">Replay</h1>
          <button className="btn secondary" onClick={onBack}>Back</button>
        </div>
        <ScoreTable game={game} history={history} step={step} />
        <Caption game={game} history={history} step={step} />
        <div className="transport">
          <button className="btn secondary" disabled={step === 0} onClick={() => setStep(0)}>First</button>
          <button className="btn secondary" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>Prev</button>
          <button className="btn secondary" disabled={step === history.length} onClick={() => setStep((s) => s + 1)}>Next</button>
          <button className="btn secondary" disabled={step === history.length} onClick={() => setStep(history.length)}>Last</button>
        </div>
      </div>
    </div>
  )
}
