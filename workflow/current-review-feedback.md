# Active review feedback — notebook task, correction round 2

Codex ran these while the current Claude run is still active. They are findings
for the SAME correction round and original acceptance criteria.

Commands actually run:

```sh
.venv/bin/python backend/scripts/run_data_notebooks.py --output-dir /private/tmp/roadaware-precheck-20261109 --timeout 300
.venv/bin/python -m pytest backend/tests/test_data_notebooks.py -q
```

Outcome: notebooks 01–04 passed with actual source data; 05 failed its deliberate
negative control assertion. Unit tests: 50 passed, 3 failed (existing EDA
confirmed_hour/confirmed_month and the temporal-overlap fixture). No model trained.

## Notebook 05 concrete failure

`AssertionError: a negative control was NOT rejected: inject_boundary_label`

The control marks only boundary_excluded AND NOT possibly_undercounted rows
eligible. On real data, the earlier boundaries are flagged, so the altered rows
can belong only to final 2025 boundary. audit_label_boundary only compares splits
present in the panel, and diagnostic_2026 is intentionally absent. This gives
no violation. Do not falsely mark this control passed or remove the requirement.

Suggested bounded fix: copy the panel and select at least one row in an earlier
represented split, keep flags coherent, then set its target_end after the first
issue of the next represented split, mark it eligible, and directly run the
label-boundary audit. Assert at least one row actually changed. Alternatively
pass explicit next split first-issue cutoffs to the audit consistently. Test it
on the real artifacts and a minimal fixture. Negative controls must be meaningful.

## Fixture logic failure

test_negative_control_temporal_overlap_and_boundary moves every first validation
day to Train. This does NOT create target-date overlap: Train max becomes Jan1,
Validation min becomes Jan2. Test real overlap by appending a row with a target
date already in Train under Validation, then audit_time_order. Test a label
crossing the first next-split issue separately with audit_label_boundary.

## EDA failures

- confirmed_hour([12:99, 7:05:61]) must return missing, not 12 or 7.
- confirmed_month([31/02/2021, 30/02/2564]) must return missing; validate dates.
- Tests already encode these cases. Rewriting notebook 02 with robust parsing
  is within the existing final correction task, and was already planned.

Please finish docs/requirements/frontend placeholder too, and remove the temporary
active review banner from root README when addressed (retain this review history).
