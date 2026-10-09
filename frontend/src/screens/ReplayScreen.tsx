import { useState } from 'react'
import { Board } from '../components/Board'
import type { GameWireState, HistoryEntry, PieceState } from '../gameTypes'
import './ReplayScreen.css'

// The board as it stood after the first `step` moves: the final game's rules and special cells, with only those pieces on it.
function gameAt(game: GameWireState, history: HistoryEntry[], step: number): GameWireState {
  const piecesOf = (id: 1 | 2): PieceState[] =>
    history.slice(0, step).flatMap((entry) => (entry.playerId === id && entry.placed ? [{ ...entry.placed, owner: id }] : []))
  const player = (id: 1 | 2) => ({ ...game.players[id], board: { ...game.players[id].board, pieces: piecesOf(id) } })
  return { ...game, players: { '1': player(1), '2': player(2) } }
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
        <p className="turn-line">{`Turn ${step} of ${history.length}`}</p>
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
