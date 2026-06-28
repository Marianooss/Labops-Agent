# BIBLE_LABOPS.md — Registro de Entregables Inmutables
> Versión: v1.0.0 · LabOps Agent · Slack Agent Builder Challenge 2026
> Compatible con: AGENTS.md v4.2 · CLAUDE.md v1.0.0 · RESCUE.md v1.0.0

---

## ⚠️ REGLA MAESTRA

**La BIBLE siempre gana.**
Si un entregable nuevo contradice una BIBLE sin razón documentada,
el entregable está mal — no la BIBLE.

El agente puede PROPONER cambios. No puede ejecutarlos sin HUMAN_APPROVAL.
Nunca modifica tokens, stack, ni flujos críticos por iniciativa propia.
RESCUE.md se activa solo cuando Mariano lo declara.

---

## 1. IDENTIDAD DEL PROYECTO

```
NOMBRE:          LabOps Agent
MARCA:           LabOps
TAGLINE:         "Predict. Alert. Act. All from Slack."
DOMINIO:         Slack Developer Sandbox (hackathon)
OWNER:           Mariano Adrian Oss · DevelopOss
ESTADO:          EN DESARROLLO
FECHA INICIO:    2026-06-25
REPO:            github.com/Marianooss/labops-agent (pendiente crear)
TRACK:           Slack Agent for Good
HACKATHON:       Slack Agent Builder Challenge 2026 (Salesforce/Devpost)
DEADLINE:        July 13, 2026 @ 5:00pm PDT
PREMIO:          $8,000 USD (First Place)
```

---

## 2. PROBLEMA QUE RESUELVE

```
PAIN REAL:
  Los laboratorios clínicos dependen de reactivos críticos.
  Cuando un reactivo se agota, los diagnósticos se detienen.
  Las soluciones actuales (Quartzy, Scispot) solo alertan DESPUÉS 
  de que el stock ya bajó del umbral — reacción, no predicción.
  Nadie predice cuándo se va a agotar un reactivo basándose en 
  patrones históricos de demanda por tipo de estudio.
  El personal de laboratorio debe salir de Slack para gestionar 
  inventario en sistemas LIMS complejos.

USUARIO OBJETIVO:
  Personal técnico y supervisores de laboratorios clínicos que 
  usan Slack como plataforma de comunicación.

POR QUÉ AHORA:
  Slack lanzó MCP Server + RTS API en 2026.
  El Agent Builder Challenge es la ventana perfecta para demostrar
  un agente predictivo nativo de Slack en healthcare operations.

MOAT (ventaja defensible):
  Modelo predictivo calibrado con 414,289 registros reales de 
  derivación clínica en Argentina — establece patrones reales de
  demanda por tipo de estudio (TSH, hemograma, ionograma, etc.)
  El know-how está en los patrones de dominio clínico, no en el modelo base.

MERCADO:
  ~900 laboratorios PAL-acreditados en Argentina (primario)
  ~200-500 mercado pagador realista
  LATAM + global (fase 2 y 3)
```

---

## 3. ENTREGABLE CANÓNICO

```
TIPO:            Slack Agent (Bolt Python)
CANAL:           Slack Workspace (Developer Sandbox)
ACCESO:          Slack Agent Builder Challenge sandbox
BACKEND:         FastAPI + Python (Vercel deploy)
BASE DE DATOS:   Supabase (PostgreSQL)
MODELO:          Prophet (demand forecasting)
LLM:             Claude API (claude-sonnet-4-6)
DEPLOY:          Vercel (backend) + Slack Sandbox (agent)
MODO DEMO:       SÍ — datos sintéticos calibrados con patrones reales
                 Badge DEMO siempre visible en datos sintéticos
```

---

## 4. STACK CANÓNICO

> El agente no puede cambiar tecnologías sin HUMAN_APPROVAL explícito.

