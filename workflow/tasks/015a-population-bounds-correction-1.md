# Goal
Correctionround1of015: close independentlyreproducedpopulation-labelbounds gaps and fixoneincorrecttestfixture. Preserveallvalidcohort/count/feature/asof/scientificrules andpinnedinputs. ReadAGENTS.md, original015task/protocolrequirementsremain. No models/frontends.

# Actual evidence
Worker015run20261111-130509-89067completed. Codexmechanicallyassembled16cells/14codecells, allcompile. Targetedpytest33pass/1failin3.09s. Actualnewrootbackend/rerun-spatial-prep-015-001 completed90.08s/manifestcomplete, includingFULLpopulationfeatureaudit (72.9scell13). No runtimebypass. Thisrunandalloldaccepteddata/reportsmustremainimmutable. Itisnotacceptedbecausehelperboundsandfixturefailurepersist. Reviewfailrecorded.

# Allowed scope
ONLY notebook19populationhelpersinFUNCTIONS3(actualcell4,.ai-team/handoffs/015/cell_04_functions_3.py) and tests19. No config/runner/datasource/feature/calendar/context/othernotebookcellchanges. All runtimebusinesslogic innotebook. Writeexactsourceedits JSON `.ai-team/handoffs/015a/notebook_cell_edits.json` list `{cell_index:4,old:<exactuniquesubstring>,new:<workerreplacement>}`. Codexmechanicallyappliesedits. Do NOT rewriteentire19notebook orexecutedoutputs. Source-onlyoriginalcellpayloadiscurrentcanonicalsource byte-for-byte. No shell/network/dependencychanges.

# Required corrections and meaningfultests
1. Counterexamples (independent, saved .ai-team/references/015-population-counterexamples.json):
   - ax=population_axes(['seg-a'],'2021-01-01','2021-01-02',fourvalidblocks);keys_from_positions(ax,'daily',[-1]) silentlyreturns2021-01-02 (negativeNumPyindexwrap).
   - sp=sparse_index(ax,'daily',DataFrame(segment_id=['seg-a'],target_date=['2021-01-01'],y_count=[1]));lookup_counts(sp,[-1,2,999]) returns[0,0,0] althoughpositionsareOUTSIDEthedefined2-cellpopulation. Unknownmustnotbecomeconditionalzero.
   - population_size(ax,'unsupported-unit') returns2bytreatinganyunknownunitasdaily.
2. Validateunits daily|6h inALLpublicpopulationhelpers. Validatepositionvectors finite,whole-number,1Dand0<=pos<population_size BEFOREcasting/indexing;rejectnegative/overflow/nonintegral/NaN/infinity/boolvaluesclearlywithPreparationError. Emptypositionarraymayreturnempty. keys↔positionsroundtripmustremainexact forvalidinputs;nosilenttruncation. `sparse_index` shouldcarry explicitpopulationbound/unit/axisevidence forlookup,notonlypositivepositions;lookupmustrequirethisbound (nocallerdefaultwhichletsunknownindicesreturn0). Updateallnormalcalls/testsconsistentlywithoutchangingvalidproducerdata.
3. Validatepositivecountsinsparse_index BEFOREintegercasting:finite,integer>=1,uniquekeys,withinpopulation;rejectfractional/negative/zero/overflowratherthantruncate. EmptypositiveindexislegitimateallzeroWITHINknownpopulation;out-of-boundqueryevenemptyspmustreject.
4. population_axes mustrejectempty/reversed/invaliddateintervals,duplicate/emptysegmentIDs,invalid/duplicateblockaxis;populationiterationsubrangeoutside/reversedmustrejectratherthanemptysuccess. Keepfixedexistingorder(date,segment,block),maxbatch100000,knownzero-countsmeaningunchanged. No rebuildingdatesfromfuturey.
5. Actualfailingtest `test_check_outputs_and_report_suffix` currentlyconstructs `output_paths(BACKEND,CFG)` THENpassesacfgwhoseoutputsarechangedtolinkage_audit/x. Thattests wrongwritepaths. Codexindependentlycalledcheck_outputs(output_paths(BACKEND,badcfg),BACKEND,badcfg) anditREFUSEDcorrectly. Fixfixturetoconstructpathsfromthe SAMEbadcfg;alsoassertnothingcreated/protectedunchanged. Do notweakenrealoutputguardsorchangeinputpathsjusttomaketestpass.
6. Addregressionsforthesecasesplusknownno-recordcell==0,first/lastindex,6hboundaryroundtrip,emptypositivepopulation/batches;exerciseREALhelpers,notduplicatedBooleanlogic. Full001normaldata/featuretables/referencesmustreproduceexactly(asbytesifdeterministic);onlyhelpers/checkmetadataexpectedchange. No alteringlabels,sourcequalitybounds,geometrypredicate,dates,featuresorpopulationexclusions.

# Verification/report
Workerexecutesnothing. CodexappliesJSONedits/compiles,runs targetedtests,actualNEWbackend/rerun-spatial-prep-015-002(fullfeatureauditon),independenthash/count/asof/featureparity/visualchecksandfullregressionaswarranted,thenreview/GitHub. Reportactualchangedfiles/edits,checksrun(none),notrun,remainingissues. Prioractual001successisnotacceptance. No inventedprecision/performanceclaims.
