"""Render HATA's manually edited TOML content into the existing static page.

Only the two files in content/ are intended for routine hand editing.  All HTML
is escaped (apart from a deliberately tiny *emphasis* syntax for news text).
"""
from __future__ import annotations

import datetime as dt
import html
from pathlib import Path
import re
import tomllib
from urllib.parse import urlsplit, quote

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "index.html"
NEWS_FILE = ROOT / "content" / "news.toml"
PAPERS_FILE = ROOT / "content" / "papers.toml"
PAPERS_TOKEN = "{{HATA_PAPERS}}"
NEWS_TOKEN = "{{HATA_NEWS}}"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
DATE_PATTERN = re.compile(r"\d{4}(?:-\d{2}(?:-\d{2})?)?\Z")
DOI_PATTERN = re.compile(r"10\.\d{4,9}/\S+\Z", re.I)


def _read_entries(path: Path, section: str) -> list[dict]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    entries = data.get(section, [])
    if not isinstance(entries, list) or any(not isinstance(item, dict) for item in entries):
        raise ValueError(f"{path}: expected [[{section}]] entries")
    return entries


def _text(item: dict, field: str, context: str, *, required: bool = True) -> str:
    value = item.get(field, "")
    if not isinstance(value, str) or (required and not value.strip()):
        raise ValueError(f"{context}: {field} must be nonempty text" if required else f"{context}: {field} must be text")
    return value.strip()


def _date(value: str, context: str) -> tuple[str, dt.date]:
    if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
        raise ValueError(f"{context}: date must be quoted YYYY, YYYY-MM or YYYY-MM-DD")
    try:
        if len(value) == 4:
            parsed = dt.date(int(value), 1, 1)
        elif len(value) == 7:
            parsed = dt.date(int(value[:4]), int(value[5:]), 1)
        else:
            parsed = dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{context}: invalid date {value!r}") from exc
    return value, parsed


def _url(value: str, context: str) -> str:
    if not value:
        return ""
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"{context}: URL must be an absolute https:// link")
    return value


def _date_html(value: str, date: dt.date, *, year_tag: str) -> str:
    stamp = html.escape(value, quote=True)
    if len(value) == 10:
        return (f'<time datetime="{stamp}"><span class="paper-month">{MONTHS[date.month - 1]}</span>'
                f'<span class="paper-day">{date.day:02d}</span><span class="paper-year">{date.year}</span></time>')
    if len(value) == 7:
        return (f'<time datetime="{stamp}" class="orbit-year"><span class="paper-month">{MONTHS[date.month - 1]}</span>'
                f'<span class="paper-day">{date.year}</span><span class="paper-year">{html.escape(year_tag)}</span></time>')
    return (f'<time datetime="{stamp}" class="orbit-year"><span class="paper-day">{date.year}</span>'
            f'<span class="paper-year">{html.escape(year_tag)}</span></time>')


def _description(text: str) -> str:
    """Plain text, with optional *emphasis* for short paper/thesis titles."""
    text = " ".join(text.split())
    parts = re.split(r"(\*[^*\n]+\*)", text)
    return "".join("<em>" + html.escape(part[1:-1]) + "</em>"
                   if part.startswith("*") and part.endswith("*") else html.escape(part)
                   for part in parts)


def read_news() -> list[dict]:
    entries = _read_entries(NEWS_FILE, "news")
    out = []
    for i, item in enumerate(entries, 1):
        context = f"{NEWS_FILE}: news #{i}"
        value, date = _date(item.get("date"), context)
        category = _text(item, "category", context)
        title = _text(item, "title", context)
        description = _text(item, "description", context)
        url = _url(_text(item, "url", context, required=False), context)
        link_text = _text(item, "link_text", context, required=False) or "More information"
        link_aria_label = _text(item, "link_aria_label", context, required=False) or "More information"
        year_tag = _text(item, "year_tag", context, required=False) or "NEWS"
        out.append(dict(date_value=value, date=date, category=category, title=title,
                        description=description, url=url, link_text=link_text,
                        link_aria_label=link_aria_label, year_tag=year_tag))
    return sorted(out, key=lambda x: x["date_value"], reverse=True)


