# DATASETS & DATA SOURCES
# FOR CONTAINER CONGESTION PREDICTION

*Research Compilation — L1: Container Congestion Predictor & Port Operations Optimiser*

---

## 1. Purpose of This Document

This document maps every data requirement from the Problem Analysis document to a real, findable data source, rates how directly usable each source is for a hackathon build, and proposes a synthetic-data strategy to fill the gaps that no public dataset covers (live berth/crane/yard operational status, which is almost always proprietary terminal-operating-system data).

---

## 2. Data Requirements Mapped to Modules

| Data need | Feeds modules |
|---|---|
| Vessel schedules & tracks (ETA, position, size) | Modules B, E, F |
| Historical port throughput / berthing time / TEU volume | Modules E, F, G |
| Berth / crane / yard capacity & configuration | Modules A, C, J |
| Live berth / crane / yard occupancy status | Modules C, G |
| Weather & sea state | Modules F, H |
| Port geography / world port reference data | Modules A, I |

---

## 3. Tier 1 — Real, Directly Downloadable Open Datasets

### 3.1 NOAA / BOEM MarineCadastre AIS Data

The single best free source of real vessel-movement ground truth. Covers over a decade of U.S. coastal AIS broadcast points (position, speed, heading, IMO/MMSI, vessel type) — this is what lets you compute real anchorage dwell time, berth dwell time, and turnaround time per vessel class at a real port.

