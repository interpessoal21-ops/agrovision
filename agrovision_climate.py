"""Climate Watch source access: NASA GISTEMP and NOAA GML greenhouse gases."""
from __future__ import annotations
from io import StringIO
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import requests

NASA_GISTEMP_URL = "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv"
NOAA_CO2_URL = "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.csv"
NOAA_CH4_URL = "https://gml.noaa.gov/webdata/ccgg/trends/ch4/ch4_mm_gl.csv"
NOAA_N2O_URL = "https://gml.noaa.gov/webdata/ccgg/trends/n2o/n2o_mm_gl.csv"
SOURCES = {
 "temperature":{"name":"NASA GISS GISTEMP v4","url":"https://data.giss.nasa.gov/gistemp/","baseline":"1951–1980","frequency":"Monthly; publication latency"},
 "co2":{"name":"NOAA GML — Mauna Loa","url":"https://gml.noaa.gov/ccgg/trends/","baseline":"Station monthly mean","frequency":"Monthly; publication latency"},
 "ch4":{"name":"NOAA GML — global marine surface network","url":"https://gml.noaa.gov/ccgg/trends_ch4/","baseline":"Global marine-surface monthly mean","frequency":"Monthly; recent values preliminary"},
 "n2o":{"name":"NOAA GML — global marine surface network","url":"https://gml.noaa.gov/ccgg/trends_n2o/","baseline":"Global marine-surface monthly mean","frequency":"Monthly; recent values preliminary"},
}

def parse_gistemp_csv(text: str) -> pd.DataFrame:
    """Parse the monthly GISTEMP table even when NASA prepends metadata lines."""
    months=("Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec")
    cleaned = str(text).lstrip("\\ufeff")
    header_index = None
    for i, line in enumerate(cleaned.splitlines()):
        cells = [cell.strip().strip('"').lstrip("\\ufeff") for cell in line.split(",")]
        normalized = {cell.lower() for cell in cells}
        if cells and cells[0].lower() == "year" and all(month.lower() in normalized for month in months):
            header_index = i
            break
    if header_index is None:
        preview = " ".join(cleaned.split())[:180]
        raise ValueError(
            "NASA GISTEMP response does not contain the expected monthly CSV header "
            "(Year, Jan…Dec). The source may have returned an HTML/error page or changed format. "
            f"Response begins: {preview!r}"
        )
    frame = pd.read_csv(StringIO("\\n".join(cleaned.splitlines()[header_index:])), skipinitialspace=True)
    frame.columns = [str(column).strip().lstrip("\\ufeff") for column in frame.columns]
    # Normalize harmless whitespace/case differences without accepting a different schema.
    lookup = {str(column).strip().lower(): column for column in frame.columns}
    if "year" not in lookup:
        raise ValueError("NASA GISTEMP monthly table is missing its Year field after header parsing.")
    month_columns = {}
    for month in months:
        source_column = lookup.get(month.lower())
        if source_column is not None:
            month_columns[month] = source_column
    if len(month_columns) != 12:
        missing = [month for month in months if month not in month_columns]
        raise ValueError(f"NASA GISTEMP monthly table is missing month columns: {missing}")
    year_column = lookup["year"]
    selected = frame[[year_column, *month_columns.values()]].copy()
    selected.columns = ["Year", *month_columns.keys()]
    long = selected.melt(id_vars="Year", var_name="Month", value_name="Anomaly_C")
    long["Year"] = pd.to_numeric(long["Year"], errors="coerce")
    long["Anomaly_C"] = pd.to_numeric(long["Anomaly_C"], errors="coerce")
    long["Month_Number"] = long["Month"].map({month: i for i, month in enumerate(months, 1)})
    long = long.dropna(subset=["Year", "Month_Number", "Anomaly_C"])
    long = long[long["Anomaly_C"] > -90].copy()
    if long.empty:
        raise ValueError("NASA GISTEMP monthly table was recognized but contained no valid monthly anomalies.")
    long["Date"] = pd.to_datetime(dict(
        year=long["Year"].astype(int), month=long["Month_Number"], day=1
    ))
    return long[["Date", "Anomaly_C"]].sort_values("Date").reset_index(drop=True)

