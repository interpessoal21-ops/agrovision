# AGROVISION

Agricultural decision-support prototype using NASA Earth-observation and climate data.

## Run locally

Create a Python virtual environment, install dependencies with `pip install -r requirements.txt`, then start the app with `streamlit run app.py`.

## Data sources

- NASA POWER Daily API: daily air temperature, precipitation and solar radiation.
- MODIS MOD13Q1 through the ORNL DAAC subset API: 16-day NDVI observations.

SMAP is not yet connected in this public deployment because the earlier SMAP workflow required authenticated NASA Earthdata access. The single SMAP sample from the notebook should not be interpreted as a field measurement.

## Important limitations

The crop-rotation comparison is an explicitly provisional, rule-based demonstration. Its scores are not calibrated crop models, yield predictions, profitability estimates, or agronomic recommendations. Local soil and management inputs are user-supplied. Satellite observations represent regional pixels and should be validated with local field data.

## Deploy

Deploy this repository on Streamlit Community Cloud using `app.py` as the main file.
