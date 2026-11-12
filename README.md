# AGROVISION

**Agricultural decision-support prototype using NASA Earth-observation and climate data.** Built for the NASA Space Apps Challenge 2026.

## Current capabilities

- Bilingual interface: English and Portuguese.
- Interactive study-area map with latitude/longitude input.
- NASA POWER daily climate data for 2020–2025.
- MODIS/Terra MOD13Q1 16-day vegetation observations for a selectable year range (2020–2025), with pixel-reliability filtering.
- Annual climate summaries and rainfall/temperature anomalies relative to the 2020–2025 baseline.
- Transparent, illustrative crop-rotation screening comparison with visible score components.
- CSV export and PDF environmental report.
- Supabase email authentication and optional per-user project persistence.
- Saved projects include the queried climate and MODIS series and can be restored in the app.

## Run locally

Create a Python virtual environment, install dependencies with `pip install -r requirements.txt`, then start the app with `streamlit run app.py`.

## Data sources

- **NASA POWER Daily API:** daily near-surface air temperature, precipitation and solar radiation for the Agroclimatology community.
- **MODIS/Terra MOD13Q1 via ORNL DAAC:** 16-day vegetation-index composites and pixel-reliability data. The app first retrieves the available composite dates and splits the selected period into batches of no more than ten dates per point-subset request, respecting the ORNL service limit.

The MODIS endpoint is queried for the selected period. NDVI is computed from NIR and red reflectance using the ratio (NIR − red) / (NIR + red); the common reflectance scale factor cancels in this ratio. Only reliability flags 0 (good) and 1 (marginal) are retained for NDVI calculations.

SMAP is **not connected** in this deployment. Do not interpret any previous isolated SMAP sample as a field measurement.

## Scientific limitations

- NASA POWER and MODIS are gridded / satellite-derived products, not field sensors. A point query does not represent every part of a farm.
- NDVI is a vegetation-greenness indicator. It does not identify crop species, diagnose plant disease, or directly measure yield.
- Climate anomalies are calculated against the queried 2020–2025 period; this short baseline is not a formal climatological normal.
- Crop-rotation scores are transparent, provisional demonstration weights. They are **not calibrated crop models, yield predictions, profitability estimates, or agronomic recommendations**.
- Soil texture, fertility and irrigation context are user-entered assumptions.
- Validate any real-world decision with local soil tests, crop calendars, field observations and qualified agronomic advice.

## Supabase setup: save projects

Email authentication uses the Supabase Auth REST API. To enable saving and restoring projects:

1. Configure Streamlit Community Cloud → **Settings → Secrets** with the Supabase **Project URL** and **Publishable key**:

   ```toml
   SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
   SUPABASE_PUBLISHABLE_KEY = "sb_publishable_YOUR_KEY"
   ```

   Never put a Supabase Secret or service-role key in Streamlit secrets for this app or in GitHub.

2. Open the Supabase project's **SQL Editor**.
3. Copy and run the complete script in `supabase/schema.sql`.
4. In Supabase **Authentication → URL Configuration**, configure the deployed Streamlit URL as appropriate.
5. Confirm email sign-up / verification settings under **Authentication → Providers → Email**.

The SQL creates `public.farm_projects`, enables Row Level Security (RLS), and limits each signed-in user to their own rows. The app uses the signed-in user's access token for database requests. Visitor sessions cannot save projects.

Saved project payloads include the selected coordinates, user-entered farm context, climate time series and MODIS observations. These records are stored in the user's Supabase project; review your data-retention and privacy requirements before collecting real farm data.

## Deploy

Deploy this repository on Streamlit Community Cloud using `app.py` as the main file. Streamlit Community Cloud automatically rebuilds after commits to the connected GitHub branch.
