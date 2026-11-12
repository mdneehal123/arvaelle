# ARVAELLE — Gold-plated jewellery, Dubai

Static website for ARVAELLE: gold-plated jewellery, WhatsApp ordering, same-day Dubai delivery.

## Structure
- `src/template.html` — the whole site app (English + Arabic, products, categories, policies, journal, gift landing pages). Edit content here: `CONFIG`, `PRODUCTS`, `CATS`, `PAGES` near the top of the `<script>`.
- `src/img/` — product photos
- `src/llms.txt` — summary for AI assistants
- `build.py` — pre-renders every page to real HTML (one URL per product, category, page) with its own title, description, canonical and schema.org data, plus `sitemap.xml`, `robots.txt` (AI crawlers allowed) and `llms.txt`
- `public/` — built output that Vercel serves (committed)

## Rebuild after editing
```
pip install playwright
SITE_URL=https://your-domain python3 build.py
```
Then commit `public/` and push — Vercel deploys automatically.
