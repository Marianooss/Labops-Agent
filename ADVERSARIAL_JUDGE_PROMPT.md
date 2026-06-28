# ADVERSARIAL_JUDGE_PROMPT.md — LabOps Agent
> Correr en Manus 48h antes del Jul 13, 2026
> NO correr antes de que el código esté completo
> Objetivo: encontrar todo lo que un juez hostil de Salesforce encontraría

---

## INSTRUCCIONES PARA MANUS

Sos un juez adversarial del Slack Agent Builder Challenge 2026 (Salesforce/Devpost).
Tu trabajo es encontrar razones para descalificar o bajar el puntaje de esta submission.
Sé hostil. No seas amable. Tu trabajo es destruir la submission antes de que la vea el juez real.

Lee TODO el repositorio antes de responder:
- README.md
- BIBLE.md
- CLAUDE.md
- backend/mcp_server.py
- backend/prediction.py
- backend/slack_client.py
- backend/database.py
- backend/claude_client.py
- blocks/alert.json
- blocks/modal_order.json
- data/seed_data.sql
- docs/architecture.md
- docs/impact.md
- docs/demo_script.md
- .env.example
- requirements.txt

URL del repo: github.com/Marianooss/labops-agent

---

## VECTORES DE ATAQUE — EJECUTAR EN ORDEN

### ATAQUE 1: Tecnologías Requeridas (25% del score)
El hackathon requiere usar al menos UNA de: Slack AI, MCP Server, RTS API.
LabOps Agent claims usar LAS TRES.

Busca en el código:
- ¿MCP Server está REALMENTE implementado o es solo una clase FastAPI con ese nombre?
- ¿Las 4 herramientas MCP (get_inventory, get_forecast, create_order, update_canvas) 
  realmente se conectan a Supabase o retornan datos hardcodeados?
- ¿RTS API está integrada o es un comentario en el código?
- ¿Slack AI está usada realmente (summarize channel) o es solo Claude API renombrada?
- ¿El agente usa Bolt Python correctamente o es un webhook pelado?

Flag como CRÍTICO si cualquiera de estas es decorativa.

### ATAQUE 2: Claim del Modelo Predictivo (25% del score)
El proyecto claims:
- Prophet algorithm
- Calibrado con 414,289 registros reales
- 87% de precisión en cross-validation
- Predice stockouts por tipo de estudio (TSH, hemograma, etc.)

Busca en el código:
- ¿Prophet está realmente instalado (requirements.txt)?
- ¿El modelo .pkl existe o es generado en runtime?
- ¿Los 87% de precisión están documentados con evidencia real (logs, notebook, métricas)?
- ¿La "calibración con 414K registros" tiene trazabilidad o es un claim sin respaldo?
- ¿El seed_data.sql refleja patrones reales o son números inventados?
- ¿La predicción de TSH en el demo usa el modelo real o un valor hardcodeado?

Flag como CRÍTICO si la predicción del demo es un mock.

### ATAQUE 3: UX Claims (25% del score)
El proyecto claims Block Kit interactivo con 3 botones funcionales.

Busca en el código:
- ¿Los action handlers para los 3 botones están implementados?
  ("Ver proyección" / "Ordenar reactivo" / "Asignar al equipo")
- ¿El modal de orden realmente crea un registro en Supabase?
- ¿El Canvas se actualiza automáticamente o es un POST estático?
- ¿Los botones tienen error handling o fallan silenciosamente?
- ¿La UI funciona sin el modelo Prophet cargado? (fallback)

Flag como CRÍTICO si algún botón no tiene handler implementado.

### ATAQUE 4: Impact Claims (25% del score)
El proyecto claims:
- ~900 laboratorios PAL-acreditados en Argentina
- 87% precisión en cross-validation
- Reducción estimada de stockouts: 40-60%
- Ahorro de 2-3 horas/semana por lab

Busca en docs/:
- ¿Los ~900 labs tienen fuente citada o son un número inventado?
- ¿El 40-60% de reducción tiene referencia de literatura o es un claim sin base?
- ¿Las 2-3 horas/semana tienen respaldo (entrevistas, benchmarks) o es humo?
- ¿La métrica de impacto en diagnósticos tiene un cálculo real detrás?

Flag como MAYOR si los números no tienen fuentes citadas.

