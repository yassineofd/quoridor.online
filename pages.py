"""Page content for Quoridor Online. Each function returns a lib.Page; build.py renders the shared layout."""

from lib import (
    FEATURES, INDEX_MODE_PAGES, SITE_NAME, Page, icon, board_svg,
    HERO_WALLS, HERO_PAWNS, HERO_ALT,
)

ANY_MODE_LIVE = any(FEATURES[k] for k in ("online", "computer", "local"))


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


def mode_cards(heading_tag="h3"):
    h = heading_tag
    return f"""
<div class="grid grid--3 grid--modes">
  <article class="card mode-card mode-card--online">
    <span class="icon-badge">{icon('globe')}</span>
    <div class="mode-body">
      <{h}>Play Online</{h}>
      {badge('online')}
      <p>Play Quoridor online against another person. Choose a username, no registration, and enter matchmaking. Want to play a specific friend? Use a private room.</p>
    </div>
    <a class="btn btn--primary" href="/play/online/">Play Online {icon('arrow')}</a>
  </article>
  <article class="card mode-card mode-card--robot">
    <span class="icon-badge">{icon('bot')}</span>
    <div class="mode-body">
      <{h}>Play Against Robot</{h}>
      {badge('computer')}
      <p>Practice against the computer. Pick Easy, Medium, Hard or Expert, from gentle for beginners to a tougher test. No registration needed.</p>
    </div>
    <a class="btn btn--primary" href="/play/computer/">Play vs Robot {icon('arrow')}</a>
  </article>
  <article class="card mode-card mode-card--local">
    <span class="icon-badge">{icon('users')}</span>
    <div class="mode-body">
      <{h}>Play With a Friend</{h}>
      {badge('local')}
      <p>Two players, one device. You share the screen and take turns on the same board. Great for playing side by side.</p>
    </div>
    <a class="btn btn--primary" href="/play/local/">Play Together {icon('arrow')}</a>
  </article>
</div>"""


def private_strip(tag="h2"):
    return f"""
<div class="private-strip">
  <div>
    <{tag}>Play privately with a friend</{tag}>
    <p>Private matches are part of online play. Share a direct invitation link or a short pairing code so your friend can join your room.{' ' if FEATURES['rooms'] else ' Private rooms are coming soon.'}</p>
  </div>
  <div class="btn-row">
    <a class="btn btn--secondary" href="/play/create-room/">Create a Room</a>
    <a class="btn btn--secondary" href="/play/join-room/">Join a Room</a>
  </div>
</div>"""


def cta_panel(text="Ready to put it into practice?"):
    return f"""
<div class="card cta-panel">
  <h2>{text}</h2>
  <p>Choose a way to play Quoridor online, against the computer, or with a friend on one device.</p>
  <a class="btn btn--primary" href="/play/">Play Now {icon('arrow')}</a>
</div>"""


def article_page(path, title, description, h1, lead, sections, related, trail_label, nav_key, extra_after=""):
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
    {cta_panel()}
    <aside class="related" aria-labelledby="related-h">
      <h2 id="related-h">Keep learning</h2>
      <ul>{rel}</ul>
    </aside>
  </article>
