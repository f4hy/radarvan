"""Per-URL crawler metadata, real 404s, legacy redirects and the sitemap."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.applications import Starlette

from radarvan import seo
from radarvan.api_types import Team
from radarvan.http_cache import CachedStaticFiles
from tests import corpus

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = (ROOT / "index.html").read_text()

MATCHES = {
    m.id: m
    for m in [
        corpus.match(1, day=5, map_name="Tournament Desert"),
        corpus.match(2, day=5, map_name="Tournament Desert", winner=Team.TWO),
        corpus.match(3, day=12, map_name="Bitter Winter"),
    ]
}
INDEX = seo.build_index(MATCHES)


def _meta(path: str, **query: str) -> seo.PageMeta:
    return seo.page_meta(path, query, lambda: INDEX)


def test_every_frontend_route_has_an_entry() -> None:
    routes = (ROOT / "src" / "routes.tsx").read_text()
    assert set(re.findall(r'slug:\s*"([^"]+)"', routes)) == set(seo.PAGES)


def test_template_carries_the_markers() -> None:
    for marker in ("<!--seo:start-->", "<!--seo:end-->", "<!--seo:body-->"):
        assert marker in TEMPLATE


@pytest.mark.parametrize(
    "path,query",
    [
        ("/no-such-page", {}),
        ("/match/999", {}),
        ("/match/abc", {}),
        ("/match/\u00b2", {}),
        ("/match/" + "9" * 5000, {}),
        ("/match", {}),
        ("/matches/extra", {}),
        ("/player-profile", {"player": "Nobody At All"}),
        ("/game-night", {"date": "2020-01-01"}),
        ("/game-night", {"date": "not-a-date"}),
        ("/map-stats", {"map": "No Such Map"}),
    ],
)
def test_unknown_things_are_404(path: str, query: dict[str, str]) -> None:
    meta = seo.page_meta(path, query, lambda: INDEX)
    assert meta.status == 404
    assert not meta.indexable


def test_match_page_names_players_map_and_game() -> None:
    meta = _meta("/match/1")
    assert meta.status == 200
    assert meta.canonical == "/match/1"
    assert "Tournament Desert" in meta.description
    assert "Zero Hour" in meta.description
    assert "Skip" in meta.title


def test_player_alias_canonicalizes() -> None:
    meta = _meta("/player-profile", player="Skip")
    assert meta.canonical == "/player-profile?player=Skip"
    assert meta.indexable


def test_static_page_canonical_drops_unknown_params() -> None:
    meta = _meta("/matches", utm_source="x")
    assert meta.canonical == "/matches"


def test_case_insensitive_slug() -> None:
    assert _meta("/Matches").status == 200


def test_rating_pages_are_noindex() -> None:
    for slug in ("player-rating", "player-rating-trend", "player-synergy"):
        meta = _meta(f"/{slug}")
        assert meta.status == 200
        assert not meta.indexable


def test_db_unavailable_never_guesses_a_404() -> None:
    meta = seo.page_meta("/player-profile", {"player": "Skip"}, lambda: None)
    assert meta.status == 200


def test_render_replaces_head_and_body() -> None:
    out = seo.render(TEMPLATE, _meta("/match/1"))
    assert out.count("<title>") == 1
    assert 'rel="canonical" href="https://www.radarvan.com/match/1"' in out
    assert "<!--seo:body-->" not in out
    assert '<a href="/player-profile?player=Skip">' in out
    assert '<script type="module"' in out


def test_json_ld_cannot_close_its_script() -> None:
    meta = seo.PageMeta(title="</script><b>", description="x")
    out = seo.render(TEMPLATE, meta)
    ld = out.split('<script type="application/ld+json">')[1].split("</script>")[0]
    assert "<" not in ld


def test_sitemap_is_valid_and_lists_entities() -> None:
    root = ET.fromstring(seo.sitemap_xml(INDEX))  # noqa: S314 - our own output
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    locs = {el.text for el in root.iter(f"{ns}loc")}
    assert "https://www.radarvan.com/" in locs
    assert "https://www.radarvan.com/match/3" in locs
    assert "https://www.radarvan.com/game-night?date=2026-01-12" in locs
    assert "https://www.radarvan.com/player-profile?player=Skip" in locs
    assert "https://www.radarvan.com/player-rating" not in locs


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    (tmp_path / "index.html").write_text(TEMPLATE)
    (tmp_path / "robots.txt").write_text("User-agent: *\n")
    monkeypatch.setattr(seo, "load_index", lambda: INDEX)
    app = Starlette()
    app.mount(
        "/", CachedStaticFiles(directory=tmp_path, html=True, shell=seo.shell_page)
    )
    return TestClient(app, follow_redirects=False)


def test_shell_status_and_tags(client: TestClient) -> None:
    resp = client.get("/match/1")
    assert resp.status_code == 200
    assert "Tournament Desert" in resp.text
    assert resp.headers["cache-control"] == "no-cache"

    resp = client.get("/match/999")
    assert resp.status_code == 404
    assert '<div id="root">' in resp.text
    assert 'content="noindex, follow"' in resp.text


def test_root_gets_home_tags(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert 'href="https://www.radarvan.com/"' in resp.text


def test_legacy_page_link_redirects(client: TestClient) -> None:
    resp = client.get("/?page=game-night&date=2026-01-05")
    assert resp.status_code == 301
    assert resp.headers["location"] == "/game-night?date=2026-01-05"
    resp = client.get("/?page=renamed-long-ago")
    assert resp.headers["location"] == "/game-night"


def test_trailing_slash_redirects(client: TestClient) -> None:
    resp = client.get("/matches/?x=1")
    assert resp.status_code == 301
    assert resp.headers["location"] == "/matches?x=1"


def test_real_files_still_served(client: TestClient) -> None:
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert resp.text.startswith("User-agent")


@pytest.mark.parametrize(
    "path,location",
    [
        ("//evil.com/", "/evil.com"),
        ("/\\evil.com/", "/%5Cevil.com"),
        ("//", "/"),
    ],
)
def test_trailing_slash_redirect_stays_on_site(path: str, location: str) -> None:
    page = seo.shell_page(TEMPLATE, path, "")
    assert page.status == 301
    assert page.location == location


def test_only_entity_pages_load_the_index() -> None:
    def load() -> seo.SiteIndex:
        raise AssertionError("index loaded")

    for path in ("/", "/matches", "/player-profile", "/no-such-page", "/match/abc"):
        seo.page_meta(path, {"utm_source": "x"}, load)
