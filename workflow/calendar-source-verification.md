# Calendar source transcription / independent source review

Codex visually inspected ALL pages of cached BOT holiday PDFs 2023, 2024,
2025 on 2026-11-10. They are image-only; empty pypdf text is NOT an empty calendar.
These are source transcriptions for Claude implementation, not model results.
Only national BANK holiday scope, not all public holidays. Regional extras on
last pages must not be applied nationally. Use conservative circular date as
known_from (end of day local); original publication latency is not proven.
Source URLs follow the verified pattern in task004, cached names
evidence/bot-holidays-YEAR.pdf. Hash actual cached files in provenance.

## 2023 original
Cover circular 2022-07-14; Gazette 2022-07-11; signed 2022-06-20.
Verified p2/p3 15 entries (dates Gregorian):
2023-01-02 NewYearObserved; 2023-03-06 MakhaBucha;
2023-04-06 Chakri; 2023-04-13 Songkran; 2023-04-14 Songkran;
2023-05-01 Labour; 2023-05-04 Coronation;
2023-06-05 QueenBirthdayAndVisakhaObserved;
2023-07-28 KingBirthday; 2023-08-01 AsalhaBucha;
2023-08-14 MotherObserved; 2023-10-13 Navamindra;
2023-10-23 Chulalongkorn; 2023-12-05 FatherNational;
2023-12-11 ConstitutionObserved.
Original is NOT complete final calendar: special May5 and later yearend shift
require amendment evidence; do not label completeness true.

## 2024 original
Cover 2023-07-26; Gazette 2023-07-18; signed 2023-06-28.
Verified p2/p3 18 original entries:
2024-01-01 NewYear; 2024-01-02 YearendObserved;
2024-02-26 MakhaObserved; 2024-04-08 ChakriObserved;
2024-04-15 Songkran; 2024-04-16 SongkranObserved;
2024-05-01 Labour; 2024-05-06 CoronationObserved;
2024-05-22 Visakha; 2024-06-03 QueenBirthday;
2024-07-22 AsalhaObserved; 2024-07-29 KingBirthdayObserved;
2024-08-12 Mother; 2024-10-14 NavamindraObserved;
2024-10-23 Chulalongkorn; 2024-12-05 FatherNational;
2024-12-10 Constitution; 2024-12-31 Yearend.
IMPORTANT original Jan2 was later REMOVED/moved to 2023-12-29. Do not use the
unamended Jan2 record for final2024 features. Need record action add/remove,
effective/known_from and as-of view, not simple forever-union of dates.
Official amendment metadata dated 2023-11-01:
https://app.bot.or.th/FIPCS/Thai/PFIPCS_showrelated.aspx?DocID=25660204-02
Potential PDF URL NOT YET VERIFIED: /content/dam/bot/fipcs/documents/FPG/2566/ThaiPDF/25660204.pdf
Verified official HTML extra2024 Apr12, announced 2024-02-21:
https://www.bot.or.th/th/news-and-media/news/news-20240221.html
Do not assume public extra Dec30 also bank holiday without BOT evidence.

## 2025 original
Cover2024-09-10; Gazette2024-09-05; signed2024-08-13.
Verified p2/p3 17 entries:
2025-01-01 NewYear; 2025-02-12 Makha;
2025-04-07 ChakriObserved; 2025-04-14 Songkran; 2025-04-15 Songkran;
2025-05-01 Labour; 2025-05-05 CoronationObserved; 2025-05-12 VisakhaObserved;
2025-06-03 QueenBirthday; 2025-07-10 Asalha; 2025-07-28 KingBirthday;
2025-08-12 Mother; 2025-10-13 Navamindra; 2025-10-23 Chulalongkorn;
2025-12-05 FatherNational; 2025-12-10 Constitution; 2025-12-31 Yearend.
Verified official HTML adds2025 Jun2 andAug11, announced2024-11-27:
https://www.bot.or.th/th/news-and-media/news/news-20241127.html

## Other verified primary HTML evidence / gaps
2021 specialFeb12,Sep24 and shiftOct25 ->Oct22, announced2021-01-06:
https://www.bot.or.th/th/news-and-media/news/news-20210106-1.html
Same source explicitly says banks OPEN Apr12/Jul27 despite public holidays.
2022 APEC Nov16-18 banks OPEN (public regional holidays), announced2022-10-05:
https://www.bot.or.th/th/news-and-media/news/news-20221005.html
Original 2021/22 annual BOT PDF URL pattern404. Calendar not complete yet.
Recurring Songkran Apr13-15 and NewYear Dec31/Jan1 may be separate festival
features across all years; do not require bankholiday membership. Bankcalendar
unknown != nonholiday: preserve coverage/unknown flags, and only derive reliable
holiday distances when requested window calendarcoverage is complete.

