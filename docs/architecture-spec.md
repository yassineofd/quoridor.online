# Quoridor.online — Website Architecture & Design Specification

Status: v1.0 (planning). Scope: architecture, page hierarchy, navigation, user journeys, visual system, SEO structure.
Out of scope: game engine, multiplayer server, matchmaking, final page copy.

**Honesty rule (applies everywhere):** a feature may only be described in public copy as available once it is implemented. Until then, routes exist as architecture, and pages show an honest "coming soon" state or are not linked from navigation.

---

## 1. Sitemap and page hierarchy

```
/                                  Homepage                         indexable, in sitemap
├── /play/                         Choose a playing mode            indexable, in sitemap
│   ├── /play/online/              Online matchmaking               indexable*, in sitemap
│   ├── /play/computer/            Robot + difficulty               indexable*, in sitemap
│   ├── /play/local/               Same-device game                 indexable*, in sitemap
│   ├── /play/create-room/         Create private room              noindex, follow, NOT in sitemap
│   └── /play/join-room/           Join by code/link                noindex, follow, NOT in sitemap
├── /room/{roomId}/                Private room + game              noindex, nofollow, NOT in sitemap
├── /how-to-play-quoridor/         Beginner tutorial                indexable, in sitemap
├── /quoridor-rules/               Formal rules                     indexable, in sitemap
├── /quoridor-strategy/            Strategy guide                   indexable, in sitemap
├── /quoridor-board-game/          Board-game overview              indexable, in sitemap
├── /about/                        About the site                   indexable, in sitemap
├── /contact/                      Contact structure                indexable, in sitemap
├── /privacy-policy/               Privacy policy                   indexable, in sitemap
├── /terms/                        Terms of use                     indexable, in sitemap
└── (any other URL)                Branded 404, HTTP 404            noindex, NOT in sitemap
```

\* The three mode pages are thin app shells. Index them **only if** each has at least ~150 words of unique intro copy (what the mode is, how it works) above or beside the app UI. Otherwise set `noindex, follow` and omit from the sitemap so they don't dilute `/play/`. Default recommendation: index `/play/` only at launch; add the others after they carry real copy.

### Page purposes

| URL | Purpose | Primary audience intent |
|---|---|---|
| `/` | Fastest path into a game + introduction to the game; targets the "play online" intent | Navigational / transactional |
| `/play/` | Practical mode chooser (online / robot / local), plus private-room entry | Transactional |
| `/play/online/` | Username → matchmaking queue → game. Contains the private-room sub-entry points | Transactional |
| `/play/computer/` | Difficulty selection → game vs. computer | Transactional |
| `/play/local/` | Direct entry into hot-seat game | Transactional |
| `/play/create-room/` | Username → create room → show link + code → wait | Transactional |
| `/play/join-room/` | Enter code (+ username) → validate → join | Transactional |
| `/room/{roomId}/` | Lobby, waiting state, and the synchronized game for a private room | Application state |
| `/how-to-play-quoridor/` | Teach a beginner to play, in a friendly, narrative order | Informational |
| `/quoridor-rules/` | Authoritative, scannable rules reference | Informational |
| `/quoridor-strategy/` | Improve play: tactics and mistakes | Informational |
| `/quoridor-board-game/` | What the game is: components, design idea, how modes differ | Informational / navigational |
| `/about/` | Purpose of the site; no invented history | Trust |
| `/contact/` | Structured feedback / support / business routes | Trust |
| `/privacy-policy/`, `/terms/` | Legal; content must match actual behavior | Trust / compliance |
| 404 | Recovery with links to Home and Play | — |

### Route relationships and decisions