- [AccessAIS (custom area/time "clip and ship", CSV, <2GB orders)](https://marinecadastre.gov/accessais/)
- [Bulk annual AIS downloads (2009–present, CSV/geodatabase)](https://marinecadastre.gov/ais/)
- [2024–2025 analysis-ready GeoParquet vessel-track files (cloud-optimised, works with DuckDB/GeoPandas)](https://github.com/ocm-marinecadastre/ais-vessel-traffic)

**Use for:** Building the historical congestion knowledge base (Module E), computing real arrival-rate distributions to seed the forecasting model (Module F), and validating synthetic data.

**Caveat:** Raw AIS has gaps and noisy points near anchorages; the GeoParquet product is already cleaned and is the better starting point for a time-boxed hackathon.

### 3.2 U.S. Bureau of Transportation Statistics — Port Performance Freight Statistics Program (PPFSP)

Congressionally mandated, nationally consistent port performance data — real, structured, and easy to pull.

- [Weekly Vessel Berthing Statistics by Port (containership & tanker average/median berthing time and call counts, Jan 2025–present)](https://www.bts.gov/ports)
- [Monthly TEUs by Port (Jan 2019–present) and Top 25 U.S. Ports by TEU](https://data.bts.gov/stories/s/mign-rc8p/)
- [Technical documentation (methodology for vessel calls, dwell time, terminal polygons)](https://www.bts.gov/PPFS-Tech-Docs)

**Use for:** Ground-truth benchmarking of your forecast output, and for populating realistic baseline berthing-time ranges per port/vessel-type in Module E.

### 3.3 Kaggle — Ports & AIS Datasets

- [Ports dataset (World Port Index derived: name, country, lat/long, harbor size/type, depth, services) — good for Module A reference data](https://www.kaggle.com/datasets/marwaashraf5814/ports-ais)
- [Port of Los Angeles shipment dataset (260k shipped items)](https://www.kaggle.com/datasets/mikoajfish99/port-of-los-angeles)

**Use for:** Quick-start static port/terminal reference tables without waiting on a government data pull.

### 3.4 NGA / NOAA World Port Index

The canonical open reference for global port physical characteristics (channel depth, berth data, cargo pier depth, anchorage depth) that underlies the Kaggle port dataset above. Useful if you need ports beyond what the Kaggle export includes.

### 3.5 Weather & Sea State

- [NOAA National Data Buoy Center (NDBC) — real buoy wind/wave data near major U.S. ports](https://www.ndbc.noaa.gov/)
- [Open-Meteo API — free, no-key historical & forecast weather API, simplest to integrate for a hackathon](https://open-meteo.com/)

**Use for:** The exogenous weather signal in the forecasting model (Module F) and disruption detection (Module H).

---

## 4. Tier 2 — Academic / Research Datasets (for methodology & realistic parameters)

These are not one-click downloads but are documented in published papers and are worth citing for credibility and for extracting realistic queuing parameters even if you cannot obtain the raw files directly:

- Maher Terminal (Port of NY/NJ) AIS-derived vessel-trajectory dataset, 2015–2023, used in the Temporal-IRL berth-scheduling paper (arXiv 2506.19843) — describes entry/exit times, waiting-area dwell, and assigned berth per vessel.
- Port of Houston longitudinal vessel arrival & queue behaviour study (arXiv 2509.22961) — good source of realistic anchorage-queue statistics.
- Port of Cagliari / Port of Antwerp vessel-arrival-time classification studies — useful for realistic weather-driven arrival uncertainty parameters.

**Use for:** Calibrating your synthetic data generator (Section 6) so demo numbers look like real-world queueing behaviour instead of arbitrary random draws.

---

## 5. Tier 3 — Commercial Platforms (reference / validation only, not for direct data pull)

These are proprietary, subscription-based congestion-intelligence products. You cannot download their data as a hackathon dataset, but their public methodology pages are useful to sanity-check what "good" congestion metrics look like and to describe the competitive landscape in your pitch:

- MarineTraffic / Kpler Container Intelligence — terminal-level congestion, vessel queues, 6-week predictive schedules.
- Portcast Port Congestion Tracker — 600+ port congestion index, public methodology write-ups are useful reference.
- GoComet Port Congestion Tracker — turnaround-time-based congestion index across ~400 ports.

---

## 6. Synthetic Data Generation Strategy

No public dataset exposes live, granular berth/crane/yard occupancy for a real terminal — that data lives inside proprietary Terminal Operating Systems (TOS). The recommended hackathon approach is a hybrid: real distributions, synthetic instances.

### Step 1 — Extract real parameters
- From MarineCadastre AIS + BTS PPFSP: real inter-arrival time distributions, real dwell-time distributions by vessel size class, real seasonal/day-of-week patterns.

### Step 2 — Define a synthetic terminal
- 6 berths, 12 quay cranes, 4 yard zones, 1 gate complex (matches the demo scenario in the Problem Analysis document) — small enough to reason about, large enough to show real bottleneck trade-offs.

### Step 3 — Generate a synthetic vessel-call schedule
- Sample vessel arrivals from the real inter-arrival distribution extracted in Step 1; assign vessel size/draft from a realistic fleet-mix distribution; deliberately inject one bunching event and one equipment-outage event for the demo narrative.

### Step 4 — Simulate operational state forward
- Use a discrete-event queuing simulation (berth occupied → cranes work at a stochastic rate → yard fills → gate processes) to produce realistic time-series berth/crane/yard occupancy that your forecasting and optimisation modules consume as if it were live TOS data.

**Why this is defensible in a hackathon pitch:** Judges will ask where your data came from — being able to say "real AIS-derived arrival patterns and BTS-benchmarked dwell times, replayed through a discrete-event simulation for the operational layer that no public dataset covers" is far stronger than either pure random data or an unexplained black box.

---

## 7. Recommended Combined Data Architecture for the Hackathon

| Layer | Source | Ingestion mode |
|---|---|---|
| Port/terminal reference | Kaggle World Port Index export | Static, one-time load |
| Vessel arrivals & tracks | MarineCadastre AIS GeoParquet (real port, historical window) | Batch load + replay |
| Congestion benchmarks | BTS PPFSP weekly berthing stats | Batch load, used for validation |
| Weather | Open-Meteo API | Live API call |
| Berth/crane/yard live status | Synthetic discrete-event simulation (Section 6) | Generated, streamed |

---

## 8. Licensing / Usage Notes

- NOAA/BOEM AIS data: public domain U.S. government data; derived products may be redistributed with source citation.
- BTS PPFSP data: public U.S. government statistical data, free to use and cite.
- Kaggle datasets: check each dataset's individual license tab before redistribution; most port/AIS datasets on Kaggle are CC0 or similar but verify per-dataset.
- Open-Meteo: free for non-commercial and most commercial use under its stated terms; attribute per their documentation.
- Commercial platforms (MarineTraffic/Kpler, Portcast, GoComet): do not scrape or redistribute their proprietary data — reference their public methodology only.

---

## 9. Quick-Start Data Acquisition Checklist

- [ ] Pick one real, well-documented port (e.g. Port of Long Beach or Port of NY/NJ) as the AIS reference case.
- [ ] Pull a 3–6 month AIS GeoParquet window for that port from the MarineCadastre bulk archive.
- [ ] Pull the matching BTS PPFSP weekly berthing statistics for the same port/period as a validation benchmark.
- [ ] Extract inter-arrival time and dwell-time distributions by vessel size class from the AIS pull.
- [ ] Build the synthetic 6-berth/12-crane/4-yard-zone terminal and run the discrete-event simulation seeded with those distributions.
- [ ] Pull Kaggle World Port Index data for the static port/terminal reference table.
- [ ] Wire in Open-Meteo for the weather signal on the same port's coordinates.
- [ ] Document, in the final report/pitch, which numbers are real (AIS, BTS) vs. simulated (berth/crane/yard live state) — this transparency is itself a differentiator per Module M (Explainability).
