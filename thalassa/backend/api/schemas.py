"""Shared Pydantic schemas for THALASSA API responses."""

from typing import Optional

from pydantic import BaseModel, field_validator, model_validator


# ── Metadata endpoint (Week 1-2) ──────────────────────────────────────────────

class Variable(BaseModel):
    name: str
    units: str
    description: str
    url: str


class GridInfo(BaseModel):
    nx: int   # longitude pixels (NX = 17280)
    ny: int   # latitude pixels  (NY = 12960)
    nz: int   # depth levels     (NZ = 90)


class TimestepInfo(BaseModel):
    count: int
    start: str
    end: str
    interval_hours: int


class RegionPreset(BaseModel):
    lat: list[float]
    lon: list[float]


class MetadataResponse(BaseModel):
    dataset: str
    metric_version: str
    variables: list[Variable]
    grid: GridInfo
    timesteps: TimestepInfo
    depth_levels: int
    regions: dict[str, RegionPreset]


# ── ROI query and derived metrics (Week 3-4) ──────────────────────────────────

class ROIRequest(BaseModel):
    """Geographic region of interest for a THALASSA query."""
    lat_min: float
    lat_max: float
    lon_min: float           # degrees, any convention (-180/180 or 0/360)
    lon_max: float
    depth_min_m: float = 0.0
    depth_max_m: float = 6625.0
    timestep: int = 0        # 0-based hourly index (0 = Sep 10 2011 00:00 UTC)
    quality: int = -6        # OpenVisus quality: -15 coarse → 0 full resolution

    @field_validator("quality")
    @classmethod
    def quality_nonpositive(cls, v: int) -> int:
        if v > 0:
            raise ValueError("quality must be ≤ 0 (0 = full resolution, negative = coarser)")
        return v

    @model_validator(mode="after")
    def ranges_valid(self) -> "ROIRequest":
        if self.lat_min >= self.lat_max:
            raise ValueError("lat_min must be < lat_max")
        if self.depth_min_m >= self.depth_max_m:
            raise ValueError("depth_min_m must be < depth_max_m")
        return self


class QueryPlanInfo(BaseModel):
    recommended_quality: int
    estimated_mb: float
    capped: bool    # True if quality was downgraded to stay under 200 MB
    notes: str


class VariableStats(BaseModel):
    min: float
    max: float
    mean: float
    std: float
    ocean_fraction: float   # fraction of non-zero (non-land) pixels


class QueryStats(BaseModel):
    """Response from POST /api/roi/query."""
    roi: ROIRequest
    query_plan: QueryPlanInfo
    shape: dict[str, int]               # {"nz": ..., "ny": ..., "nx": ...}
    variables: dict[str, VariableStats]
    surface_slices: dict[str, list]     # field → 2D list (shallowest z level)
    elapsed_ms: int


class FieldStats(BaseModel):
    min: float
    max: float
    mean: float
    std: float
    surface_slice: list     # 2D list (shallowest z level of the fetched ROI)


class DensityRequest(BaseModel):
    """Request body for POST /api/derived/density."""
    roi: ROIRequest
    include: list[str] = [
        "rho", "sigma0", "rho_thermal", "rho_haline", "compensation_index",
    ]


class DensityResponse(BaseModel):
    """Response from POST /api/derived/density."""
    roi: ROIRequest
    fields: dict[str, FieldStats]
    metric_version: str
    elapsed_ms: int


# ── Overview endpoint (Week 5-6) ──────────────────────────────────────────────

_VALID_BASINS  = {"north_atlantic", "southern_ocean", "equatorial"}
_VALID_METRICS = {"sigma0", "compensation_index", "vertical_exchange", "rho_thermal", "rho_haline"}


class OverviewRequest(BaseModel):
    """Request body for POST /api/overview."""
    basin: str = "north_atlantic"
    timestep: int = 0
    metric: str = "sigma0"

    @field_validator("basin")
    @classmethod
    def basin_valid(cls, v: str) -> str:
        if v not in _VALID_BASINS:
            raise ValueError(f"basin must be one of {sorted(_VALID_BASINS)}")
        return v

    @field_validator("metric")
    @classmethod
    def metric_valid(cls, v: str) -> str:
        if v not in _VALID_METRICS:
            raise ValueError(f"metric must be one of {sorted(_VALID_METRICS)}")
        return v


