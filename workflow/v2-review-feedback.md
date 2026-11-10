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
