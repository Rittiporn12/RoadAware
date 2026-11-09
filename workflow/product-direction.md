# RoadAware product direction

## Confirmed user requirements

- Design the website from scratch with a professional appearance and coherent UX.
- Use the previous project only as a reference or selective source of reusable assets.
- Deliver a functioning integrated web application, including the forecasting flow.
- Explain the product's differentiation from Google Maps and Waze credibly.
- Support responsive PC and mobile layouts, prioritizing mobile usage and ease
  of use throughout the route-planning experience.
- Separate backend (ML and Python notebooks) from frontend (future web UI).
  For the current stage reserve the frontend folder and document its scope only;
  do not implement screens or scaffold an application.
- Maintain meaningful GitHub checkpoints at https://github.com/Rittiporn12/RoadAware.git.
  User authorized replacing the old latest-tree contents with the new work;
  preserve history with ordinary commits and pushes rather than force pushing.
- Implement the current data-foundation stages in executable Python .ipynb
  notebooks for VS Code: collection, EDA, cleaning/preparation, temporal splits,
  and leakage audit, with actual outputs and verifiable evidence.
- User requires a rigorous advanced analytics process including Descriptive
  Analytics. A Dashboard for Data Visualization is a future phase: record its
  requirements now but do not implement it. Current EDA figures are analytical
  evidence, not the future dashboard.
- Plan routes from origin/destination and display forecast-related colors and
  historical accident explanations, including time, weather, season and holidays
  where the data supports them.

## Proposed direction, pending detailed design

Position RoadAware as a pre-trip accident forecast and explanation tool. Center
the experience on origin, destination and departure date/time, route overview,
colored forecast coverage, and a clickable explanation panel. Clearly label
historical statistics, model forecasts, uncertainty and missing coverage.

Explore comparing departure times and route alternatives only at spatial and
temporal resolutions the model supports. An hourly UI must not imply hourly
model sensitivity when the model only forecasts daily counts. Do not promise
turn-by-turn navigation or live traffic without an agreed scope and data source.

## Competitor evidence checked 2026-11-09

- Google Maps supports routing, traffic and incident reporting:
  https://support.google.com/maps/answer/9770907?hl=en-CA
- Waze already offers crash-history alerts considering traffic/road conditions,
  weekday, time and crash-report history:
  https://support.google.com/waze/answer/13014546?hl=en

Do not claim these products lack accident alerts or historical crash analysis.
Proposed differentiators to implement and demonstrate: explicit recorded-count
forecast targets/horizons, Thai accident-data provenance, local holiday analysis,
historical accident-type explanations, transparent coverage and model evaluation.
These are product objectives, not established uniqueness or accuracy claims.

## Readiness before declaring completion

Verify the complete flow from route input through actual model inference to map
and explanations. Independently assess forecast quality on an appropriate time
evaluation, along with software checks. Validate missing-data behavior and
responsive layouts. Settle forecast horizon, study area, spatial/time units,
weather/traffic sources and hosting scope before bounded implementation tasks.

## Mobile-first UX requirements

- Mobile is the primary design target; desktop gets a layout suited to its space.
- On mobile, use a map with a collapsible bottom sheet for route summaries and
  selected-area details. Keep key route controls reachable without obscuring
  the map; avoid competing nested scroll areas and hover-only interactions.
- On desktop, show the route controls/details alongside the map, keeping the
  selected route or area synchronized across both views.
- Make origin, destination and departure selection a short, clear flow. Provide
  readable summaries first and progressively reveal supporting details.
- Use comfortably sized touch controls (target at least 44 by 44 CSS pixels),
  readable Thai text, visible focus states and text labels alongside risk colors.
- Preserve entered routes when requests fail; provide actionable loading, empty,
  error and insufficient-data states without discarding context.
- Verify representative narrow mobile, tablet and desktop sizes, portrait and
  landscape behavior, on-screen keyboard behavior, and no horizontal page scroll.
- Verify actual route search, map selection and detail reading on mobile-sized
  layouts, beyond checking that components shrink to fit.
