# V2 live independent review

Currentstage task004/notebook09 externalcollection/dateevidence. User explicitly
authorized necessarynewdata/features:traffic,weather,importantdays/festivals,
seasons,timeofday,history. Goalimprovevsstrongbaselines, no guaranteedwin.

No v2 sourcecodeimplemented yet. V1 accepted/pushedf435083 and must remain intact.
Existing .venv setup installedopenpyxl3.1.5,pypdf5.9.0,shapely2.0.7; noothernewdeps.
Preflight2021typedXLSX20062 rows matchesoriginalIDsandMM/DDdates100%.
2022/23XLSXdownloads inprogress;weatherJMAlead48h2021probe72hoursnonnull bothvars.
OldMOTdatadictPDFcurrently404, don'tclaimverifiedcurrentPDF;useactualXLSXevidence.
DOH2021CSVactualdownloaded,surveypointAADTnotrealtimetraffic. Sourcepackagescached.

Codexwillappendexactruntimeevidence. Do notmarkunrunchecksaspassed.

## Important actualsource discrepancies (08:36)

Downloads2022/23complete. IndependentIDjoins:
2021original20062/XLSX20062,uniqueIDsall,MM/DDdates20062agree/0disagree.
2022original20566/XLSX20566,uniqueIDsall,MM/DDdates13298agree/7268disagree
(ALL ambiguous slash rows disagree: XLSX typed dates appear to swap ambiguous
day/month while unambiguous dates agree). Do NOT claimglobalMM/DDverified or
XLSXnecessarilygroundtruth. This is a source-format/version conflict requiring
explicit perrow/peryear evidence and confidence; preserve uncertainty.
2023original23841/XLSX23841,22139distinctIDs,448IDs withmultipletyped dates.
Do notdropduplicateIDsbyfirst andcallresolved. ConflictingIDs quarantined.
Rawroworder/formatpopulation helpsaudit butdoesnot prove trueeventdates alone.
Clarification: MM/DD_disagreement is NOT byitself an invalidsource date.2022raw
has mixed stringformat (firstunique dates01/01,02/01,...12/01,01/13,...), while
typedXLSX ischronologicallyordered. A uniqueID/date whoseXLSXtypeddate is one of
the originalslashcandidates, withsupportingcontextconsistent, can be proposed
as a publisher-counterpart-derived resolution (explicitpolicy/confidence),
withoutclaimingallrawstringsuseMM/DD or claiming independentgroundtruth.
For09 reportagreementwithBOTHcandidaterules, typeddatecandidate membership and
conflictingIDs. Do not unnecessarily blockall2022 simplybecauseMM/DD disagrees.
2023manyjoin disagreementscome fromone-to-manyIDjoins: resolveonlyIDunambiguous
rows andretainconflicts fornextstageexclusion. V1strictotherfieldIDconflicts
mustnot be silently revivedjustbecauseonecandidate date canbematched.

## Additional preflight source files (08:40)

Cached evidence/geoboundaries-tha-adm1.json,tha-adm1.geojson,thai-provinces.json
nowdownloaded. GeoJSON77features with shapeISO TH-xx (e.g.TH-45,RoiEt) so joinby
provinceCode reliably, shapelyrepresentative_point. Sourcesprovenance as task.
BOTcalendar2023/24/25PDFs downloaded asbot-holidays-2023/24/25.pdf;
pypdf extractsZEROtext on ALLpages (image-only). Do NOT silently output anempty
holidaycalendar ascomplete; recordneedsvisual/OCR. Codexinspectingofficialpages
visually andmayprovidecuratedverifiedsource records.2021/22sameURLpattern404.

## Calendar transcription ready (08:43)
MUST READ workflow/calendar-source-verification.md before calendar finalization.
Codex visually reviewed ALL PDFpages2023/24/25 and transcribed nationalbankdates,
sourcepagenumbers/circulardates and concreteamendmentgaps. Canstoreasreviewed
configrecords, registercachedPDFhashes. OfficialHTMLextra2024Apr12 and2025Jun2,
Aug11 reachable. Original2024Jan2laterREMOVED/moved2023Dec29: neverunionall
original/amendmentdatesforever. Useadd/remove/versionedknown_from or exclude
unverifiedconflict withcoverageflag. Calendarpartial != allnonholidays.

