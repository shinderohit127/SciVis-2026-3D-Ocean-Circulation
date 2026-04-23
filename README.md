# SciVis-2026-3D-Ocean-Circulation

THALASSA is an interactive visual analytics prototype for exploring 3D ocean circulation patterns in the ECCO LLC4320 dataset. The application combines a React frontend, a FastAPI backend, and background Celery workers to let users inspect a region of interest, derive density-related fields, and extract isopycnal surfaces for 3D viewing.

## What the project does

The current application is organized around three linked panels:

- `Overview Map`: a North Atlantic overview map with a surface `sigma0` overlay and a draggable region of interest.
- `Isopycnal View`: a WebGL-based 3D rendering of a selected potential-density surface inside the active ROI.
- `T-S Phase Space`: a temperature-salinity scatter plot for the active ROI, colored by `sigma0`, with lasso selection to target density layers.

The backend handles all heavy computation. The frontend is intentionally light and focuses on state management, interaction, and rendering.

## Stack

- Frontend: React, TypeScript, Vite, Zustand, TanStack Query, MapLibre GL, Plotly
- Backend: FastAPI, Uvicorn, NumPy, SciPy, scikit-image, GSW, DuckDB
- Async jobs: Celery with Redis
- Data access: `openvisuspy` against ECCO LLC4320 / OpenVisus-style sources

## Repository layout

```text
.
├── start.sh                      # local launcher for Redis, backend, Celery, frontend
├── environment.yml               # conda environment for backend + notebooks
├── docs/                         # architecture and product notes
├── notebooks/                    # exploratory and prototype analysis notebooks/scripts
├── docker/                       # container files
└── thalassa/
    ├── backend/
    │   ├── api/                  # FastAPI routes and request/response schemas
    │   ├── data_access/          # LLC4320/OpenVisus readers and depth helpers
    │   ├── services/             # density, scene extraction, planner logic
    │   ├── workers/              # Celery app and async task entry points
    │   ├── cache/                # Redis cache helpers
    │   ├── tests/                # backend tests
    │   └── main.py               # FastAPI app entrypoint
    └── frontend/
        ├── src/components/       # map, 3D view, controls, status bar, plot panels
        ├── src/api/              # frontend API hooks
        ├── src/state/            # Zustand state store
        └── src/panes/            # app shell/layout
```

## How the app works

1. The user sets an ROI, timestep, density value, and optional coloring field in the left sidebar.
2. The frontend requests:
   - overview data from `POST /api/overview`
   - density slices from `POST /api/derived/density`
   - isopycnal extraction jobs from `POST /api/scene/isopycnal`
3. The backend reads ocean subvolumes, computes TEOS-10-derived fields, and returns lightweight summaries to the browser.
4. CPU-heavy isopycnal extraction is dispatched to Celery and polled through `GET /api/jobs/{job_id}`.
5. The frontend keeps the three panels linked through shared state.

## Prerequisites

You will need the following installed locally:

- Git
- Conda or Miniconda
- Node.js 18+ and `npm`
- Redis
- A working Python toolchain compatible with the packages in `environment.yml`

You will also need access to the underlying ECCO/OpenVisus data source expected by `openvisuspy`. If that data endpoint is unavailable, the UI may load but data-backed panels will not populate.

## Clone and run locally

### 1. Clone the repository

```bash
git clone https://github.com/<your-org-or-user>/SciVis-2026-3D-Ocean-Circulation.git
cd SciVis-2026-3D-Ocean-Circulation
```

If you are using your own fork, replace the URL with your fork’s URL.

### 2. Create the conda environment

```bash
conda env create -f environment.yml
conda activate ocean
```

Note: `start.sh` expects the conda environment to be named `ocean`.

### 3. Install frontend dependencies

```bash
cd thalassa/frontend
npm install
cd ../..
```

### 4. Start Redis

If Redis is not already running on your machine:

```bash
redis-server
```

If you prefer to let the launcher script reuse an existing Redis instance, make sure it is listening on `127.0.0.1:6379`.

### 5. Launch the full stack

From the repository root:

```bash
bash start.sh
```

This script starts:

- Redis on `:6379` if one is not already running
- FastAPI backend on `:8000`
- Celery worker for async extraction jobs
- Vite frontend on `:5173`

When everything is healthy, open:

- Frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`

### 6. Stop the stack

Press `Ctrl-C` in the terminal running `start.sh`.

## Running services manually

If you want to run each piece yourself:

### Backend

```bash
conda activate ocean
cd thalassa/backend
PYTHONPATH=. uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Celery worker

```bash
conda activate ocean
cd thalassa/backend
PYTHONPATH=. celery -A workers.celery_app worker --loglevel=info --concurrency=2
```

### Frontend

```bash
cd thalassa/frontend
npm run dev
```

## Logs

When using `start.sh`, logs are written under:

```text
.logs/
├── backend.log
├── celery.log
├── frontend.log
└── redis.log
```

These are the first place to check if a panel is blank, requests are failing, or a background job never finishes.

## Development notes

- Frontend state lives in `thalassa/frontend/src/state/store.ts`.
- React Query hooks for backend communication live in `thalassa/frontend/src/api/`.
- Map rendering is implemented in `OverviewMap.tsx`.
- The custom WebGL isopycnal renderer lives in `IsopycnalView.tsx`.
- Density and phase-space data are derived in backend services under `thalassa/backend/services/derived_metrics/`.
- Isopycnal extraction is implemented in `thalassa/backend/services/scene/isopycnal.py`.

## Testing and verification

### Frontend

```bash
cd thalassa/frontend
npm run typecheck
npm run build
```

### Backend tests

```bash
conda activate ocean
cd thalassa/backend
pytest
```

## Common issues

### Redis fails to start

If `.logs/redis.log` shows an error that port `6379` is already in use, either:

- stop the conflicting Redis instance, or
- keep that Redis instance running and rerun `start.sh` so it reuses it

### Frontend loads but panels are empty

Check:

- `.logs/backend.log` for `4xx` or `5xx` API errors
- `.logs/celery.log` for worker failures
- whether the OpenVisus/ECCO source is reachable from your environment

### API works but 3D panel never updates

The isopycnal panel depends on both Redis and Celery. If the backend is up but async jobs never complete, verify:

- Redis is reachable
- the Celery worker is running
- `workers.celery_app` started without import errors

## Current status

This repository is a research/contest prototype rather than a polished production app. It already includes:

- a working local dev launcher
- backend tests
- linked panel interactions
- density-derived metrics
- async isopycnal extraction

It still assumes a research environment with data access and system dependencies already available.
