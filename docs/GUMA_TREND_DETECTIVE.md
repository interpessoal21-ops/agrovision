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


## Web edition: advanced analysis inputs

The web Trend Detective now exposes the same analysis concepts as the Python module.

- **Single annual series:** CSV columns `year,value` (Portuguese aliases `ano,valor` are accepted). At least eight consecutive annual observations are required.
- **Regional comparison:** long-format CSV columns `region,year,value` (aliases `regiao,ano,valor`). Each region is analyzed separately with the Hamed–Rao modified Mann–Kendall test and Sen slope. The p-values are adjusted across the uploaded regions with Benjamini–Hochberg FDR.
- **Environmental cross-variable analysis:** long-format CSV columns `region,year,variable,value` (Portuguese aliases accepted). Pearson and Spearman coefficients use only paired observations in the same region and year; at least eight pairs are required.

The web Hamed–Rao implementation detrends using Sen's slope, ranks the detrended series (average ranks for ties), estimates the rank-series autocorrelation, selects lags outside the nominal 95% bounds, and applies the absolute-sum variance correction. It is aligned with the public `pyMannKendall` reference implementation and is checked in CI by a parity test.

The web confidence interval is a deterministic circular moving-block bootstrap of detrended residuals (default 600 replicates; block length approximately n^(1/3); fixed seed). This is a percentile interval for Sen's slope. It is not a universal coverage guarantee: sensitivity to block length, short records, nonstationarity and structural breaks must be assessed.

Regional comparison is tabular. If at least four regions include latitude/longitude, the web edition also calculates exploratory global Moran's I on the regional Sen slopes, using a symmetrized binary k-nearest-neighbor graph (k up to 4) and haversine distances. This descriptive statistic has no permutation p-value and does not replace expert-specified spatial weights, boundary-based areal analysis, local cluster diagnostics, or spatial interpolation. Benjamini–Hochberg adjusts regional trend p-values but does not correct spatial autocorrelation. Cross-variable output is descriptive correlation only; it does not establish causal effects, adjust confounders, or perform lagged causal analysis. All input datasets must be accompanied by source, units, spatial support, temporal resolution and quality notes before scientific interpretation.
