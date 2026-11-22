# 0008 — Streamlit UI without a sidebar, light theme by default

**Status:** Accepted

## Context

The app has five pages with top navigation. The Climate Explorer originally put its filters in
the sidebar, the only page with one: switching pages opened and closed the sidebar and the
whole layout jumped. Streamlit also starts on the visitor's *system* theme when both a light
and a dark theme are configured, and offers no setting to change that.

## Decision

- **No sidebar anywhere:** the Explorer's filters are a bar above the charts.
- **Two themes** in `.streamlit/config.toml`. Light is made the default by a small script that,
  on a visitor's first visit to each page, stores "Light" in Streamlit's own theme setting
  unless the visitor already chose another theme; it then remembers the visitor's choice
  across pages.
- **Theme-neutral chart colours:** text inherits the theme, grid lines are translucent greys,
  and colour scales end on saturated colours (a scale ending in dark brown vanished on the dark
  background).
- English by default, Turkish as an option.

## Consequences

- Page switches no longer shift the layout.
- The default-theme script depends on Streamlit's local-storage key format; if a future
  Streamlit version changes it, the app falls back to Streamlit's own behaviour (system theme).

## Alternatives considered

- **A sidebar on every page:** consistent, but wastes width on pages that do not need it.
- **Only a light theme:** simplest, but removes a feature visitors expect.
