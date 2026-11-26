# Personal website: Prajwal Ram Gowda

Instructions for the coding agent working in this repository.

## 1. What this is

A one-page personal portfolio site. The design is finished and approved. A single
self-contained file, `reference/prajwal-portfolio.html`, is the **source of truth**
for how the site looks and behaves.

Your job is to:

1. Turn that file into a clean, maintainable static site (HTML, CSS, JS and font
   files) that looks and behaves **identically**.
2. Make it deployable on GitHub Pages.
3. Push it on a branch and open a pull request.

Do not redesign anything. If something in this spec seems to conflict with the
reference file, the reference file wins. Mention the conflict in the PR description.

## 2. Hard rules

- **No visual changes.** Keep every colour, font, size, spacing, radius, shadow and
  breakpoint exactly as in the reference.
- **No animation.** Don't add entrance effects, scroll effects, hover transitions,
  counters, parallax or animated charts. The only scrolling behaviour is smooth
  scrolling to anchors, and only when reduced motion isn't requested.
- **No frameworks or build step.** Plain HTML, CSS and vanilla JS. No React,
  Tailwind, bundler or npm dependencies at runtime.
- **No external requests.** Fonts are self-hosted, with no Google Fonts or CDNs.
  Add no analytics, trackers or third-party scripts.
- **Don't invent content.** Use the copy in section 6 word for word. Leave anything
  missing (dates, new roles, articles) as a TODO in the PR description instead of
  making it up.
- **Keep accessibility features**: skip link, landmarks, focus styles, reduced-motion,
  reduced-transparency and forced-colours handling, and `aria-pressed` on the theme
  button.

## 3. Target file structure

```
/
├── index.html                  # page markup + the tiny inline theme script in <head>
├── assets/
│   ├── css/site.css            # all CSS from the reference, minus the @font-face data
│   ├── js/site.js              # theme toggle + Liquid Glass refraction (deferred)
│   └── fonts/
│       ├── newsreader-normal.woff2
│       ├── newsreader-italic.woff2
│       ├── ibm-plex-sans.woff2
│       └── OFL.txt             # SIL Open Font License 1.1 (covers both families)
├── reference/
│   └── prajwal-portfolio.html  # the approved single-file design; keep unchanged
├── .nojekyll
├── README.md                   # short: what it is, how to preview, how to deploy
└── AGENTS.md                   # this file
```

### Extracting the fonts

The reference embeds three fonts as base64. Decode them to files rather than
downloading new copies, so the glyphs match exactly:

```python
import re, base64, pathlib
html = pathlib.Path("reference/prajwal-portfolio.html").read_text(encoding="utf-8")
data = re.findall(r"url\(data:font/woff2;base64,([A-Za-z0-9+/=]+)\)", html)
assert len(data) == 3, len(data)
names = ["newsreader-normal.woff2", "newsreader-italic.woff2", "ibm-plex-sans.woff2"]
out = pathlib.Path("assets/fonts"); out.mkdir(parents=True, exist_ok=True)
for name, b64 in zip(names, data):
    (out / name).write_bytes(base64.b64decode(b64))
```

The `@font-face` rules in `site.css` should then point to those files:

```css
@font-face { font-family: "Newsreader"; src: url("../fonts/newsreader-normal.woff2") format("woff2"); font-weight: 200 800; font-style: normal; font-display: swap; }
@font-face { font-family: "Newsreader"; src: url("../fonts/newsreader-italic.woff2") format("woff2"); font-weight: 200 800; font-style: italic; font-display: swap; }
@font-face { font-family: "Plex";       src: url("../fonts/ibm-plex-sans.woff2")     format("woff2"); font-weight: 100 700; font-style: normal; font-display: swap; }
```

Add `<link rel="preload" as="font" type="font/woff2" crossorigin>` for
`newsreader-normal.woff2` and `ibm-plex-sans.woff2` in `index.html`.

`OFL.txt` is supplied alongside this spec. It contains the SIL Open Font License 1.1
for both font families, with their copyright lines. Copy it to `assets/fonts/OFL.txt`
as is.

### Splitting the code

- **Theme script:** keep the small script in `<head>` inline and before the
  stylesheet link. It sets `data-theme` before first paint, which prevents a
  flash of the wrong theme.
- **`site.css`:** move everything else in `<style>` here, unchanged except for the
  font URLs.
- **`site.js`:** move the main `<script>` at the end of `<body>` here and load it
  with `<script src="assets/js/site.js" defer>`. Keep the code as written. It
  runs on `document.fonts.ready`, which is still correct with `defer`.

## 4. Design system

### Themes

