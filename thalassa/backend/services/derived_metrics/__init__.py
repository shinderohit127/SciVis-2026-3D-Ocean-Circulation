"""
Derived metrics engine — skeleton.

Responsibilities (Weeks 5-6):
- Density via gsw.rho(SA, CT, p) using TEOS-10.
  LLC4320 delivers practical salinity (SP) and potential temperature (pt);
  convert with gsw.SA_from_SP and gsw.CT_from_pt before calling rho.
- Thermal density contribution (alpha * dT).
- Haline density contribution (beta * dS).
- Compensation index (where thermal and haline effects offset each other).
- Stratification metric: N² or vertical density gradient.

All outputs must be deterministic and carry metric_version metadata (PRD §5.8).
"""
