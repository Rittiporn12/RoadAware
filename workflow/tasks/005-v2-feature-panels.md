# Goal
MANAGERUPDATE15:11: scopealsoincludes the small, separatelybounded finalsource
correction in workflow/tasks/004c-weather-quality-correction-2.md. Readit. 09
kernelhasfinished, soearlierprohibitionon09mutationduringcollectionno longer
applies ONLYtothespecific004csourcequalityfix. Yourfresh005conversationstarted
after004bfinished; youaretheONLYClaude worker. Ifpracticalwrite004cpayloadsfirst
andnotehandoffreadysoCodexcanresumelongcollectionwhileyouimplement10. Both005
and004cacceptanceareindependent; don'tmarkeitherpassed. Noextraworkers/shell.

Implement notebook10: reproducible v2 date-evidence repair, descriptive analytics,
daily and6h target panels, useful external features and leakage audit. No model
fitting in this task. User wants actual stronger forecasting experiments later,
with holiday/festival, weather, season, timeblock and traffic features tested.

# Context / read
Resume context2026-11-10 15:05: worker004b has FINISHED (no concurrentClaude).
Codexstillrunsindependentonline09weathercollection (session55670); finalsource
acceptance/offlinechecks pending, NOTpassed. YoumayIMPLEMENT10nowusingcurrent
09schemas/config andactualavailabledate/traffic/geooutputs. DoNOTexecute10or
fitmodels. Codexwillonlyexecute10AFTER09accepted. No09/configchangeswhilekernel
collectsweather. Anyold09manifeststillshowing0weathermaybepreviousrun: current
Eloopcollectsnewchunksandwillwriteweatheraggregatesandmanifestatend. Useactual
09source/currentconfig forinterface, notinventedoutputs oroldblockedreadiness.
Current09code33fixturespass, actual77points/77ISOjoin/inside,6AADTyears77provinces
each,95calendaradd/removeactions. Data2024traffic2130fullyblanknonrecords
excludedexplicitly+2736stations; provincealias พระนครศรีอยุธยา -> อยุธยา isaudited
exactmaptoexistingv1panel. Geoquerytablekeepsoriginalname_th PLUSprovince_key.
Trafficsummarykeyprovince_key. Weatherpreceding-hourrainintervalnowcorrect:
00-06usesvalid01..06,instanttemp00..05; finaledgecanberainmissing. Preserve
completehour/sourceissueboundflags. Forecastsourcecoveragewillbepartialunder
4500weightedcalls/runquota; missingcovariatesremainNaN, SAMEcohortallmodels.
Readonlytargetedsourceaids: .ai-team/references/notebook09-source-after004a.txt
isBEFORE004b,sofornewschemasuseactual09_patch/cells/C_traffic.py,D_geography.py,
E_weather.py,G_report.py,functions_part2.py (temporaryworkerpayloads, notimports).
Source05/03aidsalreadyexist. Avoidreadinghugewhole.ipynbinfiletool; toolsRead
mayrefuse. Fornew10 usemultiplemanageableFUNCTIONScells, testscombineall in
order. Ifeditinglargeipynbfailed,writeexactcellpayloads+checkedassemblyhandoff
under.ai-team/handoffs/005 andletCodexapplymechanically; finalbusinesslogicmust
liveentirelyinactual10.ipynb, noruntimeimportsfrompayloads. Focusboundedfilework,
do notrewritev1 or09, do notmodifytools/bridge (Codexsetuphandledthat).

AGENTS.md; workflow/v2-feature-policy.md (binding before fit); calendar source
verification and v2-review-feedback; accepted notebook09 and actual sourceoutputs;
v1 config,data/interim/row_audit.csv,cleaned_events.csv,quarantine.csv and03-05.
Read aggregate reports09 and v1 data before choosing exact interfaces. V1 is
frozen. Source rawCSV112136 rows2021-25 plus15239 diagnostic2026. Ambiguous dates
2021-23 resolve peruniqueID typedXLSX counterpart candidate, NOTglobalformat.
2022rawmixedformat. Existing v1 otherfieldIDconflicts2309 must remain excluded.
Inputs may be partially unavailable; never fabricate completeness or measurements.

