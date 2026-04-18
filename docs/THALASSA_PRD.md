<!--
Source of truth for the THALASSA project (IEEE SciVis Contest 2026 Task 3).
When this document and any other guidance (chat messages, CLAUDE.md, README, etc.)
disagree, this document wins. Do not modify without explicit approval from Rohit.
-->

**THALASSA**

**Product Requirements Document and Research-Oriented Implementation Plan
for IEEE SciVis Contest 2026 Task 3**

*Project thesis: a multiscale visual analytics system for density-driven ocean circulation in ECCO LLC4320*

Prepared as a contest-first but publication-minded plan.
Front end: React + TypeScript. Backend: Python/FastAPI + OpenVisus.
This document deliberately treats React as the orchestration shell, not the technical contribution.

| Contest focus | Task 3: 3D ocean circulation with depth using temperature, salinity, and vertical velocity |
| --- | --- |
| Strategic position | Research-grade visual analytics system, not a generic dashboard |
| Primary novelty | Density-derived feature modeling + linked thermohaline phase space + progressive petascale streaming |
| Submission target | Competitive SciVis entry with a credible pathway to workshop / paper framing |

**Blunt assessment:** A React dashboard by itself will not place well. The contest language, the dataset scale, and the structure of past winners all point in the same direction: the front end must expose genuinely new analysis abstractions, progressive data access, and domain-specific derived features.

# 1. Executive summary

The 2026 SciVis Contest is not asking for a pretty ocean dashboard. It is asking for advanced visualization methods over petascale climate data, and the Task 3 wording is intentionally open enough that a strong entry should define its own analysis abstractions rather than stop at the literal prompt. Task 3 asks participants to use ECCO LLC4320 temperature, salinity, and vertical velocity to visualize 3D ocean circulation and highlight thermohaline circulation. The scientific difficulty is that thermohaline circulation is not directly encoded as a full vector field in the provided task variables. Therefore the project must infer and expose density-driven structure through derived fields, water-mass analysis, and linked spatial/phase-space views.

The recommended project is THALASSA: a multiscale visual analytics system that combines progressive streaming from OpenVisus, equation-of-state based density derivation, thermohaline contribution decomposition, linked temperature-salinity-density phase space, 3D isopycnal and vertical-exchange views, and time-navigation based on feature summaries. This design fits the contest, is technically serious enough to write up, and stays inside the stack you want: React on the client, Python in the backend, with Redis/Celery or equivalent middleware.

* **Core thesis:** replace map-centric exploration with density-centric, water-mass-aware exploration.
* **Core contribution 1:** progressive petascale query planning over ECCO OpenVisus data.
* **Core contribution 2:** derived thermohaline metrics from temperature, salinity, depth, and vertical velocity.
* **Core contribution 3:** linked geographic 3D view and temperature-salinity-density phase space.
* **Core contribution 4:** event-based and embedding-based time navigation over more than ten thousand hourly timesteps.
* **Primary target user:** ocean or climate researchers who need to move from global overview to local explanation without downloading absurd amounts of data.

# 2. Contest analysis and implications

## 2.1 What the contest actually rewards

* The contest explicitly asks for innovative visualization techniques that go beyond simple maps, and it encourages interactive tool development rather than static imagery alone.
* Participants are not required to follow the listed tasks literally. Creative but technically strong directions that leverage the provided datasets are explicitly encouraged.
* The official submission is not the app alone. It is a compact research-style package: a 3–4 page paper, images, and up to a 10-minute demonstration video.
* A strong submission must therefore optimize for paper-worthy contributions, memorable system footage, and a coherent analytical narrative.

## 2.2 Task 3-specific reading

Task 3 is brief on purpose. It says to use W, theta, and salinity to visualize 3D ocean circulation patterns and highlight major circulation systems such as thermohaline circulation. That wording creates a gap between the literal input variables and the intended physical phenomenon. A weak team will treat that as a limitation and show slices plus some volume rendering. A strong team will treat that gap as the research opportunity.

* **Key challenge:** thermohaline circulation is density-driven, but density is not given directly; it must be derived from temperature, salinity, and pressure/depth.
* **Key challenge:** the dataset is too large for brute-force interaction; every serious solution needs progressive access, summarization, and caching.
* **Key challenge:** W provides only vertical velocity. So the project should emphasize vertical exchange, dense water formation, stratification, and water-mass transformation rather than pretend it has a full 3D velocity field.
* **Opportunity:** because the task is underspecified, a method-heavy response can stand out more than a polished but generic front end.

