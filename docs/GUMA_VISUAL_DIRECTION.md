# GUMA visual identity — Do campo ao mar

## Official reference

The approved identity is the user-supplied GUMA brand board. It is the source of truth for the website's visual language. The implementation uses original vector artwork derived from its motifs and does not claim to reproduce the supplied raster artwork exactly.

## Brand lockup

- **Name:** GUMA
- **Descriptor:** Território • Clima • Futuro
- **Tagline:** Do campo ao mar, com o Brasil no horizonte.
- **Project descriptor:** Earth Intelligence
- The identity connects inland agriculture, Brazilian territory, climate and the Atlantic coast.

## Palette sampled from the supplied reference

- Paper / parchment: `#E8D9C4`
- Cartographic ink: `#16272D`
- Atlantic blue: `#1D5367`
- Deep ocean: `#0D384D`
- Sun ochre: `#D79320`
- Coastal sky: `#6A8F9B`
- Terracotta: `#AC5C22`
- Muted graphite: `#586664`

## Visual language

- Warm paper texture and editorial typography.
- A round emblem with sun, human figure, staff, chapel and flowing land/water bands.
- Coastal landscape motifs: palms, boats, church silhouettes and layered sea/land forms.
- Maps and charts use the same palette, but data marks must remain high-contrast and accessible.
- Avoid generic SaaS dashboards, neon gradients, generic leaf icons and unrelated stock imagery.
- Use restrained borders and shadows; avoid excessive rounded cards.
- Keep chart axes, units, source attribution, uncertainty and scientific caveats visually clear.

## Cultural and artistic context

Carybé is a cultural reference for the relationship between people, territory and landscape. GUMA uses original visual forms and does not reproduce Carybé's paintings, signatures or protected compositions, nor imply endorsement.

## Application

The shared implementation lives in `guma_brand.py` and is used by the main Streamlit app and the Trend Detective page. New pages should call `apply_brand()` and `render_brand_hero()` rather than creating a separate visual system.
