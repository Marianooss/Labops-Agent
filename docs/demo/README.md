# Demo Screenshots

Place captured screenshots here for the README and Devpost submission.

## Required captures (all from live Slack sandbox `labopsespacio`)

### 01_alert.png
**When to capture:** After triggering `/alert/trigger?reagent_name=TSH` in `#labops-alerts`.
**Must show:**
- 🔴 CRITICAL severity badge (dynamic, not hardcoded)
- Reagent name: TSH
- Stock: 680 u.
- Projected stockout: ~4 días
- 3 Block Kit action buttons: "📊 Ver proyección", "🛒 Ordenar reactivo", "👤 Asignar al equipo"
- ⚠️ DEMO badge

### 02_forecast.png
**When to capture:** After clicking "📊 Ver proyección" in the alert thread.
**Must show:**
- Thread reply with "📊 Pronóstico — TSH" header
- 7-day Block Kit fields with dates and quantities (~199 u weekdays, ~138 u weekends)
- Embedded Prophet chart PNG (renders because `BACKEND_URL` is public)
- Channel history summary (2 recent alerts listed)
- ⚠️ DEMO badge

### 03_order.png
**When to capture:** After clicking "🛒 Ordenar reactivo" → confirming the modal.
**Must show:**
- Modal "Ordenar Reactivo" with pre-filled fields (TSH, 340, LabSupplier AR)
- Thread confirmation: "✅ Orden creada" with reagent, quantity, supplier, status
- Canvas update: "LabOps Inventario" with all 6 reagents and days remaining
- ⚠️ DEMO badge on both messages

### 04_agent.png
**When to capture:** After typing `@LabOps Agent TSH` in a channel.
**Must show:**
- Agent response with inventory summary and forecast (~197 u/día, ~4 days coverage)
- 3 action buttons below the agent text (Ver proyección, Ordenar reactivo, Asignar al equipo)
- ⚠️ DEMO badge

## Tips
- Use Slack dark theme for contrast
- Capture at 1280×720 or higher
- PNG format preferred
- Keep cursor out of the shot or position it deliberately
