# Quoridor Online

Static website built from `docs/architecture-spec.md`. Only Python 3.10+ is needed (no Node, no packages).

## Run it

```powershell
python build.py     # generates the site into ./public
python serve.py     # open http://localhost:8000
```

Run `python check.py` to verify status codes, SEO metadata, links, headings, sitemap and robots rules (17 pages).

## Hosting on a free host (no domain needed)

The site isn't tied to any domain. Deployment settings live in `site.json`:

| Setting | When to set it |
|---|---|
| `site_url` | Once you know your public address, e.g. `"https://yourname.github.io"`. While empty, canonical tags, absolute Open Graph URLs and `sitemap.xml` are left out (they require a real address). |
| `base_path` | Only if the host serves the site from a sub-folder, e.g. `"/quoridor.online"` on a GitHub Pages project site (`https://yourname.github.io/quoridor.online/`). Leave `""` on Netlify, Cloudflare Pages, Vercel or a custom domain. |

Then run `python build.py` and upload/deploy the `public/` folder. Changing domains later is just editing `site.json` and rebuilding.

Notes: `public/` includes `_headers` and `_redirects` (Netlify / Cloudflare Pages), and `.nojekyll` (GitHub Pages). Static hosts cannot
serve a private-room URL like `/room/<id>/` without a server, which doesn't exist yet, so on GitHub Pages those links show the 404 page.

## What is built (and what is not)

Built: all pages in the spec, header/footer/mobile menu, design system, SEO files, strict security headers, real 404s.

Not built, on purpose (the spec says not to): the game engine, computer opponent, matchmaking and room server. The play pages
validate input and then say honestly that the feature isn't live. Feature flags in `lib.py` (`FEATURES`) control the "Coming soon"
badges and which features the homepage claims. Flip a flag only when the feature really works.

## Things to try

| URL | What to check |
|---|---|
| `/` | Hero, three mode cards, private-room strip, FAQ |
| `/play/online/` | Enter a 1-character name to see the validation error; enter a valid one to see the "not live yet" notice |
| `/play/join-room/` | Code validation (6 chars, no 0/O/1/I) |
| `/play/computer/` | Difficulty radio cards, keyboard arrows to change selection |
| `/room/anything/` | Opens the "room isn't available" state |
| `/room/x/?preview=waiting` | Also: `join`, `starting`, `reconnecting`, `invalid`, `full`, `expired`, `unavailable`, `left` (sample data) |
| `/does-not-exist/` | Branded 404 with a real 404 status |
| `/sitemap.xml`, `/robots.txt` | Only indexable pages listed; `/room/` disallowed |

## Layout

- `lib.py` config, feature flags, icons, board illustration generator
- `pages.py` all page content
- `build.py` layout, metadata, sitemap, robots, headers
- `serve.py` local server with production-like 404 and room routing
- `static/` CSS, JS, logo, favicon (copied as is)

## Before going live

- `og-image.svg` should be exported to a 1200x630 PNG (most social networks ignore SVG previews) and referenced in `build.py`.
- Add PNG icons (180, 192, 512) for iOS and the web manifest.
- Replace the Privacy Policy and Terms drafts with reviewed text; add a real contact channel on `/contact/`.
- Review the "Quoridor" name (and any domain you pick) for trademark issues.
- Set `site_url` in `site.json` once the final address is known, then rebuild.
- When rooms exist, the host must serve `/room/<id>/` from `room/index.html` with a 200 (see `serve.py`; `_redirects` does this on Netlify / Cloudflare Pages).
