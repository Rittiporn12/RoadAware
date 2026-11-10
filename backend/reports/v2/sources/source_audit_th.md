# รายงานตรวจแหล่งข้อมูลภายนอก v2 (Notebook 09)

สร้างเมื่อ (UTC): 2026-11-10T10:59:47+00:00 | สถานะ: งานวิจัยระหว่างดำเนินการ ไม่ใช่ระบบพยากรณ์ที่พร้อมใช้ | ยังไม่มีการเทียบโมเดล

## 1. หลักฐานวันที่รายปี (ACC_CODE เดิมตรงตัว + วันที่ typed ใน XLSX + บริบทจังหวัด/เวลา)

| ปี ค.ศ. | แถว CSV v1 | กำกวมใน v1 | resolve (ID+วันที่+บริบท) | กำกวมที่ resolve | ไม่ตรง | M/D ตรง/เทียบ | D/M ตรง/เทียบ | บริบท | นโยบาย |
|---|---|---|---|---|---|---|---|---|---|
| 2021 | 20062 | 7413 | 20062 | 7413 | 0 | 20062/20062 | 898/20062 | {'agree': 20062} | resolve_only_rows_with_unique_typed_id_date_and_context_agreement |
| 2022 | 20566 | 7268 | 8135 | 7268 | 0 | 867/8135 | 8135/8135 | {'not_evaluated': 12431, 'agree': 8135} | resolve_only_rows_with_unique_typed_id_date_and_context_agreement |
| 2023 | 23841 | 8295 | 22922 | 7376 | 0 | 22922/22922 | 968/22922 | {'agree': 22922, 'not_evaluated': 919} | resolve_only_rows_with_unique_typed_id_date_and_context_agreement |
| 2024 | 23952 | 0 |  |  |  | / | / |  | csv_dates_unambiguous_no_resolution_needed |
| 2025 | 23715 | 0 |  |  |  | / | / |  | csv_dates_unambiguous_no_resolution_needed |
| 2026 | 15239 | 6034 |  |  |  | / | / |  | diagnostic_only_no_acc_code_not_a_label |

ข้อสรุปเป็นรายปีและรายแถว ไม่ใช้ parser M/D หรือ D/M แบบรวมทั้งปี (2022 มีรูปแบบผสม); การ resolve เป็นการอ้างอิงคู่ข้อมูลของผู้เผยแพร่ ไม่ใช่ ground truth อิสระ; ID ซ้ำ/ขัดแย้ง/บริบทไม่ตรงยังถูกกักกัน; แถวที่มีเฉพาะใน XLSX ไม่ถูกเพิ่ม; ปี 2026 ไม่มี ID จึงเป็น diagnostic เท่านั้น
เอกสาร data dictionary ของ MOT: no data-dictionary resource listed in the current MOT package (nothing fetched)

## 2. ความพร้อมของแหล่ง feature

| กลุ่ม | สถานะ | หลักฐาน | การใช้ที่อนุญาตในขั้นถัดไป | นโยบาย available-at | ความเสี่ยง leakage |
|---|---|---|---|---|---|
| holiday_festival | partial | reviewed BOT bank-holiday records applied 95/95; annual bases applied for years [2021, 2022, 2023, 2024, 2025] of [2021, 2022, 2023, 2024, 2025]; sources with bytes/snapshot 13/13; scope BOT_national_financial_institution_holiday (not public holidays); completeness not claimed; recurring Songkran/New Year rules are deterministic; no national public-holiday calendar | recurring fixed-festival indicators/distances (Songkran, New Year); reviewed BOT bank-holiday as-of flags/distances only where calendar_as_of coverage is known; no public-holiday flag | fixed recurring dates known in advance; bank-holiday records only when known_from + 1 day 00:00 local <= issue time; removals applied in as-of order | low for fixed festivals; medium for bank holidays (publication latency proxy); high if special days announced after issue are used |
| weather | partial | JMA GSM previous_day2 chunks with data: 7/80; province-years retained: 35/385, complete (all hours valid): 31/385; negative precipitation hours masked to NaN (raw JSON kept): 24; stop reason: repeated_failures; daily rows 12775 (complete rain 12735); issue bound = valid - 48 h, buffer 6 h, all issue_bound_ok=True | archived JMA GSM previous_day2 forecasts aggregated per province-day/6 h block, only rows with complete hours and issue_bound_ok | nominal issue bound = valid time - 48 h; require bound + 6 h buffer <= target day - 1 at 18:00 local | medium: API lead is nominal and archive delivery latency is unverified; never substitute ERA5/observations |
| season | derived | calendar-month proxy computed from the target date in the next task; no external source | calendar-month season proxy (not actual rain, not uniform across Thailand) | deterministic from target date | low |
| timeblock | derived | province x 6 h target blocks derived from each event's own time in the next task (label side only) | define the TARGET unit from each event's own time; never use an event's time to predict that same event | block boundaries are deterministic; event times are labels only | high if event time is used as an input feature |
| traffic | collected | normalized DOH AADT survey years: 6/6; availability proxy max(created,last_modified)+1d | province mean/median AADT, heavy-share mean and survey coverage from PRIOR available vintages only (never sums) | survey_year < target year and max(resource created, last_modified) + 1 day <= issue time (catalog proxy) | medium: catalog timestamps are proxies; current bytes may be revised |
| history | blocked | report availability at issue time not verified; conditional research only | blocked for operational claims; only explicitly conditional research runs that state report-date assumptions | unknown: report availability/latency at issue time not verified | high |

