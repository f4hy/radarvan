"""Per-URL status, head tags and crawler fallback body for the SPA shell, plus the sitemap.

Nothing here may surface a rating level (see the player-ratings-and-roles skill).
"""

from __future__ import annotations

import html
import json
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import NamedTuple
from urllib.parse import parse_qsl, quote, urlencode
from xml.sax.saxutils import escape as xml_escape

import structlog

from .api_types import General, MatchInfo
from .cache import register_warmer, sorted_deduped_matches
from .db_utils import ReplayManager
from .dependencies import db_manager
from .derived import CORPUS, derived
from .map_stats import MIN_GAMES as MAP_MIN_GAMES
from .player_ids import PLAYER_NAMES, resolve_player_name
from .replay_files import map_display_name, map_key

logger = structlog.get_logger(__name__)

SITE_URL = os.getenv("SITE_URL", "https://www.radarvan.com").rstrip("/")
SITE_NAME = "Radarvan"
# Mirrored in src/components/Page.tsx so the rendered title matches this one.
TITLE_SUFFIX = "Radarvan – C&C Generals Zero Hour Stats"
OG_IMAGE = f"{SITE_URL}/img/og-image.png"
GAME_NAME = "Command & Conquer: Generals – Zero Hour"
DEFAULT_DESCRIPTION = (
    "Radarvan tracks every Command & Conquer: Generals Zero Hour game our group "
    "plays on Generals Online: match history, replay stats, player profiles, "
    "win rates by general and map, build orders and game night recaps."
)
KEYWORDS = [
    "Command & Conquer",
    "C&C Generals",
    "Generals Zero Hour",
    "Zero Hour stats",
    "Generals Online",
    "C&C Zero Hour replays",
    "GenTool",
    "Radarvan",
]
# Under the protocol's 50,000-URL limit.
SITEMAP_MAX_URLS = 45_000
_START = "<!--seo:start-->"
_END = "<!--seo:end-->"
_BODY = "<!--seo:body-->"


@dataclass(frozen=True)
class StaticPage:
    title: str
    description: str
    indexable: bool = True
    priority: float = 0.6


