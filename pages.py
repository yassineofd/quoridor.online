"""Page content for Quoridor Online. Each function returns a lib.Page; build.py renders the shared layout."""

import re

from lib import (
    FEATURES, INDEX_MODE_PAGES, SITE_NAME, Page, icon, board_svg,
    HERO_WALLS, HERO_PAWNS, HERO_ALT,
)

ANY_MODE_LIVE = any(FEATURES[k] for k in ("online", "computer", "local"))


def live_ways():
    """Only the ways to play that actually work, as a readable list."""
    ways = []
    if FEATURES["online"]:
        ways.append("online against another person")
    if FEATURES["computer"]:
        ways.append("against the computer")
    if FEATURES["local"]:
        ways.append("with a friend on the same device")
    return ways[0] if len(ways) == 1 else ", ".join(ways[:-1]) + " or " + ways[-1] if ways else ""


# ---------------------------------------------------------------- shared fragments
def badge(feature: str) -> str:
    return "" if FEATURES[feature] else '<span class="badge">Coming soon</span>'


def crumbs(items):
    """items: [(label, path_or_None)] after Home. Last one is the current page."""
    parts = ['<li><a href="/">Home</a></li>']
    for label, path in items:
        parts.append(f'<li><a href="{path}">{label}</a></li>' if path else f'<li><span aria-current="page">{label}</span></li>')
    return '<nav class="breadcrumbs" aria-label="Breadcrumb"><ol>' + "".join(parts) + "</ol></nav>"


def page_head(h1, lead, trail):
    return (
        '<div class="page-head"><div class="container">'
        + crumbs(trail)
        + f"<h1>{h1}</h1>"
        + f'<p class="lead">{lead}</p>'
        + "</div></div>"
    )


def mode_cards(heading_tag="h3", home=False):
    """home=True: the home page's wording, listing only the modes that actually work."""
    h = heading_tag
    modes = [
        ("online", "online", "globe", "Play Quoridor Online", "Play Online",
         "Play Quoridor online against another person. Choose a username, no registration, and enter matchmaking. Want to play a specific friend? Use a private room.",
         "Play Quoridor online against another person. Choose a username, no registration, and enter matchmaking. Want to play a specific friend? Use a private room.",
         "/play/online/", "Play Online"),
        ("computer", "robot", "bot", "Play Quoridor Against the Computer", "Play Against the Computer",
         "Practice against the computer. Pick Easy, Medium, Hard or Expert, from gentle for beginners to a tougher test. No registration needed.",
         "Practice against the computer. Pick Easy, Medium, Hard or Expert, from gentle for beginners to a tougher test. No registration needed.",
         "/play/computer/", "Play vs Robot"),
        ("local", "local", "users", "Play Quoridor With a Friend", "Play Locally",
         "Two players, one device. You share the screen and take turns on the same board. Great for playing side by side.",
         "Play with a friend on the same device. You share the screen and take turns on the same board. No registration needed.",
         "/play/local/", "Play Together"),
    ]
    cards = []
    for feat, cls, ic, hub_title, home_title, hub_text, home_text, href, label in modes:
        if home and not FEATURES[feat]:
            continue  # only advertise modes that actually work
        title, text = (home_title, home_text) if home else (hub_title, hub_text)
        cards.append(f"""
  <article class="card mode-card mode-card--{cls}">
    <span class="icon-badge">{icon(ic)}</span>
    <div class="mode-body">
      <{h}>{title}</{h}>
      {'' if home else badge(feat)}
      <p>{text}</p>
    </div>
    <a class="btn btn--primary" href="{href}">{label.replace("Robot", "Computer") if home else label} {icon('arrow')}</a>
  </article>""")
    return f"""
<div class="grid grid--3 grid--modes">{"".join(cards)}
</div>"""


def private_strip(tag="h2", heading="Play privately with a friend"):
    return f"""
<div class="private-strip">
  <span class="icon-badge private-strip__icon">{icon('users')}</span>
  <div class="private-strip__body">
    <p class="eyebrow">Private match</p>
    <{tag}>{heading}</{tag}>
    <p class="private-strip__text">Private matches are part of online play. Share a direct invitation link or a short pairing code so your friend can join your room.{' ' if FEATURES['rooms'] else ' Private rooms are coming soon.'}</p>
    <ul class="chip-list" aria-label="Ways to invite a friend">
      <li>{icon('link')} Invitation link</li>
      <li>{icon('key')} Pairing code</li>
      <li>{icon('check')} No account needed</li>
    </ul>
  </div>
  <div class="btn-row private-strip__actions">
    <a class="btn btn--primary btn--lg" href="/play/create-room/">{icon('plus')} Create a Room</a>
    <a class="btn btn--secondary btn--lg" href="/play/join-room/">{icon('login')} Join a Room</a>
  </div>
</div>"""


def cta_panel(text="Ready to put it into practice?"):
    return f"""
<div class="card cta-panel">
  <h2>{text}</h2>
  <p>Choose a way to play Quoridor online, against the computer, or with a friend on one device.</p>
  <a class="btn btn--primary" href="/play/">Play Now {icon('arrow')}</a>
</div>"""


def article_page(path, title, description, h1, lead, sections, related, trail_label, nav_key, extra_after="", cta=True, schema=None):
    """sections: [(id, heading, html)]. related: [(label, path, blurb)]."""
    toc = "".join(f'<li><a href="#{i}">{h}</a></li>' for i, h, _ in sections)
    body_sections = "".join(f'<section id="{i}" aria-labelledby="{i}-h"><h2 id="{i}-h">{h}</h2>{html}</section>' for i, h, html in sections)
    rel = "".join(f'<li><a href="{p}"><strong>{l}</strong></a>: {b}</li>' for l, p, b in related or ())
    related_html = f"""<aside class="related" aria-labelledby="related-h">
      <h2 id="related-h">Keep learning</h2>
      <ul>{rel}</ul>
    </aside>""" if related else ""
    body = (
        page_head(h1, lead, [(trail_label, None)])
        + f"""
<div class="container article-layout">
  <details class="toc" open>
    <summary>On this page</summary>
    <nav aria-label="On this page"><ol>{toc}</ol></nav>
  </details>
  <article class="article">
    {body_sections}
    {extra_after}
    {cta_panel() if cta else ""}
    {related_html}
  </article>
</div>"""
    )
    return Page(path=path, title=title, description=description, body=body,
                breadcrumbs=[(trail_label, path)], nav_key=nav_key, schema=schema or [])


def figure(svg, caption):
    return f"<figure>{svg}<figcaption>{caption}</figcaption></figure>"


# ---------------------------------------------------------------- homepage
# The home page is a fixed structure (check.py enforces it): H1 + CTAs, then these H2s in order.
HOME_H1 = "Play Quoridor Online"
HOME_CTAS = (("Play Quoridor Now", "/play/"), ("Learn How to Play", "/how-to-play-quoridor/"))
HOME_H2S = (
    "Choose How You Want to Play",
    "How to Play Quoridor",
    "A Strategy Board Game of Movement and Tactics",
    "Frequently Asked Questions About Quoridor",
)
HOME_FAQ_QUESTIONS = (
    "Can I play Quoridor online for free?",
    "Can I play Quoridor against a computer?",
    "Can two people play on the same device?",
    "Do I need an account?",
    "How many walls does each player get?",
)


def home_faq():
    """[(question, answer_html)] built from what the site actually does."""
    ways = live_ways()
    return [
        (HOME_FAQ_QUESTIONS[0],
         "Yes. Playing is free and you don't need to register. "
         + (f"You can play {ways}. " if ANY_MODE_LIVE else "")
         + ("Online games pair you with another player through matchmaking, or you can invite a friend to a private room."
            if FEATURES["online"] else "Online play against other people is coming soon.")),
        (HOME_FAQ_QUESTIONS[1],
         'Yes. Choose <a href="/play/computer/">play against the computer</a>, then pick Easy, Medium, Hard or Expert. The computer opponent runs in your browser, so nothing is sent anywhere.'
         if FEATURES["computer"] else "Playing against the computer is coming soon."),
        (HOME_FAQ_QUESTIONS[2],
         'Yes. In <a href="/play/local/">local play</a> two players share one screen and take turns on the same board. Player 1 moves first.'
         if FEATURES["local"] else "Same-device play is coming soon."),
        (HOME_FAQ_QUESTIONS[3],
         "No. Nothing on the site requires an account. "
         + ("When you play online you just choose a display name, which is not proof of identity."
            if FEATURES["online"] else "Where a mode asks for a name, it is only a display name.")),
        (HOME_FAQ_QUESTIONS[4],
         'In a two-player game each player starts with 10 walls. Once they are used up you can only move your pawn. The <a href="/quoridor-rules/">Quoridor rules</a> cover wall placement in full.'),
    ]


def home():
    ways = live_ways()
    live_note = f" You can play {ways}." if ANY_MODE_LIVE else ""
    faq = home_faq()
    faq_html = "".join(f'<details><summary>{q}</summary><div class="answer"><p>{a}</p></div></details>' for q, a in faq)
    faq_schema = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)}}
            for q, a in faq
        ],
    }

    desc = (
        f"Play Quoridor in your browser {ways}. A free strategy game with no registration."
        if ANY_MODE_LIVE
        else "Quoridor online: learn the Quoridor game, study the rules and strategy, and choose online, computer or same-device play as each mode launches. No account needed."
    )
    (cta1, href1), (cta2, href2) = HOME_CTAS
    h2_modes, h2_how, h2_strategy, h2_faq = HOME_H2S
    body = f"""
<section class="hero" aria-labelledby="hero-h">
  <div class="container hero-grid">
    <div>
      <p class="eyebrow">Strategy board game</p>
      <h1 id="hero-h">{HOME_H1}</h1>
      <p class="lead">Quoridor is a strategy board game where two players race their pawns to the opposite side of a 9×9 board while placing walls to slow each other down.{live_note}</p>
      <div class="btn-row">
        <a class="btn btn--primary btn--lg" href="{href1}">{cta1} {icon('arrow')}</a>
        <a class="btn btn--secondary btn--lg" href="{href2}">{cta2}</a>
      </div>
    </div>
    <div class="hero-board">{board_svg(HERO_WALLS, HERO_PAWNS, HERO_ALT)}</div>
  </div>
</section>

<section class="section--tight" aria-labelledby="modes-h">
  <div class="container">
    <div class="section-head">
      <h2 id="modes-h">{h2_modes}</h2>
      <p class="text-muted">Every way to play is free and works in your browser, with no account.</p>
    </div>
    {mode_cards('h3', home=True)}
  </div>
</section>
{'<section class="section--tight" aria-label="Play privately with a friend"><div class="container">' + private_strip('h3') + '</div></section>' if FEATURES['rooms'] else ''}

<section class="section" aria-labelledby="how-h">
  <div class="container grid grid--2">
    <div>
      <h2 id="how-h">{h2_how}</h2>
      <p class="text-muted">The objective is simple: move your pawn to the opposite side of the board before your opponent does. Walls are your tool for making their trip longer than yours.</p>
      <ol class="steps">
        <li><strong>Race to the other side</strong>Your pawn starts in the middle of your edge and must reach any square on the far edge.</li>
        <li><strong>Move or place a wall</strong>On each turn you either step your pawn or place one wall.</li>
        <li><strong>Never seal the path</strong>A wall is only legal if both players still have a legal path to their goal.</li>
      </ol>
      <div class="btn-row">
        <a class="btn btn--secondary" href="/how-to-play-quoridor/">How to play Quoridor</a>
        <a class="btn btn--secondary" href="/quoridor-rules/">Read the Quoridor rules</a>
      </div>
    </div>
    <div class="card"><h3>Why the walls matter</h3><p class="text-muted">A good wall costs you one turn but costs your opponent several. Judging that trade, again and again, is the whole game.</p>{board_svg([("h",3,2),("h",3,4),("v",4,3)], [(5,3,"p1"),(3,3,"p2")], "Quoridor wall strategy. A small cluster of indigo barriers forcing a white ring pawn to take a detour around the walls.")}</div>
  </div>
</section>

<section class="section" aria-labelledby="strategy-h">
  <div class="container">
    <div class="section-head">
      <h2 id="strategy-h">{h2_strategy}</h2>
      <p class="text-muted">There are no dice, cards or hidden information. Every game is decided by what you plan and what you notice.</p>
    </div>
    <ul class="feature-list">
      <li>{icon('move')}<div><strong>Route planning</strong><span class="text-muted">Count the shortest path for both pawns before every move.</span></div></li>
      <li>{icon('wall')}<div><strong>Blocking</strong><span class="text-muted">Place walls that force long detours, not walls that add a single step.</span></div></li>
      <li>{icon('clock')}<div><strong>Timing</strong><span class="text-muted">You only have 10 walls, so choose the moment each one pays off most.</span></div></li>
      <li>{icon('target')}<div><strong>Anticipating your opponent</strong><span class="text-muted">Think about where their pawn is heading and which walls they could play next.</span></div></li>
    </ul>
    <p class="mt-4 text-muted">It runs in your browser with nothing to install, and no account is needed. Read the <a href="/quoridor-strategy/">Quoridor strategy guide</a> to improve, or learn more about the <a href="/quoridor-board-game/">Quoridor board game</a>.</p>
  </div>
</section>

<section class="section" aria-labelledby="faq-h">
  <div class="container">
    <div class="section-head"><h2 id="faq-h">{h2_faq}</h2></div>
    <div class="faq prose">{faq_html}</div>
    <p class="mt-4"><a class="btn btn--primary" href="/play/">{cta1} {icon('arrow')}</a></p>
  </div>
</section>
"""
    return Page(
        path="/",
        title="Quoridor Online: Play the Quoridor Game in Your Browser",
        description=desc,
        body=body,
        nav_key="home",
        schema=[{"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME}, faq_schema],
    )


# ---------------------------------------------------------------- play hub and modes
def play_faq():
    """[(question, answer_html)] for /play/, gated on the modes that actually work."""
    friend = "You can play locally on the same device"
    if FEATURES["rooms"]:
        friend += " or create a private online room and invite your friend."
    else:
        friend += ". Private online rooms are coming soon."
    return [
        ("Can I play Quoridor online for free?",
         "Yes. You can play Quoridor online on this website without registration. Choose an available game mode and start playing."),
        ("Can I play Quoridor against a computer?",
         "Yes. Select the computer mode and choose Easy, Medium, Hard, or Expert difficulty."),
        ("Can I play Quoridor with a friend?", friend),
        ("Do I need an account to play Quoridor?",
         "No account is required to start playing. Online play uses a username rather than a registration process."
         if FEATURES["online"] else "No account is required to start playing."),
        ("What is the objective of Quoridor?",
         "The goal is to move your pawn to the opposite side of the board before your opponent. You can also place walls to create detours, but you cannot completely block a player's route to the goal."),
    ]


def play_hub():
    faq = play_faq()
    faq_html = "".join(f"<h3>{q}</h3><p>{a}</p>" for q, a in faq)
    faq_schema = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq],
    }
    body = (
        page_head(
            "Play Quoridor Game Online",
            "Choose how you want to play: online against another person, against the computer at your own level, or side by side on one device.",
            [("Play", None)],
        )
        + f"""
<section class="section--tight" aria-labelledby="modes-h"><div class="container">
  <div class="section-head"><h2 id="modes-h">Choose Your Quoridor Game Mode</h2></div>
  {mode_cards('h3')}
</div></section>
<section class="section--tight" aria-label="Play Quoridor online with friends"><div class="container">{private_strip('h2', 'Play Quoridor Online With Friends')}</div></section>
<section class="section--tight" aria-labelledby="variants-cta-h"><div class="container">
  <div class="card cta-panel">
    <h2 id="variants-cta-h">Try a Quoridor Variant</h2>
    <p>Same pawns and walls, a new kind of race. Start with Wallrush, where both pawns begin on the same line of a taller board.</p>
    <a class="btn btn--secondary" href="/variants/">Explore Variants {icon('arrow')}</a>
  </div>
</div></section>
<section class="section--tight" aria-labelledby="achievements-cta-h"><div class="container">
  <div class="card cta-panel">
    <h2 id="achievements-cta-h">Earn Achievements and Climb the Ranks</h2>
    <p>Every game you finish earns points. Beat the robots, build a streak and unlock achievements. Your progress stays in your browser, with no account.</p>
    <a class="btn btn--secondary" href="/achievements/">See Your Achievements {icon('arrow')}</a>
  </div>
</div></section>
<section class="section" aria-labelledby="how-h"><div class="container prose">
  <h2 id="how-h">How to Play Quoridor</h2>
  <p>Quoridor is a strategy board game built around two choices: move your pawn toward the goal or place a wall to slow your opponent down. Every wall uses a limited resource, so the best move is not always the most obvious one.</p>
  <p>Your objective is to reach the opposite side of the board before your opponent. You can make progress along your own route, create detours for your opponent, and adapt your strategy as the board changes. However, you must always leave each player a legal path to their goal.</p>
  <p>New to the game? Learn the rules before your first match.</p>
  <div class="btn-row">
    <a class="btn btn--secondary" href="/how-to-play-quoridor/">Learn How to Play Quoridor</a>
    <a class="btn btn--secondary" href="/quoridor-rules/">Read the Quoridor Rules</a>
  </div>
</div></section>
<section class="section" aria-labelledby="strategy-h"><div class="container prose">
  <h2 id="strategy-h">Improve Your Quoridor Strategy</h2>
  <p>Winning takes more than moving forward. Think ahead before placing a wall, compare possible routes, and decide when to advance your pawn instead of using a barrier. Understanding how your decisions affect both players can help you make better moves.</p>
  <p>Explore practical tactics and learn how to use your walls effectively.</p>
  <div class="btn-row"><a class="btn btn--secondary" href="/quoridor-strategy/">Explore Quoridor Strategy</a></div>
</div></section>
<section class="section" aria-labelledby="faq-h"><div class="container prose article">
  <h2 id="faq-h">Frequently Asked Questions</h2>
  {faq_html}
  <p class="mt-4">Ready to put your tactics to the test?</p>
  <div class="btn-row"><a class="btn btn--primary btn--lg" href="/play/online/">Play Quoridor Online Now {icon('arrow')}</a></div>
</div></section>
"""
    )
    return Page(
        path="/play/",
        title="Play Quoridor Game Online – Free Strategy Game",
        description=(
            "Play Quoridor game online for free. Challenge the computer, compete against another player, or play with a friend on the same device. No registration required."
            if FEATURES["online"] else
            "Play Quoridor game online for free. Challenge the computer or play with a friend on the same device. No registration required."
        ),
        body=body, breadcrumbs=[("Play", "/play/")], nav_key="play", schema=[faq_schema],
    )


def unavailable(title, text):
    return f"""
<div class="notice" data-unavailable hidden role="status">
  {icon('info')}
  <div><h2>{title}</h2><p>{text}</p>
  <p><a href="/how-to-play-quoridor/">Learn how to play</a> while you wait, or head back to the <a href="/play/">mode list</a>.</p></div>
</div>"""


def server_error():
    """Shown when the game server refuses or can't be reached (live online forms only)."""
    return f"""
<div class="notice notice--error" data-error hidden role="alert">
  {icon('alert')}
  <div><h2>That didn't work</h2><p data-error-text></p><button class="btn btn--secondary" type="button" data-retry>Try again</button></div>
</div>"""


def username_field(note="2 to 20 characters. This is a display name, not an account."):
    return f"""
<div class="field">
  <label for="username">Username</label>
  <input class="input" id="username" name="username" type="text" autocomplete="nickname" maxlength="20" required aria-describedby="username-hint username-error" spellcheck="false">
  <span class="hint" id="username-hint">{note}</span>
  <div class="field-error" id="username-error" role="alert" hidden></div>
</div>"""


GAME_SCRIPTS = ["/assets/js/engine.js", "/assets/js/icons.js", "/assets/js/board.js", "/assets/js/achievements.js", "/assets/js/achievements-ui.js", "/assets/js/game.js"]
# Score, rank and achievements (kept in the browser): the summary under every play form, the Achievements page, and the reward after a game.
PROGRESS_SCRIPTS = ["/assets/js/icons.js", "/assets/js/achievements.js", "/assets/js/achievements-ui.js"]
# The remembered name and scores (profile.js), then the client for the game server: loaded by every page with a play form or a room.
PLAY_SCRIPTS = ["/assets/js/profile.js", "/assets/js/online.js"]


