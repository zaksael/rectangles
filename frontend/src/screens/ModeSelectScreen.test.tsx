import { readFileSync } from 'node:fs'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, onTestFinished, test, vi } from 'vitest'
import { ModeSelectScreen } from './ModeSelectScreen'

beforeEach(() => {
  localStorage.clear()
})

test('the screen title is a heading', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)

  expect(screen.getByRole('heading', { name: 'New Game' })).toBeInTheDocument()
})

test('on first launch, no mode is selected and Start Game is disabled with a hint', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)

  expect(screen.getByRole('radio', { name: 'Vs Bot' })).toHaveAttribute('aria-checked', 'false')
  expect(screen.getByRole('radio', { name: 'Local 2P' })).toHaveAttribute('aria-checked', 'false')
  const startButton = screen.getByRole('button', { name: 'Start Game' })
  expect(startButton).toBeDisabled()
  expect(startButton).toHaveAccessibleDescription('Choose a mode to enable Start Game')
})

test('selecting a mode enables Start Game and clears the hint', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))

  expect(screen.getByRole('button', { name: 'Start Game' })).not.toBeDisabled()
  expect(screen.queryByText('Choose a mode to enable Start Game')).not.toBeInTheDocument()
})

test('Start Game with default settings passes the documented first-launch connect params, plus implemented house-rule flags', () => {
  const onStartGame = vi.fn()
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={onStartGame} />)

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))

  expect(onStartGame).toHaveBeenCalledWith({
    boardSize: 19,
    skipLimit: 5,
    botSeats: 2,
    botDifficulty: 'Greedy',
    wallsEnabled: true,
    obstaclesEnabled: true,
    prizeEnabled: true,
    pitfallEnabled: true,
    stealEnabled: true,
    selfEnclosedPenaltyEnabled: true,
    wildcardEnabled: true,
    rerollEnabled: true,
    comebackNudgeEnabled: true,
  })
})

test('only house rules with implemented UI are shown', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))

  expect(screen.getAllByRole('checkbox')).toHaveLength(9)
  expect(screen.getByRole('checkbox', { name: 'Walls' })).toBeInTheDocument()
  expect(screen.getByRole('checkbox', { name: 'Obstacles' })).toBeInTheDocument()
  expect(screen.getByRole('checkbox', { name: 'Prize' })).toBeInTheDocument()
  expect(screen.getByRole('checkbox', { name: 'Pitfall' })).toBeInTheDocument()
  expect(screen.getByRole('checkbox', { name: 'Steal' })).toBeInTheDocument()
  expect(screen.getByRole('checkbox', { name: 'Enclosure penalty' })).toBeInTheDocument()
  expect(screen.getByRole('checkbox', { name: 'Wildcard roll' })).toBeInTheDocument()
  expect(screen.getByRole('checkbox', { name: 'Reroll' })).toBeInTheDocument()
  expect(screen.getByRole('checkbox', { name: 'Comeback' })).toBeInTheDocument()
})

test('selecting Local 2P hides the difficulty pills and omits botSeats/botDifficulty from Start Game', () => {
  const onStartGame = vi.fn()
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={onStartGame} />)

  fireEvent.click(screen.getByRole('radio', { name: 'Local 2P' }))
  expect(screen.queryByRole('radio', { name: 'Greedy' })).not.toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))

  expect(onStartGame).toHaveBeenCalledWith(expect.not.objectContaining({ botSeats: expect.anything() }))
  expect(onStartGame.mock.calls[0][0]).not.toHaveProperty('botDifficulty')
})

test('the difficulty-pills row stays mounted (reserving its space) even when it is hidden', () => {
  const { container } = render(
    <ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />,
  )

  expect(container.querySelector('.difficulty-pills')).toBeInTheDocument()

  fireEvent.click(screen.getByRole('radio', { name: 'Local 2P' }))
  expect(container.querySelector('.difficulty-pills')).toBeInTheDocument()
  expect(container.querySelector('.difficulty-pills')).toHaveClass('hidden')

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  expect(container.querySelector('.difficulty-pills')).not.toHaveClass('hidden')
})

test('hidden difficulty pills are inert (unreachable by keyboard, not just visually hidden)', () => {
  const { container } = render(
    <ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />,
  )

  fireEvent.click(screen.getByRole('radio', { name: 'Local 2P' }))

  const pillsContainer = container.querySelector('.difficulty-pills') as HTMLDivElement
  expect(pillsContainer).toHaveAttribute('inert')

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  expect(pillsContainer).not.toHaveAttribute('inert')
})

