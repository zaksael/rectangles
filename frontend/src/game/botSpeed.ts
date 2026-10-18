export type BotSpeedLabel = 'Slow' | 'Normal' | 'Fast'
export interface BotSpeed {
  label: BotSpeedLabel
  ms: number
}

export const BOT_SPEEDS: readonly BotSpeed[] = [
  { label: 'Slow', ms: 1000 },
  { label: 'Normal', ms: 500 },
  { label: 'Fast', ms: 150 },
]

const DEFAULT_SPEED = BOT_SPEEDS[1]!

const STORAGE_KEY = 'rectangles.botSpeed:v1'

export function loadBotSpeed(): BotSpeed {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return BOT_SPEEDS.find((speed) => speed.label === stored) ?? DEFAULT_SPEED
  } catch {
    return DEFAULT_SPEED
  }
}

export function saveBotSpeed(label: BotSpeedLabel): void {
  try {
    localStorage.setItem(STORAGE_KEY, label)
  } catch {
    // Private browsing or a full quota: the choice just doesn't outlive this page.
  }
}
