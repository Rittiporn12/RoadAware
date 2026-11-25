"""Build the accident file for the website's dashboard page (frontend/public/data/dashboard-v1.json).

Same records as the model, nothing more:
  2564–2568  backend/data/v4/spatial_preparation/selected_events.csv.gz — accidents on DOH highways matched to a
             2-km segment (98,207); split train (2564–2566) / seen_diagnostic (2567–2568)
  2569       the latest backend/rerun-2026-eval-national-*/data/v4/evaluation_2026/row_ledger.csv, eligible rows only
             (Jan–Sep 2569, 15,425) — the unseen test year
Details (time, type, vehicle, cause, weather, casualties, location) come from the original MOT files
(https://datagov.mot.go.th/dataset/roadaccident), joined by ACC_CODE (2564–2568) or by source row (2569).
Columns are stored as small integer codes with a dictionary; the location becomes a 0.05° grid cell (about 5 km).
Run:  .venv/bin/python backend/scripts/build_dashboard_data.py
"""
import json, re, sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BACK = ROOT / "backend"
OUT = ROOT / "frontend" / "public" / "data" / "dashboard-v1.json"
BASE = date(2021, 1, 1)
CELL = 0.05
LAT0, LON0, NLON = 5.0, 97.0, int((106 - 97) / CELL) + 1

REGIONS = {
    "เหนือ": "เชียงราย เชียงใหม่ น่าน พะเยา แพร่ แม่ฮ่องสอน ลำปาง ลำพูน อุตรดิตถ์",
    "ตะวันออกเฉียงเหนือ": "กาฬสินธุ์ ขอนแก่น ชัยภูมิ นครพนม นครราชสีมา บึงกาฬ บุรีรัมย์ มหาสารคาม มุกดาหาร ยโสธร ร้อยเอ็ด เลย ศรีสะเกษ สกลนคร สุรินทร์ หนองคาย หนองบัวลำภู อำนาจเจริญ อุดรธานี อุบลราชธานี",
    "กลาง": "กรุงเทพมหานคร กำแพงเพชร ชัยนาท นครนายก นครปฐม นครสวรรค์ นนทบุรี ปทุมธานี พระนครศรีอยุธยา พิจิตร พิษณุโลก เพชรบูรณ์ ลพบุรี สมุทรปราการ สมุทรสงคราม สมุทรสาคร สิงห์บุรี สุโขทัย สุพรรณบุรี สระบุรี อ่างทอง อุทัยธานี",
    "ตะวันออก": "จันทบุรี ฉะเชิงเทรา ชลบุรี ตราด ปราจีนบุรี ระยอง สระแก้ว",
    "ตะวันตก": "กาญจนบุรี ตาก ประจวบคีรีขันธ์ เพชรบุรี ราชบุรี",
    "ใต้": "กระบี่ ชุมพร ตรัง นครศรีธรรมราช นราธิวาส ปัตตานี พังงา พัทลุง ภูเก็ต ยะลา ระนอง สงขลา สตูล สุราษฎร์ธานี",
}
PROV_REGION = {p: r for r, ps in REGIONS.items() for p in ps.split()}
PROV_ALIAS = {"อยุธยา": "พระนครศรีอยุธยา", "กรุงเทพฯ": "กรุงเทพมหานคร"}


def col(df, *names):
    for n in names:
        if n in df.columns:
            return df[n]
    raise KeyError(names)


def parse_day(v, month_first=False):
    if pd.isna(v):
        return None
    if isinstance(v, (int, float)) or re.fullmatch(r"\d+(\.0)?", str(v).strip()):
        d = date(1899, 12, 30) + timedelta(days=int(float(v)))          # Excel serial date
    else:
        s = str(v).strip().split(" ")[0]
        try:
            a, b, yy = (int(x) for x in s.split("/"))
            dd, mm = (b, a) if month_first else (a, b)
        except ValueError:
            return None
        if yy > 2400:
            yy -= 543
        try:
            d = date(yy, mm, dd)
        except ValueError:
            return None
    return (d - BASE).days


def parse_hour(v):
    if pd.isna(v):
        return -1
    s = str(v).strip()
    m = re.match(r"^(\d{1,2}):(\d{2})", s)
    if m:                                                                # "13:45"
        h = int(m.group(1))
        return h if 0 <= h <= 23 else -1
    try:
        f = float(s)
    except ValueError:
        return -1
    if 0 <= f < 1:                                                       # fraction of a day (Excel time, 2567 file)
        return int(round(f * 24 * 60)) // 60 % 24
    h = int(f)                                                           # "13.45"
    return h if 0 <= h <= 23 else -1


