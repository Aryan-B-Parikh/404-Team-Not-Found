# presentation/ — Submission deck

`slides.pdf` (9 slides, 1280×720 landscape) is the submission deck. `slides.html` is the editable/source presentation and `preview.png` is the contact sheet.

Fonts are self-hosted in `presentation/fonts/` so the deck renders without network access.

## Slide outline

1. **Problem** — San Pedro Bay congestion, reactive hotspot discovery, manual berth/crane planning and late routing decisions.
2. **Data** — REAL: Port of Long Beach terminal reference facts. DEMO: reproducible synthetic operational history labelled `DEMO_AIS`. REAL AIS is available through the NOAA AccessAIS import path.
3. **Forecasting** — LightGBM 72-hour congestion forecasting with point estimates and quantile uncertainty bands, plus validation metrics.
4. **Optimisation** — OR-Tools CP-SAT berth allocation + quay-crane assignment under hard physical constraints, contrasted with FIFO.
5. **Routing** — DIVERT / SLOW_STEAM / PRIORITY_WINDOW / HOLD recommendations driven by predicted congestion and documented cost assumptions.
6. **72-Hour Plan** — 12 × 6-hour shifts with arrivals, berthings, crane deployment, congestion alerts, decide-by deadlines and supervisor actions.
7. **IBM Bob** — load-bearing agentic integration: IBM Bob uses the PortPulse MCP server to select and execute operational tools, receives structured engine outputs, and synthesizes the supervisor-facing decision. Tool actions are surfaced in the application. No secondary external LLM provider is used.
8. **Impact** — earlier warning, physically constrained schedules, economically informed routing, fused shift handover and auditable engine evidence.
9. **Demo** — 3–5 minute real run: start stack → Overview → Forecast → optimise/scenario → Routing → 72-Hr Plan → Bob. Replace `demo/demo-video-link.txt` with the hosted recording before final submission.

## Presentation claims

Keep the deck synchronized with the code. The default operational dataset is **synthetic `DEMO_AIS`**, not measured AIS. The REAL data claim is limited to the POLB reference capacity table unless a genuine NOAA AccessAIS file has been imported. IBM Bob is the load-bearing agent and MCP is the integration layer.