- Private rooms are **part of online play**, not a fourth mode. `/play/create-room/` and `/play/join-room/` sit under `/play/` for URL consistency, but are reached from the Play Online card, the homepage "Play privately" section, and `/play/online/`.
- `/room/{roomId}/` lives outside `/play/` so invitation links are short and stable. `roomId` must be an unguessable random token (≥128 bits, e.g. 22+ char base64url), distinct from the short human-typed **pairing code** (e.g. 6 chars from an unambiguous alphabet, short TTL, rate-limited).
- No `/quoridor-online/` page: homepage owns that intent (see §8).
- Overlap guard for informational pages — each owns one job:
  - **How to Play** = learn by doing (narrative, beginner tone).
  - **Rules** = reference (numbered, terse, edge cases like jumps and wall legality).
  - **Strategy** = decisions (heuristics, mistakes). Assumes rules known.
  - **Board Game** = context (what it is, components, why it's interesting, local vs. computer vs. online). Must not restate rules; link to them.

---

## 2. Global navigation

### Header (compact, ~56–64 px)

| Order | Item | Target | Notes |
|---|---|---|---|
| 1 | Logo + wordmark | `/` | Wordmark may collapse to logo mark below ~360 px |
| 2 | Home | `/` | |
| 3 | Play | `/play/` | |
| 4 | How to Play | `/how-to-play-quoridor/` | |
| 5 | Rules | `/quoridor-rules/` | |
| 6 | Strategy | `/quoridor-strategy/` | |
| 7 | About Us | `/about/` | |
| 8 | **Play Now** (button) | `/play/` | Primary CTA, always visible, including mobile |

Not in the main nav: Board Game overview, Contact, legal pages, individual play modes (all reachable via footer, Play page, or in-content links).

**Mobile (< 768 px):** logo left; **Play Now** button and a menu button ("Menu", with icon) on the right. Menu opens a full-width panel with the remaining items.

Menu accessibility:
- `<button aria-expanded aria-controls>` toggle with a visible text label or `aria-label="Menu"`.
- Focus moves into the panel on open, is trapped while open, `Esc` closes and returns focus to the toggle.
- Links are ≥ 48 px tall; background content is inert while open.
- Works without JS for crawlers: nav links exist in the HTML; the menu is progressively enhanced (a `<details>`-based fallback is acceptable).
- Current page marked with `aria-current="page"` plus a non-color indicator (underline/bar).
- A "Skip to main content" link is the first focusable element.

### Footer

Three columns on desktop, stacked on mobile:

| Learn | Site | Legal |
|---|---|---|
| How to Play | About Us | Privacy Policy |
| Quoridor Rules | Contact Us | Terms of Use |
| Quoridor Strategy | | |
| Quoridor Board Game *(optional, recommended for crawl depth)* | | |

Footer also carries: logo, one-line tagline, and a non-affiliation notice: "Quoridor.online is an independent site and is not affiliated with or endorsed by the publisher of the Quoridor board game." (Legal review recommended re: the Quoridor trademark and the domain name before launch.)

---

## 3. Homepage (`/`) — section order

Single `<h1>`; each section a `<section>` with an `<h2>`.

| # | Section | Content | Notes |
|---|---|---|---|
| A | Header | Logo, nav, Play Now | |
| B | Hero | H1 (includes "Quoridor" and "online"), 1–2 sentence objective + strategic challenge, **Play Now** (primary), **How to Play** (secondary text/outline button), minimalist SVG board preview | Preview is inline SVG with `<title>/<desc>` or an `<img alt>` describing it; board visual must not push the CTA below the fold on a 320×640 viewport |
| C | Choose how to play | Three cards: **Play Online**, **Play Against Robot**, **Play With a Friend** | The main functional entry; see §4 |
| D | Play privately with a friend | Compact strip: **Create a Room** / **Join a Room**; text explains invitation link or pairing code | Visually quieter than C (outline buttons, no illustration); not a 4th card |
| E | How the game works | Reach the opposite side; place barriers strategically; links to How to Play and Rules | 3-step mini illustration: move → block → reach the far side |
| F | Website features | Browser-based play, no mandatory registration, multiple modes, responsive design | **Gate each item on implementation status**; build the list from a feature flag/config, not hard-coded copy |
| G | Educational preview | Two cards → Rules, Strategy (optionally How to Play and Board Game) with "what you'll learn" blurbs | |
| H | FAQ | 5–7 short Q&As (objective, how many players, how to win, wall rules in one line, available modes, need an account?) | Use `<details>/<summary>` or accessible accordion; **FAQPage structured data only if the Q&As are visible and match** (note: Google restricts FAQ rich results for most sites, so treat as optional) |
| I | Footer | See §2 | |

Keyword placement: "Quoridor game" and "Quoridor online" naturally in `<title>`, H1/H2, hero paragraph, hero image alt, and internal link text — once or twice each, not repeated.

---

## 4. The three primary playing modes

All cards share: icon/illustration, H3, 1–2 sentence description, one button. Equal visual weight; distinguished by icon and accent usage (cyan/indigo), never by color alone.

### 4.1 Play Online
- **Description:** Play against another person over the internet. Pick a username; no account needed.
- **Action:** "Play Online" → `/play/online/`
- **Secondary link inside card or on destination page:** "Playing with a specific friend? Create or join a private room" → `/play/create-room/` / `/play/join-room/`

### 4.2 Play Against Robot
- **Description:** Practice against the computer at a level that suits you.
- **Action:** "Play vs Robot" → `/play/computer/`
- **Difficulty copy (beginner-friendly, no capability promises):**

| Level | Description |
|---|---|
| Easy | Good for learning the rules. Makes simple moves and is easy to out-plan. |
| Medium | A relaxed game for players who know the basics. |
| Hard | Plans ahead more and uses barriers deliberately. Expect a real challenge. |
| Expert | The strongest level we offer. Best for experienced players. |

  Rules for this copy: no "unbeatable", no named ratings/Elo, no claims about search depth until measured. Level names are labels; behavior is defined when the AI is built.
- Username: ask only if the final interface needs one (e.g., to label the scoreboard); otherwise default to "You".

### 4.3 Play With a Friend (local)
- **Description:** Two players, one device. Take turns on the same screen.
- **Action:** "Play Together" → `/play/local/` (opens the game directly; no username form required, optional player-name fields)
- **Clarity note on card:** "Both players share one screen and take turns."

---

## 5. User journeys and states

### 5.1 Online matchmaking
`/play/online/`
1. Landing: choose **Play Online** → username field (validation: 2–20 chars, trimmed, profanity/impersonation filter on server later).
2. **Find opponent** → queue.
3. Waiting state → matched → synchronized game starts.

States to design:
| State | Requirements |
|---|---|
| Idle / form | Inline validation, Enter submits, label not placeholder-only |
| Searching | Spinner **plus** text ("Looking for an opponent…"), elapsed time, **Cancel** button; `aria-live="polite"` |
| Slow queue | After N seconds, offer: keep waiting, play robot, create private room |
| Matched | Brief confirmation with opponent username, then board |
| Connection lost / reconnecting | Persistent banner with status icon + text; game paused for the opponent; grace period before forfeit |
| Error | Plain-language message + Retry (server unreachable, queue timeout, username rejected) |
| Cancelled | Return to form with entered username preserved |

### 5.2 Against robot
`/play/computer/`: choose difficulty (radio-card group, one pre-selected: Medium) → (username if required) → **Start game**. Option to choose who moves first can be added later; spec says nothing, so default to human first.

### 5.3 Local multiplayer
`/play/local/`: **Play With a Friend** → board with both players. Requirements:
- A persistent turn indicator naming the active player ("Player 1's turn") with a color **and** shape/label difference between players' pawns (e.g., filled circle vs. ringed circle), not color alone.
- Visible turn-change cue (text + brief non-essential highlight; none under reduced motion).
- Optional "pass the device" hint after each move.
- Controls: undo (if supported), restart, leave.

### 5.4 Creating a private room
`/play/create-room/` → `/room/{roomId}/`
1. Select **Create a Room**.
2. Enter username.
3. **Create room** → server returns `roomId` and pairing code.
4. Room page shows invitation link and pairing code, each with its own **Copy** button (feedback via text "Copied", `aria-live`); optional native Share button where `navigator.share` exists.
5. Waiting state with host-only **Cancel room**.
6. When the guest joins → both see "Opponent joined"; start when both are ready (auto-start or both press Ready; decide at implementation).

### 5.5 Joining a private room
Entry A, via link: `/room/{roomId}/` → username prompt → validate → join.
Entry B, manual: `/play/join-room/` → username + pairing code → validate → redirect to `/room/{roomId}/`.

### 5.6 Room state matrix (`/room/{roomId}/`)

| State | UX |
|---|---|
| Host waiting | Link + code + copy, cancel, connection indicator |
| Guest needs name | Username form |
| Joining | Progress text |
| Ready / starting | Both names shown, start control or countdown |
| In game | Board + status |
| Opponent disconnected | Banner, countdown to forfeit/wait |
| Self reconnecting | Rejoin automatically using a client-held room token (not the username); show "Reconnecting…" |
| Leave room | Confirm dialog; explain consequence (forfeit if mid-game) |
| Game finished | Result, rematch, leave |
| Invalid code | "That code doesn't match a room. Check it and try again." |
| Room full | "This room already has two players." Offer Create a Room |
| Expired invitation | "This invitation has expired." Offer Create a Room |
| Unavailable / not found | "This room isn't available." Offer Create a Room, Play Online |
| Rate limited | "Too many attempts. Try again in a minute." |

Error responses for invalid/expired/not-found should be indistinguishable enough to avoid letting someone enumerate valid room IDs; "full" is only revealed to someone holding a valid token/code.

**Identity:** usernames are display names only, not identity or authentication. Two players may choose the same name; the UI disambiguates (e.g., "Alex" vs "Alex (opponent)"). Seat ownership is bound to a server-issued session token stored client-side, not to the name.

---

## 6. Design system

### 6.1 Color tokens

| Token | Hex | Role |
|---|---|---|
| `--color-bg` | `#0B1220` | Page background |
| `--color-surface` | `#111C30` | Cards, header, panels |
| `--color-text` | `#FFFFFF` | Primary text |
| `--color-text-muted` | `#91A4BF` | Secondary text, captions |
| `--color-accent` | `#42D9F5` | Primary accent, links, primary CTA, focus ring |
| `--color-accent-2` | `#5267F2` | Secondary accent, selected states, large UI |
| `--color-border` | `#26364F` | Card borders, dividers |

Verified WCAG 2.x contrast ratios (computed, not estimated):

| Pair | Ratio | Verdict |
|---|---|---|
| White on `#0B1220` / `#111C30` | 18.7 / 17.0 | Passes AAA |
| Cyan on `#0B1220` / `#111C30` | 11.1 / 10.1 | Passes AAA (text, links, focus ring) |
| Muted on `#0B1220` / `#111C30` | 7.4 / 6.7 | Passes AAA for body text |
| `#0B1220` text on cyan | 11.1 | Primary button label: use dark navy on cyan |
| White on indigo `#5267F2` | 4.58 | Passes AA for normal text — use white text on indigo fills |
| Indigo **as text/icon on** `#0B1220` / `#111C30` | 4.08 / 3.72 | **Fails 4.5:1 for body text.** Passes 3:1 for large text and UI components only. Never use indigo for small text on dark surfaces. |
| Border `#26364F` on bg / surface | 1.54 / 1.40 | **Below 3:1**; OK for decorative card edges and dividers, **not** for the boundary of a form field, button, or any control that needs to be identified |

Consequences for implementation:
- Form inputs, outline buttons, and unselected radio-cards need a ≥ 3:1 boundary: use `--color-text-muted` (`#91A4BF`, ~7:1) as the control border, not `--color-border`.
- Selected state = indigo fill/gradient **plus** a check icon, thicker (2 px) border, and a text/ARIA state (`aria-checked`, "Selected"). Never color alone.
- Error/success states need icons and text. The palette has no semantic colors; add `--color-danger` (e.g., `#FF6B7A`) and `--color-success` (e.g., `#4ADE80`) and verify ≥ 4.5:1 on both surfaces when defined.
- Focus ring: 3 px solid cyan with 2 px offset, never removed; visible on both bg and surface.

Gradients (sparingly): primary CTA (`#42D9F5 → #5267F2`, 135°; if text overlays the indigo end, check contrast—use dark navy text only on the cyan region or keep gradient subtle), selected-card accent edge, and one faint radial highlight behind the hero board. No gradients on body backgrounds, text, or borders elsewhere.

Dark-only at launch (brand is dark). Declare `color-scheme: dark` so native controls and scrollbars match. A light theme is out of scope for v1.

### 6.2 Typography
- Family: one modern sans-serif, variable font, self-hosted (e.g., Inter, or a system stack `ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif` for zero font cost). Self-host with `font-display: swap`, subset to Latin, preload only the regular weight if using a web font.
- Weights: 400 body, 600 headings/buttons (optionally 700 for H1 only). No more than 3 weights.
- Fluid scale (CSS `clamp`, base 16 px):

| Role | Size | Line-height | Notes |
|---|---|---|---|
| H1 (page title) | `clamp(2rem, 1.4rem + 3vw, 3.5rem)` | 1.1 | Letter-spacing −0.02em |
| H2 (section) | `clamp(1.5rem, 1.2rem + 1.5vw, 2.25rem)` | 1.2 | |
| H3 (card/subsection) | `clamp(1.125rem, 1.05rem + .4vw, 1.375rem)` | 1.3 | |
| Body | 1rem (1.0625rem ≥ 1024 px) | 1.65 | Max line length 65–72ch for articles |
| Lead paragraph | 1.125–1.25rem | 1.55 | Hero/intros |
| Caption / small | 0.875rem | 1.5 | Never below 14 px; muted color |

- Text must reflow at 200% zoom and respect user font-size settings (rem units).
- Sentence case for headings. No decorative typefaces, all-caps limited to tiny labels.

### 6.3 Spacing, layout, shape
- 4 px base unit. Scale: 4, 8, 12, 16, 24, 32, 48, 64, 96 (tokens `--space-1…9`).
- Container: `max-width: 1120px` for marketing, `720px` text column for articles, side padding `16px` (mobile) → `24px` (tablet) → `32px` (desktop), centered. Game page uses a wider fluid container (see §7).
- Section vertical spacing: 48 px mobile → 96 px desktop. Heading-to-content 16–24 px.
- Radius: 8 px controls, 12 px cards, 16 px large panels. Pills only for status chips.
- Cards: `--color-surface` fill, 1 px `--color-border`, no shadow by default. Single soft shadow (`0 8px 24px rgba(0,0,0,.35)`) only on elevated overlays (menu panel, dialogs).
- Buttons: min height 44 px (48 px for primary CTAs on touch); horizontal padding 20–24 px; 8–12 px gap between adjacent buttons. Variants: Primary (cyan or gradient, navy text), Secondary (outline, muted border, white text), Tertiary (text link style with underline). Disabled state shown with reduced contrast **and** text/`aria-disabled`.
- Links in prose: cyan with underline (underline is the non-color cue).
- Motion: ≤ 200 ms transitions on color/opacity/transform only; no parallax, autoplay, or looping animation. Wrap all in `@media (prefers-reduced-motion: no-preference)`; with reduced motion, state changes are instant.

### 6.4 Logo and iconography
- Logo mark: a square 3×3 (or 4×4) grid outline with one thick bar crossing a gap and a path/line threading through it — evokes board, wall, path. Built from straight lines and 2 colors max (cyan + white; indigo optional).
- Constraints: legible at 16×16 (favicon), so the favicon uses a simplified variant (square + single bar + single path) with a minimum stroke width of 1 px at 16 px, and a solid navy rounded-square background tile for contrast.
- Deliverables: SVG logo (mark + wordmark horizontal), SVG mark only, `favicon.svg`, `favicon.ico` (32), `apple-touch-icon.png` (180), `icon-192.png`, `icon-512.png`, maskable icon, OG image template (1200×630).
- Wordmark: "Quoridor.online" in the site typeface, weight 600; ".online" in muted blue-gray or cyan.
- Icons: single line-icon set (2 px stroke, 24 px grid, rounded joins, `currentColor`), e.g. Lucide-style; all inline SVG, `aria-hidden="true"` when decorative.
- Illustrations: board-inspired, geometric, flat, built from the palette (9×9 grid, two pawns, a few walls). Must not copy or imitate the official board's artwork, box art, or pawn/wall designs; do not use publisher logos or the word "official".

---

## 7. Responsive behavior

Mobile-first breakpoints (min-width): `480` large phone, `768` tablet, `1024` laptop, `1440` wide desktop. The 320 px layout is the baseline; every layout must work there first.

| Element | 320–767 | 768–1023 | 1024–1439 | ≥ 1440 |
|---|---|---|---|---|
| Header | Logo, Play Now, menu button | Logo, Play Now, menu or inline nav if it fits | Full inline nav + Play Now | Same, container-capped |
| Hero | Stacked: text, CTAs (full-width buttons), then board preview | Stacked or 2-col | 2-col: text left, board right | 2-col, max container |
| Mode cards | 1 column | 3 columns if each ≥ 220 px, else 1 (or 2 + 1) | 3 columns | 3 columns |
| Private-room strip | Stacked buttons | Row | Row | Row |
| Edu cards / features | 1 col | 2 col | 3 col (features) / 2–3 (edu) | Same |
| Footer | Single column | 2 col | 3–4 col | Same |
| Article pages | Single column, TOC collapsed (`<details>`) | Single column | Content + sticky TOC sidebar | Same |

General rules:
- No horizontal scroll at any width (test 320 px and 200% zoom); use `min-width: 0` on grid/flex children, `overflow-wrap: anywhere` on long tokens (codes, links), tables wrapped in scroll containers only when unavoidable.
- Touch targets ≥ 44×44 CSS px with ≥ 8 px between neighbors. Nothing depends on hover; tooltips have tap/focus equivalents.
- Respect safe-area insets (`env(safe-area-inset-*)`) for fixed bars.
- Viewport meta: `width=device-width, initial-scale=1`; never disable zoom.
- Use `dvh`/`svh` rather than `100vh` for full-height sections (mobile browser bars).

### Game screen layout (all play routes + room)
The board is the priority; page chrome shrinks around it.
- The board is a square: `width = min(100% of container width, available height after header/status/controls)`, using `aspect-ratio: 1/1` and container/viewport units. Minimum comfortable board size on a 320 px phone ≈ 288 px (16 px gutters); at 288 px, a 9×9 board gives ~32 px cells, wall slots need enlarged hit areas (see below).
- **Portrait phone/tablet:** header (compact) → player/turn bar (opponent) → board → player bar (you) → control row (wall counts, undo/resign/leave). Page does not scroll during play; the board region is fixed to the viewport minus chrome.
- **Landscape phone / desktop:** board left (square, as large as the height permits), side panel right (turn, wall counts, move log, controls, chat/status). Side panel ≥ 280 px; collapses below board when width < ~720 px.
- **Wall placement on touch:** wall slots are narrow, so use a two-step interaction (tap to preview/select slot, confirm, with a visible cancel) or drag with offset preview; hit areas padded beyond the visible gap; orientation toggle button; all actions also reachable by keyboard (arrow-key cursor + toggles) and exposed in text via an `aria-live` move announcer. Detailed interaction design is part of the game-implementation phase.
- Header on game routes may compact further (hide secondary nav links behind the menu) but keeps a way out.
- Supporting content (rules link, difficulty explainer) goes below the game fold or in a collapsible panel — gameplay actions and educational content are visually separated.

---

## 8. SEO and indexability

### 8.1 Keyword-to-page mapping (proposed targets, not verified volumes)

| Page | Primary target | Natural secondary variations |
|---|---|---|
| `/` | quoridor game, quoridor online | play Quoridor online, online Quoridor game, free browser Quoridor |
| `/play/` | quoridor game online | play Quoridor online free, Quoridor vs computer, play Quoridor with a friend |
| `/how-to-play-quoridor/` | how to play Quoridor | Quoridor instructions for beginners, how do you win Quoridor |
| `/quoridor-rules/` | quoridor rules | Quoridor wall rules, can you jump in Quoridor |
| `/quoridor-strategy/` | quoridor strategy | Quoridor tips, how to win Quoridor, Quoridor wall strategy |
| `/quoridor-board-game/` | quoridor board game | Quoridor game board, Quoridor pieces |

Rules: one primary intent per URL; each variation used where it reads naturally (title, H1/H2, first paragraph, image alt, internal anchor text); no repeated phrase blocks; validate against Search Console data after launch and revise.

`/quoridor-online/` is **not** created: "quoridor online" belongs to the homepage. Revisit only if (a) search data shows a distinct intent the homepage can't satisfy, and (b) there's genuinely different content (e.g., an online-play guide, etiquette, disconnect policy) — not a re-skin of the homepage.

### 8.2 Per-page metadata (draft; finalize with real copy)

| URL | `<title>` (≤ ~60 chars) | Meta description (≤ ~155 chars) |
|---|---|---|
| `/` | Quoridor Online — Play the Quoridor Game Free in Your Browser | Play Quoridor online against a friend, a computer opponent, or on one device. No registration needed. *(Only when true.)* |
| `/play/` | Play Quoridor Game Online — Choose a Mode | Choose how to play Quoridor: online, against the computer, or with a friend on the same device. |
| `/how-to-play-quoridor/` | How to Play Quoridor — Beginner's Guide | Learn how to play Quoridor: the goal, how pawns move, how to place barriers, and how to win. |
| `/quoridor-rules/` | Quoridor Rules — Setup, Movement & Wall Placement | Clear Quoridor rules: board setup, legal moves, wall restrictions, and winning conditions. |
| `/quoridor-strategy/` | Quoridor Strategy — Tips for Pathfinding & Walls | Improve at Quoridor with strategy on shortest paths, wall timing, defense, and common mistakes. |
| `/quoridor-board-game/` | Quoridor Board Game — Overview & How It Works | What the Quoridor board game is, its components, the central challenge, and how play modes differ. |

Titles/descriptions are unique per page; templates inject them from per-route metadata, with a build-time check that fails on duplicates, missing values, or length overruns.

### 8.3 Technical requirements

| Area | Requirement |
|---|---|
| Rendering | All public informational pages and the homepage are static-generated (SSG) or server-rendered: full content, headings, links, and metadata in the initial HTML, no JS needed to read them. Game UIs are client-rendered islands within a server-rendered shell. |
| Status codes | Unknown URLs → real **404**. Never serve the homepage (or a 200 "not found" shell) for unknown paths; configure the host's fallback accordingly and don't use SPA catch-all rewrites. Invalid `/room/{id}/` → app-level error state; respond with 404 (or 200 + `noindex` if the SPA must resolve it—prefer 404/410 for expired rooms). Retired URLs → 301 to the closest equivalent. |
| Canonicals | Absolute `<link rel="canonical">` per indexable page, self-referencing. Pick one host (`https://quoridor.online`, no `www` or redirect it), HTTPS only (HSTS), consistent trailing slash (as listed above), lowercase paths. Redirect all variants (http, www, no-slash, query-string duplicates) with single 301 hops. |
| Robots meta | Rooms, create/join-room, and 404: `noindex`. Room pages: `noindex, nofollow, noarchive`. Send the same via `X-Robots-Tag` header for `/room/*` so it holds even if HTML fails. |
| robots.txt | Allow all public pages; `Disallow: /room/` (crawl-budget hygiene) and API/WebSocket paths; reference the sitemap. **Disallow does not protect privacy** (the file is public, and a blocked URL can still be indexed if linked), so protection comes from unguessable IDs, `noindex`, no public links to rooms, and server-enforced access. Caution: if `/room/` is disallowed, crawlers can't see its `noindex`; since room URLs are never linked publicly, either approach is acceptable. Decision: use `noindex` + `X-Robots-Tag` and also `Disallow` in robots.txt, accepting that `noindex` is a backstop. |
| Sitemap | `/sitemap.xml`, canonical absolute URLs only, `200`-status and indexable only, `<lastmod>` from real content changes. Contains: `/`, `/play/`, the four informational pages, about, contact, privacy, terms (plus mode pages if indexed). **Never** contains rooms, create/join-room, 404, or any URL carrying a code/token. |
| Structured data (JSON-LD) | `WebSite` (+ `Organization` only with real, non-invented facts) on home; `BreadcrumbList` on subpages; `Article`/`WebPage` on guides; `VideoGame`/`Game` markup only if accurate; `FAQPage` only if visible content matches. No fabricated ratings, reviews, or counts. |
| Open Graph / Twitter | `og:title`, `og:description`, `og:type`, `og:url`, `og:image` (1200×630, with alt), `og:site_name`, `twitter:card=summary_large_image`. Rooms: generic OG only, with no room ID, code, or names in any metadata. |
| Language & viewport | `<html lang="en">`; `<meta charset>`; viewport meta. Add `hreflang` only when translated versions exist. |
| Semantic HTML | One `<h1>` per page; logical `h2→h3`; landmarks `<header> <nav> <main> <footer>`; lists for lists; `<details>` for FAQ; tables only for tabular data; descriptive link text (no "click here"). |
| Internal links | Crawlable `<a href>` (never click handlers only). Every informational page links to the other three and to `/play/`; each guide ends with a "Play now" CTA. Breadcrumbs on subpages. Footer provides sitewide links. Homepage reaches every indexable page within one click (via nav/footer/sections). |
| Performance | Targets (75th percentile, mobile): LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1. Approaches: ship minimal JS on content pages, load the game bundle only on play routes, inline critical CSS, self-host fonts with `font-display`, SVG for illustrations, AVIF/WebP with explicit `width/height`, `loading="lazy"` below the fold (not for LCP image), compression (Brotli), long-cache immutable hashed assets, CDN. |
| Images | Descriptive `alt` (functional images describe function; decorative `alt=""`), natural keywords where accurate, responsive `srcset`. |
| Accessibility (SEO-adjacent) | WCAG 2.2 AA target; labels on all fields; error messages programmatically tied to inputs; live regions for game events; keyboard-operable board. |
| Security headers | CSP, `Referrer-Policy: strict-origin-when-cross-origin` (also prevents invite-URL leakage in referrers; room pages use `no-referrer`), `X-Content-Type-Options`, frame restrictions. |
| Invitation URLs | The invite link is the `roomId` URL; avoid putting the pairing code in the URL. Use `rel="noreferrer"` on any outbound links from room pages; no third-party analytics scripts on room pages that could capture the URL. |
| Duplicate avoidance | No parameter variants indexed (`?ref=`, UTM): canonical ignores them. No tag/category/archive pages at launch. |
| Monitoring | Search Console + Bing Webmaster, sitemap submission, coverage review post-launch, 404 log review, broken-link check in CI. |

---

## 9. Static, legal, and error pages

| Page | Contents (structure only, final copy later) | Cautions |
|---|---|---|
| `/about/` | Purpose of the site; focus on accessible browser-based strategy gaming; what you can do here (only current features); non-affiliation notice; link to Play and Contact | **No** invented history, team bios, awards, user counts, or founding dates |
| `/contact/` | Three clearly labeled paths: Feedback, Technical support, Business inquiries; for each: what to include and expected topic | **Do not invent an email address, form endpoint, or social links.** Until a real channel exists, show the structure with a "contact channel coming soon" note or omit the page from nav. If a form is added: spam protection, privacy notice link, no collection of more than necessary |
| `/privacy-policy/` | Reserved; must be written from the real system: data collected (usernames, IP/logs, room metadata, session tokens), retention/expiry of rooms, analytics, cookies/local storage, third-party processors (hosting, CDN, analytics), user rights, contact, effective date | Legal review. Don't publish placeholder text that misstates practices. Until final, show a clearly marked draft |
| `/terms/` | Reserved; service use, acceptable use and username conduct, no guarantees of availability, disconnect/forfeit handling, intellectual property and non-affiliation, limitation of liability, changes, governing law | Legal review |
| 404 | Branded page, on-brand illustration (a pawn blocked by a wall), clear message ("We couldn't find that page"), buttons: Home, Play; optional links to How to Play | HTTP 404, `noindex`, same header/footer, no redirect |
| Error/maintenance | Branded 500/503 page with `Retry-After` for maintenance | |
| Cookie/consent | Decide after the privacy audit: if only strictly necessary storage is used, no banner; if analytics/ads are added in regulated regions, consent is required before they load | |

---

## 10. Implementation priorities and dependencies

### Phase 0 — Foundations (blocks everything)
1. Decisions: tech stack with SSG/SSR support (e.g., Astro/Next.js/SvelteKit for pages + a client-side game island), hosting/CDN, domain/HTTPS/redirect rules, repo and CI.
2. Design tokens (§6), base CSS, layout components (container, grid, card, button, form field, dialog), accessible header/menu/footer.
3. Logo/favicon set and OG template.
4. Trademark/naming review of "Quoridor" in the domain and copy; non-affiliation text. *(Depends on nothing; do early because it can change branding.)*

### Phase 1 — Public shell and content (can ship without any working game)
1. Routing and metadata system (title/description/canonical/OG per route, duplicate checks).
2. Homepage sections A–I, using feature flags so unimplemented features aren't advertised.
3. `/play/` with mode cards that show "Coming soon" for unbuilt modes (not indexed until functional if they would be thin or misleading).
4. Four informational pages (write: Rules first since the game engine and other pages depend on its exact wording, then How to Play, Strategy, Board Game).
5. About, Contact (structure), Privacy and Terms (clearly drafted), 404/500.
6. `robots.txt`, `sitemap.xml`, JSON-LD, redirects, security headers.
7. Quality gates: Lighthouse/axe in CI, link checker, 320 px overflow test, keyboard test.

### Phase 2 — Local play (no backend)
Depends on: design system, **Rules finalized** (rule engine correctness, including pawn jumps and path-blocking checks), board component (responsive square, keyboard/touch input, wall placement UX).
Deliverable: `/play/local/` functional. This is the first mode and also the base for the other two.

### Phase 3 — Computer opponent
Depends on: engine + local board UI. Implement difficulty levels, then **tune and describe them from measured behavior**; update the §4.2 copy to match. `/play/computer/`.

### Phase 4 — Online multiplayer
Depends on: engine (authoritative on server), backend and real-time transport (WebSocket or similar), session tokens, username validation/moderation, rate limiting, reconnection and forfeit rules, privacy policy updated for data actually collected.
Order: (a) room infrastructure + `/room/{id}/` states, (b) create/join flows (private rooms are simpler than matchmaking and test the sync layer), (c) matchmaking queue for `/play/online/`.
Server must validate all moves; never trust the client.

### Phase 5 — Polish and growth
Index the mode pages once they have unique copy; analytics (privacy-compliant) and Search Console review; expand content (e.g., puzzles, glossary, variants) only where there is distinct search intent; accessibility audit by a real user test; i18n if justified.

### Dependency summary
```
Tokens + components ─┬─> Public shell ─┬─> Informational pages ──> SEO launch
                     │                 └─> Homepage (flag-gated)
Rules wording ───────┴─> Rule engine ──> Local board ──> Computer ──> (reuse in)
                                                    └──> Online rooms ──> Matchmaking
Privacy policy must be updated before any online data collection goes live.
```

---

## 11. Open decisions (need an owner)

1. Indexing of `/play/online/`, `/play/computer/`, `/play/local/`: index at launch with unique copy, or `noindex` until polished. *(Recommendation: index only `/play/` at launch.)*
2. Whether the computer mode asks for a username.
3. Room start model: auto-start vs. both-ready.
4. Disconnect/forfeit grace period and room TTL (affects Terms and Privacy).
5. Real contact channel(s) for `/contact/`.
6. Tech stack and hosting choice (must support SSG/SSR and real 404s).
7. Whether to add a "Board Game" link to the main nav (currently footer-only to keep nav compact).