def watch_scripts(path):
    """Every play page except the search page itself carries on a running online search in the background."""
    return ["/assets/js/matchwatch.js"] if FEATURES["online"] and path != "/play/online/" else []


def stage(form_kind, panel_html, board_label, walls=(), pawns=(), live=False, art=None, form_attrs=""):
    """art: ready-made board picture for pages that are not the classic board (see the variants below)."""
    tall = art is not None and "board-art--tall" in art
    return f"""
<div class="container stage" data-stage>
  <div class="stage-panel">
    <form data-play-form="{form_kind}" {form_attrs}data-live="{'true' if live else 'false'}" novalidate>{panel_html}</form>
    <div class="progress-teaser" data-progress-teaser hidden></div>
  </div>
  <div class="stage-board{' stage-board--tall' if tall else ''}">{art or board_svg(walls, pawns, board_label)}</div>
</div>
<div class="container game-wrap" data-game-wrap hidden><div data-game-host></div></div>"""


MODE_WALLS = [("h", 3, 3), ("v", 5, 5), ("h", 6, 1)]
MODE_PAWNS = [(8, 4, "p1"), (0, 4, "p2")]


def mode_intro(heading_id, heading, *paragraphs):
    """The unique copy under a mode page's form: what the mode is and how it works (what makes the page worth indexing)."""
    return (
        f'<section class="section" aria-labelledby="{heading_id}"><div class="container prose">'
        f'<h2 id="{heading_id}">{heading}</h2>' + "".join(f"<p>{p}</p>" for p in paragraphs)
        + "</div></section>"
    )


def mode_page(path, title, desc, h1, lead, crumb, form_kind, panel, label, indexable=None, scripts=(), live=False, intro=""):
    idx = INDEX_MODE_PAGES if indexable is None else indexable
    parent = [("Play", "/play/")] if path.startswith("/play/") else []
    body = (
        '<div class="page-head"><div class="container">'
        + crumbs(parent + [(crumb, None)])
        + f"<h1>{h1}</h1><p class=\"lead\">{lead}</p></div></div>"
        + stage(form_kind, panel, label, MODE_WALLS, MODE_PAWNS, live)
        + intro
    )
    return Page(
        path=path, title=title, description=desc, body=body,
        indexable=idx, robots=None if idx else "noindex, follow",
        breadcrumbs=parent + [(crumb, path)], scripts=list(dict.fromkeys(list(scripts) + PROGRESS_SCRIPTS + PLAY_SCRIPTS + watch_scripts(path) + ["/assets/js/play.js"])), nav_key="play",
    )


def play_online():
    live = FEATURES["online"]
    searching = f"""
<div class="search-state" data-searching hidden>
  <div class="search-line">
    <span class="spinner" aria-hidden="true"></span><span data-search-text role="status" aria-live="polite" data-i18n-skip>Finding your opponent&hellip;</span><span class="search-elapsed" data-search-elapsed aria-hidden="true"></span>
  </div>
  <div data-slow hidden>
    <div class="search-actions">
      <a class="btn btn--primary btn--block" href="/play/computer/" data-alt>Play against the computer</a>
      <a class="btn btn--secondary btn--block" href="/play/create-room/" data-alt>Invite a friend</a>
    </div>
    <p class="small text-muted mt-4">Your search keeps running in the background. If someone is found while you play, we'll ask whether you want to join them.</p>
  </div>
  <div class="search-cancel"><button class="btn btn--secondary" type="button" data-cancel-search>Cancel search</button></div>
</div>"""
    panel = (
        '<div class="status-line"><span class="status-dot' + (' status-dot--ok' if live else '') + '" aria-hidden="true"></span><span>'
        + ("Matchmaking status: ready" if live else "Matchmaking status: not connected") + '</span></div>'
        + username_field()
        + '<button class="btn btn--primary btn--lg btn--block" type="submit">Find an opponent</button>'
        + ('<p class="small text-muted mt-4">Everyone chooses their own language with the translate button at the top of the page. It only changes what you see, so you can be matched with anyone, whichever language they use.</p>' if live else '')
        + (searching + server_error() if live else
           unavailable("Online matchmaking isn't live yet", "There is no matchmaking server on this site yet, so nobody can be paired with you. Nothing was sent anywhere."))
        + '<p class="small text-muted mt-4" data-hide-searching>Want to play one specific person? Try a private room: <a href="/play/create-room/">create a room</a> or <a href="/play/join-room/">join a room</a>.</p>'
    )
    return mode_page(
        "/play/online/", "Play Quoridor Online Against Another Player",
        "Play Quoridor online against another person. Pick a username, enter matchmaking and start a synchronized game.",
        "Play Quoridor online", "Pick a username, find an opponent, and play a live game against another person.",
        "Play online", "online", panel, "Play Quoridor online: board game preview with two pawns and walls.", live=live,
        indexable=live,  # a page that says "not connected" has nothing to offer a search result
        intro=mode_intro(
            "online-how-h", "How Online Matchmaking Works",
            "Enter a username and press Find an opponent. The site pairs you with the next person who is searching, and the game starts as soon as you are matched. There is nothing to install and no account to make: your username is only a display name for the game.",
            'The usual Quoridor rules apply. On each turn you move your pawn or place a wall, and a wall may never close off every route to the goal. Would you rather play someone you know? <a href="/play/create-room/">Create a private room</a> and send your friend the invitation link, or warm up first <a href="/play/computer/">against the computer</a>.',
        ) if live else "",
    )


def difficulty_choice(value, title, desc, checked=False):
    chk = " checked" if checked else ""
    return f"""
<div class="choice"><input type="radio" name="difficulty" id="d-{value}" value="{value}"{chk}>
  <label class="choice-body" for="d-{value}">
    <span class="check" aria-hidden="true">{icon('check')}</span>
    <span><span class="choice-title">{title}</span><span class="choice-state"> (selected)</span><br><span class="choice-desc">{desc}</span></span>
  </label></div>"""


# How each level plays is defined by static/assets/js/ai.js and measured with tests/ai_bench.py
# (docs/game-engine.md has the results). Keep these descriptions in step with the latest measurements.
DIFFICULTY_LEVELS = [
    ("easy", "Easy", "Good for learning the rules. Makes mistakes on purpose: it wanders and places walls without much of a plan.", False),
    ("medium", "Medium", "A relaxed game for players who know the basics. Takes sensible steps and blocks you when a wall clearly pays off, but doesn't plan ahead.", True),
    ("hard", "Hard", "Looks two moves ahead (its move and your reply) and places walls deliberately. Expect a real challenge.", False),
    ("expert", "Expert", "The strongest level we offer. Searches several moves deeper, taking up to about a second per move, so it can feel slower to answer.", False),
]


def play_computer():
    choices = "".join(difficulty_choice(v, t, d, c) for v, t, d, c in DIFFICULTY_LEVELS)
    panel = (
        f'<fieldset class="fieldset"><legend>Difficulty</legend><div class="choice-group">{choices}</div></fieldset>'
        + '<p class="small text-muted">You move first, as the cyan filled pawn, from the bottom edge. The robot plays on your device; nothing is sent anywhere. In our own test games (20 per pairing, robots against robots) each level beat the one below it at least 16 times out of 20.</p>'
        + f'<button class="btn btn--primary btn--lg btn--block" type="submit">{icon("play")} Start game</button>'
    )
    return mode_page(
        "/play/computer/", "Play Quoridor Against the Computer",
        "Play Quoridor against a computer opponent. Choose Easy, Medium, Hard or Expert and start without registering.",
        "Play Quoridor against the computer", "Choose a difficulty and start a game. No registration needed.",
        "Play against robot", "computer", panel, "Play Quoridor against the computer: board game preview with two pawns and walls.",
        scripts=["/assets/js/engine.js", "/assets/js/ai.js"] + GAME_SCRIPTS[1:],
        intro=mode_intro(
            "computer-how-h", "Practice Quoridor Against the Computer",
            'The computer opponent runs in your browser, so a game starts instantly and works without an account. Start on Easy to see how pawns and walls interact, then move up a level whenever you win comfortably. New to the game? Read <a href="/how-to-play-quoridor/">how to play Quoridor</a>, or study the <a href="/quoridor-strategy/">strategy guide</a> to get more out of your walls.',
        ),
    )


def name_field(n):
    # Under the second name: how to get a score between two friends (game.js counts it when both names were typed).
    hint = '<span class="hint" id="name2-hint">In a two-player game, type both names to keep score of who wins between you. The score stays on this device.</span>' if n == 2 else ""
    described = f"name{n}-hint name{n}-error" if hint else f"name{n}-error"
    return f"""
<div class="field">
  <label for="name{n}">Player {n} name (optional)</label>
  <input class="input" id="name{n}" name="name{n}" type="text" maxlength="20" autocomplete="off" spellcheck="false" aria-describedby="{described}">
  {hint}
  <div class="field-error" id="name{n}-error" role="alert" hidden></div>
</div>"""


def play_local():
    panel = (
        '<div class="card"><h2 class="h-sm">Two players, one device</h2>'
        '<p class="text-muted">You share the screen and take turns on the same board. The active player is always named on screen, with a clear cue when the turn changes.</p>'
        '<ul class="text-muted"><li>Player 1 uses the filled cyan pawn and moves first, from the bottom edge.</li><li>Player 2 uses the white ring pawn, from the top edge.</li><li>Pass the device after each move.</li></ul></div>'
        '<div class="spacer"></div>'
        + name_field(1) + name_field(2)
        + f'<button class="btn btn--primary btn--lg btn--block" type="submit">{icon("play")} Start game</button>'
    )
    return mode_page(
        "/play/local/", "Play Quoridor With a Friend on One Device",
        "Play a two-player Quoridor game on the same device. Share the screen and take turns.",
        "Play Quoridor with a friend", "Share one screen and take turns on the same board.",
        "Play with a friend", "local", panel, "Play Quoridor with a friend on one device: board game preview with two pawns and walls.",
        scripts=GAME_SCRIPTS,
        intro=mode_intro(
            "local-how-h", "Play Side by Side on One Screen",
            'Local play is the quickest way to play with a friend: sit together, share one screen and pass the device after each move. Type both names if you want the site to keep score of who wins between you. The score stays on this device. Two players is the classic game. For three or four players, a different board size or your own rules, try the <a href="/variants/">Quoridor variants</a>.',
        ),
    )


# ---------------------------------------------------------------- variants
# Each variant is a game of its own (rules in static/assets/js/engine.js and server/engine.py, VARIANTS). Add one here, give it a
# page like wallrush(), and list it in VARIANT_CARDS so the /variants/ page shows it.
def play_with_choice(live):
    """Radio buttons on a variant page: play on this device, or open a private room and invite friends (play.js reads them).
    Without a game server the second choice is shown but cannot be picked."""
    friends = (
        "Everyone plays on their own device. You get an invitation link and a short code to send."
        if live else "Coming soon. The game server that connects the devices is not available on this site yet."
    )
    return f"""
<fieldset class="fieldset"><legend>How do you want to play?</legend><div class="choice-group">
  <div class="choice"><input type="radio" name="playwith" id="pw-device" value="device" checked>
    <label class="choice-body" for="pw-device">
      <span class="check" aria-hidden="true">{icon('check')}</span>
      <span><span class="choice-title">On this device</span><span class="choice-state"> (selected)</span><br><span class="choice-desc">Share one screen and pass the device after each move.</span></span>
    </label></div>
  <div class="choice"><input type="radio" name="playwith" id="pw-friends" value="friends"{'' if live else ' disabled'}>
    <label class="choice-body" for="pw-friends">
      <span class="check" aria-hidden="true">{icon('check')}</span>
      <span><span class="choice-title">With invited friends</span><span class="choice-state"> (selected)</span><br><span class="choice-desc">{friends}</span></span>
    </label></div>
</div></fieldset>"""


def variant_form(names_html, live, settings_html=""):
    """The setup form of a variant: where it is played, the settings both ways share, then the names of the players
    on one device or your own name for a room of friends, and the button for whichever is chosen."""
    return (
        play_with_choice(live) + settings_html
        + f'<div data-device-only>{names_html}</div>'
        + '<div data-friends-only hidden>' + username_field("2 to 20 characters. Your friends will see this name.")
        + '<p class="small text-muted">You get an invitation link and a short pairing code to send. The game starts as soon as everyone has joined.</p></div>'
        + f'<button class="btn btn--primary btn--lg btn--block" type="submit" data-device-only>{icon("play")} Start game</button>'
        + f'<button class="btn btn--primary btn--lg btn--block" type="submit" data-friends-only hidden>{icon("plus")} Create room</button>'
        + (server_error() if live else "")
    )


WALLRUSH_PAWNS = [(8, 2, "p1"), (8, 6, "p2")]
WALLRUSH_GOALS = ((0, "#5EEAD4", 0.16),)  # one goal row, shared by both players
WALLRUSH_ALT = (
    "Wallrush board at the start of a game: a tall grid, 9 squares wide and 13 high. Two pawns stand side by side "
    "on the same row, with four rows behind them, and the top row is highlighted as the goal for both players."
)


def wallrush_art():
    return board_svg([], WALLRUSH_PAWNS, WALLRUSH_ALT, rows=13, cols=9, goals=WALLRUSH_GOALS)


# Pointrush: 11 x 11, up to four pawns (one per edge, drawn in the in-game player colours), one goal square in the middle.
POINTRUSH_PAWNS = [(10, 5, "#42D9F5"), (5, 0, "#FF9F43"), (0, 5, "#C084FC"), (5, 10, "#A3E635")]
POINTRUSH_GOAL = ((5, 5, "#5EEAD4"),)
POINTRUSH_ALT = (
    "Pointrush board at the start of a game: a square grid, 11 squares on each side. Four pawns, cyan, orange, violet and green, "
    "stand in the middle of the four edges, and the square in the center of the board is highlighted as the goal for every player."
)


def pointrush_art():
    return board_svg([], POINTRUSH_PAWNS, POINTRUSH_ALT, rows=11, cols=11, goals=(), goal_cells=POINTRUSH_GOAL)


# (path, name, icon, one-line summary, button label)
VARIANT_CARDS = [
    ("/variants/wallrush/", "Wallrush", "wall",
     "A race on a taller board. Both pawns start side by side on the same line and sprint for the same goal edge, "
     "placing walls to slow each other down.", "Play Wallrush"),
    ("/variants/pointrush/", "Pointrush", "target",
     "A race to the center for two, three or four players. Every pawn starts in the middle of an edge of a square board "
     "and sprints for the central square, placing walls to hold the others back.", "Play Pointrush"),
    ("/variants/custom/", "Custom Game", "sliders",
     "Classic Quoridor, set up your way. Pick the board size, how many walls each player gets, whether to borrow moves "
     "and how long a turn lasts, then play a friend on the same device" + (" or in a private room." if FEATURES["rooms"] else "."), "Set Up a Custom Game"),
]


def variant_faq(faq, heading_id, heading):
    """FAQ section (visible text) and its FAQPage JSON-LD for a variants page."""
    html = (
        f'<section class="section" aria-labelledby="{heading_id}"><div class="container prose">'
        f'<h2 id="{heading_id}">{heading}</h2><div class="faq">'
        + "".join(f'<details><summary>{q}</summary><div class="answer"><p>{a}</p></div></details>' for q, a in faq)
        + "</div></div></section>"
    )
    schema = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)}} for q, a in faq],
    }
    return html, schema


VARIANTS_FAQ = [
    ("What are Quoridor variants?",
     "Quoridor variants are different ways to play the Quoridor board game: a new board size, a different starting position, "
     "more players or custom rules. Wallrush, Pointrush and Custom Quoridor keep the pawns, walls and path rule of the classic game."),
    ("Can I play Quoridor with 3 or 4 players?",
     'Yes. <a href="/variants/pointrush/">Pointrush</a> is a Quoridor variant for two, three or four players'
     + (", on one device or online with invited friends," if FEATURES["rooms"] else " on one device,")
     + " where every pawn races to the square in the center of the board."),
    ("Can I change the board size or the number of walls in Quoridor?",
     'Yes. <a href="/variants/custom/">Custom Quoridor</a> lets you choose a board from 5 × 5 to 13 × 13, from 0 to 30 walls per player, '
     "borrowed moves and the time per move."),
    ("Are the Quoridor variants free to play?",
     "Yes. All variants are free in your browser, with no download and no account."),
] + ([
    ("Can I play a Quoridor variant online with friends?",
     'Yes. On the Wallrush, Pointrush or Custom Quoridor page choose "With invited friends", create a private room and send your friends the invitation link or pairing code. '
     "Everyone plays on their own device, and the game starts as soon as all the seats are taken."),
] if FEATURES["rooms"] else [])


def variants_hub():
    faq_html, faq_schema = variant_faq(VARIANTS_FAQ, "variants-faq-h", "Quoridor Variants: Frequently Asked Questions")
    cards ="".join(f"""
  <article class="card mode-card mode-card--variant">
    <span class="icon-badge">{icon(ic)}</span>
    <div class="mode-body">
      <h3>{name}</h3>
      <p>{text}</p>
    </div>
    <a class="btn btn--primary" href="{href}">{label} {icon('arrow')}</a>
  </article>""" for href, name, ic, text, label in VARIANT_CARDS)
    body = (
        page_head(
            "Quoridor Variants Online",
            "Play free Quoridor variants in your browser: Wallrush, Pointrush for 2 to 4 players, and Custom Quoridor with your own board size, walls and rules.",
            [("Variants", None)],
        )
        + f"""
<section class="section--tight" aria-labelledby="variants-h"><div class="container">
  <div class="section-head"><h2 id="variants-h">Choose a Variant</h2></div>
  <div class="grid grid--3 grid--modes">{cards}
  </div>
</div></section>
<section class="section" aria-labelledby="variants-why-h"><div class="container prose">
  <h2 id="variants-why-h">What Is a Quoridor Variant?</h2>
  <p>A variant keeps the heart of Quoridor: on your turn you either move your pawn or place a wall, and you may never close off every route to the goal. What changes is the setup, such as the size of the board, where the pawns start and where they are heading.</p>
  <p>If you are new to walls and pawns, start with the classic game. The variants are easier to enjoy once you know how a wall bends a route.</p>
  <div class="btn-row">
    <a class="btn btn--secondary" href="/how-to-play-quoridor/">Learn How to Play Quoridor</a>
    <a class="btn btn--secondary" href="/play/">Play Classic Quoridor</a>
  </div>
  <p class="mt-4">More variants will be added here over time.</p>
</div></section>
""" + faq_html
    )
    return Page(
        path="/variants/",
        title="Quoridor Variants Online – Wallrush, Pointrush & Custom",
        description="Play free Quoridor variants online: Wallrush, Pointrush for 2 to 4 players, and Custom Quoridor with your own board size, walls and rules. No download, no sign-up.",
        body=body, breadcrumbs=[("Variants", "/variants/")], nav_key="variants", schema=[faq_schema],
    )


WALLRUSH_FAQ = [
    ("What is Wallrush?",
     "Wallrush is a free two-player Quoridor variant played on a tall 9 by 13 board. Both pawns start side by side on the same line "
     "and race to the same goal row, placing walls to slow each other down."),
    ("How is Wallrush different from classic Quoridor?",
     'In classic Quoridor the pawns start on opposite edges and cross the board toward each other. In Wallrush they race in the same direction, '
     'and a pawn standing next to the other one may also use its moves (borrowed moves). The wall and path rules are those of the '
     '<a href="/quoridor-rules/">Quoridor rules</a>.'),
    ("How many walls does each player have in Wallrush?",
     "Each player has 10 walls. A wall is two squares long, and you may never block every route to the top row."),
    ("Can I play Wallrush online for free?",
     "Yes. Wallrush is free in your browser, with no download and no account. Two players take turns on one device"
     + (", or you can invite a friend to a private room and play from separate devices." if FEATURES["rooms"] else ".")),
]