## 2.3 What this means for scope

* Do not spread effort across all contest tasks. Task 3 alone is large enough to support a top-tier project.
* Do not waste early weeks on generic UI polish, mobile support, or fancy theming. The first hard milestone is a working derived-field pipeline over streamed ROI queries.
* Do not promise direct circulation streamlines from nonexistent horizontal velocity. Build your story around density structure, water masses, overturning, stratification, and vertical exchange.
* Do not frame the project as a dashboard. Frame it as a visual analytics system with a web interface.

# 3. Lessons from past winners

The three attached winner papers point to a consistent winning pattern. None of them won because they merely displayed raw fields. They won because they coupled domain-specific feature extraction, aggressive data preparation, and coordinated analytical workflows.

**Pattern extraction from the attached 2022–2024 winner papers**

| Winner | What they actually did | What matters for your project |
| --- | --- | --- |
| 2022 wildfire | Overview-to-detail analytical workflow, similarity plots, flow integration, volume rendering, and even ML-based simulation prediction. | A winning entry can include analysis abstractions and predictive or summarization layers, not just direct visualization. |
| 2023 VisAnywhere | Reorganized massive data for web delivery, reduced per-view payloads, used a single web codebase, and linked 2D/3D/multidevice views. | Web delivery is acceptable at the highest level only when backed by ruthless preprocessing and thoughtful system architecture. |
| 2024 PlumeViz | Built domain-specific features such as centerlines, gradients, ROI workflows, interpolation, and multifaceted exploration. | Domain-aware derived features are non-negotiable. The raw scalar field is only the substrate. |
| Common denominator | Each project transformed raw data into user-facing analytical objects. | Your equivalent analytical objects should be density surfaces, water masses, stratification metrics, and vertical-exchange events. |

## 3.1 Transferable principles

* Precompute and reorganize data before you obsess over UI.
* Expose derived features, not just original variables.
* Support a clear analytical ladder: global overview -> candidate selection -> local explanation -> comparative validation.
* Include at least one technically distinctive method that can become the paper hook.
* Validate with a real domain expert if at all possible.

# 4. Proposed project concept

## 4.1 Name and positioning

Project name: THALASSA — A multiscale visual analytics system for density-driven ocean circulation in ECCO LLC4320.

One-sentence pitch: THALASSA lets researchers explore thermohaline structure in petascale ocean simulations through progressive streaming, density-derived features, linked temperature-salinity phase space, 3D isopycnal exploration, and event-centric temporal navigation.

## 4.2 Paper-worthy technical contributions

* **Contribution A:** task-adaptive progressive query planning over OpenVisus IDX data, including fast previews, prioritized refinement, and ROI-aware caching.
* **Contribution B:** thermohaline decomposition layer that derives density, thermal and haline density contributions, compensation index, and stratification measures from temperature/salinity/depth.
* **Contribution C:** dual-domain analytics that link geographic 3D space to temperature-salinity-density phase space and back again through brushing and selection.
* **Contribution D:** temporal state navigation using per-timestep feature descriptors and embeddings so users can find regimes, transitions, and anomalies among more than ten thousand hours of output.
* **Contribution E (stretch):** persistent vertical-exchange event detection and tracking using connected 3D regions defined by strong vertical motion and unstable or weakly stable stratification.

## 4.3 Scope boundaries

* Primary focus is desktop and laptop. Responsive layout is useful, but phone-first design is not a core research objective.
* No VR in version 1. That would be scope theater unless the core analytical system is already excellent.
* No attempt to render full-resolution global volumes directly in the browser.
* No unsupported scientific claims about full 3D current trajectories from incomplete velocity data.

# 5. Product requirements document

## 5.1 Problem statement

Researchers need to inspect thermohaline structure in an ocean simulation whose raw volume, temporal span, and depth complexity make direct manual exploration impractical. Conventional ocean dashboards default to maps, slices, and static scalar overlays, which are not enough to understand density-driven exchange, water-mass separation, or the interaction between temperature, salinity, and vertical motion across depth. THALASSA must turn raw variables into interpretable analytical objects while preserving interactive response times over web delivery.