def num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0).clip(lower=0).astype(int)


SEL = BACK / "data/v4/spatial_preparation/selected_events.csv.gz"
RAW = {y: BACK / f"data/raw/accidents/accidents_{y}_original.csv" for y in range(2564, 2569)}
NEW_2569 = BACK / "data/v3/evaluation_2026_source/20261111/accident2026.csv"
LEDGER = sorted(BACK.glob("rerun-2026-eval-national-*/data/v4/evaluation_2026/row_ledger.csv"))[-1]
SPLIT_TH = {"train": "ข้อมูลฝึก", "seen_diagnostic": "ข้อมูลตรวจ", "test_2026": "ข้อมูลทดสอบ"}


def details(df):
    """Attribute columns of an original MOT file (both column layouts)."""
    return pd.DataFrame({
        "hour": col(df, "เวลา").map(parse_hour).values,
        "type": col(df, "ลักษณะการเกิดเหตุ", "ลักษณะการเกิดอุบัติเหตุ").astype(str).str.strip().values,
        "veh": col(df, "รถคันที่1").astype(str).str.strip().values,
        "cause": col(df, "มูลเหตุสันนิษฐาน").astype(str).str.strip().values,
        "wx": col(df, "สภาพอากาศ").astype(str).str.strip().values,
        "agency": col(df, "หน่วยงาน").astype(str).str.strip().values,
        "dead": num(col(df, "ผู้เสียชีวิต", "จำนวนผู้เสียชีวิต")).values,
        "serious": num(col(df, "ผู้บาดเจ็บสาหัส", "จำนวนผู้บาดเจ็บสาหัส")).values,
        "minor": num(col(df, "ผู้บาดเจ็บเล็กน้อย", "จำนวนผู้บาดเจ็บเล็กน้อย")).values,
        "lat": pd.to_numeric(col(df, "LATITUDE"), errors="coerce").values,
        "lon": pd.to_numeric(col(df, "LONGITUDE"), errors="coerce").values,
    })


def read_raw(path):
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    return df


rows = []
sel = pd.read_csv(SEL, low_memory=False)
sel["be"] = sel["event_uid"].str.split(":").str[0].astype(int)
sel["code"] = sel["event_uid"].str.split(":").str[1].astype("int64")
for be, path in RAW.items():
    s_y = sel[sel["be"] == be]
    raw = read_raw(path).drop_duplicates("ACC_CODE").set_index("ACC_CODE")
    src = raw.loc[s_y["code"].values].reset_index(drop=True)
    t = details(src)
    t["be"] = be
    t["day"] = [(date.fromisoformat(x) - BASE).days for x in s_y["event_date"]]
    t["prov"] = s_y["province_key"].astype(str).str.replace("\u0e4d\u0e32", "\u0e33", regex=False).replace(PROV_ALIAS).values
    t["split"] = s_y["split"].values
    rows.append(t)
    print(f"{be}: {len(t)} model records", file=sys.stderr)

led = pd.read_csv(LEDGER, low_memory=False)
led = led[led["exclusive_reason"] == "eligible"]
src = read_raw(NEW_2569).iloc[led["source_row"].values - 1].reset_index(drop=True)
t = details(src)
t["be"] = 2569
t["day"] = [(date.fromisoformat(x) - BASE).days for x in led["event_date"]]
t["prov"] = led["province"].astype(str).str.replace("\u0e4d\u0e32", "\u0e33", regex=False).replace(PROV_ALIAS).values
t["split"] = "test_2026"
rows.append(t)
print(f"2569: {len(t)} model records (eligible, {LEDGER.parent.parent.parent.parent.name})", file=sys.stderr)
for t in rows:
    t.loc[~t["prov"].isin(PROV_REGION), "prov"] = "ไม่ระบุ"
    t.loc[t["hour"] < 0, "hour"] = -1

d = pd.concat(rows, ignore_index=True).sort_values("day", kind="stable").reset_index(drop=True)