test('Enter activates a non-native radio/checkbox widget', () => {
  const onStartGame = vi.fn()
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={onStartGame} />)

  fireEvent.keyDown(screen.getByRole('radio', { name: 'Local 2P' }), { key: 'Enter' })

  expect(screen.getByRole('radio', { name: 'Local 2P' })).toHaveAttribute('aria-checked', 'true')
})

test('the segmented groups are named by their visible label and their options are plain buttons', () => {
  const { container } = render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)
  fireEvent.click(screen.getByRole('radio', { name: 'Local 2P' }))

  for (const name of ['Board size', 'Skip limit']) {
    const group = screen.getByRole('radiogroup', { name })
    expect(group).not.toHaveAttribute('aria-label')
    for (const option of within(group).getAllByRole('radio')) expect(option).toHaveAttribute('type', 'button')
  }
  expect(container.querySelector('label')).toBeNull()
})

function renderRadios(group: string) {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)
  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  // Difficulty is a plain labelled group, so it is not a second radiogroup nested inside Opponent.
  return within(screen.getByRole(group === 'Difficulty' ? 'group' : 'radiogroup', { name: group })).getAllByRole('radio')
}

describe.each(['Board size', 'Skip limit', 'Difficulty'])('%s radio options', (group) => {
  test.each([
    ['ArrowRight', 0, 1],
    ['ArrowDown', 0, 1],
    ['ArrowLeft', 1, 0],
    ['ArrowUp', 1, 0],
    ['ArrowRight', -1, 0], // wraps from the last
    ['ArrowLeft', 0, -1], // wraps from the first
  ])('%s from option %i moves the selection and focus to option %i', (key, from, to) => {
    const radios = renderRadios(group)
    const [start, end] = [radios.at(from)!, radios.at(to)!]
    fireEvent.click(start)

    fireEvent.keyDown(start, { key })

    expect(end).toHaveAttribute('aria-checked', 'true')
    expect(end).toHaveFocus()
  })

  test('have one tab stop, on the selected option', () => {
    const radios = renderRadios(group)
    const tabStops = () => radios.filter((r) => r.tabIndex === 0)

    fireEvent.click(radios[1])
    expect(tabStops()).toEqual([radios[1]])

    fireEvent.click(radios[0])
    expect(tabStops()).toEqual([radios[0]])
  })
})

describe('Opponent cards', () => {
  const renderCards = () => {
    render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)
    return [screen.getByRole('radio', { name: 'Vs Bot' }), screen.getByRole('radio', { name: 'Local 2P' })]
  }

  test('the tab stop starts on the first card and follows the selected one', () => {
    const [bot, local] = renderCards()
    expect([bot.tabIndex, local.tabIndex]).toEqual([0, -1])

    fireEvent.click(local)

    expect([bot.tabIndex, local.tabIndex]).toEqual([-1, 0])
  })

  test('the Difficulty pills sit in a labelled group, not a second radiogroup nested in Opponent, and state their own position', () => {
    const [bot] = renderCards()
    fireEvent.click(bot)

    expect(screen.queryByRole('radiogroup', { name: 'Difficulty' })).not.toBeInTheDocument()
    const pills = within(screen.getByRole('group', { name: 'Difficulty' })).getAllByRole('radio')
    expect(pills.map((p) => [p.getAttribute('aria-posinset'), p.getAttribute('aria-setsize')])).toEqual([
      ['1', '3'],
      ['2', '3'],
      ['3', '3'],
    ])
  })

  test('an arrow from the first card selects and focuses the other, and wraps back', () => {
    const [bot, local] = renderCards()

    fireEvent.keyDown(bot, { key: 'ArrowRight' })
    expect(local).toHaveAttribute('aria-checked', 'true')
    expect(local).toHaveFocus()

    fireEvent.keyDown(local, { key: 'ArrowRight' })
    expect(bot).toHaveAttribute('aria-checked', 'true')
    expect(bot).toHaveFocus()
  })
})

// jsdom skips the imported stylesheet, so tests that assert computed style inject the real file.
function injectModeSelectCss() {
  const style = document.createElement('style')
  style.textContent = readFileSync('src/screens/ModeSelectScreen.css', 'utf8')
  document.head.append(style)
  onTestFinished(() => style.remove())
}

