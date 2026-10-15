# frontend

React/TypeScript frontend for Rectangles. Talks to the FastAPI/WebSocket server in `../rectangles/server/`.

```
npm install
npm run dev     # dev server
npm run build   # tsc -b && vite build
npm test        # vitest run
npm run coverage  # vitest run --coverage
```

The server serves the built bundle: run `npm run build`, then `uv run python -m rectangles.server.app` from the repo root and open `http://127.0.0.1:8765/`. During development `npm run dev` forwards `/ws` to the server on port 8765.