def wallrush():
    faq_html, faq_schema = variant_faq(WALLRUSH_FAQ, "wr-faq-h", "Wallrush: Frequently Asked Questions")
    live = FEATURES["rooms"]
    panel = (
        '<div class="card"><h2 class="h-sm">Two players, one race</h2>'
        '<p class="text-muted">Both pawns race to the highlighted row at the top of the board. '
        + ("Take turns on one screen, or invite a friend to play from their own device.</p>" if live else "Share the screen and take turns.</p>")
        + '<ul class="text-muted"><li>Both pawns start on the same line, with four rows behind them.</li><li>Each player has 10 walls.</li><li>The first pawn to reach the top row wins.</li></ul></div>'
        '<div class="spacer"></div>'
        + variant_form(name_field(1) + name_field(2), live)
    )
    parent = [("Variants", "/variants/")]
    body = (
        '<div class="page-head"><div class="container">'
        + crumbs(parent + [("Wallrush", None)])
        + '<h1>Wallrush: A Quoridor Variant</h1><p class="lead">Play Wallrush free online, a two-player Quoridor race game where both pawns start on the same line of a 9 by 13 board and sprint for the same edge.</p></div></div>'
        + stage("local", panel, "", live=live, art=wallrush_art(), form_attrs='data-variant="wallrush" data-leave="variants" ')
        + f"""
<section class="section" aria-labelledby="wr-rules-h"><div class="container prose">
  <h2 id="wr-rules-h">How Wallrush Works</h2>
  <p>Wallrush is played on a tall board, 9 squares wide and 13 high. In classic Quoridor the pawns start on opposite edges and cross the board toward each other. Here both pawns start side by side on the same row, with four rows of space behind them, and both race to the same goal: the top row.</p>
  <ol>
    <li><strong>One action per turn.</strong> Move your pawn one square up, down, left or right, or place one wall. Player 1 moves first.</li>
    <li><strong>Walls.</strong> Each player has 10 walls. A wall is two squares long. It blocks movement across it for both pawns, and walls cannot overlap or cross each other.</li>
    <li><strong>Keep a path open.</strong> You may not place a wall that leaves either pawn with no route to the top row.</li>
    <li><strong>Meeting the other pawn.</strong> If the other pawn stands right in front of yours, jump over it. If a wall or the edge blocks the jump, step to either side of it instead, exactly as in Quoridor.</li>
    <li><strong>Borrowed moves.</strong> While your pawn stands right next to the other pawn, with no wall between them, you may also move to any square the other pawn could move to from where it stands, jumps and side-steps included.</li>
    <li><strong>Winning.</strong> The first pawn to reach any square of the top row wins.</li>
  </ol>
  <p>Each turn has a 32 second clock, and each player has 5 minutes for the whole game. If a turn runs out of time, the game moves your pawn one step along its shortest route. If your 5 minutes run out, you lose.</p>
  <h2 id="wr-tips-h">Things to Think About</h2>
  <p>Because both pawns share one goal, you are racing in the same lane as your opponent. A wall that slows them down can also slow you if your routes overlap, so look at both routes before you place one. The room behind the starting line is yours to use: stepping sideways to a clear column can beat walking straight into a wall.</p>
  <p>For the full wall, jump and side-step rules, read the Quoridor rules. Wallrush uses them, plus the borrowed moves above.</p>
  <div class="btn-row">
    <a class="btn btn--secondary" href="/quoridor-rules/">Read the Quoridor Rules</a>
    <a class="btn btn--secondary" href="/quoridor-strategy/">Quoridor Strategy</a>
    <a class="btn btn--secondary" href="/variants/">All Variants</a>
  </div>
</div></section>
""" + faq_html
    )
    return Page(
        path="/variants/wallrush/",
        title="Wallrush – Free Online Quoridor Variant Race Game",
        description="Play Wallrush online free: a two-player Quoridor variant on a tall 9 by 13 board where both pawns start on one line and race to the same edge, with 10 walls each.",
        body=body, breadcrumbs=parent + [("Wallrush", "/variants/wallrush/")], nav_key="variants", schema=[faq_schema],
        scripts=GAME_SCRIPTS + PLAY_SCRIPTS + watch_scripts("/variants/wallrush/") + ["/assets/js/play.js"],
    )


def players_choice():
    """Radio buttons for the number of players (read by play.js, which shows one name field per player)."""
    items = "".join(f"""
<div class="choice"><input type="radio" name="players" id="players-{n}" value="{n}"{' checked' if n == 2 else ''}>
  <label class="choice-body" for="players-{n}">
    <span class="check" aria-hidden="true">{icon('check')}</span>
    <span class="choice-title">{n} players</span>
  </label></div>""" for n in (2, 3, 4))
    return f'<fieldset class="fieldset"><legend>Number of players</legend><div class="choice-group choice-group--row">{items}</div></fieldset>'


POINTRUSH_FAQ = [
    ("What is Pointrush?",
     "Pointrush is a free Quoridor variant for two, three or four players on an 11 by 11 board. Every pawn starts in the middle of an edge "
     "and races to the same goal: the square in the center."),
    ("Can you play Quoridor with 4 players?",
     ("Yes. In Pointrush four players take turns, each starting from a different edge. They can share one device, or each play on their own device "
      "after joining a private room with an invitation link."
      if FEATURES["rooms"] else "Yes. In Pointrush four players share one device and take turns, each starting from a different edge.")
     + " With three players each has 8 walls, and with four players each has 6."),
    ("How do you win at Pointrush?",
     "The first pawn to step onto the center square wins. You can place walls to hold the other pawns back, but you may never leave a pawn "
     "with no route to the center."),
    ("Is Pointrush free to play online?",
     "Yes. Pointrush is free in your browser, with no download and no account."),
]


def pointrush():
    faq_html, faq_schema = variant_faq(POINTRUSH_FAQ, "pr-faq-h", "Pointrush: Frequently Asked Questions")
    live = FEATURES["rooms"]
    names = "".join(f'<div data-player-field="{n}"{" hidden" if n > 2 else ""}>{name_field(n)}</div>' for n in (1, 2, 3, 4))
    panel = (
        '<div class="card"><h2 class="h-sm">Two to four players, one center square</h2>'
        '<p class="text-muted">Every pawn races to the highlighted square in the center of the board. '
        + ("Share one screen, or invite friends to join from their own devices.</p>" if live else "Share the screen and take turns.</p>")
        + '<ul class="text-muted"><li>Pawns start in the middle of the edges, five squares from the center.</li><li>Each player has 12, 8 or 6 walls, with two, three or four players.</li><li>The first pawn to reach the center square wins.</li></ul></div>'
        '<div class="spacer"></div>'
        + variant_form(names, live, settings_html=players_choice())
    )
    parent = [("Variants", "/variants/")]
    body = (
        '<div class="page-head"><div class="container">'
        + crumbs(parent + [("Pointrush", None)])
        + '<h1>Pointrush: A Quoridor Variant for 2 to 4 Players</h1><p class="lead">Play Pointrush free online, a multiplayer Quoridor variant where two, three or four pawns race for the same square in the center of an 11 by 11 board.</p></div></div>'
        + stage("local", panel, "", live=live, art=pointrush_art(), form_attrs='data-variant="pointrush" data-leave="variants" ')
        + f"""
<section class="section" aria-labelledby="pr-rules-h"><div class="container prose">
  <h2 id="pr-rules-h">How Pointrush Works</h2>
  <p>Pointrush is played on a square board, 11 squares on each side, with one special square in the middle. In classic Quoridor each pawn crosses the board to the opposite edge. Here every pawn starts in the middle of an edge, five squares from the center, and all of them race to the same goal: the center square. Two, three or four players can take part.</p>
  <ol>
    <li><strong>One action per turn.</strong> Move your pawn one square up, down, left or right, or place one wall. Player 1 moves first, then the turns pass in order from Player 2 onward.</li>
    <li><strong>Starting edges.</strong> Player 1 starts at the bottom edge. In a two-player game Player 2 starts at the top edge. With three or four players, Player 2 starts at the left edge, Player 3 at the top edge and Player 4 at the right edge.</li>
    <li><strong>Walls.</strong> Each player has 12 walls in a two-player game, 8 with three players and 6 with four players. A wall is two squares long. It blocks movement across it for every pawn, and walls cannot overlap or cross each other.</li>
    <li><strong>Keep a path open.</strong> You may not place a wall that leaves any pawn with no route to the center square.</li>
    <li><strong>Meeting other pawns.</strong> If another pawn stands right in front of yours, jump over it. If a wall, the edge or a third pawn blocks the jump, step to either side of it instead, as in Quoridor. You can never land on a square that is taken.</li>
    <li><strong>Winning.</strong> The first pawn to step onto the center square wins.</li>
  </ol>
  <p>Each turn has a 32 second clock, and each player has 5 minutes for the whole game. If a turn runs out of time, the game moves your pawn one step along its shortest route. If your 5 minutes run out, you lose.</p>
  <h2 id="pr-tips-h">Things to Think About</h2>
  <p>Every route ends on the same square, so the lanes cross in the middle and the pawns crowd the last few squares. A wall near the center slows everyone, not only the player you aimed at, and with three or four players a wall that holds back one rival can help another. Watch who is closest, and save your walls for the moment the leader is about to arrive.</p>
  <p>For the full wall, jump and side-step rules, read the Quoridor rules. Pointrush uses them, with the center square as the only goal.</p>
""" + (
    """  <h2 id="pr-online-h">Playing With Friends Online</h2>
  <p>Choose "With invited friends", pick the number of players and create a room. You get an invitation link and a short pairing code. Each friend opens the link, or types the code on the <a href="/play/join-room/">join a room</a> page, and picks a name. The game starts as soon as every seat is taken, and the players move in turn, each on their own device. If a player leaves a game of three or four, the game ends for everyone and nobody wins.</p>
  """ if FEATURES["rooms"] else "") + """<div class="btn-row">
    <a class="btn btn--secondary" href="/quoridor-rules/">Read the Quoridor Rules</a>
    <a class="btn btn--secondary" href="/quoridor-strategy/">Quoridor Strategy</a>
    <a class="btn btn--secondary" href="/variants/">All Variants</a>
  </div>
</div></section>
""" + faq_html
    )
    return Page(
        path="/variants/pointrush/",
        title="Pointrush – 4-Player Quoridor Variant, Play Free Online",
        description="Play Pointrush online free: a multiplayer Quoridor variant for 2 to 4 players on an 11 by 11 board where every pawn races to the center square. No download needed.",
        body=body, breadcrumbs=parent + [("Pointrush", "/variants/pointrush/")], nav_key="variants", schema=[faq_schema],
        scripts=GAME_SCRIPTS + PLAY_SCRIPTS + watch_scripts("/variants/pointrush/") + ["/assets/js/play.js"],
    )


# Custom Game: the classic layout with settings the players choose. The limits mirror CUSTOM_LIMITS in engine.js.
CUSTOM_SIZES = (5, 7, 9, 11, 13)
CUSTOM_CLOCKS = ((0, "No time limit"), (15, "15 seconds per move"), (32, "32 seconds per move"), (60, "1 minute per move"), (120, "2 minutes per move"))


def custom_settings():
    sizes = "".join(f'<option value="{n}"{" selected" if n == 9 else ""}>{n} × {n} squares{" (classic)" if n == 9 else ""}</option>' for n in CUSTOM_SIZES)
    clocks = "".join(f'<option value="{s}">{label}</option>' for s, label in CUSTOM_CLOCKS)
    return f"""
<div class="field">
  <label for="size">Board size</label>
  <select class="input" id="size" name="size" aria-describedby="size-hint">{sizes}</select>
  <span class="hint" id="size-hint">Pawns start in the middle of opposite edges. A bigger board makes a longer race.</span>
</div>
<div class="field">
  <label for="walls">Walls per player</label>
  <input class="input" id="walls" name="walls" type="number" inputmode="numeric" min="0" max="30" step="1" value="10" required aria-describedby="walls-hint walls-error">
  <span class="hint" id="walls-hint">From 0 to 30. Classic Quoridor gives each player 10.</span>
  <div class="field-error" id="walls-error" role="alert" hidden></div>
</div>
<div class="field">
  <label for="clock">Time per move</label>
  <select class="input" id="clock" name="clock" aria-describedby="clock-hint">{clocks}</select>
  <span class="hint" id="clock-hint">When the time runs out, the game moves the pawn one step along its shortest route. With a clock on, each player also has 5 minutes in total.</span>
</div>
<div class="fieldset">
  <div class="choice"><input type="checkbox" id="borrow" name="borrow">
    <label class="choice-body" for="borrow">
      <span class="check" aria-hidden="true">{icon('check')}</span>
      <span><span class="choice-title">Borrowed moves</span><span class="choice-state"> (on)</span><br><span class="choice-desc">Next to the other pawn, you may also move wherever it could move.</span></span>
    </label></div>
</div>"""


CUSTOM_FAQ = [
    ("Can I change the board size in Quoridor?",
     "Yes. In a Custom Quoridor game you can play on a 5 × 5, 7 × 7, 9 × 9, 11 × 11 or 13 × 13 board. The classic board is 9 × 9."),
    ("How many walls can each player have in a custom game?",
     "From 0 to 30 walls per player, the same for both players. Classic Quoridor gives each player 10 walls."),
    ("Can I play Quoridor with a time limit?",
     "Yes. Choose no clock, or 15 seconds, 32 seconds, 1 minute or 2 minutes per move. When the clock runs out, the game moves your pawn one step along its shortest route."),
    ("Can I play a custom Quoridor game with a friend?",
     ('Yes. Play on the same device and take turns, or choose "With invited friends", create a private room and send your friend the invitation link or pairing code. '
      "The room keeps the board size, walls, borrowed moves and clock you chose."
      if FEATURES["rooms"] else "Yes, on the same device: share the screen and take turns.")),
]


def custom_game():
    faq_html, faq_schema = variant_faq(CUSTOM_FAQ, "cg-faq-h", "Custom Quoridor: Frequently Asked Questions")
    live = FEATURES["rooms"]
    panel = (
        '<div class="card"><h2 class="h-sm">Set up your game</h2>'
        '<p class="text-muted">Choose the rules, then '
        + ("play on one device or invite a friend." if live else "share the screen with a friend and take turns.")
        + ' The defaults are classic Quoridor.</p></div>'
        '<div class="spacer"></div>'
        + variant_form(name_field(1) + name_field(2), live, settings_html=custom_settings())
    )
    parent = [("Variants", "/variants/")]
    body = (
        '<div class="page-head"><div class="container">'
        + crumbs(parent + [("Custom Game", None)])
        + '<h1>Custom Quoridor Game</h1><p class="lead">Play Quoridor with your own rules: choose the board size, the number of walls, borrowed moves and the time per move.</p></div></div>'
        + stage("local", panel, "Custom Game: board game preview with two pawns, shown here at the classic 9 by 9 size.", (), [(8, 4, "p1"), (0, 4, "p2")],
                live=live, form_attrs='data-variant="custom" data-leave="variants" ')
        + """
<section class="section" aria-labelledby="cg-rules-h"><div class="container prose">
  <h2 id="cg-rules-h">How a Custom Game Works</h2>
  <p>A custom game is played like classic Quoridor: two pawns start in the middle of opposite edges, and the first to reach the far edge wins. Before you start, you and your friend decide how the game is set up. Player 1 moves first.</p>
  <ol>
    <li><strong>Board size.</strong> Play on a 5 × 5, 7 × 7, 9 × 9, 11 × 11 or 13 × 13 board. A small board is a quick skirmish. A large one leaves room for long detours.</li>
    <li><strong>Walls per player.</strong> Give each player anywhere from 0 to 30 walls. With none, the game is a pure race. With many, it turns into a maze fight. A wall is two squares long, and walls cannot overlap or cross each other.</li>
    <li><strong>Keep a path open.</strong> Whatever the setup, you may not place a wall that leaves either pawn with no route to its goal.</li>
    <li><strong>Borrowed moves.</strong> If you turn this on, a pawn standing right next to the other pawn, with no wall between them, may also move to any square the other pawn could move to from where it stands.</li>
    <li><strong>Time per move.</strong> Play with no clock, or choose 15 seconds, 32 seconds, 1 minute or 2 minutes. When the clock runs out, the game moves your pawn one step along its shortest route. With a clock on, each player also has 5 minutes for the whole game.</li>
  </ol>
  <h2 id="cg-tips-h">Ideas to Try</h2>
  <p>Try a 5 × 5 board with 3 walls each for a game that is over in minutes, or a 13 × 13 board with 20 walls each for a long battle of detours. Both players always get the same number of walls. When you play again, your settings stay in place.</p>
  <p>""" + ("You can play it on one device, or invite a friend to a private room that keeps your settings: your friend sees them before joining." if FEATURES["rooms"] else "This game is played on one device.") + """</p>
  <div class="btn-row">
    <a class="btn btn--secondary" href="/quoridor-rules/">Read the Quoridor Rules</a>
    <a class="btn btn--secondary" href="/variants/">All Variants</a>
  </div>
</div></section>
""" + faq_html
    )
    return Page(
        path="/variants/custom/",
        title="Custom Quoridor – Choose Board Size, Walls & Rules Online",
        description=("Play custom Quoridor online free on one device or in a private room. Choose the board size from 5×5 to 13×13, the walls, borrowed moves and the time per move."
                     if FEATURES["rooms"] else
                     "Play custom Quoridor online free with a friend on one device. Choose the board size from 5×5 to 13×13, the number of walls, borrowed moves and the time per move."),
        body=body, breadcrumbs=parent + [("Custom Game", "/variants/custom/")], nav_key="variants", schema=[faq_schema],
        scripts=GAME_SCRIPTS + PLAY_SCRIPTS + watch_scripts("/variants/custom/") + ["/assets/js/play.js"],
    )


def create_room():
    live = FEATURES["rooms"]
    panel = (
        username_field("2 to 20 characters. Your friend will see this name.")
        + f'<button class="btn btn--primary btn--lg btn--block" type="submit">{icon("plus")} Create room</button>'
        + (server_error() if live else
           unavailable("Private rooms aren't live yet", "There is no room server on this site yet, so no room was created and no link or code was generated."))
        + """<h2 class="h-sm mt-6">What happens next</h2>
<ol class="text-muted"><li>You get an invitation link and a short pairing code.</li><li>Copy either one and send it to your friend.</li><li>The match starts as soon as your friend joins.</li></ol>"""
        + ('' if live else '<p class="small"><a href="/room/EXAMPLE-ROOM-ID/?preview=waiting">Preview the waiting-room screen</a> (sample data)</p>')
    )
    return mode_page(
        "/play/create-room/", "Play Quoridor Online With Friends – Private Room",
        "Play Quoridor online with friends. Create a private room, share the invitation link or pairing code, and the game starts as soon as your friend joins.",
        "Create a private room", "Make a room, then share the invitation link or pairing code with your friend.",
        "Create a room", "create-room", panel, "Create a private Quoridor room: board game preview with two pawns and walls.", live=live,
        indexable=live,  # the only room page worth finding in search; join-room and the rooms themselves stay noindex
        intro=mode_intro(
            "room-how-h", "How to Play Quoridor Online With a Friend",
            "A private room is for playing one specific person, wherever they are. Choose a username and create a room: you get an invitation link and a short pairing code. Send either one to your friend and the game starts as soon as they join. Neither of you needs an account.",
            'Rooms made here use the classic rules on a 9×9 board, with 10 walls each. Your friend can open the link, or type the code on the <a href="/play/join-room/">join a room</a> page. Want other rules, a bigger board or up to four players? Open one of the <a href="/variants/">Quoridor variants</a> and choose to invite friends: the invitation link and code work the same way. Want a quick game against a stranger instead? Try <a href="/play/online/">online matchmaking</a>.',
        ) if live else "",
    )