# Keyed by routes.tsx slug; tests/test_seo.py fails if the two lists drift.
PAGES: dict[str, StaticPage] = {
    "matches": StaticPage(
        "Matches",
        "Every C&C Generals Zero Hour match our group has played, newest first: "
        "teams, generals, maps, winners, replay stats and build orders.",
        priority=0.8,
    ),
    "game-night": StaticPage(
        "Game Night",
        "Recaps of each Command & Conquer Generals Zero Hour game night: "
        "standings, highlights, the match of the night and every replay.",
        priority=0.9,
    ),
    "tournaments": StaticPage(
        "Tournaments",
        "C&C Generals Zero Hour tournaments: teams, results and per-map records.",
    ),
    "bracket": StaticPage(
        "1v1 Bracket",
        "Our Generals Zero Hour 1v1 double-elimination bracket, with schedule, "
        "results and predictions.",
    ),
    "balance-teams": StaticPage(
        "Balance Teams",
        "Split tonight's players into fair Zero Hour teams.",
        priority=0.3,
    ),
    "draft": StaticPage(
        "Map Draft",
        "Draft a C&C Generals Zero Hour map and starting positions for tonight.",
        priority=0.3,
    ),
    "superlatives": StaticPage(
        "Records",
        "All-time C&C Generals Zero Hour records: longest games, biggest "
        "upsets, win streaks and more from our replays.",
        priority=0.7,
    ),
    "team-stats": StaticPage(
        "Team Stats",
        "Which C&C Generals Zero Hour team pairings and general combos win most often.",
    ),
    "general-stats": StaticPage(
        "General Stats",
        "Win rates for every Zero Hour general - USA, China and GLA subfactions "
        "- overall, by map and by matchup.",
        priority=0.8,
    ),
    "composition-predictor": StaticPage(
        "Composition Predictor",
        "Which Zero Hour generals, team compositions and maps are favored "
        "between equally skilled players, estimated from our replays.",
    ),
    "powers": StaticPage(
        "Generals Powers",
        "Which generals powers C&C Zero Hour players pick and use, and how "
        "often: Spy Drone, Carpet Bomb, Artillery, A-10 and more.",
    ),
    "game-length": StaticPage(
        "Game Length",
        "How long Command & Conquer Generals Zero Hour games last, by format and map.",
    ),
    "ffa": StaticPage(
        "Free-For-All",
        "C&C Generals Zero Hour free-for-all games and records.",
    ),
    "opening-book": StaticPage(
        "Build Orders",
        "Zero Hour build orders by general, mined from real replays: what "
        "players build first and how it turns out.",
        priority=0.7,
    ),
    "player-stats": StaticPage(
        "Player Stats",
        "C&C Generals Zero Hour player stats: win/loss records by general, "
        "format and month.",
        priority=0.8,
    ),
    "player-profile": StaticPage(
        "Player Profile",
        "Profiles of every player in our Generals Zero Hour group: favourite "
        "generals and maps, badges, rivals and match history.",
        priority=0.7,
    ),
    "head-to-head": StaticPage(
        "Head to Head",
        "Compare two C&C Generals Zero Hour players: record against each "
        "other, as teammates, and by general and map.",
    ),
    "map-stats": StaticPage(
        "Map Stats",
        "C&C Generals Zero Hour map stats: games played and win rates by "
        "general and player on every map.",
        priority=0.8,
    ),
    "map-voting": StaticPage(
        "Map Voting",
        "Vote on the Generals Zero Hour maps we play.",
        priority=0.3,
    ),
    "choose-map": StaticPage(
        "Choose Map",
        "Pick a random C&C Generals Zero Hour map for tonight.",
        priority=0.3,
    ),
    # Rating-derived, admin, or per-user: reachable, never indexed.
    "player-rating-trend": StaticPage("Rating Trend", "", indexable=False),
    "player-rating": StaticPage("Player Ratings", "", indexable=False),
    "player-synergy": StaticPage("Player Synergy", "", indexable=False),
    "manage-maps": StaticPage("Manage Maps", "", indexable=False),
    "debug-data": StaticPage("Debug Matchid", "", indexable=False),
    "admin-panel": StaticPage("Admin", "", indexable=False),
    "account": StaticPage("Account", "", indexable=False),
    "match": StaticPage("Match", "", indexable=False),
}
DEFAULT_SLUG = "game-night"
LEGACY_PAGE_PARAM = "page"

GENERAL_NAMES = {
    General.USA: "USA",
    General.AIR: "Air Force",
    General.LASER: "Laser",
    General.SUPER: "Superweapon",
    General.CHINA: "China",
    General.NUKE: "Nuke",
    General.TANK: "Tank",
    General.INFANTRY: "Infantry",
    General.GLA: "GLA",
    General.TOXIN: "Toxin",
    General.STEALTH: "Stealth",
    General.DEMO: "Demolition",
}


class MapEntry(NamedTuple):
    name: str
    games: int
    last_played: date


class SiteIndex(NamedTuple):
    matches: Mapping[int, MatchInfo]
    # Canonical name -> last night played, for everyone who played a real game.
    players: Mapping[str, date]
    nights: Mapping[date, int]
    maps: Mapping[str, MapEntry]


@derived(on=CORPUS, maxsize=1)
def site_index(replay_manager: ReplayManager) -> SiteIndex:
    return build_index(sorted_deduped_matches(replay_manager))