</div>"""
    )
    return Page(path=path, title=title, description=description, body=body,
                breadcrumbs=[(trail_label, path)], nav_key=nav_key)


def figure(svg, caption):
    return f"<figure>{svg}<figcaption>{caption}</figcaption></figure>"


# ---------------------------------------------------------------- homepage
def home():
    live_note = (
        "Play against another person, the computer, or a friend on the same device."
        if ANY_MODE_LIVE
        else "Learn the rules and strategy now; online, computer and same-device play are being added."
    )
    features = [
        ("responsive", True, "layout", "Responsive design", "The site is built mobile-first and works from small phones to wide desktop monitors."),
        ("noaccount", True, "userx", "No account required", "Nothing on the site asks you to register. Modes that need a name just ask for a display name."),
        ("browser", ANY_MODE_LIVE, "smartphone", "Browser-based play", "Play in your browser with nothing to install."),
        ("modes", sum(FEATURES[k] for k in ("online", "computer", "local")) >= 2, "globe", "Different playing modes", "Play online, against the computer, or on one shared device."),
    ]
    live_items = "".join(
        f'<li>{icon(ic)}<div><strong>{t}</strong><span class="text-muted">{d}</span></div></li>'
        for _, ok, ic, t, d in features if ok
    )
    planned_items = "".join(f"<li>{t}</li>" for _, ok, _, t, _ in features if not ok)
    planned = (
        f'<div class="card planned"><h3>On the way</h3><p class="text-muted">These are planned but not available yet:</p><ul>{planned_items}</ul></div>'
        if planned_items else ""
    )

    faq = [
        ("What is the goal of Quoridor?",
         "Move your pawn to any square on the opposite side of the board before your opponent reaches yours. Each turn you either move your pawn or place a wall to slow your opponent down."),
        ("How many players are there?",
         "The standard game is for two players. The physical game also has a four-player version, but every mode planned for this site is a two-player game."),
        ("Can I block my opponent completely?",
         'No. A wall is only legal if both players still have at least one open route to their goal side. See the <a href="/quoridor-rules/">Quoridor rules</a> for the details.'),
        ("Which ways to play are there?",
         ("You can play online, against a computer opponent at four difficulty levels, or with a friend on the same device." if ANY_MODE_LIVE
          else "Three are planned: online against another person (with private rooms for friends), against a computer opponent at four difficulty levels, and with a friend on the same device. They are not live yet.")),
        ("Do I need an account?",
         "No. Nothing on the site requires an account. Where a mode needs a name, you pick a display name; it is not proof of identity."),
        ("How many walls does each player get?",
         "In a two-player game each player starts with 10 walls. Once they are used up, you can only move your pawn."),
    ]
    faq_html = "".join(
        f'<details><summary>{q}</summary><div class="answer"><p>{a}</p></div></details>' for q, a in faq
    )

    desc = (
        "Play Quoridor online against a friend, a computer opponent, or on one device. A free browser strategy game with no registration."
        if ANY_MODE_LIVE
        else "Quoridor online: learn the Quoridor game, study the rules and strategy, and choose online, computer or same-device play as each mode launches. No account needed."
    )
    body = f"""
<section class="hero" aria-labelledby="hero-h">
  <div class="container hero-grid">
    <div>
      <p class="eyebrow">Strategy board game</p>
      <h1 id="hero-h">Play the Quoridor game online</h1>
      <p class="lead">Race your pawn across a 9×9 board while placing walls to slow your opponent down. The goal is simple; outsmarting your opponent is the challenge. {live_note}</p>
      <div class="btn-row">
        <a class="btn btn--primary btn--lg" href="/play/">Play Now {icon('arrow')}</a>
        <a class="btn btn--secondary btn--lg" href="/how-to-play-quoridor/">How to Play</a>
      </div>
    </div>
    <div class="hero-board">{board_svg(HERO_WALLS, HERO_PAWNS, HERO_ALT)}</div>
  </div>
</section>

<section class="section--tight" aria-labelledby="modes-h">
  <div class="container">
    <div class="section-head">
      <h2 id="modes-h">Choose how to play</h2>
      <p class="text-muted">Three ways to play Quoridor online and offline. No account needed for any of them.</p>
    </div>
    {mode_cards('h3')}
  </div>
</section>

<section class="section--tight" aria-labelledby="private-h">
  <div class="container">{private_strip('h2').replace('<h2>', '<h2 id="private-h">', 1)}</div>
</section>

<section class="section" aria-labelledby="how-h">
  <div class="container grid grid--2">
    <div>
      <h2 id="how-h">How the game works</h2>
      <p class="text-muted">Quoridor is easy to learn and surprisingly deep. You win by reaching the opposite side of the board, and walls are your tool for making your opponent's trip longer than yours.</p>
      <ol class="steps">
        <li><strong>Race to the other side</strong>Your pawn starts at the middle of your edge and must reach any square on the far edge.</li>
        <li><strong>Move or block</strong>On each turn you either step your pawn one square or place a wall.</li>
        <li><strong>Never seal the path</strong>Walls can lengthen a route but never close it completely.</li>
      </ol>
      <div class="btn-row">
        <a class="btn btn--secondary" href="/how-to-play-quoridor/">How to play Quoridor</a>
        <a class="btn btn--secondary" href="/quoridor-rules/">Read the rules</a>
      </div>
    </div>
    <div class="card"><h3>Why the walls matter</h3><p class="text-muted">A good wall costs you one turn but costs your opponent several. Judging that trade, again and again, is the whole game.</p>{board_svg([("h",3,2),("h",3,4),("v",4,3)], [(5,3,"p1"),(3,3,"p2")], "A small cluster of indigo barriers forcing a white ring pawn to take a detour around the walls.")}</div>
  </div>