describe('selection cue on the opponent cards', () => {
  const renderCards = () => {
    injectModeSelectCss()
    const { container } = render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)
    return [...container.querySelectorAll<HTMLElement>('.mode-card')]
  }
  const cssRules = () => [...document.styleSheets].flatMap((sheet) => [...sheet.cssRules])

  test('the selected card is marked by a filled marker and a light tint, the other by neither', () => {
    const [bot, local] = renderCards()
    const marker = (card: HTMLElement) => card.querySelector('.mode-marker')!
    const tint = 'color-mix(in srgb, var(--ink) 6%, transparent)'

    expect(marker(bot)).toHaveAttribute('aria-hidden', 'true')
    expect(marker(local)).toHaveAttribute('aria-hidden', 'true')
    fireEvent.click(local)
    expect(getComputedStyle(marker(local)).backgroundColor).toBe('var(--ink)')
    expect(getComputedStyle(local).backgroundColor).toBe(tint)
    expect(getComputedStyle(marker(bot)).backgroundColor).not.toBe('var(--ink)')
    expect(getComputedStyle(bot).backgroundColor).not.toBe(tint)
    // The hollow marker's border is 55% ink like the card's, which clears the 3:1 floor for a control boundary.
    expect(getComputedStyle(marker(bot)).borderTopColor).toBe('color-mix(in srgb, var(--ink) 55%, transparent)')
  })

  // jsdom can't evaluate :focus-visible or :has, so the keyboard-only ring is asserted on the stylesheet's selectors.
  test('the focus ring is keyboard-only: it never follows :focus-within, which a mouse click also sets', () => {
    renderCards()
    const selectors = cssRules()
      .flatMap((rule) => ((rule as CSSStyleRule).selectorText ?? '').split(',').map((selector) => selector.trim()))

    expect(selectors.some((selector) => selector.includes(':focus-within'))).toBe(false)
    expect(selectors).toContain('.mode-card:focus-visible')
    expect(selectors).toContain('.mode-card:has(.mode-card-select:focus-visible)')
  })

  // Forced-colors mode drops backgrounds and shadows but keeps borders, so the selected marker thickens its border there.
  test('the selected marker has a thicker border in forced-colors mode, where its fill is dropped', () => {
    renderCards()
    const forced = cssRules()
      .filter((rule) => rule instanceof CSSMediaRule && rule.conditionText.includes('forced-colors: active'))
      .flatMap((rule) => [...(rule as CSSMediaRule).cssRules] as CSSStyleRule[])
    const marker = forced.find((rule) => rule.selectorText === '.mode-card.selected .mode-marker')

    expect(marker?.style.borderWidth).toBe('5px')
  })
})

// Series play needs the round-transition screen, so the Games picker stays hidden until it lands.
test('hides the Games picker while series play is not implemented', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)
  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))

  expect(screen.getByRole('radiogroup', { name: 'Skip limit' })).toBeInTheDocument()
  expect(screen.queryByRole('radiogroup', { name: 'Games' })).not.toBeInTheDocument()
  expect(screen.queryByRole('radio', { name: 'Best of 3' })).not.toBeInTheDocument()
})

test('does not send seriesLength even when a stored setting has one', () => {
  localStorage.setItem('rectangles.modeSelectSettings:v1', JSON.stringify({ seriesLength: 3 }))
  const onStartGame = vi.fn()
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={onStartGame} />)

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))

  expect(onStartGame.mock.calls[0][0]).not.toHaveProperty('seriesLength')
})

test('persists settings to localStorage on Start Game and pre-fills them on the next mount', () => {
  const { unmount } = render(
    <ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />,
  )
  fireEvent.click(screen.getByRole('radio', { name: 'Local 2P' }))
  fireEvent.click(screen.getByRole('radio', { name: '23×23' }))
  fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))
  unmount()

  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)

  expect(screen.getByRole('radio', { name: 'Local 2P' })).toHaveAttribute('aria-checked', 'true')
  expect(screen.getByRole('radio', { name: '23×23' })).toHaveAttribute('aria-checked', 'true')
})

test('while isConnecting, Start Game is disabled and reads Connecting…', () => {
  render(<ModeSelectScreen isConnecting connectFailed={false} onStartGame={vi.fn()} />)

  expect(screen.getByRole('button', { name: 'Connecting…' })).toBeDisabled()
})

test('while connectFailed, shows an inline retry message and Start Game stays enabled', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed onStartGame={vi.fn()} />)
  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))

  expect(
    screen.getByText('Couldn’t connect — your settings are unchanged, try again'),
  ).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Start Game' })).not.toBeDisabled()
})

test('Reset to Defaults opens a confirm dialog', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  fireEvent.click(screen.getByRole('button', { name: 'Reset to Defaults' }))

  expect(screen.getByRole('heading', { name: 'Reset to Defaults?' })).toBeInTheDocument()
})

