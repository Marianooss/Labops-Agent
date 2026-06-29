# LabOps Agent — Demo Script (≤3 Minutes)
> BIBLE-LABOPS-DEMO-FLOW · Updated 2026-06-29
> Record in Slack Developer Sandbox with live Render deploy.

---

## Pre-Demo Setup Checklist

Before recording:
- [ ] Render deploy live: `https://labops-agent.onrender.com` (`/health` returns 200)
- [ ] `BACKEND_URL=https://labops-agent.onrender.com` set in Render env vars (chart renders)
- [ ] `RUN_SOCKET_MODE=1` set in Render env vars (bot is online in Slack)
- [ ] Slack sandbox `https://labopsespacio.slack.com` open, `#labops-alerts` visible
- [ ] Supabase has seed data loaded (TSH stock=680, is_demo=true)
- [ ] `lab_config` table exists in Supabase (for Canvas persistence)
- [ ] Screen recording software ready (screen only, no camera)

**Quick verification commands (run from your machine):**
```bash
curl "https://labops-agent.onrender.com/health"
curl "https://labops-agent.onrender.com/alert/trigger?reagent_name=TSH"
```

---

## Demo Script

---

### SEGMENT 1: The Problem (0:00–0:30)

**[Screen: Show #labops-alerts channel]**

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

**[Action: Trigger the alert via curl or wait for scheduled alert]**

```bash
curl "https://labops-agent.onrender.com/alert/trigger?reagent_name=TSH"
```

**[Screen: Watch the Block Kit alert appear in #labops-alerts]**

The message shows dynamic severity derived from the Prophet model:
```
🔴 CRÍTICO — TSH

Reactivo: TSH            Severidad: 🔴 CRÍTICO
Stock actual: 680 u.     Stockout proyectado: ~3 días

¿Por qué? La demanda de TSH aumenta en invierno
(junio–agosto) en Argentina (~197 unid/día proyectado en días hábiles,
~138 en fines de semana). El stock actual (680) no cubre el
período de reorden de 7 días.

[📊 Ver proyección]  [🛒 Ordenar reactivo]  [👤 Asignar al equipo]

⚠️ DEMO — datos sintéticos calibrados con patrones reales
```

**Narration:**
> "LabOps Agent just detected that TSH — the highest-volume test in
> Argentine labs — will run out in about 3 days. Demand spikes every winter
> here, and current stock won't cover the reorder window.
>
> The agent explains WHY, not just WHAT. And it gives three actions
> directly in the message."

---

### SEGMENT 3: Taking Action (1:00–2:00)

**[Action: Click "🛒 Ordenar reactivo"]**

**[Screen: Modal opens with pre-filled fields]**

```
Ordenar Reactivo

Reactivo:    TSH                    [pre-filled]
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
Reactivo: TSH
Cantidad: 340.0
Proveedor: LabSupplier AR
Estado: pending

⚠️ DEMO — datos sintéticos calibrados con patrones reales
```

Canvas updates to show:
```
LabOps Inventario

🔴 TSH — 680 u. | 3 días | high
🟡 Hemograma — 2100 u. | 12 días | critical
🟢 Ionograma — 1850 u. | 12 días | medium
🟢 Glucosa — 920 u. | 7 días | medium
🟢 Urea — 760 u. | 10 días | low
🟢 Creatinina — 640 u. | 8 días | medium
```

**Narration:**
> "Order confirmed. A thread reply logs the transaction.
> The inventory Canvas updates automatically.
> All from Slack. No LIMS login required."

---

### SEGMENT 4: Forecast + Channel History (2:00–2:45)

**[Action: Click "📊 Ver proyección" in the alert thread]**

**[Screen: Thread opens with Block Kit fields + embedded chart]**

```
📊 Pronóstico — TSH
Próximos 7 días · demanda media ~181 u/día · total ~1268 u
Rango = banda de confianza 80% (Prophet)

2026-06-30        2026-07-01        2026-07-02
199 u · 180–217   200 u · 183–217   197 u · 178–216

2026-07-03        2026-07-04        2026-07-05        2026-07-06
198 u · 179–215   140 u · 122–158   137 u · 119–156   197 u · 179–216

[ chart: Demand Forecast — TSH (line + 80% CI band) ]
⚠️ DEMO — datos sintéticos calibrados con patrones reales
```

> Note: weekends dip (~138 u) and weekdays peak (~197–200 u); at this rate
> the current stock of 680 is consumed by **~2026-07-02 (~3 days)** — inside the
> 7-day reorder window, hence the 🔴 CRÍTICO flag.

**Narration:**
> "The agent surfaces 7-day demand forecasts with 80% confidence bands,
> and an embedded Prophet chart. You see the weekend dip in real time.
> When you ask about recent history, the agent summarizes past alerts
> from the channel — full context without leaving Slack."

**[Optional beat — multi-reagent reasoning]**

Type in channel:
```
@LabOps Agent compará el riesgo de stockout de TSH, Hemograma e Ionograma
```

The agent calls `get_inventory` + `get_forecast` per reagent and reasons across
the whole inventory — severity is computed, not hardcoded:
```
🤖 LabOps Agent
🔴 TSH        — ~3 días  → CRÍTICO  (pico de invierno)
🟢 Hemograma  — >12 días → OK       (demanda estable)
🟢 Ionograma  — >12 días → OK       (demanda estable)
⚠️ DEMO
```

**Narration:**
> "And it reasons across the whole inventory — TSH is critical because of the
> winter spike, while Hemograma and Ionograma stay stable. Same model, per-reagent."

---

### SEGMENT 5: Close (2:45–3:00)

**[Screen: Show the #labops-alerts channel with the alert + thread + Canvas]**

**Narration:**
> "LabOps Agent: predict, alert, act — all from Slack.
>
> Built on MCP Server, Slack Channel History API, and Claude API.
> Calibrated with patterns derived from anonymized demand analysis.
>
> Live at labops-agent.onrender.com —
> for the 900 accredited labs in Argentina managing critical
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
→ Re-run the curl command, check Render logs

**If modal doesn't open:**
→ Verify Slack App has `chat:write` and `commands` scopes

**If Canvas doesn't update:**
→ Show the thread confirmation instead — it's equally valid

**If chart doesn't render:**
→ Native Block Kit fields still show the 7-day forecast; mention "chart renders when BACKEND_URL is public"

---

## Video Upload Checklist

- [ ] Video ≤ 3:00 minutes
- [ ] Uploaded to YouTube (or Vimeo) as **Public** or **Unlisted**
- [ ] Link copied and ready for Devpost submission
- [ ] Title: "LabOps Agent — Slack Agent Builder Challenge 2026"

---

*Demo Script v2.0.0 · BIBLE-LABOPS-DEMO-FLOW · 2026-06-29*
*Verified against live Render deploy and Slack sandbox.*