</section>

<section class="section" aria-labelledby="features-h">
  <div class="container">
    <div class="section-head"><h2 id="features-h">What this site offers</h2></div>
    <ul class="feature-list">{live_items}</ul>
    {planned}
  </div>
</section>

<section class="section" aria-labelledby="learn-h">
  <div class="container">
    <div class="section-head">
      <h2 id="learn-h">Learn Quoridor</h2>
      <p class="text-muted">Read first or learn as you play. Both guides are written for beginners.</p>
    </div>
    <div class="grid grid--2">
      <article class="card">
        <span class="icon-badge">{icon('book')}</span>
        <h3>Quoridor rules</h3>
        <p class="text-muted">Board setup, starting positions, legal moves and jumps, wall restrictions, and exactly what counts as a win.</p>
        <a href="/quoridor-rules/">Read the Quoridor rules</a>
      </article>
      <article class="card">
        <span class="icon-badge">{icon('target')}</span>
        <h3>Quoridor strategy</h3>
        <p class="text-muted">How to count paths, when to place walls, how to budget them, and the mistakes that cost beginners games.</p>
        <a href="/quoridor-strategy/">Explore Quoridor strategy</a>
      </article>
    </div>
  </div>
</section>

<section class="section" aria-labelledby="faq-h">
  <div class="container">
    <div class="section-head"><h2 id="faq-h">Frequently asked questions</h2></div>
    <div class="faq prose">{faq_html}</div>
  </div>
</section>
"""
    return Page(
        path="/",
        title="Quoridor Online: Play the Quoridor Game in Your Browser",
        description=desc,
        body=body,
        nav_key="home",
        schema=[{"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME}],
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


def username_field(note="2 to 20 characters. This is a display name, not an account."):
    return f"""
<div class="field">
  <label for="username">Username</label>
  <input class="input" id="username" name="username" type="text" autocomplete="nickname" maxlength="20" required aria-describedby="username-hint username-error" spellcheck="false">
  <span class="hint" id="username-hint">{note}</span>
  <div class="field-error" id="username-error" role="alert" hidden></div>
</div>"""


def stage(form_kind, panel_html, board_label, walls=(), pawns=()):
    return f"""
<div class="container stage">
  <div class="stage-panel">
    <form data-play-form="{form_kind}" novalidate>{panel_html}</form>
  </div>
  <div class="stage-board">{board_svg(walls, pawns, board_label)}</div>
</div>"""


MODE_WALLS = [("h", 3, 3), ("v", 5, 5), ("h", 6, 1)]
MODE_PAWNS = [(8, 4, "p1"), (0, 4, "p2")]


def mode_page(path, title, desc, h1, lead, crumb, form_kind, panel, label, indexable=None):
    idx = INDEX_MODE_PAGES if indexable is None else indexable
    parent = [("Play", "/play/")] if path.startswith("/play/") else []
    body = (
        '<div class="page-head"><div class="container">'
        + crumbs(parent + [(crumb, None)])
        + f"<h1>{h1}</h1><p class=\"lead\">{lead}</p></div></div>"
        + stage(form_kind, panel, label, MODE_WALLS, MODE_PAWNS)
    )
    return Page(
        path=path, title=title, description=desc, body=body,
        indexable=idx, robots=None if idx else "noindex, follow",
        breadcrumbs=parent + [(crumb, path)], scripts=["/assets/js/play.js"], nav_key="play",
    )


def play_online():
    panel = (
        '<div class="status-line"><span class="status-dot" aria-hidden="true"></span><span>Matchmaking status: not connected</span></div>'
        + username_field()
        + '<button class="btn btn--primary btn--lg btn--block" type="submit">Find an opponent</button>'
        + unavailable("Online matchmaking isn't live yet", "There is no matchmaking server yet, so nobody can be paired with you. Nothing was sent anywhere.")
        + '<p class="small text-muted mt-4">Want to play one specific person? Try a private room: <a href="/play/create-room/">create a room</a> or <a href="/play/join-room/">join a room</a>.</p>'
    )
    return mode_page(
        "/play/online/", "Play Quoridor Online Against Another Player",
        "Play Quoridor online against another person. Pick a username, enter matchmaking and start a synchronized game.",
        "Play Quoridor online", "Pick a username, find an opponent, and play a live game against another person.",
        "Play online", "online", panel, "Quoridor board preview for online play.",
    )


def difficulty_choice(value, title, desc, checked=False):
    chk = " checked" if checked else ""
    return f"""
