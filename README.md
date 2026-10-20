# HATA — Harmonic Analysis: Theory and Application

A low-maintenance static homepage for HATA at DTU Compute's Mathematics section.

**Website (after enabling Pages):** https://jakoblem.github.io/hata/  
**Repository:** https://github.com/jakoblem/hata  
**Planned DTU address:** https://hata.compute.dtu.dk/

The published site consists of plain HTML/CSS/images in [`site/`](site/), generated from an HTML template and small TOML content files. No PHP, CMS, JavaScript framework, browser-side publication API requests, cookies or tracking. Python 3.12's standard library handles the build; site visitors need no special software.

## How to update the homepage

**For routine content updates, use the source files below rather than editing the generated page:**

| What you want to change | Where to edit |
| --- | --- |
| Main page wording, headings, research cards, links, people section, or HTML layout | [`templates/index.html`](templates/index.html) |
| Research visit, talk, conference, defence, award, other announcement | [`content/news.toml`](content/news.toml) |
| Submitted/accepted manuscript, or paper absent from arXiv and DTU Orbit | [`content/papers.toml`](content/papers.toml) |
| Colours, spacing, typography, card layout, responsive styling | [`site/assets/styles.css`](site/assets/styles.css) |
| Staff member or arXiv/Orbit author alias | [`config/authors.json`](config/authors.json) (infrequent) |

### Changing the main HTML page

For ordinary HTML/content changes, edit **[`templates/index.html`](templates/index.html)**. This is the source for the homepage. Use it for changes such as the hero text, research-area descriptions, researcher interests, publication-directory links, section headings, or page structure.

**Do not edit `site/index.html` directly.** It is generated from `templates/index.html` together with the TOML content and publication data, so the next GitHub Actions build can overwrite direct edits.

After editing `templates/index.html`, commit the change to `main`. GitHub Actions rebuilds `site/index.html` automatically. To rebuild locally, run:

```sh
python3 scripts/update_papers.py --offline
```

Automatic publication updates use [`scripts/update_papers.py`](scripts/update_papers.py), and the TOML renderer is [`scripts/content_build.py`](scripts/content_build.py).

### Easiest way: edit on GitHub

