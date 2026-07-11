# scripts/

## generate_page.py

Renders `docs/index.html` (served by GitHub Pages) from the root `README.md`, which is the single source of truth for the CV's content.

```
python3 scripts/generate_page.py
```

Run it after every edit to `README.md`, `docs/style.css`, or the profile photo, and commit the regenerated `docs/index.html` along with your change.

It expects `README.md`'s existing structure: an `#` title, an optional `<img>`/`![]()` photo reference and contact line right below it, `##` sections, `###` subsections for entries with their own heading/meta/bullets (e.g. jobs), and plain `- ` bullets for flat list sections (e.g. certifications). `Skills`, `Education`, and `Publications` render in the sidebar column; everything else renders in the main column — see `SIDEBAR_TITLES` in the script to change that.
