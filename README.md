# THALASSA — 3D Ocean Circulation Visual Analytics

**IEEE SciVis Contest 2026 · Task 3 · ECCO LLC4320**

THALASSA is a multiscale visual analytics system for exploring density-driven
3D ocean circulation in the NASA ECCO LLC4320 simulation — a
17,280 × 12,960 × 90 voxel, 10,312-hourly-timestep global ocean model.
It combines progressive petascale data streaming, TEOS-10 density derivation,
linked thermohaline phase space, 3D isopycnal surface rendering, and
event-centric temporal navigation into a single interactive web application.

---

## Research Contributions

| ID | Contribution | Status |
|----|---|---|
| **A** | Task-adaptive progressive query planning over OpenVisus IDX (cost-capped quality levels, fast previews, auto-refinement) | Complete |
| **B** | TEOS-10 thermohaline decomposition — SA, CT, σ₀, α, β, ρ_thermal, ρ_haline, compensation index, N² | Complete |
| **C** | Dual-domain linked analytics — geographic 3D view ↔ T–S–ρ phase space with lasso-to-isopycnal targeting | Complete |
| **D** | Temporal state navigation — per-timestep thermohaline descriptors, anomaly z-scores, play/scrub over 10,312 hours | Complete |
| **E** | Vertical-exchange event scoring — VE = \|w\| × exp(−N²/N²_ref) | Complete |

---

## Four Linked Panels

```
┌─────────────────────────┬─────────────────────────┐
│                         │                         │
│   Overview Map          │   3D Isopycnal View     │
│   MapLibre + σ₀         │   WebGL + viridis       │
│   heatmap overlay       │   orbit / zoom          │
│   click → re-center ROI │   PNG + GLB export      │
├─────────────────────────┼─────────────────────────┤
│                         │                         │
│   T–S Phase Space       │   Anomaly Timeline      │
│   Plotly scattergl      │   σ₀ z-scores over      │
│   lasso → set σ₀        │   time window           │
│                         │   click bar → jump      │
└─────────────────────────┴─────────────────────────┘
```

### Sidebar controls

- **ROI** — lat/lon bounds, depth range (0–6,600 m)
- **Temporal navigation** — scrub slider over all 10,312 timesteps, play/pause, 0.5×–4× speed
- **Isopycnal σ₀** — target density value; typical ranges annotated
- **Color by** — CT, SA, thermal expansion α, haline contraction β
- **Mesh quality** — Preview (fast ~3 s), Standard (balanced), Fine (full detail)
- **Decimation** — face cap at Off / 50 k / 20 k for bandwidth control

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| `←` / `→` | Step timestep ±1 |
| `Shift` + `←` / `→` | Step timestep ±10 |
| `Space` | Play / pause |
| `[` / `]` | Cycle quality preset down / up |

---

## System Architecture

```
Browser (React + Vite)
  │  TanStack Query — submit + poll pattern
  ▼
FastAPI  (:8000)
  │  sync: metadata, ROI query, density, overview, benchmark
  │  async (Celery): isopycnal extraction, temporal window
  ▼
Redis (:6379) — broker + result backend + 24 h response cache
  ▼
Celery workers — marching cubes, decimation, temporal descriptors
  ▼
LLC4320Reader → openvisuspy → ECCO OpenVisus IDX (Pelican CDN)
  theta: pelican://osg-htc.org/nasa/nsdf/climate1/llc4320/idx/theta/…
  salt:  pelican://osg-htc.org/nasa/nsdf/climate1/llc4320/idx/salt/…
  w:     pelican://osg-htc.org/nasa/nsdf/climate2/llc4320/idx/w/…
```

**Progressive refinement:** when quality is Standard or Fine, the isopycnal
hook concurrently submits a preview job at quality −7 (surface in ~3 s) and
the full-quality job. The panel shows the preview immediately, then swaps to
the refined mesh when it arrives, with a "Refining…" badge.

---

## API Reference

