# Goal

Second/final correction round for008. Fix a demonstrated train-serving numeric serialization mismatch, preserving the accepted models and strict1e-12 prediction parity. Read AGENTS.md and original008/008a requirements. No concurrent worker. 008a fixed the namespace/unbound-unit bugs but parity still fails; do NOT loosen tolerances or refit.

# Actual failure and independently diagnosed cause

- Actual pytest after008a: 1failed/53passed in4.24seconds (test_real_predict_batch_matches_saved_11_daily_6h_mixed), maxdifference0.008606182959599029 on its sample.
- Actual notebook13 --stage serve-check failed atcell7 after6.58seconds. backend/reports/v2/serving/reload_parity.csv: loading saved10features reproduces every11prediction within1e-12, but request_builder differs in2025 by up to4.445917687922481daily/1.4344854814239686h.2024 matches.
- Manager verified built vsreference features: no differences above1e-12, but bitwise numeric differences ONLY doy_sin/doy_cos on all diagnostic rows. Their maxdifference is1.1102230246251565e-16. Tree splits can amplify these nearzero differences.
- Accepted10 write_csv_gz uses DataFrame.to_csv(index=False,lineterminator='\n') DEFAULT float formatting, then11 load_unit_frame uses pandas default read_csv numeric parser. New request builder skips that persistence/parse boundary. Both accepted10/11 sources are immutable.
- Diagnostic-only in-memory default CSV roundtrip of built frame (io.StringIO(built.to_csv(index=False,lineterminator='\n')), pd.read_csv(... keys/categoricals str, keep_default_na=False,na_values=[''])) before predict_frame restored ALL35467daily and1418686h diagnostic predictions: maxdiff8.881784197001252e-16daily/4.440892098500626e-16 6h;0rows above1e-12. No implementation changed by manager, no passing acceptance claim. Evidence .ai-team/references/008a-float-parity-diagnosis.json and reproduction code .ai-team/references/diagnose_serving_float_roundtrip.py.

# Scope

Only13 FUNCTIONS/builder and necessary parity/contract/report cells, inference tests, workercheckedpayload/applier under .ai-team/handoffs/008b. No09-12, modelbundles/protocol/config/lock, V1 or frontend changes. Keep all source/as-of/unknownlabel/hash guards. Manager runs commands, archives failed13log/reports before fresh run; do not overwrite them. API task009 waits until008 accepted. ML remains in.ipynb.

# Acceptance

1. Encode the training numeric representation contract explicitly for builder output, using the same serialization/parser semantics as accepted10->11 (no labels/lookups/rounding based on outcomes). A named helper and explanatory docstring/report make this reproducible for future dates too. Ensure types, NaN patterns, exact trained feature order, row order and mixed/single batch invariance remain intact. No arbitrary decimal rounding, prediction clipping or tolerance relaxation. Do not change formulas/accepted sourcefiles.
2. Tests catch this exact numericalboundary bug: actual saved11 rows on2025, nearzero cyclical features and mixedbatch order; selected-model and baseline parity all diagnostic rows innotebook. Test canonicalization's default pandas parse semantics independently of simply calling the implementation twice. Preservehandcalculatedasof/feature tests. No skipped real-data acceptance when artifacts exist.
3. Original13 fullnotebook must run through all checks with actual bundles, stress, latency, subgroup report, strictJSON and hashes. Review remaining cells for concrete interface errors to avoid another round. Reportheader in15_report has unescaped pipe text 'max |Δ pred|' that breaks itsMarkdown table; replace with plain wording without embeddedpipe. Keepstatisticalresults unchanged.
4. Report actual changed cells and tested/not-tested details; no falsepassedclaims. Provide checked assembler command; manager will inspectdiff, execute tests/full13, verifyread-only164acceptedfilehashes, recordformalreview andGitHubcheckpoint.

# Limits

This is correction2of2 for008. If another blocker remains after independent verification, report it precisely; do not declarecomplete or silently alter requirements. No shell/Git/network or otherworker. No need to suppress the known local joblib physical-core warning: log it honestly; it is not the cause of the parity mismatch.