There are two themes, set as `data-theme` on `<html>`. In the code they're named
`limestone` (light) and `black` (dark). The visitor never sees those names: they
switch with a single moon/sun icon button.

| Token | Limestone (light) | Black (dark) | Used for |
|---|---|---|---|
| `--bg` | `#e2ddd2` | `#000` | page background |
| `--paper` | `#ece8df` | `#0d0d0d` | solid fallback when transparency is reduced |
| `--ink` | `#1d1c19` | `#ece9e2` | main text |
| `--muted` | `#57534b` | `#9e998f` | secondary text |
| `--rule` | `#c4bdaf` | `#2b2a27` | hairline dividers |
| `--s1` | `#2b45b0` | `#7189f0` | cobalt accent, focus ring, primary button |
| `--link` | `#2b45b0` | `#9aabff` | links |
| `--glass` | `rgba(246,243,236,.26)` | `rgba(30,30,32,.20)` | glass tint |
| `--rim-hi` / `--rim-lo` | white .95 / .35 | white .42 / .10 | glass edge highlights |
| `--glass-shadow` | warm, soft | deep black | glass drop shadow |
| `--field-a` / `--field-b` | cobalt .30 / ochre .26 | cobalt .42 / ochre .30 | soft light behind the hero |
| `--paper-line` | ink at 7% | ink at 7% | graph-paper grid lines |

Theme rules:

- **First visit:** follow `prefers-color-scheme`.
- **After a click:** store the choice in `localStorage` under `prg-theme` and keep
  it on later visits.
- **Toggle button:** shows a moon in light mode and a sun in dark mode, and sets
  `aria-pressed="true"` in dark mode.

### Typography

| Role | Font | Notes |
|---|---|---|
| Headings, lead paragraph, role titles, big numbers, contact email | **Newsreader** (variable, with optical sizes) | weight 400 (300 for the big numbers); `font-variation-settings: "opsz" 72` on the h1 and big numbers |
| Body, nav, buttons, labels | **IBM Plex Sans** (variable), loaded as family name `Plex` | base 17px (1.0625rem), line height 1.6; tabular, lining numbers |

Never substitute Inter, Geist, DM Sans, Instrument Serif or system fonts, except as
fallbacks.

### Layout

- **Content width:** `.wrap`, maximum 1160px with fluid side gutters.
- **Desktop:** every major row uses a 5 : 7 two-column grid (hero, section headings,
  work rows).
- **900px and below:** the grids collapse to one column.
- **640px and below:** the nav moves to its own row inside the header capsule.
- **Background:** a fixed 32px graph-paper grid over the whole page, plus soft cobalt
  and ochre light behind the hero. The glass needs something behind it to look like
  glass, so don't remove these.

### Liquid Glass

Elements with the `.glass` class get four things:

1. **Translucent tint:** `--glass`.
2. **Specular rim:** the `::after` gradient border, brighter at top-left.
3. **Soft top sheen:** the `::before` highlight.
4. **Edge refraction:**
   - In Chromium browsers, `site.js` builds an SVG displacement map for each glass
     element's size and corner radius, and applies it with
     `backdrop-filter: url(#lgN) blur() saturate()`. Content behind the glass bends
     near the rounded edge, like the rim of a lens.
   - Safari and Firefox don't support SVG filters in `backdrop-filter`. They keep the
     CSS fallback, `blur(16px) saturate(175%)`. This is expected, not a bug.

Two data attributes control the effect:

- **`data-refract`:** `1` for large panels (scale 48), `.6` for small controls
  (scale 30).
- **`data-blur`:** overrides the blur amount. The header uses `7` so text stays
  readable when content scrolls under it.

Filters are cached by size and rebuilt on resize, debounced at 150ms. Under
`prefers-reduced-transparency: reduce`, glass falls back to the solid `--paper`
colour.

The glass elements are:

- the header capsule
- the theme button
- both hero buttons
- the résumé card
- the contact card

Keep project rows and body text off glass so they stay easy to read.

## 5. Page structure, top to bottom

1. **Skip link:** "Skip to content", pointing to `#main`.
2. **Header:**
   - a sticky glass capsule 14px from the top
   - the name on the left
   - nav links, in this order: Résumé (`#resume`), Work (`#work`), Writing
     (`#writing`), Contact (`#contact`)
   - the theme icon button on the right
3. **Hero, 5 : 7:**
   - **Left:** the h1, the lead paragraph, then two buttons: "Email me" (solid
     cobalt glass, `mailto:`) and "See my work" (clear glass, `#work`).
   - **Right:** the glass **résumé card** with `id="resume"`. It has the heading
     "Résumé", a "LinkedIn profile" link, the roles list and a footer line.
