# Goal
Correction1of017. Read AGENTS.md/original017 and preserve every original requirement. Claude authors all code;Codexrunscommands/tests/review. One worker only.

# Evidence
Assembler refused payloadcell_04_functions_3.py line35: `dict(reference,n_cells=int(d.size), 'density_float64_le_sha256':..., 'min':..., 'max':...)` mixes keywordarg and mapping syntax:SyntaxError positionalargumentfollowskeywordargument. No canonical21created, noactualkernelrun. compileall allpayloads+runner+verifier+tests reports this same syntaxerror. Testsdownstream17pass/2fail/19errorsbecause21absent;notindependentbehaviorfailures. Existing016helperfix verifiedsuccessfully:254arraymetriccomparisonsmatches (evidence.ai-team/references/016-002-independent-metrics-helper-fixed.json).

# Scope
017payloads/config/runner/verifier/focusedtests/assembler21extension only ifneeded. Noaccepted14/16–20 sources/results/pins orscientificpolicyedits. No2026reads/scores/modeltraining/frontend/API/memoryfiles. Source21stillnotassembled;Codexwillassembleafteryoufinish.

# Acceptance
Fixsyntax properly;reviewallFUNCTIONS/pipelinecells and testfile forconcreteexecutiondefectsnow (e.g.configkeys/columnnames/types/CSVroundtrips/datetimeperiodmapping/capture/shapes). Cannotexecutecommandswithfiletools;explainwhatwasstaticreviewed,don'tclaimtestsrun. PreservefixedOOFthresholds/science/nohiddengate. Ifadditionalissuesfound,fixtheminthisboundedbatchandreport.
Inspecttest_source_notebook_unexecuted_and_no_handoff_reference andassemblerchecks toensureappropriatepayloadsourcecompilecoverage. No skippingtests/looseningproductionreadiness. No forcedallpasssoftchecks;diagnosticlimitationshonest.

# Verification/report
Codexassembleexactpayloads,runfocused/fulltests,actualfreshroot017-001 (none existsyet),independentverifier/plotsbeforeacceptance. Supplyexactcommands,changedfiles,checksactuallyrun(none),notrun,remainingissues. Keepboundedandconcise.
