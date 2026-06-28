# RESCUE.md — LabOps Agent
> Rescue protocol for AI-complacent deliverables.
> Activate when: agent shipped placeholder data, skipped validation, 
> or delivered incomplete work.
> Compatible with AGENTS.md v4.2 · System 35 Anti-Vaporware Protocol

---

## ⚠️ ACTIVATION RULE
RESCUE.md se activa SOLO cuando Mariano lo declara explícitamente.
El agente nunca activa RESCUE.md por iniciativa propia.
Declaración válida: "RESCUE" o "activar RESCUE" o "RESCUE.md"

---

## Activation Criteria

Activate RESCUE.md when ANY of the following are detected:

- [ ] Datos sintéticos sin badge DEMO visible en la UI de Slack
- [ ] Predicción inventada sin trazabilidad al modelo Prophet
- [ ] Block Kit buttons que no ejecutan acción real (mocks)
- [ ] MCP tools que retornan datos hardcodeados sin Supabase
- [ ] Delivery Gate checks declarados como "done" sin verificación
- [ ] Documentación desalineada con código real
- [ ] PHI o datos reales de pacientes en cualquier lugar del repo
- [ ] API keys hardcodeadas en el código

---

## Rescue Protocol Steps

### Phase 1 — Stop and Assess

1. **HALT all new feature work.** No additions until rescue complete.
2. **Run F17 VAPORWARE SCAN** on entire project.
3. **Run F5 AUDITOR MODE** on all files touched since last verified state.
4. **Document findings** in ERROR_LOG.md.

### Phase 2 — Triage Findings

```
CRITICAL — Blocks hackathon submission
  → Fix immediately. No exceptions.
  Examples: sandbox not working, MCP tools broken, demo fails

HIGH — Affects judge score or credibility  
  → Fix before next session.
  Examples: missing DEMO badge, Block Kit buttons non-functional

MEDIUM — Documentation gaps, minor inconsistencies
  → Fix in next session.
  Examples: missing comments, stale SESSION_STATE
```

### Phase 3 — Surgical Fix

1. **One issue at a time.** No bulk replacements.
2. **Replace placeholders with real data or explicit DEMO badges.**
3. **Verify each fix** with manual test in Slack sandbox.
4. **Update BIBLE.md and SESSION_STATE.md** after each fix.

### Phase 4 — Verification Gate

Before declaring rescue complete:

- [ ] All Slack Block Kit buttons functional in sandbox
- [ ] MCP Server returns real Supabase data (not mocks)
- [ ] DEMO badge visible on all synthetic data
- [ ] Prophet model returns valid prediction (not hardcoded)
- [ ] SESSION_STATE.md updated with rescue summary
- [ ] Mariano confirms rescue is complete

---

## Rescue Log

| Date | Trigger | Findings | Resolution |
|------|---------|----------|------------|
| — | — | — | — |

---

## LabOps-Specific Risk Registry

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Slack sandbox not provisioned | HIGH | CRITICAL | Register at api.slack.com/developer-program immediately |
| Prophet model fails on demo data | MEDIUM | HIGH | Pre-validate with seed data before recording video |
| MCP tools timeout | LOW | HIGH | Add 10s timeout + fallback error message in Block Kit |
| Block Kit modal broken | LOW | HIGH | Test every interactive component in sandbox |
| Demo video > 3 minutes | MEDIUM | MEDIUM | Script demo, rehearse 3x before recording |
| Submission form incomplete | LOW | CRITICAL | Read Devpost requirements checklist 48h before deadline |

---

*RESCUE.md v1.0.0 — LabOps Agent · Slack Agent Builder Challenge 2026*
