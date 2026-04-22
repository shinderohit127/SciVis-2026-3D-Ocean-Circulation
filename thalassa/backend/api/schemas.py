"""Shared Pydantic schemas for THALASSA API responses."""

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
