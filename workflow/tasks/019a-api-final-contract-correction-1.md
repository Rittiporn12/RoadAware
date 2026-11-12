# Goal: correction1 of at most2 for019; close only final contract/verification gaps

Read AGENTS.md, workflow/tasks/019-integrated-research-backend-api.md and .ai-team/references/019-source-review-notes.md. PreserveALLoriginalAPIrequirements, no newfeatures/models/refit/tuning/frontend/deploy. Claude solecode/testwriter; Codexruns/reviews. Allaccepted13/14/16–23/raw/models/configs/data immutable. Root001mustremainunchanged. No oldkernelpipeline reruns ormemorywrites. Keepthisoneboundedcorrection.

# Actual verification

-24assembled. TargetedAPI+assembler **67passed/1failed/1skipped1.55s**. Failuretest_predictions_order_errors_and_limits line335 rejects literaltext `NaN` in an error string `non-finite JSON constant refused (NaN/Infinity)`. That is legalfiniteJSON. Correct fixture toparseJSONrejectnonfiniteconstants andwalknumericvalues; don'tremoveusefulerrorwordingjusttoappeasestringscan. Keepnoabsolute-path/traceback/inputbodychecks.1actualtestskippeduntilenabled.
- Codexinspectedsource24geometry/strictcontractandruntimebootstrap;manager24/configpinssuppliedONLYforlocalintegrationtesting(notwholeAPIacceptance). `ROADAWARE_API_ACTUAL=1 ... -k actual` **1passed4.16s**:actualcomponentload/geometry3105/selectedthresholdparity.
- **LiveHTTProot backend/rerun-api-019-001:46/46passed6.06s,startup4.07s**. Realuvicornlocalhostport8765;13provinceexamples,14provincehistory,22selected+baselinebothunits128each exactsavedresponses,3105geometryIDswalk/historycutoffs,explicit2026unsupported,strictJSON/64KiB/128/duplicates/CORS/errors;ownserverstopped. Evidence smoke_evidence.json/sample_responses.json/openapi.json. Priorreviewduration16.89wasmanagertranscriptionerror, corrected09:01;useactualJSON6.06only.
- Corebackendfunctionswork. Remainingissuesbelowareexistingcontractgaps, notnewproductscope. Useraskedfinishquickly; donotrevisitacceptedmodels/catalog/dataaudits.

# Allowed changes

019payloads/new24/config, backend/api, server/smokeCLI, API/assemblertests, requirements/constraints/runbook/frontendintegrationdoc/README onlyasneededbelow. **DoNOTeditworkflow/api/input-pins-v3.json orothermanagerpins.** Current24/configpinswillbe staleaftercorrection;Codexreassembles,inspects/testsandrefreshespins, thenactual002HTTP. Workertoolsfilesonly,noshell/Git/extraagents.

# Required corrections

1. **APIevaluationnumericOOF/seenresults missing.** `_load_evaluation` onlyreads21manifest;`evaluation_21_summary` returnsmethodIDs/reportfilenames/checkcounts, noOOF/2024/25scores. Manifest.selectedonlyholdsselected/baselinestrings. Consumeactualaccepted21 `reports/v3/spatial_evaluation/metrics_by_group.csv` underrecord.root, verifyfileSHAagainstpinned21manifestBEFOREread. Exposeboundedselected+strongbaselinepooledOOFandseen2024/25metricsperunit, withscope/horizon/ncells/recordcounts/deviance/MAE/RMSE/bias/WAPE+status/totals/floorauditwherepresent. CSVcolumns: scope,dimension,group,role,method,n,mean_poisson_deviance,mae,rmse,bias,wape,wape_status,total_pred,total_actual,... . **dimensionisnotdim**;lookatactualvalues ratherthanassumingoverall. Keep2026separatebiaseddiagnostic;noselectionchange. Allquery/filterlogicin24FUNCTIONS, runtime.pyonlyverifiedread/delegation. AddpurefixturetestandliveHTTPnumericparityagainsthashboardCSV (independentcomparison, notonlymethodIDs).
2. **OpenAPI usableexamples/schemas.** Currentpaths+error/unavailableexamplesminimal, norequestBodyschemas/no200examples. Addboundedrequestschemasandactualpublicsuccess/error/unavailableexamplesforprediction/history/geometry/evaluation routes, especiallybothspatialunits/provinceV2. Reuseactualsaved13/22publicfixtures oractual001sample_responses, noeventrows/privatepaths. Docsdescribeactualsinglevalidationauthority(nofeatureduplication). Addmeaningfultestsforrequiredfields,maxItems128/strictfields,examplesconsistentactualresponse andactualsavedOpenAPIsmoke. Don'tbuildSwaggerUI/frontend.
3. **Portableassemblerchecks.** Alsoapplyexistinglocal_specskipwrapperto14and23(and24asneeded)ignoredpayloadintegrationtests, keepingpureassemblerfixtures/canonicalsourcecontracttests. Freshclonewithout.ai-teammustnotfailsolelyonignoredspecabsence;skipwithreason,notfakepass. Thisexplicitlyextendsprior20/21/22instruction;nouserconfirmationneeded. AddSciPy==1.13.1toconstraints(actual.venvPython3.9.6). Noinstall/upgrade.
4. **AuditableactualHTTPfailclosed/read-onlyevidence.** Extendexistinghelperboundedly:
   - recordbefore/afterhashesagainsttrustedpinsforconsumedmanager/componentrecords,source/config/geometry/catalogruntimedata andchosen13/22bundle/baselinestats files (boundedconsumedset,notentirerawhistory). Checkunchanged;writeaggregateevidenceinsideNEWsmokerootonly. Startupalreadyverifieschains; donotrerunacceptedpipelines.
   - addONEclearlylabelledtest-fixtureliveHTTP503caseafterhealthyserverstops: useCOPIEDmanagerlockwitha deliberatelywrongsourcehash, nevermodifyrealpins/artifacts. Startsameappwithserver-sideinjectedload_runtime(...fixturelock...), verify/health200,/ready503stablehash/unavailablecode, prediction503sanitised/nozero,stoponlyownprocess. Fixture isnotacceptedproductionconfig; no newpublicAPIfeature/endpoint. CanbuildchildPythonfactoryinsideexistingworker-authoredsmokeCLI;nofixtureAPIimportsfrom.ai-team. Failclosedmustoccurbeforeexec/deserialization. No arbitraryclientpaths.
   - keepfull001checks;actualnewroot002. Handlecleanup/evidenceonfailureswithoutkillingothers. Noextraoperationalfeatures.

# Manager policy clarifications

- V2provincecompatibilitymayremainoptionalforresearchreadinessIFcomponentstatusandroute503explicit;actualavailableV2muststillpasssaved13parity(current001does). Notpermissiontoomitprovinceendpoint.
- StaticCORS/bodylimitsbeforeverifiedconfigacceptableiftheirpubliccontractmatchespinnedconfig;don'taddframework/configrefactor.
- Preserveallprediction/history/geometryresultsfrom001; onlyevaluationcontent/docs/verificationfixes. Currentsource24/configpinsareforintegrationtestsonly;Codexmustrefreshafteryourcodechangesbeforeactualruntime.

# Report / commands

Changedfiles,orderedpayloads/exactassembly, targetedAPI+assembler, actualintegration, fullbackendregression, smoke002commands, checksactuallyrun(none)/notrun, remaininglimits. Givecurrent24/configFUNCTIONShashproposalifconvenientbutdoNOTwritepinsorclaimacceptance. CodexwillcheckactualHTTPandartifactdata;nofurthermodelstage.