## 3. จราจร (DOH AADT)

Annual average daily traffic (vehicles/day) at DOH survey points on DOH highways. Survey-point AADT cannot be summed into unique vehicles or real-time flow; later stages may use only mean/median/survey-coverage summaries per province.
Per-resource proxy available_from = max(catalog created, catalog last_modified) + 1 day (CKAN timestamps read as UTC). created alone is not conservative when bytes were revised. A survey vintage may feed a target date only if survey_year < target year AND available_from <= issue time. The catalog-vintage proxy does not prove the current bytes were publicly delivered then. Never use the target year's own annual AADT.

แถวที่ว่างทุกคอลัมน์ใน CSV เป็นบรรทัดว่าง (non-record) ไม่ใช่จุดสำรวจซ้ำ จึงนับแยกและไม่เข้าสถิติ; key ซ้ำนับเฉพาะแถวที่มีข้อมูลและ key ครบ; แถวที่ระบุตัวตนไม่ครบไม่ถูกรวม/เดา; ชื่อจังหวัดใช้แผนที่ alias ที่ตรวจแล้วแบบตรงตัวเท่านั้น (พระนครศรีอยุธยา -> อยุธยา) โดยเก็บข้อความดิบไว้ใน province_raw

| ปีสำรวจ พ.ศ. | สถานะ | แถวที่อ่าน | บรรทัดว่าง | station | key ซ้ำ | ระบุตัวตนไม่ครบ | total ใช้ได้ (station) | total ไม่ตรงผลรวม | available_from (proxy, UTC) | ฐาน |
|---|---|---|---|---|---|---|---|---|---|---|
| 2563 | normalized | 2701 | 0 | 2701 | 0 | 0 | 2701 | 0 | 2024-06-01T07:41:10.140471+00:00 | max(created,last_modified)+1d |
| 2564 | normalized | 2709 | 0 | 2709 | 0 | 0 | 2709 | 0 | 2022-03-25T06:10:50.811162+00:00 | max(created,last_modified)+1d |
| 2565 | normalized | 2701 | 0 | 2701 | 0 | 0 | 2701 | 0 | 2024-06-01T07:48:05.556631+00:00 | max(created,last_modified)+1d |
| 2566 | normalized | 2710 | 0 | 2710 | 0 | 0 | 2710 | 0 | 2025-05-30T06:56:57.278942+00:00 | max(created,last_modified)+1d |
| 2567 | normalized | 4866 | 2130 | 2736 | 0 | 0 | 2736 | 0 | 2025-05-30T07:05:03.742919+00:00 | max(created,last_modified)+1d |
| 2568 | normalized | 2739 | 0 | 2739 | 0 | 0 | 2739 | 0 | 2026-01-21T04:28:53.557666+00:00 | max(created,last_modified)+1d |

## 4. ภูมิศาสตร์และจุดสอบถามอากาศ

geoBoundaries gbOpen (OpenStreetMap-derived, ODbL per API metadata); NOT an official Thai-government boundary
shapely representative_point inside each province polygon: a label/proxy weather query point, not a road or event location
shapes 77 (expected 77); joined by ISO code 77, by exact normalized English name 0, unresolved 0; points inside polygon 77; v1 panel provinces without a point: none; point provinces not in panel: none; audited aliases used: {'พระนครศรีอยุธยา': 'อยุธยา'}

## 5. พยากรณ์อากาศย้อนหลัง (Open-Meteo Previous Runs, JMA GSM)

