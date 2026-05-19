# DEMO_STORYBOARD.md

> **6–8 minute live demo for the hackathon jury.** This is the script —
> what to say, what to click, what to anticipate the audience asking.
> Read the project as a **fintech prototype** first, an AI demo second.

---

## Pre-demo checklist (do this 5 minutes before going on stage)

- [ ] `docker compose up -d` — postgres + redis running, both green.
- [ ] `python scripts/reset_database.py` — fresh seed (9 agents, genesis ledger).
- [ ] `uvicorn backend.main:app --port 8000 --log-level warning` — backend up on :8000.
- [ ] Frontend dev server running, pointing at `:8000`.
- [ ] Browser windows ready: (1) the dashboard, (2) `psql` shell (for the chain-corruption stunt), (3) `localhost:8000/docs` (the OpenAPI page — as a fallback if the frontend hiccups).
- [ ] Confirm Gemini key has fresh per-minute quota — fire one warmup call to `/api/v1/health` and one `POST /api/v1/jobs` against a `$30` budget (REJECTED tier — no LLM cost) to verify the API responds.
- [ ] Mentally rehearse the 30-second elevator pitch (Section 1 below) so you don't fumble the opening.

---

## 1. Opening (30 seconds) — the thesis

**Say it exactly like this:**

> "Just as humans gather, divide work, and exchange labor for payment — AI agents will do the same. We built the **payment infrastructure** for that economy.
>
> This isn't an AI demo. It's a fintech demo. Three pillars: **escrow** that locks user budget, **AI-as-judge** that verifies before money releases, and a **hash-chained ledger** that makes every transaction cryptographically auditable."

Cue the dashboard. Wallets grid visible.

---

## 2. Live demo (4–5 minutes)

### Setup shot (10 seconds)
On screen: nine agent wallets at **$0.00**, one user wallet at **$1,000.00**. Genesis block visible at the bottom of the ledger (`block_number: 0`, hash `27ba0da4…`).

> "Day zero. Nine agents on the marketplace. The user has $1,000. No one's been paid yet."

### Submit the job (10 seconds)
Click into the prompt input. Type:

```
Create a landing page for a developer AI tool
budget: $200
```

Click **Submit**. The page transitions; the WebSocket feed lights up.

> "The user just locked $200 into escrow. The frontend subscribed to a per-job WebSocket and is watching live."

### Beat 1 — Escrow + manager bid (~25 seconds)
Events appear in this order:
- `job.created` → `job.escrow_locked` → `payment.escrow_locked $200`
- `job.manager_bidding_started`
- `agent.bid.success ProjectManager_001`

Hover the PM's bid card. Read it aloud:

> "ProjectManager_001 just bid **$182** with an 18% margin. The math is in the prompt: it has to keep enough margin to cover four sub-agent payments plus four $2 judge fees, while still earning a profit."

Highlight the PM wallet ticking from **$0** to **$182** in real time. Highlight escrow wallet showing **$18** remaining (the user's unfunded buffer — that's the refund-at-end).

### Beat 2 — Planning (~25 seconds)
- `job.planning_started`
- `task.created` × 4 (one per sub-task)
- `job.plan_completed sub_task_count=4 expected_profit=24.76`

Show the four sub-tasks in the right panel:
- t1: Market research → $25, depends on nothing
- t2: Landing page copy → $35, depends on t1
- t3: Design direction → $22, depends on t1
- t4: Build landing page HTML → $55, depends on t2 + t3

> "The PM has decomposed the job into a DAG. Notice the structure: research feeds copy AND design in parallel; web dev waits for both. The marketplace is about to run four bidding rounds."

### Beat 3 — Marketplace in motion (~60 seconds)
Pause on **t1's bidding round**. The WS feed shows:
- `bidding.round_started eligible=[7 agents]`
- `bidding.bid_submitted ContentWriter_002 $13.00 (ghost, 65%)`
- `bidding.bid_submitted Designer_001 $14.40 (underdog discount)`
- `bidding.bid_submitted MarketResearcher_001 $20.00 confidence=0.85`
- `bidding.bid_submitted WebDeveloper_001 …`  (probably scope-reducing)
- A persona moment: `bidding.agent_declined ContentWriter_001 reasoning="copywriting is not market research"` — **read this aloud**: *"Notice — agents decline tasks outside their skill. The persona isn't cosmetic."*
- `bidding.winner_selected winner=MarketResearcher_001 score=0.78`

Open the **winner_selected** card. Read the reranker reasoning aloud:

> "The system explains why it picked: skill-match dominates, reputation as secondary, ghost agents filtered before rerank. This isn't just a price sort."

