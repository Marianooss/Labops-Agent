# Claude Rules — LabOps Agent

> These rules govern ALL Claude behavior in this repo.
> Violation of any rule requires immediate rollback.

---

## 1. PRE-CODE RITUAL (non-optional)

Before writing or editing ANY code:
1. Read the specific file you will touch
2. Read `AGENTS.md` at project root
3. Read `BIBLE.md` for immutable declarations
4. Read `SESSION_STATE.md` for current session context
5. Grep for ground truth — never assume from memory

## 2. PROJECT CONTEXT

- **Name:** LabOps Agent
- **Goal:** Slack Agent for Good — Devpost submission by July 13, 2026
- **Track:** Slack Agent Builder Challenge 2026 (Salesforce)
- **Prize:** $8,000 USD (First Place)
- **Stack:** FastAPI + Bolt Python + Supabase + Prophet + Claude API
- **Deploy:** Render / Railway / Fly (persistent host) + Slack Developer Sandbox — **not** Vercel (Socket Mode needs a persistent websocket; see BIBLE DEC-07)
- **No PHI ever.** Only operational lab data (reagents, quantities, equipment names).

## 3. DECISION FILTER

Every code change MUST improve at least one of the 4 judging criteria:
1. **Technological Implementation** — MCP Server + Channel History API + Claude API summarization all used functionally
2. **Design** — Block Kit interactive UX, not passive notifications
3. **Potential Impact** — quantified lab operations improvement
4. **Quality of the Idea** — uniqueness, no existing product does this

If a change improves none → do NOT make it.

## 4. IMMUTABLE STACK (no human approval = no change)

| Layer | Technology |
|-------|------------|
| Backend | FastAPI + Python 3.11+ |
| Slack | Bolt Python |
| DB | Supabase (PostgreSQL) |
| Prediction | Prophet (Facebook) |
| LLM | Claude API `claude-sonnet-4-6`, **temperature=0** |
| UI | Slack Block Kit (buttons, modals) |
| Canvases | Slack Canvas API |
| Deploy | Render / Railway / Fly (persistent host) + Slack Sandbox — **not** Vercel (Socket Mode needs a persistent websocket; see BIBLE DEC-07) |

## 5. BLOCK KIT FIRST RULE

- Interactive buttons in messages are the PRIMARY UX pattern
- Slash commands are secondary/admin only
- Never present a passive notification where an interactive button can be used
- All Block Kit messages that show synthetic data MUST include `:warning: *DEMO*` badge

## 6. MCP SERVER — 4 TOOLS REQUIRED

These tools MUST be exposed and functional:
- `get_inventory(reagent_name)` → stock data
- `get_forecast(reagent_name, days)` → Prophet prediction
- `create_order(reagent_name, quantity, supplier)` → Supabase insert
- `update_canvas(channel_id, reagent_data)` → Canvas payload prepared

## 7. PREDICTION MODEL RULES

- Algorithm: **Prophet** only (seasonality + trend)
- All production/demo data is **synthetic** with visible DEMO badge
- Calibrated patterns (not real data): TSH spikes in winter (Jun-Aug AR), hemogram/ionogram stable
- Never modify Prophet algorithm without human approval + metric revalidation
- Model file `models/demand_model.pkl` is gitignored

## 8. CLAUDE API USAGE

- **Temperature: 0** — never change
- **Purpose only:** natural language explanation of WHY stockout is predicted
- **Never** use Claude for prediction math — that is Prophet's job
- API key via `ANTHROPIC_API_KEY` env var only — never hardcode

## 9. DEMO FLOW (locked — 3 minutes)

This flow is canonical for the hackathon video:
- 0:00–0:45: Prediction — TSH stockout in 4 days
- 0:45–1:30: Alert in #labops-alerts with 3 Block Kit buttons
- 1:30–2:15: Order modal → confirm → Canvas auto-update
- 2:15–3:00: Claude explains WHY + Claude API summarizes channel history

## 10. CODE STYLE RULES

- No hardcoded API keys anywhere (use env vars)
- All demo/synthetic data must have visible `:warning: *DEMO*` badge in Slack UI
- No patient data (PHI) in any file, comment, or log
- Import all dependencies at top of file
- Prefer minimal, focused edits over large refactors
- Add regression tests when fixing bugs

## 11. AUDIT CHECKLIST (run before every commit)

```bash
# No hardcoded keys
grep -r "hardcoded_api_key\|ANTHROPIC_API_KEY.*=" backend/ | grep -v ".env\|example\|comment"
# → must return empty

# DEMO badge present
grep "DEMO" backend/ blocks/ -r
# → must appear on all synthetic data displays

# Prophet referenced
grep "prophet\|Prophet" backend/
# → must appear in prediction engine

# Slack tech referenced
grep "bolt\|MCP\|channel" backend/ -r
# → must appear in Slack integration layer
```

## 12. DELIVERY GATE

Never declare "done" until ALL checks pass:
- [ ] Slack sandbox active
- [ ] MCP 4 tools functional
- [ ] Block Kit alert with 3 buttons functional
- [ ] Prophet predicts TSH stockout correctly in demo
- [ ] Claude API explains WHY in natural language
- [ ] DEMO badge visible on all synthetic data
- [ ] Video demo ≤3 min recorded
- [ ] Devpost submission completed

## 13. WHEN IN DOUBT

1. Read the file
2. Grep for the truth
3. Report what you find
4. Wait for **HUMAN_APPROVAL** before touching anything critical

## 14. ESCALATION

- `RESCUE.md` activates ONLY when Mariano declares it
- 3-strike rule: same bug fails 3 times → stop, report, wait for approval
- BIBLE.md always wins in disputes