## Source review update / interim notebook structure (08:46)
Calendar verification doc now includes actualdownloaded visuallychecked2022PDF
(differentworkingFIPCSURL),2023yearend amendmentPDF,2022extras/2023May5news.
Readtheupdateddoc; original2022URLpattern404isNOTasourceblocknow.
Interim09notebookinspected08:46 hasonly8cells: intro,Eweather,Fcalendar,Greport,
finalchecks,limits. A/B/C/Dfunctions/source/date/traffic/geoappearmissing atthis
interimpoint. EnsureNotebookEditinsertsemanticsretainALLcellsandFUNCTIONS before
completion (mayjustbeyourinprogressassembly, but independentlyverifycellinventory).
Preflightweatherprobeconfigcurrentlylatitude14.0doesNOTmatchactualcachedprobe
latitude13.75; fixprovenanceURLtoactualverifiedURLfromtaskfeedback. Traffic
availabilitymustusemax(resourcecreated,resourcemodified)conservativeproxy+buffer,
notcreatedaloneifcurrentresourcebytesmayhavechanged.

2021calendar gap also nowresolved by officialBOTembeddedinfographic. Read final
sectionofcalendar-source-verification.md; downloadedPNG,20visuallyverifiedbank
dates,known_fromJan6only,sourcequalityproxycaveat. Addonlyscene7officialasset
allowlistwithparentBOTURLprovenance. All5yearannualsourcecontentnowavailable
(2021PNG,2022FIPCS,2023-25PDF);completefinalholidaycoverage stillrequires
amendmentsanddoesNOTmeanallpublicholidays.

## Resume independent inspection (12:28, task004a)
ExistingFUNCTIONS cached_fetch returns hashverifiedcache even ifrequestedURLchanged
underthesameresourceID (e.g.querycoordinates/configchange). RequireURLidentity
and rejectchangedrequest orstoreexplicitnewversion; don'trelabelcachedwrongquery.
register_preflight currentlyonlystoresoldhashwhenfilebyteschange, cannotpreserve
oldbytesafterexternalfilemutation. Preferintegrityfailureonchangedregistered
preflight ratherthan silentlyadoptit asnewvalidsnapshot. Addfixturechecks.
Weatherpayloadmustvalidatehourly_units temp°C/rainmm andexactvariables; existing
startswithlookupcouldacceptprevious_day20forprevious_day2. Actualcachedprobehas
exactkeys temperature_2m_previous_day2/precipitation_previous_day2 andunits°C/mm.
Rejectduplicates/irregularhourlytimegrids,negative/nonfiniteprecipitation,
outofrequestedperiod/locationcount mismatches, andnonsensicalgridcoordinates.
GeopointsrequestedvsAPIgridcoords remainauditedproxy; no needunreasonablyrequire
returnedgridinsideprovince (weathergridlegitimatelycoulddiffer). Counterpart
province/time0mismatch verifiedforuniqueIDs2021(20062),2022(20566),2023(20498).
Do notinterpretthat assupportforconflictingduplicateIDs.03strictconflictsremain.

## Real current09 FUNCTIONS date audit / tooling (12:33)
Codexactuallyexecutedexistingread_xlsx_id_dates+audit_dates_by_id onrealcachedfiles:
2021resolved20062(readingsmdy19164,equal898).
2022resolved8135(dmy7268,equal867), xlsx_untyped_or_missing_date12431.
2023resolved22922(mdy21954,equal968), xlsx_id_conflicting_dates919.
2022XLSXcontainsmanyTEXTdates, notalltyped. ThisdoesNOTblockretainingoriginal
single-valid-orderdates:005policykeepsoriginalvalidunambiguousdates andonlyuses
typedcounterpartevidence toresolveambiguousones. Do NOT claimall2022XLSXcells
typed oryearlyglobalDMY. Reporttheactualtypes/profileandconfidence.
Tooling: Editon.ipynb failsbydesign, useNotebookEdit. Toavoida45KBFUNCTIONS
rewrite forsmallchanges, workerMAYwrite exactJSONreplacementpayload to
.ai-team/handoffs/004a-patches.json (listofnotebookcellid/index,exactoldstring,
exactnewstring,expectedoldsha optionally). Codex can mechanicallyapply YOUR
authoredpatch as toolinghandoff, thencompile/test. ThisisnotpermissionforCodex
toauthorMLlogic. Avoidlosingbudgetrewritingwhole45KBcell. Mentionhandoff inreport.
Plain source-only current09 reading aid (Codex extracted beforeyourchanges):
.ai-team/references/notebook09-source-current.txt (87730bytes,1500lines,
FUNCTIONS first~930lines). UseReadwithoffset/limitonthisinsteadoflargeipynb
toolresult; verifyactualcelltextbeforepatch. ThisisareadingaidNOTruntimecode.

