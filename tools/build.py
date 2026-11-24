"""Merge cut-off tables + school info, backtest prediction methods, write site/data.js."""
import csv, json, re, math, statistics as st
from pathlib import Path

RAW = Path(__file__).parent / "raw"
YEARS = [2023, 2024, 2025, 2026]
TRACKS = ["IP", "PG3", "PG2", "PG1", "aff_IP", "aff_PG3", "aff_PG2", "aff_PG1"]
# Highest possible AL in each posting group's range (a cut-off at this value means
# the school still had places, i.e. anyone eligible for that group got in).
CAP = {"IP": 22, "PG3": 22, "PG2": 25, "PG1": 30}

def parse(v):
    v = v.strip()
    if not v or v == "-":
        return None
    m = re.match(r"^(\d+)([MDP]?)\*?$", v)
    if not m:
        raise ValueError(v)
    return {"v": int(m.group(1)), "hcl": m.group(2) or None}

cop = {}  # school -> track -> year -> {"v","hcl"}
for y in YEARS:
    with open(RAW / f"cop{y}.csv", newline="") as f:
        for row in csv.DictReader(f):
            s = row["school"].strip()
            for t in TRACKS:
                p = parse(row[t])
                if p:
                    cop.setdefault(s, {}).setdefault(t, {})[y] = p

# ---------- school info ----------
def norm(name):
    n = name.upper().replace("’", "'").replace(",", "")
    for a, b in [("GOVT.", "GOVERNMENT"), ("ST ", "ST. ")]:
        n = n.replace(a, b)
    n = re.sub(r"\((SECONDARY)\)", "", n)
    for w in ["SECONDARY SCHOOL", "SCHOOL", "SECONDARY", "INSTITUTION", "JUNIOR COLLEGE", "HIGH", "GIRLS'", "GIRLS"]:
        n = n.replace(w, " ")
    return re.sub(r"[^A-Z.()' ]", " ", re.sub(r"\s+", " ", n)).strip()

meta = {}
with open(RAW / "meta.csv", newline="") as f:
    for row in csv.DictReader(f):
        meta[row["school_name"].upper()] = row

ALIASES = {
    "Anglo-Chinese (Independent) (Secondary)": "ANGLO-CHINESE (INDEPENDENT)",
    "Hwa Chong Institution (Secondary)": "HWA CHONG",
    "Raffles Institution (Secondary)": "RAFFLES",
    "St. Joseph's Institution (Secondary)": "ST. JOSEPH'S",
    "Dunman High (Secondary)": "DUNMAN HIGH",
    "Dunman": "DUNMAN",
    "National Junior College (Secondary)": "NATIONAL",
    "Temasek Junior College (Secondary)": "TEMASEK JUNIOR COLLEGE",
    "Temasek": "TEMASEK",
    "Nanyang Girls' High": "NANYANG",
    "Tanjong Katong Girls'": "TANJONG KATONG GIRLS",
    "Tanjong Katong": "TANJONG KATONG",
    "Crescent Girls'": "CRESCENT",
}
# Secondary sections of these schools are boys-only (data.gov.sg lists the whole
# S1-JC2 school, which is co-ed at JC level).
BOYS_AT_SEC = {"Hwa Chong Institution (Secondary)", "Raffles Institution (Secondary)",
               "Anglo-Chinese (Independent) (Secondary)", "St. Joseph's Institution (Secondary)"}