## 5.2 Target users

| Persona | Needs | Why they matter |
| --- | --- | --- |
| Ocean / climate researcher | Identify dense water formation, sinking regions, stratification changes, and water-mass patterns over time. | Primary scientific user and strongest source of evaluation credibility. |
| Visualization researcher / contest judge | See a coherent technical method, not just pretty pictures. | The contest is judged on novelty, clarity, and technical execution. |
| Advanced student or analyst | Learn where and why interesting structures appear and generate publishable figures. | Secondary user; useful for reproducibility and educational impact. |

## 5.3 User goals and scientific questions

* Where are the dominant regions of dense-water formation, sinking, and upwelling?
* At a selected location and depth range, is density variation primarily temperature-driven or salinity-driven?
* Which water masses occupy a selected region, and how do they move or transform over time in temperature-salinity-density space?
* Where does strong vertical motion coincide with weak or unstable stratification?
* Which timesteps or periods are anomalous relative to the rest of the 14-month simulation?
* How do basin-scale signatures differ between the North Atlantic, Southern Ocean, equatorial regions, and other regions of interest?

## 5.4 Core user workflow

1. Start from a coarse global overview that summarizes density anomaly, vertical exchange score, or water-mass occupancy by basin and depth band.
2. Use the timeline or state-embedding view to choose an interesting regime or anomaly.
3. Select a basin, bounding box, or known circulation zone to open a local 3D analysis lens.
4. Inspect linked views: 3D isopycnals, vertical curtain, temperature-salinity-density phase space, and local quantitative distributions.
5. Brush a water-mass cluster or phase-space region and see the corresponding spatial voxels highlighted in the 3D view.
6. Adjust thresholds, isopycnal values, and depth ranges to refine hypotheses.
7. Save snapshots, annotations, and story bookmarks for the final paper and video.

## 5.5 Functional requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | Progressive global overview maps and coarse summaries across time and depth. | Must | Fast first impression is essential because the raw data are too large. |
| FR-2 | ROI selection by basin preset, bounding box, and depth range. | Must | This is the gateway to every detailed query. |
| FR-3 | Derive density and selected stability metrics from temperature, salinity, and depth. | Must | Without this, the system has no thermohaline story. |
| FR-4 | 3D isopycnal rendering for local ROIs with color encoding by temperature, salinity, compensation, or vertical motion. | Must | Primary 3D analytical view. |
| FR-5 | Linked temperature-salinity-density phase-space view with density contours and brush-back to geographic voxels. | Must | This is the strongest differentiator from a normal dashboard. |
| FR-6 | Vertical curtain or profile view along latitude, longitude, or transect. | Must | Needed to understand depth structure. |
| FR-7 | Temporal navigation through embedding, anomaly timeline, or ranked events. | Must | Users cannot scrub blindly through 10k+ timesteps. |
| FR-8 | Vertical-exchange event detection and ranking. | Should | Good technical hook; can start coarse. |
| FR-9 | Comparative mode for two times, regions, or basins. | Should | Important for analysis and paper figures. |
| FR-10 | Snapshot, annotation, and bookmark export. | Must | Needed for the contest manuscript and video. |
| FR-11 | Session restore and sharable state URLs. | Should | Useful if you work with collaborators or domain experts. |
| FR-12 | Multiuser collaboration / synchronized views. | Stretch | Not needed unless the core system is already excellent. |

## 5.6 Derived variables and analytical objects

| Object / Metric | Definition | Why it matters |
| --- | --- | --- |
| Potential or in-situ density anomaly | Equation-of-state derived from temperature, salinity, and pressure/depth. | Thermohaline circulation is fundamentally density-driven. |
| Thermal density contribution | Approximate density contribution from temperature via thermal expansion coefficient. | Separates temperature-driven from salinity-driven effects. |
| Haline density contribution | Approximate density contribution from salinity via haline contraction coefficient. | Same reason; enables explanatory comparisons. |
| Compensation index | Measures where thermal and haline effects offset one another. | Useful for identifying visually deceptive regions where temperature and salinity compensate. |
| Stratification metric | Density gradient or Brunt-Vaisala-like stability estimate. | Helps explain whether vertical motion occurs in stable or unstable water columns. |
| Vertical exchange score | Composite metric combining |w| with stability / density structure. | Turns vertical motion into a navigable event field. |
| Water-mass clusters | Unsupervised groups in temperature-salinity-density-depth space. | Provides a user-facing abstraction over raw voxels. |
| Time-step state descriptor | Histogram or signature vector summarizing thermohaline structure at a timestep. | Enables anomaly ranking and temporal embedding. |