def build_index(matches: Mapping[int, MatchInfo]) -> SiteIndex:
    players: dict[str, date] = {}
    nights: dict[date, int] = {}
    map_games: dict[str, list[MatchInfo]] = {}
    for m in matches.values():
        if m.is_dev:
            continue
        nights[m.date] = nights.get(m.date, 0) + 1
        for name in m.roster().human_participant_names():
            players[name] = max(players.get(name, m.date), m.date)
        map_games.setdefault(map_key(m.map), []).append(m)
    maps = {
        key: MapEntry(
            name=map_display_name(games[0].map),
            games=len(games),
            last_played=max(g.date for g in games),
        )
        for key, games in map_games.items()
    }
    return SiteIndex(matches=matches, players=players, nights=nights, maps=maps)


class Link(NamedTuple):
    label: str
    href: str


@dataclass(frozen=True)
class PageMeta:
    title: str
    description: str = DEFAULT_DESCRIPTION
    # Path plus query, e.g. "/player-profile?player=Skip"; None = don't declare.
    canonical: str | None = None
    status: int = 200
    indexable: bool = True
    heading: str = ""
    links: list[Link] = field(default_factory=list)


class ShellPage(NamedTuple):
    status: int
    html: str | None = None
    location: str | None = None


def full_title(tab: str) -> str:
    return f"{tab} · {TITLE_SUFFIX}"


def _href(path: str, **params: str) -> str:
    return f"{path}?{urlencode(params)}" if params else path


def _long_date(d: date) -> str:
    return f"{d:%B} {d.day}, {d.year}"


def _not_found(path: str) -> PageMeta:
    return PageMeta(
        title=full_title("Page not found"),
        description=f"There's nothing at {path} on Radarvan.",
        status=404,
        indexable=False,
        heading="Page not found",
    )


def _team_lines(match: MatchInfo) -> list[tuple[int, list[str], bool]]:
    """(team, ["Name (General)", ...], won) per team, in team order."""
    teams: dict[int, tuple[list[str], bool]] = {}
    for slot in match.roster().participants:
        name = resolve_player_name(slot.name, slot.color) if slot.name else "CPU"
        general = (
            GENERAL_NAMES.get(General(slot.general), "") if slot.general >= 0 else ""
        )
        names, won = teams.get(slot.team, ([], False))
        names.append(f"{name} ({general})" if general else name)
        teams[slot.team] = (names, won or slot.won)
    return [(t, names, won) for t, (names, won) in sorted(teams.items())]


def _matchup(match: MatchInfo) -> str:
    # Same shape as MatchPage.tsx's matchupLabel, so the rendered title agrees.
    teams: dict[int, list[str]] = {}
    for p in match.players:
        teams.setdefault(int(p.team), []).append(p.name)
    return " vs ".join(", ".join(names) for names in teams.values())


def _match_meta(match_id: int, index: SiteIndex) -> PageMeta:
    match = index.matches.get(match_id)
    if match is None:
        return _not_found(f"/match/{match_id}")
    fmt = match.composition.category if match.composition else ""
    map_name = map_display_name(match.map)
    teams = _team_lines(match)
    lineup = " vs ".join(", ".join(names) for _, names, _ in teams)
    winners = [", ".join(names) for _, names, won in teams if won]
    result = f" Won by {winners[0]}." if len(winners) == 1 else ""
    description = (
        f"{fmt + ' ' if fmt else ''}C&C Generals Zero Hour match on {map_name}, "
        f"{_long_date(match.date)}: {lineup}.{result} "
        f"{round(match.duration_minutes)} minutes - replay stats, build orders "
        f"and timeline."
    )
    links = [
        Link(
            f"Game night {_long_date(match.date)}",
            _href("/game-night", date=str(match.date)),
        ),
        Link(f"{map_name} map stats", _href("/map-stats", map=map_name)),
    ]
    links += [
        Link(name, _href("/player-profile", player=name))
        for name in sorted(match.roster().human_participant_names())
    ]
    return PageMeta(
        title=full_title(_matchup(match)),
        description=description,
        canonical=f"/match/{match_id}",
        indexable=not match.is_dev,
        heading=f"{lineup} on {map_name}",
        links=links,
    )


