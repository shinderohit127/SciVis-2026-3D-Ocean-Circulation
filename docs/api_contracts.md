# THALASSA API Contracts

Updated as endpoints stabilize. Reflects actual implementation, not the PRD sketch.
Source schemas: `thalassa/backend/api/schemas.py`.

## Versioning

All responses carry `metric_version` string. Cached items are keyed by this version.
Current: `v0.1.0`

---

## GET /api/metadata

Returns dataset description, variable list, grid dimensions, timestep range, and region presets.

**Status:** Implemented (stub). Week 1–2: replace with live OpenVisus introspection.

**Response:**
```json
{
  "dataset": "ECCO LLC4320",
  "metric_version": "v0.1.0",
  "variables": [
    { "name": "theta", "units": "°C", "description": "Potential temperature", "url": "pelican://..." },
    { "name": "salt",  "units": "psu", "description": "Practical salinity",    "url": "pelican://..." },
    { "name": "w",     "units": "m/s", "description": "Vertical velocity",     "url": "pelican://..." }
  ],
  "grid": { "nx": 12960, "ny": 17280, "nz": 90 },
  "timesteps": { "count": 10312, "start": "2011-09-10T00:00:00Z", "end": "2012-11-15T00:00:00Z", "interval_hours": 1 },
  "depth_levels": 90,
  "regions": {
    "north_atlantic": { "lat": [0.0, 70.0], "lon": [-60.0, 0.0] },
    "southern_ocean":  { "lat": [-90.0, -30.0], "lon": [-180.0, 180.0] },
    "equatorial":      { "lat": [-15.0, 15.0],  "lon": [-180.0, 180.0] }
  }
}
```

---

## GET /health

**Status:** Implemented.

**Response:** `{ "status": "ok", "version": "0.1.0" }`

---

*Additional endpoints documented here as implemented per PRD §6.5.*

Planned (Weeks 3–6):
- `POST /api/overview`
- `POST /api/roi/query`
- `POST /api/derived/density`
- `POST /api/scene/isopycnal`
- `POST /api/phase-space`
- `POST /api/features/events`
- `POST /api/features/embedding`
- `POST /api/export/state`
- `WS /api/progress`
