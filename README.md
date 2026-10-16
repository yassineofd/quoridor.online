# Quoridor.online

Static website built from `docs/architecture-spec.md`. Only Python 3.10+ is needed (no Node, no packages).

## Run it

```powershell
python build.py     # generates the site into ./public
python serve.py     # open http://localhost:8000
```

Run `python check.py` to verify status codes, SEO metadata, links, headings, sitemap and robots rules (17 pages).

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
- Review the "Quoridor" name and domain for trademark issues.
- Host so unknown URLs return 404 and `/room/<id>/` serves `room/index.html` with a 200 (see `serve.py`; `public/_headers` has the headers).
