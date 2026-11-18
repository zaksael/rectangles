import { render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { SurrenderConfirmDialog } from './SurrenderConfirmDialog'

test('a negative score shows a true minus sign', () => {
  render(
    <SurrenderConfirmDialog playerName="You" opponentName="Bot" scores={[{ name: 'You', score: -5 }]} isSeries={false} onCancel={vi.fn()} onConfirm={vi.fn()} />,
  )
  expect(screen.getByRole('dialog')).toHaveTextContent('−5')
})