## Worker handoff
Read this alongside live feedback before calendar implementation/docs. You may
store transcription as explicit reviewed config records with source page numbers,
hashes and confidence. Snapshot verified HTML sources through the collector.
If amendment PDF cannot be fetched, mark original conflicting Jan2 record excluded
until verified, and mark affected window incomplete rather than wrong. Do not
silently skip all calendar evidence just because PDFs contain no extractable text.

## Additional verified PDFs / HTML (08:48)
Downloaded and visually inspected ALL3 pages each:
evidence/bot-holidays-2022.pdf from verified actual URL
https://www.bot.or.th/content/dam/bot/fipcs/documents/FPG/2564/ThaiPDF/25640124.pdf
Cover2021-07-21; Gazette2021-07-20; signed2021-07-07.17 original entries:
2022-01-03 NewYearObserved; 2022-02-16 Makha; 2022-04-06 Chakri;
2022-04-13 Songkran; 2022-04-14 Songkran; 2022-04-15 Songkran;
2022-05-02 LabourObserved; 2022-05-04 Coronation; 2022-05-16 VisakhaObserved;
2022-06-03 QueenBirthday; 2022-07-13 Asalha; 2022-07-28 KingBirthday;
2022-08-12 Mother; 2022-10-13 Navamindra; 2022-10-24 ChulalongkornObserved;
2022-12-05 FatherNational; 2022-12-12 ConstitutionObserved.
Verified official HTML adds2022Jul29 andOct14, announced2021-11-10:
https://www.bot.or.th/th/news-and-media/news/news-20211110-2.html
Do NOT addpublicJul15/Dec30 asbank holidays withoutspecificevidence.

evidence/bot-yearend-amendment-2023.pdf actualverifiedURL:
https://www.bot.or.th/content/dam/bot/fipcs/documents/FPG/2566/ThaiPDF/25660204.pdf
Cover2023-11-13; Gazette2023-11-10; signed2023-11-01. Page3 explicitly
REMOVES2024-01-02 and ADDS2023-12-29. Use conservativeknown_from2023-11-13.
This now resolves the earlierJan2conflict. Registerhash/sourcep3/transcription.

Verified official HTML adds2023May5, announced2023-01-30:
https://www.bot.or.th/th/news-and-media/news/news-20230130.html
2021 Gazettecandidate URL403 (not evidence):
https://ratchakitcha.soc.go.th/DATA/PDF/2563/E/207/T_0062.PDF

## 2021 official infographic now found and visually verified (08:47)
Official news20210106-1.html embeds this source image (link218 in web view):
https://s7ap1.scene7.com/is/image/bot/news-20210106-1?wid=2000&fmt=png
Downloaded evidence/bot-holidays-2021.png, visually inspected full image.
Image explicitly says updated2021-01-06, national bankholiday scope20entries:
2021-01-01 NewYear; 2021-02-12 Special; 2021-02-26 Makha;
2021-04-06 Chakri; 2021-04-13 Songkran; 2021-04-14 Songkran; 2021-04-15 Songkran;
2021-05-03 LabourObserved; 2021-05-04 Coronation; 2021-05-26 Visakha;
2021-06-03 QueenBirthday; 2021-07-26 AsalhaObserved; 2021-07-28 KingBirthday;
2021-08-12 Mother; 2021-09-24 Special; 2021-10-13 Navamindra;
2021-10-22 ChulalongkornObserved; 2021-12-06 FatherObserved;
2021-12-10 Constitution; 2021-12-31 Yearend.
Use conservative known_from2021-01-06(endofday), so Jan1record would NOT be
available underthissnapshot; recurringNewYearfeature cancoverit separately.
Do NOT backdate allrecords to2020merelybecauseoriginalannualdecreewasolder.
Currentbytesretrieved2026, historicalimageavailabilityitselfnotproven; label
reviewedpublisherdatedsource/researchproxy. Collector needs scene7hostallowlist
ONLYfor this officialembeddedasset and recordsparentBOTpage; no broadnewhosts.
