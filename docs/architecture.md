# LabOps Agent — Technical Architecture
> For judges: this document describes the full technical architecture,
> data flow, and component interactions.

---

## System Overview

LabOps Agent is a Slack-native AI agent that predicts reagent stockouts
in clinical laboratories before they happen. It runs on Slack platform
APIs (Channel History API, Canvas API) plus an Anthropic MCP Server and
Claude API summarization, orchestrated via a FastAPI backend with Prophet
demand forecasting.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        SLACK WORKSPACE                            │
│                                                                   │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │ #labops-alerts  │  │ Canvas Inventario │  │   App Home     │  │
│  │                 │  │                  │  │                │  │
│  │ 🔴 TSH Alert   │  │ Stock: 680 units  │  │ Agent status   │  │
│  │ [📊][🛒][👤]   │  │ Order: pending    │  │ Last check     │  │
│  └────────┬────────┘  └────────┬─────────┘  └────────────────┘  │
└───────────┼──────────────────────────────────────────────────────┘
            │ Socket Mode (Bolt Python)
            │ Events: button clicks, modal submissions, mentions
            ▼
┌──────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                               │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    MCP SERVER                             │    │
│  │                                                          │    │
│  │  get_inventory(reagent_name?)                            │    │
│  │  → Returns current stock + is_demo flag                  │    │
│  │                                                          │    │
│  │  get_forecast(reagent_name, days=30)                     │    │
│  │  → Returns Prophet daily demand forecast                  │    │
│  │                                                          │    │
│  │  create_order(reagent_name, quantity, supplier)          │    │
│  │  → Creates order record in Supabase                      │    │
│  │                                                          │    │
│  │  update_canvas(channel_id, reagent_data)                 │    │
│  │  → Prepares Block Kit Canvas payload                     │    │
│  └─────────────────────┬────────────────────────────────────┘    │
│                        │                                          │
│  ┌─────────────────────▼────────────────────────────────────┐    │
│  │                PREDICTION ENGINE                          │    │
│  │                                                          │    │
│  │  Algorithm: Prophet (Facebook/Meta)                      │    │
│  │  Training: synthetic data calibrated with real patterns  │    │
│  │  Source: anonymized demand analysis (Argentina)          │    │
│  │  Accuracy: rolling-origin CV MAPE ~8-11%, 80% CI         │    │
│  │            coverage ~79-82% (well calibrated)            │    │
│  │                                                          │    │
│  │  Key patterns:                                           │    │
│  │  - TSH: peak_mult=2.5 (Mar-May autumn peak, 414K B2B)   │    │
│  │  - Hemograma: moderate variation (CV=0.359), Jan-May    │    │
│  │  - Ionograma: stable year-round                          │    │
│  │                                                          │    │
│  │  calculate_stockout_projection():                        │    │
│  │  → Returns projected_stockout_days                       │    │
│  │  → alert_trigger = days < reorder_lead_time             │    │
│  │  → Pickle serialized: models/{reagent}_model.pkl        │    │
│  └─────────────────────┬────────────────────────────────────┘    │
└───────────────────────┼──────────────────────────────────────────┘
                        │
            ┌───────────┴──────────┐
            ▼                      ▼
┌───────────────────┐  ┌──────────────────────────────────────────┐
│    SUPABASE       │  │              CLAUDE API                   │
│                   │  │                                          │
│  inventory        │  │  Model: claude-sonnet-4-6                │
│  demand_history   │  │  Temperature: 0                          │
│  orders           │  │  Use: natural language explanations      │
│  alerts_log       │  │  "TSH is at risk because demand spikes   │
│                   │  │   every winter in Argentina..."          │
│  All rows:        │  │                                          │
│  is_demo=true ✅  │  └──────────────────────────────────────────┘
└───────────────────┘
```

---

## Slack Technologies — Detailed Usage

### 1. MCP Server
**What it does:** Exposes 4 lab operation tools to the Slack agent.

The MCP Server is the bridge between the Slack agent and the lab data layer. When the agent needs to check inventory or create an order, it calls these tools via the MCP protocol rather than making direct database calls.

```
Tools exposed:
- get_inventory     → reads from Supabase inventory table
- get_forecast      → runs Prophet model for demand projection
- create_order      → writes to Supabase orders table
- update_canvas     → generates Block Kit Canvas payload
```

**Why MCP:** Keeps the agent's data access declarative and auditable. Each tool call is logged and the agent can reason about which tool to use for which task.

### 2. Channel History API
**What it does:** Retrieves thread-scoped message history for contextual alert discussion.

When a user clicks "📊 Ver proyección" on an alert, the agent uses Slack's `conversations_replies` API to fetch prior messages in the current thread about the target reagent — without storing any data externally. This gives the agent contextual memory within Slack's own infrastructure.

```
Scopes used: channels:history, groups:history
Query method: client.conversations_replies(channel=channel, ts=thread_ts, limit=10) filtered by reagent name + alert keywords
Returns: past alerts, orders placed, resolutions from the current thread
```

### 3. Thread History via Channel History API — *implemented*
> The three technologies that work out-of-the-box with the bot token are the
> **MCP Server**, the **Channel History API** (`conversations_replies`), and
> **Claude API summarization**.

**What it does:** Retrieves recent replies from the current alert thread to surface prior context for the specific stockout discussion.

When a user clicks "📊 Ver proyección", the agent calls `conversations_replies` on the current thread, filters messages mentioning the target reagent and containing alert keywords (🔴 CRÍTICO, 🟡 ADVERTENCIA, 📊 Pronóstico), and returns up to 3 matching messages as thread history.

```
Scopes used: channels:history, groups:history (bot token xoxb-)
Query method: client.conversations_replies(channel=channel, ts=thread_ts, limit=10)
Filter: reagent name match + alert keyword match
Returns: thread-scoped prior alerts with timestamps and snippets
```

> ⚠️ **Design decision:** `search.messages` (Slack Search API) was evaluated but
> replaced by `conversations_replies` because `search.messages` requires a **user
> token** (`xoxp-`) that is not available in the standard bot-token deployment.
> The bot token (`search:read` bot scope) receives empty results. Thread-scoped
> history provides the relevant context without requiring a user token.

### 4. Claude API Summarization
**What it does:** Uses Claude API to summarize `#labops-alerts` channel history on demand.

