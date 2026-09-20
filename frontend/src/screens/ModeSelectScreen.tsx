import { useState, type KeyboardEvent } from 'react'

type Opponent = 'bot' | 'local2p'
type BotDifficulty = 'Basic' | 'Greedy' | 'Blocking'
type SeriesLength = 3 | 5 | null

interface HouseRules {
  prizeEnabled: boolean
  pitfallEnabled: boolean
  stealEnabled: boolean
  wallsEnabled: boolean
  obstaclesEnabled: boolean
  selfEnclosedPenaltyEnabled: boolean
  wildcardEnabled: boolean
  rerollEnabled: boolean
  comebackNudgeEnabled: boolean
}

interface ModeSelectSettings {
  opponent: Opponent
  botDifficulty: BotDifficulty
  boardSize: number
  skipLimit: number
  seriesLength: SeriesLength
  houseRules: HouseRules
}

export interface StartGameParams {
  boardSize: number
  skipLimit: number
  seriesLength?: number
  botSeats?: number
  botDifficulty?: BotDifficulty
  wildcardEnabled: boolean
  rerollEnabled: boolean
  wallsEnabled: boolean
  obstaclesEnabled: boolean
  prizeEnabled: boolean
  pitfallEnabled: boolean
  stealEnabled: boolean
  selfEnclosedPenaltyEnabled: boolean
  comebackNudgeEnabled: boolean
}

const STORAGE_KEY = 'rectangles.modeSelectSettings'

// The server's PLAYER_2 preset - the only value botSeats accepts.
const BOT_SEATS = 2

const DEFAULT_SETTINGS: ModeSelectSettings = {
  opponent: 'bot',
  botDifficulty: 'Greedy',
  boardSize: 19,
  skipLimit: 5,
  seriesLength: null,
  houseRules: {
    prizeEnabled: true,
    pitfallEnabled: false,
    stealEnabled: true,
    wallsEnabled: true,
    obstaclesEnabled: false,
    selfEnclosedPenaltyEnabled: true,
    wildcardEnabled: false,
    rerollEnabled: false,
    comebackNudgeEnabled: false,
  },
}

const BOARD_SIZES = [19, 23, 27]
const SKIP_LIMITS = [3, 5]
const DIFFICULTIES: BotDifficulty[] = ['Basic', 'Greedy', 'Blocking']
const GAMES_OPTIONS: { label: string; value: SeriesLength }[] = [
  { label: 'Single game', value: null },
  { label: 'Best of 3', value: 3 },
  { label: 'Best of 5', value: 5 },
]
const HOUSE_RULE_GROUPS: { label: string; rules: { key: keyof HouseRules; label: string }[] }[] = [
  {
    label: 'Special cells',
    rules: [
      { key: 'prizeEnabled', label: 'Prize' },
      { key: 'pitfallEnabled', label: 'Pitfall' },
      { key: 'stealEnabled', label: 'Steal' },
    ],
  },
  {
    label: 'Board setup',
    rules: [
      { key: 'wallsEnabled', label: 'Walls' },
      { key: 'obstaclesEnabled', label: 'Obstacles' },
      { key: 'selfEnclosedPenaltyEnabled', label: 'Enclosure penalty' },
    ],
  },
  {
    label: 'Dice & turn',
    rules: [
      { key: 'wildcardEnabled', label: 'Wildcard roll' },
      { key: 'rerollEnabled', label: 'Reroll' },
      { key: 'comebackNudgeEnabled', label: 'Comeback' },
    ],
  },
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
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
}