## 5.7 Views and screen architecture

Recommended desktop layout: one application with coordinated panes, not separate disconnected pages.

| Pane | Purpose | Implementation hint |
| --- | --- | --- |
| A. Global overview map | Select basin/ROI and show coarse derived fields over the globe. | MapLibre + server-generated rasters or deck.gl layers. |
| B. 3D local exploration | Show isopycnals, selected surfaces, and ROI context. | vtk.js with server-generated meshes and optional low-res volume textures. |
| C. T-S-density phase space | Inspect water masses and brush regions back to space. | Plotly or custom WebGL scatter/hexbin. |
| D. Vertical section / curtain | Explain depth variation and stratification along a line. | Canvas/WebGL heatmap; optionally server raster. |
| E. Timeline / state embedding | Navigate seasonal change, anomalies, and detected events. | Scatter/line chart with linked highlighting. |
| F. Parameter and story panel | Thresholds, presets, bookmarks, export. | Standard React side panel. |

## 5.8 Non-functional requirements

| Category | Target |
| --- | --- |
| Initial global preview latency | < 1.5 s for coarse summaries and raster previews under normal network conditions. |
| ROI derived-query latency | < 3 s for moderate ROI at preview quality; progressive refinement may continue afterward. |
| Client interaction | Smooth brushing/panning/selection once data are loaded; avoid browser lockups. |
| Scientific reproducibility | Derived metrics must be deterministic, versioned, and exportable with metadata. |
| Traceability | Any figure used in the paper or video must be reproducible from a saved state or notebook. |
| Scalability | System must remain usable without loading full global fields at full resolution into memory. |
| Robustness | Graceful fallback from volume mode to surface/slice mode when bandwidth or memory is constrained. |

## 5.9 Success metrics

* A domain user can move from global overview to a physically interpretable local explanation in under 3 minutes without external scripts.
* The system consistently produces at least 6–8 paper-quality figures and 3–4 strong video sequences.
* You can demonstrate one clearly novel analytical capability that cannot be reduced to a standard map or slice viewer.
* You can articulate a paper claim that is methodological, not merely presentational.
* You complete at least one case study and one lightweight expert walkthrough before the contest deadline.

# 6. Technical architecture

## 6.1 Recommended stack

| Layer | Choice | Why this choice |
| --- | --- | --- |
| UI shell | React + TypeScript + Vite | Fast iteration, strong state management ecosystem, easy composition of linked views. |
| Client state | Zustand or Redux Toolkit + TanStack Query | Separates UI state from server query state cleanly. |
| 2D geospatial view | MapLibre GL JS and or deck.gl | Useful for ROI selection and coarse field overlays. |
| 3D rendering | vtk.js for surfaces, slices, and optional volume mode | Better fit for scientific geometry and scalar rendering than plain chart libraries. |
| Charts / analytics views | Plotly or D3/Observable Plot | Good support for linked brushing and phase-space views. |
| Backend API | FastAPI + Uvicorn/Gunicorn | Clean async Python service layer. |
| Data access | OpenVisus / openvisuspy | Matches the official contest distribution format and progressive streaming workflow. |
| Scientific compute | NumPy, xarray, Numba, GSW / TEOS-10, scikit-image, scikit-learn | Covers derived metrics, meshing, clustering, and summarization. |
| Heavy async jobs | Celery or RQ with Redis | Needed for event detection, ROI precompute, and mesh generation. |
| Metadata / summary store | DuckDB + Parquet | Excellent for compact analytical summaries and offline pipelines. |
| Object cache | Redis and optionally MinIO / S3-compatible storage | Cache meshes, previews, and precomputed summaries. |
| Reverse proxy / deployment | Nginx + Docker Compose initially | Enough unless you outgrow a single-node deployment. |

## 6.2 Architectural principle: React is the control plane, not the compute plane

