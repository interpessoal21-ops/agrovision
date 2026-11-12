"""Official MAPA ZARC open-data access and transparent decendio parsing."""
from __future__ import annotations

import io
import re
import unicodedata

import pandas as pd
import requests

DATASET_ID = "tabua-de-risco-zoneamento-agricola-de-risco-climatico"
DATASET_PAGE = "https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico"
CKAN_API = "https://dados.agricultura.gov.br/api/3/action/package_show"
FALLBACK_2026_2027 = (
    "https://dados.agricultura.gov.br/dataset/6d3d141c-885e-41a4-ab7f-dc8ff323b96f/"
    "resource/139e5a60-1f43-4cc8-aeab-a35dbbf816c0/download/"
    "dados-abertos-tabua-de-risco-safra-2026-2027.csv"
)


def normalize_text(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().casefold()


def normalize_column(value):
    return re.sub(r"[^a-z0-9]", "", normalize_text(value))


def list_zarc_resources(timeout=25):
    """Return official season CSV resources from the MAPA CKAN catalogue."""
    response = requests.get(
        CKAN_API, params={"id": DATASET_ID}, timeout=timeout,
        headers={"User-Agent": "AGROVISION/1.0 (MAPA ZARC open-data client)"}
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success") or not payload.get("result"):
        raise ValueError("MAPA CKAN did not return a valid ZARC dataset record.")
    resources = []
    for resource in payload["result"].get("resources", []):
        fmt = str(resource.get("format", "")).strip().lower()
        title = str(resource.get("name") or resource.get("description") or resource.get("id") or "ZARC CSV")
        url = resource.get("url")
        if url and (fmt == "csv" or ".csv" in str(url).lower()):
            resources.append({
                "id": str(resource.get("id", "")),
                "title": title,
                "url": str(url),
                "last_modified": resource.get("last_modified") or resource.get("created") or "",
                "format": fmt or "csv",
            })
    if not resources:
        raise ValueError("No CSV resources were listed by the MAPA ZARC catalogue.")
    resources.sort(key=lambda item: (item["title"], item["last_modified"]), reverse=True)
    return resources


def load_zarc_csv(url, timeout=60):
    """Download and parse an official MAPA CSV without silently changing its values."""
    response = requests.get(
        url, timeout=timeout,
        headers={"User-Agent": "AGROVISION/1.0 (MAPA ZARC open-data client)"}
    )
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "").lower()
    if "text/html" in content_type and len(response.content) < 2_000_000:
        raise ValueError("MAPA returned an HTML page instead of the CSV file.")
    errors = []
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            frame = pd.read_csv(
                io.BytesIO(response.content), sep=None, engine="python",
                encoding=encoding, dtype=str, keep_default_na=False,
                on_bad_lines="error"
            )
            frame.columns = [str(column).strip().lstrip("\ufeff") for column in frame.columns]
            if frame.empty or len(frame.columns) < 5:
                raise ValueError("Downloaded ZARC table is empty or has too few columns.")
            return frame
        except Exception as exc:
            errors.append(str(exc))
    raise ValueError("Could not parse MAPA ZARC CSV: " + " | ".join(errors))


def column_map(frame):
    return {normalize_column(column): column for column in frame.columns}


def find_column(frame, *aliases):
    columns = column_map(frame)
    for alias in aliases:
        found = columns.get(normalize_column(alias))
        if found is not None:
            return found
    return None


def unique_values(frame, column, base=None):
    if column not in frame.columns:
        return []
    source = frame if base is None else base
    if column not in source.columns:
        return []
    values = [str(value).strip() for value in source[column].tolist() if str(value).strip()]
    return sorted(set(values), key=lambda value: normalize_text(value))


def filter_zarc_rows(frame, filters):
    """Apply exact text/code filters; missing filter fields are deliberately ignored."""
    result = frame.copy()
    aliases = {
        "crop": ("Nome_cultura", "cultura", "crop"),
        "uf": ("UF", "sigla_uf"),
        "municipality": ("municipio", "Município", "municipality"),
        "soil": ("Cod_Solo", "cod_solo", "solo"),
        "cycle": ("Cod_Ciclo", "Cod_Ciclo_Cultivar", "grupo", "ciclo"),
        "management": ("Nome_Outros_Manejos", "outros_manejos"),
        "climate": ("Nome_Clima", "clima"),
    }
    for key, value in filters.items():
        if value is None or str(value).strip() == "":
            continue
        col = find_column(result, *aliases.get(key, (key,)))
        if col is None:
            continue
        target = normalize_text(value)
        result = result[result[col].map(normalize_text) == target]
    return result.reset_index(drop=True)


def decendio_columns(frame):
    found = {}
    for column in frame.columns:
        name = normalize_column(column)
        match = re.fullmatch(r"(?:dec|decendio)(\d{1,2})", name)
        if match:
            number = int(match.group(1))
            if 1 <= number <= 36:
                found[number] = column
    return found


def decode_risk(value):
    """Keep source values explicit: 0 means outside the recommended window."""
    raw = str(value).strip()
    if not raw or normalize_text(raw) in {"nan", "none", "null", "-"}:
        return None
    try:
        number = int(float(raw.replace(",", ".")))
    except (TypeError, ValueError):
        return {"raw": raw, "label": "Valor original não interpretado", "risk": None}
    if number == 0:
        return {"raw": raw, "label": "Fora da janela recomendada (0)", "risk": 0}
    if number in (20, 30, 40):
        return {"raw": raw, "label": f"Risco de {number}%", "risk": number}
    return {"raw": raw, "label": f"Valor oficial: {raw}", "risk": number}


def expand_decendios(row, columns):
    """Expand wide dec1..dec36 columns into month/dekad/risk records."""
    months = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    periods = []
    for number in range(1, 37):
        column = columns.get(number)
        if column is None:
            continue
        decoded = decode_risk(row.get(column, ""))
        if decoded is None:
            continue
        month = (number - 1) // 3
        dekad = (number - 1) % 3
        ranges = ("1–10", "11–20", "21–fim")
        periods.append({
            "Decêndio": number,
            "Mês": months[month],
            "Período": ranges[dekad],
            "Risco": decoded["label"],
            "Risco (%)": decoded["risk"],
            "Valor original MAPA": decoded["raw"],
        })
    return periods


def crop_matches_app_crop(official_crop, app_crop):
    official = normalize_text(official_crop)
    app = normalize_text(app_crop)
    aliases = {
        "maize (grain)": ("milho",),
        "soybean": ("soja",),
        "common bean (dry)": ("feijao", "feijao comum"),
    }
    return any(alias in official for alias in aliases.get(app, (app,)))