def join_room():
    live = FEATURES["rooms"]
    panel = (
        username_field("2 to 20 characters. Your opponent will see this name.")
        + """<div class="field">
  <label for="code">Pairing code</label>
  <input class="input input--code" id="code" name="code" type="text" inputmode="text" autocomplete="off" autocapitalize="characters" maxlength="6" required aria-describedby="code-hint code-error" spellcheck="false">
  <span class="hint" id="code-hint">6 characters. Got an invitation link instead? Just open it.</span>
  <div class="field-error" id="code-error" role="alert" hidden></div>
</div>"""
        + f'<button class="btn btn--primary btn--lg btn--block" type="submit">{icon("login")} Join room</button>'
        + (server_error() if live else
           unavailable("Private rooms aren't live yet", "There is no room server on this site yet, so the code can't be checked."))
        + ('' if live else '<p class="small mt-4">Preview other screens (sample data): <a href="/room/EXAMPLE-ROOM-ID/?preview=invalid">invalid code</a>, <a href="/room/EXAMPLE-ROOM-ID/?preview=full">room full</a>, <a href="/room/EXAMPLE-ROOM-ID/?preview=expired">expired invitation</a>.</p>')
    )
    return mode_page(
        "/play/join-room/", "Join a Private Quoridor Room",
        "Join a private Quoridor room with a pairing code or an invitation link.",
        "Join a private room", "Enter the pairing code your friend sent you, or open their invitation link.",
        "Join a room", "join-room", panel, "Join a private Quoridor room: board game preview with two pawns and walls.", indexable=False, live=live,
    )


def room():
    live = FEATURES["rooms"]

    def state(name, inner):
        return f'<section data-state="{name}" hidden>{inner}</section>'

    def msg(name, h, text, status_icon="alert", cls="notice notice--error"):
        return state(name, f"""
<div class="{cls}">{icon(status_icon)}<div><h1 tabindex="-1">{h}</h1><p>{text}</p></div></div>
<div class="btn-row">
  <a class="btn btn--primary" href="/play/create-room/">Create a Room</a>
  <a class="btn btn--secondary" href="/play/join-room/">Join with a code</a>
  <a class="btn btn--secondary" href="/play/">Back to Play</a>
</div>""")

    # data-pair-only / data-group-only: the parts of this screen for a room of two seats and for one of three or four (room.js shows one set).
    # data-host-only / data-guest-only: the host cancels the room, a guest who has joined only steps out.
    waiting = state("waiting", f"""
<h1 tabindex="-1" data-pair-only>Waiting for your opponent</h1>
<h1 tabindex="-1" data-group-only hidden>Waiting for your friends</h1>
<p class="small text-muted" id="waiting-game" data-i18n-skip hidden></p>
<div class="status-line" role="status" data-pair-only><span class="status-dot status-dot--wait" aria-hidden="true"></span><span>Waiting for a second player to join. Connected as host.</span></div>
<div class="status-line" role="status" data-group-only hidden><span class="status-dot status-dot--wait" aria-hidden="true"></span><span id="lobby-count" data-i18n-skip></span></div>
<ul class="lobby" id="lobby" aria-label="Players in this room" data-group-only hidden></ul>
<h2 class="h-sm">Invitation link</h2>
<div class="code-box"><div class="value" id="invite-link"></div><button class="btn btn--secondary" type="button" data-copy="invite-link">{icon('copy')} Copy link</button></div>
<div id="code-section">
<h2 class="h-sm">Pairing code</h2>
<div class="code-box"><div class="value value--big" id="invite-code"></div><button class="btn btn--secondary" type="button" data-copy="invite-code">{icon('copy')} Copy code</button></div>
</div>
<p class="small text-muted" id="copy-status" role="status" aria-live="polite"></p>
<p class="small text-muted" data-group-only hidden>Send the link or the code to your friends. The game starts as soon as every seat is taken.</p>
<div class="btn-row room-actions"><button class="btn btn--secondary" type="button" data-leave data-host-only>{icon("x")} Cancel room</button><button class="btn btn--secondary" type="button" data-leave data-guest-only hidden>{icon("logout")} Leave room</button></div>""")

    join = state("join", f"""
<h1 tabindex="-1">Join this room</h1>
<p class="text-muted"><strong id="host-name">Your friend</strong> invited you to play Quoridor. Choose a username to join.</p>
<p class="small text-muted" id="join-game" data-i18n-skip hidden></p>
<form novalidate>
{username_field('2 to 20 characters. The other players will see this name.')}
<button class="btn btn--primary btn--lg btn--block" type="submit">{icon('login')} Join room</button>
</form>""")

    starting = state("starting", """
<h1 tabindex="-1">Both players are in</h1>
<div class="status-line" role="status"><span class="status-dot status-dot--ok" aria-hidden="true"></span><span id="starting-text">Alex and Sam are connected. The game is about to start.</span></div>
<p class="text-muted">The board appears in a moment.</p>""")

    reconnecting = state("reconnecting", f"""
<h1 tabindex="-1">Reconnecting&hellip;</h1>
<div class="status-line" role="status"><span class="status-dot status-dot--wait" aria-hidden="true"></span><span>Connection lost. Trying to rejoin your seat automatically.</span></div>
<p class="text-muted">Your opponent can see that you're reconnecting. If you can't return within a minute, the game ends as a forfeit.</p>
<div class="btn-row"><button class="btn btn--secondary" type="button" data-leave>{icon("logout")} Leave room</button></div>""")

    left = state("left", """
<h1 tabindex="-1">You left the room</h1>
<p class="text-muted">Your seat has been released.</p>
<div class="btn-row"><a class="btn btn--primary" href="/play/">Back to Play</a><a class="btn btn--secondary" href="/">Home</a></div>""")

    game = state("game", f"""
<div class="notice notice--error" data-connection hidden role="status">{icon('alert')}<div><p>Connection lost. Trying to reconnect&hellip;</p></div></div>
<div data-game-host></div>""")

    unavailable_text = (
        "This room may have been cancelled, finished or expired, or the link may be wrong. Nothing about this link was stored or checked."
        if live else
        "Private rooms aren't live yet, so this link can't be opened. Nothing about this link was stored or checked."
    )
    inner = (
        waiting + join + starting + reconnecting + game
        + msg("invalid", "That code doesn't match a room", "Check the code and try again, or ask your friend to send the invitation link again.")
        + msg("full", "This room is full", "Every seat in this room is already taken. You can create your own room instead.")
        + msg("expired", "This invitation has expired", "Invitations only last for a limited time. Ask your friend for a new one, or create your own room.")
        + msg("unavailable", "This room isn't available", unavailable_text, "info", "notice")
        + left
    )
    body = f"""
<div class="container pad-room" data-room-shell{' data-live' if live else ''}>
  <div class="stage-panel narrow">
    {inner}
    <p class="notice preview-note small" data-preview-note hidden role="note">{icon('info')}<span>Design preview with sample data. No room, link or opponent is real.</span></p>
  </div>
</div>"""
    return Page(
        path="/room/_/", title="Private room | Quoridor Online",
        description="Private Quoridor room.",
        body=body, indexable=False, robots="noindex, nofollow, noarchive",
        canonical=False, scripts=GAME_SCRIPTS + PLAY_SCRIPTS + watch_scripts("/room/") + ["/assets/js/room.js"],
        out_file="room/index.html", generic_social=True, nav_key="play",
    )


# ---------------------------------------------------------------- informational pages
SETUP_BOARD = board_svg([], [(8, 4, "p1"), (0, 4, "p2")],
    "Quoridor starting position. A Quoridor board at the start of a game: a cyan pawn in the middle of the bottom edge and a white ring pawn in the middle of the top edge, with no walls placed.")
MID_BOARD = board_svg([("h", 3, 3), ("v", 4, 4), ("h", 5, 1), ("h", 2, 5)], [(5, 4, "p1"), (3, 4, "p2")],
    "Quoridor board game position. A Quoridor game in progress: a cyan pawn and a white ring pawn face each other, with several indigo walls placed between squares.")
MOVE_BOARD = board_svg([("h", 4, 4)], [(5, 4, "p1"), (1, 4, "p2")],
    "Quoridor rules diagram. A cyan pawn with dashed squares marked with arrows to the left, right and below it. The square above is not marked because an indigo wall blocks it.",
    marks=[(5, 3, "←"), (5, 5, "→"), (6, 4, "↓")])
JUMP_BOARD = board_svg([], [(5, 4, "p1"), (4, 4, "p2")],
    "Quoridor rules diagram. A cyan pawn directly below a white ring pawn. The square directly above the white pawn is dashed and marked A: the cyan pawn can jump there.",
    marks=[(3, 4, "A")])
SIDESTEP_BOARD = board_svg([("h", 3, 4)], [(5, 4, "p1"), (4, 4, "p2")],
    "Quoridor rules diagram. A cyan pawn directly below a white ring pawn with an indigo wall behind the white pawn. The squares to the left and right of the white pawn are dashed and marked A and B: the cyan pawn can move to either.",
    marks=[(4, 3, "A"), (4, 5, "B")])
WALL_BOARD = board_svg([("h", 2, 3), ("h", 2, 5)], [(6, 4, "p1"), (2, 4, "p2")],
    "Quoridor rules diagram. Two indigo walls placed side by side in front of a white ring pawn. Together they cover four squares of the row below it, so the pawn must walk sideways around them.")
SEALED_BOARD = board_svg([("h", 0, 0)], [(8, 4, "p1"), (0, 0, "p2")],
    "Quoridor rules diagram. A white ring pawn in the top-left corner under an indigo wall. A dashed red wall marked with a cross would close the only way out of that corner, so it is not allowed.",
    bad_walls=[("v", 0, 1)])
GOAL_BOARD = board_svg([], [(1, 4, "p1"), (7, 4, "p2")],
    "Quoridor rules diagram. A cyan pawn one step from the top edge. Every square of the top row is dashed and ticked: reaching any of them wins.",
    marks=[(0, c, "✓") for c in range(9)])


OVERLAP_BOARD = board_svg([("h", 4, 3)], [(7, 4, "p1"), (1, 4, "p2")],
    "Quoridor rules diagram. An indigo wall lies below the fifth row across the fourth and fifth columns. A dashed red wall marked with a cross would share the fifth column with it, so it is not allowed.",
    bad_walls=[("h", 4, 4)])
CROSS_BOARD = board_svg([("h", 4, 3)], [(7, 4, "p1"), (1, 4, "p2")],
    "Quoridor rules diagram. An indigo wall lies across the board. A dashed red vertical wall marked with a cross would cross it at its middle point, so it is not allowed.",
    bad_walls=[("v", 4, 3)])
WALL_JUMP_BOARD = board_svg([("h", 4, 3)], [(5, 4, "p1"), (4, 4, "p2")],
    "Quoridor rules diagram. A cyan pawn directly below a white ring pawn with an indigo wall between them. The three dashed squares left, right and below the cyan pawn are its only moves: it cannot jump the white pawn through the wall.",
    marks=[(5, 3, "←"), (5, 5, "→"), (6, 4, "↓")])


def how_to_play_faq():
    """[(question, answer_html)]: online-play questions the sections above do not already answer in full."""
    online = FEATURES["online"]
    faq = [
        ("Who goes first in an online game?",
         "The server picks at random who moves first. If you play a rematch, you and your opponent swap places, so the other player goes first."
         if online else
         "In same-device and computer games Player 1 (the filled cyan pawn) always moves first. The screen shows whose turn it is."),
        ("Can I undo a move?",
         "Not in an online game: a move or wall is final as soon as you make it. Undo is only available when you practice against the computer."
         if online else
         "Undo is available when you practice against the computer. Walls are permanent once placed."),
        ("Can I move or remove a wall after placing it?",
         "No. Walls stay on the board for the rest of the game, so check the preview before you confirm."),
        ("What happens when I run out of walls?",
         "You can only move your pawn from then on. Your opponent can keep using any walls they have left, so don't spend all of yours too early."),
        ("Can a pawn jump over a wall?",
         "No. A pawn only jumps over the other pawn. A wall always stops movement across it."),
    ]
    if online:
        faq += [
            ("What if my connection drops during a game?",
             "The game shows your opponent that you are reconnecting, and your browser tries to rejoin your seat automatically. If you can't get back within a minute, the game counts as a forfeit."),
            ("Can I play on my phone?",
             "Yes. Online games run in a mobile browser with nothing to install. Drag a wall from the tray onto the board to place it, or tap a wall in the tray, tap a groove and press Place selected wall to confirm."),
            ("Can I play someone who uses a different language?",
             "Yes. Everyone picks their own language with the translate button in the page header (English, Spanish, French, German, Arabic, Russian or Chinese). It only changes how the page looks to you. The game, the matchmaking and the rooms are the same for everyone, and there is no chat, so you and your opponent can each play in your own language. Names can be written in any alphabet."),
            ("Can I play the same opponent again?",
             "Yes. When a game ends, press Request rematch. The game restarts once your opponent accepts, with the starting seats swapped."),
        ]
    return faq


def how_to_play():
    online, rooms = FEATURES["online"], FEATURES["rooms"]
    if online:
        play_links = ['<a class="btn btn--primary btn--lg" href="/play/online/">Find an opponent ' + icon("arrow") + "</a>"]
        if rooms:
            play_links.append('<a class="btn btn--secondary btn--lg" href="/play/create-room/">Invite a friend</a>')
        if FEATURES["computer"]:
            play_links.append('<a class="btn btn--secondary btn--lg" href="/play/computer/">Practice vs the computer</a>')
    else:
        play_links = ['<a class="btn btn--primary btn--lg" href="/play/">Play Quoridor Now ' + icon("arrow") + "</a>"]
    faq = how_to_play_faq()
    faq_html = '<div class="faq">' + "".join(
        f'<details><summary>{q}</summary><div class="answer"><p>{a}</p></div></details>' for q, a in faq) + "</div>"
    faq_schema = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)}} for q, a in faq],
    }
    not_live = "" if online else '<div class="callout"><p><strong>Online matches are coming soon.</strong> The rules below are the same ones used everywhere on this site, so you can already practice <a href="/play/">against the computer or with a friend on one device</a>.</p></div>'

    if online:
        start_steps = f"""
<ol class="steps">
<li><strong>Open Play Online and choose a username.</strong>Use 2 to 20 characters. It is only a display name your opponent will see. You don't need an account.</li>
<li><strong>Press Find an opponent.</strong>You are paired with the next player who is searching, and the game opens on its own. You can cancel the search at any time.</li>
<li><strong>Check your side.</strong>On your screen your own pawn always starts in the middle of the bottom row, marked <em>(you)</em>, and your goal is the top row. Each player has 10 walls, shown as <em>Walls: 10</em>.</li>
<li><strong>Wait for the first turn.</strong>The server chooses at random who moves first, and the turn bar tells you whose go it is.</li>
</ol>"""
        if rooms:
            start_steps += """
<h3>Playing a specific friend</h3>
<p>Choose <a href="/play/create-room/">Create a Room</a>, then send your friend the invitation link or the short pairing code. They open the link, or enter the code on <a href="/play/join-room/">Join a Room</a>, pick a username, and the game starts as soon as they arrive. An unjoined room expires after 30 minutes."""
            start_steps += "</p>"
    else:
        start_steps = """
<ol class="steps">
<li><strong>Open a game.</strong>Choose a mode on the <a href="/play/">Play</a> page. No account is needed.</li>
<li><strong>Check your side.</strong>Your pawn starts in the middle of the bottom row and your goal is the top row. Each player has 10 walls.</li>
<li><strong>Take turns.</strong>Player 1 moves first, and the turn bar shows whose go it is.</li>
</ol>"""

    if online:
        move_steps = """
<ol class="steps">
<li><strong>Wait for <em>Your turn</em>.</strong>Moves are only accepted from you when the turn bar says it's your go.</li>
<li><strong>Look for the highlighted squares.</strong>The squares you can legally reach are highlighted. Walls and the board edge are already taken into account.</li>
<li><strong>Click or tap a highlighted square.</strong>Your pawn moves one square and the turn passes to your opponent. With a keyboard, use the arrow keys and Enter.</li>
</ol>"""
        timer_note = '<div class="callout"><p><strong>Watch the clock.</strong> Each turn has a 32-second timer, and each player has 5 minutes for the whole game; both clocks are shown above the board. If a turn runs out, the server plays a pawn step along your shortest route for you, so you lose the chance to place a wall that turn. If your 5 minutes run out, you lose.</p></div>'
    else:
        move_steps = """
<ol class="steps">
<li><strong>Wait for your turn.</strong>The turn bar shows whose go it is.</li>
<li><strong>Look for the highlighted squares.</strong>The squares you can legally reach are highlighted.</li>
<li><strong>Click or tap a highlighted square.</strong>Your pawn moves one square and the turn passes.</li>
</ol>"""
        timer_note = ""

    sections = [
        ("what-is-quoridor", "What Is Online Quoridor?", f"""
<p>Quoridor is a strategy game for two players on a 9×9 board. Online, you play it in your browser against another person, with no downloads and no account. There are no dice, cards or hidden information, so you win by thinking ahead.</p>
<div class="callout"><p><strong>The objective:</strong> be the first player to move your pawn to <em>any square</em> on the opposite edge of the board.</p></div>
<p>On your turn you can walk toward your goal, or place a wall to make your opponent's walk longer. Choosing between the two, turn after turn, is the whole game. The server checks every move, so nobody can cheat or play an illegal one. This page teaches the basics step by step; the <a href="/quoridor-rules/">Quoridor rules</a> page is the full reference.</p>
{not_live}"""),
        ("board-and-pieces", "The Quoridor Board and Pieces", f"""
<p>Everything you need is on the game screen.</p>
<ul>
<li><strong>The board.</strong> A grid of 9×9 squares (81 in total) with thin grooves between them.</li>
<li><strong>Pawns.</strong> Each player has one pawn. Player 1 is the filled cyan circle and Player 2 is the white ring, so they differ by shape as well as color. Your own name is marked <em>(you)</em>.</li>
<li><strong>Walls.</strong> Each wall is two squares long, sits in the grooves between squares, and blocks movement across it. The player cards show how many walls each of you has left.</li>
</ul>
{figure(MID_BOARD, 'A game in progress. The cyan and white pieces are the pawns; the indigo bars are walls sitting in the grooves between squares.')}"""),
        ("set-up", "How to Set Up an Online Game" if online else "How to Set Up a Game", f"""{start_steps}
{figure(SETUP_BOARD, 'The starting position as you see it. Your goal is any square on the edge where your opponent starts: here, cyan aims for the top row and white for the bottom row.')}"""),
        ("move-your-pawn", "How to Move Your Pawn", f"""
<p>On your turn you do <strong>one</strong> thing: move your pawn <em>or</em> place a wall. This section covers moving.</p>
<h3>Step one square</h3>
{move_steps}
{timer_note}
<p>A pawn moves up, down, left or right, one square at a time. It can't move diagonally (apart from the special case below), through a wall, or off the board.</p>
{figure(MOVE_BOARD, 'Squares the cyan pawn can step to. The wall above it blocks the move up.')}
<h3>Jump over the other pawn</h3>
<p>If the opponent's pawn is on the square right next to yours, you can't share the square, so you <strong>jump straight over it</strong> and land on the square directly behind. The game highlights that square for you, and the jump counts as your whole move.</p>
{figure(JUMP_BOARD, 'The cyan pawn jumps over the white pawn to square A.')}
<h3>Step diagonally when a jump is blocked</h3>
<p>If a wall or the edge of the board sits right behind the other pawn, you can't jump. Instead you may move to a square <strong>beside</strong> the opponent's pawn, as long as no wall blocks that step.</p>
{figure(SIDESTEP_BOARD, 'The wall behind the white pawn stops the jump, so the cyan pawn may go to A or B instead.')}"""),
        ("place-walls", "How to Place Walls", f"""
<p>Instead of moving, you can place one wall. A wall makes your opponent's route longer, which is just as good as getting you closer to the goal.</p>
<ol class="steps">
<li><strong>Pick a wall.</strong>Under the board is your wall tray, with one horizontal and one vertical wall. Drag the one you want onto the board.</li>
<li><strong>Choose the spot.</strong>While you drag, the nearest groove shows a preview. On a touch screen the wall is held just above your finger so you can see it.</li>
<li><strong>Check that it's allowed.</strong>A wall can't overlap or cross another wall, and it can never take away a player's last route to their goal. If the preview isn't legal, a message under the board says why and the wall can't be placed.</li>
<li><strong>Let go to place it.</strong>Release the wall over the groove you want and your wall count goes down by one. You can also tap a wall in the tray to choose its type, tap a groove on the board, and then press Place selected wall.</li>
</ol>
<p>Walls are final. They can't be moved or picked up again, and an online game has no undo, so take a second look at the preview first.</p>
{figure(WALL_BOARD, 'Two walls side by side. The white pawn needed 6 steps to reach the bottom row; now it needs 8, counting only the walls.')}
<h3>An illegal wall</h3>
<p>The dashed wall below isn't allowed. The white pawn in the corner would have no way out, and a wall may never take away a player's last route.</p>
{figure(SEALED_BOARD, 'Not allowed: this wall would seal the white pawn into the corner.')}"""),
        ("how-to-win", "How to Win Quoridor", f"""
<p>The first player whose pawn reaches <strong>any square</strong> on the opposite edge wins immediately. You don't need to land on a particular square.</p>
{figure(GOAL_BOARD, 'The cyan pawn is one step from winning: any square in the top row will do.')}
<p>{"An online game can also end if a player presses <em>Resign</em>, leaves the game, or stays disconnected for more than a minute. In each case the other player wins. Afterwards you can request a rematch." if online else "A game can also end if a player resigns, which gives the win to the other side."}</p>"""),
        ("beginner-tips", "Beginner Tips", """
<ol class="steps">
<li><strong>Count both routes.</strong>Before each turn, work out how many steps you need and how many your opponent needs. Whoever is ahead should usually keep moving.</li>
<li><strong>Plan one step further.</strong>Ask what your opponent can do in reply before you commit to a move or a wall.</li>
<li><strong>Spend walls where they hurt most.</strong>A wall that adds one step costs you a turn and a wall. Look for walls that force several steps of detour.</li>
<li><strong>Balance moving and blocking.</strong>Only moving lets a good blocker catch you out, and only walling leaves you no closer to the goal.</li>
<li><strong>Keep an eye on the timer.</strong>""" + ("Online turns last 32 seconds, and each player has 5 minutes in total. Decide early, and keep the tab open so you don't forfeit by disconnecting." if online else "Each turn has a 32-second timer, and each player has 5 minutes in total.") + """</li>
<li><strong>Practice first.</strong>""" + ('<a href="/play/computer/">Play the computer on Easy</a> to get used to the controls before you meet a person.' if FEATURES["computer"] else "Take a few moves slowly to get used to the controls.") + """</li>
</ol>
<p>When you're ready for more, read the <a href="/quoridor-strategy/">Quoridor strategy guide</a>.</p>"""),
        ("play-your-first-game", "Play Your First Online Game" if online else "Play Your First Game", f"""
<div class="card cta-panel">
  <p class="h-sm"><strong>You know enough to start.</strong></p>
  <p>{"Pick a username, press Find an opponent, and learn as you play. The board highlights your legal moves and explains why a wall isn't allowed." if online else "Choose a mode and learn as you play. The board highlights your legal moves and explains why a wall isn't allowed."}</p>
  <div class="btn-row">{"".join(play_links)}</div>
</div>"""),
        ("faq", "Frequently Asked Questions", faq_html),
    ]
    return article_page(
        "/how-to-play-quoridor/", "How to Play Quoridor Online – Beginner's Guide",
        "Learn how to play Quoridor online: start a game, move your pawn, place walls, beat the turn timer and invite a friend to a private room.",
        "How to Play Quoridor Online: A Beginner's Guide",
        "A step-by-step introduction to online play with diagrams: how to start a game, what you can do on your turn, and how a game is won.",
        sections,
        [("Quoridor rules", "/quoridor-rules/", "the precise rules, including every wall restriction."),
         ("Quoridor strategy", "/quoridor-strategy/", "tactics for getting ahead."),
         ("The Quoridor board game", "/quoridor-board-game/", "what the game is and where it comes from.")],
        "How to play Quoridor", "how", cta=False, schema=[faq_schema],
    )