```yaml
slack:
  sdk:           bolt-python
  sandbox:       Slack Developer Program (gratis)
  technologies:
    - MCP Server (herramientas del agente)
    - Real-Time Search API (búsqueda en workspace)
    - Slack AI (resúmenes de canal)
    - Block Kit (UI interactiva)
    - Canvas API (documentos de inventario)

backend:
  framework:     FastAPI
  language:      Python 3.11+
  deploy:        Vercel

prediction:
  algorithm:     Prophet (Facebook/Meta)
  training:      414,289 B2B derivation records (Argentina)
  accuracy:      87% cross-validation
  features:      [test_type, month, week_of_year, trend]

database:
  provider:      Supabase
  tables:
    - inventory (reagent_name, current_stock, unit, criticality)
    - demand_history (reagent_name, date, quantity, test_type)
    - orders (reagent_name, quantity, supplier, status, created_at)
    - alerts_log (reagent_name, predicted_stockout_date, severity, created_at)

llm:
  provider:      Anthropic
  model:         claude-sonnet-4-6
  temperature:   0
  use:           natural language explanation of predictions
  key:           ANTHROPIC_API_KEY (env var, never hardcoded)
```

---

## 5. DESIGN SYSTEM — SLACK NATIVE

> Este proyecto no tiene frontend web. La UI es 100% Slack-native.
> Block Kit es el design system. No hay CSS, no hay tokens de color.

```
COMPONENTES CANÓNICOS:
  - Section blocks (texto con mrkdwn)
  - Action blocks (botones interactivos)
  - Modal views (formularios de orden)
  - Canvas (documento de inventario)

BOTONES CANÓNICOS (en alerta de stockout):
  - "📊 Ver proyección" → abre modal con gráfico de demanda
  - "🛒 Ordenar reactivo" → abre modal de orden
  - "👤 Asignar al equipo" → abre selector de usuarios

CANAL CANÓNICO:
  - #labops-alerts (alertas automáticas del agente)

TONO DE MENSAJES:
  - Directo y específico ("TSH se agota en 4 días")
  - Explica el POR QUÉ ("demanda estacional de junio")
  - Sugiere acción concreta
```

---

## 6. BIBLIAS DECLARADAS

### BIBLE-LABOPS-DEMO-FLOW

```
Entregable  : demo/script.md
Tipo        : demo script
Declarada   : 2026-06-25
Inmutable   : SÍ — requiere HUMAN_APPROVAL para modificar
Aplica a    : Video demo de 3 minutos para submission

FLUJO CANÓNICO (NO CAMBIAR):
  0:00–0:45 — Predicción: TSH agotado en 4 días
  0:45–1:30 — Alerta Block Kit con 3 botones
  1:30–2:15 — Modal orden → confirmación → Canvas actualizado
  2:15–3:00 — Explicación LLM + Slack AI resume historial
```

### BIBLE-LABOPS-IMPACT-METRICS

```
Entregable  : docs/impact.md
Tipo        : impact declaration
Declarada   : 2026-06-25
Inmutable   : SÍ — requiere HUMAN_APPROVAL para modificar

MÉTRICAS DECLARADAS (para judging):
  - ~900 laboratorios PAL-acreditados en Argentina
  - Modelo calibrado con 414,289 registros reales
  - 87% precisión en cross-validation
  - TSH es el estudio de mayor volumen (273,601 unidades en dataset)
  - Reducción estimada de stockouts: 40-60% (basado en literatura)
  - Ahorro estimado: 2-3 horas/semana por lab en gestión de inventario
```

---

## 7. ARQUITECTURA

```
┌─────────────────────────────────────────────────────────┐
│                    SLACK WORKSPACE                       │
│   #labops-alerts  │  Canvas Inventario  │  App Home     │
└──────────────────┬──────────────────────────────────────┘
                   │ Bolt Python (events, actions, modals)
┌──────────────────▼──────────────────────────────────────┐
│                  FASTAPI BACKEND                         │
│                                                          │
│  ┌─────────────────┐    ┌──────────────────────────┐    │
│  │   MCP SERVER    │    │   PREDICTION ENGINE      │    │
│  │                 │    │                          │    │
│  │ get_inventory() │    │ - Prophet model          │    │
│  │ get_forecast()  │    │ - Stockout date calc     │    │
│  │ create_order()  │    │ - Demand by test type    │    │
│  │ update_canvas() │    │ (calibrated: 414K rows)  │    │
│  └────────┬────────┘    └──────────────┬───────────┘    │
└───────────┼────────────────────────────┼────────────────┘
            │                            │
┌───────────▼────────────────────────────▼────────────────┐
│                      SUPABASE                            │
│  inventory  │  demand_history  │  orders  │  alerts_log  │
└─────────────┴──────────────────┴──────────┴─────────────┘
            │
┌───────────▼────────────────────────────────────────────┐
│                   CLAUDE API                            │
│  - Generar explicación en lenguaje natural              │
│  - Resumir historial de alertas (vía Slack AI)          │
└────────────────────────────────────────────────────────┘
```