def _player_meta(raw: str, index: SiteIndex) -> PageMeta:
    name = resolve_player_name(raw)
    last = index.players.get(name)
    if last is None:
        return _not_found(f"/player-profile?player={raw}")
    return PageMeta(
        title=full_title(name),
        description=(
            f"{name}'s Command & Conquer Generals Zero Hour profile: win/loss "
            f"record by general and map, favourite generals, rivals, badges "
            f"and full match history. Last played {_long_date(last)}."
        ),
        canonical=_href("/player-profile", player=name),
        # Pickup opponents get a page, but only the group's own are worth indexing.
        indexable=name in PLAYER_NAMES,
        heading=f"{name} - Zero Hour player profile",
        links=[
            Link(f"{name}'s player stats", "/player-stats"),
            Link(f"{name}'s matches", "/matches"),
        ],
    )


def _head_to_head_meta(raw1: str, raw2: str, index: SiteIndex) -> PageMeta:
    p1, p2 = resolve_player_name(raw1), resolve_player_name(raw2)
    if p1 not in index.players or p2 not in index.players:
        return _not_found("/head-to-head")
    return PageMeta(
        title=full_title(f"{p1} vs {p2}"),
        description=(
            f"{p1} vs {p2} in C&C Generals Zero Hour: head-to-head record, "
            f"results as teammates, and how each does by general and map."
        ),
        canonical=_href("/head-to-head", player1=p1, player2=p2),
        indexable=p1 in PLAYER_NAMES and p2 in PLAYER_NAMES,
        heading=f"{p1} vs {p2} head to head",
        links=[
            Link(p1, _href("/player-profile", player=p1)),
            Link(p2, _href("/player-profile", player=p2)),
        ],
    )


def _game_night_meta(raw: str, index: SiteIndex) -> PageMeta:
    try:
        night = date.fromisoformat(raw)
    except ValueError:
        return _not_found(f"/game-night?date={raw}")
    games = index.nights.get(night)
    if games is None:
        return _not_found(f"/game-night?date={raw}")
    played = [m for m in index.matches.values() if m.date == night and not m.is_dev]
    names = sorted({n for m in played for n in m.roster().human_participant_names()})
    maps = sorted({map_display_name(m.map) for m in played})
    return PageMeta(
        title=full_title(f"Game Night {night}"),
        description=(
            f"C&C Generals Zero Hour game night, {_long_date(night)}: {games} "
            f"games with {', '.join(names)} on {', '.join(maps)}. Standings, "
            f"highlights and every replay."
        ),
        canonical=_href("/game-night", date=str(night)),
        heading=f"Zero Hour game night - {_long_date(night)}",
        links=[Link(n, _href("/player-profile", player=n)) for n in names]
        + [
            Link(f"{_matchup(m)} on {map_display_name(m.map)}", f"/match/{m.id}")
            for m in played
        ],
    )


def _map_meta(raw: str, index: SiteIndex) -> PageMeta:
    entry = index.maps.get(map_key(raw))
    if entry is None:
        return _not_found(f"/map-stats?map={raw}")
    return PageMeta(
        title=full_title(f"{entry.name} · Map Stats"),
        description=(
            f"{entry.name} in Command & Conquer Generals Zero Hour: {entry.games} "
            f"games played, win rates by general and by player."
        ),
        canonical=_href("/map-stats", map=entry.name),
        indexable=entry.games >= MAP_MIN_GAMES,
        heading=f"{entry.name} - Zero Hour map stats",
    )


def _site_links() -> list[Link]:
    return [Link(p.title, f"/{slug}") for slug, p in PAGES.items() if p.indexable]


def _static_meta(slug: str) -> PageMeta:
    page = PAGES[slug]
    if not page.indexable:
        return PageMeta(
            title=full_title(page.title), indexable=False, heading=page.title
        )
    return PageMeta(
        title=full_title(page.title),
        description=page.description,
        canonical=f"/{slug}",
        heading=f"{page.title} - C&C Generals Zero Hour",
    )