class DepthBandSummary(BaseModel):
    band: str                   # "surface" | "thermocline" | "deep" | "abyss"
    depth_range: list[float]    # [z_lo, z_hi] metres
    mean_map: list              # 2D list (ny, nx) depth-mean metric values
    stats: dict[str, float]     # min, max, mean, std


class OverviewResponse(BaseModel):
    """Response from POST /api/overview."""
    basin: str
    metric: str
    timestep: int
    quality: int
    shape: dict[str, int]
    lats: list[float]
    lons: list[float]
    depth_bands: list[DepthBandSummary]
    elapsed_ms: int


# ── Vertical exchange endpoint (Week 5-6) ─────────────────────────────────────

class VerticalExchangeRequest(BaseModel):
    """Request body for POST /api/derived/vertical_exchange."""
    roi: ROIRequest
    n2_ref_s2: float = 1e-5   # N² reference threshold in s⁻²


class VerticalExchangeResponse(BaseModel):
    """Response from POST /api/derived/vertical_exchange."""
    roi: ROIRequest
    stats: dict[str, float]     # min, max, mean, std, p95
    surface_slice: list         # 2D list (shallowest z level)
    event_fraction: float       # fraction of voxels above 95th-percentile threshold
    metric_version: str
    elapsed_ms: int


# ── Scene / isopycnal endpoint (Week 5-6) ─────────────────────────────────────

class IsopycnalRequest(BaseModel):
    """Request body for POST /api/scene/isopycnal."""
    roi: ROIRequest
    sigma0_value: float
    color_by: Optional[str] = None          # "CT" | "SA" | "alpha" | "beta" | None
    target_faces: Optional[int] = None      # decimate to ≤ N faces; None = no decimation


# ── Benchmark (Week 11-12) ────────────────────────────────────────────────────

class BenchmarkRun(BaseModel):
    quality: int
    shape: dict[str, int]
    elapsed_ms: int
    estimated_mb: float
    note: str


class BenchmarkResponse(BaseModel):
    """Response from POST /api/benchmark."""
    roi: dict
    runs: list[BenchmarkRun]
    total_elapsed_ms: int


# ── Async job polling (Week 5-6) ──────────────────────────────────────────────

class JobStatus(BaseModel):
    """Response from GET /api/jobs/{job_id}."""
    job_id: str
    status: str               # "queued" | "running" | "complete" | "failed"
    result: Optional[dict] = None
    error: Optional[str] = None


# ── Temporal navigation (Week 9-10) ───────────────────────────────────────────

MAX_TIMESTEP = 10311   # LLC4320: 10,312 hourly steps (0-indexed)
MAX_WINDOW_SAMPLES = 200


class TemporalWindowRequest(BaseModel):
    """Request body for POST /api/temporal/window."""
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    depth_min_m: float = 0.0
    depth_max_m: float = 2000.0
    t_start: int = 0
    t_end: int = MAX_TIMESTEP
    n_samples: int = 50       # number of evenly-spaced timesteps to sample

    @field_validator("t_start", "t_end")
    @classmethod
    def timestep_range(cls, v: int) -> int:
        if not (0 <= v <= MAX_TIMESTEP):
            raise ValueError(f"timestep must be 0–{MAX_TIMESTEP}")
        return v

    @field_validator("n_samples")
    @classmethod
    def samples_cap(cls, v: int) -> int:
        return min(max(v, 2), MAX_WINDOW_SAMPLES)

    @model_validator(mode="after")
    def t_order(self) -> "TemporalWindowRequest":
        if self.t_start >= self.t_end:
            raise ValueError("t_start must be < t_end")
        return self


class TimestepDescriptor(BaseModel):
    """Thermohaline summary for one timestep."""
    timestep: int
    sigma0_mean: float
    sigma0_std: float
    ct_mean: float
    sa_mean: float
    anomaly_score: float   # |z-score| of sigma0_mean relative to the window


class TemporalWindowResponse(BaseModel):
    """Response from POST /api/temporal/window (returned via job result)."""
    t_start: int
    t_end: int
    n_computed: int
    descriptors: list[TimestepDescriptor]
    descriptor_version: str