<div class="choice"><input type="radio" name="difficulty" id="d-{value}" value="{value}"{chk}>
  <label class="choice-body" for="d-{value}">
    <span class="check" aria-hidden="true">{icon('check')}</span>
    <span><span class="choice-title">{title}</span><span class="choice-state"> (selected)</span><br><span class="choice-desc">{desc}</span></span>
  </label></div>"""


def play_computer():
    levels = [
        ("easy", "Easy", "Good for learning the rules. Makes simple moves and is easy to out-plan.", False),
        ("medium", "Medium", "A relaxed game for players who know the basics.", True),
        ("hard", "Hard", "Plans further ahead and uses walls deliberately. Expect a real challenge.", False),
        ("expert", "Expert", "The strongest level we offer, best for experienced players.", False),
    ]
    choices = "".join(difficulty_choice(v, t, d, c) for v, t, d, c in levels)
    panel = (
        f'<fieldset class="fieldset"><legend>Difficulty</legend><div class="choice-group">{choices}</div></fieldset>'
        + '<p class="small text-muted">Level names describe the intended challenge. We will describe how each one actually plays once the computer opponent has been built and tested.</p>'
        + '<button class="btn btn--primary btn--lg btn--block" type="submit">Start game</button>'
        + unavailable("The computer opponent isn't ready yet", "There is no game engine yet, so a game can't start. Your difficulty choice was not saved or sent anywhere.")
    )
    return mode_page(
        "/play/computer/", "Play Quoridor Against the Computer",
        "Play Quoridor against a computer opponent. Choose Easy, Medium, Hard or Expert and start without registering.",
        "Play Quoridor against the computer", "Choose a difficulty and start a game. No registration needed.",
        "Play against robot", "computer", panel, "Quoridor board preview for a game against the computer.",
    )


def play_local():
    panel = (
        '<div class="card"><h2 class="h-sm">Two players, one device</h2>'
        '<p class="text-muted">You share the screen and take turns on the same board. The active player will always be named on screen, with a clear cue when the turn changes.</p>'
        '<ul class="text-muted"><li>Player 1 uses the filled cyan pawn.</li><li>Player 2 uses the white ring pawn.</li><li>Pass the device after each move.</li></ul></div>'
        '<div class="spacer"></div>'
        '<button class="btn btn--primary btn--lg btn--block" type="submit">Start game</button>'
        + unavailable("The shared-device game isn't ready yet", "There is no game engine yet, so a game can't start.")
    )
    return mode_page(
        "/play/local/", "Play Quoridor With a Friend on One Device",
        "Play a two-player Quoridor game on the same device. Share the screen and take turns.",
        "Play Quoridor with a friend", "Share one screen and take turns on the same board.",
        "Play with a friend", "local", panel, "Quoridor board preview for a two-player game on one device.",
    )


def create_room():
    panel = (
        username_field("2 to 20 characters. Your friend will see this name.")
        + '<button class="btn btn--primary btn--lg btn--block" type="submit">Create room</button>'
        + unavailable("Private rooms aren't live yet", "There is no room server yet, so no room was created and no link or code was generated.")
        + """<h2 class="h-sm mt-6">What happens next</h2>
<ol class="text-muted"><li>You get an invitation link and a short pairing code.</li><li>Copy either one and send it to your friend.</li><li>The match starts when both of you are in.</li></ol>
<p class="small"><a href="/room/EXAMPLE-ROOM-ID/?preview=waiting">Preview the waiting-room screen</a> (sample data)</p>"""
    )
    return mode_page(
        "/play/create-room/", "Create a Private Quoridor Room",
        "Create a private Quoridor room and share the invitation link or pairing code with a friend.",
        "Create a private room", "Make a room, then share the invitation link or pairing code with your friend.",
        "Create a room", "create-room", panel, "Quoridor board preview for a private room.", indexable=False,
    )


def join_room():
    panel = (
        username_field("2 to 20 characters. Your opponent will see this name.")
        + """<div class="field">
  <label for="code">Pairing code</label>
  <input class="input input--code" id="code" name="code" type="text" inputmode="text" autocomplete="off" autocapitalize="characters" maxlength="6" required aria-describedby="code-hint code-error" spellcheck="false">
  <span class="hint" id="code-hint">6 characters. Got an invitation link instead? Just open it.</span>
  <div class="field-error" id="code-error" role="alert" hidden></div>