def find_meta(school):
    # exact name-based lookups first, then normalised
    raw_upper = meta
    special = {
        "Temasek Junior College (Secondary)": "TEMASEK JUNIOR COLLEGE",
        "Temasek": "TEMASEK SECONDARY SCHOOL",
        "Dunman High (Secondary)": "DUNMAN HIGH SCHOOL",
        "Dunman": "DUNMAN SECONDARY SCHOOL",
        "Tanjong Katong Girls'": "TANJONG KATONG GIRLS' SCHOOL",
        "Tanjong Katong": "TANJONG KATONG SECONDARY SCHOOL",
        "National Junior College (Secondary)": "NATIONAL JUNIOR COLLEGE",
        "Nanyang Girls' High": "NANYANG GIRLS' HIGH SCHOOL",
        "Raffles Institution (Secondary)": "RAFFLES INSTITUTION",
        "Raffles Girls' (Secondary)": "RAFFLES GIRLS' SCHOOL (SECONDARY)",
        "Hwa Chong Institution (Secondary)": "HWA CHONG INSTITUTION",
        "St. Joseph's Institution (Secondary)": "ST. JOSEPH'S INSTITUTION",
        "Anglo-Chinese (Independent) (Secondary)": "ANGLO-CHINESE SCHOOL (INDEPENDENT)",
        "Anglo-Chinese (Barker Road)": "ANGLO-CHINESE SCHOOL (BARKER ROAD)",
        "Methodist Girls' (Secondary)": "METHODIST GIRLS' SCHOOL (SECONDARY)",
        "Singapore Chinese Girls'": "SINGAPORE CHINESE GIRLS' SCHOOL",
        "Crescent Girls'": "CRESCENT GIRLS' SCHOOL",
        "Cedar Girls'": "CEDAR GIRLS' SECONDARY SCHOOL",
        "CHIJ St. Nicholas Girls' (Secondary)": "CHIJ ST. NICHOLAS GIRLS' SCHOOL",
        "Paya Lebar Methodist Girls' (Secondary)": "PAYA LEBAR METHODIST GIRLS' SCHOOL (SECONDARY)",
        "St. Andrew's": "ST ANDREW'S SCHOOL (SECONDARY)",
        "Catholic High (Secondary)": "CATHOLIC HIGH SCHOOL",
        "Maris Stella High (Secondary)": "MARIS STELLA HIGH SCHOOL",
        "River Valley High (Secondary)": "RIVER VALLEY HIGH SCHOOL",
        "Fairfield Methodist (Secondary)": "FAIRFIELD METHODIST SCHOOL (SECONDARY)",
        "Geylang Methodist (Secondary)": "GEYLANG METHODIST SCHOOL (SECONDARY)",
        "St. Margaret's (Secondary)": "ST. MARGARET'S SCHOOL (SECONDARY)",
        "St. Patrick's": "ST. PATRICK'S SCHOOL",
        "Gan Eng Seng": "GAN ENG SENG SCHOOL",
        "Hai Sing Catholic": "HAI SING CATHOLIC SCHOOL",
        "Assumption English": "ASSUMPTION ENGLISH SCHOOL",
        "Bukit Panjang Govt. High": "BUKIT PANJANG GOVT. HIGH SCHOOL",
        "Kuo Chuan Presbyterian": "KUO CHUAN PRESBYTERIAN SECONDARY SCHOOL",
        "Chung Cheng High (Main)": "CHUNG CHENG HIGH SCHOOL (MAIN)",
        "Chung Cheng High (Yishun)": "CHUNG CHENG HIGH SCHOOL (YISHUN)",
        "CHIJ Secondary (Toa Payoh)": "CHIJ SECONDARY (TOA PAYOH)",
        "CHIJ Katong Convent": "CHIJ KATONG CONVENT",
        "CHIJ St. Joseph's Convent": "CHIJ ST. JOSEPH'S CONVENT",
        "CHIJ St. Theresa's Convent": "CHIJ ST. THERESA'S CONVENT",
    }
    key = special.get(school)
    if key:
        return raw_upper.get(key)
    for suffix in [" SECONDARY SCHOOL", " HIGH SCHOOL", " SCHOOL", ""]:
        cand = school.upper().replace("’", "'") + suffix
        if cand in raw_upper:
            return raw_upper[cand]
        cand2 = school.upper().replace(" HIGH", "") + suffix
        if cand2 in raw_upper:
            return raw_upper[cand2]
    return None

# ---------- prediction methods ----------
def series(s, t, upto):
    d = cop.get(s, {}).get(t, {})
    return [d[y]["v"] for y in YEARS if y <= upto and y in d]

def m_naive(h): return h[-1]
def m_mean(h): return sum(h) / len(h)
def m_wavg(h):
    w = [1, 2, 3, 4][-len(h):]
    return sum(a * b for a, b in zip(h, w)) / sum(w)
def make_rev(alpha):
    def f(h):
        if len(h) < 2:
            return h[-1]
        prev_mean = sum(h[:-1]) / len(h[:-1])
        return h[-1] + alpha * (prev_mean - h[-1])
    return f

METHODS = {"same as last year": m_naive, "average of all years": m_mean,
           "recency-weighted average": m_wavg}
for a in [0.2, 0.3, 0.4, 0.5, 0.6]:
    METHODS[f"last year pulled {int(a*100)}% back to its own average"] = make_rev(a)

def clipv(x, t):
    base = t.replace("aff_", "")
    return max(4, min(CAP[base], x))

def backtest():
    """Predict each year Y (2025, 2026) from years before it; non-affiliated tracks only."""
    res = {k: [] for k in METHODS}
    for s in cop:
        for t in ["IP", "PG3", "PG2", "PG1"]:
            for target in [2025, 2026]:
                d = cop[s].get(t, {})
                if target not in d:
                    continue
                h = series(s, t, target - 1)
                if len(h) < 2:
                    continue
                actual = d[target]["v"]
                for k, f in METHODS.items():
                    res[k].append((t, target, clipv(f(h), t), actual))
    out = {}
    for k, rows in res.items():
        err = [p - a for _, _, p, a in rows]
        pg3 = [p - a for t, _, p, a in rows if t == "PG3"]
        out[k] = {"n": len(err), "mae": sum(abs(e) for e in err) / len(err),
                  "mae_pg3": sum(abs(e) for e in pg3) / len(pg3),
                  "exact_pg3": sum(1 for e in pg3 if round(e) == 0) / len(pg3)}
    return out, res

