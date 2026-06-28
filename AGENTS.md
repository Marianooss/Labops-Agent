# AGENTS.md — LabOps Agent
> Versión: 1.0.0 · Adapted from AGENTS.md v4.2 · DevelopOss
> Project: LabOps Agent · Slack Agent Builder Challenge 2026
> Compatible: Claude · Cursor · Windsurf · Claude Code
> Lives in: project root

---

## PRIME DIRECTIVE

Before ANY action in this repo, in this exact order:

1. Read CLAUDE.md — project identity, LLM backend, audit checklist
2. Read BIBLE.md — immutable stack, tokens, flows, delivery gate
3. Read SESSION_STATE.md — current context and pending tasks
4. Read the specific file you are about to touch
5. Grep for ground truth — never assume from memory

**HACKATHON FIRST RULE:**
Every decision is evaluated against the 4 judging criteria.
If a change doesn't improve any criterion, don't make it.

---

## OPERATING MODE

Declare your mode at the start of every response:

- 🏗️ ARCHITECT — designing structure, flows, architecture
- 🔨 BUILDER — writing production code
- 🔬 AUDITOR — reviewing, verifying, checking
- 🚑 RESCUE — fixing broken deliverables (only when Mariano declares)

---

## INVIOLABLE RULES (apply always, no exceptions)

**R01 — DEVPOST FIRST:**
Every session prioritizes hackathon delivery. No scope creep.
Judge criteria are the filter for every decision.

**R02 — BIBLE WINS:**
Stack, flows, and declared metrics are immutable without HUMAN_APPROVAL.
If in doubt, BIBLE.md is the source of truth.

**R03 — NO PHI EVER:**
Zero patient data. Zero health information. Only operational lab data
(reagent names, quantities, equipment names). No exceptions.

**R04 — NEVER INVENT:**
No hardcoded data, no fake metrics, no assumed API responses.
All demo data is synthetic and labeled with DEMO badge.
All production data is from Supabase.

**R05 — DELIVERY GATE:**
Never declare "done" without passing all Delivery Gate checks in BIBLE.md.
One incomplete check = not done.

**R06 — DEMO BADGE:**
All synthetic/demo data must have a visible DEMO badge in the Slack UI.
No exceptions. Block Kit must show it.

**R07 — BLOCK KIT FIRST:**
Interactive buttons in messages are the primary UX pattern.
Slash commands are secondary/admin only.
Never present a passive notification where an interactive button can be used.

**R08 — THREE TECHNOLOGIES:**
MCP Server, Real-Time Search API, and Slack AI must all be
functionally used — not decoratively. Each must serve a real purpose
in the agent flow.

**R09 — PROPHET IS CANONICAL:**
The prediction model is Prophet. Temperature=0 for Claude API.
Neither changes without HUMAN_APPROVAL and metric revalidation.

**R10 — NO AEGIS:**
Aegis integration is permanently cancelled (DEC-03 in BIBLE.md).
Do not propose it again. Do not reference it in code or docs.

---

## PREMORTEM (mandatory before any new feature)

Before writing a single line of code for a new feature:

```
PREMORTEM: [feature name]
→ Why will this fail?
→ What dependencies could break?
→ What does the judge NOT see in this?
→ Does this improve any of the 4 criteria?
→ Time estimate vs. time available?
```

If the answers show more risk than value → park it in BIBLE.md section 14.

---

## DELIVERY GATE — REFERENCE

Full checklist in BIBLE.md section 11.
Key items that block everything else:
- [ ] Slack sandbox active
- [ ] MCP 4 tools functional
- [ ] Block Kit alert with 3 buttons functional
- [ ] Prophet prediction working on demo data
- [ ] Demo video ≤3 min recorded

---

## PROJECT STRUCTURE (canonical)

```
labops-agent/
├── AGENTS.md           ← this file
├── BIBLE.md            ← immutable declarations
├── CLAUDE.md           ← LLM instructions
├── RESCUE.md           ← rescue protocol
├── SESSION_STATE.md    ← current session context
├── README.md           ← public-facing (for judges)
├── .env.example        ← env vars template (no secrets)
├── .gitignore          ← .env, __pycache__, models/*.pkl
│
├── backend/
│   ├── main.py         ← FastAPI app entry point
│   ├── mcp_server.py   ← MCP tools (get_inventory, get_forecast, create_order, update_canvas)
│   ├── prediction.py   ← Prophet model wrapper
│   ├── slack_client.py ← Bolt Python app + event handlers
│   ├── database.py     ← Supabase client
│   └── claude_client.py← Claude API wrapper
│
├── models/
│   └── demand_model.pkl← Serialized Prophet model (gitignored if large)
│
├── data/
│   └── seed_data.sql   ← Demo data for Supabase (DEMO badge required)
│
├── blocks/             ← Block Kit JSON templates
│   ├── alert.json      ← Stockout alert message
│   ├── modal_order.json← Order reagent modal
│   └── canvas.json     ← Inventory canvas template
│
├── docs/
│   ├── architecture.md ← Diagram for judges
│   ├── impact.md       ← Impact metrics (BIBLE-LABOPS-IMPACT-METRICS)
│   └── demo_script.md  ← 3-minute demo flow
│
└── demo/
    └── seed_scenario.py← Script to populate demo data
```

---

## SESSION WORKFLOW

### Starting a session:
```
1. Declare mode: 🏗️/🔨/🔬/🚑
2. Read SESSION_STATE.md
3. State what you're working on
4. Run PREMORTEM if new feature
5. Execute
```

### Ending a session:
```
1. Update SESSION_STATE.md:
   - COMPLETADO HOY
   - PENDIENTE PRÓXIMA SESIÓN
   - BUGS CONOCIDOS
   - PRÓXIMA SESIÓN ARRANCAR CON
2. Run audit checklist from CLAUDE.md
3. Declare: "Session complete. Delivery Gate status: [X/Y checks passing]"
```

---

## WIP COMMIT FORMAT (for long sessions)

```
WIP: [brief description]
---
Phase: [current phase]
Decisions: [key decisions made]
Remaining: [what's left]
Blocked_by: [if any blocker]
```

---

## 3-STRIKE DEBUG RULE (R27 from AGENTS.md v4.2)

If the same bug fails to fix after 3 attempts:
1. STOP immediately
2. Report:
   ```
   STATUS: 3-STRIKE REACHED
   BUG: [description]
   ATTEMPTED: [fix 1] / [fix 2] / [fix 3]
   REASON: [why each failed]
   RECOMMENDATION: [proposed approach]
   ```
3. Wait for HUMAN_APPROVAL before proceeding

---

## QUICK REFERENCE — JUDGING CRITERIA MAPPING

| Feature | Criterion | Points impact |
|---------|-----------|---------------|
| MCP + RTS + Slack AI all used | Technological Implementation | HIGH |
| Block Kit interactive buttons | Design | HIGH |
| Prophet prediction accuracy | Technological Implementation | MEDIUM |
| Canvas auto-update | Design | MEDIUM |
| Impact metrics declared | Potential Impact | HIGH |
| Scalability plan | Potential Impact | MEDIUM |
| No existing product does this | Quality of the Idea | HIGH |
| Demo video polished | All 4 | HIGH |

---

*AGENTS.md v1.0.0 · LabOps Agent · Slack Agent Builder Challenge 2026*
*Adapted from AGENTS.md v4.2 · DevelopOss*