4. **Selected work:**
   - a section heading row
   - three rows, each with the big number and its label on the left
   - on the right: organisation, project title, summary, and a "How it was built"
     `<details>`
5. **Writing:** one note with a "Read it" `<details>`.
6. **Get in touch:** a section heading plus a glass contact card with the email
   address in large type and a LinkedIn link.
7. **Footer:** "Prajwal Ram Gowda, Dubai" and "Back to top".

## 6. Content (use word for word)

- **Page title:** Prajwal Ram Gowda — Data and decision science
- **Meta description:** Prajwal Ram Gowda builds analytics for group finance, cargo
  logistics and real-world healthcare evidence. Based in Dubai.
- **h1:** I turn scattered records into figures people can decide with.
- **Lead:** **Data and decision scientist, based in Dubai.** I've built group-wide
  reporting for eight businesses, a model that fills the gaps in cargo journeys, and
  real-world evidence studies for life-sciences teams.
- **Résumé roles**, most recent first:
  - Manager, Business Intelligence and Analytics, Ghassan Aboud Group
  - Data Scientist, DP World
  - Decision Scientist, Mu Sigma
- **Résumé footer:** Business intelligence and analytics, based in Dubai
- **Work rows:**

  | Big number | Label | Organisation | Title |
  |---|---|---|---|
  | 8 | businesses on one reporting model | Ghassan Aboud Group | One view across eight businesses |
  | Gaps | in container journeys, given estimated times | DP World | Filling the gaps in cargo journeys |
  | 12+ | real-world evidence studies | Mu Sigma | Finding evidence in healthcare data |

  Copy the summary and "How it was built" text for each row from the reference.
- **Email:** prajwalram8@gmail.com
- **LinkedIn:** https://www.linkedin.com/in/prajwal-ram-gowda/

## 7. Small additions that are allowed

- **Social preview tags:** add Open Graph and Twitter card tags (`og:title`,
  `og:description`, `og:type=website`, `twitter:card=summary`). Use the existing
  title and description. Leave `og:url` and `og:image` as TODO comments.
- **Canonical URL:** add `<link rel="canonical">` with a TODO for the final domain.
- **Favicon:** add a simple SVG favicon, the letter "P" set in Newsreader in `--ink`
  on `--bg`. Skip it if it can't be done cleanly.

Nothing else.

## 8. Acceptance checks (run before opening the PR)

1. **Visual match:**
   - Serve the repo locally (`python3 -m http.server`).
   - Use Playwright with Chromium to screenshot `index.html` and
     `reference/prajwal-portfolio.html` at 1440×900 and 390×844, in both themes.
   - The screenshots must match. A small pixel difference from font hinting is fine.
   - Attach the four `index.html` screenshots to the PR.
2. **No errors:** the console shows no errors and no failed network requests.
3. **No external requests:** every request goes to the site's own origin.
4. **Theme toggle:**
   - Clicking it switches the theme and updates `aria-pressed`.
   - The choice survives a reload.
   - The wrong theme never flashes on load.
5. **Refraction:**
   - In Chromium, glass elements have an inline `backdrop-filter` starting with
     `url(#lg`.
   - In Firefox or WebKit, they fall back to blur with no errors.
6. **Anchors:**
   - Every nav link scrolls to its target.
   - The target isn't hidden under the sticky header (scroll-margin is 96px).
7. **Accessibility:**
   - Lighthouse accessibility score of 95 or higher.
   - Keyboard tab order is logical and focus rings are visible.
   - Reduced motion and reduced transparency are respected.
8. **HTML:** passes the W3C validator with no errors.

## 9. Git and deployment

1. Create a branch, e.g. `site/liquid-glass-portfolio`. Don't commit directly to
   the default branch.
2. Make focused commits, in this order:
   - add the reference file
   - extract the fonts
   - split out the CSS and JS
   - add the meta tags, favicon and README
3. Push and open a PR titled **"Add liquid glass portfolio site"**. The description
   should cover what changed, the screenshots, the acceptance check results, and the
   TODO list below.
4. **Deployment:** GitHub Pages from the default branch, root folder (`.nojekyll`
   included). Don't change repository settings yourself; describe the steps in the
   README.

## 10. Open TODOs for the owner (list in the PR, don't implement)

- Add dates to each résumé role.
- Add the current role (Strategic Research & Competitive Intelligence, DP World
  Parks & Zones) if the owner wants it shown.
- Add a downloadable PDF résumé and a "Download PDF" link in the résumé card header.
- Replace the single writing sample with two or three published pieces, or hide the
  section.
- Set the final domain for the canonical link and `og:url`, and add an `og:image`.
