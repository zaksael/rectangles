import { useState } from 'react'
import type { GameAction, GameWireState, SeriesWireState } from '../gameTypes'
import { HOUSE_RULE_GROUPS } from '../houseRules'
import { useAutoOpenDialog } from '../useAutoOpenDialog'
import { SurrenderConfirmDialog } from './SurrenderConfirmDialog'

interface SettingsOverlayProps {
  game: GameWireState
  series: SeriesWireState | null
  opponentLabel: string
  sendAction: (action: GameAction) => void
  onClose: () => void
  botSeat?: number
}

export function SettingsOverlay({ game, series, opponentLabel, sendAction, onClose, botSeat }: SettingsOverlayProps) {
  const dialogRef = useAutoOpenDialog()
  const enabledCount = Object.values(game.houseRules).filter((rule) => rule.enabled).length
  const [confirmingSurrender, setConfirmingSurrender] = useState(false)
  const isBotTurn = botSeat !== undefined && game.turn.currentPlayerId === botSeat
  return (
    // Suppress the native auto-close so Escape routes through the same onClose as the button.
    <dialog
      className="modal settings"
      ref={dialogRef}
      aria-labelledby="settings-title"
      onCancel={(e) => {
        e.preventDefault()
        onClose()
      }}
    >
      <div className="settings-header">
        <h2 id="settings-title">Menu</h2>
      </div>
      <div className="settings-body">
        <dl className="match-info">
          <div>
            <dt>Opponent</dt>
            <dd>{opponentLabel}</dd>
          </div>
          <div>
            <dt>Board size</dt>
            <dd>
              {game.board.size}×{game.board.size}
            </dd>
          </div>
          <div>
            <dt>Skip limit</dt>
            <dd>{game.board.skipLimit}</dd>
          </div>
          {series && (
            <div>
              <dt>Series</dt>
              <dd>
                Round {series.gamesPlayed + 1} of {series.length}
              </dd>
            </div>
          )}
        </dl>
        <p className="settings-rules-summary">
          {enabledCount === 0 ? 'No house rules in this match' : `${enabledCount} house ${enabledCount === 1 ? 'rule' : 'rules'} on`}
        </p>
        {enabledCount > 0 && (
          <div className="settings-rules">
            {HOUSE_RULE_GROUPS.map((group) => (
              <section key={group.label}>
                <h3>{group.label}</h3>
                <ul>
                  {group.rules.map((rule) => {
                    const wireKey = rule.key.replace(/Enabled$/, '') as keyof GameWireState['houseRules']
                    const on = game.houseRules[wireKey].enabled
                    return (
                      <li key={rule.key} className={on ? 'settings-rule on' : 'settings-rule'}>
                        <span className="settings-box" aria-hidden="true" />
                        <span>{rule.label}</span>
                        <span className="visually-hidden">{on ? 'On' : 'Off'}</span>
                      </li>
                    )
                  })}
                </ul>
              </section>
            ))}
          </div>
        )}
        <div className="settings-footer">
          <div className="actions">
            <button className="btn secondary" onClick={onClose} autoFocus>
              Resume
            </button>
            {game.turn.turnState !== 'gameOver' && (
              <button className="btn destructive" onClick={() => setConfirmingSurrender(true)} disabled={isBotTurn}>
                Surrender
              </button>
            )}
          </div>
        </div>
      </div>
      {confirmingSurrender && (
        <SurrenderConfirmDialog
          opponentName={game.players[game.turn.currentPlayerId === 1 ? '2' : '1'].name}
          scores={(['1', '2'] as const).map((id) => ({ name: game.players[id].name, score: game.players[id].score.totalScore }))}
          isSeries={series !== null}
          onCancel={() => setConfirmingSurrender(false)}
          onConfirm={() => {
            sendAction({ type: 'surrender' })
            setConfirmingSurrender(false)
            onClose()
          }}
        />
      )}
    </dialog>
  )
}
