# Goal and resume context

Resume and finish the user's backend/ML completion request after Claude session quota reset. This is a continuation of009 interrupted byquota, NOT a correction round for a tested implementation defect. Read AGENTS.md and original task009-local-backend-api-catalog.md in full; all endpoint, notebook, security/integrity, testing and documentation acceptance criteria stillapply. Also read010-historical-description-source-recovery.md; integrate its exactraw description recovery into14 now, before finalcatalog export/APIacceptance. This supersedes009's earlier suggestion to leave22012 unmatched descriptions for a later study. No concurrentworker, nofrontend/deployment/Git/shell.

## What is complete and immutable

Mainc296bfe: notebook13MLserving accepted,57tests passed9.40s, actual13completed27.32s/18checks. All177335saved11predictions reproduce within1e-12, all diagnosticfeaturevalues match10bitwise. Newtraining_numeric_representation helper deliberately mirrors10->11pandasdefaultCSVserialization/parser; retain thiscontract exactly. Do not refit/reselect/change09-13/configs/locks/bundles.186acceptedfilehashes savedlocal .ai-team/references/backend-serving-before-api.json.

Actual13source aid .ai-team/references/notebook13-source-current.txt and trustedfacts .ai-team/references/serving13-accepted-hashes.json. Samefacts backed up in workflow/wip/009-api-quota-checkpoint/status.json. APIdependencies alreadyinstalledwithoutMLupgrades: FastAPI0.115.14,uvicorn0.34.3,httpx0.28.1,pydantic2.11.10,starlette0.46.2. Source/function14/runtimepins followoriginal009 contract, manager createsbackend_runtime_lock onlyafter14acceptance.

## What009 wrote before quota

Run20261110-235758-36357 stopped00:03:37Bangkok2026-11-11withHTTP429: sessionlimit resets04:00. Its result.json is_errortrue/terminal_reasonapi_error even thoughsubtype sayssuccess; nofinalreport/acceptance. Noactiveworker remains.

- backend/config/catalog_v2.json (partialprovisionalconfig)
- .ai-team/handoffs/009/cells/02_functions.py (worker-authoredcatalogFUNCTIONS payload)
- Exactsource backup: workflow/wip/009-api-quota-checkpoint/notebook14-functions.py.txt sha256c240458df0fce63dd69ec01f1ebc44b4957e1d82cfbac8b9283b7a720902b78b

Syntaxcompileonly passed. Noassembled14, actual14run, catalogtests/APIpackage/endpoints/liveHTTPsmoke exist yet. InspectthepartialcodeasWIP, nottrustedcompleteimplementation. Continueit orrevisewithincatalogscope; allMLlogicmustendupin.ipynb, thinAPItransport.pyallowed. Do not claimunrunchecksaspasse.

## Additional source audit / completion target

Read010task and managerpreflight .ai-team/references/catalog_raw_enrichment_preflight.py/.json (summarybackup workflow/wip/009-api-quota-checkpoint/description-recovery-preflight.json). All106308retainedUIDs matchsourcefile/source_rowrawcoordinatesandBEyear:ACC_CODEexactly;84296existingdescriptionsmatchrawwith0differences. Restoring22012repairedUIDs fromhashverifiedrawreducesunknownaccident_type26147->4984,presumed_cause23097->1196,weather22604->724. Thesearehistoricalattributesonly. Keeprealrawblanksunknown; do notchangeeventdates/counts/features. Implementidentity/hash/legacycomparisonnegativecontrols as010requires.

## Deliverable order

1. Finish14catalog config/FUNCTIONS/report/checkedassembler andtargetedfixtures, withrawdescriptionrecovery.
2. FinishthinlocalAPI/bootstrap, explicitCORS/resourcebounds/strictpayloads/sanitizederrors/healthreadiness, endpointsandOpenAPIexamples per009. Mustverify13/14source+manifestpinsbeforeexec/deserialization; missingmanagerlock=readiness503, neverautotrustcurrentfiles.
3. Addcompatibledependencyconstraints/runbook, reproduciblecommandsfromVSCodeIntegratedTerminal, source/modelrestorationinstructions; nofrontend.
4. Reportchangedfiles/exactfunctions/commands/checksactuallyrun/notrun/remainingissues. Codex mechanicallyassemblesifneeded, independentlyinspectsdiff,runsfixtures+14,createsreviewedruntimepins,runfullsuiteandactualHTTPserverparity/errorchecks,thenGitHubcheckpoint. Neverdeclarebackendcompletebeforethisevidenceexists.

Ifquotaremainsunavailable reportexactresettimeandpreservework; userexplicitlypreferswaitingforClaude, notCodextakingoverimplementation. Noautomaticretryloopsorsecondworker.