function buildStartGameParams(settings: ModeSelectSettings): StartGameParams {
  return {
    boardSize: settings.boardSize,
    skipLimit: settings.skipLimit,
    ...(settings.seriesLength !== null ? { seriesLength: settings.seriesLength } : {}),
    ...(settings.opponent === 'bot'
      ? { botSeats: BOT_SEATS, botDifficulty: settings.botDifficulty }
      : {}),
    ...settings.houseRules,
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

interface ModeSelectScreenProps {
  isConnecting: boolean
  connectFailed: boolean
  onStartGame: (params: StartGameParams) => void
}

export function ModeSelectScreen({ isConnecting, connectFailed, onStartGame }: ModeSelectScreenProps) {
  const [settings, setSettings] = useState<ModeSelectSettings>(loadSettings)

  function updateHouseRule(key: keyof HouseRules, value: boolean): void {
    setSettings((s) => ({ ...s, houseRules: { ...s.houseRules, [key]: value } }))
  }

  function handleStartGame(): void {
    saveSettings(settings)
    onStartGame(buildStartGameParams(settings))
  }

  return (
    <div>
      <p>New Game</p>

      <div role="radiogroup" aria-label="Opponent">
        <div
          role="radio"
          aria-checked={settings.opponent === 'bot'}
          aria-label="Vs Bot"
          tabIndex={0}
          onClick={() => setSettings((s) => ({ ...s, opponent: 'bot' }))}
          onKeyDown={(e) => handleActivateKey(e, () => setSettings((s) => ({ ...s, opponent: 'bot' })))}
        >
          Vs Bot
          {settings.opponent === 'bot' && (
            <div role="radiogroup" aria-label="Difficulty">
              {DIFFICULTIES.map((difficulty) => (
                <div
                  key={difficulty}
                  role="radio"
                  aria-checked={settings.botDifficulty === difficulty}
                  tabIndex={0}
                  onClick={() => setSettings((s) => ({ ...s, botDifficulty: difficulty }))}
                  onKeyDown={(e) =>
                    handleActivateKey(e, () => setSettings((s) => ({ ...s, botDifficulty: difficulty })))
                  }
                >
                  {difficulty}
                </div>
              ))}
            </div>
          )}
        </div>
        <div
          role="radio"
          aria-checked={settings.opponent === 'local2p'}
          tabIndex={0}
          onClick={() => setSettings((s) => ({ ...s, opponent: 'local2p' }))}
          onKeyDown={(e) => handleActivateKey(e, () => setSettings((s) => ({ ...s, opponent: 'local2p' })))}
        >
          Local 2P
        </div>
      </div>

      <div role="radiogroup" aria-label="Board size">
        {BOARD_SIZES.map((size) => (
          <button
            key={size}
            role="radio"
            aria-checked={settings.boardSize === size}
            onClick={() => setSettings((s) => ({ ...s, boardSize: size }))}
          >
            {size}×{size}
          </button>
        ))}
      </div>

      <div role="radiogroup" aria-label="Skip limit">
        {SKIP_LIMITS.map((limit) => (
          <button
            key={limit}
            role="radio"
            aria-checked={settings.skipLimit === limit}
            onClick={() => setSettings((s) => ({ ...s, skipLimit: limit }))}
          >
            {limit}
          </button>
        ))}
      </div>

      <div role="radiogroup" aria-label="Games">
        {GAMES_OPTIONS.map((option) => (
          <button
            key={option.label}
            role="radio"
            aria-checked={settings.seriesLength === option.value}
            onClick={() => setSettings((s) => ({ ...s, seriesLength: option.value }))}
          >
            {option.label}
          </button>
        ))}
      </div>

      {HOUSE_RULE_GROUPS.map((group) => (
        <div key={group.label}>
          <span>{group.label}</span>
          {group.rules.map(({ key, label }) => (
            <div
              key={key}
              role="checkbox"
              aria-checked={settings.houseRules[key]}
              tabIndex={0}
              onClick={() => updateHouseRule(key, !settings.houseRules[key])}
              onKeyDown={(e) => handleActivateKey(e, () => updateHouseRule(key, !settings.houseRules[key]))}
            >
              {label}
            </div>
          ))}
        </div>
      ))}

      <button onClick={handleStartGame} disabled={isConnecting}>
        {isConnecting ? 'Connecting…' : 'Start Game'}
      </button>
      {connectFailed && <div aria-live="polite">Couldn&apos;t connect — try again</div>}
    </div>
  )
}
