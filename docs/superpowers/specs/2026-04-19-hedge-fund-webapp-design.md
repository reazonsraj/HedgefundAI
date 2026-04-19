# AI Hedge Fund Web Application — Design Spec

## Overview

A standalone web application for the AI Hedge Fund project. Provides a clean dashboard UI (top navigation, dark theme) for browsing assets across stocks/ETFs/forex, building portfolios, running multi-agent AI analysis with streaming results, and reviewing historical runs. Single-user, no auth, SQLite persistence.

## Stack

- **Frontend**: React 18 + Vite + TypeScript + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI with SSE streaming
- **Database**: SQLite via SQLAlchemy
- **Location**: `webapp/` directory at project root
  - `webapp/frontend/` — React app
  - `webapp/backend/` — FastAPI server

The backend imports directly from `src/` (run_hedge_fund, agent registry, model config, data APIs with yfinance fallback). No duplication of existing logic.

## Layout

Top navigation bar with 5 tabs: Dashboard, Assets, Portfolio, History, Settings.

Dark theme (#0a0a0a background, #111 cards, #222 borders). Accent color: indigo (#6366f1). Signal colors: green (#22c55e) for bullish/buy, red (#ef4444) for bearish/short, yellow (#eab308) for neutral/hold.

## Pages

### Dashboard

Summary cards across the top:
- Total portfolio value
- Active positions count
- Last run timestamp
- Quick signal summary (e.g. "3 Buy / 2 Short")

Below cards: most recent analysis run results (portfolio decisions table + agent signal breakdown). "Run Analysis" button in the top nav launches analysis on the current portfolio.

### Assets

Three category tabs: **Stocks**, **ETFs/Indices**, **Forex**.

Each tab shows a grid of preset popular tickers:
- Stocks: AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, JPM, V, UNH, BRK.B, JNJ, MA, PG, HD (and more)
- ETFs/Indices: SPY, QQQ, IWM, DIA, VTI, VOO, ARKK, XLF, XLE, XLK
- Forex: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURGBP, EURJPY, GBPJPY

Each ticker shows as a card with name and "+" button to add to portfolio. Search bar at top filters results and allows adding any custom ticker.

No external API calls on this page — search is against the local preset list. Custom tickers are accepted without validation (the analysis run will handle unknown tickers gracefully via yfinance fallback).

### Portfolio

Shows all tickers added from the Assets page, grouped by category. Each ticker has a remove button.

Configuration panel:
- Initial cash (default $100,000)
- Margin requirement (default 0%)
- Date range (start/end, default: 3 months back to today)
- Model selector (dropdown from api_models.json — grouped by provider)
- Agent selector (checkboxes for all 18+ analysts, with "Select All" toggle)

"Run Analysis" button at bottom. Disabled if no tickers selected.

### Analysis Run (streaming view)

When "Run Analysis" is clicked:
1. Portfolio page transitions to a results view
2. Top: progress bar showing overall completion
3. Summary cards update in real-time (signals count)
4. Agent cards grid below — each card appears as its agent completes:
   - Agent name and avatar/icon
   - Per-ticker signal: bullish (green), bearish (red), neutral (yellow)
   - Confidence percentage
   - Expandable reasoning text
5. Risk Manager card appears after all analysts
6. Final Portfolio Decision card appears last with the full decisions table:
   - Ticker, Action (BUY/SHORT/HOLD), Quantity, Confidence, Reasoning

### History

Chronological list of past analysis runs. Each row shows:
- Timestamp
- Tickers analyzed
- Model used
- Summary (e.g. "3 Buy, 1 Short, 1 Hold")
- Status (completed/failed)

Click a row to expand full results (same view as the streaming results page, but static).

### Settings

- API key inputs for each provider (Anthropic, OpenAI, DeepSeek, Groq, Google, xAI, etc.)
- Keys are saved to the project's `.env` file
- Show/hide toggle for each key field
- "Test Connection" button per provider (optional, stretch goal)

## Database Schema

### portfolios
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| name | TEXT | User-given name, default "My Portfolio" |
| tickers | JSON | List of ticker strings |
| initial_cash | REAL | Default 100000.0 |
| margin_requirement | REAL | Default 0.0 |
| created_at | DATETIME | UTC |
| updated_at | DATETIME | UTC |

### analysis_runs
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| portfolio_id | INTEGER FK | References portfolios.id |
| model_name | TEXT | e.g. "claude-sonnet-4-6" |
| model_provider | TEXT | e.g. "Anthropic" |
| selected_analysts | JSON | List of analyst IDs |
| tickers | JSON | Snapshot of tickers at run time |
| start_date | TEXT | YYYY-MM-DD |
| end_date | TEXT | YYYY-MM-DD |
| status | TEXT | pending / running / completed / failed |
| decisions | JSON | Final portfolio decisions (null until complete) |
| created_at | DATETIME | UTC |
| completed_at | DATETIME | Null until done |

### analysis_results
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| run_id | INTEGER FK | References analysis_runs.id |
| agent_name | TEXT | e.g. "warren_buffett_agent" |
| ticker | TEXT | e.g. "AAPL" |
| signal | TEXT | bullish / bearish / neutral |
| confidence | REAL | 0-100 |
| reasoning | TEXT | Full reasoning text |
| raw_data | JSON | Complete agent output |
| created_at | DATETIME | UTC |

## API Endpoints

### Portfolios
- `GET /api/portfolios` — list all portfolios
- `POST /api/portfolios` — create portfolio `{name, tickers, initial_cash, margin_requirement}`
- `GET /api/portfolios/:id` — get portfolio by ID
- `PUT /api/portfolios/:id` — update portfolio
- `DELETE /api/portfolios/:id` — delete portfolio

### Analysis
- `POST /api/analysis/run` — start analysis run `{portfolio_id, model_name, model_provider, selected_analysts, start_date, end_date}`. Returns `{run_id}`.
- `GET /api/analysis/stream/:run_id` — SSE stream of agent results. Events: `agent_start`, `agent_complete` (with signal data), `run_complete` (with final decisions), `run_error`.
- `GET /api/analysis/history` — list all past runs (newest first)
- `GET /api/analysis/:run_id` — get full run with all results

### Assets
- `GET /api/assets/presets` — returns preset tickers grouped by category (stocks, etfs, forex). No external API calls.
- `GET /api/assets/search?q=AAPL` — search presets by query string. Local only.

### Config
- `GET /api/config/models` — returns available models from api_models.json
- `GET /api/config/api-keys` — returns which API keys are set (not the values)
- `PUT /api/config/api-keys` — save API keys to .env file `{provider: key}`

## Streaming Architecture

1. `POST /api/analysis/run` creates a run record (status: pending), then spawns a background thread.
2. Background thread:
   - Updates run status to "running"
   - Registers a handler on `AgentProgress` to capture status updates
   - Calls `run_hedge_fund()` with the configured parameters
   - As each agent completes, saves result to `analysis_results` table and pushes SSE event
   - On completion, saves final decisions to `analysis_runs.decisions`, sets status to "completed"
   - On error, sets status to "failed" with error info
3. `GET /api/analysis/stream/:run_id` connects to SSE. The endpoint reads results from the database and streams new ones as they arrive via an asyncio Queue tied to the progress handler.
4. Frontend `EventSource` receives events and renders agent cards progressively.

## Error Handling

- **Missing API key**: Settings page shows which keys are configured. Analysis run checks for required key before starting and returns clear error.
- **Network failure during analysis**: Agent errors are caught individually (existing behavior — agents default to neutral). Run still completes. If the entire run crashes, status is set to "failed".
- **Unknown ticker**: yfinance fallback handles it. If yfinance also fails, agents get empty data and return neutral signals.
- **Concurrent runs**: Only one analysis can run at a time. UI disables "Run Analysis" while a run is in progress.

## Frontend Structure

```
webapp/frontend/src/
  components/
    layout/
      TopNav.tsx          — navigation bar with tabs
      Layout.tsx          — page wrapper with nav
    dashboard/
      SummaryCards.tsx     — stat cards row
      RecentRun.tsx       — latest run results
    assets/
      AssetTabs.tsx       — Stocks/ETFs/Forex tabs
      AssetCard.tsx       — individual ticker card with add button
      AssetSearch.tsx     — search input
    portfolio/
      TickerList.tsx      — selected tickers with remove
      RunConfig.tsx       — cash, margin, model, agents config
    analysis/
      AgentCard.tsx       — single agent result card
      AgentGrid.tsx       — grid of streaming agent cards
      DecisionTable.tsx   — final portfolio decisions
      ProgressBar.tsx     — overall run progress
    history/
      RunList.tsx         — list of past runs
      RunDetail.tsx       — expanded run view
    settings/
      ApiKeyForm.tsx      — API key inputs
  pages/
    DashboardPage.tsx
    AssetsPage.tsx
    PortfolioPage.tsx
    HistoryPage.tsx
    SettingsPage.tsx
  hooks/
    useAnalysisStream.ts  — SSE hook for streaming results
    usePortfolio.ts       — portfolio state management
  services/
    api.ts               — fetch wrapper for all API calls
  types/
    index.ts             — TypeScript types
  App.tsx                — router + layout
  main.tsx               — entry point
```

## Key Constraints

- External APIs (Financial Datasets, yfinance, LLM providers) are ONLY called when the user clicks "Run Analysis". All other pages use local data.
- Single concurrent run — no parallel analysis runs.
- SQLite database file stored at `webapp/backend/hedge_fund.db`.
- Frontend dev server on port 5173, backend on port 8000.
