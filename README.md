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

## Access and authentication

The app supports two access modes:

- **Visitor:** opens the prototype without creating an account.
- **Email account:** uses Supabase Auth for email/password registration and sign-in. Email confirmation depends on the Supabase project's authentication settings.

To enable email authentication on Streamlit Community Cloud:

1. Create a Supabase project and open **Project Settings → API**.
2. Copy the **Project URL** and the **Publishable key** (starts with `sb_publishable_`). Never use or expose the Secret key (`sb_secret_`) or the legacy service-role key.
3. In the Streamlit app, open **Settings → Secrets** and add:

```toml
SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_YOUR_KEY"
```

   For older projects that still use an anon key, the app also accepts `SUPABASE_ANON_KEY` as a backwards-compatible setting. Keep either key only in Streamlit Secrets, never in GitHub.

4. In Supabase **Authentication → URL Configuration**, add the deployed Streamlit app URL to the allowed redirect/site URLs as appropriate for the project.
5. In **Authentication → Providers / Email**, configure email sign-up and confirmation to match the intended access policy.

Until these secrets are configured, visitor access remains available and the email forms stay disabled. Passwords are sent directly to Supabase Auth over HTTPS; the app does not store passwords or put private keys in the repository. The current prototype keeps the signed-in session in Streamlit session state and does not yet save user profiles or farm projects to a database.
