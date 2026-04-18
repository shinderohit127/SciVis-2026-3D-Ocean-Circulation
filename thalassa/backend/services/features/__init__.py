"""
Feature service — skeleton.

Responsibilities (Weeks 9-10):
- Water-mass clustering: HDBSCAN in temperature-salinity-density-depth space.
- Vertical-exchange event detection: connected 3D regions where |w| is high
  and stratification is weak or unstable.
- Per-timestep descriptor vectors: basin-stratified histograms + motion stats.
- 2D temporal embedding: UMAP or t-SNE over descriptor vectors.
"""