# Allowed files/scope
NEW backend/notebooks/10_v2_preparation_features_leakage.ipynb;
backend/config/feature_pipeline_v2.json; extend backend/scripts/run_v2_notebooks.py
stage prepare (all=09then10), --data-root read-onlyv1root, --external-root and
--output-dir independentroots; extend backend/tests/test_v2_notebooks.py.
DocsREADMEs update truthfulstate. All data logic innotebook; runner/tests.py only.
Generated large event/panel matrices only backend/data/v2 (gitignored); tracked
aggregate evidence backend/reports/v2/preparation. No09changeswithoutCodexfinding,
no01-08/v1data/reports/configchanges, nofrontend/API/models/Git/shell/subagents.
NotebookEdit available; file-only implementation. Codexrunschecks.

# Acceptance / implementation
1. Thai narrative withgoals/dataflow/schema choices/actualoutputs/constraints.
Self-contained FUNCTIONS code cells, freshkernelVSCodeRunAll, robustbackend/env
roots. Same project.venv runner nbclient executedoutputs. Explicit dependency
hash validation:09manifest/config/derivedsourcefiles andv1manifests, failtampering.
No network10; require sourcedata09 andrecordallinputhashes/sourcecellhashes.

2. Reconstruct originalrowdecisions fromv1rowaudit/cleaned/quarantine, preserving
source_file/source_row/event_uid and strictnon-datefailures. Resolveonly09exact
IDdateevidence withcandidate membership andunambiguouspublishercounterpart.
Before accepting date, independently compare source context province and time
(usingnormalizedoriginalaliasvalues; typedXLSXprovince/time asneeded) toprevent
cross-versionIDmisassignment. Missingcounterpartcontext means explicit confidence
anddon'tsilentlyassertcontextverified. Preserve id_conflict_other_fields;
nevergroupbyfirst forconflicts. Originalretaineddates stayunlesscorrectionproven
bycandidateevidence, excludeout-ofyear andambiguous. NoXLSX-onlynewlabels.
All2026 remainsdiagnostic. Save rowlineage/localaudit, aggregatepolicycounts,
v1-v2 retaineddatechange/countdelta, rowreconciliation imported=retained+collapsed+
quarantine+diagnostic. Policy/provenanceexplicit; nochoicesfromscores.

3. Rebuild candidate-day unknownflags fromremaininguncertainty; repairedambiguous
dateonlyrows no longerflagbothdates. Missingprovince flagsALL77 forplausibledates;
preserveinvalidcoord/exclusionpolicyv1 inthisfirstexperiment. AllstrictIDconflicting
rowsflagpossiblecandidatedates. CorrectlymapAD/BEyears, timesseconds including
24:00invalid, localtimezone. Ifnodatecandidates flagyear scopeorblockasv1policy;
never silently knownzero. Do notuserealizedflag/mask asfeatures.

4. Full77province x1826day2021-25 panel, additional x4timeblock panel.
Dailyand6h counts reconcile bysum, allfourblocktarget_start/endexplicit;
issuedaybefore18:00local. training_eligible=false forunknownflags; broadcastdaily
flagsall4blocks. Emptyknowncells zeroSELECTEDrecordedevents, notproventruezero.
Samev1splitdatesTrain2021-23,2024development,2025seenreuseddiag;2026neverlabels.
Provincecodejoinusing09pointstable +auditedThai normalization(กรุงเทพมหานคร,
บึงกาฬetc), nofuzzyguesses. Saveunresolvedcounts; don'tdropunknownsilently.
Forcontextfields preservev1strictpolicy, do NOT use outcomeweather/cause/injury/
involvedcarsasfeatures. Descriptiveoutputscanillustrateaccidenttypes/history
butseparateclearlyfrompredictors.