def rules():
    sections = [
        ("objective", "Game objective and winning condition", """
<p>Quoridor is a two-player game on a 9×9 board. You win by being <strong>the first player to move your pawn onto any one of the 9 squares of the opposite edge</strong>, the edge your opponent started on. You don't need to land on a particular square, and you win the moment you arrive.</p>
<p>Nothing is captured and nothing is removed from the board. The game is a race in which walls make a route longer, so each player's goal edge is simply the other player's starting edge.</p>
<p class="small text-muted">This page describes the two-player game. The official four-player version uses the same rules with 5 walls per player and a pawn on each edge. It is not covered here and is not available on this site.</p>"""),
        ("pieces", "Board layout, player positions and pieces", f"""
<p>A standard set has one board with 81 squares, 20 walls and 4 pawns. A two-player game uses two pawns and all 20 walls.</p>
<ul>
<li><strong>Board.</strong> 9 rows by 9 columns of squares, separated by thin grooves.</li>
<li><strong>Pawns.</strong> One per player. Each player starts on the <strong>middle square (the fifth of nine) of their own edge</strong>, so the two pawns face each other across the board.</li>
<li><strong>Walls.</strong> A wall is two squares long. It is placed in the grooves between squares, never on a square.</li>
</ul>
{figure(SETUP_BOARD, "Starting position: a pawn in the middle of each player's edge and no walls on the board. Each player's goal is the whole edge where the other pawn starts.")}"""),
        ("setup", "Standard setup and walls per player", """
<p>In a two-player game each player takes <strong>10 walls</strong> and keeps them to the side. Both pawns go on the middle square of their starting edge.</p>
<div class="table-wrap"><table>
<thead><tr><th scope="col">Item</th><th scope="col">Two-player game</th></tr></thead>
<tbody>
<tr><td>Board</td><td>9×9 squares (81)</td></tr>
<tr><td>Pawns</td><td>1 per player, on the middle square of its own edge</td></tr>
<tr><td>Walls</td><td>10 per player (20 in the set)</td></tr>
<tr><td>Wall length</td><td>2 squares</td></tr>
<tr><td>Wall positions</td><td>8 × 8 in each of 2 orientations (128 in total)</td></tr>
</tbody></table></div>
<p>The official rulebook has the players draw lots to decide who starts. On this site, Player 1 (the filled cyan pawn that starts at the bottom) always moves first in same-device and computer games. In online games the server picks who goes first at random, and a rematch swaps the order.</p>"""),
        ("turns", "Turn order: move the pawn or place a wall", """
<p>Players alternate turns. On your turn you do <strong>exactly one</strong> of these two things:</p>
<ol>
<li>move your pawn, or</li>
<li>place one of your walls.</li>
</ol>
<p>You can't do both and you can't pass. Once you have placed all 10 of your walls, you can only move your pawn.</p>"""),
        ("movement", "Legal pawn movement", f"""
<ul>
<li>A pawn moves <strong>one square</strong> up, down, left or right. Moving backwards or sideways is allowed.</li>
<li>A pawn <strong>can't move diagonally</strong>, apart from the sidestep described in the next section.</li>
<li>A pawn <strong>can't pass through a wall</strong>. It has to go around. A wall blocks movement across its groove in both directions.</li>
<li>A pawn <strong>can't leave the board</strong> and can't end its move on the other pawn's square.</li>
</ul>
{figure(MOVE_BOARD, 'The cyan pawn can step left, right or down. The wall above it blocks the move up.')}"""),
        ("jumping", "Jumping over an opponent and special movement situations", f"""
<p>When the two pawns stand on <strong>neighboring squares</strong> that are <strong>not separated by a wall</strong>, the player whose turn it is may <strong>jump</strong> over the opponent's pawn and land on the square directly behind it, advancing an extra square. The jump is your whole move for that turn. It is a choice, never an obligation.</p>
{figure(JUMP_BOARD, 'Straight jump: the cyan pawn jumps over the white pawn and lands on A.')}
<h3>When the jump is blocked: the sidestep</h3>
<p>If a <strong>wall</strong> is directly behind the pawn you would jump, you can't jump. Instead you may place your pawn on a square <strong>to the left or to the right of the opponent's pawn</strong>. This is the one situation in which a pawn moves diagonally.</p>
{figure(SIDESTEP_BOARD, 'The wall behind the white pawn blocks the straight jump, so the cyan pawn may move to A or B instead.')}
<h3>Details that matter</h3>
<ul>
<li><strong>A wall between the pawns blocks the jump.</strong> Neighboring pawns separated by a wall can't jump over each other. Each is simply blocked in that direction.</li>
<li><strong>The sidestep squares must be reachable.</strong> You can't step to a side square if a wall lies between it and the opponent's pawn.</li>
<li><strong>Jumps work in every direction.</strong> Forwards, backwards or sideways, whenever the two pawns are neighbors.</li>
<li><strong>The board edge.</strong> The official rulebook mentions only a wall behind the jumped pawn. This site treats the board edge the same way: with no square to land on, you sidestep instead.</li>
</ul>"""),
        ("walls", "Wall placement, orientation and restrictions", f"""
<p>A wall covers the length of <strong>two squares</strong> and sits exactly in the grooves between two sets of two squares. It is either <strong>horizontal</strong> (blocking movement up and down) or <strong>vertical</strong> (blocking movement left and right).</p>
<p>A wall placement is legal only if all of these are true:</p>
<ol>
<li><strong>You have a wall left.</strong> Each player has 10.</li>
<li><strong>It lies fully on the board</strong>, centered between two pairs of squares. There are 8 × 8 positions in each orientation.</li>
<li><strong>It does not overlap another wall,</strong> not even by one square.</li>
<li><strong>It does not cross another wall.</strong> A horizontal and a vertical wall can't share the same middle point.</li>
<li><strong>It leaves every player a route to their goal edge</strong> (see the next section).</li>
</ol>
<p>Walls may touch end to end or meet at a right angle, and you can place them in front of your opponent or anywhere else. Once placed, a wall <strong>stays for the rest of the game</strong>. It can't be moved, rotated or taken back.</p>
{figure(WALL_BOARD, 'Two horizontal walls placed end to end. Together they cover four columns, so the white pawn has to walk sideways around them.')}"""),
        ("paths", "The legal route rule", f"""
<p>You may place a wall to slow your opponent or to protect your own path, but you may <strong>never leave any player, yourself included, with no route at all to their goal edge</strong>. The official rulebook puts it as: an access to the goal line must always be left open.</p>
<ul>
<li>Check both pawns before you place a wall. Each must still have a path of legal one-square steps to at least one square of its goal edge.</li>
<li>A wall that makes a route <strong>much longer</strong> is perfectly legal. Only a wall that makes it <strong>impossible</strong> is forbidden.</li>
<li>For this check, <strong>only walls count as obstacles.</strong> Pawns are ignored because they move and can be jumped. This is how this site enforces the rule.</li>
<li>The check applies to the position <em>after</em> your wall is placed, with all earlier walls in place. A wall that is legal now can become illegal later, once other walls have been added.</li>
</ul>
{figure(SEALED_BOARD, 'Not allowed: the dashed wall would shut the white pawn into the top-left corner, leaving it no route to the bottom edge.')}"""),
        ("illegal", "Common illegal moves, with examples", f"""
<p>These are the attempts that break the rules most often. The game on this site refuses each of them and says why.</p>
<div class="table-wrap"><table>
<thead><tr><th scope="col">Illegal move</th><th scope="col">Why it's illegal</th></tr></thead>
<tbody>
<tr><td>Moving two squares in one turn</td><td>A pawn moves one square. The only extra distance comes from a jump, which lands behind the opponent's pawn.</td></tr>
<tr><td>Moving diagonally on an open board</td><td>A diagonal step exists only as the sidestep when a straight jump is blocked.</td></tr>
<tr><td>Walking through a wall</td><td>A wall blocks movement across the groove it sits in.</td></tr>
<tr><td>Jumping over a pawn through a wall</td><td>A jump needs neighboring pawns that are <em>not separated by a wall</em>.</td></tr>
<tr><td>Sidestepping when the straight jump is possible</td><td>The sidestep is only allowed when a wall (or the board edge) is directly behind the opponent's pawn.</td></tr>
<tr><td>Moving and placing a wall in one turn, or passing</td><td>Each turn is exactly one action.</td></tr>
<tr><td>Placing a wall on top of another wall</td><td>Walls may not overlap, even partly.</td></tr>
<tr><td>Crossing two walls at their middle</td><td>A horizontal and a vertical wall can't share a middle point.</td></tr>
<tr><td>Placing an 11th wall</td><td>Each player has 10 walls.</td></tr>
<tr><td>Sealing a pawn in</td><td>Every player must keep at least one route to their goal edge.</td></tr>
<tr><td>Moving or taking back a placed wall</td><td>Walls are permanent.</td></tr>
</tbody></table></div>
<h3>Overlapping walls</h3>
{figure(OVERLAP_BOARD, 'Not allowed: the dashed wall would overlap the existing wall along one square.')}
<h3>Crossing walls</h3>
{figure(CROSS_BOARD, 'Not allowed: the dashed vertical wall would cross the horizontal wall at its middle point.')}
<h3>Jumping through a wall</h3>
{figure(WALL_JUMP_BOARD, 'With a wall between the pawns no jump is possible. The cyan pawn can only step left, right or down.')}"""),
        ("summary", "Quick rules summary", f"""
<ol>
<li>Two players, a 9×9 board, one pawn each on the middle square of opposite edges, 10 walls each.</li>
<li>Win by being first to reach <strong>any square</strong> of the opposite edge.</li>
<li>Each turn: move your pawn one square <strong>or</strong> place one wall.</li>
<li>Pawns step up, down, left or right, never through walls.</li>
<li>Neighboring pawns with no wall between them: jump to the square behind the opponent. If a wall is behind them, step to their left or right instead.</li>
<li>A wall is 2 squares long, can't overlap or cross another wall, and is permanent.</li>
<li>No wall may leave any player without a route to their goal edge.</li>
<li>With no walls left, you can only move.</li>
</ol>
<div class="card cta-panel">
  <p class="h-sm"><strong>Put the rules into practice.</strong></p>
  <p>The board highlights your legal moves and explains why a wall isn't allowed, so you can learn as you play.</p>
  <div class="btn-row"><a class="btn btn--primary" href="/play/">Play Quoridor {icon('arrow')}</a><a class="btn btn--secondary" href="/how-to-play-quoridor/">Beginner's guide</a></div>
</div>
<p class="small text-muted">These rules follow the official Gigamic rulebook (Quoridor, designed by Mirko Marchesi). The rulebook is silent on a few edge cases, and there this site's game applies the conventions marked above: the board edge acts like a wall behind a jumped pawn, and pawns are ignored by the route check. Quoridor Online is independent and not affiliated with Gigamic or the designer.</p>"""),
    ]
    return article_page(
        "/quoridor-rules/", "Quoridor Rules Explained – How to Move and Place Walls",
        "Understand the Quoridor rules, including pawn movement, jumping, wall placement, legal paths, turn order, and how to win the game.",
        "Quoridor Rules: The Complete Guide",
        "The full reference to the two-player Quoridor rules: setup, pawn movement, jumps, wall placement and the rule that keeps every path open.",
        sections,
        [("How to play Quoridor", "/how-to-play-quoridor/", "a gentler, step-by-step introduction."),
         ("Quoridor strategy", "/quoridor-strategy/", "what to do with these rules once you know them."),
         ("The Quoridor board game", "/quoridor-board-game/", "components, history and how play modes differ.")],
        "Quoridor rules", "rules", cta=False,
    )


# ---- Strategy page boards. Every step count quoted on the strategy page was checked by searching for the
# shortest route around the walls shown (pawns ignored, as in the legal-route rule). If you change a
# position or a caption, re-check the numbers.
_GAP_LINE = [("h", 4, 1), ("h", 4, 5)]  # a row of walls with gaps at the left edge, in the middle and at the right edge

ST_ROUTE_BOARD = board_svg(
    [("h", 3, 2), ("h", 3, 4)], [(6, 4, "p1"), (1, 2, "p2")],
    "Quoridor strategy diagram. Two indigo walls side by side cover four columns in front of a cyan pawn near the bottom. A white ring pawn stands near the top left. "
    "Dashed squares numbered 1 to 8 trace the cyan pawn's shortest route: up two squares, two squares right, then straight up past the right end of the walls.",
    marks=[(5, 4, "1"), (4, 4, "2"), (4, 5, "3"), (4, 6, "4"), (3, 6, "5"), (2, 6, "6"), (1, 6, "7"), (0, 6, "8")])
ST_WEAK_BOARD = board_svg(
    _GAP_LINE, [(5, 0, "p1"), (4, 3, "p2")],
    "Quoridor strategy diagram. A row of indigo walls with three gaps: at the left edge, in the middle and at the right edge. A white ring pawn stands just above the middle gap and a cyan pawn "
    "stands just below the left-edge gap. One extra wall, outlined in white, lies a row below the line under the middle columns, so the white pawn can simply step aside.",
    new_walls=[("h", 5, 3)])
ST_STRONG_BOARD = board_svg(
    _GAP_LINE, [(5, 0, "p1"), (4, 3, "p2")],
    "Quoridor strategy diagram. The same position, but the new wall, outlined in white, closes the middle gap. The row of walls is now open only at the left edge and the right edge, "
    "and the white pawn has to walk three squares to the left to get through.",
    new_walls=[("h", 4, 3)])
ST_SHARED_BEFORE_BOARD = board_svg(
    _GAP_LINE, [(5, 4, "p1"), (3, 3, "p2")],
    "Quoridor strategy diagram. A row of indigo walls with gaps at the left edge, in the middle and at the right edge. A cyan pawn stands just below the middle gap and a white ring pawn stands above it, "
    "one column to the left. Both pawns need to pass through the middle gap.")
ST_SHARED_AFTER_BOARD = board_svg(
    _GAP_LINE, [(5, 4, "p1"), (3, 3, "p2")],
    "Quoridor strategy diagram. The same position after a wall, outlined in white, closes the middle gap. Both pawns now have to walk to the left edge or the right edge to get through.",
    new_walls=[("h", 4, 3)])
ST_LONE_GAP_BOARD = board_svg(
    _GAP_LINE + [("h", 4, 3)], [(6, 7, "p1"), (4, 3, "p2")],
    "Quoridor strategy diagram. A row of indigo walls closed everywhere except the far left edge. The two right-hand gaps are shut, the last one by a wall outlined in white. "
    "A cyan pawn stands below the row near the right edge, a long way from the opening. A white ring pawn stands above the row only three squares from it.",
    new_walls=[("h", 4, 7)])
ST_RACE_BOARD = board_svg(
    [("h", 1, 0), ("v", 5, 1)], [(4, 4, "p1"), (3, 6, "p2")],
    "Quoridor strategy diagram. A cyan pawn in the middle of the board and a white ring pawn to its right and one row higher. Two walls far off at the left do not touch either pawn's route.")
ST_FOUR_WALLS_BOARD = board_svg(
    [("h", 2, 0), ("h", 2, 2), ("h", 2, 4), ("h", 2, 6)], [(7, 4, "p1"), (2, 4, "p2")],
    "Quoridor strategy diagram. Four horizontal walls placed end to end across the board, leaving only the far right column open. A white ring pawn stands just above the row of walls "
    "and a cyan pawn stands well below it. Both must get past the row.")
ST_LEDGER_BOARD = board_svg(
    _GAP_LINE + [("h", 4, 3)], [(5, 0, "p1"), (4, 3, "p2")],
    "Quoridor strategy diagram. A row of indigo walls closed in the middle, with a second wall across the two left columns just above the left-edge gap. A cyan pawn stands at the left edge below the row "
    "and a white ring pawn stands above it. Dashed squares numbered 1 to 7 trace cyan's shortest route: through the left gap, two squares right, then straight up.",
    marks=[(4, 0, "1"), (4, 1, "2"), (4, 2, "3"), (3, 2, "4"), (2, 2, "5"), (1, 2, "6"), (0, 2, "7")])
ST_THREAT_BOARD = board_svg(
    _GAP_LINE + [("h", 4, 3), ("h", 3, 0)], [(5, 0, "p1"), (4, 3, "p2")],
    "Quoridor strategy diagram. The same position with a vertical wall, outlined in white, beside the left-edge gap. It shuts cyan into a one-square-wide channel along the left edge.",
    new_walls=[("v", 4, 0)])