def _parse_noaa_monthly_csv(text: str,value_column: str,output_column: str) -> pd.DataFrame:
    lines=text.splitlines(); header_index=None; header_line=None
    for i,line in enumerate(lines):
        candidate=line.lstrip().lstrip("#").strip(); low=candidate.lower()
        if all(x in low for x in ("year","month",value_column.lower())) and "," in candidate:
            header_index=i; header_line=candidate; break
    if header_index is None: raise ValueError(f"NOAA file has no recognizable {value_column} CSV header.")
    csv_text="\n".join([header_line,*lines[header_index+1:]])
    frame=pd.read_csv(StringIO(csv_text),skipinitialspace=True)
    frame.columns=[str(c).strip().lower() for c in frame.columns]
    required={"year","month",value_column.lower()}
    if not required.issubset(frame.columns): raise ValueError(f"NOAA file missing columns: {sorted(required)}")
    for col in required: frame[col]=pd.to_numeric(frame[col],errors="coerce")
    frame=frame.dropna(subset=list(required))
    frame=frame[(frame[value_column.lower()]>0)&frame["month"].between(1,12)].copy()
    frame["Date"]=pd.to_datetime(dict(year=frame["year"].astype(int),month=frame["month"].astype(int),day=1),errors="coerce")
    return frame.dropna(subset=["Date"])[["Date",value_column.lower()]].rename(columns={value_column.lower():output_column}).sort_values("Date").reset_index(drop=True)

def parse_noaa_co2_csv(text: str) -> pd.DataFrame:
    return _parse_noaa_monthly_csv(text,"average","CO2_ppm")

def parse_noaa_global_gas_csv(text: str,gas: str) -> pd.DataFrame:
    cols={"ch4":"CH4_ppb","n2o":"N2O_ppb"}; gas=gas.lower()
    if gas not in cols: raise ValueError("gas must be 'ch4' or 'n2o'.")
    return _parse_noaa_monthly_csv(text,"average",cols[gas])

def fetch_climate_watch(timeout: int=35) -> dict:
    urls={"temperature":NASA_GISTEMP_URL,"co2":NOAA_CO2_URL,"ch4":NOAA_CH4_URL,"n2o":NOAA_N2O_URL}
    headers={"User-Agent":"AGROVISION-ClimateWatch/1.1 (research dashboard)"}
    def get(url):
        response=requests.get(url,timeout=timeout,headers=headers); response.raise_for_status(); return response.text
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={k:pool.submit(get,v) for k,v in urls.items()}
        raw={k:v.result() for k,v in futures.items()}
    return {"temperature":parse_gistemp_csv(raw["temperature"]),"co2":parse_noaa_co2_csv(raw["co2"]),
      "ch4":parse_noaa_global_gas_csv(raw["ch4"],"ch4"),"n2o":parse_noaa_global_gas_csv(raw["n2o"],"n2o"),
      "retrieved_at":pd.Timestamp.now(tz="UTC"),"sources":SOURCES}


def summarize_local_extremes(
    climate: pd.DataFrame,
    hot_day_c: float = 35.0,
    heavy_rain_mm: float = 50.0,
    dry_day_mm: float = 1.0,
) -> pd.DataFrame:
    """Summarize transparent daily extremes from a NASA POWER point series.

    Counts are screening indicators, not official heatwave/drought classifications.
    Missing precipitation days break dry spells; missing temperature days are excluded.
    """
    required = {"PRECTOTCORR", "T2M_MAX"}
    missing = required.difference(climate.columns)
    if missing:
        raise ValueError(f"Climate series missing required columns: {sorted(missing)}")
    if not isinstance(climate.index, pd.DatetimeIndex):
        raise ValueError("Climate series must use a DatetimeIndex.")
    if climate.empty:
        return pd.DataFrame(columns=[
            "Year", "Hot days (Tmax threshold)", "Heavy-rain days",
            "Longest dry spell (days)", "Valid temperature days",
            "Valid precipitation days"
        ])
    rows = []
    work = climate[["PRECTOTCORR", "T2M_MAX"]].copy().sort_index()
    for year, group in work.groupby(work.index.year):
        rain = pd.to_numeric(group["PRECTOTCORR"], errors="coerce")
        tmax = pd.to_numeric(group["T2M_MAX"], errors="coerce")
        dry = rain.lt(dry_day_mm).where(rain.notna(), False)
        # A missing day breaks a spell; group consecutive calendar dates only.
        longest = current = 0
        previous_date = None
        for date, is_dry in dry.items():
            if previous_date is not None and (date - previous_date).days != 1:
                current = 0
            if bool(is_dry):
                current += 1
                longest = max(longest, current)
            else:
                current = 0
            previous_date = date
        rows.append({
            "Year": int(year),
            "Hot days (Tmax threshold)": int(tmax.ge(hot_day_c).sum()),
            "Heavy-rain days": int(rain.ge(heavy_rain_mm).sum()),
            "Longest dry spell (days)": int(longest),
            "Valid temperature days": int(tmax.notna().sum()),
            "Valid precipitation days": int(rain.notna().sum()),
        })
    return pd.DataFrame(rows).sort_values("Year").reset_index(drop=True)
