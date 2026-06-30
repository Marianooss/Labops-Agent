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

## Demo Script — Final Voiceover (≤ 3 Minutes)

> **TTS Voice Recommendation:** Male — Professional/Corporate or Financial/Narrator, US or UK neutral accent. Speed: **1.0x**.

---

**[00:00] — Opening Title Card**

> "Welcome to the LabOps Agent demonstration.
> LabOps Agent. Slack-First predictive operations for clinical laboratories.
> A predictive operations platform that transforms Slack into an intelligent clinical inventory management hub."

*(Visual: LabOps logo centered on dark background with product name and tagline. Duration: ~12 seconds.)*

---

**[00:12]**

> "In the healthcare sector, a reagent stockout in a clinical laboratory is not just a logistics issue; it is a critical operational failure that directly delays patient diagnostics."

---

**[00:21]**

> "Traditional solutions fail because they rely on static thresholds, completely ignoring biological seasonality and demand spikes. This leads to emergency reorder costs up to five times higher and unsustainable lead times."

---

**[00:33]**

> "To solve this, we designed LabOps Agent with a Slack-First philosophy. Our architecture utilizes a persistent Socket Mode connection integrated with an asynchronous FastAPI backend."

---

**[00:44]**

> "Through a decoupled Model Context Protocol server, we orchestrate a predictive engine powered by Meta Prophet and a Supabase database, leveraging Claude 4.6 Sonnet for context synthesis."

---

**[00:56]**

> "Let's see the solution in action. From a completely clean Slack channel, a user mentions the agent to request the stock prediction for the TSH reagent."

---

**[01:06]**

> "The agent responds natively and instantly with a structured Block Kit message. By clicking 'View forecast,' the AI seamlessly retrieves the thread history and deploys an advanced predictive chart with an eighty percent confidence interval."

---

**[01:39]**

> "If stock is running low, the user can trigger a reorder directly from the interface. Upon confirming the purchase of three hundred and forty units, data synchronizes instantly with Supabase."

---

**[01:56]**

> "This reactively updates the LabOps Inventory Canvas on the right side in real time, displaying the new 'High' stock status to the entire lab team."

---

**[02:06]**

> "Finally, the workflow closes by assigning the task review to a team member natively, transforming Slack into a highly efficient, predictive, and automated operations hub for clinical management."

---

**[02:17] — End screen**

> "LabOps Agent — predict, alert, act. All from Slack."

---

## Production Notes

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