---

## 8. FLUJOS CRÍTICOS

```
FLUJO-01 — Alerta de Stockout (happy path):
  1. Scheduler corre cada hora → prediction engine calcula stockouts
  2. Si projected_stockout_days < reorder_lead_time → dispara alerta
  3. Claude API genera explicación en lenguaje natural
  4. Bolt Python publica Block Kit message en #labops-alerts
  5. Botones interactivos esperan acción del usuario
  → Resultado: Lab staff alertado antes del problema

FLUJO-02 — Orden de Reactivo:
  1. Usuario clickea "Ordenar reactivo" en mensaje de alerta
  2. Modal se abre con proveedor sugerido, cantidad, fecha estimada
  3. Usuario confirma → orden creada en Supabase
  4. Canvas de inventario se actualiza automáticamente
  5. Confirmación en hilo del mensaje original
  → Resultado: Orden gestionada sin salir de Slack

FLUJO-03 — Consulta de Historial:
  1. Usuario pregunta al agente sobre un reactivo
  2. RTS API busca mensajes y canvases relacionados en el workspace
  3. Slack AI resume el historial del canal
  4. Agente responde con contexto completo
  → Resultado: Visibilidad histórica sin LIMS externo
```

---

## 9. REGLAS DE NEGOCIO INAMOVIBLES

```
RN-01: El agente predice ANTES del stockout — nunca alerta por umbral bajo.
       La diferencia con Quartzy/Scispot es esta. No ceder.

RN-02: Cero PHI — Solo datos operacionales (reactivos, cantidades, equipos).
       Ningún dato de paciente en ningún lugar del proyecto.

RN-03: DEMO badge visible en todos los datos sintéticos.
       Los datos de producción del lab demo son ficticios — debe ser claro.

RN-04: Block Kit interactivo — nunca slash commands como interfaz principal.
       Los botones en el mensaje son el paradigma de UX declarado.

RN-05: Las tres tecnologías (MCP + RTS API + Slack AI) deben usarse realmente.
       No como wrapper decorativo — deben cumplir función real en el flujo.
```

---

## 10. CONTRATOS DE DATOS

```
FUENTE 1: Datos sintéticos de demo
  · Calibrados con patrones del dataset real (414,289 registros AR)
  · Badge DEMO visible siempre
  · Formato: JSON en Supabase (seed data)
  · NO son los datos reales de Labmedicina — son sintéticos

FUENTE 2: Claude API
  · URL: api.anthropic.com/v1/messages
  · Key: ANTHROPIC_API_KEY (env var)
  · Uso: explicaciones en lenguaje natural, no predicción

FUENTE 3: Prophet model
  · Trained on: patrones extraídos del dataset real
  · Serialized: models/demand_model.pkl
  · Retrained: offline, no en producción
```

---

## 11. DELIVERY GATE (HACKATHON)

> Un entregable NO está "done" hasta pasar todos estos checks.

```
[ ] Slack Developer Sandbox activo y accesible
[ ] MCP Server expone las 4 herramientas (get_inventory, get_forecast, create_order, update_canvas)
[ ] RTS API busca mensajes relacionados con reactivos en el workspace
[ ] Slack AI resume historial de canal #labops-alerts
[ ] Block Kit muestra alerta con 3 botones funcionales
[ ] Modal de orden funciona end-to-end
[ ] Canvas se actualiza automáticamente al confirmar orden
[ ] Prophet model predice stockout de TSH correctamente en demo
[ ] Claude API explica el POR QUÉ en lenguaje natural
[ ] DEMO badge visible en datos sintéticos
[ ] Video demo ≤3 minutos grabado y en YouTube/Vimeo
[ ] Diagrama de arquitectura incluido en submission
[ ] URL del sandbox proporcionada a slackhack@salesforce.com y testing@devpost.com
[ ] Descripción del proyecto en inglés
[ ] Submission en Devpost completada antes del Jul 13 5pm PDT
```

---

## 12. PROHIBICIONES ABSOLUTAS