</div>"""
        + '<button class="btn btn--primary btn--lg btn--block" type="submit">Join room</button>'
        + unavailable("Private rooms aren't live yet", "There is no room server yet, so the code can't be checked.")
        + '<p class="small mt-4">Preview other screens (sample data): <a href="/room/EXAMPLE-ROOM-ID/?preview=invalid">invalid code</a>, <a href="/room/EXAMPLE-ROOM-ID/?preview=full">room full</a>, <a href="/room/EXAMPLE-ROOM-ID/?preview=expired">expired invitation</a>.</p>'
    )
    return mode_page(
        "/play/join-room/", "Join a Private Quoridor Room",
        "Join a private Quoridor room with a pairing code or an invitation link.",
        "Join a private room", "Enter the pairing code your friend sent you, or open their invitation link.",
        "Join a room", "join-room", panel, "Quoridor board preview for joining a private room.", indexable=False,
    )


def room():
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
<div class="btn-row room-actions"><button class="btn btn--secondary" type="button" data-leave>Cancel room</button></div>""")

    join = state("join", f"""
<h1 tabindex="-1">Join this room</h1>
<p class="text-muted">You were invited to play Quoridor. Choose a username to join.</p>
<form data-play-form="room-guest" novalidate>
{username_field('2 to 20 characters. Your opponent will see this name.')}
<button class="btn btn--primary btn--lg btn--block" type="submit">Join room</button>
{unavailable("Private rooms aren't live yet", "There is no room server yet, so you can't be added to this room.")}
</form>""")

    starting = state("starting", """
<h1 tabindex="-1">Both players are in</h1>
<div class="status-line" role="status"><span class="status-dot status-dot--ok" aria-hidden="true"></span><span>Alex and Sam are connected. The game is about to start.</span></div>
<p class="text-muted">Sample screen. Who moves first will be shown here before play begins.</p>""")

    reconnecting = state("reconnecting", """
<h1 tabindex="-1">Reconnecting&hellip;</h1>
<div class="status-line" role="status"><span class="status-dot status-dot--wait" aria-hidden="true"></span><span>Connection lost. Trying to rejoin your seat automatically.</span></div>
<p class="text-muted">Your opponent can see that you're reconnecting. If you can't return within the grace period, the game ends as a forfeit.</p>
<div class="btn-row"><button class="btn btn--secondary" type="button" data-leave>Leave room</button></div>""")

    left = state("left", """
<h1 tabindex="-1">You left the room</h1>
<p class="text-muted">Your seat has been released.</p>
<div class="btn-row"><a class="btn btn--primary" href="/play/">Back to Play</a><a class="btn btn--secondary" href="/">Home</a></div>""")

    inner = (
        waiting + join + starting + reconnecting
        + msg("invalid", "That code doesn't match a room", "Check the code and try again, or ask your friend to send the invitation link again.")
        + msg("full", "This room is full", "Two players are already in this room. You can create your own room instead.")
        + msg("expired", "This invitation has expired", "Invitations only last for a limited time. Ask your friend for a new one, or create your own room.")
        + msg("unavailable", "This room isn't available", "Private rooms aren't live yet, so this link can't be opened. Nothing about this link was stored or checked.", "info", "notice")
        + left
    )
    body = f"""
<div class="container pad-room">
  <div class="stage-panel narrow">
    {inner}
    <p class="notice preview-note small" data-preview-note hidden role="note">{icon('info')}<span>Design preview with sample data. No room, link or opponent is real.</span></p>
  </div>
</div>"""
    return Page(
        path="/room/_/", title="Private room | Quoridor Online",
        description="Private Quoridor room.",
        body=body, indexable=False, robots="noindex, nofollow, noarchive",
        canonical=False, scripts=["/assets/js/play.js", "/assets/js/room.js"],
        out_file="room/index.html", generic_social=True, nav_key="play",
    )


# ---------------------------------------------------------------- informational pages
SETUP_BOARD = board_svg([], [(8, 4, "p1"), (0, 4, "p2")],
    "A Quoridor board at the start of a game: a cyan pawn in the middle of the bottom edge and a white ring pawn in the middle of the top edge, with no walls placed.")
