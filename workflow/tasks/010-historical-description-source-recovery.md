# Goal

Complete historical context for the backend by recovering the already-available raw descriptions of V2 repaired retained events. This is a new bounded data-enrichment task after009 implementation ends, not a model change or exception to009 acceptance. User wants backend/ML finished before frontend and original product needs historical accident types. Read AGENTS.md. No concurrent Claude worker. Keep API contract stable; no model/config changes09-13.

# Actual manager evidence

009 preflight correctly found v1descriptive snapshot covers84296of106308V2events, leaving22012repaired additions unmatched. Further READ-ONLY preflight proved all106308 retained V2UIDs map exactly to their original raw CSV row via row_lineage_v2 source_file/source_row (source_row2=firstdata row), with exact BE-year:ACC_CODE equality and sourcehashes matching the v1rawmanifest that10recorded. Thus we can recover descriptions instead of artificially leaving them all unknown. .ai-team/references/catalog_raw_enrichment_preflight.py and catalog_raw_enrichment_preflight.json reproduce it. No implementation or accepted data changed by manager.

For accident_type/presumed_cause/weather respectively: raw value vslegacy descriptor mismatch count on all84296matchedUIDs=0 each. Unknown counts before26147/23097/22604; after exactraw recovery4984/1196/724. Unknown values still genuinely blank inraw, never infer/fill from other events. Timeblock remains the V2repaired event time. Total106308,77provinces,2021-2025 unchanged. This is historical outcome context ONLY, never predictor.

# Scope

Only14_backend_catalog.ipynb / checked14payloads, catalog_v2 config, focusedcatalogtests, necessary truthfuldocs. NO09-13/config/experiment/serving/bundles/data changes, nofit, nofrontend/deployment/Git/shell. APIcode unchanged unless a concrete backward-compatible metadata field needs transport support, explain anysuchchange. Final logic in.ipynb no .ai-team runtime imports. Codex runs tests and14 after applying. Original009 API/catalog requirements stillapply.

# Acceptance

1. Hashverify10 preparation manifest and every needed input:10-registered v1rawmanifest, V2events androw_lineage, v1schemaaliasconfig (check actualrole in10manifest), eachrawCSV againstmanifestfilehash andregisteredceyear. For trusted retainedV2events ONLY, join source lineage1:1 and bounds-check source_row integer>=2<=N+1. Require retainedUID/sourcecoordinateunique, lineageuidsetexacteventsuidset, and exact BEyear:normalizedrawACC_CODE equality. If nottruefail clearly, neverfuzzyjoin/idonlymerge/guess row. Neverreinterpret dates; useaccepted event_date/timeblock/province. No extra rawonlyrecords.
2. Recover ONLY accident_type,presumed_cause,weather via original audited schema_aliases with exactlyonepresentalias perfield (ambiguousheadersfail; missingheaderexplicitunknown). Whitespace normalization identical to V1norm_text. Preserve source blanks/unknown labels. Compare all matchinglegacyUIDs andfail anydescriptivevaluedisagreement; no overwrite of V1descriptivefile. Retain separatelegacy_match/provenance/missing counts inexport/report. Do not exposeeventUID/source_row/rawnarratives toHTTP. Exportaggregates only. APIquery schema remainscompatible; unknowncategorycountsnowreflect actualraw completeness.
3. Actualexport:106308events/no rowmultiplication, descriptionrecovery22012UIDs, categoryunknowncounts4984/1196/724, all84296knownUIDvalues unchanged. All monthly/category totals reconcile; prepare a report showingoldversusnewcoverage and sourcehashprovenance, not claimingunknownattributesknown. Historicalweather/cause notcausalforecastinput. Existingprediction/evaluation/safetylabels unchanged.
4. Meaningful fixturetests reject tamperedrawfile, rowbounds,rowUIDmismatch, duplicateevent/lineage/ambiguousheader, legacydescriptorconflict; preserveunrecoverableblank andsourcealiasesacrossyears, no newrecords. Runmanageractual14freshkernelthenindependentraworaclecompare. No relaxing original009 APIlimits/sanitization/locks. Manager creates final backend_runtime_lock AFTER14acceptance (newcatalogmanifest/hashpins), thenAPIactualtests/smoke. If14wasalreadyrun, preserveinitialcatalogevidence andusefreshoutputroot/archive; neveroverwriteoldmanifest.

# Report

Changedfiles/logic/interfacecompatibility, actualchecks/notrun, exactassembler/test/runcommands, remainingissues. Workerfiletoolsonly, noshell/Git/network/secondworker. Do notclaimacceptance merelybecausematchingmanagerpreflightnumbers.
