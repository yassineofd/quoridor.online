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
        ("online", "online", "globe", "Play Online", "Play Online",
         "Play Quoridor online against another person. Choose a username, no registration, and enter matchmaking. Want to play a specific friend? Use a private room.",
         "Play Quoridor online against another person. Choose a username, no registration, and enter matchmaking. Want to play a specific friend? Use a private room.",
         "/play/online/", "Play Online"),
        ("computer", "robot", "bot", "Play Against Robot", "Play Against the Computer",
         "Practice against the computer. Pick Easy, Medium, Hard or Expert, from gentle for beginners to a tougher test. No registration needed.",
         "Practice against the computer. Pick Easy, Medium, Hard or Expert, from gentle for beginners to a tougher test. No registration needed.",
         "/play/computer/", "Play vs Robot"),
        ("local", "local", "users", "Play With a Friend", "Play Locally",
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


def private_strip(tag="h2"):
    return f"""
<div class="private-strip">
  <span class="icon-badge private-strip__icon">{icon('users')}</span>
  <div class="private-strip__body">
    <p class="eyebrow">Private match</p>
    <{tag}>Play privately with a friend</{tag}>
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
    rel = "".join(f'<li><a href="{p}"><strong>{l}</strong></a>: {b}</li>' for l, p, b in related)
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
    <aside class="related" aria-labelledby="related-h">
      <h2 id="related-h">Keep learning</h2>
      <ul>{rel}</ul>
    </aside>
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
    <div class="card"><h3>Why the walls matter</h3><p class="text-muted">A good wall costs you one turn but costs your opponent several. Judging that trade, again and again, is the whole game.</p>{board_svg([("h",3,2),("h",3,4),("v",4,3)], [(5,3,"p1"),(3,3,"p2")], "A small cluster of indigo barriers forcing a white ring pawn to take a detour around the walls.")}</div>
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
def play_hub():
    def status(k, label):
        return f"<tr><td>{label}</td><td>{'Available' if FEATURES[k] else 'Coming soon'}</td></tr>"

    body = (
        page_head(
            "Play Quoridor Game Online",
            "Choose how you want to play: online against another person, against the computer at your own level, or side by side on one device.",
            [("Play", None)],
        )
        + f"""
<section class="section--tight"><div class="container">
  <div class="section-head"><h2>Choose a mode</h2></div>
  {mode_cards('h3')}
</div></section>
<section class="section--tight"><div class="container">{private_strip('h2')}</div></section>
<section class="section"><div class="container grid grid--2">
  <div>
    <h2>Current status</h2>
    <p class="text-muted">We only list a mode as available once it works, so you can see where each one stands.</p>
    <div class="table-wrap article"><table><thead><tr><th scope="col">Mode</th><th scope="col">Status</th></tr></thead><tbody>
      {status('online', 'Play online')}{status('rooms', 'Private rooms')}{status('computer', 'Play against robot')}{status('local', 'Play with a friend (same device)')}
    </tbody></table></div>
  </div>
  <div>
    <h2>New to Quoridor?</h2>
    <p class="text-muted">The rules take about two minutes to read. Start with the <a href="/how-to-play-quoridor/">beginner's guide to how to play Quoridor</a>, check the <a href="/quoridor-rules/">full rules</a> for edge cases, and come back to <a href="/quoridor-strategy/">strategy</a> when you want to win more.</p>
  </div>
</div></section>
"""
    )
    return Page(
        path="/play/",
        title="Play Quoridor Game Online: Choose a Mode",
        description="Choose how to play Quoridor: online against another person, against the computer at four difficulty levels, or with a friend on the same device.",
        body=body, breadcrumbs=[("Play", "/play/")], nav_key="play",
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


GAME_SCRIPTS = ["/assets/js/engine.js", "/assets/js/icons.js", "/assets/js/board.js", "/assets/js/game.js"]


def stage(form_kind, panel_html, board_label, walls=(), pawns=(), live=False):
    return f"""
<div class="container stage" data-stage>
  <div class="stage-panel">
    <form data-play-form="{form_kind}" data-live="{'true' if live else 'false'}" novalidate>{panel_html}</form>
  </div>
  <div class="stage-board">{board_svg(walls, pawns, board_label)}</div>
</div>
<div class="container game-wrap" data-game-wrap hidden><div data-game-host></div></div>"""


MODE_WALLS = [("h", 3, 3), ("v", 5, 5), ("h", 6, 1)]
MODE_PAWNS = [(8, 4, "p1"), (0, 4, "p2")]


def mode_page(path, title, desc, h1, lead, crumb, form_kind, panel, label, indexable=None, scripts=(), live=False):
    idx = INDEX_MODE_PAGES if indexable is None else indexable
    parent = [("Play", "/play/")] if path.startswith("/play/") else []
    body = (
        '<div class="page-head"><div class="container">'
        + crumbs(parent + [(crumb, None)])
        + f"<h1>{h1}</h1><p class=\"lead\">{lead}</p></div></div>"
        + stage(form_kind, panel, label, MODE_WALLS, MODE_PAWNS, live)
    )
    return Page(
        path=path, title=title, description=desc, body=body,
        indexable=idx, robots=None if idx else "noindex, follow",
        breadcrumbs=parent + [(crumb, path)], scripts=list(scripts) + ["/assets/js/online.js", "/assets/js/play.js"], nav_key="play",
    )


def play_online():
    live = FEATURES["online"]
    searching = f"""
<div class="search-state" data-searching hidden>
  <div class="search-line" role="status" aria-live="polite">
    <span class="spinner" aria-hidden="true"></span><span data-search-text>Looking for an opponent&hellip;</span><span class="search-elapsed" data-search-elapsed></span>
  </div>
  <div class="btn-row"><button class="btn btn--secondary" type="button" data-cancel-search>Cancel search</button></div>
  <div data-slow hidden>
    <p class="small text-muted mt-4">Still looking. There may be nobody else searching right now. Keep waiting, or:</p>
    <div class="btn-row"><a class="btn btn--secondary" href="/play/computer/">Play the robot</a><a class="btn btn--secondary" href="/play/create-room/">Create a private room</a></div>
  </div>
</div>"""
    panel = (
        '<div class="status-line"><span class="status-dot' + (' status-dot--ok' if live else '') + '" aria-hidden="true"></span><span>'
        + ("Matchmaking status: ready" if live else "Matchmaking status: not connected") + '</span></div>'
        + username_field()
        + '<button class="btn btn--primary btn--lg btn--block" type="submit">Find an opponent</button>'
        + (searching + server_error() if live else
           unavailable("Online matchmaking isn't live yet", "There is no matchmaking server on this site yet, so nobody can be paired with you. Nothing was sent anywhere."))
        + '<p class="small text-muted mt-4">Want to play one specific person? Try a private room: <a href="/play/create-room/">create a room</a> or <a href="/play/join-room/">join a room</a>.</p>'
    )
    return mode_page(
        "/play/online/", "Play Quoridor Online Against Another Player",
        "Play Quoridor online against another person. Pick a username, enter matchmaking and start a synchronized game.",
        "Play Quoridor online", "Pick a username, find an opponent, and play a live game against another person.",
        "Play online", "online", panel, "Quoridor board preview for online play.", live=live,
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
        "Play against robot", "computer", panel, "Quoridor board preview for a game against the computer.",
        scripts=["/assets/js/engine.js", "/assets/js/ai.js"] + GAME_SCRIPTS[1:],
    )


def name_field(n):
    return f"""
<div class="field">
  <label for="name{n}">Player {n} name (optional)</label>
  <input class="input" id="name{n}" name="name{n}" type="text" maxlength="20" autocomplete="off" spellcheck="false" aria-describedby="name{n}-error">
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
        "Play with a friend", "local", panel, "Quoridor board preview for a two-player game on one device.",
        scripts=GAME_SCRIPTS,
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
        "/play/create-room/", "Create a Private Quoridor Room",
        "Create a private Quoridor room and share the invitation link or pairing code with a friend.",
        "Create a private room", "Make a room, then share the invitation link or pairing code with your friend.",
        "Create a room", "create-room", panel, "Quoridor board preview for a private room.", indexable=False, live=live,
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
        "Join a room", "join-room", panel, "Quoridor board preview for joining a private room.", indexable=False, live=live,
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

    waiting = state("waiting", f"""
<h1 tabindex="-1">Waiting for your opponent</h1>
<div class="status-line" role="status"><span class="status-dot status-dot--wait" aria-hidden="true"></span><span>Waiting for a second player to join. Connected as host.</span></div>
<h2 class="h-sm">Invitation link</h2>
<div class="code-box"><div class="value" id="invite-link"></div><button class="btn btn--secondary" type="button" data-copy="invite-link">{icon('copy')} Copy link</button></div>
<h2 class="h-sm">Pairing code</h2>
<div class="code-box"><div class="value value--big" id="invite-code"></div><button class="btn btn--secondary" type="button" data-copy="invite-code">{icon('copy')} Copy code</button></div>
<p class="small text-muted" id="copy-status" role="status" aria-live="polite"></p>
<div class="btn-row room-actions"><button class="btn btn--secondary" type="button" data-leave>{icon("x")} Cancel room</button></div>""")

    join = state("join", f"""
<h1 tabindex="-1">Join this room</h1>
<p class="text-muted"><strong id="host-name">Your friend</strong> invited you to play Quoridor. Choose a username to join.</p>
<form novalidate>
{username_field('2 to 20 characters. Your opponent will see this name.')}
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
        + msg("full", "This room is full", "Two players are already in this room. You can create your own room instead.")
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
        canonical=False, scripts=GAME_SCRIPTS + ["/assets/js/online.js", "/assets/js/room.js"],
        out_file="room/index.html", generic_social=True, nav_key="play",
    )


# ---------------------------------------------------------------- informational pages
SETUP_BOARD = board_svg([], [(8, 4, "p1"), (0, 4, "p2")],
    "A Quoridor board at the start of a game: a cyan pawn in the middle of the bottom edge and a white ring pawn in the middle of the top edge, with no walls placed.")
MID_BOARD = board_svg([("h", 3, 3), ("v", 4, 4), ("h", 5, 1), ("h", 2, 5)], [(5, 4, "p1"), (3, 4, "p2")],
    "A Quoridor game in progress: a cyan pawn and a white ring pawn face each other, with several indigo walls placed between squares.")
MOVE_BOARD = board_svg([("h", 4, 4)], [(5, 4, "p1"), (1, 4, "p2")],
    "A cyan pawn with dashed squares marked with arrows to the left, right and below it. The square above is not marked because an indigo wall blocks it.",
    marks=[(5, 3, "←"), (5, 5, "→"), (6, 4, "↓")])
JUMP_BOARD = board_svg([], [(5, 4, "p1"), (4, 4, "p2")],
    "A cyan pawn directly below a white ring pawn. The square directly above the white pawn is dashed and marked A: the cyan pawn can jump there.",
    marks=[(3, 4, "A")])
SIDESTEP_BOARD = board_svg([("h", 3, 4)], [(5, 4, "p1"), (4, 4, "p2")],
    "A cyan pawn directly below a white ring pawn with an indigo wall behind the white pawn. The squares to the left and right of the white pawn are dashed and marked A and B: the cyan pawn can move to either.",
    marks=[(4, 3, "A"), (4, 5, "B")])
WALL_BOARD = board_svg([("h", 2, 3), ("h", 2, 5)], [(6, 4, "p1"), (2, 4, "p2")],
    "Two indigo walls placed side by side in front of a white ring pawn. Together they cover four squares of the row below it, so the pawn must walk sideways around them.")
SEALED_BOARD = board_svg([("h", 0, 0)], [(8, 4, "p1"), (0, 0, "p2")],
    "A white ring pawn in the top-left corner under an indigo wall. A dashed red wall marked with a cross would close the only way out of that corner, so it is not allowed.",
    bad_walls=[("v", 0, 1)])
GOAL_BOARD = board_svg([], [(1, 4, "p1"), (7, 4, "p2")],
    "A cyan pawn one step from the top edge. Every square of the top row is dashed and ticked: reaching any of them wins.",
    marks=[(0, c, "✓") for c in range(9)])


OVERLAP_BOARD = board_svg([("h", 4, 3)], [(7, 4, "p1"), (1, 4, "p2")],
    "An indigo wall lies below the fifth row across the fourth and fifth columns. A dashed red wall marked with a cross would share the fifth column with it, so it is not allowed.",
    bad_walls=[("h", 4, 4)])
CROSS_BOARD = board_svg([("h", 4, 3)], [(7, 4, "p1"), (1, 4, "p2")],
    "An indigo wall lies across the board. A dashed red vertical wall marked with a cross would cross it at its middle point, so it is not allowed.",
    bad_walls=[("v", 4, 3)])
WALL_JUMP_BOARD = board_svg([("h", 4, 3)], [(5, 4, "p1"), (4, 4, "p2")],
    "A cyan pawn directly below a white ring pawn with an indigo wall between them. The three dashed squares left, right and below the cyan pawn are its only moves: it cannot jump the white pawn through the wall.",
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
             "Yes. Online games run in a mobile browser with nothing to install. In wall mode, tap a groove to select a wall, then press Place selected wall to confirm."),
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
<li><strong>Stay in Move pawn mode.</strong>The squares you can legally reach are highlighted. Walls and the board edge are already taken into account.</li>
<li><strong>Click or tap a highlighted square.</strong>Your pawn moves one square and the turn passes to your opponent. With a keyboard, use the arrow keys and Enter.</li>
</ol>"""
        timer_note = '<div class="callout"><p><strong>Watch the clock.</strong> Each turn has a 15-second timer, shown above the players. If it runs out, the server plays a pawn step along your shortest route for you, so you lose the chance to place a wall that turn.</p></div>'
    else:
        move_steps = """
<ol class="steps">
<li><strong>Wait for your turn.</strong>The turn bar shows whose go it is.</li>
<li><strong>Stay in Move pawn mode.</strong>The squares you can legally reach are highlighted.</li>
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
<li><strong>Press Place wall.</strong>The board switches to wall mode. Press Move pawn to go back.</li>
<li><strong>Pick a groove.</strong>Point at the board and the nearest groove shows a preview. Press Rotate wall to switch between across and up and down.</li>
<li><strong>Check that it's allowed.</strong>A wall can't overlap or cross another wall, and it can never take away a player's last route to their goal. If the preview isn't legal, a message under the buttons says why and the wall can't be placed.</li>
<li><strong>Place it.</strong>With a mouse, click the groove. On a touch screen, tap it to select it and then press Place selected wall. Your wall count goes down by one.</li>
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
<li><strong>Keep an eye on the timer.</strong>""" + ("Online turns last 15 seconds. Decide early, and keep the tab open so you don't forfeit by disconnecting." if online else "Each turn has a 15-second timer.") + """</li>
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


def strategy():
    sections = [
        ("pathfinding", "Efficient pathfinding", """
<p>Every decision in Quoridor comes down to one comparison: <strong>how many moves do I need to win, and how many does my opponent need?</strong> Count the shortest route for each pawn, taking walls and possible jumps into account.</p>
<p>If you're ahead on that count, moving usually keeps you ahead. If you're behind, you need a wall that changes the count in your favor.</p>"""),
        ("walls", "Offensive and defensive wall placement", """
<p>A wall is an <strong>offensive</strong> tool when it lengthens your opponent's route. It's <strong>defensive</strong> when it protects your own path, for example by occupying a groove your opponent could use to cut across your route.</p>
<ul>
<li>The best walls add <em>several</em> steps, not one. Look for spots where a pawn must backtrack along a corridor.</li>
<li>Walls work best <em>together</em>. Extending an existing wall or using the board edge can turn a small barrier into a long detour.</li>
<li>Remember that your opponent can walk around, so aim for walls that force the longest walk-around.</li>
</ul>"""),
        ("management", "Wall management", """
<p>You start with 10 walls and they're gone for good once placed. Treat them as a budget:</p>
<ul>
<li>Don't spend walls early just because you can.</li>
<li>Running out of walls leaves you unable to respond if your opponent starts to pull ahead.</li>
<li>Walls your opponent hasn't used are a threat: you must always consider what they could do next turn.</li>
</ul>"""),
        ("timing", "Timing decisions", """
<p>A wall is more valuable when it comes at the right moment. Placing it <em>after</em> your opponent has committed to a route often costs them more than placing it before. On the other hand, waiting too long can mean a good wall spot disappears or the game is already lost.</p>
<p>A useful habit: before placing any wall, ask whether you could place the same wall <em>next</em> turn at no extra cost. If you can, take the step now instead.</p>"""),
        ("mistakes", "Common mistakes", """
<ul>
<li><strong>Walling for one step.</strong> A wall that adds a single step usually costs you a turn and a wall for no net gain.</li>
<li><strong>Ignoring your own path.</strong> Strong walls can be turned against you by a later wall.</li>
<li><strong>Using walls too early.</strong> Few walls left means few options late in the game.</li>
<li><strong>Forgetting jumps.</strong> The opponent's pawn can change where your path runs, so recount often.</li>
<li><strong>Never moving.</strong> Walls slow your opponent but only moving wins the game.</li>
</ul>"""),
        ("levels", "Beginner and advanced considerations", """
<h3>If you're a beginner</h3>
<ul><li>Learn to count both routes before every move.</li><li>Prefer moving when you're ahead.</li><li>Practice spotting walls that add three or more steps.</li></ul>
<h3>As you improve</h3>
<ul><li>Plan sequences of walls that combine into long corridors.</li><li>Think about where the opponent's pawn will be, not only where it is.</li><li>Use pawn positions to create jump or block opportunities.</li></ul>
<p class="small text-muted">These are general rules of thumb rather than proven optimal play. Test them against real opponents.</p>"""),
    ]
    return article_page(
        "/quoridor-strategy/", "Quoridor Strategy: Pathfinding, Walls & Timing",
        "Improve at Quoridor with strategy for shortest paths, offensive and defensive walls, wall management, timing, and common mistakes.",
        "Quoridor strategy",
        "How to think about the race, when walls are worth it, and which mistakes to avoid.",
        sections,
        [("Quoridor rules", "/quoridor-rules/", "check the exact wall restrictions."),
         ("How to play Quoridor", "/how-to-play-quoridor/", "start here if you're brand new."),
         ("The Quoridor board game", "/quoridor-board-game/", "more about the game itself.")],
        "Quoridor strategy", "strategy",
    )


def board_game():
    sections = [
        ("what", "What the Quoridor board game is", """
<p>Quoridor is an abstract strategy board game for two or four players. There are no dice, cards or hidden information: both players see everything, so the result depends on planning. It was designed by Mirko Marchesi and published by Gigamic.</p>
<p class="small text-muted">Quoridor Online is an independent website. It is not affiliated with or endorsed by the game's designer or publisher.</p>"""),
        ("components", "Board layout and components", """
<p>A standard set contains a 9×9 board with grooves between the squares, four pawns and twenty walls. In a two-player game each player uses one pawn and ten walls. Pawns start at the middle of opposite edges.</p>
<p>For the exact step-by-step rules, see the <a href="/quoridor-rules/">Quoridor rules</a>.</p>"""),
        ("challenge", "The central strategic challenge", """
<p>The game is a race with a twist. Moving gets you closer to winning, but walls change how far away the finish is for <em>both</em> players. Every turn is a trade-off between making progress and making your opponent's progress harder, and you only have a limited number of walls to spend.</p>"""),
        ("barriers", "How barriers shape movement", """
<p>Walls don't capture or remove anything. They only change the shape of the board, turning open squares into corridors and detours. Because a wall can never fully seal a path, a good barrier is one that makes the opponent's <em>shortest</em> route much longer than yours.</p>"""),
        ("modes", "Local, computer and online play", """
<div class="table-wrap"><table>
<thead><tr><th scope="col">Mode</th><th scope="col">What it's like</th></tr></thead>
<tbody>
<tr><td><strong>Local (same device)</strong></td><td>Two people share one screen and take turns, much like a physical board.</td></tr>
<tr><td><strong>Against the computer</strong></td><td>Solo practice at a chosen difficulty, any time.</td></tr>
<tr><td><strong>Online</strong></td><td>Play another person remotely, via matchmaking or a private room shared with a friend.</td></tr>
</tbody></table></div>
<p>See which modes are open on the <a href="/play/">Play Quoridor game online</a> page.</p>"""),
    ]
    return article_page(
        "/quoridor-board-game/", "Quoridor Board Game: Overview & How It Works",
        "What the Quoridor board game is: its components, the central strategic challenge, how walls shape movement, and how local, computer and online play differ.",
        "The Quoridor board game",
        "An overview of the game: what's in the box, why it's interesting, and the ways you can play it here.",
        sections,
        [("How to play Quoridor", "/how-to-play-quoridor/", "learn the game step by step."),
         ("Quoridor rules", "/quoridor-rules/", "the full rule reference."),
         ("Quoridor strategy", "/quoridor-strategy/", "improve your play.")],
        "Quoridor board game", "board",
    )


# ---------------------------------------------------------------- static and legal pages
def simple_page(path, title, desc, h1, lead, content, trail):
    body = page_head(h1, lead, [(trail, None)]) + f'<div class="container pad-page"><div class="article prose">{content}</div></div>'
    return Page(path=path, title=title, description=desc, body=body, breadcrumbs=[(trail, path)], nav_key=("about" if path == "/about/" else None))


def about():
    status = (
        "You can play Quoridor in the browser."
        if ANY_MODE_LIVE
        else "The game modes are still being built. For now you can read the rules, the beginner's guide and the strategy guide."
    )
    content = f"""
<h2>Our purpose</h2>
<p>Quoridor Online is a simple, accessible place to play and learn the Quoridor strategy game in your browser, with no account needed.</p>
<h2>What we focus on</h2>
<ul>
<li>A clear, distraction-free board that works on phones, tablets and desktops.</li>
<li>Easy ways to start: online, against the computer, or with a friend on one device.</li>
<li>Honest, useful guides on <a href="/how-to-play-quoridor/">how to play Quoridor</a>, the <a href="/quoridor-rules/">rules</a> and <a href="/quoridor-strategy/">strategy</a>.</li>
</ul>
<h2>Where things stand</h2>
<p>{status} We only describe a feature as available once it works.</p>
<h2>Independence</h2>
<p>Quoridor Online is an independent project. It isn't affiliated with or endorsed by the designer or publisher of the Quoridor board game.</p>
<p><a class="btn btn--primary" href="/play/">Play Now</a></p>"""
    return simple_page("/about/", "About Quoridor Online", "About Quoridor Online: an independent, browser-based home for the Quoridor strategy game.",
                       "About us", "An accessible, browser-based place for strategy gaming.", content, "About us")


def contact():
    content = f"""
<div class="callout"><p><strong>No public contact channel has been set up yet.</strong> This page shows how contact will be organized; it can't send messages yet.</p></div>
<h2 id="feedback">Feedback</h2>
<p>Ideas, suggestions or things you'd like to see. Helpful to include: the page or mode you mean and what you'd change.</p>
<h2 id="support">Technical support</h2>
<p>Something not working? Helpful to include: your device, browser and version, what you did, and what you expected to happen. Please don't send passwords or personal data.</p>
<h2 id="business">Business inquiries</h2>
<p>Partnerships, press and other business matters. Helpful to include: who you are, your organization and what you propose.</p>"""
    return simple_page("/contact/", "Contact Quoridor Online", "How to contact Quoridor Online for feedback, technical support or business inquiries.",
                       "Contact us", "Feedback, technical support and business inquiries.", content, "Contact us")


ONLINE_FACTS = """
<li><strong>Online games and private rooms</strong> use a game server. It keeps in memory (not on disk) the display name you type, a random seat token, and when you last contacted it, for as long as the room exists. Rooms are deleted shortly after a game ends or both players leave, and an unjoined room expires after 30 minutes.</li>
<li>Your browser keeps the seat token in its local storage so that a reload can rejoin your seat. It is removed when you leave the room.</li>
<li>Network addresses are held in memory for about a minute to limit abuse.</li>
<li>The site sets no cookies and loads no analytics or third-party scripts.</li>"""


def privacy():
    online_facts = ONLINE_FACTS if FEATURES["online"] else "<li>Online play is not available on this site, so no names or network addresses are collected.</li>"
    content = f"""
<div class="callout callout--draft"><p><strong>Draft placeholder.</strong> This is not the final privacy policy. The final text must be written from how the live service actually works and reviewed for the laws that apply.</p></div>
<h2>How the software works today</h2>
<p>These are facts about the current software, written down so that the final policy can be checked against them.</p>
<ul>
<li><strong>Same-device and computer games</strong> run entirely in your browser. Nothing about those games is sent anywhere or stored.</li>
{online_facts}</ul>
<h2>What the final policy must cover</h2>
<ul>
<li>What data the service collects (for example usernames, connection data and logs) and why.</li>
<li>How private rooms are created, how long they exist and when they're deleted.</li>
<li>Analytics, cookies and similar storage, and whether consent is needed.</li>
<li>Third-party services such as hosting, content delivery and analytics.</li>
<li>How long data is kept, who can access it, and how people can exercise their rights.</li>
<li>How to contact us about privacy, and the date the policy took effect.</li>
</ul>"""
    return simple_page("/privacy-policy/", "Privacy Policy | Quoridor Online", "Privacy policy for Quoridor Online (draft placeholder).",
                       "Privacy policy", "How Quoridor Online handles information. Draft placeholder.", content, "Privacy policy")


ONLINE_TERMS_FACTS = """
<h2>How online games work today</h2>
<p>These are facts about the current software, written down so that the final terms can be checked against them.</p>
<ul>
<li>If a player's connection is lost for more than a minute during an online game, that player forfeits and the opponent wins.</li>
<li>Leaving or resigning mid-game counts as a forfeit. Either player may ask for a rematch after a game; the first move then passes to the other player.</li>
<li>An invitation (link and pairing code) expires after 30 minutes if nobody joins. Rooms and their state are not kept after play ends.</li>
<li>Usernames are display names, not accounts. Two players may choose the same name.</li>
</ul>"""


def terms():
    content = """
<div class="callout callout--draft"><p><strong>Draft placeholder.</strong> These are not the final terms. The final wording must reflect the real service and applicable requirements.</p></div>
""" + (ONLINE_TERMS_FACTS if FEATURES["online"] else "") + """<h2>What the final terms must cover</h2>
<ul>
<li>Who may use the service and how.</li>
<li>User responsibilities, including acceptable usernames and conduct toward other players.</li>
<li>Service availability, changes and interruptions.</li>
<li>What happens on disconnection or forfeit.</li>
<li>Intellectual property and the site's independence from the game's designer and publisher.</li>
<li>Limitation of liability, changes to the terms, and governing law.</li>
</ul>"""
    return simple_page("/terms/", "Terms of Use | Quoridor Online", "Terms of use for Quoridor Online (draft placeholder).",
                       "Terms of use", "The rules for using Quoridor Online. Draft placeholder.", content, "Terms of use")


def not_found():
    body = f"""
<div class="container notfound">
  {board_svg([("h",5,3),("h",5,5),("v",6,3),("v",6,4)], [(7,4,"p1")], "A cyan pawn enclosed by indigo barriers, unable to move forward.", goal_tint=False)}
  <h1>We couldn't find that page</h1>
  <p class="lead">The page you're looking for doesn't exist or has moved.</p>
  <div class="btn-row">
    <a class="btn btn--primary" href="/">Go to Home</a>
    <a class="btn btn--secondary" href="/play/">Go to Play</a>
  </div>
</div>"""
    return Page(path="/404/", title="Page not found | Quoridor Online", description="This page could not be found.",
                body=body, indexable=False, robots="noindex, follow", canonical=False, out_file="404.html", http_status=404)


def all_pages():
    return [
        home(), play_hub(), play_online(), play_computer(), play_local(), create_room(), join_room(), room(),
        how_to_play(), rules(), strategy(), board_game(), about(), contact(), privacy(), terms(), not_found(),
    ]
