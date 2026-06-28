# LabOps Agent — Demo Script (3 Minutes)
> BIBLE-LABOPS-DEMO-FLOW · Declared 2026-06-25
> This is the canonical demo. Do NOT deviate without HUMAN_APPROVAL.
> Record in Slack Developer Sandbox with seed data loaded.

---

## Pre-Demo Setup Checklist

Before recording:
- [ ] Supabase has seed data loaded (TSH stock=680, is_demo=true)
- [ ] FastAPI backend running: `uvicorn backend.main:app --reload` (auto-pre-trains Prophet models on startup)
- [ ] Slack client running: `python -m backend.slack_client`
- [ ] Slack sandbox open in browser, `#labops-alerts` channel visible
- [ ] Screen recording software ready (no camera needed, screen only)

---

## Demo Script

---

### SEGMENT 1: The Problem (0:00–0:30)

**[Screen: Show #labops-alerts channel — empty or with old messages]**

**Narration:**
> "Clinical laboratories depend on reagents to run tests. When a reagent
> runs out, testing stops — and patients wait.
>
> Current solutions send alerts when stock is already low. By then,
> it's too late to avoid the stockout.
>
> LabOps Agent predicts stockouts **before they happen** — and lets
> lab staff act directly from Slack."

---

### SEGMENT 2: The Prediction Fires (0:30–1:00)

**[Action: Run the alert trigger]**

```bash
curl "http://localhost:8000/alert/trigger?reagent_name=TSH&channel=labops-alerts"
```

**[Screen: Watch the Block Kit alert appear in #labops-alerts]**

The message shows:
```
🔴 CRÍTICO — TSH

📊 Proyección de stockout: ~4 días
📦 Stock actual: 680 unidades
📈 Demanda proyectada: ~205 unid/día (pico de invierno)
⚠️ Lead time de reorden: 7 días

Por qué: La demanda de TSH aumenta un 80% en invierno
(junio-agosto) en Argentina. El stock actual no cubre
el período de reorden.

[📊 Ver proyección]  [🛒 Ordenar reactivo]  [👤 Asignar al equipo]

🔬 DEMO — datos sintéticos calibrados con patrones reales AR
```

**Narration:**
> "LabOps Agent just detected that TSH — the highest-volume test in
> Argentine labs — will run out in 4 days. Demand spikes every winter
> in Argentina, and current stock won't cover the reorder window.
>
> The agent explains WHY, not just WHAT. And it gives three actions
> directly in the message."

---

### SEGMENT 3: Taking Action (1:00–2:00)

**[Action: Click "🛒 Ordenar reactivo"]**

**[Screen: Modal opens with pre-filled fields]**

The modal shows:
```
Ordenar Reactivo

Reactivo:    TSH                    [pre-filled, read-only]
Cantidad:    [340] unidades          [suggested: 50% of current stock]
Proveedor:   [▼ LabSupplier AR  ]   [dropdown]
             LabSupplier AR
             Bioquímica SA
             LabMed Corp
             Diagnósticos Plus

[Cancelar]                    [✅ Confirmar Orden]
```

**Narration:**
> "One click opens the order modal. The reagent is pre-filled,
> the quantity is suggested based on the demand forecast, and
> the supplier dropdown pulls from our approved list."

**[Action: Select supplier, click Confirmar Orden]**

**[Screen: Thread reply appears + Canvas updates]**

Thread reply:
```
✅ Orden creada
TSH · 500 unidades · LabSupplier AR
Estado: pending · ID: #ORD-2026-001
🔬 DEMO
```

Canvas updates to show:
```
Inventario LabOps — DEMO
TSH · Stock: 680 · Última orden: pending
```

**Narration:**
> "Order confirmed. A thread reply logs the transaction.
> The inventory Canvas updates automatically.
> All from Slack. No LIMS login required."

---

### SEGMENT 4: Context from Channel History + Claude AI (2:00–2:45)

**[Action: Click "📊 Ver proyección" or ask the agent directly]**

Type in channel:
```
@LabOps resumen de alertas recientes de TSH
```

**[Screen: Claude AI summary appears in thread]**

The agent responds with:
```
📊 Proyección — TSH (próximos 7 días)
🔬 DEMO — datos sintéticos

Fecha         Demanda proyectada    Banda
2026-06-27    207 unid              190-224
2026-06-28    209 unid              192-226
2026-06-29    211 unid              194-228
2026-06-30    205 unid              188-222
2026-07-01    208 unid              191-225
2026-07-02    212 unid              195-229
2026-07-03    210 unid              193-227

📉 Stock actual (680) se agota ~2026-06-30
🔴 CRÍTICO: 4 días < 7 días de lead time
```

**Narration:**
> "The agent also surfaces 7-day demand forecasts with confidence bands.
> And when you ask about recent history, Claude AI summarizes past
> alerts from the channel history — giving full context without leaving Slack."

---

### SEGMENT 5: Close (2:45–3:00)

**[Screen: Show the #labops-alerts channel with the alert + thread]**

**Narration:**
> "LabOps Agent: predict, alert, act — all from Slack.
>
> Built on MCP Server, Slack Channel History API, and Claude API.
> Calibrated with patterns derived from anonymized demand analysis.
>
> For the 900 accredited labs in Argentina managing critical
> reagents every day."

**[End screen or fade out]**

---

## Recording Notes

- **No camera needed** — screen recording only
- **No slides** — the system running live is the demo
- **No music** — narration only
- Keep cursor movements slow and deliberate
- Pause 1 second after each UI action to let it register visually
- If a command takes >3 seconds → cut and resume after the result
- Total target: under 3:00 (Slack hackathon limit is 3 minutes)

---

## Backup Plan (if something breaks during recording)

**If Block Kit alert doesn't appear:**
→ Run `curl` command again, check FastAPI logs for errors

**If modal doesn't open:**
→ Verify Slack App has `channels:read` and `groups:read` scopes

**If Canvas doesn't update:**
→ Show the thread confirmation instead — it's equally valid

**If Claude AI summary is slow:**
→ Skip segment 4 and go straight to segment 5 — demo still works

---

## Video Upload Checklist

- [ ] Video ≤ 3:00 minutes
- [ ] Uploaded to YouTube (or Vimeo) as **Public** or **Unlisted**
- [ ] Link copied and ready for Devpost submission
- [ ] Title: "LabOps Agent — Slack Agent for Good | AgentHack 2026"

---

*Demo Script v1.0.0 · BIBLE-LABOPS-DEMO-FLOW · 2026-06-25*