def _legacy_redirect(query: Mapping[str, str]) -> str:
    # Mirrors App.tsx's LegacyPageRedirect, unknown slug -> DEFAULT_SLUG included.
    slug = query[LEGACY_PAGE_PARAM].lower()
    target = slug if slug in PAGES and slug != "match" else DEFAULT_SLUG
    rest = {k: v for k, v in query.items() if k != LEGACY_PAGE_PARAM}
    return _href(f"/{target}", **rest)


# Bounded so int() can't reject it; ASCII-only because str.isdigit() accepts "²".
_MATCH_ID = re.compile(r"[0-9]{1,18}")
_ENTITY_PARAMS = {
    "player-profile": ("player",),
    "head-to-head": ("player1", "player2"),
    "game-night": ("date",),
    "map-stats": ("map",),
}


def _names_entity(slug: str, query: Mapping[str, str]) -> bool:
    return slug in _ENTITY_PARAMS and all(query.get(k) for k in _ENTITY_PARAMS[slug])


def page_meta(
    path: str, query: Mapping[str, str], load: Callable[[], SiteIndex | None]
) -> PageMeta:
    # Only entity pages call load(), so other pages never wait on a corpus rebuild.
    # None = DB unavailable: entity pages fall back to page-level tags, never a guessed 404.
    parts = [p for p in path.split("/") if p]
    if not parts:
        return PageMeta(
            title=f"{SITE_NAME} – Command & Conquer Generals Zero Hour Stats & Replays",
            canonical="/",
            heading="Radarvan - C&C Generals Zero Hour stats",
        )
    slug = parts[0].lower()
    if slug == "match" and len(parts) == 2:
        if not _MATCH_ID.fullmatch(parts[1]):
            return _not_found(path)
        index = load()
        if index is None:
            return PageMeta(title=full_title("Match"), canonical=f"/match/{parts[1]}")
        return _match_meta(int(parts[1]), index)
    if len(parts) != 1 or slug not in PAGES or slug == "match":
        return _not_found(path)

    index = load() if _names_entity(slug, query) else None
    if index is not None:
        if slug == "player-profile" and query.get("player"):
            return _player_meta(query["player"], index)
        if slug == "head-to-head" and query.get("player1") and query.get("player2"):
            return _head_to_head_meta(query["player1"], query["player2"], index)
        if slug == "game-night" and query.get("date"):
            return _game_night_meta(query["date"], index)
        if slug == "map-stats" and query.get("map"):
            return _map_meta(query["map"], index)
    return _static_meta(slug)


def _head_html(meta: PageMeta) -> str:
    e = html.escape
    url = f"{SITE_URL}{meta.canonical}" if meta.canonical else None
    tags = [
        f"<title>{e(meta.title)}</title>",
        f'<meta name="description" content="{e(meta.description)}" />',
        f'<meta name="robots" content="{"index, follow" if meta.indexable else "noindex, follow"}" />',
        '<meta property="og:type" content="website" />',
        f'<meta property="og:site_name" content="{SITE_NAME}" />',
        f'<meta property="og:title" content="{e(meta.title)}" />',
        f'<meta property="og:description" content="{e(meta.description)}" />',
        f'<meta property="og:image" content="{OG_IMAGE}" />',
        '<meta property="og:image:width" content="400" />',
        '<meta property="og:image:height" content="210" />',
        '<meta name="twitter:card" content="summary" />',
        f'<meta name="twitter:title" content="{e(meta.title)}" />',
        f'<meta name="twitter:description" content="{e(meta.description)}" />',
    ]
    if url:
        tags.append(f'<link rel="canonical" href="{e(url)}" />')
        tags.append(f'<meta property="og:url" content="{e(url)}" />')
    if meta.indexable:
        tags.append(_json_ld(meta, url))
    return "\n    ".join(tags)


