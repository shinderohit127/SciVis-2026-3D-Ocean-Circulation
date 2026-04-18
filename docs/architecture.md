# THALASSA Architecture Notes

Updated as we build. Source of truth for architectural decisions made during implementation.

## Current status: Week 1–2 scaffold

### Service topology (local dev)

```
Browser (React/Vite :5173)
  └─ /api/* proxy ──► FastAPI (Uvicorn :8000)
                          ├─ Redis :6379       (cache + Celery broker)
                          ├─ DuckDB file       (metadata + summaries, no service)
                          └─ OpenVisus remote  (LLC4320 IDX via pelican://)
```

### React is control plane only

All density, clustering, mesh extraction, and event computation lives in the Python backend.
The frontend makes requests and renders results. No heavy numerics in JavaScript — ever.

### Cache key scheme (PRD §6.6)

Content-addressed keys over `(roi_hash, time_index, depth_range, metric, quality)`.

Format: `thalassa:{metric}:{roi_hash}:{t}:{z0}-{z1}:q{quality}`

Example: `thalassa:density:a3f9c1:4500:0-45:q-6`

### Known invariants

- OpenVisus quality: negative int, -15 is very coarse, 0 is full resolution.
- LLC4320 raw reads may be horizontally flipped vs standard lon convention.
  ALWAYS overlay cartopy coastlines before trusting any subvolume.
- TEOS-10 conversion chain: SP → SA via `gsw.SA_from_SP`, pt → CT via `gsw.CT_from_pt`,
  then `gsw.rho(SA, CT, p)` where p is pressure in dbar from depth.

### Known risks (PRD §10)

- openvisuspy compat with Python 3.11 — verify before locking deps.
- Grid orientation flip — mandatory orientation check per subvolume.
- Browser memory — surface-first design, no full global volumes in browser.