test('confirming the reset dialog restores match setup but keeps the chosen opponent', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  fireEvent.click(screen.getByRole('radio', { name: '23×23' }))
  fireEvent.click(screen.getByRole('radio', { name: 'Blocking' }))

  fireEvent.click(screen.getByRole('button', { name: 'Reset to Defaults' }))
  fireEvent.click(screen.getByRole('button', { name: 'Reset' }))

  expect(screen.queryByRole('heading', { name: 'Reset to Defaults?' })).not.toBeInTheDocument()
  expect(screen.getByRole('radio', { name: 'Vs Bot' })).toHaveAttribute('aria-checked', 'true')
  expect(screen.getByRole('radio', { name: '19×19' })).toHaveAttribute('aria-checked', 'true')
  expect(screen.getByRole('radio', { name: 'Greedy' })).toHaveAttribute('aria-checked', 'true')
})

test('cancelling the reset dialog leaves settings untouched', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  fireEvent.click(screen.getByRole('radio', { name: '23×23' }))

  fireEvent.click(screen.getByRole('button', { name: 'Reset to Defaults' }))
  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

  expect(screen.queryByRole('heading', { name: 'Reset to Defaults?' })).not.toBeInTheDocument()
  expect(screen.getByRole('radio', { name: '23×23' })).toHaveAttribute('aria-checked', 'true')
})

describe('changed-from-defaults cue', () => {
  const renderScreen = () => render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)
  const pick = (name: string) => fireEvent.click(screen.getByRole('radio', { name }))
  const cue = () => screen.queryByText(/changed from defaults/)

  test('shows nothing while every setting is at its default', () => {
    renderScreen()
    pick('Local 2P')

    expect(cue()).not.toBeInTheDocument()
  })

  test('counts a changed board size, then a changed skip limit', () => {
    renderScreen()
    pick('Local 2P')

    pick('23×23')
    expect(cue()).toHaveTextContent('1 changed from defaults')

    pick('3')
    expect(cue()).toHaveTextContent('2 changed from defaults')
  })

  test('counts each house rule that is off, and drops the count when it is turned back on', () => {
    renderScreen()
    pick('Local 2P')

    fireEvent.click(screen.getByRole('checkbox', { name: 'Obstacles' }))
    expect(cue()).toHaveTextContent('1 changed from defaults')

    fireEvent.click(screen.getByRole('checkbox', { name: 'Reroll' }))
    expect(cue()).toHaveTextContent('2 changed from defaults')

    fireEvent.click(screen.getByRole('checkbox', { name: 'Obstacles' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Reroll' }))
    expect(cue()).not.toBeInTheDocument()
  })

  test('counts a non-default bot difficulty only while Vs Bot is chosen', () => {
    renderScreen()
    pick('Vs Bot')

    pick('Blocking')
    expect(cue()).toHaveTextContent('1 changed from defaults')

    pick('Local 2P')
    expect(cue()).not.toBeInTheDocument()
  })

  test('does not count the opponent or a saved series length, which the player cannot see', () => {
    localStorage.setItem('rectangles.modeSelectSettings:v1', JSON.stringify({ opponent: 'local2p', seriesLength: 3 }))
    renderScreen()
    expect(cue()).not.toBeInTheDocument()

    pick('Vs Bot')
    expect(cue()).not.toBeInTheDocument()
  })

  test('shows the cue straight away for saved settings that differ from the defaults', () => {
    localStorage.setItem(
      'rectangles.modeSelectSettings:v1',
      JSON.stringify({ opponent: 'local2p', boardSize: 27, houseRules: { prizeEnabled: false } }),
    )
    renderScreen()

    expect(cue()).toHaveTextContent('2 changed from defaults')
  })

  test('Reset restores every counted kind', () => {
    renderScreen()
    pick('Vs Bot')
    pick('Blocking')
    pick('27×27')
    pick('3')
    fireEvent.click(screen.getByRole('checkbox', { name: 'Walls' }))
    expect(cue()).toHaveTextContent('4 changed from defaults')

    fireEvent.click(screen.getByRole('button', { name: 'Reset to Defaults' }))
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Reset' }))
    expect(cue()).not.toBeInTheDocument()
  })

  test('Reset to Defaults is described by the cue while there is one', () => {
    renderScreen()
    pick('Local 2P')
    expect(screen.getByRole('button', { name: 'Reset to Defaults' })).toHaveAccessibleDescription('')

    pick('23×23')
    expect(screen.getByRole('button', { name: 'Reset to Defaults' })).toHaveAccessibleDescription('1 changed from defaults')
  })
})