| Method | Path | Purpose |
|--------|------|---------|
| `GET`  | `/health` | Liveness check |
| `GET`  | `/api/metadata` | Dataset variables, grid info, timestep range, basin presets |
| `POST` | `/api/roi/query` | Raw theta/salt subvolume read with cost estimation |
| `POST` | `/api/derived/density` | TEOS-10 density fields for an ROI |
| `POST` | `/api/derived/vertical_exchange` | VE score and event fraction |
| `POST` | `/api/overview` | Coarse basin-level σ₀ heatmap (north_atlantic / southern_ocean / equatorial) |
| `POST` | `/api/scene/isopycnal` | Submit async marching-cubes isopycnal job → `job_id` |
| `GET`  | `/api/scene/export/{job_id}.glb` | Download completed mesh as binary glTF 2.0 |
| `GET`  | `/api/jobs/{job_id}` | Poll async job status (queued / running / complete / failed) |
| `POST` | `/api/temporal/window` | Submit async temporal descriptor job → `job_id` |
| `POST` | `/api/benchmark` | Density pipeline latency at multiple quality levels |

Interactive docs: `http://localhost:8000/docs`

---

## Repository Layout

```
.
├── start.sh                        # single-command launcher (Redis → API → Celery → Vite)
├── environment.yml                 # conda environment (Python 3.11, openvisuspy, gsw, …)
├── pipelines/
│   └── run_benchmark.py            # paper §V latency table generator
├── notebooks/                      # exploratory analysis scripts
└── thalassa/
    ├── backend/
    │   ├── main.py                 # FastAPI app — registers all routers
    │   ├── api/                    # routers: derived, overview, scene, temporal, benchmark, export, jobs, metadata, roi
    │   ├── api/schemas.py          # all Pydantic request/response models
    │   ├── data_access/            # LLC4320Reader, depth levels, basin presets
    │   ├── services/
    │   │   ├── derived_metrics/    # density.py, vertical_exchange.py
    │   │   ├── features/           # temporal.py — per-timestep descriptor
    │   │   ├── query_planner/      # planner.py — cost estimation and quality capping
    │   │   └── scene/              # isopycnal.py, decimation.py, gltf_export.py
    │   ├── workers/
    │   │   ├── celery_app.py       # Celery instance (Redis broker)
    │   │   └── tasks.py            # compute_density_async, extract_isopycnal_async, compute_temporal_window_async
    │   ├── cache/                  # Redis TTL cache helpers
    │   └── tests/                  # 75 pytest tests — 100 % passing
    └── frontend/
        ├── src/
        │   ├── App.tsx             # global keyboard shortcuts
        │   ├── api/                # isopycnal.ts, temporal.ts, overview.ts, derived.ts, roi.ts, metadata.ts
        │   ├── components/         # OverviewMap, IsopycnalView, TSPhaseSpace, AnomalyTimeline, ROIControls, StatusBar, PanelBoundary
        │   ├── panes/              # MainLayout.tsx — 2×2 CSS grid
        │   └── state/store.ts      # Zustand store (roi, sigma0, colorBy, playback, quality, decimation)
        └── vite.config.ts
```

---

## Prerequisites

- **Git**
- **Conda / Miniconda** (Python 3.11 environment)
- **Node.js 18+** and `npm`
- **Redis** (`redis-server` in PATH, or Docker)
- Access to the ECCO OpenVisus Pelican endpoint (panels will load but stay empty without it)

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/<your-org>/SciVis-2026-3D-Ocean-Circulation.git
cd SciVis-2026-3D-Ocean-Circulation
```

### 2. Create the conda environment

```bash
conda env create -f environment.yml
conda activate ocean
```

`start.sh` expects the environment to be named `ocean`.

### 3. Install frontend dependencies

```bash
cd thalassa/frontend && npm install && cd ../..
```

### 4. Launch

```bash
bash start.sh
```

This starts Redis (if not already running on :6379), FastAPI on :8000, a Celery
worker with 2 concurrent slots, and the Vite dev server on :5173. All logs go to
`.logs/`.

| Service | URL |
|---------|-----|
| Application | http://localhost:5173 |
| API docs | http://localhost:8000/docs |

Press `Ctrl-C` to stop everything cleanly.

### 5. (Optional) Run services manually

```bash
# Backend
conda activate ocean
cd thalassa/backend
PYTHONPATH=. uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Celery worker (separate terminal)
conda activate ocean
cd thalassa/backend
PYTHONPATH=. celery -A workers.celery_app worker --loglevel=info --concurrency=2

