# V2 feature and cohort policy (before v2 fitting)

User authorizes real external data and feature experiments: festivals/important
days, weather, season, time of day, traffic. Existing v1 frozen; v2 is a separate
research experiment. No performance claim before actual evaluation.

## Labels and date repair
Use original cached MOT CSV rows, not new XLSX-only events. Exact ACC_CODE
publisher-counterpart typed XLSX date may resolve an original slash-date row
only if unique by ID, in that row's own candidate set and supporting context
agrees. Preserve strict v1 ID-other-field conflicts. 2022 is mixed-format, so
no single global D/M or M/D parser is valid. Missing/nonmatching/context-conflict
counterparts remain uncertain. Save provenance and counts per decision.
2024/25 unambiguous Excel dates unchanged; 2026 no-ID diagnostic never labels.
Keep other v1 reasons/masks, including missing province and coordinate exclusion,
for a clean first comparison of date evidence. Rebuild uncertain candidate-day
flags after repair. Each selected count is recorded MOT-source count, not true
complete all-road accidents. Unknown labels are not zero. Eligibility remains
an outcome-derived offline research filter, unavailable for prospective claims.

## Units / known-before-journey inputs
Primary unit province-day. Additional separate province x 6-hour block experiment
(00-06,06-12,12-18,18-24 local) addresses time of day. Issue previous day18:00
Asia/Bangkok for both. Known block boundaries are inputs; actual event time only
defines labels. Broadcast unresolved daily flags to all four blocks to avoid
claiming missing-time events are known zeros. Never directly compare daily and
6-hour errors as if the targets were identical. Sum block predictions for a
separately labelled daily reconciliation diagnostic if useful.

Core date inputs: province,weekday,month,weekend,day-of-month and cyclical
day-of-year(sin/cos). Timeblock categorical for block unit. No rawyear/timestamp,
source IDs, outcomes, incident weather, cause, death/injury or vehicle-involved
counts as features.

Festival inputs: recurring SongkranApr13-15/NewYearDec31Jan1, nearest signed
distance clipped14days, pre/post windows1-3 and4-7days. Calendar lookup crosses
year boundaries correctly, known deterministically; explicit conventions not
optimized from scores. Reviewed bankholiday snapshot with add/remove actions
and conservative known_from; unknown calendar coverage remains unknown, not
nonholiday. Date-only announcement available end of day local. Special days
not announced at issue are unavailable. Bankholiday != publicholiday.

Season inputs: month proxy hot(Mar-May),wet(Jun-Oct),cool(Nov-Feb), clearly
a simplistic calendar proxy with regional limitations, not observed rain or
proof Thailand has identical seasons. Cyclical day terms and province allow
regional/month patterns; test marginal value rather than assume improvement.

Weather: JMA GSM archived previous_day2 rain sum/temp mean from09 at province
representative point. Complete24h/6h only; no partial rainfall sums. Max nominal
issuebound +6h buffer <= issue; units/timezone checked. Missing source remains
missing, train-only imputation/missing indicators. Never replace with target-day
observed/reanalysis weather. Point and delivery-time assumptions remain research
limitations. Report geographic/time coverage before any comparison.

Traffic: DOH annual survey-point mean/median AADT, heavy-share mean and station
coverage per province; never sum to unique provincial cars or label real time.
Use newest PRIOR survey year whose max(resource_created,resource_modified)+1day
<= issue. Catalog-vintage proxy does not prove historical bytes. No targetyear
annual actual in forecasts. Missing -> missing; no future nearest/backfill.

History: separate CONDITIONAL sensitivity scenario only, not primary claims.
If added, use an explicit conservative30-day minimum publication-delay
assumption, and no label whose event-end+30days >issue. Rolling windows must
preserve unknown labels and coverage denominators; no hindsight filling.
Historical source publication still unproved. Provide same strong rolling
baseline in that scenario. This sensitivity cannot silently replace primary
experiment or be called operational. If not implemented yet mark pending.

## Evaluation commitments
Lock v2 model protocol after panel verification but before fitting. Compare
Poisson,RandomForest,HGB plus strong fitted-only global/province/province-weekday
(and province-block/province-block-weekday) baselines on IDENTICAL keys perunit.
Feature ablation fixed groups: cleaned core; +festival/bankcalendar/season;
+archivedweather; +as-oftraffic; fullgroup removal tests as feasible. Missing
weather does not change cohort permodel; any completecoverage sensitivity uses
same explicit fixedkeys for every comparator and is separately reported.
Same four chronological2022/23 folds. 2024/25 already seen development diagnostics,
not untouched tests. Do not pick winner from later-year results. New v2 cohort
differs from v1; no numeric cross-version superiority claim without sharedkeys.
Primary Poisson deviance; MAE/RMSE/bias/coverage secondary; report fold stability,
paired calendar-block uncertainty and honest failure to beat strongest baseline.
No frontend/dashboard build yet; retain planned analytics/visualization docs.
