# Problem Statement — Container Congestion Predictor & Port Operations Optimiser

**Sector:** Logistics & Ports
**Severity tag:** Critical Now
**Setting:** San Pedro Bay — the twin Ports of Long Beach (POLB) and Los Angeles (POLA), the largest container gateway in the Western Hemisphere.

---

## 1. Core problem

> *Port operators still allocate berths, cranes, and yard space across hundreds of vessels manually in spreadsheets. Congestion hotspots are identified reactively — after vessels are already queuing — and alternate-routing decisions come too late to matter. The 2021 LA/Long Beach backlog (100+ ships waiting offshore for weeks, $10B+ in global supply-chain cost) is the canonical example of what happens when this is done reactively instead of predictively.*

**Primary users:** Port/terminal operations managers, shift supervisors, berth planning teams, vessel agents, carriers deciding on routing, and regional port authorities.

**Winning interpretation (§1 of the spec):**
> *The product must forecast congestion before it happens using vessel schedules and berth/yard/crane capacity data, recommend alternate routing or timing strategies, optimise berth and crane assignments under real operational constraints, and hand a shift supervisor a concrete 72-hour operations plan — not just a dashboard of current status.*

---

## 2. What the solution must NOT become (§1.1 of the spec)

- A live map that only shows where ships currently are (monitoring, not prediction or optimisation).
- An LLM-only chatbot that invents ETAs, berth availability, or crane throughput numbers.
- A congestion score with no underlying cause (berth-limited vs. yard-limited vs. crane-limited vs. gate-limited) and no recommended action.
- A berth/crane schedule that ignores hard constraints (vessel draft, berth length, crane reach, tidal windows, labor shift limits) and is therefore operationally unusable.
- A system that cannot explain why it predicted a hotspot or why it ranked one routing/berthing option over another.

---

## 3. Evidence: the 2021 San Pedro Bay backlog

In late 2021 the San Pedro Bay complex experienced the most visible supply-chain failure of the pandemic era:

- **100+ container ships waited offshore for weeks.** The Southern California Marine Exchange vessel queue climbed to a peak of roughly **109 ships** in January 2022, with dozens of vessels routinely waiting 2–4 weeks before a berth opened.
- **An estimated $10B+ in supply-chain impact.** The backlog rippled through inland distribution: empty containers stranded in Asia, chassis shortages, warehouse overflow, and holiday inventory shortfalls across the US economy.
- **The queue was managed the way it had always been managed.** Vessel arrivals, anchorage assignments, berth windows, crane gangs and yard plans were tracked in spreadsheets and updated by phone — hundreds of vessels against ~80 POLB berths and dozens of terminal operations, all asynchronous.

The structural problem was not a lack of capacity on paper — POLB alone operates 80 berths across 10 piers with 71 post-Panamax gantry cranes — it was that **no single operator view existed** connecting three tightly coupled things: *who is arriving and when* (vessel schedules), *what the infrastructure can absorb* (berth/crane capacity), and *what the congestion actually looks like right now and next* (queue behaviour).

---

## 4. Stakeholder pain

**Port / marine terminal operators**
- **Manual berth planning.** Berth allocation and crane assignment are worked out in spreadsheets, vessel by vessel. A single ULCV discharge plan can be 10,000+ moves; juggling 30–40 concurrent calls by hand means the plan is stale the moment a vessel slips.
- **Reactive hotspot discovery.** Congestion is noticed *after* vessels start stacking — the queue has already formed before anyone re-balances. There is no 72-hour warning that Pier J or Pier E is about to saturate.
- **Late routing decisions.** Diversion to Oakland, Seattle-Tacoma, Prince Rupert or Ensenada is only evaluated once the wait is already known and unacceptable. Timely divert/slow-steam decisions (before the last leg) save real money: a large container ship costs on the order of **$32,000/day** while it waits.

**Vessel operators / carriers**
- Long anchorage waits burn fuel and crew time, cascade into downstream port rotations, and stress time-sensitive cargo — refrigerated containers face growing spoilage risk by the hour.

**Shift supervisors**
- Handover between 6-hour shifts is verbal + spreadsheet; arrivals, berthings, crane moves, congestion alerts and routing decisions live in separate places. A single fused plan with a checklist does not exist today.

**Consequences of inaction:** queues form reactively, cranes and berths idle while ships wait offshore, expensive vessels anchor for weeks, and alternates are chosen too late to help.

---

## 5. The challenge — exactly four items

The project scope is deliberately **exactly this — nothing more, nothing less**:

1. **Predict congestion hotspots** using vessel schedules and berth capacity data.
2. **Recommend alternate routing strategies.**
3. **Optimise berth and crane assignments.**
4. **Generate a 72-hour port operations plan** for shift supervisors.

Explicitly out of scope: customs clearance, pricing/rating, carbon tracking, yard-level (inside-terminal) planning, and full AIS berth-clustering research.

---

## 6. What "solved" means for this submission

- Item 1 is a **real trained model** (LightGBM, not a lookup table) validated on a holdout with explicit uncertainty bands.
- Item 3 is a **real exact solver** (OR-Tools CP-SAT) constrained by the *published, real* POLB terminal capacities, compared against an industry-default FIFO baseline.
- Item 4 is **structured output** (JSON + human-readable shift text) a supervisor could actually print for handover, with visible assumptions and confidence levels.
- All four are reachable **from the dashboard** and **through Bob**, the AI ops assistant that invokes the engines and answers strictly from their output.

PortPulse AI implements all four items end-to-end; the mapping to code, API and UI is in [`README.md`](../README.md) and [`docs/architecture.md`](architecture.md).
