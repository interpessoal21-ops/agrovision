# GUMA Trend Detective — NASA Space Apps Challenge 02

## Primary challenge
**Be An Earth System Trend Detective!** GUMA's primary challenge direction is to investigate long-term environmental trends using transparent statistical methods and Earth-observation evidence.

## Current implemented slice
- NASA GISS GISTEMP v4 global monthly land-ocean temperature anomalies, aggregated to annual means.
- User-uploaded annual CSV for an explicitly selected year and indicator column.
- Mann–Kendall monotonic trend test with tie-corrected variance and two-sided normal-approximation p-value.
- Sen's slope, the median of all pairwise slopes.
- User-selected analysis window and visible sample size.

## Statistical methods — expanded implementation\n- Mann–Kendall variance can be adjusted with the Hamed–Rao rank-autocorrelation correction; the interface must expose whether the correction was applied and which lags were selected. This is an approximation, not a universal fix for all dependence structures.\n- Sen's slope uncertainty is estimated with a reproducible circular moving-block bootstrap of detrended residuals. Report confidence level, replicate count, block length and random seed. The interval is conditional on this resampling design.\n- Autocorrelation-aware mode requires consecutive annual observations; gaps are rejected rather than silently treated as equally spaced.\n\n## Statistical boundaries
The Mann–Kendall test assumes independent observations. Serial autocorrelation can affect significance. The current implementation does not yet perform autocorrelation correction, seasonal Mann–Kendall, field significance, spatial multiple-testing correction, bootstrap confidence intervals or climate attribution. A significant monotonic trend is not proof of causation. The NASA global series is not a local or regional product.

## Data provenance
NASA GISS GISTEMP v4 global land-ocean temperature index. Monthly anomalies are referenced to 1951–1980. NASA may revise recent monthly observations; GUMA caches retrieved data for 24 hours. The interface displays retrieval time and source documentation.

## Visual identity
The page uses an original cartographic illustration of flowing contours, layered land/water-like forms and a navigation point. It is inspired by the broad organic, human and territorial language associated with Carybé, but does not reproduce or trace any protected artwork. No endorsement or affiliation is implied.

## Next validation gates
1. Add a serial-correlation-aware Mann–Kendall option and seasonal test where justified.
2. Add confidence intervals for Sen's slope with documented method and reproducible seed.
3. Add regional/spatial gridded data only with explicit grid, resolution, coverage, units and missing-data metadata.
4. Validate calculations against published reference datasets and independent implementations.
5. Add expert review and a reproducible validation notebook before presenting outputs as operational science.