MID_BOARD = board_svg([("h", 3, 3), ("v", 4, 4), ("h", 5, 1), ("h", 2, 5)], [(5, 4, "p1"), (3, 4, "p2")],
    "A Quoridor game in progress: a cyan pawn and a white ring pawn face each other, with several indigo walls placed between squares.")


def how_to_play():
    sections = [
        ("objective", "The goal of the game", """
<p>Quoridor is a game for two players. You win by being the first to get your pawn to <strong>any square on the opposite edge</strong> of the board. Your opponent is trying to do the same thing in the other direction.</p>
<p>The twist: on your turn you can <em>either</em> move your pawn <em>or</em> place a wall to make your opponent's journey longer. Deciding which to do each turn is the entire game.</p>"""),
        ("board", "Understanding the board", f"""
<p>The board is a 9×9 grid of 81 squares. Between squares there are thin grooves where walls can go. Each player has one pawn and, in a two-player game, <strong>10 walls</strong>.</p>
<p>Pawns start in the middle square of their own edge, facing each other across the board. Your goal row is the edge where your opponent starts.</p>
{figure(SETUP_BOARD, 'The starting position: each pawn on the middle square of its own edge. The cyan pawn is filled, the white one is a ring, so they differ by shape as well as color.')}"""),
        ("turns", "Player turns", """
<p>Players take turns, one action each. On your turn you must do exactly one of these:</p>
<ol><li><strong>Move your pawn</strong> one square, or</li><li><strong>Place one wall</strong> on the board.</li></ol>
<p>You can't pass. Players agree beforehand who moves first.</p>"""),
        ("movement", "Pawn movement", """
<p>A pawn moves one square at a time, up, down, left or right. No diagonal moves (apart from one special case below), and you can't move through a wall.</p>
<h3>Jumping your opponent</h3>
<p>If your opponent's pawn is right next to yours, you can jump straight over it to the square behind. If a wall (or the board edge) blocks that jump, you may instead step to a square beside the opponent's pawn, as long as no wall is in the way. The <a href="/quoridor-rules/#movement">Quoridor rules</a> spell this out precisely."""
        + "</p>"),
        ("barriers", "Using barriers", f"""
<p>A wall is two squares long and sits in the groove between squares, blocking movement across it. Walls are permanent: once placed, they can't be moved or removed.</p>
<p>You can't place a wall on top of another wall, and you can never place a wall that completely cuts a player off from their goal. Walls make routes <em>longer</em>, not impossible.</p>
{figure(MID_BOARD, 'Walls make paths longer: each pawn now has to walk around the barriers in front of it.')}"""),
        ("winning", "Winning the game", """
<p>The first player whose pawn reaches <strong>any square on the opposite edge</strong> wins immediately. There is no need to reach a particular square.</p>"""),
        ("tips", "Beginner guidance", """
<ul>
<li><strong>Count both routes.</strong> Before each move, ask: how many steps do I need, and how many does my opponent need?</li>
<li><strong>Don't spend walls too early.</strong> You only have 10, and a wall that costs your opponent one step is rarely worth a turn.</li>
<li><strong>Use walls that add several steps.</strong> The best walls force long detours.</li>
<li><strong>Keep moving.</strong> A game of only walls leaves you with no progress at all.</li>
</ul>
<p>When you're ready for more, read the <a href="/quoridor-strategy/">Quoridor strategy guide</a>.</p>"""),
    ]
    return article_page(
        "/how-to-play-quoridor/", "How to Play Quoridor: A Beginner's Guide",
        "Learn how to play Quoridor: the goal, the board, how pawns move and jump, how to place walls, and how to win.",
        "How to play Quoridor",
        "A friendly walkthrough for beginners: what you're trying to do, what you can do on your turn, and how a game is won.",
        sections,
        [("Quoridor rules", "/quoridor-rules/", "the precise rules, including every wall restriction."),
         ("Quoridor strategy", "/quoridor-strategy/", "tactics for getting ahead."),
         ("The Quoridor board game", "/quoridor-board-game/", "what the game is and where it comes from.")],
        "How to play Quoridor", "how",
    )