This is the most important stack decision. React should manage coordination, layout, state, and interaction logic. It should not be responsible for heavyweight scientific computation or naive client-side handling of massive volumes. The real system value lives in the backend query planner, derived-field engine, and scene-generation pipeline.

## 6.3 Data flow

1. Client requests a global or ROI view with time, depth range, region, and quality budget.
2. FastAPI forwards the request to a query planner that estimates payload size and chooses a coarse OpenVisus quality level first.
3. Backend fetches raw subvolumes or summary statistics from OpenVisus.
4. Derived-field engine computes density, contribution metrics, and selected analytical features.
5. If a 3D scene is requested, backend extracts meshes or downsampled textures and caches them.
6. Client receives a fast preview first, then refinement updates over HTTP polling or WebSocket push.
7. All final user-visible states are serializable for export and paper reproducibility.

## 6.4 Core backend services

| Service | Responsibilities |
| --- | --- |
| Metadata service | Variables, depth levels, basin presets, value ranges, available timesteps, and cached summaries. |
| Query planner | Estimate ROI cost, choose OpenVisus quality, prioritize refinement, and route to caches. |
| Derived metrics engine | Density, thermal / haline contribution, compensation index, stratification, vertical exchange score. |
| Scene service | Generate isopycnal meshes, sliced rasters, decimated polydata, and optional volume textures. |
| Feature service | Water-mass clustering, event detection, event ranking, temporal descriptors, and embeddings. |
| Export service | Snapshot metadata, high-resolution figure generation, and JSON state serialization. |

## 6.5 API surface (first pass)

| Endpoint | Purpose |
| --- | --- |
| GET /api/metadata | Available variables, depth levels, basins, timesteps, presets. |
| POST /api/overview | Coarse global or basin-level summaries for selected metric/time/depth. |
| POST /api/roi/query | Return preview subvolume statistics or slices for a selected ROI. |
| POST /api/derived/density | Compute density-related fields for a ROI. |
| POST /api/scene/isopycnal | Extract one or more isopycnal surfaces with color encodings. |
| POST /api/phase-space | Temperature-salinity-density histogram or sampled scatter for current selection. |
| POST /api/features/events | Ranked vertical-exchange events for a time range or basin. |
| POST /api/features/embedding | Low-dimensional embedding of per-timestep state descriptors. |
| POST /api/export/state | Save shareable state and figure metadata. |
| WS /api/progress | Push progressive refinement and long-job updates. |

## 6.6 Data model and transfer strategy

* Tabular summaries: Arrow IPC or JSON for smaller payloads; Parquet for offline storage.
* 2D rasters: PNG / WebP or raw arrays depending on interaction frequency.
* 3D geometry: glTF or vtk.js-compatible polydata, optionally compressed.
* Small ROI voxel textures: quantized Uint16 or Float32 arrays only when needed.
* Long-running jobs: store results under content-addressed cache keys derived from ROI, time, depth, metric, and quality.

# 7. Novel analytical methods to implement

## 7.1 Thermohaline contribution decomposition

This should be the scientific heart of the system. Compute seawater density from temperature, salinity, and pressure/depth using a TEOS-10 compatible implementation. Then derive local thermal and haline contributions so users can ask not only where dense water occurs, but why it is dense. This is far more informative than plotting temperature and salinity separately.

* Output fields: density, density anomaly, thermal contribution, haline contribution, compensation index.
* Visual encoding: bivariate legend or switchable overlays so users can distinguish temperature-dominated from salinity-dominated regions.
* Use case: identify cold-driven sinking vs salt-driven sinking and regions where T and S cancel each other.

## 7.2 Linked T-S-density phase space

A normal dashboard shows maps and maybe a time slider. That is not enough. The project needs a second analytical domain: temperature-salinity-density space. This phase-space view becomes the bridge between water masses and geography.

* Plot sampled points or hexbin density in temperature-salinity space, optionally faceted or colored by density or depth band.
* Overlay selected isopycnal contours.
* Brush a region in phase space to highlight corresponding spatial voxels in the 3D view.
* Support cluster discovery in this space using HDBSCAN or a simpler density-based alternative.

## 7.3 Event-based vertical exchange detection

W by itself is noisy and easy to misuse. Convert it into candidate analytical events by combining strong vertical motion with density structure. The event detector can operate first at coarse resolution. That is enough to build a ranked list of interesting timesteps and regions.

