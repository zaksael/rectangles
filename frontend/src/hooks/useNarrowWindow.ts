import { useEffect, useState } from 'react'

// Playing and Replay are laid out for a window at least this wide (the board plus a 360px rail).
export const MIN_WINDOW_WIDTH = 1320

export function useNarrowWindow(): { narrow: boolean; width: number } {
  const [width, setWidth] = useState(() => window.innerWidth)
  useEffect(() => {
    const onResize = () => setWidth(window.innerWidth)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  return { narrow: width < MIN_WINDOW_WIDTH, width }
}