def _json_ld(meta: PageMeta, url: str | None) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": meta.title,
        "description": meta.description,
        "url": url or SITE_URL,
        "inLanguage": "en",
        "keywords": ", ".join(KEYWORDS),
        "about": {
            "@type": "VideoGame",
            "name": GAME_NAME,
            "alternateName": ["C&C Generals Zero Hour", "Generals Zero Hour"],
            "publisher": "Electronic Arts",
            "genre": "Real-time strategy",
        },
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": SITE_URL},
    }
    # "<" escaped so a name can never close the script element.
    body = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return f'<script type="application/ld+json">{body}</script>'


def _body_html(meta: PageMeta) -> str:
    # For crawlers that don't run JS; createRoot replaces it on mount.
    e = html.escape
    links = meta.links + _site_links()
    items = "".join(
        f'<li><a href="{e(link.href)}">{e(link.label)}</a></li>' for link in links
    )
    return (
        '<main style="font-family:system-ui,sans-serif;padding:24px">'
        f"<h1>{e(meta.heading or meta.title)}</h1>"
        f"<p>{e(meta.description)}</p>"
        f"<nav><ul>{items}</ul></nav>"
        "</main>"
    )


def render(template: str, meta: PageMeta) -> str:
    """Fill the seo markers in the built index.html."""
    start, end = template.find(_START), template.find(_END)
    if start == -1 or end == -1:
        return template
    out = (
        template[: start + len(_START)]
        + "\n    "
        + _head_html(meta)
        + "\n    "
        + template[end:]
    )
    return out.replace(_BODY, _body_html(meta), 1)


def load_index() -> SiteIndex | None:
    try:
        with db_manager.get_replay_manager() as replay_manager:
            return site_index(replay_manager)
    except Exception:
        logger.warning("seo site index unavailable", exc_info=True)
        return None


register_warmer(load_index)


def shell_page(template: str, path: str, query_string: str) -> ShellPage:
    """Blocking (may touch the DB): call from a worker thread."""
    query = dict(parse_qsl(query_string))
    if path in ("/", "/index.html") and LEGACY_PAGE_PARAM in query:
        return ShellPage(status=301, location=_legacy_redirect(query))
    if path != "/" and path.endswith("/"):
        # Collapse leading slashes and quote "\\": "//evil.com/" or "/\\evil.com/" must not
        # become a protocol-relative Location.
        return ShellPage(
            status=301,
            location="/"
            + quote(path.strip("/"), safe="/")
            + (f"?{query_string}" if query_string else ""),
        )
    if path == "/index.html":
        path = "/"
    meta = page_meta(path, query, load_index)
    return ShellPage(status=meta.status, html=render(template, meta))


def sitemap_xml(index: SiteIndex) -> str:
    latest = max(index.nights, default=None)

    def url(loc: str, lastmod: date | None, priority: float) -> str:
        mod = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
        return (
            f"<url><loc>{xml_escape(SITE_URL + loc)}</loc>{mod}"
            f"<priority>{priority:.1f}</priority></url>"
        )

    entries = [url("/", latest, 1.0)]
    entries += [
        url(f"/{slug}", latest, page.priority)
        for slug, page in PAGES.items()
        if page.indexable
    ]
    entries += [
        url(_href("/player-profile", player=name), last, 0.7)
        for name, last in sorted(index.players.items())
        if name in PLAYER_NAMES
    ]
    entries += [
        url(_href("/map-stats", map=m.name), m.last_played, 0.5)
        for m in sorted(index.maps.values(), key=lambda m: -m.games)
        if m.games >= MAP_MIN_GAMES
    ]
    entries += [
        url(_href("/game-night", date=str(night)), night, 0.6)
        for night in sorted(index.nights, reverse=True)
    ]
    # Newest first, so a cap drops the oldest matches.
    matches = (m for m in index.matches.values() if not m.is_dev)
    entries += [url(f"/match/{m.id}", m.date, 0.4) for m in matches]
    if len(entries) > SITEMAP_MAX_URLS:
        logger.warning("sitemap truncated", urls=len(entries))
        entries = entries[:SITEMAP_MAX_URLS]
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )
