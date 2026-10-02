import { useState, type KeyboardEvent } from 'react'
import { implementedGroups, implementedHouseRules, type HouseRules } from '../houseRules'
import { ResetConfirmDialog } from './ResetConfirmDialog'
import './ModeSelectScreen.css'

type Opponent = 'bot' | 'local2p' | null
type BotDifficulty = 'Basic' | 'Greedy' | 'Blocking'
type SeriesLength = 3 | 5 | null

interface ModeSelectSettings {
  opponent: Opponent
  botDifficulty: BotDifficulty
  boardSize: number
  skipLimit: number
  seriesLength: SeriesLength
  houseRules: HouseRules
}

export interface StartGameParams extends Partial<HouseRules> {
  boardSize: number
  skipLimit: number
  seriesLength?: number
  botSeats?: number
  botDifficulty?: BotDifficulty
}

const STORAGE_KEY = 'rectangles.modeSelectSettings:v1'

// The server's PLAYER_2 preset - the only value botSeats accepts.
const BOT_SEATS = 2

const DEFAULT_SETTINGS: ModeSelectSettings = {
  opponent: null,
  botDifficulty: 'Greedy',
  boardSize: 19,
  skipLimit: 5,
  seriesLength: null,
  houseRules: {
    prizeEnabled: true,
    pitfallEnabled: true,
    stealEnabled: true,
    wallsEnabled: true,
    obstaclesEnabled: true,
    selfEnclosedPenaltyEnabled: true,
    wildcardEnabled: true,
    rerollEnabled: true,
    comebackNudgeEnabled: true,
  },
}

// Flip to true when the round-transition screen lands; until then the Games picker is hidden and seriesLength isn't sent.
const SERIES_IMPLEMENTED = false

const BOARD_SIZES = [19, 23, 27]
const SKIP_LIMITS = [3, 5]
const DIFFICULTIES: BotDifficulty[] = ['Basic', 'Greedy', 'Blocking']
const GAMES_OPTIONS: { label: string; value: SeriesLength }[] = [
  { label: 'Single game', value: null },
  { label: 'Best of 3', value: 3 },
  { label: 'Best of 5', value: 5 },
]
function loadSettings(): ModeSelectSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return DEFAULT_SETTINGS
    }
    const parsed = JSON.parse(raw)
    return {
      ...DEFAULT_SETTINGS,
      ...parsed,
      houseRules: { ...DEFAULT_SETTINGS.houseRules, ...parsed.houseRules },
    }
  } catch {
    return DEFAULT_SETTINGS
  }
}

function saveSettings(settings: ModeSelectSettings): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
  } catch {
    // Throws in private browsing (Safari/Firefox) or when storage quota is
    // exceeded - losing sticky settings for this one match isn't worth
    // blocking Start Game over.
  }
}

function buildStartGameParams(settings: ModeSelectSettings): StartGameParams {
  return {
    boardSize: settings.boardSize,
    skipLimit: settings.skipLimit,
    ...(SERIES_IMPLEMENTED && settings.seriesLength !== null ? { seriesLength: settings.seriesLength } : {}),
    ...(settings.opponent === 'bot'
      ? { botSeats: BOT_SEATS, botDifficulty: settings.botDifficulty }
      : {}),
    ...implementedHouseRules(settings.houseRules),
  }
}

// The mode cards, difficulty pills, and house-rule rows are non-native
// (div with role="radio"/"checkbox"), so they don't get Enter/Space
// activation for free the way a real <button> does.
function handleActivateKey(e: KeyboardEvent, onActivate: () => void): void {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    onActivate()
  }
}

// Difficulty is a plain `group`, so a group boundary is either role.
const RADIO_GROUP = '[role="radiogroup"], [role="group"]'
const ARROW_STEP: Record<string, number> = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }

// Radio pattern: an arrow key moves the selection, and focus, to the neighbouring radio of the same group, wrapping.
// Clicking the neighbour reuses its own onClick, so no group needs its own arrow handling.
function handleRadioArrowKey(e: KeyboardEvent<HTMLElement>): void {
  const step = ARROW_STEP[e.key]
  if (!step) return
  const group = e.currentTarget.closest(RADIO_GROUP)!
  const radios = [...group.querySelectorAll<HTMLElement>('[role="radio"]')].filter((r) => r.closest(RADIO_GROUP) === group)
  const next = radios[(radios.indexOf(e.currentTarget) + step + radios.length) % radios.length]
  e.preventDefault()
  next.click()
  next.focus()
}

interface ModeSelectScreenProps {
  isConnecting: boolean
  connectFailed: boolean
  onStartGame: (params: StartGameParams) => void
}

export function ModeSelectScreen({ isConnecting, connectFailed, onStartGame }: ModeSelectScreenProps) {
  const [settings, setSettings] = useState<ModeSelectSettings>(loadSettings)
  const [confirmingReset, setConfirmingReset] = useState(false)

  function updateHouseRule(key: keyof HouseRules, value: boolean): void {
    setSettings((s) => ({ ...s, houseRules: { ...s.houseRules, [key]: value } }))
  }

  function handleStartGame(): void {
    saveSettings(settings)
    onStartGame(buildStartGameParams(settings))
  }

  const noModeSelected = settings.opponent === null
  const visibleGroups = implementedGroups()

  return (
    <div className="mode-select">
      <div className="screen-header">
        <h1 className="title">New Game</h1>
      </div>

      <div className="mode-cards" role="radiogroup" aria-label="Opponent">
        <div
          className={settings.opponent === 'bot' ? 'mode-card selected' : 'mode-card'}
          onClick={() => setSettings((s) => ({ ...s, opponent: 'bot' }))}
        >
          <div
            className="mode-card-select"
            role="radio"
            aria-checked={settings.opponent === 'bot'}
            aria-label="Vs Bot"
            tabIndex={settings.opponent === 'local2p' ? -1 : 0}
            onKeyDown={(e) => {
              handleActivateKey(e, () => setSettings((s) => ({ ...s, opponent: 'bot' })))
              handleRadioArrowKey(e)
            }}
          >
            <span className="mode-name">Vs Bot</span>
            <span className="mode-desc">Play a computer opponent, pick a difficulty</span>
          </div>
          <div
            className={settings.opponent === 'bot' ? 'difficulty-pills' : 'difficulty-pills hidden'}
            role="group"
            aria-label="Difficulty"
            aria-hidden={settings.opponent !== 'bot'}
            inert={settings.opponent !== 'bot'}
          >
            {DIFFICULTIES.map((difficulty, index) => (
              <button
                key={difficulty}
                type="button"
                className={settings.botDifficulty === difficulty ? 'pill active' : 'pill'}
                role="radio"
                aria-checked={settings.botDifficulty === difficulty}
                aria-posinset={index + 1}
                aria-setsize={DIFFICULTIES.length}
                tabIndex={settings.botDifficulty === difficulty ? 0 : -1}
                onKeyDown={handleRadioArrowKey}
                onClick={() => setSettings((s) => ({ ...s, botDifficulty: difficulty }))}
              >
                {difficulty}
              </button>
            ))}
          </div>
        </div>
        <div
          className={settings.opponent === 'local2p' ? 'mode-card selected' : 'mode-card'}
          role="radio"
          aria-checked={settings.opponent === 'local2p'}
          aria-label="Local 2P"
          tabIndex={settings.opponent === 'local2p' ? 0 : -1}
          onClick={() => setSettings((s) => ({ ...s, opponent: 'local2p' }))}
          onKeyDown={(e) => {
            handleActivateKey(e, () => setSettings((s) => ({ ...s, opponent: 'local2p' })))
            handleRadioArrowKey(e)
          }}
        >
          <span className="mode-name">Local 2P</span>
          <span className="mode-desc">Two players share this device</span>
        </div>
      </div>

      {noModeSelected ? (
        <div className="empty-hint-box">
          <p id="start-game-hint" className="empty-hint">
            Choose a mode to configure the match
          </p>
        </div>
      ) : (
        <div className="config">
          <div className="config-section">
            <div className="section-label-row">
              <span className="section-label">Match setup</span>
              <button type="button" className="reset-link" onClick={() => setConfirmingReset(true)}>
                Reset to Defaults
              </button>
            </div>
            <div className="field-row">
              <div className="field">
                <span className="field-label" id="board-size-label">Board size</span>
                <div className="segmented" role="radiogroup" aria-labelledby="board-size-label">
                  {BOARD_SIZES.map((size) => (
                    <button
                      key={size}
                      className={settings.boardSize === size ? 'active' : undefined}
                      type="button"
                      role="radio"
                      aria-checked={settings.boardSize === size}
                      tabIndex={settings.boardSize === size ? 0 : -1}
                      onKeyDown={handleRadioArrowKey}
                      onClick={() => setSettings((s) => ({ ...s, boardSize: size }))}
                    >
                      {size}×{size}
                    </button>
                  ))}
                </div>
              </div>
              <div className="field">
                <span className="field-label" id="skip-limit-label">Skip limit</span>
                <div className="segmented" role="radiogroup" aria-labelledby="skip-limit-label">
                  {SKIP_LIMITS.map((limit) => (
                    <button
                      key={limit}
                      className={settings.skipLimit === limit ? 'active' : undefined}
                      type="button"
                      role="radio"
                      aria-checked={settings.skipLimit === limit}
                      tabIndex={settings.skipLimit === limit ? 0 : -1}
                      onKeyDown={handleRadioArrowKey}
                      onClick={() => setSettings((s) => ({ ...s, skipLimit: limit }))}
                    >
                      {limit}
                    </button>
                  ))}
                </div>
              </div>
              {SERIES_IMPLEMENTED && (
                <div className="field">
                  <span className="field-label" id="games-label">Games</span>
                  <div className="segmented" role="radiogroup" aria-labelledby="games-label">
                    {GAMES_OPTIONS.map((option) => (
                      <button
                        key={option.label}
                        className={settings.seriesLength === option.value ? 'active' : undefined}
                        type="button"
                        role="radio"
                        aria-checked={settings.seriesLength === option.value}
                        tabIndex={settings.seriesLength === option.value ? 0 : -1}
                        onKeyDown={handleRadioArrowKey}
                        onClick={() => setSettings((s) => ({ ...s, seriesLength: option.value }))}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {visibleGroups.length > 0 && (
            <div className="config-section">
              <span className="section-label">House rules</span>
              <div className="rules-groups">
                {visibleGroups.map((group) => (
                  <div className="rules-group" key={group.label}>
                    <span className="group-label">{group.label}</span>
                    <div className="rules-grid">
                      {group.rules.map(({ key, label }) => (
                        <button
                          key={key}
                          type="button"
                          className={settings.houseRules[key] ? 'rule on' : 'rule'}
                          role="checkbox"
                          aria-checked={settings.houseRules[key]}
                          onClick={() => updateHouseRule(key, !settings.houseRules[key])}
                        >
                          <span className="checkbox" aria-hidden="true"></span>
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <button
        className={isConnecting ? 'btn primary connecting' : 'btn primary'}
        onClick={handleStartGame}
        disabled={isConnecting || noModeSelected}
        aria-describedby={noModeSelected ? 'start-game-hint' : undefined}
      >
        {isConnecting ? 'Connecting…' : 'Start Game'}
      </button>
      {connectFailed && (
        <div className="start-error" aria-live="polite">
          Couldn’t connect — your settings are unchanged, try again
        </div>
      )}
      {confirmingReset && (
        <ResetConfirmDialog
          onCancel={() => setConfirmingReset(false)}
          onConfirm={() => {
            setSettings((s) => ({ ...DEFAULT_SETTINGS, opponent: s.opponent }))
            setConfirmingReset(false)
          }}
        />
      )}
    </div>
  )
}