def rules():
    sections = [
        ("setup", "Board setup", f"""
<p>The board is a <strong>9×9 grid</strong> of 81 squares. Walls fit in the grooves between squares. In a two-player game each player has <strong>one pawn and 10 walls</strong>.</p>
{figure(SETUP_BOARD, 'Board setup with pawns on their starting squares and no walls placed.')}"""),
        ("starting", "Starting positions", """
<p>Each pawn starts on the <strong>middle square of its own edge</strong>. The two pawns face each other across the board. A player's goal is any square on the edge where the opponent started.</p>"""),
        ("turns", "Turn order", """
<p>Players alternate turns. On your turn you must do exactly one of the following:</p>
<ul><li>move your pawn, or</li><li>place one of your walls.</li></ul>
<p>Passing isn't allowed. Who goes first is agreed or decided by chance before the game begins. This site will always show who moves first.</p>"""),
        ("movement", "Legal movement", """
<ul>
<li>A pawn moves <strong>one square</strong> up, down, left or right.</li>
<li>A pawn can't move diagonally, except for the special jump case below.</li>
<li>A pawn can't pass through a wall or leave the board.</li>
</ul>
<h3>Jumping</h3>
<ul>
<li>If your opponent's pawn is on an adjacent square, you may <strong>jump straight over it</strong> to the square directly behind, provided no wall lies between you and them or between them and that square.</li>
<li>If a wall or the board edge blocks that straight jump, you may move to a square <strong>beside the opponent's pawn</strong> (diagonal from your starting square), provided no wall blocks that move.</li>
</ul>"""),
        ("walls", "Wall placement restrictions", """
<ul>
<li>A wall covers the width of <strong>two squares</strong>.</li>
<li>It must lie entirely on the board, in the grooves between squares.</li>
<li>It can't <strong>overlap</strong> another wall, even partly.</li>
<li>It can't <strong>cross</strong> another wall at the middle (a horizontal wall can't cross a vertical wall at the same point).</li>
<li>Once placed, a wall stays for the rest of the game.</li>
<li>When you've placed all your walls you can only move.</li>
</ul>"""),
        ("paths", "Keeping paths open", """
<p>You may <strong>never</strong> place a wall that leaves either player without any route to their goal edge. Before placing a wall, check both pawns: each must still be able to reach at least one goal square. For this check, only walls count as obstacles.</p>
<p>A wall that makes a route much longer is perfectly legal; a wall that closes it entirely is not.</p>"""),
        ("winning", "Winning conditions", """
<p>The first player to move their pawn onto <strong>any square of the opposite edge</strong> wins at once.</p>"""),
        ("reference", "Quick reference", """
<div class="table-wrap"><table>
<thead><tr><th scope="col">Item</th><th scope="col">Two-player game</th></tr></thead>
<tbody>
<tr><td>Board</td><td>9×9 squares</td></tr>
<tr><td>Walls per player</td><td>10</td></tr>
<tr><td>Starting square</td><td>Middle of your own edge</td></tr>
<tr><td>Each turn</td><td>Move one square <em>or</em> place one wall</td></tr>
<tr><td>Wall size</td><td>2 squares wide</td></tr>
<tr><td>Wall rule</td><td>No overlap, no crossing, never block every route</td></tr>
<tr><td>Win</td><td>Reach any square of the opposite edge first</td></tr>
</tbody></table></div>
<p class="small text-muted">Published rule sets and house rules can differ in small details. When the game modes launch, this page will state exactly which rules the site uses.</p>"""),
    ]
    return article_page(
        "/quoridor-rules/", "Quoridor Rules: Setup, Movement & Wall Placement",
        "Clear Quoridor rules: board setup, starting positions, legal moves and jumps, wall placement restrictions, and winning conditions.",
        "Quoridor rules",
        "A structured reference to the rules of Quoridor, from board setup to the wall restrictions that keep every path open.",
        sections,
        [("How to play Quoridor", "/how-to-play-quoridor/", "a gentler, step-by-step introduction."),
         ("Quoridor strategy", "/quoridor-strategy/", "what to do with these rules once you know them."),
         ("The Quoridor board game", "/quoridor-board-game/", "components, history and how play modes differ.")],
        "Quoridor rules", "rules",
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


def privacy():
    content = """
<div class="callout callout--draft"><p><strong>Draft placeholder.</strong> This is not the final privacy policy. The final text must be written from how the live service actually works and reviewed for the laws that apply.</p></div>
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


def terms():
    content = """
<div class="callout callout--draft"><p><strong>Draft placeholder.</strong> These are not the final terms. The final wording must reflect the real service and applicable requirements.</p></div>
<h2>What the final terms must cover</h2>
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