When a lab supervisor asks for context about a reagent's recent history, the agent calls the Claude API to generate a natural language summary of the relevant thread or channel history. This provides a human-readable summary without the agent having to parse raw message history.

```
Use case: "Resume los últimos incidentes con TSH"
Output: Claude-generated summary of recent TSH alerts
```

---

## Data Flow — Stockout Alert

```
T+0:    Scheduler runs every hour
        → calls calculate_stockout_projection() for each reagent

T+1s:   Prophet model loaded from models/TSH_model.pkl
        → predicts daily demand for next 90 days
        → cumulative demand vs current_stock = stockout_date

T+2s:   projected_stockout_days=4 < reorder_lead_time=7
        → alert_trigger=True, severity="critical"
        (680 units ÷ ~197 u/day mean → cumulative demand
         crosses stock on day 4)

T+3s:   Claude API called (temperature=0)
        → generates natural language explanation
        → "TSH demand peaks in autumn (Mar-May). Current stock
           will cover ~4 days at projected consumption rate."

T+4s:   Bolt Python sends Block Kit message to #labops-alerts
        → 🔴 CRITICAL badge
        → 3 interactive buttons
        → 🔬 DEMO badge

T+5s:   Message visible to lab staff in Slack
        → staff clicks "🛒 Ordenar reactivo"
        → modal opens with pre-filled reagent + suggested quantity

T+6s:   Staff confirms order
        → create_order() writes to Supabase
        → Canvas updates with new order status
        → Thread confirmation message
```

---

## Prediction Model

**Algorithm:** Facebook Prophet

Prophet was chosen for its native handling of:
- **Yearly seasonality** — TSH demand peaks every autumn (Mar-May) in Argentina
- **Weekly seasonality** — lower demand on weekends (lab closures)
- **Trend detection** — gradual growth or decline in test volumes

**Calibration:**
The model was trained on synthetic data calibrated with demand patterns
derived from anonymized analysis of Argentine clinical laboratory operations.
The synthetic data preserves the statistical patterns (seasonal multipliers,
weekly rhythms, noise levels) without including any real patient or
laboratory identifiers.

**Performance — rolling-origin cross-validation (headline metric):**

Measured with `prophet.diagnostics.cross_validation` on the daily model that
actually serves forecasts (initial=240d, period=30d, horizon=14d → 4 folds,
56 predictions per reagent). Reproduce with `python scripts/cross_validation.py`
(writes `notebooks/cv_metrics.json`).

| Reagent | MAPE | MAE | RMSE | 80% CI coverage |
|---------|------|-----|------|-----------------|
| TSH | 11.34% | 12.09 | 16.21 | 78.6% |
| Hemograma | 8.39% | 14.14 | 17.38 | 80.4% |
| Ionograma | 8.44% | 12.77 | 15.71 | 80.4% |
| Glucosa | 8.45% | 10.71 | 13.16 | 82.1% |
| Urea | 8.52% | 6.44 | 7.88 | 82.1% |
| Creatinina | 8.66% | 6.89 | 8.46 | 78.6% |

Out-of-sample MAPE lands in the ~8–11% range, and coverage of the 80% interval
is ~79–82% — i.e. the uncertainty bands are well calibrated (close to the
nominal 80%), not over-confident.

**Caveats (honesty):**
- The earlier "84.3% / MAPE 15.75% cross-validation" figure was *self-consistency
  on the model's own training data* — not a real test. It has been removed as a
  headline claim.
- A monthly hold-out backtest (`notebooks/holdout_metrics.json`) exists, but the
  Hemograma/Ionograma figures there rested on a **single test point each** and are
  statistically meaningless — they are **not** cited. The TSH monthly figure
  (3.29%, 7 points) is illustrative only; the rolling-origin CV above is the
  metric to cite.
- Critical flags (stockout within lead time): 100% reproducible at temperature=0.
- Model serialized to `models/{reagent}_model.pkl` after first fit (~10-30s);
  subsequent calls load from disk (<100ms).

---

## Security & Privacy

- **No PHI:** Only operational data (reagent names, quantities, dates)
- **DEMO badge:** Visible on all synthetic data in Slack messages
- **Supabase secret key:** Backend uses privileged access (not anon key)
- **RLS disabled:** Intentional for hackathon (no real user data)
- **No real patient data** in any file in this repository

---

## Stack

| Component | Technology | Version |
|---|---|---|
| Slack SDK | Bolt Python | 1.18+ |
| Backend | FastAPI | 0.111+ |
| Prediction | Prophet | 1.1.5 |
| Database | Supabase (PostgreSQL) | — |
| LLM | Claude API (claude-sonnet-4-6) | — |
| Deploy | Render / Railway / Fly (persistent host) — see `render.yaml` | Socket Mode needs a long-lived process; **not** Vercel serverless |
| Language | Python | 3.11+ |

---

*LabOps Agent · Technical Architecture · Slack Agent Builder Challenge 2026*