* Candidate score example: |w| times a function of weak or unstable stratification.
* Find connected 3D regions above threshold.
* Track regions through time by overlap or centroid matching.
* Rank by persistence, integrated score, depth span, and spatial footprint.

## 7.4 Temporal state embedding

You cannot ask a user to drag a slider through 10,312 hourly timesteps and call that analysis. Build a time-navigation layer. Each timestep should have a descriptor vector such as basin-stratified histograms in temperature-salinity-density space plus vertical motion statistics. Then build a 2D embedding or anomaly score. This becomes the user’s navigation map over time.

# 8. Detailed implementation plan

## 8.1 Phase plan aligned to the contest timeline

| Weeks | Phase | Output |
| --- | --- | --- |
| 1-2 | Architecture and feasibility lock | OpenVisus access verified, depth mapping confirmed, derived density prototype on small ROI, tech stack frozen. |
| 3-4 | Backend foundation | FastAPI service, query planner skeleton, Redis cache, metadata endpoints, ROI fetch API. |
| 5-6 | Core derived fields | Density pipeline, contribution decomposition, basic vertical stability metrics, reproducible notebooks. |
| 7-8 | Primary linked views | Global overview map, 3D local view, vertical curtain, T-S phase-space view with brushing. |
| 9-10 | Time navigation and events | Per-timestep descriptors, anomaly ranking, temporal embedding, first event detector. |
| 11-12 | Performance hardening and figure design | Caching, decimation, progressive refinement, paper-quality figure presets, export tools. |
| 13 | Case studies | North Atlantic and Southern Ocean walkthroughs, plus one additional regional story. |
| 14 | Expert review and ablations | At least one expert walkthrough, bug fixes, feature pruning, messaging cleanup. |
| 15 | Submission production | 3–4 page paper, appended figures, final video, backup demo build. |

## 8.2 Workstream breakdown

### Workstream A: Data and backend

* Implement OpenVisus wrappers for ROI/time/depth queries.
* Create pressure-from-depth and density computation utilities.
* Build metric cache keys and invalidation strategy.
* Precompute coarse per-timestep descriptors to avoid online full-dataset scans.
* Implement mesh extraction and decimation utilities for isopycnal scenes.

### Workstream B: Front-end analytics

* Design interaction model and state graph before polishing components.
* Implement linked selections across map, 3D, phase space, and timeline.
* Add loading states that show progressive refinement honestly; do not fake precision.
* Build a saved-view system for bookmarks and exportable figure states.

### Workstream C: Research and validation

* Define 2–3 concrete scientific case studies before the interface is finished.
* Run accuracy checks for density and derived metrics on sampled ROIs.
* Benchmark latency and payload sizes for typical interactions.
* Get feedback from one oceanography-adjacent person even if informal.

## 8.3 Must-have vs stretch scope

| Category | Must-have | Stretch |
| --- | --- | --- |
| Data access | ROI query pipeline and progressive preview | Advanced prefetch heuristics and speculative caching |
| Derived fields | Density, contribution decomposition, stability metric | Double-diffusion diagnostics, spiciness, neutral-density extras |
| Views | Map + 3D + T-S phase space + timeline + curtain | Extra small multiples, collaboration mode, dual monitor presets |
| Feature analytics | Simple event ranking and anomaly timeline | Full persistent tracking with rich event genealogy |
| Output | Snapshots, bookmarks, reproducible states | Automated story generation or narrated tour mode |

## 8.4 Concrete engineering tasks

1. Create a small command-line prototype that fetches a single ROI for theta, salt, and w from OpenVisus at two quality levels.
2. Add density computation and verify values across several depth levels.
3. Compute one experimental compensation map and one isopycnal mesh for a known region.
4. Expose those results through a minimal FastAPI endpoint.
5. Build a React page that shows the 3D view plus a T-S plot for the same ROI.
6. Implement linked brushing between the T-S plot and the spatial view.
7. Add a coarse timeline summary and event ranking for a restricted region and time window.
8. Only after these work end to end should you start broader UI polish and export tooling.

# 9. Evaluation plan

## 9.1 Technical evaluation