# Frontend (separate terminal)
cd thalassa/frontend
npm run dev
```

---

## Running Tests

```bash
conda activate ocean
cd thalassa/backend
python -m pytest tests/ -v
```

**75 tests, 0 failures.**

| Test file | Coverage |
|-----------|----------|
| `test_metadata.py` | `/api/metadata` response shape and content |
| `test_roi.py` | ROI query, 422 validation, land-mask fraction |
| `test_derived.py` | Density fields, surface slice shape, σ₀ range |
| `test_vertical_exchange.py` | VE score bounds, event fraction |
| `test_overview.py` | Basin heatmap, depth bands, lat/lon arrays |
| `test_isopycnal.py` | Marching-cubes geometry, empty isovalue, color values |
| `test_jobs.py` | Job status polling, state mapping |
| `test_gltf_export.py` | GLB magic bytes, JSON chunk, accessor counts, binary layout |
| `test_decimation.py` | Face reduction, color re-interpolation, edge cases |
| `test_temporal_service.py` | Anomaly z-score logic, schema validation |
| `test_benchmark_endpoint.py` | Latency table structure, quality cap |
| `test_export_endpoint.py` | GLB download, 404/409/503 error paths |

---

## Exporting Paper Figures

### 3D isopycnal surface

1. In the **3D Isopycnal** panel, click **PNG** to download the WebGL canvas.
2. Click **GLB** to download a binary glTF 2.0 file.
   - Open in Blender: *File → Import → glTF 2.0 (.glb/.gltf)*
   - The per-vertex scalar (CT / SA / α / β) is stored as `_CT`, `_SA`, etc. —
     apply a custom colormap via a *Attribute* node in the shader graph.
3. For ParaView: open the `.glb` via *File → Open* (glTF reader included since PV 5.9).

### Performance benchmark (paper §V)

```bash
conda activate ocean
# Server must be running; data connection required for accurate numbers
python pipelines/run_benchmark.py --runs 3 --output markdown

# LaTeX table directly:
python pipelines/run_benchmark.py --runs 3 --output latex > table.tex

# Save raw JSON:
python pipelines/run_benchmark.py --runs 1 --save results.json
```

---

## Troubleshooting

### Panels are blank

1. Check `.logs/backend.log` for connection errors to the OpenVisus Pelican endpoint.
2. Check `.logs/celery.log` — Celery must import the backend cleanly (`PYTHONPATH=.` is required).
3. If the Overview Map shows no σ₀ overlay, the `/api/overview` job may still be queued.
   Celery needs at least one free worker slot (default: 2).

### Redis conflict on :6379

`start.sh` skips starting Redis if a process is already listening on :6379.
If the existing instance is stale or wrong, stop it manually then rerun `start.sh`.

### Isopycnal panel stays on "Computing…"

- The job may be stuck in Celery. Open `http://localhost:8000/docs` and call
  `GET /api/jobs/{job_id}` with the ID shown in the status bar.
- If status is `failed`, check `.logs/celery.log` for the Python traceback.
- Try lowering quality to **Preview** or shrinking the ROI to reduce compute time.

### "No isopycnal found"

The requested σ₀ value is outside the ocean density range for the chosen ROI.
Check the typical range guide in the sidebar:
- Surface warm water: 24–26 kg m⁻³
- Thermocline: 26–27.5 kg m⁻³
- Deep cold water: 27.5–28 kg m⁻³

---

## Project Status

All 12 planned development weeks are complete.

| Weeks | Deliverable |
|-------|-------------|
| 1–2 | LLC4320Reader, OpenVisus integration, depth levels, TEOS-10 prototype |
| 3–4 | ROI query pipeline, query cost planner, Redis cache, density endpoint |
| 5–6 | Vertical exchange score, isopycnal marching cubes, overview heatmap, Celery async jobs |
| 7–8 | Three-panel React frontend (map, 3D, T–S), WebGL renderer, MapLibre integration |
| 7–8 | UI polish — color legends, panel titles, WebGL UNSIGNED_INT fix, 422 fixes |
| 9–10 | Temporal navigation — time slider, play controls, anomaly timeline panel |
| 11–12 | Mesh decimation (VTK QEM), binary glTF export, quality presets, benchmark endpoint |
| Final | Test suite (75 tests), progressive two-pass refinement, keyboard shortcuts, axis labels, PNG capture, benchmark pipeline script |

---

## Stack

| Layer | Libraries |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Zustand, TanStack Query v5, MapLibre GL JS, Plotly.js, WebGL 1 |
| Backend | FastAPI, Uvicorn, NumPy, SciPy, scikit-image, GSW (TEOS-10), PyVista |
| Async | Celery 5, Redis |
| Data | openvisuspy, ECCO LLC4320 via OpenVisus IDX / Pelican CDN |
| Tests | pytest, pytest-asyncio, httpx |
