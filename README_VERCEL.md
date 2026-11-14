# GUMA Web Edition

This directory-level migration is being introduced alongside the existing Streamlit research prototype.

## Current status

- The Vite/React web interface is an early frontend shell.
- The existing Streamlit application remains the reference implementation for analytical workflows.
- Do not describe the web edition as feature-equivalent until data connectors, authentication, saved projects, exports and analytical methods have been ported and tested.
- Dark surfaces must use light foreground text; light paper surfaces retain dark text.

## Local development

```bash
npm install
npm run dev
```

## Production build

```bash
npm run build
```

The Vercel project should use the repository root, Vite framework preset, build command `npm run build`, and output directory `dist`.