### Beat 4 — The Designer drama (the wow moment, ~60 seconds)
Wait for t3 (Design direction) to land in `VERIFYING`. The judge fires. The verdict comes back:

- `judge.verdict_delivered decision=REVISION_REQUESTED score=0.62`
- `task.revision_requested feedback="palette uses generic #3B82F6 — fails developer-audience brief fidelity"`

Pause. Read aloud:

> "The judge **just rejected the designer's first attempt**. The score sat in the [0.50, 0.69] revision band. The designer played it safe — generic blue palette, no audience signal. The judge cited the exact hex code as evidence.
>
> **This is the part that matters for the economy.** Watch what happens next."

The designer's second attempt fires automatically. Eventually:
- `task.execution_completed Designer_001 (attempt=1)`
- `judge.verdict_delivered decision=APPROVED score=0.88`
- `task.state_changed VERIFIED → PAID`

Show the side-by-side palette comparison if the UI has it (otherwise pull up the `output_json` and read the hex codes):

```
attempt 1 primary    : #3B82F6   ← generic Tailwind blue
attempt 2 primary    : #0D1117   ← GitHub dark, audience-coded
attempt 1 background : #FFFFFF   ← safe
attempt 2 background : #161B22   ← committed
attempt 1 score      : 0.62  (REVISION_REQUESTED)
attempt 2 score      : 0.88  (APPROVED)
```

> "Two judge fees deducted from the PM's margin — $4 total. The revision cost the designer half their potential pay. **The reputation system has real economic teeth.**"

### Beat 5 — Money flowing + final HTML (~45 seconds)
While t4 (WebDeveloper) is bidding + executing, narrate the wallet grid:
- t1 milestones drained MarketResearcher's slot of the PM wallet
- t2 paid the ContentWriter (premium bidder, $33.25 — *"won at higher price because reputation weighted the selection"*)
- t3 paid Designer_001 (after revision, $19.80 — underdog discount visible)
- Judge wallet ticking up: $2 + $2 + $4 + $2 = **$10** total fees

When t4 reaches `PAID`:
- `job.state_changed EXECUTING → COMPLETED`
- `payment.pm_profit_realized $X`
- `job.completed`

Switch to the **rendered HTML** view (frontend should render the `html_artifact` field in an iframe).

> "**The system actually shipped something.** Not a chatbot transcript — a runnable landing page. That HTML came out of WebDeveloper_001's `output_json` field, threaded through the aggregator."

### Beat 6 — The trust button (~30 seconds)
Click **Verify Chain Integrity**.

```
POST /api/v1/ledger/verify
→ { is_valid: true, blocks_verified: 21, duration_ms: 4 }
```

> "Twenty-one transactions, four milliseconds, **cryptographically valid**. Every dollar that moved is traceable."

#### Optional drama stunt (only if confident — adds 30s)
Open the psql shell. Run:
```sql
UPDATE transactions SET amount = 99999.99 WHERE block_number = 5;
```
Click **Verify Chain Integrity** again.

```
→ { is_valid: false, first_bad_block: 5 }
```

The UI flashes red. Read aloud:

> "Tamper with one byte — the chain notices the next block over. This is the same property a real blockchain gives you, in 30 lines of Python plus three SQL columns."

Restore: `UPDATE transactions SET amount = 6.25 WHERE block_number = 5;`

---

## 3. Architecture (1 minute)

Flip to the architecture slide. Hit these points fast:

- **9 agents**, 6 personas + 3 ghost rule-based bidders. Ghosts inflate the bidding pool but are hard-filtered before the reranker — they can't win execution. The marketplace LOOKS competitive even on a quiet day.
- **DAG executor** with bounded parallelism. The Gemini client enforces a semaphore (3 concurrent calls max) so a 4-task DAG doesn't melt the rate limit.
- **Hash-chained ledger** — three SQL columns (`block_number`, `block_hash`, `previous_block_hash`), 30 lines of code in `payments/ledger_service.py`. Audit-grade with no blockchain infrastructure.
- **WebSocket fan-out** — `core/event_bus.py` writes every event to the audit log AND broadcasts to live subscribers. The frontend's live feed and the historical replay come from the same row.
- **LLM-as-Judge** — the verification step is itself an autonomous agent with a fixed $2 fee per evaluation, regardless of verdict. Academic term: LLM-as-Judge (Zheng et al. 2023). Persona isolation via the system prompt; rubric weights are configured, not negotiable.

---

## 4. Fintech positioning (1 minute)

Don't pitch this as an AI project. Pitch it as a **fintech** project:

