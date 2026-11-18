import { useEffect, useEffectEvent, useState } from 'react'
import type { GameAction, GameWireState, SeriesWireState } from '../game/gameTypes'
import { BOT_SPEEDS, type BotSpeedLabel } from '../game/botSpeed'
import { KeyBadge } from '../components/KeyBadge'
import { HOUSE_RULE_GROUPS } from '../game/houseRules'
import { seriesRound } from '../game/seriesRound'
import { useAutoOpenDialog } from '../hooks/useAutoOpenDialog'
import { LeaveSeriesDialog } from './LeaveSeriesDialog'
import { SurrenderConfirmDialog } from './SurrenderConfirmDialog'

interface SettingsOverlayProps {
  game: GameWireState
  series: SeriesWireState | null
  modeLabel: string
  sendAction: (action: GameAction) => void
  onClose: () => void
  onLeaveSeries: () => void
  botSeat?: number | undefined
  // Given in a Vs Bot match only: the Menu's one adjustable item.
  botSpeed?: { current: BotSpeedLabel; onChange: (label: BotSpeedLabel) => void } | undefined
}

export function SettingsOverlay({ game, series, modeLabel, sendAction, onClose, onLeaveSeries, botSeat, botSpeed }: SettingsOverlayProps) {
  const dialogRef = useAutoOpenDialog()
  const enabledCount = Object.values(game.houseRules).filter((rule) => rule.enabled).length
  // The seat that opened the confirm: a turn change under it (a skip the server was still answering) closes it rather than make the other player concede.
  const [surrenderSeat, setSurrenderSeat] = useState<1 | 2 | null>(null)
  const currentSeat = game.turn.currentPlayerId === 1 ? 1 : 2
  if (surrenderSeat !== null && surrenderSeat !== currentSeat) setSurrenderSeat(null)
  const [leaving, setLeaving] = useState(false)
  const isBotTurn = botSeat !== undefined && game.turn.currentPlayerId === botSeat
  // The screen behind ignores keys while a dialog is open, so the key that opened the Menu closes it here (not over the confirm on top of it).
  const handleKeyDown = useEffectEvent((event: KeyboardEvent) => {
    if (event.key.toLowerCase() === 'm' && !event.repeat && !event.ctrlKey && !event.metaKey && !event.altKey && surrenderSeat === null && !leaving) onClose()
  })
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => handleKeyDown(event)
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])
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
      <h2 id="settings-title">Menu</h2>
      <div className="settings-body">
        <dl className="match-info">
          <div>
            <dt>Mode</dt>
            <dd>{modeLabel}</dd>
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
                {`Round ${seriesRound(game, series)} of ${series.length} — ${series.scores['1']}–${series.scores['2']}`}
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
                    const on = game.houseRules[rule.wire].enabled
                    return (
                      <li key={rule.key} className={on ? 'settings-rule on' : 'settings-rule'}>
                        <span>{rule.label}</span>
                        <span className="settings-rule-state">{on ? 'On' : 'Off'}</span>
                      </li>
                    )
                  })}
                </ul>
              </section>
            ))}
          </div>
        )}
        {botSpeed && (
          <div className="settings-speed">
            <h3>Bot speed</h3>
            <div className="speed-options" role="group" aria-label="Bot speed">
              {BOT_SPEEDS.map((speed) => (
                <button key={speed.label} className="btn secondary" aria-pressed={speed.label === botSpeed.current} onClick={() => botSpeed.onChange(speed.label)}>
                  {speed.label}
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="settings-footer">
          <div className="actions">
            <button className="btn secondary" onClick={onClose} aria-keyshortcuts="Escape" autoFocus>
              Resume
              <KeyBadge>Esc</KeyBadge>
            </button>
            {game.turn.turnState !== 'gameOver' && (
              <button className="btn destructive quiet" onClick={() => !isBotTurn && setSurrenderSeat(currentSeat)} aria-disabled={isBotTurn || undefined} aria-describedby={isBotTurn ? 'surrender-note' : undefined}>
                Surrender
              </button>
            )}
            {series && !series.isComplete && (
              <button className="btn destructive quiet" onClick={() => setLeaving(true)}>
                Leave series
              </button>
            )}
          </div>
          {isBotTurn && game.turn.turnState !== 'gameOver' && (
            <p id="surrender-note" className={series && !series.isComplete ? 'settings-footer-note centred' : 'settings-footer-note'}>
              Available on your turn
            </p>
          )}
        </div>
      </div>
      {leaving && <LeaveSeriesDialog onCancel={() => setLeaving(false)} onConfirm={onLeaveSeries} />}
      {surrenderSeat !== null && (
        <SurrenderConfirmDialog
          playerName={game.players[surrenderSeat === 1 ? '1' : '2'].name}
          opponentName={game.players[surrenderSeat === 1 ? '2' : '1'].name}
          scores={(['1', '2'] as const).map((id) => ({ name: game.players[id].name, score: game.players[id].score.totalScore }))}
          isSeries={series !== null}
          onCancel={() => setSurrenderSeat(null)}
          onConfirm={() => {
            sendAction({ type: 'surrender' })
            setSurrenderSeat(null)
            onClose()
          }}
        />
      )}
    </dialog>
  )
}
