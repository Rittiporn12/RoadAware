# Goal
Finish interrupted task004 (external collection/date evidence09), not a redesign.
Original run20261110-083444-56482 stopped on Claude session quota, NOT accepted.
User confirmed reset and authorizes continuing under existing Claude-code/Codex-
verification roles. V2 feature preparation005 and3-family models follow after09.

# Original requirements / context (binding)
Read AGENTS.md, workflow/tasks/004-external-sources-date-audit.md in full,
workflow/v2-checkpoint-status-th.md, workflow/v2-review-feedback.md,
workflow/calendar-source-verification.md and workflow/v2-feature-policy.md.
Original004 acceptance/constraints remain binding. Read actual09/config before
editing; most collector FUNCTIONS/sections A-G already exist. Preserve correct
work, do not regenerate45KB FUNCTIONS merely for convenience. Need complete
setup before A, runner, tests, calendar-source integration, config fixes, docs.
Worker has filetools only (NotebookEdit supported); Codex executes shell/tests.
Avoid huge rewrites/output; use bounded targeted cells/edits and concise report.

# Allowed files
Same004scope:09ipynb,config/external_sources_v2.json,new scripts/run_v2_notebooks.py,
tests/test_v2_notebooks.py, requirements-data.txt add openpyxl/pypdf/shapely ifmissing,
backend/root/notebooksREADMEs. Sources/largeoutputs ignoreddata/external_v2;
smallaggregateauditreports/v2/sources written bynotebook uponactualexecution.
No v1 data/reports/notebooks01-08/config modifications; no10/models/frontend yet;
noGit/shell/delegation. Do not alterworkflowtask/policy/review docs.

# Concrete incomplete points / required changes
1. Current09has FUNCTIONS andA-G butNOsetupcell definingCFG/roots/REGISTRY_PATH/
REFRESH/OFFLINE etc. Ensure clean freshkernelRunAll works fromVSCode; configpath
robust. Runner project.venv freshnbclientkernel, --stage collect/all (09only now),
--output-dir,--external-root,--data-root(readonlyv1),--timeout, offlinecacheflag
ifuseful. All businesslogic staysPythonnotebook; runner/testsPythononly.
2. Actual cached weatherprobeURLlatitude13.75,longitude100.5, NOT14.0. Correct
provenance. MissingMOTdictionaryURL actuallyknowninoriginaltask/feedback404;
logattempt/gapwithoutclaimingverifiedformat.2022mixedformat; preservebothcandidate
agreement andperIDunique/contextuncertainty. Never globallyparseallMM/DD.
3. Integrate reviewed calendar transcription intoexplicitconfigrecords with
sourceURL/page/hashvalidation andverified_by visualreviewprovenance. ALL5annual
sourcecontentsnowavailable:2021officialBOTembeddedscene7PNG,2022officialFIPCS
PDF,2023/24/25annualPDF;2023yearend amendmentactualPDF (remove2024Jan2,
add2023Dec29),officialHTML2021extras/2022extras/2023May5/2024Apr12/2025Jun2Aug11.
See exactrecords/URLs/circulardates and limitations incalendar-source-verification.
RawPDFimageonly:emptytext!=nocalendar. DoNOTrequirepypdfkeywordsextraction to
use reviewedfixedfestivalevidence. Resolveknown_fromendofdaylocal, actionsadd/
remove, scopeBANK!=public, duplicates/versionedrecords. Calendarcoverageunknown
doesnotmeanordinaryday. Do notclaimglobalcompletepubliccalendar.2021source
known_fromJan6ONLY, historicalpublicationisresearchproxy. Match reviewedsource
hash toactualpreflightfile; ifbytesdiffer failreviewrecordratherthanapplyblindly.
Youmay addreviewedrecordsintojsonconfig fromCodextranscription, hash actualfile
viaexistingrecord whenruntimecollects. Strictsourcevalidation. Onlyexactscene7
host officialembeddedasset allowedwithparentBOTURL, noarbitrarynewhosts.
4. Trafficper-resourceavailability proxy max(created,last_modified)+1day;
createdaloneisnotconservativeforrevisedbytes. Documentproxy!=historicaldelivery
proof. AADTannualstationmeans/median, notsumuniquevehicles/realtime, no sameyear
annualactual usedearlyyear. Normalizeall2020-25annualCSVschemavariations,
recordunsupportedunits/duplicates/nonnumeric/unknownprovince ratherthansilent.
5. Weatheractual77×2021-25 JMA GSM lead2 as004. Boundedcache/resume/quotas,
complete24/6h only; noNaNrain->0, conservativelead+6hguard. Make progressvisible,
maxnetworkrequests500, responsecap/timeouts/retries. Do not collect in worker
(noshell); Codex runsactual09. Partialcoveragehonest, notfabricated. If fullrun
slow20sbetween80chunksokay; cachedrerunshouldnotwaitnetworkinterval.
6. Meaningfulofflinefixturetests per004 inclcachemutation/retry/IDconflict/
calendarasof+remove/weathercompletehours/traffic/geo/runnerroots. Neverpretend
executedtestresults; provideexactcommandsforCodex. Requiredpackagesalready
installedlocal(.venv openpyxl3.1.5 pypdf5.9.0 shapely2.0.7); CodexPDFQAuses
pypdfium2separately, notrequiredruntimeunlessneeded. Existingv1tests143pass,
112frozenv1filesunchanged atcheckpoint556c1b3.

# Acceptance / verification / report
Alloriginal004criteria. Codexwillinspectactualdiff, runallfixturesandactual09,
auditinput/outputs/hash/units/provenance/coverage, checkv1unchanged andrerunoffline
isolatedreports toverify deterministicderivedaggregates. PassingCLI!=acceptance.
Readlivefeedbackbeforefinal. Report changedfiles, checksactuallyrun(notrunwith
fileonlytools), exactcommands, outputpaths/schemas, genuinegaps, next005interface.
Do notmark09completeinREADMEbeforeCodexruntimeevidenceorclaimV2beatsbaseline.