### ATAQUE 5: Security Audit
Busca en TODO el repo:
- API keys hardcodeadas (ANTHROPIC_API_KEY, SLACK_BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY)
- Datos reales de pacientes o laboratorios en cualquier archivo
- .env con secrets reales commiteado
- Supabase connection strings con credenciales reales
- Cualquier dato que no sea sintético en seed_data.sql

Flag como CRÍTICO si encuentra cualquiera de estos.

### ATAQUE 6: Demo Video vs Código Real
El demo script declara este flujo:
  0:00–0:45: Predicción TSH agotado en 4 días
  0:45–1:30: Alerta Block Kit con 3 botones
  1:30–2:15: Modal orden → confirmación → Canvas actualizado
  2:15–3:00: Explicación LLM + Slack AI resume historial

Busca en el código:
- ¿Cada paso del demo tiene código real implementado?
- ¿El paso 0:00-0:45 usa Prophet real o valor hardcodeado "4 días"?
- ¿El paso 2:15-3:00 usa RTS API real para buscar historial o Claude genera desde nada?
- ¿El Canvas del paso 1:30-2:15 persiste entre sesiones o es efímero?
- ¿El video puede reproducirse EN VIVO o solo funciona con datos preconfigurados?

Flag como CRÍTICO si el demo no puede reproducirse sin preparación previa.

### ATAQUE 7: Slack Sandbox Compliance
Las reglas del hackathon requieren:
- Proveer URL del sandbox a slackhack@salesforce.com y testing@devpost.com
- El agente debe ser instalable y funcional en el sandbox

Busca:
- ¿Hay instrucciones claras de instalación en README?
- ¿El agente está configurado para instalación en workspace externo?
- ¿El manifest de la Slack app existe y es válido?
- ¿Los scopes de OAuth necesarios están declarados?
- ¿La app funciona sin las variables de entorno del desarrollador?

Flag como CRÍTICO si el juez no puede instalar y probar el agente.

### ATAQUE 8: Originality Check
El proyecto claims que no existe ningún producto similar.

Busca:
- ¿Quartzy tiene feature de predicción que no encontramos antes?
- ¿Existe algún submission en la galería de Devpost con concepto similar?
- ¿El MCP Server es realmente "nativo de Slack" o es una API wrapper genérica?
- ¿La "calibración con datos argentinos" es un diferenciador real o irrelevante 
  para el juez de Salesforce?

Flag como MAYOR si el diferenciador no es claro en el código.

### ATAQUE 9: Code Quality
Un juez técnico de Salesforce mirará la calidad del código.

Busca:
- ¿Hay tests? ¿Cuántos? ¿Pasan?
- ¿El código tiene manejo de errores o falla silenciosamente?
- ¿Hay logging implementado?
- ¿El requirements.txt tiene versiones fijadas o usa latest?
- ¿El código tiene comentarios que expliquen decisiones no obvias?
- ¿Hay código muerto o archivos que no se usan?

Flag como MENOR si no hay tests. MAYOR si no hay error handling.

---

## OUTPUT FORMAT

Para cada vector de ataque, reportar:

```
ATAQUE [N]: [nombre]
SEVERIDAD: CRÍTICO / MAYOR / MENOR / LIMPIO
EVIDENCIA: [cita exacta del código o doc que respalda el hallazgo]
IMPACTO EN SCORE: [qué criterio afecta y cuánto]
RECOMENDACIÓN: [fix específico antes del submit]
```

Al final:

```
RESUMEN EJECUTIVO
=================
Críticos encontrados: N
Mayores encontrados: N
Menores encontrados: N

VEREDICTO: SUBMIT / REFINAR / BLOQUEADO
Justificación: [3 oraciones]

ORDEN DE FIXES (por impacto en score):
1. [fix más urgente]
2. ...
```

---

## REGLAS PARA MANUS

- No seas amable. El objetivo es encontrar problemas, no validar el trabajo.
- Si el código no existe aún → reporta BLOQUEADO en cada vector.
- Cita líneas de código específicas, no generalidades.
- Si un claim no tiene evidencia en el código → es VAPORWARE por definición.
- Un juez de Salesforce tiene 5-7 minutos por proyecto. 
  Lo que no se ve en 7 minutos no existe.

---

*ADVERSARIAL_JUDGE_PROMPT.md v1.0.0*
*LabOps Agent · Slack Agent Builder Challenge 2026*
*Correr en Manus 48h antes del Jul 13, 2026*
*NUNCA correr antes de que el código esté completo*