# Same category written differently across the years' files
CANON = {
    "type": {"ชนท้าย (ช่องจราจรเดียวกัน)": "ชนท้าย", "ไม่มีรายละเอียด": "ไม่ระบุ"},
    "cause": {"ขับรถเร็วเกินอัตราที่กำหนด": "ขับรถเร็วเกินอัตรากำหนด", "มีการตัดหน้าระยะกระชั้นชิด": "คน/รถ/สัตว์ตัดหน้ากระชั้นชิด"},
}
for k, m in CANON.items():
    d[k] = d[k].replace(m)


def dictionary(series, keep=None, other="อื่นๆ"):
    """Most frequent first; values outside the top `keep` (or seen < 20 times) become 'อื่นๆ'."""
    counts = Counter(series)
    names = [k for k, c in counts.most_common() if c >= 20 and k not in ("nan", "", other, "-")]
    if keep:
        names = names[:keep]
    names.append(other)
    idx = {k: i for i, k in enumerate(names)}
    return names, series.map(lambda v: idx.get(v, len(names) - 1)).astype(int).tolist()


prov_names = sorted(PROV_REGION, key=lambda p: (list(REGIONS).index(PROV_REGION[p]), p)) + ["ไม่ระบุ"]
prov_idx = {p: i for i, p in enumerate(prov_names)}
type_names, type_codes = dictionary(d["type"], keep=10)
veh_names, veh_codes = dictionary(d["veh"], keep=12)
cause_names, cause_codes = dictionary(d["cause"], keep=12)
wx_names, wx_codes = dictionary(d["wx"], keep=6)
ag_names, ag_codes = dictionary(d["agency"], keep=3)
split_keys = ["train", "seen_diagnostic", "test_2026"]
split_codes = d["split"].map({k: i for i, k in enumerate(split_keys)}).astype(int).tolist()

ok = d["lat"].between(5, 21) & d["lon"].between(97, 106)
cell = ((((d["lat"] - LAT0) / CELL).round().astype("Int64") * NLON) + ((d["lon"] - LON0) / CELL).round().astype("Int64"))
cell = cell.where(ok, -1).fillna(-1).astype(int).tolist()

out = {
    "meta": {
        "version": 1,
        "built": datetime.now().strftime("%Y-%m-%d"),
        "source": "https://datagov.mot.go.th/dataset/roadaccident",
        "base_date": BASE.isoformat(),
        "years_be": sorted(d["be"].unique().tolist()),
        "last_day": int(d["day"].max()),
        "records": int(len(d)),
        "grid": {"cell_deg": CELL, "lat0": LAT0, "lon0": LON0, "nlon": NLON},
        "note": "ชุดเดียวกับที่โมเดลใช้: อุบัติเหตุบนทางหลวงกรมทางหลวงที่จับคู่กับช่วงถนนได้ (ห่างไม่เกิน 50 ม.)",
    },
    "dims": {
        "region": list(REGIONS) + ["ไม่ระบุ"],
        "prov": prov_names,
        "provRegion": [list(REGIONS).index(PROV_REGION[p]) if p in PROV_REGION else len(REGIONS) for p in prov_names],
        "split": [SPLIT_TH[k] for k in split_keys],
        "type": type_names, "veh": veh_names, "cause": cause_names, "wx": wx_names, "agency": ag_names,
    },
    "cols": {
        "day": d["day"].tolist(), "hour": d["hour"].astype(int).tolist(),
        "prov": d["prov"].map(prov_idx).astype(int).tolist(),
        "type": type_codes, "veh": veh_codes, "cause": cause_codes, "wx": wx_codes, "agency": ag_codes,
        "split": split_codes, "dead": d["dead"].tolist(), "serious": d["serious"].tolist(), "minor": d["minor"].tolist(), "cell": cell,
    },
}
OUT.parent.mkdir(parents=True, exist_ok=True)
# accident coordinates for the home page's hero map (backend/scripts/build_hero_map.py)
POINTS = BACK / "data/v4/dashboard/points.csv.gz"
POINTS.parent.mkdir(parents=True, exist_ok=True)
d.loc[ok, ["lat", "lon"]].round(5).to_csv(POINTS, index=False)
OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"wrote {OUT.relative_to(ROOT)}  {OUT.stat().st_size/1e6:.2f} MB  records={len(d)}", file=sys.stderr)
for k in ("type", "veh", "cause", "wx", "agency"):
    print(k, out["dims"][k], file=sys.stderr)
