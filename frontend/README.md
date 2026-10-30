# frontend

React/TypeScript frontend for Rectangles. Talks to the Scala WebSocket server in `../server-scala/server/`.

```
npm ci
npm run dev     # dev server
npm run build   # tsc -b && vite build
npm test        # vitest run; the integration tests start the staged server (`sbt server/stage` in ../server-scala first)
npm run coverage  # vitest run --coverage
```

The server serves the built bundle: run `npm run build`, then `server-scala/target/stage/bin/rectangles-server` from the repo root and open `http://127.0.0.1:8765/`. During development `npm run dev` forwards `/ws` to the server on port 8765 (or `RECTANGLES_SERVER_PORT`, when set).