```
PRO-01: Usar PHI o datos reales de pacientes en cualquier lugar
PRO-02: Hardcodear API keys en el código
PRO-03: Usar slash commands como interfaz principal (usar Block Kit)
PRO-04: Integrar Aegis o cualquier sistema externo no verificado
PRO-05: Declarar "done" sin pasar Delivery Gate completo
PRO-06: Mostrar datos sintéticos sin badge DEMO visible
PRO-07: Modificar el algoritmo Prophet sin revalidar métricas declaradas
PRO-08: Cambiar el stack sin HUMAN_APPROVAL
PRO-09: Inventar métricas de impacto — solo usar las declaradas en BIBLE
PRO-10: Agregar features que no mejoren alguno de los 4 criterios del juez
```

---

## 13. ESCALABILIDAD — DECLARADA (para judging)

```
FASE 1 (Hackathon → Mes 3):
  → 5 laboratorios piloto en Argentina
  → Validar reducción de stockouts

FASE 2 (Mes 4-6):
  → 20+ laboratorios en Argentina
  → Modelo genérico: cualquier lab con histórico de consumo

FASE 3 (Mes 7-12):
  → LATAM expansion
  → Transfer learning para labs sin histórico propio
```

---

## 14. IDEAS PARKEADAS

```
IDEA-001 [2026-06-25]: Integrar con sistema de proveedores para auto-order
  — Motivo: Post-hackathon, requiere API de proveedor

IDEA-002 [2026-06-25]: Dashboard web para gerencia del laboratorio
  — Motivo: Post-hackathon, el jurado evalúa Slack-native

IDEA-003 [2026-06-25]: Extender a gestión de equipos y calibración
  — Motivo: Post-hackathon, V2 del producto
```

---

## 15. CÓMO MODIFICAR ESTA BIBLE

```
1. Mariano escribe: "HUMAN_APPROVAL: modificar BIBLE-[X]"
2. El agente propone el cambio exacto — no lo ejecuta
3. Mariano confirma con "SÍ" explícito
4. El agente ejecuta el cambio y registra en sección 16
5. La versión anterior queda en sección 17 (BIBLE HISTORY)
```

---

## 16. HISTORIAL DE DECISIONES

```
DEC-01 [2026-06-25]: Slack Agent for Good como track (no New Slack Agent)
  — Motivo: Healthcare operations = impacto social claro, mejor para judging

DEC-02 [2026-06-25]: Prophet para predicción (no ARIMA, no LSTM)
  — Motivo: Mejor manejo de estacionalidad, interpretable, rápido de implementar

DEC-03 [2026-06-25]: Descartada integración Aegis
  — Motivo: Aegis no tiene API pública deployada, ficción técnica, riesgo alto

DEC-04 [2026-06-25]: Datos sintéticos calibrados (no dataset real en producción)
  — Motivo: PRO-01, ética, viabilidad, cumplimiento de reglas hackathon

DEC-05 [2026-06-25]: FastAPI + Vercel (no Next.js)
  — Motivo: Backend puro, más simple, compatible con Bolt Python

DEC-06 [2026-06-25]: Las tres tecnologías requeridas (MCP + RTS + Slack AI)
  — Motivo: Maximiza Technological Implementation criterion (25%)
```

---

## 17. BIBLE HISTORY

```
[Vacío — ninguna BIBLE ha sido modificada todavía]
```

---

## 18. SESSION_STATE — ÚLTIMA SESIÓN

```
FECHA:            2026-06-25
MODO OPERATIVO:   🏗️ ARCHITECT
BRANCH/COMMIT:    main · initial setup

COMPLETADO HOY:
  ✅ Idea validada: LabOps Agent
  ✅ Market research: gap confirmado (Quartzy/Scispot son pasivos)
  ✅ Premortem ejecutado (Gemini): pivotado de MediAgent a LabOps
  ✅ Judge evaluation: 89/100 → 95+ con 3 mejoras
  ✅ Aegis integration: descartada (no ejecutable)
  ✅ BIBLE.md, CLAUDE.md, AGENTS.md, RESCUE.md generados

PENDIENTE PRÓXIMA SESIÓN:
  → Registrarse en Slack Developer Program (sandbox)
  → Crear repo github.com/Marianooss/labops-agent
  → Setup FastAPI skeleton + Supabase schema
  → Implementar MCP Server (4 herramientas)

PRÓXIMA SESIÓN ARRANCAR CON:
  "BUILDER MODE — Stage 1: Slack Developer Sandbox + repo setup"
```

---

*BIBLE_LABOPS.md v1.0.0 · LabOps Agent · Slack Agent Builder Challenge 2026*
*Compatible con AGENTS.md v4.2 · CLAUDE.md v1.0.0 · RESCUE.md v1.0.0*