def render_group_news(news: list[dict]) -> str:
    lines = []
    for item in news:
        date_markup = _date_html(item["date_value"], item["date"], year_tag=item["year_tag"])
        lines.extend([
            '            <li class="paper-item">',
            f'              <div class="paper-date">{date_markup}</div>',
            f'              <div class="paper-info"><p class="paper-type">{html.escape(item["category"])}</p><h3>{html.escape(item["title"])}</h3><p class="paper-authors">{_description(item["description"])}</p></div>',
        ])
        if item["url"]:
            url, link, aria = (html.escape(item[key], quote=True) for key in ("url", "link_text", "link_aria_label"))
            lines.append(f'              <div class="paper-sources" aria-label="{aria}"><a href="{url}" target="_blank" rel="noopener noreferrer">{link} <span aria-hidden="true">↗</span></a></div>')
        lines.append('            </li>')
    return "\n" + "\n".join(lines) + "\n" if lines else "\n"


def read_manual_papers() -> list[dict]:
    entries = _read_entries(PAPERS_FILE, "papers")
    out = []
    for i, item in enumerate(entries, 1):
        context = f"{PAPERS_FILE}: paper #{i}"
        title = _text(item, "title", context)
        authors = item.get("authors")
        if not isinstance(authors, list) or not authors or any(not isinstance(a, str) or not a.strip() for a in authors):
            raise ValueError(f"{context}: authors must be a nonempty list of names")
        status = _text(item, "status", context).lower()
        if status not in {"submitted", "accepted", "published"}:
            raise ValueError(f"{context}: status must be submitted, accepted or published")
        value, date = _date(item.get("date"), context)
        journal = _text(item, "journal", context, required=False)
        url = _url(_text(item, "url", context, required=False), context)
        doi = _text(item, "doi", context, required=False)
        if doi and not DOI_PATTERN.fullmatch(doi):
            raise ValueError(f"{context}: doi must look like 10.1234/suffix (no URL)")
        out.append(dict(title=title, authors=[a.strip() for a in authors], status=status,
                        date_value=value, date=date, journal=journal, url=url, doi=doi))
    return sorted(out, key=lambda x: x["date_value"], reverse=True)


def render_manual_papers(manual: list[dict], automatic: list[dict], same_paper) -> str:
    lines = []
    for item in manual:
        if any(same_paper(item, paper) for paper in automatic):
            continue
        status = item["status"]
        label = {"submitted": "SUBMITTED MANUSCRIPT", "accepted": "ACCEPTED MANUSCRIPT",
                 "published": "JOURNAL PUBLICATION"}[status]
        if item["journal"]:
            label += " · " + item["journal"]
        date_markup = _date_html(item["date_value"], item["date"], year_tag="PAPER")
        title = html.escape(item["title"])
        sources = []
        if item["doi"]:
            doi_url = "https://doi.org/" + quote(item["doi"], safe="/-._;()")
            sources.append(("DOI", doi_url))
        if item["url"]:
            sources.append(("Paper", item["url"]))
        if sources:
            primary = html.escape(sources[0][1], quote=True)
            heading = f'<h3><a href="{primary}" target="_blank" rel="noopener noreferrer">{title} <span aria-hidden="true">↗</span></a></h3>'
            source_markup = ('<div class="paper-sources" aria-label="Publication links">' +
                             ' '.join(f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{name} <span aria-hidden="true">↗</span></a>' for name, url in sources) + '</div>')
        else:
            heading = f'<h3>{title}</h3>'
            source_markup = ('<div class="paper-sources">Not yet publicly available</div>' if status == "submitted"
                             else '<div class="paper-sources">Publication link forthcoming</div>')
        lines.extend([
            '          <li class="paper-item">',
            f'            <div class="paper-date">{date_markup}</div>',
            f'            <div class="paper-info"><p class="paper-type">{html.escape(label)}</p>{heading}<p class="paper-authors">{html.escape(", ".join(item["authors"]))}</p></div>',
            f'            {source_markup}',
            '          </li>',
        ])
    return "\n" + "\n".join(lines) + "\n" if lines else ""


def build_html(automatic: list[dict], render_automatic, same_paper) -> str:
    """Return full HTML without touching the generated file."""
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count(PAPERS_TOKEN) != 1 or template.count(NEWS_TOKEN) != 1:
        raise ValueError("templates/index.html must contain exactly one marker for papers and news")
    paper_html = render_manual_papers(read_manual_papers(), automatic, same_paper) + render_automatic(automatic)
    news_html = render_group_news(read_news())
    return template.replace(PAPERS_TOKEN, paper_html).replace(NEWS_TOKEN, news_html)