5. Featuregroupsperworkflow/v2-feature-policy.md: coredate +sincosdayofyear;
festivalSongkran/NewYear recurringcrossyearnearestsigneddistanceclipped14,
pre/post1-3/4-7windows; reviewedbankcalendarasofknown_from,add/removeactions,
unknowncoverageflagsno0fakecoverage; seasonalcalendarproxy;
JMApreviousday2 rain/temp daily/6h, completehours andmaxissuebound+6hguard;
DOHprovinceannualstationmean/medianAADT/heavyshare/stationcoverage, newest
prioravailablevintage maxcreated/modified+1day, nofutureannualactual/backfill.
Missingweather/traffic remainsNaNfortrain-onlyimputerlater; source-availability
flagsallowed iffknownatissue, auditquality/outcomeflagsnotallowed. Keepallmodels
samepanelkeys regardlessfeaturemissingness. Numericalfeaturesnoinfinity.
Actualeventtimeonlylabels; deterministictimeblockfeatureallowedfor6htarget.
DoNOTimplementconditionalhistoryuntilCodexconfirmsseparatescenarioafterprimary.
Markhistorypendingbecausehistoricalpublicationavailabilityunverified.

6. Machine-readablefeatureavailabilitymatrixgroup/name/unit/source/available_at/
knownbeforeissue/teststatus/assumptions; strictallowlistsdaily/block andforbidden
names. As-ofjoinassertions andnegativecontrols (futureannualtraffic/specialholiday
lateannouncement/weatherhourpostissue) MUST reject deliberatelyleakyfixtures.
Dates/splits/ID/target/masks nevermodelinputs. Readinessproduction=false;
operationalBLOCKED, sourcevintage/delivery/selectioncoverage caveats.

7. Descriptiveanalyticsactualbefore/after2021-25/bydayofmonth1-12versus13+, months,
provinces,weekday,timeblock; targetdispersion/zeros/nonzeros; unknown/missingness
coverage byyearfeaturegroup, weatherleadbounds,trafficvintagecounts,banksnapshot
coverage. Labelchartsrecordedselectedcounts, notriskorcausalfeatureeffects.
Modest meaningfulPNG fordatefixbias/timeblocks/sourcecoverage. Thai report
data_preparation_v2_th.md explainswhatchanged/why, usedvsunusedcanonicalcolumns,
yeartoyeartypenormalization, sources, featuredefinition/limitations, handoffto11.
All strictJSONfinite, aggregateCSV/PNGandmanifest. No fabricatedmetricsorwin.

8. Meaningful offlinefixtures: uniqueIDdatecandidate andcontextmatch/conflicts,
2022mixedformat,strictotherIDconflictpreserved,repairedflagsremovedonlywhenvalid,
unknownprovinceALL77, eventexact6/12/18boundaries,datecrossyearfestival,latebank
announcement+removeaction,unknowncalendar!=nonholiday,asoftrafficfuturevintage
rejected,weathercompletehours/issueguard,panels daily=sum4blocks,countsnonnegative,
featureallowlistcannotacceptoutcomes,independentrunnerrootisolation/tamperfail.
Tests use syntheticfixturedataforverificationONLY, never claimrealcollection.

# Verification requested / report
Codex inspectsactualdiff andrunsallfixtures+real10, independently checks row and
panelreconciliation, sourcefeaturecoverage/leadguards andv1hashimmutability,
thenrepeat10isolatedoutput andcomparedeterministicartifacts. Worker report
changedfiles, checksactuallyrun(nonewithfiletoolsonly), exactcommands,
input/outputschemas, featurelist/hashinterfacefor11, assumptions andremaininggaps.
Read workflow/v2-review-feedback.md beforefinaldocs/report. No claimsmodelsbeat
baselinesuntilnextboundedexperimentstageactuallyruns.
