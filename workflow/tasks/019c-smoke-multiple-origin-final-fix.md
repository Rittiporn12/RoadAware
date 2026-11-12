# Goal

Fix only the smoke-helper category accounting defect found in final019b acceptance. Requires explicit user approval for this extra correction beyond the two-round limit in AGENTS.md; Codex must not invoke this task until that approval arrives. Claude remains sole code/test writer. No shell/Git/extraagents.

## Context and actual evidence

019b run20261112-124630-96550 reviewed FAIL. Task019b completed fixture child dispatch, chosen-bundle chain collection and14/23portability. Targeted82passed/2skipped0.91s. Actual003:72/73checks passed7.38s/startup4.06s, both processreturncodes0/portsreleased. AllpublicAPI/prediction/history/geometry/32numeric21CSVrows/OpenAPIexamples PASS. Actualcorrupt-sourcefixture health200/ready503artifact_hash_mismatch/predict503sanitized/nofakezero PASS. All78consumedfiles equaltrustedpins andunchanged incl4spatialbundles/4provincebundles/2baselineNPZ/rootmanagerlock PASS.

Sole failing check: coverage_problems(pins) reports `evaluation_record: 0 < 1`. In consumed_pins, add() uses setdefault on the path;21manifest is added first from the22spatial_serving_pins chain, so adding that SAME path as evaluation_record retains only its first origin. The file is present, hash verified and unchanged; category accounting loses overlapping membership. Do not remove the check or change model/data/acceptance criteria to pass.

Read AGENTS.md and inspect only backend/scripts/smoke_api_live.py, relevant smoke tests in backend/tests/test_backend_api.py and actual003/read_only_evidence.json as needed. No broad history/model notebook reads.

## Allowed changes / acceptance

Only backend/scripts/smoke_api_live.py, backend/tests/test_backend_api.py, and runbook/README smoke-root references if needed. Accepted13–24source/config/data/models/manifests/managerpins unchanged. No model fitting, pipeline reruns, frontend/deploy, new features, memorywrites or edits to oldrunroots.

- Correct accounting so a verified path present through more than one accepted chain satisfies every applicable required category while remaining one physical file in before/afterhash checks. Keep provenance accurate (multi-membership or equivalent semantic-path/category accounting). Missing evaluationmanifest must still fail; empty/bundleless sets must still fail. Do not globally relax category requirements. Preserve conflict/refusal behavior and all actual API checks.
- Add focused regression reproducing the REAL overlap (21manifest pinned via22servingpins, then also evaluationrecord) and prove valid overlap passes while missing required membership/file still fails. Keep existing tests meaningful and update any expected fixture shape only as necessary.
- Next actualroot backend/rerun-api-019-004; never rewrite001/002/003. No notebook reassembly or managerpin changes needed unless Codex independently finds unexpected changes.
- Report changed files, checks actually run(none, files-onlyworker), checks not run and any remaining issue. Do not claim pass/acceptance. Codex runs targeted/full final regression and actual004HTTP, verifies source diff/pins/public outputs before acceptance.