bt, res_rows = backtest()
best = min(bt, key=lambda k: bt[k]["mae_pg3"])
print("Backtest (predict 2025 & 2026 from earlier years):")
for k, v in sorted(bt.items(), key=lambda kv: kv[1]["mae_pg3"]):
    print(f"  {k:48s} n={v['n']:4d}  MAE all={v['mae']:.3f}  MAE PG3={v['mae_pg3']:.3f}  exact PG3={v['exact_pg3']:.0%}")
print("Best:", best)

# Error spread of the best method, and the year-wide ("cohort") component.
rows = res_rows[best]
errs_pg3 = [p - a for t, _, p, a in rows if t == "PG3"]
sd_total = st.pstdev(errs_pg3)
bias = st.mean(errs_pg3)
# year-wide shift: mean change across uncapped PG3 schools each year
shifts = []
for y in [2024, 2025, 2026]:
    ch = []
    for s in cop:
        d = cop[s].get("PG3", {})
        if y in d and y - 1 in d and d[y]["v"] < 22 and d[y - 1]["v"] < 22:
            ch.append(d[y]["v"] - d[y - 1]["v"])
    shifts.append(st.mean(ch))
    print(f"  mean PG3 change into {y}: {st.mean(ch):+.2f} (n={len(ch)})")
sd_cohort = st.pstdev(shifts) if len(shifts) > 1 else 0.5
sd_cohort = max(sd_cohort, 0.35)
sd_school = math.sqrt(max(sd_total ** 2 - sd_cohort ** 2, 0.25))
print(f"error sd total={sd_total:.3f} bias={bias:+.3f} cohort sd={sd_cohort:.3f} school sd={sd_school:.3f}")

# ---------- assemble ----------
f_best = METHODS[best]
schools = []
missing_meta = []
for s, tracks in cop.items():
    if 2026 not in set(y for t in tracks.values() for y in t):
        continue  # school no longer posting in latest year
    m = find_meta(s)
    if not m:
        missing_meta.append(s)
    hist, pred, stale = {}, {}, []
    for t, d in tracks.items():
        hist[t] = {str(y): (str(d[y]["v"]) + (d[y]["hcl"] or "")) for y in YEARS if y in d}
        h = series(s, t, 2026)
        if h:
            pred[t] = round(clipv(f_best(h), t), 2)
            if 2026 not in d:
                stale.append(t)
    nature = (m or {}).get("nature", "")
    if s in BOYS_AT_SEC:
        nature = "BOYS"
    mts = [x for x in [(m or {}).get("mt1"), (m or {}).get("mt2"), (m or {}).get("mt3")] if x and x != "na"]
    schools.append({
        "name": s,
        "full": (m or {}).get("school_name", s).title().replace("'S", "'s").replace("Chij", "CHIJ"),
        "postal": (m or {}).get("postal_code", ""),
        "zone": (m or {}).get("zone", "").title(),
        "town": (m or {}).get("town", "").title(),
        "gender": {"BOYS": "Boys", "GIRLS": "Girls", "CO-ED": "Co-ed"}.get(nature, ""),
        "type": (m or {}).get("type", "").title(),
        "sap": (m or {}).get("sap") == "Yes",
        "autonomous": (m or {}).get("autonomous") == "Yes",
        "ipSchool": "IP" in tracks,
        "mt": [x.title() for x in mts],
        "hist": hist,
        "pred": pred,
        "stale": stale,
    })
schools.sort(key=lambda x: x["name"])
print("schools:", len(schools), "missing meta:", missing_meta)

model = {
    "method": best,
    "backtest": {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in bt.items()},
    "sdTotal": round(sd_total, 3), "sdCohort": round(sd_cohort, 3), "sdSchool": round(sd_school, 3),
    "bias": round(bias, 3),
    "yearShifts": {str(y): round(v, 2) for y, v in zip([2024, 2025, 2026], shifts)},
    "cap": CAP,
}
out = Path(__file__).parent.parent / "data.js"
out.write_text("// Generated by build.py. Cut-offs: sgschooling.com (2023, 2025, 2026 intakes), "
               "skoolopedia.com (2024 intake). School info: data.gov.sg General Information of Schools.\n"
               f"window.SCHOOLS = {json.dumps(schools, ensure_ascii=False)};\n"
               f"window.MODEL = {json.dumps(model)};\n")
print("wrote", out, out.stat().st_size, "bytes")
