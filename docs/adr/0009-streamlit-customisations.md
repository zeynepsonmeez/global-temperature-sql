# 0009 — Streamlit customisations outside its public API

**Status:** Accepted

## Context

Four parts of the interface need behaviour that Streamlit 1.67 has no setting for:

| Wanted | Why Streamlit cannot do it |
|---|---|
| An orange top bar with white navigation | `config.toml` themes colour the page, not the header |
| The EN/TR switch inside the top bar | Widgets can only be placed in the page body |
| Light theme on a first visit, dark as an option | With two themes configured, Streamlit starts on the system theme (see [0008](0008-streamlit-without-sidebar.md)) |
| A globe that spins until the visitor touches it | `st.plotly_chart` cannot animate |

## Decision

Implement them outside the public API, but keep every such dependency in one known place,
pin the Streamlit version and write down how to check them after an upgrade.

- **CSS on Streamlit's internal names** — all in `page_style()` in `app/components.py`:
  `data-testid` attributes (`stHeader`, `stTopNavLink`, `stMainMenuButton`,
  `stMainBlockContainer`, `stMetricValue`), the widget-key class `.st-key-lang_toggle`
  (with `aria-checked` on its buttons) and the class `.stTextArea`.
- **Default light theme** — `default_light_theme()` in `app/components.py` writes Streamlit's
  local-storage key `stActiveTheme-<page path>-v2` and reads the background colour of
  `[data-testid="stApp"]`.
- **Spinning globe** — `render_globe()` in `app/views/home.py` renders the figure as HTML in
  `st.iframe` and rotates it with `Plotly.relayout`. plotly.js is served from `app/static/`
  (`enableStaticServing`), written there from the installed plotly package, so the globe also
  works without internet.
- `streamlit` is pinned to an exact version in `requirements-app.txt`.

## Consequences

- The interface looks and behaves as designed, and nothing changes until the pin is changed on
  purpose.
- An upgrade can break these customisations **silently**: the app still runs and the tests
  still pass, because headless tests do not render CSS. Each one fails safe — the default
  Streamlit look, the system theme, or a still globe — so nothing becomes unusable.

### Checklist after changing the Streamlit version

Open the app in a browser, in both themes, and check:

1. The top bar is orange, its links are white and the current page is highlighted.
2. The EN/TR switch sits in the top bar, left of the menu, and the selected language is white.
3. In a private window the first page opens in the light theme; after choosing Dark in the
   menu, other pages open dark too.
4. The home globe turns, stops on a click or drag, and ▶ starts it again.
5. `pytest tests/test_app.py` passes (it also checks that plotly.js is served locally).

If a check fails, look up the renamed `data-testid` or class in the browser's developer tools
and update `page_style()`, or the local-storage key in `default_light_theme()`.

## Alternatives considered

- **Only Streamlit's own options:** a neutral header, the language switch as a row on every
  page and the system theme first. Robust, but the design loses its identity.
- **A custom Streamlit component (React):** a supported API for the header and switch, but a
  JavaScript build chain for a cosmetic need.
- **plotly.js from a CDN:** no extra file, but the globe is blank without internet — a risk
  for a classroom presentation.
- **plotly.js inlined in the page (`include_plotlyjs=True`):** works offline, but sends about
  4.5 MB again on every rerun.
