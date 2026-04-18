"""Metadata endpoint — describes the LLC4320 dataset to the frontend."""

from fastapi import APIRouter

from api.schemas import GridInfo, MetadataResponse, RegionPreset, TimestepInfo, Variable

router = APIRouter()

# Stub metadata — Week 1-2 task: replace with live OpenVisus introspection.
_METADATA = MetadataResponse(
    dataset="ECCO LLC4320",
    metric_version="v0.1.0",
    variables=[
        Variable(
            name="theta",
            units="°C",
            description="Potential temperature",
            url="pelican://osg-htc.org/nasa/nsdf/climate1/llc4320/idx/theta/theta_llc4320_x_y_depth.idx",
        ),
        Variable(
            name="salt",
            units="psu",
            description="Practical salinity",
            url="pelican://osg-htc.org/nasa/nsdf/climate1/llc4320/idx/salt/salt_llc4320_x_y_depth.idx",
        ),
        Variable(
            name="w",
            units="m/s",
            description="Vertical velocity",
            url="pelican://osg-htc.org/nasa/nsdf/climate2/llc4320/idx/w/w_llc4320_x_y_depth.idx",
        ),
    ],
    grid=GridInfo(nx=12960, ny=17280, nz=90),
    timesteps=TimestepInfo(
        count=10312,
        start="2011-09-10T00:00:00Z",
        end="2012-11-15T00:00:00Z",
        interval_hours=1,
    ),
    depth_levels=90,
    regions={
        "north_atlantic": RegionPreset(lat=[0.0, 70.0], lon=[-60.0, 0.0]),
        "southern_ocean": RegionPreset(lat=[-90.0, -30.0], lon=[-180.0, 180.0]),
        "equatorial": RegionPreset(lat=[-15.0, 15.0], lon=[-180.0, 180.0]),
    },
)


@router.get("/metadata", response_model=MetadataResponse)
async def get_metadata() -> MetadataResponse:
    """Return dataset metadata: variables, grid dimensions, timestep range, and basin presets."""
    return _METADATA