ST_SLOT_BOARD = board_svg(
    _GAP_LINE + [("v", 4, 3)], [(6, 4, "p1"), (2, 7, "p2")],
    "Quoridor strategy diagram. A row of indigo walls with a gap in the middle, and a vertical wall outlined in white standing in the middle of that gap. "
    "A dashed red wall with a cross marks the only horizontal wall that could have closed the gap. A cyan pawn stands below the gap and a white ring pawn is at the upper right.",
    new_walls=[("v", 4, 3)], bad_walls=[("h", 4, 3)])


def figure_pair(*figs):
    return '<div class="figure-pair">' + "".join(figs) + "</div>"


def strategy():
    computer = FEATURES["computer"]
    extra = []
    if FEATURES["local"]:
        extra.append('Playing a friend on the <a href="/play/local/">same device</a> is a good way to talk through counts out loud.')
    if FEATURES["online"]:
        extra.append('Online opponents will also show you styles the computer does not: some wall early, some race.')
    extra_practice = f'<p>{" ".join(extra)}</p>' if extra else ""
    practice_link = '<a href="/play/computer/">play against the computer</a>' if computer else "play against the computer once that mode is available"
    sections = [
        ("plan-your-route", "Plan Your Route Before Placing Walls", f"""
<p>Every decision in Quoridor starts with a count: <strong>how many moves does each pawn still need to reach its goal edge?</strong> Work out the shortest legal route for yourself and for your opponent, going around every wall on the board. The rest of this guide builds on that count.</p>
<div class="callout"><p><strong>How the examples count.</strong> A step is one square up, down, left or right. Counts follow the shortest route around the walls and ignore jumps and pawn positions, the same way the legal-route rule on the <a href="/quoridor-rules/">rules page</a> does. Cyan is the filled pawn and moves up; white is the ring pawn and moves down.</p></div>
<h3>The straight line is not always the shortest</h3>
{figure(ST_ROUTE_BOARD, 'Cyan needs 8 steps: the numbered squares go around the right end of the walls. White also needs 8, one step left and then straight down.')}
<p>Two walls side by side cover four columns, so cyan's straight route up the middle is blocked. Going around the right end takes two sideways steps and 8 steps in total. Going around the left end takes three sideways steps and 9 in total. White has the same trouble from the other side: one step left, then straight down, also 8.</p>
<p>That is an 8 to 8 tie with cyan on the move. When the counts are equal, the player who moves first arrives first, so cyan is a tempo ahead.</p>
<h3>Balance direct progress against detours</h3>
<p>A sideways step can feel like a wasted move, but when a wall is in the way it is part of the shortest route. The useful question is not "am I moving forward?" but "did that move make my count smaller?"</p>
<ul>
<li><strong>Take the detour that shortens the count.</strong> A forward step into a dead end is worse than a sideways step toward the nearest gap.</li>
<li><strong>Stay flexible when two gaps cost about the same.</strong> A pawn that can use either of two distant gaps is harder to punish than one that has already committed, because one wall rarely closes both.</li>
<li><strong>Recount after every wall.</strong> A new wall can lengthen your route and also change which gap is nearest.</li>
</ul>
<p>Only once you know both counts does it make sense to ask whether a wall would help.</p>"""),
        ("use-walls-efficiently", "Use Walls Efficiently", f"""
<p>You have 10 walls, and a placed wall can never be moved. Each one also costs the move you would otherwise have made. That gives a simple way to price a wall:</p>
<div class="callout"><p><strong>Value of a wall = steps it adds to your opponent's route, minus steps it adds to yours, minus 1.</strong> The 1 is the step you did not take. A wall that adds only one step to your opponent just breaks even, and it still uses up one of your 10 walls.</p></div>
<p>In the position below, a row of walls has three gaps: one at the left edge, a two-wide one in the middle and one at the right edge. White stands at the middle gap and needs 4 steps. Cyan needs 5 and is on the move, so cyan is a step behind.</p>
{figure_pair(
    figure(ST_WEAK_BOARD, 'Wall A (outlined) adds 1 step: white sidesteps. White 4 to 5, cyan stays at 5. Value: 1 - 0 - 1 = 0.'),
    figure(ST_STRONG_BOARD, 'Wall B (outlined) adds 3 steps: white must walk to the left edge. White 4 to 7, cyan stays at 5. Value: 3 - 0 - 1 = 2.'),
)}
<p>Wall A is placed right in front of white's path on open ground, so white simply steps aside. Wall B finishes the row of walls that was already there and shuts the nearest gap, so the next one is three squares away. After wall B cyan needs 5 steps and white needs 7. Same wall budget, very different result.</p>
<h3>Where efficient walls come from</h3>
<ul>
<li><strong>Existing walls.</strong> A wall that closes a gap in a line, or joins two walls, can add several steps. On a nearly empty board, the best single wall adds only about one.</li>
<li><strong>Distance to the next opening.</strong> Closing a gap is worth the number of extra squares the pawn must walk to the next gap, so look for gaps whose neighbors are far away.</li>
<li><strong>Patience.</strong> Walls that add one step are rarely worth a slot. Save your walls for moments like wall B.</li>
</ul>"""),
        ("balance-offense-defense", "Balance Offense and Defense", f"""
<p>Every wall changes the board for both pawns. Before you place one, count both routes <em>after</em> the wall, not just your opponent's.</p>
<h3>A wall that hurts both players helps the one who moves next</h3>
<p>Here both pawns need to pass through the same two-wide gap. Each needs 5 steps and cyan is on the move, so cyan is already winning the pure race. Closing the gap looks aggressive:</p>
{figure_pair(
    figure(ST_SHARED_BEFORE_BOARD, 'Before: cyan 5, white 5, cyan to move.'),
    figure(ST_SHARED_AFTER_BOARD, 'After cyan closes the gap: both need 8, and white is on the move.'),
)}
<p>Both pawns now have a detour of three squares, so the count is 8 to 8. But the wall used up cyan's turn, so white is on the move at equal distance and arrives first. Cyan turned a winning race into a losing one and spent a wall to do it.</p>
<h3>What defense actually means</h3>
<p>In Quoridor, defense is mostly about keeping your own route hard to punish. Before each move, look at your route and ask: <strong>which single wall would add the most steps to me?</strong> If the answer is 3 or more, deal with it now:</p>
<ul>
<li>Step past the choke point before your opponent can close it (see "Recognize When to Move Instead").</li>
<li>Choose a route where no single wall hurts that much, for example one with two gaps of similar cost.</li>
<li>Take away the wall's slot, as shown in the advanced tactics below.</li>
</ul>
<p>Offense and defense are the same arithmetic. A wall that adds more steps to your opponent than to you is attacking and defending at once. A wall that adds the same number to both is just a gift of the move.</p>"""),
        ("think-ahead", "Think Several Moves Ahead", f"""
<p>Before you place a wall, play out your opponent's best reply, not just their reply to the position you have in mind. A wall also changes what <em>they</em> can do next.</p>
<p>Take the row of walls from the previous section, with cyan far over on the right side. Cyan needs 6 steps and white needs 4, with cyan on the move. Cyan is behind, so closing the middle gap looks attractive: it adds 3 steps to white's route (4 to 7) and nothing to cyan's (still 6). On paper cyan has gone from two steps behind to one step ahead.</p>
{figure(ST_LONE_GAP_BOARD, 'White replies by closing the right-hand gap (outlined). Cyan now needs 13 steps, white still needs 7.')}
<p>Now look at the board from white's side. Cyan's wall left only the right-hand gaps and the left edge open. White's reply shuts the right-hand gap, which leaves a single opening at the far left. White is three squares from it. Cyan is seven columns away, so cyan's route grows from 6 to 13 while white's stays at 7.</p>
<p>The lesson is not "never close gaps". It is that <strong>a wall removes options for the player who is farther away</strong>, so check what is left after your wall as well as what it takes away.</p>
<ol class="steps">
<li><strong>Imagine the wall and recount both routes.</strong>This is the number you hope to gain.</li>
<li><strong>Find the opponent's best wall against you.</strong>Recount again with that wall on the board. Does the wall you just imagined make it stronger?</li>
<li><strong>Compare the totals.</strong>Only place the wall if you are still ahead after their best reply.</li>
<li><strong>Do the same for them.</strong>Ask which of their walls become stronger once your wall is down.</li>
</ol>"""),
        ("move-instead", "Recognize When to Move Instead", f"""
<p>A wall feels active, but a pawn step is free: it costs no wall and always makes progress. If you are winning the race, the right move is often just to move.</p>
{figure(ST_RACE_BOARD, 'Cyan needs 4 steps, white needs 5, and cyan is on the move.')}
<p>Here cyan needs 4 steps and white needs 5, with cyan to move. Count what each side can do:</p>
<ul>
<li>If cyan just steps forward, the count is 3 to 5 with white on the move. For white to turn the race around, a wall would have to add 3 steps to cyan's route. The best single wall on this board adds 1.</li>
<li>If cyan places a wall that adds 1 step to white, the count is 4 to 6. Cyan was already winning, so that wall changed nothing and cost cyan one of its 10 walls.</li>
</ul>
<h3>A quick race check</h3>
<p>Use the counts on your own turn, ignoring jumps and assuming no more walls:</p>
<div class="table-wrap"><table>
<thead><tr><th scope="col">Your count compared with theirs</th><th scope="col">What it means</th></tr></thead>
<tbody>
<tr><td>Equal or lower, on your move</td><td>You win the pure race. To catch up, your opponent needs a wall that adds at least <strong>your lead plus 2</strong> steps, because you will have stepped first. Keep moving unless a wall of yours clearly beats that.</td></tr>
<tr><td>Behind by <em>k</em> steps, on your move</td><td>Walking will not be enough. You need a wall that adds at least <strong><em>k</em> + 1</strong> steps to your opponent, because the wall costs you your move.</td></tr>
</tbody></table></div>
<p>The second row explains the previous section: cyan was one step behind (5 against 4) and needed a wall worth at least 2, so wall B (adds 3) was worth placing and wall A (adds 1) was not. In the race above, cyan leads by one step (4 against 5), so white would need a wall that adds 3 or more.</p>
<p>Moving can also be your defense. If your opponent has a wall that would add 3 steps to your route right in front of you, stepping past that spot removes the threat for free. Use the check above to decide whether a wall of your own is actually needed.</p>"""),
        ("beginner-mistakes", "Common Beginner Mistakes", f"""
<ul>
<li><strong>Playing too defensively.</strong> Building a barrier across the middle feels safe, but a long row of walls also lies across your own path.</li>
<li><strong>Ignoring the opponent's route.</strong> Counting only your own steps hides the other half of the race. If you do not recount after each of their walls, you will not notice when you fall behind.</li>
<li><strong>Wasting walls on one-step detours.</strong> A wall that adds 1 step is worth 0 (see "Use Walls Efficiently") and permanently uses one of your 10.</li>
<li><strong>Hoarding all 10 walls.</strong> A wall never used is worth nothing once the game ends. Keep a couple in reserve, but spend them on walls worth 2 or more.</li>
<li><strong>Forgetting that walls are permanent.</strong> A wall that helps you now can cost you later if the game moves your pawn through that area.</li>
</ul>
{figure(ST_FOUR_WALLS_BOARD, 'Before the four walls cyan needs 7 and white needs 6. After them cyan needs 11 and white needs 10.')}
<p>The board above shows the first mistake. Four walls were placed end to end across the board, leaving only the far right column open. That adds 4 steps to white's route (6 to 10), which sounds like a lot. But the row lies across cyan's path too, so cyan's route also grows by 4 (7 to 11). Cyan spent four turns and 40% of its walls, and the race is exactly as close as it was before.</p>"""),
        ("advanced-tactics", "Advanced Quoridor Tactics", f"""
<h3>Keep a tempo ledger</h3>
<p>Strong players think in counts: how many steps each side needs and who is on the move. Writing it down for a few turns makes the pattern clear. This is the position from "Use Walls Efficiently" a few moves later:</p>
<div class="table-wrap"><table>
<thead><tr><th scope="col">After</th><th scope="col">Cyan needs</th><th scope="col">White needs</th><th scope="col">On the move</th></tr></thead>
<tbody>
<tr><td>Start</td><td>5</td><td>4</td><td>Cyan</td></tr>
<tr><td>Cyan closes the middle gap</td><td>5</td><td>7</td><td>White</td></tr>
<tr><td>White walls the two left columns just above the left gap</td><td>7</td><td>7</td><td>Cyan</td></tr>
</tbody></table></div>
<p>Cyan started a step behind and swung ahead with the gap-closing wall. At that moment no single wall adds more than 2 steps to cyan's route, so white's reply, which adds exactly 2, was the strongest one by count. The counts are now level with cyan on the move, which on its own would favor cyan.</p>
<h3>Then stress-test your route</h3>
<p>A level count is only half the picture. Ask what your opponent's best wall would add <em>right now</em>:</p>
{figure_pair(
    figure(ST_LEDGER_BOARD, 'Cyan needs 7 steps (numbered squares), white needs 7, and cyan is on the move.'),
    figure(ST_THREAT_BOARD, 'White threatens the outlined wall: cyan 7 to 14, white 7 to 8.'),
)}
<p>Cyan's route runs through a one-square-wide channel beside the board edge, and a channel has no alternative. A vertical wall next to the gap would add 7 steps to cyan's route and only 1 to white's. The same wall is worth even more once cyan has stepped into the channel (9 steps instead of 7). So the level count does not make cyan safe, and cyan's real question this turn is how to deal with that threat. Routes along the edge or between walls, yours or theirs, are where one wall costs the most, so check them first.</p>
<h3>Take away the opponent's best wall</h3>
<p>If one wall would hurt you badly, you can sometimes make it illegal instead of walking away from it. A wall that crosses or overlaps its only legal slot removes the threat for good.</p>
{figure(ST_SLOT_BOARD, 'The vertical wall (outlined) crosses the middle gap. The only wall that could shut the gap, dashed and crossed out, is no longer legal.')}
<p>In this position cyan relies on the middle gap, and white has no need of it. A horizontal wall there would add 3 steps to cyan's route. The gap is two columns wide between two walls, so the only wall that can close it is the one in the dashed position. Overlapping either neighbor is not allowed, and a vertical wall through its middle point crosses it. By placing that vertical wall, cyan has made the gap permanent. It costs a turn and a wall, so do it only when the gap is your lifeline and the threat is large.</p>
<h3>Hold two or three walls for the finish</h3>
<p>Tactics like the lone-gap squeeze need a wall in hand to carry out. A player who has used all 10 can only move, and cannot answer a late wall with a wall of their own. Spend early walls only when they are worth 2 or more, and keep a couple in reserve for the moment a gap appears.</p>
<h3>Remember what the counts leave out</h3>
<p>The counts above ignore pawns. When the pawns stand face to face, the player on the move can jump over the other pawn and cover two squares in one turn, so give a pawn that is about to jump an extra step of credit. The <a href="/quoridor-rules/">rules page</a> explains jumps and sidesteps in full.</p>
<p class="small text-muted">These are rules of thumb built from counting positions, not a proof of optimal play. Test them against real opponents.</p>"""),
        ("practice", "Practice Against Different Opponents", f"""
<p>Reading about counts is one thing, doing it every turn is another. The fastest way to improve is to play many games and make the count a habit. You can {practice_link} at a level that suits you:</p>
<div class="table-wrap"><table>
<thead><tr><th scope="col">Level</th><th scope="col">Good for</th></tr></thead>
<tbody>
<tr><td><strong>Easy</strong></td><td>Learning to count routes and spotting walls worth 3 or more without pressure. It wanders and walls without much of a plan.</td></tr>
<tr><td><strong>Medium</strong></td><td>Practicing move-or-wall decisions. It blocks you when a wall clearly pays off, so careless walls of your own are punished.</td></tr>
<tr><td><strong>Hard</strong></td><td>Practicing the look-ahead check. It looks two moves ahead and places walls deliberately.</td></tr>
<tr><td><strong>Expert</strong></td><td>Stress-testing your counting. It searches several moves deeper and can take up to about a second to answer.</td></tr>
</tbody></table></div>
<p>Three drills make the practice count:</p>
<ol class="steps">
<li><strong>Say both counts before every move.</strong>"I need 6, they need 5." If you cannot say it, you cannot decide.</li>
<li><strong>Predict the value of each wall.</strong>Work out what it adds to each route and subtract 1 before you place it. Aim for 2 or more.</li>
<li><strong>Find the turning point after each game.</strong>Look for the first turn at which the lead changed hands, and ask what you could have counted differently.</li>
</ol>
{extra_practice}"""),
    ]
    return article_page(
        "/quoridor-strategy/", "Quoridor Strategy – Tips, Tactics and Winning Ideas",
        "Improve your Quoridor strategy with practical tips on efficient routes, wall placement, tempo, opponent prediction, and defensive planning.",
        "Quoridor Strategy: Tips and Tactics to Improve Your Game",
        "Learn to count routes, spend walls where they pay off, and decide when to just move, with worked examples on real board positions.",
        sections,
        [("Quoridor rules", "/quoridor-rules/", "check the exact wall restrictions."),
         ("How to play Quoridor", "/how-to-play-quoridor/", "start here if you're brand new."),
         ("The Quoridor board game", "/quoridor-board-game/", "more about the game itself.")],
        "Quoridor strategy", "strategy",
    )


def board_game_faq():
    """[(question, answer_html)] for the board-game overview page."""
    ways = live_ways()
    return [
        ("How many people can play the Quoridor board game?",
         "The physical game is for two or four players. In a four-player game each person gets 5 walls instead of 10. This website is for two players, which is the classic duel."),
        ("How long does a game of Quoridor take?",
         "A typical two-player game lasts somewhere between 10 and 20 minutes, depending on how long each player thinks."),
        ("Is Quoridor hard to learn?",
         "No. The rules fit in a couple of sentences: move one square or place a wall, and reach the opposite edge first. The depth comes later, from learning when a wall is worth more than a step."),
        ("Is there any luck in Quoridor?",
         "None. There are no dice, cards or hidden pieces, and both players see the whole board at all times. The better plan wins."),
        ("Do the pieces have to be wooden?",
         "No. Many sets, including the classic edition, use wooden walls and pawns, but the rules only care about the pieces' size and number, not the material."),
        ("Can I play Quoridor online instead of buying a set?",
         (f"Yes. You can play {ways} in your browser, free and without an account. " if ANY_MODE_LIVE else "")
         + 'See the <a href="/play/">Play page</a> for what is available. The rules are the standard two-player rules described in the <a href="/quoridor-rules/">Quoridor rules</a>.'),
    ]


