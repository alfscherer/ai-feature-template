# Frontend

One screen: a textarea, an optional context field, an analyze button, and the structured
result. That's the whole feature -- the point of this repository is the backend architecture,
and the UI exists to demonstrate the API is actually usable, not to show off frontend work.

## Choices made to keep it that small

- **Plain `fetch`, no data-fetching library.** One request, triggered by one button, with
  loading/error/result as three `useState` calls (`src/App.tsx`). React Query or SWR solve
  problems (caching, refetching, request deduplication) this screen doesn't have.
- **Hand-written types, not codegen.** `src/types.ts` mirrors `app/api/schemas.py` and
  `app/llm/schemas/feedback.py` by hand. FastAPI already exposes an OpenAPI schema at
  `/openapi.json` that a tool like `openapi-typescript` could generate these from -- worth
  doing the moment there's more than one screen or the schema starts changing often enough
  that hand-syncing becomes a real source of bugs. For one screen, the codegen step and its
  dependency would cost more than it saves.
- **No CSS framework.** `src/index.css` is hand-written, plain CSS. Tailwind or a component
  library are reasonable choices for a real product UI; here they'd be a dependency and a
  build-time cost purely to render one form and one result card.
- **No client-side router, no global state.** There's one screen. Introducing either would be
  solving a problem this repository doesn't have yet.

## Running it

`npm run dev` starts Vite on port 5173 and proxies `/api/*` to `http://localhost:8000`
(`vite.config.ts`), so the browser talks to one origin and never has to deal with CORS, and the
backend never needs a CORS policy for local development. In front of a real deployment, the
frontend's build output (`npm run build` -> `dist/`) would be served from behind the same
reverse proxy or CDN as the API, for the same reason.

## A known, accepted dependency risk

`npm audit` flags the pinned Vite 5.x line for a few dev-server-only advisories (a path-traversal
/ `server.fs.deny` bypass, fixed only in Vite 6.4.3+). They affect `vite dev`/`vite preview`
serving files to a browser that can reach the dev server's port -- not the production build
output, and not anything reachable through the API. Vite 6+ carries the fix but wasn't used here
to avoid pinning to a config API this repository hasn't verified against; on a network where the
dev server's port might be reached by an untrusted client, don't run `npm run dev` exposed
beyond localhost. This tradeoff -- and it is a tradeoff, not a non-issue -- would be revisited
before this stopped being a portfolio project.
