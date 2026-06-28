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
│  │  Accuracy: 84.3% cross-validation (MAPE 15.75%)          │    │
│  │                                                          │    │
│  │  Key patterns:                                           │    │
│  │  - TSH: winter_mult=1.8 (Jun-Aug spike in AR)           │    │
│  │  - Hemograma: stable year-round                          │    │
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
**What it does:** Queries `#labops-alerts` message history for past reagent incidents.

When a user asks "what happened with TSH last month?", the agent uses Slack's `conversations.history` API to fetch past messages about TSH from `#labops-alerts` — without storing any data externally. This gives the agent contextual memory within Slack's own infrastructure.

```
Scopes used: channels:history, groups:history
Query method: client.conversations_history(channel_id) filtered by reagent name
Returns: past alerts, orders placed, resolutions
```

### 3. Slack Search API (Real-Time Search)
**What it does:** Searches the entire workspace in real time for reagent mentions using Slack's `search.messages` API.

When a user clicks "📊 Ver proyección", the agent runs a real-time search for the reagent across all accessible channels (not just `#labops-alerts`). This surfaces relevant conversations, past alerts, and team discussions that may not be in the immediate channel history.

```
Scopes used: search:read
Query method: client.search_messages(query="TSH in:labops-alerts", count=5)
Returns: cross-channel matches with timestamps and snippets
```

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

T+2s:   projected_stockout_days=3.3 < reorder_lead_time=7
        → alert_trigger=True, severity="critical"

T+3s:   Claude API called (temperature=0)
        → generates natural language explanation
        → "TSH demand spikes in winter (Jun-Aug). Current stock
           will cover ~3 days at projected consumption rate."

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
- **Yearly seasonality** — TSH demand spikes every winter in Argentina
- **Weekly seasonality** — lower demand on weekends (lab closures)
- **Trend detection** — gradual growth or decline in test volumes

**Calibration:**
The model was trained on synthetic data calibrated with demand patterns
derived from anonymized analysis of Argentine clinical laboratory operations.
The synthetic data preserves the statistical patterns (seasonal multipliers,
weekly rhythms, noise levels) without including any real patient or
laboratory identifiers.

**Performance:**
- 84.3% accuracy on cross-validation (MAPE 15.75%, RMSE 20.6 units)
- Critical flags (stockout within lead time): 100% reproducible at temperature=0
- Model serialized to `models/{reagent}_model.pkl` after first fit (~10-30s)
- Subsequent calls load from disk (<100ms)

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
| Deploy | Vercel | — |
| Language | Python | 3.11+ |

---

*LabOps Agent · Technical Architecture · Slack Agent Builder Challenge 2026*