def board_game():
    faq = board_game_faq()
    faq_html = '<div class="faq">' + "".join(
        f'<details><summary>{q}</summary><div class="answer"><p>{a}</p></div></details>' for q, a in faq) + "</div>"
    faq_schema = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)}} for q, a in faq],
    }
    ways = live_ways()
    opponents = (ways[0].upper() + ways[1:] + ".") if ways else "Coming soon."
    sections = [
        ("what-is-quoridor", "What Is the Quoridor Board Game?", """
<p>Quoridor is an abstract strategy board game for two or four players, designed by Mirko Marchesi and published by Gigamic. Each player has a single pawn and a stock of walls. There are no dice, cards or hidden information, so every game is decided by planning rather than luck.</p>
<p>Its appeal is how little it asks of you. You can explain it in a minute, yet each turn poses a real question: do I step closer to my goal, or do I spend a wall to slow my opponent down?</p>
<p class="small text-muted">Quoridor Online is an independent website. It is not affiliated with or endorsed by the game's designer or publisher.</p>"""),
        ("objective", "Objective and Basic Gameplay", f"""
<div class="callout"><p><strong>The objective:</strong> be the first player to move your pawn onto <em>any square</em> of the opposite edge of the board.</p></div>
<p>Players take turns, and on each turn you do <strong>one</strong> of two things:</p>
<ul>
<li><strong>Move your pawn</strong> one square up, down, left or right. If your opponent's pawn is directly in front of you, you can jump over it.</li>
<li><strong>Place a wall</strong> in the grooves between squares to block movement. A wall can never be moved afterwards, and you may never seal off a player's last route to their goal.</li>
</ul>
<p>That is the whole game. The step-by-step version is in <a href="/how-to-play-quoridor/">How to play Quoridor</a>, and every edge case is covered by the <a href="/quoridor-rules/">Quoridor rules</a>.</p>
{figure(SETUP_BOARD, 'The starting position of a two-player game: each pawn begins in the middle of its own edge and aims for the opposite one.')}"""),
        ("components", "What Comes in a Physical Game Set?", """
<p>A standard Quoridor set is compact. The classic edition is made of wood and contains:</p>
<ul>
<li><strong>A 9×9 board</strong> of 81 squares, with narrow grooves running between them for the walls.</li>
<li><strong>Four pawns</strong>, one per player in a four-player game. In a two-player game you use two of them, which start in the middle of opposite edges.</li>
<li><strong>Twenty wooden walls</strong>, each long enough to span two squares. They are shared out equally: 10 each in a two-player game, 5 each with four players.</li>
</ul>
<p>Many boards have storage for the unused walls, so the walls you have left are always easy to count.</p>"""),
        ("movement-blocking-planning", "How the Game Combines Movement, Blocking and Planning", f"""
<p>Moving and blocking are two sides of one race. Your walk to the goal gets shorter as you move, while a well-placed wall makes your <em>opponent's</em> walk longer. The player who needs fewer turns to finish is ahead, and every turn is a choice about how to change that count.</p>
<ul>
<li><strong>Movement</strong> is steady but slow: one square per turn.</li>
<li><strong>Blocking</strong> can add many steps for your opponent at once, but each wall is permanent and you only have so many.</li>
<li><strong>Planning</strong> ties them together: when to hold your walls back, when to spend one, and what your opponent can do in reply.</li>
</ul>
<p>Walls never capture or remove anything. They only reshape the board into corridors and detours, and because a wall may never completely seal a path, the best barrier is one that makes the opponent's <em>shortest</em> route much longer than yours.</p>
{figure(MID_BOARD, 'A game in progress. The indigo walls have turned open squares into corridors, and both pawns now have to walk around them.')}
<p>For a deeper look, read the <a href="/quoridor-strategy/">Quoridor strategy guide</a>.</p>"""),
        ("who-enjoys-quoridor", "Who Might Enjoy Quoridor?", """
<ul>
<li><strong>Families and casual players.</strong> The rules are short and the pieces are easy to understand, so a new player can join in during the first game.</li>
<li><strong>Chess and abstract-strategy fans.</strong> Perfect information and no luck mean that mistakes and good ideas both show up on the board.</li>
<li><strong>People who like to out-think an opponent.</strong> Because walls turn the board into a shared puzzle, you are always weighing your own plan against what the other player might do.</li>
<li><strong>Anyone short on time.</strong> A game is usually over in a quarter of an hour or so, and the set is small enough to carry.</li>
</ul>
<p>If you prefer games driven by dice, cards or bluffing, Quoridor may feel too open. If you like a tidy puzzle with a human opponent, it is a good fit.</p>"""),
        ("physical-vs-online", "Physical Board Game Versus Browser-Based Play", f"""
<p>The rules are the same either way. What changes is how you play.</p>
<div class="table-wrap"><table>
<thead><tr><th scope="col"><span class="sr-only">Aspect</span></th><th scope="col">Physical set</th><th scope="col">In your browser</th></tr></thead>
<tbody>
<tr><th scope="row">Setup</th><td>Unpack the board, pawns and walls.</td><td>Open a page. Nothing to install and no account.</td></tr>
<tr><th scope="row">Rule checking</th><td>Players check each wall themselves.</td><td>The game highlights legal moves and refuses illegal walls.</td></tr>
<tr><th scope="row">Opponents</th><td>Someone at the same table.</td><td>{opponents}</td></tr>
<tr><th scope="row">Feel</th><td>Wooden pieces and a table between you.</td><td>Instant start, any time, on a phone or computer.</td></tr>
</tbody></table></div>
<p>Neither is better. A physical set is a pleasure at a table, while the browser version is the quickest way to learn the game or get a match when nobody is around. See <a href="/play/">all the ways to play Quoridor online</a>.</p>"""),
        ("faq", "Frequently Asked Questions", faq_html),
        ("play-and-learn", "Play Quoridor and Keep Learning", f"""
<div class="card cta-panel">
  <p class="h-sm"><strong>Ready to try it?</strong></p>
  <p>Start a game now, or read up first. The board highlights your legal moves, so you can learn as you play.</p>
  <div class="btn-row">
    <a class="btn btn--primary btn--lg" href="/play/">Play Quoridor Now {icon('arrow')}</a>
    <a class="btn btn--secondary btn--lg" href="/how-to-play-quoridor/">How to play</a>
  </div>
</div>
<ul>
<li><a href="/quoridor-rules/"><strong>Quoridor rules</strong></a>: the full rule reference, including every wall restriction.</li>
<li><a href="/quoridor-strategy/"><strong>Quoridor strategy</strong></a>: pathfinding, wall timing and common mistakes.</li>
<li><a href="/how-to-play-quoridor/"><strong>How to play Quoridor</strong></a>: a beginner's walkthrough with diagrams.</li>
</ul>"""),
    ]
    return article_page(
        "/quoridor-board-game/", "Quoridor Board Game – Overview, Objective and Gameplay",
        "Discover the Quoridor board game, its goal, pawns, wooden walls, and strategic gameplay. Learn the basics and try the game online.",
        "Quoridor: The Strategy Board Game",
        "What the game is, what comes in the box, and why a few pawns and walls make such a good duel of planning.",
        sections, None,
        "Quoridor board game", "board", cta=False, schema=[faq_schema],
    )


# ---------------------------------------------------------------- static and legal pages
def simple_page(path, title, desc, h1, lead, content, trail, scripts=()):
    body = page_head(h1, lead, [(trail, None)]) + f'<div class="container pad-page"><div class="article prose">{content}</div></div>'
    return Page(path=path, title=title, description=desc, body=body, breadcrumbs=[(trail, path)], scripts=list(scripts), nav_key=("about" if path == "/about/" else None))


def about():
    modes = []
    if FEATURES["online"]:
        modes.append('<li><strong><a href="/play/online/">Play online</a>.</strong> Play against another person after choosing a display name. No registration is needed.</li>')
    if FEATURES["rooms"]:
        modes.append('<li><strong><a href="/play/create-room/">Private rooms</a>.</strong> Invite a specific friend with a link or a short pairing code.</li>')
    if FEATURES["computer"]:
        modes.append('<li><strong><a href="/play/computer/">Play against the computer</a>.</strong> Practice at Easy, Medium, Hard or Expert difficulty.</li>')
    if FEATURES["local"]:
        modes.append('<li><strong><a href="/play/local/">Play on one device</a>.</strong> Two players share a screen and take turns on the same board.</li>')
    modes_html = "\n".join(modes)
    online_languages = (
        ". Players who use different languages can play each other online, because the language only changes what each person sees."
        if FEATURES["online"] else ".")
    content = f"""
<h2>Our purpose</h2>
<p>Quoridor.online exists to give people a simple place to play Quoridor and learn how it works. Quoridor is easy to explain and rewarding to think about, but it can be hard to try if you don't own a set or have someone to play with. A browser is all you need here.</p>
<p>We also want to help new players get started and improve. That is why the site pairs the game with plain-language guides, instead of leaving you to work out the rules alone.</p>
<h2>What you can do here</h2>
<p>You can play Quoridor in your browser, and read up on it whenever you like.</p>
<h3>Ways to play</h3>
<ul>
{modes_html}
</ul>
<h3>Ways to learn</h3>
<ul>
<li><a href="/how-to-play-quoridor/">How to play Quoridor</a>: a beginner's walkthrough with diagrams.</li>
<li><a href="/quoridor-rules/">Quoridor rules</a>: the full reference, including every wall restriction.</li>
<li><a href="/quoridor-strategy/">Quoridor strategy</a>: pathfinding, wall timing and common mistakes.</li>
<li><a href="/quoridor-board-game/">The Quoridor board game</a>: an overview of the physical game and how the browser version compares.</li>
</ul>
<h2>Our approach</h2>
<ul>
<li><strong>Accessible.</strong> The game runs in your browser with nothing to install and no account, on phones, tablets and computers.</li>
<li><strong>Clear.</strong> A clean board, plain wording and rules that are explained in full rather than assumed.</li>
<li><strong>Straightforward.</strong> You choose how to play and start. We only describe a feature as available once it works.</li>
<li><strong>For everyone.</strong> The site and the game can be shown in English, Spanish, French, German, Arabic, Russian or Chinese with the translate button{online_languages}</li>
</ul>
<h2>An independent project</h2>
<p>Quoridor.online is an independent website. It is not affiliated with, sponsored by or endorsed by the designer or publisher of the Quoridor board game. Quoridor was designed by Mirko Marchesi and published by Gigamic, and we credit them as the source of the game. The game rules described here are those of the standard two-player game, and the guides and software on this site are our own work.</p>
<p>If you enjoy the game and would like a physical set, it is available from its publisher and from game retailers.</p>
<h2>Contact us</h2>
<p>Have feedback, a technical problem or a business inquiry? Visit the <a href="/contact/">contact page</a>.</p>
<p><a class="btn btn--primary" href="/play/">Play Now</a></p>"""
    return simple_page("/about/", "About Quoridor.online – Play and Learn Quoridor",
                       "Learn about Quoridor.online, a browser-based destination for playing Quoridor and exploring its rules, strategies, and gameplay.",
                       "About Quoridor.online", "A browser-based place to play Quoridor and learn how the game works.", content, "About us")


CONTACT_EMAIL = "lahssanyassine1@gmail.com"
CONTACT_TOPICS = (
    ("Technical issue", "Technical issue"),
    ("Feedback", "Feedback or suggestion"),
    ("Accessibility", "Accessibility"),
    ("General inquiry", "General inquiry"),
)


def contact():
    options = "".join(f'<option value="{v}">{label}</option>' for v, label in CONTACT_TOPICS)
    content = f"""
<p>Questions, ideas, or something not working? We read every message. Tell us what you think of the game, report a problem, or suggest what we should add next.</p>
<p>You can write to us at <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a>, or use the form below to start a message in your email app.</p>
<form class="contact-form" id="contact-form" data-to="{CONTACT_EMAIL}" novalidate hidden>
  <div class="field">
    <label for="contact-topic">Subject</label>
    <select class="input" id="contact-topic" name="topic">{options}</select>
  </div>
  <div class="field">
    <label for="contact-name">Your name <span class="text-muted">(optional)</span></label>
    <input class="input" id="contact-name" name="name" type="text" autocomplete="name" maxlength="80">
  </div>
  <div class="field">
    <label for="contact-email">Your email <span class="text-muted">(optional, so we can reply)</span></label>
    <input class="input" id="contact-email" name="email" type="email" autocomplete="email" maxlength="120">
  </div>
  <div class="field">
    <label for="contact-message">Message</label>
    <textarea class="input input--area" id="contact-message" name="message" rows="7" maxlength="3000" required aria-describedby="contact-message-hint contact-message-error"></textarea>
    <span class="hint" id="contact-message-hint">Please don't include passwords or other sensitive personal data.</span>
    <div class="field-error" id="contact-message-error" role="alert" hidden></div>
  </div>
  <div class="field">
    <label class="check-line"><input type="checkbox" id="contact-env" name="env"> Include my browser and screen details (useful for technical issues)</label>
  </div>
  <button class="btn btn--primary" type="submit">{icon('arrow')} Write email</button>
  <div class="notice contact-status" id="contact-status" role="status" hidden>{icon('info')}<div></div></div>
</form>
<h2 id="report-a-problem">Reporting a problem</h2>
<p>The more detail you give, the faster we can find the cause. Please include:</p>
<ul>
<li>The page or game mode you were using (for example online play, against the computer, or one device).</li>
<li>Your device, operating system, and browser with its version.</li>
<li>What you did, what you expected to happen, and what happened instead.</li>
<li>A screenshot, if it helps. For an online game, the time it happened.</li>
</ul>
<h2 id="privacy">Your information</h2>
<p>We use your message and email address only to answer you. The form doesn't send anything by itself: it opens a draft in your own email app, and nothing is sent until you send it. See the <a href="/privacy-policy/">Privacy Policy</a> for how the site handles information.</p>"""
    return simple_page("/contact/", "Contact Quoridor.online",
                       "Contact the Quoridor.online team with questions, feedback, website issues, or suggestions about the online Quoridor game.",
                       "Contact Us", "Send us your feedback, questions or a problem report.", content, "Contact us",
                       scripts=["/assets/js/contact.js"])


PRIVACY_EFFECTIVE = ("2026-10-24", "24 October 2026")
PRIVACY_HISTORY = (
    ("2026-10-17", "17 October 2026", "First full version of this Privacy Policy. It replaces the earlier draft placeholder."),
    ("2026-10-17", "17 October 2026", "Explained that an online search can keep running while you play elsewhere on the site, and the session-storage entry that makes this possible."),
    ("2026-10-17", "17 October 2026", "Added Google Analytics (Google tag) on public pages, with its cookies and data processing. It is not loaded on online-room pages."),
    ("2026-10-17", "17 October 2026", "Described the language choice that the translate button keeps in your browser, and added translated versions of the site."),
    ("2026-10-21", "21 October 2026", "Described the light or dark theme choice that the theme switch keeps in your browser."),
    ("2026-10-23", "23 October 2026", "Described the display name and the win counts between two players that your browser now remembers, in entries named quoridor.username and quoridor.scores."),
    ("2026-10-23", "23 October 2026", "Described the score, rank and achievements that your browser now keeps, in an entry named quoridor.progress."),
    ("2026-10-24", "24 October 2026", "Private rooms can now be set up for a game variant and for up to four players. Said that a room also holds the settings of its game, and that every player in a room sees the display names of the others."),
)

LANGUAGE_STORAGE = """<p>If you pick a language with the translate button, your browser keeps the language code (for example <em>es</em>) in an entry named <em>quoridor.lang</em>, so the site opens in that language next time. It is never sent to us, and the game server never learns which language you use. Until you choose, the site reads your browser's language list to pick a first language; that stays in your browser too.</p>"""

PROFILE_STORAGE_NAME = "<p>So that you do not have to type your name again, your browser keeps the last display name you entered (an entry named <em>quoridor.username</em>) and fills it in the next time. Saving it sends nothing to us.</p>"

# {where}: the games that keep a score. Private rooms exist only where online play is offered.
PROFILE_STORAGE_SCORES = "<p>Games between two named players ({where}) are also counted in your browser, in an entry named <em>quoridor.scores</em>. This tally holds the two names, how many games each has won against the other, when you last played, and the identifiers of the last few games so that none is counted twice. It is used only to show the score between you and a friend. It never leaves your device, and your friend's browser keeps a tally of its own.</p>"
SCORES_WHERE_ONLINE = "in a private online room, or on one device when both players typed a name"
SCORES_WHERE_LOCAL = "on one device, when both players typed a name"

PROGRESS_STORAGE = "<p>To keep your score, rank and achievements, your browser keeps a tally of the games you finish, in an entry named <em>quoridor.progress</em>. It holds how many games you have played and won, how many walls you have placed, your best streaks, the last day you played, the points you have earned, and the achievements you have unlocked with the day you unlocked each one. It never contains your moves or your display name, and it is never sent to us. If you clear your site data, or press Reset progress on the Achievements page, your score, rank and achievements start over.</p>"

THEME_STORAGE = "<p>If you choose a theme with the theme switch in the menu, your browser keeps your choice (<em>light</em> or <em>dark</em>) in an entry named <em>quoridor.theme</em>, so the site opens in that theme next time. It is never sent to us.</p>"

TRANSLATION_NOTE = '<p class="small text-muted">This page can be read in other languages with the translate button. The translations are provided for convenience; if they differ from the English text, the English text applies.</p>'



