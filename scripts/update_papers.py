#!/usr/bin/env python3
"""Build HATA's static publication feed from arXiv and the public DTU Orbit portal.

The website never fetches either source in the browser. This best-effort updater
is run by GitHub Actions, keeps a checked-in cache and never erases cached items
on upstream failures. No non-stdlib Python dependencies are required.

Orbit's public portal is HTML, *not* a documented stable feed/API. Its parser is
intentionally conservative; monitor scheduled Actions runs and request a proper
Pure API/feed from DTU Library for long-term guaranteed Orbit harvesting.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
from html.parser import HTMLParser
import json
import re
import sys
import time
import unicodedata
from difflib import SequenceMatcher
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "authors.json"
DATA = ROOT / "site" / "data" / "papers.json"
PAGE = ROOT / "site" / "index.html"
SUBMITTED = ROOT / "config" / "submitted-papers.json"
API_URL = "https://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"
NUMBER_SHOWN = 5
MAX_CACHED = 100
VALID_ID = re.compile(r"(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})\Z", re.I)
VALID_ORBIT_SLUG = re.compile(r"[a-z0-9-]{5,180}\Z")
ORBIT_PUBLICATION_PATH = re.compile(r"^/en/publications/([a-z0-9-]{5,180})/?$", re.I)
ORBIT_PROFILE = "https://orbit.dtu.dk/en/persons/{slug}/"
NEWS_BLOCK = re.compile(r"(?<=<!-- PAPERS:START -->).*?(?=<!-- PAPERS:END -->)", re.S)
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
PUB_YEAR = re.compile(r"(?<!\d)(19[789]\d|20\d\d)(?!\d)")
USER_AGENT = "HATA-group-website/2.0 (+https://hata.compute.dtu.dk; daily publication digest)"


def normalize_name(name: str) -> str:
    flat = unicodedata.normalize("NFKD", name)
    return "".join(c for c in flat.casefold() if c.isalnum() and not unicodedata.combining(c))


def normalize_title(title: str) -> str:
    return normalize_name(html.unescape(title))


def read_authors() -> list[dict]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))["authors"]


def create_query(members: list[dict]) -> str:
    aliases = list(dict.fromkeys(name for member in members for name in member["arxiv_names"]))
    return " OR ".join('au:"' + name.replace('"', "") + '"' for name in aliases)


def fetch_url(url: str, attempts: int = 2, max_bytes: int = 3_000_000) -> bytes:
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/atom+xml, text/html, application/xml, */*",
    })
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                data = response.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise ValueError("Upstream response exceeds size limit")
                return data
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            if attempt + 1 == attempts:
                raise RuntimeError(f"Upstream temporarily unavailable: {url}: {exc}") from exc
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def fetch_atom(members: list[dict], attempts: int = 3) -> bytes:
    params = {
        "search_query": create_query(members), "start": "0", "max_results": "100",
        "sortBy": "submittedDate", "sortOrder": "descending",
    }
    return fetch_url(API_URL + "?" + urllib.parse.urlencode(params), attempts=attempts)


def member_matches(author_names: list[str], members: list[dict]) -> list[str]:
    byline = {normalize_name(name) for name in author_names}
    return [member["name"] for member in members if any(
        normalize_name(alias) in byline for alias in member["arxiv_names"]
    )]


def parse_atom(xml_data: bytes, members: list[dict]) -> list[dict]:
    tree = ET.fromstring(xml_data)
    if tree.tag != ATOM + "feed":
        raise ValueError("The arXiv endpoint did not return an Atom feed")
    papers = []
    for entry in tree.findall(ATOM + "entry"):
        authors = [" ".join((node.text or "").split()) for node in entry.findall(f"{ATOM}author/{ATOM}name")]
        matches = member_matches(authors, members)
        if not matches:
            continue
        id_url = (entry.findtext(ATOM + "id") or "").strip()
        found = re.search(r"(?:https?://)?(?:export\.)?arxiv\.org/abs/(.+)$", id_url)
        if not found:
            continue
        identifier = re.sub(r"v\d+$", "", found.group(1))
        if not VALID_ID.fullmatch(identifier):
            continue
        published = (entry.findtext(ATOM + "published") or "")[:10]
        try:
            dt.date.fromisoformat(published)
        except ValueError:
            continue
        title = " ".join((entry.findtext(ATOM + "title") or "").split())
        if not title:
            continue
        primary = entry.find(ARXIV + "primary_category")
        category = primary.get("term", "") if primary is not None else ""
        if not category:
            categories = entry.findall(ATOM + "category")
            category = categories[0].get("term", "") if categories else ""
        papers.append({
            "id": identifier, "arxiv_id": identifier,
            "title": title, "authors": authors, "published": published,
            "date_precision": "day", "primary_category": category,
            "url": "https://arxiv.org/abs/" + identifier,
            "matched_members": matches,
        })
    return papers


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def strip_html(markup: str) -> str:
    parser = _PlainText()
    parser.feed(markup)
    return " ".join(" ".join(parser.parts).split())


def valid_orbit_url(url: str) -> bool:
    try:
        parts = urllib.parse.urlsplit(url)
        return (parts.scheme == "https" and parts.netloc == "orbit.dtu.dk" and
                bool(ORBIT_PUBLICATION_PATH.fullmatch(parts.path)) and not parts.query and not parts.fragment)
    except (TypeError, ValueError):
        return False


def parse_orbit(raw_html: bytes | str, member: dict) -> list[dict]:
    """Conservatively extract visible publication links + publication years.

    No invented day/month: Orbit's listing normally provides a publication *year*
    only. Never treat an Orbit journal year as a newly submitted preprint date.
    This HTML parser is a best effort, not a supported API contract.
    """
    source = raw_html.decode("utf-8", "replace") if isinstance(raw_html, bytes) else raw_html
    anchor = re.compile(r"<a\b(?P<attrs>[^>]*?)>(?P<body>.*?)</a\s*>", re.I | re.S)
    href = re.compile(r"\bhref\s*=\s*([\"'])(.*?)\1", re.I | re.S)
    matches = list(anchor.finditer(source))
    papers: list[dict] = []
    seen = set()
    for n, tag in enumerate(matches):
        hm = href.search(tag.group("attrs"))
        if not hm:
            continue
        url = urllib.parse.urljoin("https://orbit.dtu.dk/", html.unescape(hm.group(2)))
        if not valid_orbit_url(url) or url in seen:
            continue
        title = strip_html(tag.group("body"))
        if len(title) < 12 or len(title) > 400:
            continue
        # A year immediately following the title (after author names) can be
        # extracted from the public Pure portal's short rendering. Never grab
        # a year from the next publication: stop at its own title link.
        next_paper_start = min((other.start() for other in matches[n + 1:]
                                if (m := href.search(other.group("attrs"))) and
                                valid_orbit_url(urllib.parse.urljoin("https://orbit.dtu.dk/", html.unescape(m.group(2))))),
                               default=len(source))
        trailing = strip_html(source[tag.end():min(tag.end() + 2200, next_paper_start)])
        yearmatch = PUB_YEAR.search(trailing[:550])
        if yearmatch is None:
            continue
        year = int(yearmatch.group(1))
        if not (1990 <= year <= dt.date.today().year + 2):
            continue
        slug = ORBIT_PUBLICATION_PATH.fullmatch(urllib.parse.urlsplit(url).path).group(1)
        papers.append({
            "id": "orbit:" + slug.lower(), "title": title, "authors": [],
            "published": f"{year}-01-01", "date_precision": "year",
            "orbit_year": year, "orbit_url": url, "matched_members": [member["name"]],
        })
        seen.add(url)
    return papers[:12]


def fetch_orbit(members: list[dict]) -> list[dict]:
    found: list[dict] = []
    for member in members:
        slug = member.get("orbit_slug")
        if not slug or not VALID_ORBIT_SLUG.fullmatch(slug):
            print(f"WARNING: No Orbit person slug for {member['name']}; skipping.", file=sys.stderr)
            continue
        url = ORBIT_PROFILE.format(slug=slug)
        try:
            rows = parse_orbit(fetch_url(url, attempts=2), member)
            if not rows:
                print(f"WARNING: No readable Orbit entries for {member['name']} ({url}). Portal HTML may have changed.", file=sys.stderr)
            found.extend(rows)
        except (RuntimeError, ValueError) as exc:
            print(f"WARNING: {exc}; retaining last-known Orbit entries.", file=sys.stderr)
    return found


def valid_cache_row(item: dict) -> bool:
    try:
        identifier = item["id"]
        if not (VALID_ID.fullmatch(identifier) or
                (identifier.startswith("orbit:") and VALID_ORBIT_SLUG.fullmatch(identifier[6:]) and valid_orbit_url(item.get("orbit_url", "")))):
            return False
        if item.get("arxiv_id") and not VALID_ID.fullmatch(item["arxiv_id"]):
            return False
        dt.date.fromisoformat(item["published"])
        if not (isinstance(item["title"], str) and item["title"].strip()
                and isinstance(item["authors"], list)
                and all(isinstance(a, str) for a in item["authors"])):
            return False
        if item.get("orbit_url") and not valid_orbit_url(item["orbit_url"]):
            return False
        return True
    except (KeyError, ValueError, TypeError, AttributeError):
        return False


def _record(item: dict) -> dict:
    arxiv_id = item.get("arxiv_id") or (item["id"] if VALID_ID.fullmatch(item["id"]) else None)
    is_orbit_only = not arxiv_id
    orbit_url = item.get("orbit_url")
    orbit_year = item.get("orbit_year")
    if orbit_year:
        orbit_year = int(orbit_year)
    published = item["published"]
    if is_orbit_only and orbit_year:
        published = f"{orbit_year}-01-01"
    return {
        "id": arxiv_id or item["id"],
        "title": item["title"], "authors": item["authors"],
        "published": published, "date_precision": "year" if is_orbit_only else "day",
        "primary_category": item.get("primary_category", "") if arxiv_id else "",
        "arxiv_id": arxiv_id,
        "url": "https://arxiv.org/abs/" + arxiv_id if arxiv_id else None,
        "orbit_url": orbit_url, "orbit_year": orbit_year,
        "matched_members": sorted(set(item.get("matched_members", []))),
    }


def same_paper(a: dict, b: dict) -> bool:
    if a.get("arxiv_id") and a.get("arxiv_id") == b.get("arxiv_id"):
        return True
    if a.get("orbit_url") and a.get("orbit_url") == b.get("orbit_url"):
        return True
    aa, bb = normalize_title(a["title"]), normalize_title(b["title"])
    return (aa == bb) or (min(len(aa), len(bb)) > 28 and
                         SequenceMatcher(None, aa, bb).ratio() >= .97)


def _merge_two(a: dict, b: dict) -> dict:
    # Prefer up-to-date arXiv bylines/dates. Prefer Orbit only for its URL/year.
    out = dict(a)
    for fld in ("orbit_url", "orbit_year"):
        if b.get(fld):
            out[fld] = b[fld]
    if b.get("arxiv_id"):
        for fld in ("id", "arxiv_id", "url", "title", "authors", "published", "date_precision", "primary_category"):
            out[fld] = b[fld]
    elif not out.get("arxiv_id"):
        for fld in ("title", "published", "date_precision"):
            out[fld] = b[fld]
        if b.get("authors"):
            out["authors"] = b["authors"]
    out["matched_members"] = sorted(set(a["matched_members"]) | set(b["matched_members"]))
    return out


def merge_papers(existing: list[dict], fresh: list[dict]) -> list[dict]:
    merged: list[dict] = []
    for item in [*existing, *fresh]:
        if not valid_cache_row(item):
            continue
        row = _record(item)
        match = next((i for i, old in enumerate(merged) if same_paper(old, row)), None)
        if match is None:
            merged.append(row)
        else:
            merged[match] = _merge_two(merged[match], row)
    # A revised arXiv title can link two previously separate Orbit/arXiv rows.
    # Coalesce transitively after the first pass rather than leaving duplicates.
    i = 0
    while i < len(merged):
        j = i + 1
        while j < len(merged):
            if same_paper(merged[i], merged[j]):
                merged[i] = _merge_two(merged[i], merged.pop(j))
            else:
                j += 1
        i += 1
    merged.sort(key=lambda x: (x["published"], x["id"]), reverse=True)
    return merged[:MAX_CACHED]


def read_submitted_papers() -> list[dict]:
    """Read opt-in, unpublished manuscripts; never include the commented example."""
    if not SUBMITTED.exists():
        return []
    payload = json.loads(SUBMITTED.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("papers"), list):
        raise ValueError("submitted-papers.json must contain a papers list")
    rows = []
    for item in payload["papers"]:
        if not isinstance(item, dict):
            raise ValueError("Each submitted paper must be an object")
        title, authors, date = item.get("title"), item.get("authors"), item.get("submitted")
        if not isinstance(title, str) or not title.strip() or not isinstance(authors, list) or not authors or not all(isinstance(a, str) and a.strip() for a in authors):
            raise ValueError("Submitted papers require a title and nonempty list of authors")
        if not isinstance(date, str):
            raise ValueError("Submitted papers require a YYYY-MM-DD submission date")
        dt.date.fromisoformat(date)
        journal = item.get("journal", "")
        if not isinstance(journal, str):
            raise ValueError("Optional journal must be text")
        rows.append({"title": title.strip(), "authors": authors, "submitted": date, "journal": journal.strip()})
    return rows


def render_submitted_papers(submitted: list[dict], published: list[dict]) -> str:
    """Only announce manuscripts without a matching public arXiv/Orbit record."""
    lines = []
    for item in sorted(submitted, key=lambda x: x["submitted"], reverse=True):
        if any(same_paper(item, paper) for paper in published):
            continue
        date = dt.date.fromisoformat(item["submitted"])
        label = "SUBMITTED MANUSCRIPT"
        if item["journal"]:
            label += " · " + item["journal"]
        lines.extend([
            '          <li class="paper-item">',
            f'            <div class="paper-date"><time datetime="{date.isoformat()}"><span class="paper-month">{MONTHS[date.month-1]}</span><span class="paper-day">{date.day:02d}</span><span class="paper-year">{date.year}</span></time></div>',
            f'            <div class="paper-info"><p class="paper-type">{html.escape(label)}</p><h3>{html.escape(item["title"])}</h3><p class="paper-authors">{html.escape(", ".join(item["authors"]))}</p></div>',
            '            <div class="paper-sources">Not yet publicly available</div>',
            '          </li>',
        ])
    return ("\\n" + "\\n".join(lines) + "\\n") if lines else ""


def render_news(papers: list[dict]) -> str:
    if not papers:
        return '\n          <li class="no-papers">Browse publications through our DTU Orbit profiles.</li>\n'
    lines = [""]
    for item in papers[:NUMBER_SHOWN]:
        pub = dt.date.fromisoformat(item["published"])
        name = html.escape(item["title"], quote=True)
        members = ", ".join(item.get("matched_members", []))
        authors = html.escape(", ".join(item["authors"]) if item["authors"] else "HATA researcher: " + members, quote=True)
        label = ("arXiv PREPRINT" if item.get("arxiv_id") else "DTU ORBIT PUBLICATION")
        if item.get("arxiv_id") and item.get("orbit_url"):
            label += " · ORBIT RECORD"
        elif item.get("arxiv_id") and item.get("primary_category"):
            label += " · " + item["primary_category"]
        if item.get("arxiv_id"):
            date_display = (f'<time datetime="{pub.isoformat()}"><span class="paper-month">{MONTHS[pub.month-1]}</span>'
                            f'<span class="paper-day">{pub.day:02d}</span><span class="paper-year">{pub.year}</span></time>')
        else:
            date_display = f'<time datetime="{pub.year}" class="orbit-year"><span class="paper-day">{pub.year}</span><span class="paper-year">ORBIT</span></time>'
        primary = ("https://arxiv.org/pdf/" + item["arxiv_id"]) if item.get("arxiv_id") else item.get("orbit_url")
        if not valid_orbit_url(primary) and not item.get("arxiv_id"):
            continue
        sources = []
        if item.get("orbit_url"):
            sources.append(f'<a href="{html.escape(item["orbit_url"], quote=True)}" target="_blank" rel="noopener noreferrer">Orbit <span aria-hidden="true">↗</span></a>')
        if item.get("arxiv_id"):
            sources.append(f'<a href="{html.escape(item["url"], quote=True)}" target="_blank" rel="noopener noreferrer">arXiv <span aria-hidden="true">↗</span></a>')
        lines.extend([
            '          <li class="paper-item">',
            f'            <div class="paper-date">{date_display}</div>',
            f'            <div class="paper-info"><p class="paper-type">{html.escape(label)}</p><h3><a href="{html.escape(primary, quote=True)}" target="_blank" rel="noopener noreferrer">{name} <span aria-hidden="true">↗</span></a></h3><p class="paper-authors">{authors}</p></div>',
            '            <div class="paper-sources" aria-label="Publication links">' + ' '.join(sources) + '</div>',
            '          </li>',
        ])
    lines.append("")
    return "\n".join(lines)


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def update(offline: bool = False) -> tuple[int, bool]:
    members = read_authors()
    cache = json.loads(DATA.read_text(encoding="utf-8"))
    current_names = {member["name"] for member in members}
    old = [p for p in cache.get("papers", []) if set(p.get("matched_members", [])) & current_names]
    incoming_arxiv: list[dict] = []
    incoming_orbit: list[dict] = []
    if not offline:
        try:
            incoming_arxiv = parse_atom(fetch_atom(members), members)
            if not incoming_arxiv:
                print("WARNING: arXiv returned no matching papers; preserving cache.", file=sys.stderr)
        except (RuntimeError, ValueError, ET.ParseError) as exc:
            print(f"WARNING: {exc}; preserving cached arXiv data.", file=sys.stderr)
        incoming_orbit = fetch_orbit(members)
    papers = merge_papers(old, incoming_orbit + incoming_arxiv)
    if not papers:
        raise RuntimeError("No publications or valid cache; refusing to build an empty feed.")
    cache = {
        "source": "arXiv and DTU Orbit",
        "notes": "Snapshot of first arXiv submission dates and Orbit publication years. Orbit collection is best-effort HTML parsing (not a stable official feed); no entries are removed on source failure.",
        "papers": papers,
    }
    changed_json = write_if_changed(DATA, json.dumps(cache, ensure_ascii=False, indent=2) + "\n")
    index = PAGE.read_text(encoding="utf-8")
    if len(NEWS_BLOCK.findall(index)) != 1:
        raise RuntimeError("Missing or duplicate PAPERS markers in site/index.html")
    submitted = read_submitted_papers()
    submitted_html = render_submitted_papers(submitted, papers)
    changed_html = write_if_changed(PAGE, NEWS_BLOCK.sub(lambda m: submitted_html + render_news(papers), index))
    print(f"Rendered {min(NUMBER_SHOWN, len(papers))} of {len(papers)} cached distinct papers; "
          f"arXiv: {len(incoming_arxiv)} new feed entries; Orbit: {len(incoming_orbit)}; "
          f"{'offline' if offline else 'online'}; {'files changed' if changed_json or changed_html else 'no file changes'}.")
    return len(papers), changed_json or changed_html


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Rebuild from cached JSON only, without network access")
    args = parser.parse_args()
    update(offline=args.offline)
