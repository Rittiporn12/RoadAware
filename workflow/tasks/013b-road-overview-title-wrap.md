# Goal
Correct the actual V3.1 overview PNG title clipping observed by Codex. This is correction round1 of013a, visual wording only; no data/scientific logic change.

# Context
Read AGENTS.md.013a worker20261111-091924-71069 added EXAT successfully.66fixtures and394fullbackendtests actually passed; online35.14s/offline17.09s notebooks completed. Independent visual review found the map title single long second line clips beyond the PNG right edge. Other figure fine. All data reports still under independent review; do not claim accepted.

# Allowed files
ONLY .ai-team/handoffs/013a/cell_16_replacement.py, which is the exact current notebook17 plotting cell source. Codex will mechanically splice it. Do not read/rewrite full executed notebooks, change configs, tests, data, metrics, matching or existing plotting loops/styles.

# Acceptance criteria
Wrap overview title into short readable lines (source list may be a separate line). Keep snapshot timestamp/mode, source coverage versus accident-report completeness distinction, descriptive geometry not risk/forecast distinction. Preserve exact data/loops/styles, distribution figure, output paths and dimensions. Ensure wording fits the10inch map; use explicit linebreaks and reasonable font size. No other logic changes.

# Verification requested
No shell/test access. Codex independently compares cell diff, replays offline into a new root, verifies raw/derived hashes unchanged, inspects actual PNG. Worker report changedfiles, checks run(none), notrun, remaining issues. No frontend/models.
