"""Shared Pydantic schemas for THALASSA API responses."""

from pydantic import BaseModel


class Variable(BaseModel):
    name: str
    units: str
    description: str
    url: str


class GridInfo(BaseModel):
    nx: int
    ny: int
    nz: int


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
