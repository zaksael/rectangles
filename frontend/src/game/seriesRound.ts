import type { GameWireState, SeriesWireState } from './gameTypes'

// The round being played, or the one just finished once its game is over.
export const seriesRound = (game: GameWireState, series: SeriesWireState) => (game.turn.turnState === 'gameOver' ? series.gamesPlayed : series.gamesPlayed + 1)
