# Previous project assessment

Source: `/Users/earthnaja/Documents/GitHub/Work - Earth/Project Work/Source Code/RoadAware_2rd`

Reviewed: 2026-11-09. Read-only inspection; no source files copied, modified, or executed.
This is a reuse assessment, not acceptance of the old application or its models.

## User intent

Build a new working route-planning web application that forecasts recorded accident
counts, shows colored route areas, and explains historical accident patterns and
relevant precautions. Consider departure date/time, weather, traffic, season and
holidays where supported. Use the previous project as a reference and selectively
reuse suitable assets, rather than adopting the old application wholesale.
Forecast horizon, geographic scope and spatial/temporal units remain undecided.

## Independently inspected evidence

- Streamed CSV records using Python csv.DictReader: accidents_cleaned.csv has
  124,353 data rows; accidents_cleaned_with_weather.csv also has 124,353 rows;
  road_segments/segments_2km.csv has 21,313 rows. Counts are records, not proof
  of distinct accidents. Inspected column headers; did not audit every value.
- app/app.js calls /api/hotspots; roadaware_hotspot_server.py dispatches to
  HotspotEngine. This frontend is connected to historical weighted hotspots,
  not the separate forecast API.
- roadaware_hotspots.py selects segment centers near route geometry and scores
  route slices using weighted historical rates. Nearby centers do not establish
  that accidents occurred on the same road or carriageway.
- roadaware_route_service.py exposes a separate daily-grid forecast service;
  capabilities explicitly disable hourly prediction and production. It uses
  a locked model bundle, coverage checks and optional registered forecasts.
- route_grid_mapping.py contains route/grid intersection and time allocation
  logic; candidate for reuse after focused verification.

## Candidates to retain or adapt

| Asset | Proposed treatment |
| --- | --- |
| data/raw/accidents and boundaries | Preserve source data and provenance; inspect raw schemas and coverage before import. |
| data/processed/accidents_cleaned.csv and quality reports | Starting reference for cleaning, dates, IDs, categories and lineage; revalidate before training. |
| Weather merge and weather reports | Useful retrospective analysis and matching logic; not future forecast weather. |
| scripts/build_prepared_latest.py and cleaning/audit scripts | Review individual transformations against confirmed definitions before selective reuse. |
| scripts/route_grid_mapping.py and associated tests | Candidate geometry component; verify coordinate system and assumptions for the new spatial unit. |
| scripts/roadaware_route_service.py and backend API | Reference for model provenance, missing coverage, input validation and API contracts. |
| app/ and historical hotspot scripts | UX/route display reference; historical scores must be labeled separately from forecasts. |
| Poisson/HGB artifacts and evaluation reports | Experimental benchmarks; do not adopt weights or performance claims without reproduction. |

## Findings reported by old documentation (not reverified here)

- Clean data covers 2564–2568 and January–August 2569. The latter lacks source
  accident IDs; documentation reports unresolved date issues and duplicates.
- Weather is ERA5-Land reanalysis matched at event time, not archived forecasts
  available before departure. Some raw weather files reference another project.
- Prototype forecasts use 5 km grid-day recorded counts, with a next-day issue
  schedule; road hotspot tables instead use 1 km / 2 km segments. These units
  cannot be treated as equivalent or made more precise by rendering small circles.
- Later HGB experiments use limited spatial scope; inspect the actual bundle
  before deciding coverage. Unknown areas must remain unknown.
- Validation was reused and the 2568 Test was previously examined. Old metrics
  are not an untouched evaluation for a newly tuned model.
- Forecast registry and independent route outcomes were not available in the
  reviewed reports. No evidence here establishes personal crash probability
  or a reduction in accidents from route recommendations.

## Verification limits and next decisions

No training, unit tests, model loading, servers, network calls or browser checks
were run. Old reports of passing tests remain historical claims. No runtime
compatibility or complete data quality acceptance is implied.

Before implementation: agree on forecast target/horizon and covered area; inspect
raw-data definitions, date ambiguity and reporting delay; define spatial units
and a new evaluation protocol; determine future-weather and traffic availability.
Delegate bounded implementation tasks to Claude only after scope is concrete.