ExactreviewedcalendarSHA256anchorsnowappendedtocalendar-source-verification.md
and.jsonaid .ai-team/references/calendar-reviewed-sha256.json. Useasexpected
reviewedhashesinconfig; runtimehashbindingaloneisnotproofnewbyteswerereviewed.

## Quota evidence (12:43)
OfficialOpen-Meteopricingverified:600calls/min,5000/hour,10000/day; requests>14days
countfractionally.77provinces*1826days/14 approx10043weightedcalls, so1runmay
stoponhourly/dailyquota; partialcoverageacceptableONLYifexplicitlyquota-limited,
notclaimarchiveitselfmissing. No bypass/repeatedhammering/paidservice. Resume
hashverifiedcachelater. Completehourscoveragechecksremainstrict. Codexcanrun
otherverification/preparationworkbetweenlegitimatequotaresumes.
Source:https://open-meteo.com/en/pricing (actualhourly/dailylimits).

Toolinghandoffclarification: observedbackend/notebooks/09_patch/cells/*.py being
written. TreatasTEMPORARYworker-authoredcellpayloadsONLY, notruntimeimports.
Provideexactassemblymanifest/mapping(orderedinserts/replacements)forCodex to
mechanicallyapplyintotheactual09ipynb. Codexwillmovestagingpayloadsunderignored
.ai-teamafterassembly. Finalbusinesslogic MUSTresidein.ipynb andRunAllstandalone;
testsshouldexecutebothFUNCTIONScells, notjustoldone. Do notcommit09_patchas
alternativehiddenPythonpipeline. Actualrunner mustexecuteassembled09notpayloads.

## Actual pytest at12:47 (fix before final docs)
CodexmechanicallyappliedClaudeapplier:actual09now20cells/schema/compilepass.
Command .venv/bin/python -m pytest backend/tests/test_v2_notebooks.py -q
RESULT:20passed,3FAILED in0.51s (notaccepted).
1.test_province_join_iso_exact_name_unresolved: fixtureChonBuri andChonburi both
normalizetocode20 sojoincorrectlymarksboth unresolved_duplicate_code; assertion
expectsoneexactresolved. Separateuniqueexactjoincasefromduplicatecase, preserve
duplicaterejectiontest, don'tweakenactualguard.
2.test_representative_point_inside_concave_polygon: pandas convertsmissinglatNone
toNaN; assertpd.isna ratherthan`is None`. Actualmissinggeometryshouldstillreject.
3.test_runner_stages_roots_and_env: expectsresolve_roots(output=v1root,data=v1root)
raises, butdefaultbackendusesexactlythatintentionally reports/v2separatefromv1.
Correctfixturetoactualprotectedoverlapcase, retainnormaldefaultrootallowedtest.
Actualrootprotectionmustremainmeaningful notcosmetic. Fulltraceavailable pytest.
NeedexplicitcacheURL/preflightmutation/weatherunits/exactvars guardsfrom12:28
feedbackstillnotpresentinassembledFUNCTIONS; re-readallnewfeedbackbeforefinal.
ExactreviewedSHAanchorsalsoalreadyprovidedinverificationdoc. Applieralreadyrun,
soifpayloadupdatesafterwardsCodexmustresyncauthoredcells (currentapplierno-op
whenpart2exists, thereforewon'tapplynewpart2changesunlessyouprovideupdates).

## 004b same-run independent evidence / weather interval correction (14:51)
Codexexecutedexisting09functions againstREALAPI5provincesfull2021:43800hourly
rows,43800nonnulltempandrain,strictpayloadvalidatorpasses,oldaggregator1825daily
rows/issueboundstrue. Raw+requestevidence at/private/tmp/roadaware-weather-annual-component.
IMPORTANT officialhourlydefinitionsverified https://open-meteo.com/en/docs :
precipitation isPRECEDINGHOURSUM,temperatureINSTANT. Currentaggregate_weather
groupsbothbyvalidtime.hour,so00-06rainusespreviousday23..05ratherthan00..06.
Fixnowwithin004b: keepinstanttempbucketbyvalidtime; bucketprecipbyintervalstart
(valid_time_local-1h). Preserveoriginalvalidtimeandnominalissueboundforsource
availabilityguards (DON'Tshiftissueboundalongwithraininterval). For00-06rain
sumvaluesending01,02,03,04,05,06; forday00-24ending01..nextday00. Needseparate
unique/validhourcountspervariable, complete24/6only. Retainoldoutputnamesneeded
next10, addmetadata n_rain_hours/intervalconventionifuseful. Emittargetkeysfrom
temperaturegridonly (avoidpreviousdaystraybucketfromfirstmidnightrain). Last
availabledaymaylacknextmidnighthour: rainNaN+missingflag,neverpartialsum orfake0;
adjacentyearschunksalreadyconcatcanprovideboundaryhourwhenavailable. No extra
APIrequestneededmerelytohidethefinaledgegap. DoNOTclaimsame-dayraincomplete
underold0..23convention. Docs/reportstatepreceding-houralignment.
Adddistincthour-valuefixture(e.g.rainvalues0..24:00-06sum1..6=21,not0..5=15),
midnight/yearboundary,missinglastinterval=>NaN,andissueguardincludesrain'sactual
latestvalidtime. Updateolderaggregationfixturesappropriatelywithoutweakening
missingnessguard. Smalloverrideaggregate_weatherintheworker-authoredpart2cell
isacceptabletoavoidold45KBrewrite; testsmustexecuteeffectivebothFUNCTIONScells.

## 004b actual interim fixtures (14:54)
Codexresynced004bpayloadswithworker applier thenran
.venv/bin/python -m pytest backend/tests/test_v2_notebooks.py -q
28passed2FAILED (0.86s); fixbeforefinal alongsideweatherintervalissue.
1.aadt_station_rows np.select failscondlistbool dtype: assignmentofpandas
nullablebooleanvaluesintodupSeries castsobject; numpy2requiresboolndarray.
FutureWarningaroundline494andTypeErrorselectaround497. Fixexplicitbooldtype/
non-nullmasks, notdeletefixture. ActualrealAADT2024 samepathwouldfail.
2.test_pinned_source_local_first_offline_refresh_and_mismatch finalfresh-offline
casepassesroot3/newregistrytopinned_source butfetcher2closurestillusesroot2/reg2
whichhascachedbytes ->expectsNonebutgetscache. Correctfixtureinjectconsistent
root/registry soofflinewithoutcacheactuallytested; keepchangedpin/cacheguards.
Independentraw2024check:4866parsed=2130FULLYBLANKallcolumns+2736nonblank,
nonblankmissingprovince0. Frozen112v1filesstillunchanged.

## Current005worker scope extension (15:11) — MUST READ
Readworkflow/tasks/004c-weather-quality-correction-2.md. Managerextended005
explicitlytoincludethesmallfinal09negative-rainqualityfix. 09kernelFINISHED
431.9s; noactivecollectorwritingnow.7rawannualchunksdownloaded/only3usable
because4chunkscontain6hours(-0.1mm)each. Keepraw,maskONLYbadperhourNaN,
preservetemp/otherlocations,complete-windowrainNaN; don'trejectwholebatch or
stopallcollectiononmaskablevaluequality. Actualsourcefilescached no newdownload
neededtoverify. Original004contracts/remaining005contractstillapply. Onlyone
Claude worker(currentyou), noadditionalworker. Ifpossiblewrite004cpayloadsfirst,
notehandoffready, thencontinue10soCodexresumescollectioninparallel. Thisis
boundedcorrection2for004andmaxroundsremainbinding. 004bhistoricreviewFAILsaved;
actualdata/catalog/calendars/traffic/geoalreadyreal, onlyweatherqualitypipeline
needsvalue-maskpolicy. DoNOTclaimacceptanceorcompleteweathercoverage.

005runnerrootclarification: independentlyrerunning10into/tmpoutputmuststill
readaccepted09reportsfromtheirread-onlysourceroot(usuallybackend),separatefrom
externalrawrootandv1root. Explicit--source-root/ROADAWARE_V2_SOURCES_ROOT option
isallowed/encouragedifneeded. Do notrequire09reportstobeundernewemptyoutputdir
or silentlyfallbackfromanexplicitwrongroot. StagepreparemustNOTrerun09/network;
allmay09->10. Recordactualinputroots/hashes andrejecttampering.
# Manager runtime feedback for task007 (2026-11-10 22:07)

Actual11 daily OOF completed139.1s;6h running. Many Poisson NumPy matmul
RuntimeWarnings (divide byzero/overflow/invalid), fitted status ok. Do not alter
11/config/locks or suppress warnings. In12 include actual fit_log warning counts
and convergence warnings byunit/family, linking rawfit_log. Codex separately
reproduced all3warnings on benign normal random70000x100 matrix @100vector:
allfinite and maxabsdiff vsnp.einsum1.5987211554602254e-14. LocalNumPy2.0.2 BLAS
is macOSAccelerate. This points to a numerical-warning/environment issue but
does NOT automatically validate model predictions; Codex will independently
compare saved Poisson predictions vsnon-BLAS contraction before acceptance.
Report observed evidence, do not claim a proven upstreambug or allwarningssafe.
Codex checked primary upstream reports: https://github.com/numpy/numpy/issues/28687
and https://github.com/numpy/numpy/issues/29820 describe similar incorrect matmul
warnings on macOS/M4, including identity matrices. Cite as corroborating context,
not as model-specific verification or proof this host is the same bug. Local
probe JSON: backend/reports/v2/reviews/numpy_matmul_probe.json (read-only).

# Manager clarification for task006 (2026-11-10 18:10, BEFORE any V2 fit)

Status update 18:17: source004c independently ACCEPTED (historical run
20261110-175342-94403). Actual09 bounded online completed972.28s,42/80chunks,
204/385province-years retained,172complete,222negative rain hours masked,
35newrequests/4407.4weightedcallestimate then configuredquota stop. Partial
coverage explicit. Actual10 is now running; NOT accepted yet. Do not fit.
One-off backend/notebooks/09_patch moved to ignored
.ai-team/handoffs/004c-accepted-archive; actual09 contains all logic. Read actual
notebook/source aid for code, not the old payload path. No09/10 modifications.

Independent static finding 18:13 in authored 03_functions2.py:
run_unit_oof builds `frame.loc[..., list(keys) + ['y', 'target_date']]`;
target_date already belongs to both units' keys, so this creates duplicate
target_date columns. Deduplicate selection columns (preserving order) and add a
small end-to-end OOF fixture checking unique columns, unique keys and metric/
calendar-block selection. Fix before handing off; this is pre-review feedback,
not a request to change statistical settings. Also read the clarification below.

Usability guard before long fits: write_selection_lock intentionally refuses
existing lock files. Ensure section A rejects an already-completed output root
BEFORE fitting, with an exact fresh --output-dir / --model-data-root command;
or use immutable per-run subdirectories. A second VS Code Run All must not spend
the entire OOF runtime only to fail when discovering an old selection lock.
Preserve old locks/results; do not silently overwrite them.

Read before final handoff. Current proposed model config uses SimpleImputer
add_indicator=True. Please set add_indicator=False explicitly for both Poisson
and RF preprocessing. The locked input allowlist forbids weather missing/quality
flags and source-status predictors; API collection coverage is a retrospective
sampling artifact, not established historical availability. Do not add extra
missingness-indicator predictors outside the declared groups. Preserve numeric
NaNs until train-only imputation; keep all-missing columns with zero fallback.
HGB native missing handling remains as drafted (document source-coverage
confounding and diagnose missingness shifts later; it does not establish that
missingness was known prospectively). No change to model hyperparameters.
The protocol draft receives this clarification before the manager lock or fits.
