# PortPulse AI — Submission Scope Lock

## MVP that is in scope

PortPulse AI is intentionally scoped around the core operator workflow:

1. **Observe** — San Pedro Bay terminal capacity, vessel queue, weather and operational state.
2. **Predict** — 24/48/72-hour congestion forecasting with uncertainty and confidence.
3. **Explain risk** — hotspot ranking, binding-resource attribution and disruption flags.
4. **Optimise** — physically constrained berth allocation + quay-crane assignment with OR-Tools CP-SAT and FIFO comparison.
5. **Decide** — alternate routing recommendations and what-if stress tests.
6. **Act** — a 12-shift / 72-hour operating plan with provenance.
7. **Ask** — IBM Bob through MCP, where Bob invokes the real engines and explains their outputs.

## Deliberately deferred

The following are **Phase 2**, not missing MVP requirements:

- full live Terminal Operating System (TOS) integration
- EDI/event-stream ingestion
- complete port-wide berth estate beyond the four modeled POLB container terminals
- full BTS benchmark automation in the live inference path
- continuous online model retraining
- production authentication/authorization and multi-tenant deployment
- enterprise-scale distributed scheduling

This prevents the project from becoming a broad prototype with many shallow features. The roadmap prioritizes one complete, auditable decision loop over breadth.

## Architecture principle

**IBM Bob is the agentic interface, not the scheduler.**

```text
Operational data
      ↓
LightGBM + Isolation Forest
      ↓
Risk / hotspot attribution
      ↓
OR-Tools CP-SAT
      ↓
Validated berth + crane schedule
      ↓
Routing + 72h plan
      ↓
IBM Bob via MCP
      ↓
Supervisor-facing explanation
```

Bob may decide which tools to call and how to communicate the result, but the operational numbers and hard scheduling decisions come from deterministic/validated engines.

## Performance limitation

The prototype intentionally favors transparent, reproducible computation over production-grade latency. Cold forecast execution is approximately 11 seconds and a cold full plan can take approximately 20–30 seconds; warm cached requests are approximately 1 second. The demo should prewarm the engines before the walkthrough. This is a documented prototype limitation, not a claim of real-time dispatch latency.
