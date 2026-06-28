# LabOps Agent 🔬

> **Slack Agent for Good** — Slack Agent Builder Challenge 2026 (Salesforce/Devpost)

**Predict. Alert. Act. All from Slack.**

LabOps Agent is a Slack-native AI agent that predicts reagent stockouts in clinical laboratories **before they happen**, based on historical demand patterns by test type — and enables lab staff to act directly from Slack without switching to external LIMS systems.

---

## The Problem

Clinical laboratories run on reagents. When a critical reagent runs out mid-operation, testing stops. Current solutions (Quartzy, Scispot) only send passive threshold alerts **after** stock is already low. No product today predicts stockouts based on test-type demand patterns.

**Example:** TSH demand spikes every winter in Argentina (Jun–Aug). A lab with 680 units at 205 units/day will run out in 3.3 days. Without prediction, they find out when the analyzer throws an error.

---

## What LabOps Agent Does

1. **Predicts** stockouts using Prophet, calibrated on 414,289 real B2B derivation records from Argentine clinical labs
2. **Alerts** lab staff in `#labops-alerts` with interactive Block Kit messages — before the stockout happens
3. **Acts** — staff orders reagents, assigns tasks, and updates inventory without leaving Slack

---

## Slack Technologies Used (All Three)

| Technology | How It's Used |
|---|---|
| **MCP Server** | Exposes 4 lab tools: `get_inventory`, `get_forecast`, `create_order`, `update_canvas` |
| **Real-Time Search API** | Searches workspace messages and canvases for reagent incident history |
| **Slack AI** | Summarizes `#labops-alerts` channel history when querying past incidents |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  SLACK WORKSPACE                     │
│   #labops-alerts  │  Canvas Inventario  │  App Home  │
└──────────────────┬──────────────────────────────────┘
                   │ Bolt Python (Socket Mode)
┌──────────────────▼──────────────────────────────────┐
│                FASTAPI BACKEND                       │
│  ┌─────────────────┐   ┌──────────────────────────┐ │
│  │   MCP SERVER    │   │   PREDICTION ENGINE      │ │
│  │ get_inventory   │   │   Prophet + seasonality  │ │
│  │ get_forecast    │   │   calibrated: 414K rows  │ │
│  │ create_order    │   │   87% cross-val accuracy │ │
│  │ update_canvas   │   └──────────────────────────┘ │
│  └─────────────────┘                                 │
└─────────────────────────────────┬───────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────┐
│                    SUPABASE                          │
│  inventory │ demand_history │ orders │ alerts_log    │
└─────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────┐
│                  CLAUDE API                          │
│  Natural language explanations of predictions        │
└─────────────────────────────────────────────────────┘
```

---

## Demo Flow (3 minutes)

**0:00–0:45** — Agent detects TSH will run out in ~4 days (demand forecast exceeds stock)

**0:45–1:30** — Alert fires in `#labops-alerts` with Block Kit buttons:
- 📊 Ver proyección
- 🛒 Ordenar reactivo
- 👤 Asignar al equipo

**1:30–2:15** — User clicks "Ordenar reactivo" → modal opens → one click confirms → Canvas auto-updates

**2:15–3:00** — Agent explains WHY TSH is at risk (seasonal demand pattern) → Slack AI summarizes past incidents

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- Supabase account
- Slack Developer Sandbox (via [Slack Developer Program](https://api.slack.com/developer-program))
- Anthropic API key

### 1. Clone and install

```bash
git clone https://github.com/Marianooss/labops-agent
cd labops-agent
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in your keys:
# SUPABASE_URL, SUPABASE_KEY
# SLACK_BOT_TOKEN, SLACK_APP_TOKEN
# ANTHROPIC_API_KEY
# LABOPS_ALERTS_CHANNEL=#labops-alerts
```

### 3. Set up Supabase

```bash
# Run in Supabase SQL Editor:
# 1. data/create_tables.sql
# 2. data/seed_data.sql
```

### 4. Create Slack App

- Go to [api.slack.com/apps](https://api.slack.com/apps) → Create New App
- Enable Socket Mode
- Add scopes: `chat:write`, `channels:read`, `groups:read`, `im:write`, `users:read` 
- Install to your Developer Sandbox workspace

### 5. Run

```bash
# Terminal 1: FastAPI backend
uvicorn backend.main:app --reload

# Terminal 2: Slack agent (Socket Mode)
python -m backend.slack_client

# Test alert trigger:
curl "http://localhost:8000/alert/trigger?reagent=TSH&channel=labops-alerts"
```

---

## Project Structure

```
labops-agent/
├── backend/
│   ├── main.py           # FastAPI entry point
│   ├── mcp_server.py     # MCP tools (4 lab tools)
│   ├── prediction.py     # Prophet demand forecasting
│   ├── slack_client.py   # Bolt Python + event handlers
│   ├── database.py       # Supabase client
│   └── claude_client.py  # Claude API wrapper
├── blocks/
│   ├── alert.json        # Stockout alert Block Kit
│   ├── modal_order.json  # Order reagent modal
│   └── canvas.json       # Inventory canvas template
├── data/
│   ├── create_tables.sql # Supabase schema
│   └── seed_data.sql     # Demo data (DEMO badge)
├── docs/
│   ├── architecture.md   # Technical architecture
│   ├── impact.md         # Impact metrics
│   └── demo_script.md    # 3-minute demo script
├── models/               # Prophet serialized models (.pkl)
├── AGENTS.md             # Development operating system
├── BIBLE.md              # Immutable declarations
└── CLAUDE.md             # Claude Code instructions
```

---

## UiPath Components Used

None — this project uses the **Slack platform** (MCP Server, Real-Time Search API, Slack AI) as the orchestration and agent layer.

---

## Data & Privacy

All data in this project is **synthetic and clearly labeled with DEMO badges**. No real patient data, no PHI. The prediction model was calibrated using anonymized demand patterns from 414,289 B2B clinical lab derivation records in Argentina — the records themselves are not included in this repository.

---

## License

MIT License — see [LICENSE](LICENSE)

---

## Builder

**Mariano Adrian Oss** · [DevelopOss](https://developoss.com) · Buenos Aires, Argentina

B2B KAM in clinical diagnostics (4 years) + AI Builder. This project applies real insider knowledge of clinical laboratory operations to a problem that existing software hasn't solved: predictive reagent management inside the tools labs already use daily.

---

*LabOps Agent · Slack Agent Builder Challenge 2026 · Track: Slack Agent for Good*
