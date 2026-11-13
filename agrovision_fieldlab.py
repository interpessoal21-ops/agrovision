"""AGROVISION Field Lab: transparent, user-submitted experiment records."""
import math

ALLOWED_CROPS = (
    "Soja", "Milho", "Feijão", "Café", "Cana-de-açúcar",
    "Algodão", "Arroz", "Trigo", "Mandioca", "Sistema diversificado", "Outro"
)
ALLOWED_REGIONS = ("Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul")
ALLOWED_METRICS = (
    "Produtividade", "Consumo de água", "Dias de estresse térmico",
    "Precipitação", "NDVI", "Custo de produção", "Outro"
)


def validate_trial_record(record: dict) -> dict:
    """Validate a public research note; values remain contributor-reported."""
    required = (
        "title", "display_alias", "macroregion", "crop", "season",
        "hypothesis", "strategy", "comparator", "metric", "unit",
    )
    cleaned = {}
    for key in required:
        value = str(record.get(key, "")).strip()
        if not value:
            raise ValueError(f"Missing required field: {key}")
        cleaned[key] = value
    limits = {"title": 90, "display_alias": 32, "season": 20,
              "hypothesis": 700, "strategy": 500, "comparator": 500,
              "unit": 24}
    for key, limit in limits.items():
        if len(cleaned[key]) > limit:
            raise ValueError(f"{key} exceeds {limit} characters.")
    if cleaned["macroregion"] not in ALLOWED_REGIONS:
        raise ValueError("Unknown Brazilian macroregion.")
    if cleaned["crop"] not in ALLOWED_CROPS:
        raise ValueError("Unknown crop category.")
    if cleaned["metric"] not in ALLOWED_METRICS:
        raise ValueError("Unknown comparison metric.")
    for key in ("baseline_value", "alternative_value"):
        value = record.get(key)
        if value is not None and value != "":
            try:
                number = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"{key} must be numeric.") from None
            if not math.isfinite(number):
                raise ValueError(f"{key} must be finite.")
            cleaned[key] = number
        else:
            cleaned[key] = None
    cleaned["notes"] = str(record.get("notes", "")).strip()[:1000]
    cleaned["status"] = "community observation"
    cleaned["published"] = True
    return cleaned


def relative_difference(baseline, alternative):
    """Return percent change when baseline is nonzero; otherwise None."""
    if baseline is None or alternative is None:
        return None
    baseline, alternative = float(baseline), float(alternative)
    if not math.isfinite(baseline) or not math.isfinite(alternative) or baseline == 0:
        return None
    return round((alternative - baseline) / abs(baseline) * 100.0, 2)