* Latency benchmark for global preview queries.
* Latency benchmark for ROI-derived-field queries at multiple quality levels.
* Mesh size and transfer size benchmark for isopycnal scenes.
* Browser memory and frame-rate profiling on a representative laptop.
* Cache hit-rate measurement during repeated analytical workflows.

## 9.2 Analytical evaluation

* Case study 1: North Atlantic dense water formation and sinking signature.
* Case study 2: Southern Ocean deep and bottom water related structures.
* Case study 3: equatorial or regional upwelling zone where vertical motion dominates.
* Compare the explanatory value of raw temperature/salinity views versus density-contribution views.

## 9.3 User evaluation

* At minimum, conduct one or two informal domain-expert walkthroughs.
* Prepare concrete tasks, for example: identify a region where salinity rather than temperature is the dominant density driver.
* Record whether the linked phase-space view actually helps users explain what they see in the 3D view.
* Collect comments that can be quoted or paraphrased in the final paper and video.

# 10. Risks and mitigation

| Risk | Why it matters | Mitigation |
| --- | --- | --- |
| Overbuilding the front end | Easy to spend weeks on UI chrome while the scientific core remains weak. | Freeze UI ambition early; backend-derived features first. |
| Data access bottlenecks | OpenVisus queries can become the critical path. | Coarse-first strategy, ROI-limited queries, persistent caches, precomputed summaries. |
| Scientific overclaim | You do not have full velocity vectors in Task 3. | Use careful language: density-driven structure, vertical exchange, water masses, inferred thermohaline patterns. |
| Browser overload | 3D volumes and huge geometries will kill interactivity. | Surface-first design, mesh decimation, slice fallback, avoid full global volumes. |
| No expert feedback | Weakens credibility and final paper framing. | Find one oceanography student, faculty member, or adjacent researcher early. |
| Trying to do everything | Classic contest failure. | Enforce must-have scope and cut stretch goals aggressively by week 10. |

# 11. Submission strategy

## 11.1 Paper framing

* Lead with the methodological problem: thermohaline structure is not directly visible in the raw task variables.
* Present THALASSA as a density-centric visual analytics system for petascale ocean data.
* Organize the paper around contributions, not around screens.
* Use two case studies plus one concise performance table.
* Include one figure that shows linked geographic and phase-space analysis side by side; that is your signature image.

## 11.2 Video structure

1. Start with the challenge: 10k+ hourly timesteps, 90 depth levels, huge 3D fields, and incomplete direct circulation variables.
2. Show the global overview and time embedding to prove scale handling.
3. Drill into a case study and reveal density contribution decomposition.
4. Use linked brushing between T-S space and 3D geography as the central wow moment.
5. End with event ranking and export/bookmark workflow to show analytical maturity.

# 12. Final recommendations

* Keep React, but demote it to orchestration. The research contribution belongs in the dataflow, derived metrics, and analysis model.
* Build the density pipeline before you build the dashboard.
* Use the winner papers as precedent for domain-specific feature extraction and aggressive preprocessing, not as permission to make something flashy but shallow.
* Your minimum viable winning system is: progressive ROI access, density decomposition, linked T-S and 3D views, and time navigation. Everything else is secondary.
* If you execute that core well and validate it with at least one believable case study, you will have something that looks like real visualization research instead of a student project demo.

# Appendix A. Suggested repository structure

| Path | Purpose |
| --- | --- |
| frontend/ | React application, linked views, state management, export UI. |
| backend/api/ | FastAPI routers and request schemas. |
| backend/services/ | Query planning, metrics computation, scene generation, event analytics. |
| backend/workers/ | Celery or RQ jobs for heavy async tasks. |
| backend/tests/ | Metric correctness, cache logic, API contracts. |
| pipelines/ | Offline precompute scripts for descriptors, events, and summaries. |
| notebooks/ | Exploratory notebooks and paper figure reproducibility notebooks. |
| docs/ | Architecture notes, API contracts, case study logs, manuscript figures. |

# Appendix B. Source basis used for this plan

Official contest pages: tasks, data, examples, FAQ, and submission instructions on sciviscontest2026.github.io.
Attached winner papers: 2022 wildfire winner article, 2023 VisAnywhere article, and 2024 PlumeViz article.
Supporting oceanography references for density and ECCO context: TEOS-10 / GSW documentation, NASA ECCO pages, and official or peer-reviewed LLC4320 descriptions.