> "Stripe, Visa, Mastercard, and Google are all publicly investing in agent-to-agent payment infrastructure in 2026. **We built a working prototype of that future** — not the agents themselves, but the rails underneath them.
>
> Seven pillars, all live:
> 1. **Escrow** — user money locked before any agent acts.
> 2. **Milestone payments** — 25% / 25% / 50% releases on state transitions.
> 3. **AI-verified settlement** — money only flows after a judge approves output.
> 4. **Reputation-as-collateral** — agents earn reputation through delivery, lose it through rejection.
> 5. **Hash-chained ledger** — cryptographically auditable, no blockchain overhead.
> 6. **Agent-to-agent transfers** — the PM hires sub-agents and pays them autonomously.
> 7. **Algorithmic bidding** — hybrid embedding + composite score + LLM reranker selection.
>
> The agents are the product showcase. The **payment rails** are the technology."

---

## 5. Q&A — anticipate these questions

### "How does the judge stay objective?"
> "Three guardrails: a **fixed $2 fee** per evaluation regardless of verdict (no incentive to approve), **evidence-cited reasoning** (the prompt requires it — `'good work'` is forbidden, `'hero_headline X is specific and quantified'` is the standard), and a **fixed-weight rubric** (0.25 scope, 0.20 structure, 0.35 content, 0.20 fidelity) computed on the wire. We can show you the prompt — it's in `backend/agents/prompts/qa_judge.py`."

### "What if Gemini goes down mid-job?"
> "Demonstrated live earlier in development: a 429 quota error during PM bidding → tenacity backed off through `[5, 10, 20]` seconds → still failed → `GeminiAPIError` caught at the orchestrator → **$200 full refund** to the user → job FAILED with reason `pm_bid_failed:GeminiAPIError`. Money conservation perfect, chain stayed valid. The system survives partial Gemini failures."

### "How do you prevent agents from colluding?"
> "Three layers. **Ghost agents are filtered before the reranker** — they fill the marketplace visually but can't win execution. **Reputation is updated after every verdict** — score >= 0.85 adds 0.02, score < 0.50 subtracts 0.05, clamped to [0.10, 0.99]. Collusion would have to survive both layers AND fool the judge, which is an independent agent. **In v2, you'd swap the single judge for a quorum.**"

### "Isn't this just a chatbot orchestrator?"
> "No — and here's the proof. **Money actually moves.** We just watched $200 enter escrow, $182 transfer to the PM, four milestone payments fan out, two judge fees deduct, $18 refund issue, and PM keep $14.75 in margin. **All of that reconciles to the cent.** The ledger is hash-chained, so the audit trail is cryptographically verifiable. **Try that with a chatbot.**"

### "Why didn't you use blockchain?"
> "We have the same trust property — hash-chained immutability — at **100× lower complexity**. The ledger is a Postgres table with three extra columns and `validate_chain()` is 40 lines of code. Could move to on-chain settlement post-MVP, but the trust model doesn't require it. We earned that simplification by being honest about what the chain needs to prove."

### "How does the manager pick sub-tasks?"
> "An LLM call with a structured prompt — the PM persona has explicit decomposition rules per budget tier. MINIMAL ($50–$149) → 2 tasks. STANDARD ($150–$499) → 4 tasks: research → copy + design → web dev. PREMIUM ($500+) → up to 6 tasks. The prompt enforces that sub-task budgets sum to ≤ `accepted_bid × (1 − margin)`, with 5–10% reserved as overflow."

### "What about latency?"
> "End-to-end for a STANDARD job: about 90 seconds wall-clock — dominated by Gemini latency. The DAG runs with bounded parallelism (3 concurrent agents). For demo polish you'd add a 'slow mode' that paces events for the human eye, but everything you saw was real time."

### "Can multiple users use the same agent pool?"
> "Yes — the agent registry is a singleton, but every wallet operation locks the affected rows (`SELECT FOR UPDATE`) and the ledger has a per-process write lock. For multi-tenant production you'd swap that lock for a Postgres advisory lock and add user authentication. Out of scope for the hackathon."

---

## Backup talking points (if a moment dies)

- **MarketResearcher declining the copywriting task** — note when it happens. Read the agent's exact reasoning aloud. It's funnier than a slide can be.
- **The premium bidder** — ContentWriter_001 wins despite bidding higher than ContentWriter_002 (the ghost). The composite score weights reputation at 25% and skill at 35% — together they out-vote the 20% price weight.
- **The seeded reputations** — they aren't random. ContentWriter is 0.88 (highest worker), Designer is 0.71 (underdog), Judge is 0.95 (system authority). The reputation scoreboard you see on the wallet grid is *narrative*, not just data.

---

## End state

After the demo runs, leave the dashboard at the COMPLETED state with the rendered HTML visible. Ledger panel shows 21+ blocks, chain validates, total volume ~$425. Hand off to questions.

Good luck.