JMA GSM previous_day2 chunks with data: 7/80; province-years retained: 35/385, complete (all hours valid): 31/385; negative precipitation hours masked to NaN (raw JSON kept): 24; stop reason: repeated_failures; daily rows 12775 (complete rain 12735); issue bound = valid - 48 h, buffer 6 h, all issue_bound_ok=True
previous_day2 = value from the run roughly 48 h before valid time (Open-Meteo docs). The nominal issue bound is valid_time - 48 h; this API lead does not prove the historical public delivery latency, so a 6 h publication buffer is assumed and features must satisfy bound + buffer <= target day - 1 at 18:00 local.
Open-Meteo hourly definitions (https://open-meteo.com/en/docs): temperature_2m is the instant value at valid time; precipitation is the sum over the PRECEDING hour. Temperature is bucketed by valid time; precipitation by its interval start (valid time - 1 h): the 00-06 block sums values valid 01:00..06:00 and a day sums 01:00..next-day 00:00. A day whose next-midnight value is not collected stays rain_missing (never a partial sum or 0). The availability guard uses the original valid times / nominal issue bounds of every row used, including rain's interval end.

## 6. ปฏิทินวันหยุดธนาคาร (ธปท.) และเทศกาล

Bank of Thailand national financial-institution (bank) holidays only. NOT the national public-holiday calendar; regional extras are not applied nationally; public holidays when banks open are not bank holidays.
known_from is a date-only conservative circular/announcement date; a record is usable only from the END of that local day (known_from + 1 day 00:00 Asia/Bangkok). Original publication latency is not proven; historical bytes retrieved in 2026 are a research proxy.
reviewed BOT bank-holiday records applied 95/95; annual bases applied for years [2021, 2022, 2023, 2024, 2025] of [2021, 2022, 2023, 2024, 2025]; sources with bytes/snapshot 13/13; scope BOT_national_financial_institution_holiday (not public holidays); completeness not claimed

| แหล่ง | ชนิด | บทบาท | known_from | สถานะตรวจ |
|---|---|---|---|---|
| bot_holiday_main_page | html | context | None | no_entries (html_snapshot_date_text_found) |
| bot_news_20210106_1 | html | parent_page | 2021-01-06 | no_entries (html_snapshot_date_text_found) |
| bot_holidays_2021_png | png | annual_base | 2021-01-06 | live_bytes_identical_to_reviewed_copy |
| bot_holidays_2022_pdf | pdf | annual_base | 2021-07-21 | live_bytes_identical_to_reviewed_copy |
| bot_news_20211110_2 | html | special_announcement | 2021-11-10 | html_snapshot_date_text_found |
| bot_news_20221005 | html | context | 2022-10-05 | no_entries (html_snapshot_date_text_found) |
| bot_holidays_2023_pdf | pdf | annual_base | 2022-07-14 | live_bytes_identical_to_reviewed_copy |
| bot_news_20230130 | html | special_announcement | 2023-01-30 | html_snapshot_date_text_found |
| bot_holidays_2024_pdf | pdf | annual_base | 2023-07-26 | live_bytes_identical_to_reviewed_copy |
| bot_yearend_amendment_2023_pdf | pdf | amendment | 2023-11-13 | live_bytes_identical_to_reviewed_copy |
| bot_news_20240221 | html | special_announcement | 2024-02-21 | html_snapshot_date_text_found |
| bot_holidays_2025_pdf | pdf | annual_base | 2024-09-10 | live_bytes_identical_to_reviewed_copy |
| bot_news_20241127 | html | special_announcement | 2024-11-27 | html_snapshot_date_text_found |

## 7. ช่องว่างของแหล่งข้อมูล (บันทึกจากการรันจริง)

- MOT data dictionary: no data-dictionary resource listed in the current MOT package (nothing fetched). Codex reported the old MOT data-dictionary PDF URL returns HTTP 404 (exact URL not recorded in the task files). A cached search snippet claiming MM/DD is NOT a verified document. Any dictionary resource listed in the live package is snapshotted only; its content is not used as date-format proof. Typed XLSX date cells matched by original ACC_CODE are the primary evidence.
- traffic: BE 2567 has 2130 fully blank CSV lines: counted as non-records and excluded from station data/statistics (raw bytes kept; not duplicate survey points)
- traffic: availability uses max(created, last_modified) + 1 day catalog proxy; it does not prove the current bytes were delivered then
- weather coverage incomplete: 31/385 province-years complete, 35 retained (stop reason: repeated_failures; value-quality masked hours: 24); see weather_coverage.csv missing_reason; rerun to resume
- weather value quality: 24 negative precipitation hours (raw min -0.1 mm) masked to NaN in that hour only; raw JSON unchanged; any 6 h/day rain window containing one is NaN (rain_missing_reason); temperature kept
- weather: Open-Meteo previous_day2 lead is nominal; historical public delivery latency is not verified (6 h buffer assumed)
- calendar: Original 2021/2022 annual BOT PDF URLs following the 2025 pattern returned 404 (not evidence; 2021 infographic and 2022 FIPCS PDF used instead)
- calendar: 2021 Gazette candidate https://ratchakitcha.soc.go.th/DATA/PDF/2563/E/207/T_0062.PDF returned 403 (not evidence; host not allowlisted)
- calendar: No national public-holiday calendar collected; BOT bank holidays are a different, narrower list
- calendar: Further amendments not listed here are unknown: calendar coverage is never claimed complete
- calendar: Historical publication latency of every source is unproven; known_from is the conservative circular/announcement date