def privacy():
    online = FEATURES["online"]
    eff_iso, eff_text = PRIVACY_EFFECTIVE
    toc = [
        ("information", "Information we collect and why"), ("logs", "Server logs, analytics and cookies"),
        ("storage", "Local storage in your browser"), ("third-parties", "Third-party services and embedded content"),
        ("rooms", "Multiplayer rooms, usernames and shared links"), ("retention", "Data retention and deletion"),
        ("children", "Children's privacy"), ("rights", "Your rights and applicable law"),
        ("contact", "Contact information"), ("updates", "Effective date and update history"),
    ]
    toc_html = "\n".join(f'<li><a href="#{i}">{t}</a></li>' for i, t in toc)
    if online:
        info_online = """<li><strong>Online play.</strong> To play online or in a private room you type a display name. Our game server holds that name, a random seat token that identifies your seat, your moves, the settings of the room's game (such as the variant or the board size), and the time you were last connected, for as long as the game or room exists. No account, email address or password is involved.</li>
<li><strong>Network address.</strong> Your IP address reaches our server with every request. The game server keeps it in memory for about a minute so it can limit abuse, such as creating rooms too fast.</li>"""
        storage_online = LANGUAGE_STORAGE + THEME_STORAGE + PROFILE_STORAGE_NAME + PROFILE_STORAGE_SCORES.format(where=SCORES_WHERE_ONLINE) + PROGRESS_STORAGE + """<p>When you create or join an online room, your browser stores a small entry under the name <em>quoridor.seat.</em> followed by the room's identifier. It contains your seat token, your seat number and the display name you chose. It lets you reload the page or recover from a dropped connection and keep your seat. The entry is removed when you leave the room. If you close the tab without leaving, it stays until you clear it, but it stops working once the room has expired.</p>
<p>While you search for an opponent, your browser also keeps the search ticket and your display name in <em>session storage</em> (an entry named <em>quoridor.search</em>) for that tab only. It lets the search carry on while you play the computer or open a private room, and lets the search page pick it up again after a reload. It is removed when the search ends and disappears when you close the tab.</p>"""
        rooms_html = """<h2 id="rooms">5. Multiplayer rooms, usernames and shared links</h2>
<ul>
<li><strong>Usernames are display names, not accounts.</strong> They are 2 to 20 characters. Please do not use your real name, your email address or anything else that identifies you. Two players may choose the same name.</li>
<li><strong>Who sees your name.</strong> The other players in your game see your display name. Anyone who opens a private-room invitation before it is full can also see the host's display name and which game the room is for.</li>
<li><strong>Shared links and codes act like keys.</strong> A private room is reached through a long random link and a short pairing code. Anyone who has the link or code while a seat is open can take that seat, so share it only with the person you want to play. Room pages ask search engines not to index them and are served so that the page address is not passed on to other sites.</li>
<li><strong>Matchmaking.</strong> If you ask to be matched with a stranger, your display name and a temporary ticket wait in a queue in the server's memory until an opponent is found. The ticket is dropped if your browser stops checking in for about 20 seconds. Your search can keep running while you play the computer or wait in a private room; if an opponent is found then, you are asked whether to join, and nothing starts unless you say yes within about 20 seconds. If you say no, you keep searching but are not offered that player again. If you do not answer, your search ends.</li>
<li><strong>No chat.</strong> There is no free-text chat between players, so the only text you share with an opponent is your display name.</li>
<li><strong>Everything is in memory.</strong> Rooms are not written to a database or to disk. If the game server restarts, active rooms are lost.</li>
</ul>"""
        retention_online = """<li><strong>Rooms and display names:</strong> deleted automatically. A room nobody has joined expires after 30 minutes. A finished game stays for up to 10 minutes so that either player can ask for a rematch. A room whose players have both left is deleted after about 5 minutes.</li>
<li><strong>Matchmaking tickets:</strong> dropped after about 20 seconds without a check-in, and in any case after 10 minutes.</li>
<li><strong>IP addresses used for abuse limiting:</strong> held in memory for about a minute.</li>
<li><strong>Seat token in your browser:</strong> removed when you leave the room. You can also delete it at any time through your browser's site-data settings.</li>"""
        rights_extra = "The data our game server holds about a game (a display name, a seat token and an IP address in memory) is deleted within minutes, so there is usually nothing left to give you, correct or erase by the time a request could be answered. "
    else:
        info_online = "<li><strong>Online play.</strong> Online play and private rooms are not available on this site at the moment, so no display names or seat tokens are collected. This policy will be updated before they are offered.</li>"
        storage_online = LANGUAGE_STORAGE + THEME_STORAGE + PROFILE_STORAGE_NAME + PROFILE_STORAGE_SCORES.format(where=SCORES_WHERE_LOCAL) + PROGRESS_STORAGE + "<p>Nothing else is stored in your browser's local storage. If online play is added later, this section will describe what it stores.</p>"
        rooms_html = """<h2 id="rooms">5. Multiplayer rooms, usernames and shared links</h2>
<p>Online play and private rooms are not available on this site at the moment, so no display names, rooms or invitation links exist. This policy will be updated before they are offered.</p>"""
        retention_online = ""
        rights_extra = ""
    storage_loss = ", and you cannot resume an online seat after a reload" if online else ""
    history_html = "".join(f'<li><time datetime="{d}">{t}</time>: {note}</li>' for d, t, note in PRIVACY_HISTORY)
    content = TRANSLATION_NOTE + f"""
<p>This policy explains what information Quoridor.online (&ldquo;we&rdquo;, &ldquo;us&rdquo;) handles when you visit the site, play Quoridor, or contact us. We keep it short because we collect very little: there are no accounts and no advertising, and the only analytics is Google Analytics on our public pages.</p>
<p><strong>In short:</strong> games against the computer and on one device stay in your browser; Google Analytics sets cookies to count visits (never on online-room pages); and the little that online play needs is kept in memory only, for minutes.</p>
<nav aria-label="On this page"><p><strong>On this page</strong></p>
<ol>
{toc_html}
</ol></nav>

<h2 id="information">1. Information we collect and why</h2>
<ul>
<li><strong>Playing against the computer or on one device.</strong> These games run entirely in your browser. Your moves are not sent to us or stored.</li>
{info_online}
<li><strong>Technical data from your visit.</strong> Like any website, our web server receives your IP address and basic details of each request. Section 2 explains how this is used.</li>
<li><strong>Messages you send us.</strong> If you write to us, we receive your message, your email address and anything else you include. Section 9 explains how.</li>
</ul>
<p>We use this information only to run the site and the game, keep it secure and working, prevent abuse, and answer you. We do not sell it, rent it, or use it for advertising or profiling, and we do not make automated decisions about you.</p>
<p>Where the law asks for a legal basis (for example under the GDPR), we rely on our legitimate interest in running and securing a free game site, and on your request when you contact us. This processing is minimal and short-lived.</p>

<h2 id="logs">2. Server logs, analytics and cookies</h2>
<ul>
<li><strong>Server logs.</strong> When your browser requests a page, our web server and hosting provider receive technical information such as your IP address, the date and time, the page or file requested, the response status and usually your browser and device type. Our own server logs record the request and IP address but replace room identifiers and matchmaking tickets with a placeholder, so a log cannot be used to enter a room. We use logs to keep the site secure and reliable and to investigate faults and abuse. They are kept only as long as needed for those purposes.</li>
<li><strong>Analytics.</strong> We use Google Analytics (Google tag) to understand how many people visit the site, which pages they read and how they arrive, so we can improve it. Google receives your IP address, your browser and device details, the page you viewed and where you came from, and reports aggregated statistics to us. We do not use it for advertising and we do not combine it with any other information about you. It is not loaded on online-room pages, so private room links are never sent to Google.</li>
<li><strong>Cookies.</strong> Google Analytics sets first-party cookies (named <code>_ga</code> and <code>_ga_</code> followed by an identifier) in your browser to tell visits apart. They are used only for these statistics. You can block or delete them in your browser settings, or install Google's <a href="https://tools.google.com/dlpage/gaoptout" rel="noopener noreferrer">browser opt-out add-on</a>; the site works the same without them. The site sets no other cookies. Section 3 describes the one other kind of browser storage it uses.</li>
</ul>

<h2 id="storage">3. Local storage in your browser</h2>
<p>Local storage is a small area of your browser where a site can keep data on your device. It is not sent to us with page requests.</p>
{storage_online}
<p>Local storage is used only to make the site work as you asked, never for tracking. If you block or clear it, the site still works; you just have to choose your language again, type your name again and start your scores over{storage_loss}.</p>

<h2 id="third-parties">4. Third-party services and embedded content</h2>
<ul>
<li><strong>Google Analytics.</strong> Public pages load Google's analytics script from Google servers, and Google processes the visit data described in section 2 under its own <a href="https://policies.google.com/privacy" rel="noopener noreferrer">privacy policy</a>. This may involve transferring data outside your country. Online-room pages load nothing from other companies.</li>
<li><strong>Nothing else from other companies is loaded.</strong> Apart from Google Analytics, pages load scripts, styles, fonts and images only from Quoridor.online itself, and the site's security headers block anything else. There are no embedded videos, social-media buttons or advertising scripts.</li>
<li><strong>Hosting.</strong> The site and its game server are run by hosting providers who process requests on our behalf, including the technical data in section 2. They act as our service providers and have their own policies for the logs they keep.</li>
<li><strong>Email.</strong> The form on the <a href="/contact/">contact page</a> does not send anything itself. It prepares a message in your own email app, and nothing is sent until you press send there. Your email provider and ours then handle that message under their own policies.</li>
<li><strong>Links to other sites.</strong> If you follow a link to another website, that site's own privacy policy applies.</li>
</ul>

{rooms_html}

<h2 id="retention">6. Data retention and deletion</h2>
<ul>
{retention_online}
<li><strong>Server logs:</strong> kept only as long as needed for security and fault-finding, then deleted.</li>
<li><strong>Emails to us:</strong> kept for as long as needed to answer you and keep a record of the conversation, then deleted. Ask us at any time to delete yours.</li>
<li><strong>Games against the computer and on one device:</strong> nothing is sent to us. Only the name and the tallies described in section 3 stay in your browser, until you clear them in your browser's site-data settings.</li>
</ul>
<p>Because the site has no accounts, we cannot look up data by name. To have information removed sooner, contact us (section 9) and tell us what you want removed, as precisely as you can.</p>

<h2 id="children">7. Children's privacy</h2>
<p>Quoridor is a family game, and the site needs no account or personal details. We do not knowingly collect personal information from children, and we do not direct advertising at anyone. Online play asks only for a display name. Children should pick a nickname rather than their real name and ask a parent or guardian before playing online. If you believe a child has given us personal information, contact us and we will delete it.</p>

<h2 id="rights">8. Your rights and applicable law</h2>
<p>Depending on where you live (for example in the European Economic Area, the United Kingdom or California), you may have the right to:</p>
<ul>
<li>ask whether we hold personal information about you and get a copy;</li>
<li>have inaccurate information corrected, or have your information deleted;</li>
<li>restrict or object to how your information is used, and receive it in a portable format where that applies;</li>
<li>withdraw consent where we relied on it; and</li>
<li>complain to your local data-protection authority.</li>
</ul>
<p>We do not sell or share personal information for advertising, and we will not treat you differently for exercising your rights. {rights_extra}To make a request, contact us as described in section 9. We may need details that let us find the data and confirm that it is yours, and we will reply within the time the law requires.</p>

<h2 id="contact">9. Contact information</h2>
<p>For questions about this policy or to make a privacy request, email <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> or use the <a href="/contact/">contact page</a>. Please do not include passwords or other sensitive details in your message.</p>

<h2 id="updates">10. Effective date and update history</h2>
<p>This policy is effective from <time datetime="{eff_iso}">{eff_text}</time>. When we change it, we update the date and add an entry below. If a change materially affects how your information is used, we will say so on the site before it takes effect.</p>
<ul>
{history_html}
</ul>"""
    return simple_page("/privacy-policy/", "Privacy Policy – Quoridor.online",
                       "How Quoridor.online handles your information: what we collect, cookies and browser storage, online rooms and usernames, retention, and your rights.",
                       "Privacy Policy", f"What we collect, what we don't, and how long we keep it. Effective {eff_text}.", content, "Privacy Policy")


TERMS_EFFECTIVE = ("2026-10-17", "17 October 2026")
TERMS_HISTORY = (
    ("2026-10-17", "17 October 2026", "First full version of these Terms of Use. It replaces the earlier draft placeholder."),
)


def terms():
    online = FEATURES["online"]
    eff_iso, eff_text = TERMS_EFFECTIVE
    toc = [
        ("acceptance", "Acceptance of the terms"), ("service", "Description of the website and its features"),
        ("acceptable-use", "Acceptable and prohibited use"), ("multiplayer", "Multiplayer behavior and room sharing"),
        ("availability", "Availability, interruptions and changes to the service"),
        ("intellectual-property", "Intellectual property and trademarks"),
        ("disclaimers", "Disclaimers and limitations"), ("third-parties", "Links to third-party services"),
        ("changes", "Changes to the terms"), ("contact", "Contact details and effective date"),
    ]
    toc_html = "\n".join(f'<li><a href="#{i}">{t}</a></li>' for i, t in toc)
    if online:
        service_online = """<li><strong>Online play.</strong> Play against another person after choosing a display name. No account is needed.</li>
<li><strong>Private rooms.</strong> Invite a specific friend with a link or a short pairing code.</li>"""
        multiplayer_html = """<h2 id="multiplayer">4. Multiplayer behavior and room sharing</h2>
<ul>
<li><strong>Display names.</strong> A name is 2 to 20 characters and is not an account, so it gives you no ownership of the name and two players may choose the same one. Choose a name you would be comfortable having shown to a stranger. Do not use a name that is offensive, hateful, sexually explicit or threatening, that impersonates another person or the site, or that reveals personal details such as your real name or email address.</li>
<li><strong>Conduct toward other players.</strong> Play fairly and respectfully. Do not harass others, and do not abandon games repeatedly to frustrate opponents.</li>
<li><strong>Shared links and codes act like keys.</strong> A private room is reached through a long random link and a short pairing code. Anyone who has the link or code while a seat is open can take that seat. You are responsible for sharing it only with the person you want to play, and for any use made of a link or code you share publicly.</li>
<li><strong>Invitations expire.</strong> An invitation expires after 30 minutes if nobody joins. Rooms and their state are not kept after play ends.</li>
<li><strong>Disconnection and forfeit.</strong> If a player's connection is lost for more than a minute during an online game, that player forfeits and the opponent wins. Leaving or resigning mid-game also counts as a forfeit. A player who does not move within the time limit has a move played for them by the server. After a game, either player may ask for a rematch, and the first move then passes to the other player.</li>
<li><strong>We may act on misuse.</strong> We may end a game, remove a room or display name, or block access to online play for anyone who breaks these terms or abuses the service, without notice where that is needed to protect the service or other players.</li>
</ul>"""
    else:
        service_online = '<li><strong>Online play and private rooms.</strong> These are not available at the moment. These terms will be updated before they are offered.</li>'
        multiplayer_html = """<h2 id="multiplayer">4. Multiplayer behavior and room sharing</h2>
<p>Online play and private rooms are not available on this site at the moment. Before they are offered, this section will be updated to cover display names, conduct toward other players, the sharing of room links and codes, and what happens when a player disconnects or forfeits.</p>"""
    history_html = "".join(f'<li><time datetime="{d}">{t}</time>: {note}</li>' for d, t, note in TERMS_HISTORY)
    content = TRANSLATION_NOTE + f"""
<p>These terms govern your use of Quoridor.online (&ldquo;we&rdquo;, &ldquo;us&rdquo;). They are short because the site is simple: you play Quoridor in your browser and read our guides, with no account to create.</p>
<p><strong>In short:</strong> use the site fairly and lawfully, be considerate to other players, understand that it is a free service provided as is, and remember that Quoridor.online is independent of the game's designer and publisher.</p>
<nav class="toc" aria-label="On this page"><h2 id="on-this-page">On this page</h2>
<ol>
{toc_html}
</ol></nav>

<h2 id="acceptance">1. Acceptance of the terms</h2>
<p>By visiting or using Quoridor.online you agree to these Terms of Use. Please also read our <a href="/privacy-policy/">Privacy Policy</a>, which explains how information is handled. If you do not agree to these terms, please do not use the site.</p>
<p>The site is meant for everyone who enjoys the game. If you are a child, please ask a parent or guardian before playing online. If you are using the site on behalf of an organization, you confirm that you may agree to these terms for it.</p>

<h2 id="service">2. Description of the website and its features</h2>
<p>Quoridor.online is a free website where you can play the board game Quoridor and learn how it works. Depending on what is available at the time, it offers:</p>
<ul>
<li><strong>Play against the computer</strong> at several difficulty levels, running in your browser.</li>
<li><strong>Play on one device,</strong> where two players share a screen and take turns.</li>
{service_online}
<li><strong>Guides,</strong> including how to play, the full rules and strategy.</li>
</ul>
<p>We describe a feature as available only once it works. The site needs no account, and we may add, change or remove features over time.</p>

<h2 id="acceptable-use">3. Acceptable and prohibited use</h2>
<p>You may use the site for your own personal, non-commercial enjoyment and learning. You agree not to:</p>
<ul>
<li>break any law, or use the site to harm, harass, threaten or deceive anyone;</li>
<li>attack, overload or disrupt the site or its game server, including by flooding it with requests or creating rooms in bulk;</li>
<li>probe for or exploit security weaknesses, or try to reach another player&rsquo;s seat, room or data;</li>
<li>use bots, scripts or other automated tools to play online games, to queue for matches or to scrape the site, other than ordinary search-engine crawling;</li>
<li>cheat, for example by modifying the game or tampering with requests in a way that defeats the fairness of an online game;</li>
<li>copy, resell or sell access to the site, or present our software, text or design as your own; or</li>
<li>use the site in any way that interferes with other people&rsquo;s enjoyment of it.</li>
</ul>
<p>You are free to link to the site and to play with friends. If you believe you have found a security problem, please tell us through the <a href="/contact/">contact page</a> rather than exploiting it.</p>

{multiplayer_html}

<h2 id="availability">5. Availability, interruptions and changes to the service</h2>
<p>We aim to keep the site running, but we do not promise that it will always be available, fast, secure or free of errors. The site may be interrupted for maintenance, updates, hosting problems or reasons outside our control, and we may change, suspend or end any feature, or the whole service, at any time.</p>
<p>Games are not guaranteed to survive an interruption. Games against the computer and on one device live only in your browser, and active online rooms are kept in memory and are lost if the game server restarts. Please do not rely on the site for anything that cannot be lost.</p>

<h2 id="intellectual-property">6. Intellectual property and trademarks</h2>
<p>The software, text, guides, graphics, board and design of Quoridor.online are our own work and are protected by copyright and other laws. You may play the game, read the guides, and share links to the site. Beyond that, please do not copy, adapt or distribute them without our written permission, except where the law allows it.</p>
<p>Quoridor was designed by Mirko Marchesi and is published by Gigamic. &ldquo;Quoridor&rdquo; and any related names, logos and trademarks belong to their respective owners. Quoridor.online is an independent website. It is not affiliated with, sponsored by or endorsed by the designer or publisher of the board game, and any use of their names is only to credit and identify the game. If you would like a physical set, it is available from its publisher and from game retailers.</p>
<p>If you send us feedback or suggestions, you allow us to use them to improve the site without owing you anything for them.</p>

<h2 id="disclaimers">7. Disclaimers and limitations</h2>
<p>To the extent permitted by applicable law:</p>
<ul>
<li>The site is provided <strong>&ldquo;as is&rdquo; and &ldquo;as available&rdquo;</strong>, without warranties of any kind, whether express or implied, including that it will be uninterrupted, error-free, secure, or suitable for a particular purpose.</li>
<li>The guides are for general learning and enjoyment. The computer opponent can make poor moves, and we do not promise that any rule explanation or game result is free of mistakes.</li>
<li>We are not liable for any indirect, incidental or consequential loss, or for loss of data, games, profits or goodwill, arising from your use of, or inability to use, the site. Our total liability for any claim relating to the site is limited to the amount you paid us to use it, which is nothing for a free service.</li>
<li>We are not responsible for what other players do, or for what happens if you share a room link or code with someone else.</li>
</ul>
<p>Nothing in these terms excludes or limits any right or liability that cannot be excluded or limited by law, including liability for death or personal injury caused by negligence, for fraud, and any mandatory consumer rights you have where you live.</p>

<h2 id="third-parties">8. Links to third-party services</h2>
<p>The site may link to other websites, such as the publisher of the game, retailers, or services you use to email us. We do not control those sites and are not responsible for their content, availability, policies or practices. A link is not an endorsement. Their own terms and privacy policies apply when you use them.</p>

<h2 id="changes">9. Changes to the terms</h2>
<p>We may update these terms as the site changes or as the law requires. When we do, we will change the effective date below and add an entry to the update history. If a change materially affects your rights, we will say so on the site before it takes effect. Your continued use of the site after a change means you accept the updated terms. If you do not accept them, please stop using the site.</p>

<h2 id="contact">10. Contact details and effective date</h2>
<p>For questions about these terms, email <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> or use the <a href="/contact/">contact page</a>.</p>
<p>These terms are effective from <time datetime="{eff_iso}">{eff_text}</time>.</p>
<ul>
{history_html}
</ul>"""
    return simple_page("/terms/", "Terms of Use – Quoridor.online",
                       "The terms for using Quoridor.online: acceptable use, multiplayer conduct and room sharing, availability, intellectual property, disclaimers and how the terms change.",
                       "Terms of Use", f"The rules for using Quoridor.online. Effective {eff_text}.", content, "Terms of Use")


def achievements():
    """The player's score, rank and achievements. Drawn in the browser from what achievements.js keeps there, so the page has no
    content of its own to index."""
    body = (
        page_head(
            "Achievements",
            "Earn points and ranks as you play: win games, build streaks and try every way to play. Your progress is kept in this browser.",
            [("Achievements", None)],
        )
        + """
<div class="container pad-page">
  <div data-achievements></div>
  <p class="visually-hidden" role="status" aria-live="polite" data-ach-status></p>
  <noscript><p class="notice">Your achievements are kept in your browser and need JavaScript to be shown.</p></noscript>
</div>"""
    )
    return Page(
        path="/achievements/", title="Achievements and Rank – Quoridor.online",
        description="See your Quoridor score, rank and achievements. Your progress is saved in your browser only.",
        body=body, indexable=False, robots="noindex, follow", breadcrumbs=[("Achievements", "/achievements/")],
        scripts=PROGRESS_SCRIPTS,
    )


def not_found():
    links = [("Home", "/", "Start from the beginning."),
             ("How to Play", "/how-to-play-quoridor/", "Learn the basics in a few minutes."),
             ("Rules", "/quoridor-rules/", "The full rules, step by step."),
             ("Strategy", "/quoridor-strategy/", "Tips for winning more games.")]
    link_cards = "".join(
        f'<li><a class="card notfound-link" href="{href}"><strong>{label}</strong><span class="text-muted">{blurb}</span></a></li>'
        for label, href, blurb in links)
    body = f"""
<div class="container notfound">
  {board_svg([("h",5,3),("h",5,5),("v",6,3),("v",6,4)], [(7,4,"p1")], "Quoridor pawn blocked by walls. A cyan pawn enclosed by indigo barriers, unable to move forward.", goal_tint=False)}
  <h1>This Page Couldn't Be Found</h1>
  <p class="lead">It may have moved, or the link might have a typo. No harm done: even the best pawn gets blocked sometimes. Pick a way back below.</p>
  <div class="btn-row">
    <a class="btn btn--primary btn--lg" href="/play/">{icon('arrow')} Play Quoridor</a>
  </div>
  <nav class="notfound-nav" aria-labelledby="notfound-h">
    <h2 id="notfound-h" class="h-sm">Or head somewhere useful</h2>
    <ul>{link_cards}</ul>
  </nav>
</div>"""
    return Page(path="/404/", title="Page Not Found | Quoridor Online", description="This page could not be found. Play Quoridor or browse the rules, strategy and how-to-play guides.",
                body=body, indexable=False, robots="noindex, follow", canonical=False, out_file="404.html", http_status=404)


def all_pages():
    return [
        home(), play_hub(), play_online(), play_computer(), play_local(), create_room(), join_room(), room(),
        variants_hub(), wallrush(), pointrush(), custom_game(), achievements(),
        how_to_play(), rules(), strategy(), board_game(), about(), contact(), privacy(), terms(), not_found(),
    ]