1. Open [\`content/news.toml\`](content/news.toml) or [\`content/papers.toml\`](content/papers.toml) on GitHub.
2. Click the pencil (**Edit this file**).
3. Copy an existing \`[[news]]\` or \`[[papers]]\` block, change the values, and commit the change to \`main\` (or propose a pull request for review).
4. Open **Actions → Publish HATA website** to confirm the build succeeds. A change to \`main\` triggers the site build; a scheduled daily run also refreshes arXiv/Orbit records.
5. Check [the GitHub Pages site](https://jakoblem.github.io/hata/) once deployment finishes. Publishing to the separate DTU hostname depends on the optional DTU deployment configuration.

No local software is required when editing through GitHub. The file format is **TOML**, so text values must have quotation marks, but entries do not need commas between them. The examples below are illustrative; **do not publish fictional entries**.

### Add a news item

Add a block in \`content/news.toml\`:

```toml
[[news]]
date = "2026-10"
category = "RESEARCH VISIT · OTH REGENSBURG"
title = "Research visit"
description = "Two HATA researchers visit colleagues for research discussions."
url = "https://example.org/visit"
link_text = "Host information"
```

The required fields are \`date\`, \`category\`, \`title\`, and \`description\`. The link fields \`url\`, \`link_text\` and \`link_aria_label\` are optional; omit them for unlinked news. \`year_tag\` is an optional short label used alongside month-only/year-only dates (e.g. \`"VISIT"\`). Use \`*italics*\` in descriptions to emphasize a thesis or paper title. Other HTML and Markdown are treated as text and escaped.

Dates must be **quoted strings**: \`"2026-10-14"\` (specific day), \`"2026-10"\` (known month) or \`"2026"\` (year only). Prefer a full date when known; do not invent missing days. Items are sorted newest first. Keep announcements short so the homepage remains focused.

### Add a paper not yet visible in arXiv/Orbit

Add a block in \`content/papers.toml\`:

```toml
[[papers]]
title = "Example mathematical manuscript"
authors = ["Ole Christensen", "Marzieh Hasannasab"]
status = "submitted"
date = "2026-10-09"
journal = "Example Journal"
```

The required fields are \`title\`, \`authors\` (an array of names), \`status\` and \`date\`. Accepted statuses are **\`submitted\`**, **\`accepted\`**, and **\`published\`**. The optional fields are \`journal\`, \`doi\` (for example \`"10.1000/example"\`) and \`url\` (a direct HTTPS link). The homepage displays plain, nonclickable titles when no link is available. Use a publication year such as \`"2026"\` when the precise date is unknown; never pretend that a publication-year record has a known January 1 publication date.

The build checks manually supplied titles against the arXiv/Orbit cache and suppresses manual copies when a matching publication appears, so one paper should not appear twice. Remove superseded manual records when convenient. Manuscripts not publicly available should only be announced with coauthor approval.

### What happens automatically

- arXiv and DTU Orbit are checked daily by GitHub Actions. Their publications are cached in \`site/data/papers.json\` and shown as research highlights.
- Any manual papers absent from those sources are rendered into the same **Latest papers** list.
- Entries in \`content/news.toml\` appear separately under **Other news**.
- Each build combines all sources with the immutable \`templates/index.html\` structure and writes a static \`site/index.html\`.
- Validation rejects invalid dates, malformed TOML, unsafe links and incomplete records rather than silently publishing bad content. A failed build leaves the previously published Pages site intact.
- Routine GitHub commits need no manual rebuild: the publishing workflow runs automatically on pushes to \`main\`.

### Check changes locally (optional)

From the repository root with Python **3.12+** installed:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/update_papers.py --offline
python3 -m http.server 8000 --directory site
```

Open http://localhost:8000/ to preview. \`--offline\` uses the last cached publication data; omitting it fetches newer data from arXiv and Orbit. Do not commit generated changes blindly; review them as with any other website change.

## GitHub Pages and publication workflow

The repository is [jakoblem/hata](https://github.com/jakoblem/hata) and its Pages site is [jakoblem.github.io/hata](https://jakoblem.github.io/hata/). Publishing requires **Settings → Pages → Source: GitHub Actions** and Actions permissions suitable for deployment. The workflow in [\`.github/workflows/publish.yml\`](.github/workflows/publish.yml) builds on pushes to \`main\`, on manual **Run workflow**, and daily at 05:17 UTC. It runs tests, refreshes papers, renders HTML, and uploads \`site/\` as the Pages artifact. As a best effort it also commits refreshed \`site/index.html\` and the paper cache back to \`main\`; branch protection may prevent that commit without blocking Pages deployment.

The canonical DTU hostname, https://hata.compute.dtu.dk/, is separately hosted and must be deployed using the optional, IT-approved mechanism described below. Merely publishing GitHub Pages does not update that hostname.

## Research news: arXiv + DTU Orbit

The automatic publication feed is generated daily by [`scripts/update_papers.py`](scripts/update_papers.py) using author names in [`config/authors.json`](config/authors.json). On each build it is combined with manual entries in [`content/papers.toml`](content/papers.toml), and the Other news section is read from [`content/news.toml`](content/news.toml).

- **arXiv** — queried through the Atom API for full author names/aliases; exact bylines are checked after fetching. Uses the original *first submission date*, not later revision dates.
- **DTU Orbit** — the script reads each researcher's public `/publications/` page, finds publication links, and collects their *publication years*. The current public portal is HTML; **this is best-effort scraping, not a DTU-supported stable API**. It may need a change if the portal markup or access rules change.
- **Deduplication** — matches by arXiv identifier, Orbit publication URL or highly similar normalized titles. Results are retained in `site/data/papers.json`; where a paper appears in both, both **Orbit · arXiv** links are shown on a single row.
- **Dates** — Orbit-only records show a *year*, not a fabricated month/day. A publication year is not the same thing as the first arXiv submission date or the date a record was added to Orbit. List order is therefore approximate for Orbit-only records.
- **Resilience** — when an upstream source fails, the published static site keeps its last known entries. Browser visitors never wait for arXiv or Orbit.
- **Source health** — online refreshes exit with code 2 after building the cached site if either source or any Orbit profile fails (including empty/unreadable HTML). The workflow still publishes that build, then fails a separate `source-health` job. See the build summary and `publication-source-health` artifact for per-profile errors, last successful refresh and consecutive failure counts. `site/data/source-status.json` persists this information when the best-effort cache commit succeeds; otherwise history remains in Actions artifacts. Offline builds never claim a successful source refresh or change health history.
- **Completeness** — a five-item **highlights** section is not a complete bibliography. The homepage links to targeted HATA searches in arXiv and Orbit, while each researcher card links to the individual Orbit profile. Orbit's combined search can miss records, so the individual profiles are the safer route for complete Orbit coverage.

There are verified sample papers from arXiv and Orbit committed into the initial cache. Publication records from Orbit's public pages were checked in October 2026 (for example, *Two results on polynomially-generated wavelet frames and nonorthogonal polynomial frames*, *Weaving information packets* and *Cyclic frames in finite-dimensional Hilbert spaces*). The Orbit parsing algorithm has fixtures and unit tests, but **a live Orbit refresh must still be checked after its first GitHub run**. A guaranteed feed would be better provided by DTU Library via an approved Pure/Orbit API or export.

The existing HTML collector has no API key, but is currently blocked by Orbit's Cloudflare challenge. It does not bypass the challenge or retry HTTP 401/403. **A green Pages deployment is not evidence that Orbit refreshed.** See [Orbit investigation and integration prerequisites](docs/orbit-integration.md) for tested endpoints, alternatives and the precise information needed from DTU Library. An approved API/export can replace the collector without changing the webpage; no speculative API adapter or credential has been added.

## Researcher portraits and the paper figure

The image links on each person card point to the corresponding DTU Orbit portrait assets (the photo IDs correspond to the staff CWIS profile IDs). Their URLs are from DTU's published researcher profiles. **These external photo URLs need checking on the published page**; DTU can change them or restrict hotlinking.

If an external photo does not load, the page switches to a locally hosted fallback portrait extracted from the supplied historical HATA archive. This is to avoid blank cards. When current high-resolution CWIS photos are available and redistribution is approved, it would be better to save those locally in `site/assets/people/` so the page has no external image dependency.

The featured plot `site/assets/papers/gabor-frame-hyperbolic-slits.webp` is an optimized web image from the one-page PDF supplied by the researcher, with a caption and link to [arXiv:2601.07642](https://arxiv.org/abs/2601.07642). Future selected figures can be added **manually** without introducing a news-editor burden. Avoid automatic extraction from third-party papers unless licensing permits it.

## DTU server: recommended GitHub Actions SSH/rsync deployment

When DTU Compute IT provides the SSH host, web-root path and a dedicated deployment account, the daily GitHub Action can update both GitHub Pages **and** the DTU server in one job, avoiding a second cron schedule. This only transfers the already-generated files under `site/`; the DTU server does not need Python, PHP, or Git.

**Caution:** The linked DTU ITS wiki `https://itswiki.compute.dtu.dk/index.php/Web_server` returned **403 Forbidden** from our environment. We have not confirmed the correct host, document root, group ownership, SSH accessibility from the public internet, or DTU's local policies. Do not guess these settings.

In **GitHub → Settings → Secrets and variables → Actions**, configure:

| Kind | Name | Value |
|---|---|---|
| Variable | `DTU_DEPLOY_ENABLED` | `true` **only once the destination has been verified** |
| Variable | `DTU_SSH_HOST` | Hostname supplied by DTU Compute IT |
| Variable | `DTU_SSH_USER` | SSH deployment account |
| Variable | `DTU_WEB_ROOT` | **Dedicated, writable directory for this site only** |
| Variable | `DTU_SSH_PORT` | Optional; defaults to 22 |
| Secret | `DTU_SSH_PRIVATE_KEY` | Dedicated SSH private key (not your personal main key) |
| Secret | `DTU_SSH_KNOWN_HOSTS` | **Verified** host-key line(s), provided or confirmed by IT |

`DTU_DEPLOY_ENABLED` is **unset/off by default**, so GitHub Pages builds do not require DTU access. The script [`scripts/deploy_dtu.sh`](scripts/deploy_dtu.sh) checks input paths and permissions before `rsync`. It uses `--delete` to remove stale files, which is safe **only when the destination directory contains nothing unrelated to HATA**. Back up the old PHP site, and get the exact folder approved before enabling this.

**Avoid posting SSH credentials in the repository or a chat.** Place the private key only in GitHub Actions Secrets. Restrict its server access to the dedicated HATA directory where possible.

### Alternative: cron on the DTU server

If the DTU host cannot accept inbound SSH from GitHub Actions (firewall/policy), a DTU-side cron can pull the public GitHub repo and copy `site/` to the dedicated web root. The helper [`scripts/pull_dtu.sh`](scripts/pull_dtu.sh) is included. It is a pull model: credentials stay on DTU, not GitHub.

Provision once on the DTU server (the paths are **examples only**):

```sh
git clone https://github.com/jakoblem/hata.git "$HOME/hata-repo"
mkdir -p /path/verified/dedicated/hata-webroot
# Test manually:
HATA_REPO="$HOME/hata-repo" HATA_WEB_ROOT=/path/verified/dedicated/hata-webroot \
  bash "$HOME/hata-repo/scripts/pull_dtu.sh"
```

Then, **after consulting DTU IT**, add a cron entry running that command daily *after* GitHub's publication workflow. For example, with the confirmed paths inserted:

```crontab
# Illustrative only; cron's timezone must be checked.
45 7 * * * HATA_REPO=/home/USERNAME/hata-repo HATA_WEB_ROOT=/VERIFIED/DEDICATED/WEBROOT /bin/bash /home/USERNAME/hata-repo/scripts/pull_dtu.sh >> /home/USERNAME/hata-sync.log 2>&1
```

The pull variant relies on GitHub Actions committing refreshed `site/index.html` and `site/data/papers.json` back to `main`. **If bot commits are blocked, this cron job only downloads the previously committed snapshot.** Either allow such commits or run the updater locally on the DTU machine before `rsync` (requires outbound access to arXiv and Orbit), or fetch a published Pages artifact.

The canonical HATA domain is hosted by DTU; it should not be set as a GitHub Pages custom domain when the actual files are served by DTU. DTU IT controls the HTTPS certificate, virtual host and DNS.

## Local development

The commands above run the unit tests, build offline, and start a preview server. For an online refresh use `python3 scripts/update_papers.py` without `--offline`.

The deployable site is the complete **contents** of `site/`, not the project root.

```
content/news.toml             # Manual news entries; edit here
content/papers.toml           # Manual submitted/accepted/published papers; edit here
templates/index.html          # Source HTML with generated-content slots
site/
  index.html                  # Generated page: do not hand edit
  assets/styles.css
  assets/analysis.svg
  assets/people/              # Historical fallback headshots
  assets/papers/              # Optimized figure from supplied PDF
  data/papers.json            # Last-known merged arXiv + Orbit records
config/authors.json           # Authors and Orbit profile slugs
scripts/content_build.py      # TOML parsing and safe HTML rendering
scripts/update_papers.py      # Fetch, merge, deduplicate, build
scripts/deploy_dtu.sh         # Optional GitHub → DTU SSH upload
scripts/pull_dtu.sh           # Optional DTU cron pull
.github/workflows/publish.yml # Daily workflow and Pages publication
tests/test_content_build.py   # Content parsing/build tests
tests/test_update_papers.py   # arXiv/Orbit fixtures and tests
```

The PHP-based historical PmWiki website was used for background and locally hosted fallback photographs only. It is not deployed.
