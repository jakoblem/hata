# HATA — Harmonic Analysis: Theory and Application

A low-maintenance static homepage for HATA at DTU Compute's Mathematics section.

**Website (after enabling Pages):** https://jakoblem.github.io/hata/  
**Repository:** https://github.com/jakoblem/hata  
**Planned DTU address:** https://hata.compute.dtu.dk/

The web site is plain HTML/CSS/images in [`site/`](site/). No PHP, CMS, JavaScript framework, browser-side requests to publication APIs, build dependencies, cookies or tracking. A Python standard-library script compiles research highlights into static HTML. No knowledge of Git or Python is needed for visitors.

## Submitted manuscripts not yet online

Optional manuscripts are listed in [`config/submitted-papers.json`](config/submitted-papers.json). The `_example` is documentation only; **`"papers": []` keeps this feature inactive**. When a paper has been approved for public announcement, add an entry to `papers` with `title`, `authors` (list), `submitted` (YYYY-MM-DD) and optional `journal`. No PDF or link is needed. It appears as a submitted manuscript with no clickable title. The publication updater suppresses it automatically when an arXiv or Orbit record with the same title is found; remove the manual entry when no longer needed. Do not add confidential submission details without coauthor approval.

## First publication to GitHub Pages

1. Create a **public, empty repository** called `hata` under the `jakoblem` account, with default branch `main`, **without** an initial README or gitignore. Do not create a license yet; choose one after reviewing institutional/licensing constraints on DTU portrait images.
2. Add the complete contents of this project to the **root** of the repository (not the `HATA-homepage/` wrapper directory).
3. In GitHub: **Settings → Pages → Build and deployment → Source → GitHub Actions**.
4. In GitHub: **Settings → Actions → General → Workflow permissions**, select **Read and write permissions** if the controls are available. This is for the optional commit of refreshed publication data. Publishing Pages still works when branch protection blocks such commits.
5. Open **Actions → Publish HATA website → Run workflow**. This runs the unit tests, tries to refresh arXiv and Orbit, and publishes the static site. It also runs on new commits and daily at `05:17 UTC`.
6. Check the site at **https://jakoblem.github.io/hata/**. The source repository URL `github.com/jakoblem/hata` is not the hosted site.

The first deployment must be confirmed in the **Actions** tab and the **Pages** settings. This is a deployment plan; nothing is automatically published merely by downloading this ZIP.

## Research news: arXiv + DTU Orbit

The feed is generated daily in `scripts/update_papers.py` using author names in [`config/authors.json`](config/authors.json).

- **arXiv** — queried through the Atom API for full author names/aliases; exact bylines are checked after fetching. Uses the original *first submission date*, not later revision dates.
- **DTU Orbit** — the script reads each researcher's public `/publications/` page, finds publication links, and collects their *publication years*. The current public portal is HTML; **this is best-effort scraping, not a DTU-supported stable API**. It may need a change if the portal markup or access rules change.
- **Deduplication** — matches by arXiv identifier, Orbit publication URL or highly similar normalized titles. Results are retained in `site/data/papers.json`; where a paper appears in both, both **Orbit · arXiv** links are shown on a single row.
- **Dates** — Orbit-only records show a *year*, not a fabricated month/day. A publication year is not the same thing as the first arXiv submission date or the date a record was added to Orbit. List order is therefore approximate for Orbit-only records.
- **Resilience** — when an upstream source fails, the published static site keeps its last known entries. Browser visitors never wait for arXiv or Orbit.
- **Completeness** — a five-item **highlights** section is not a complete bibliography. The homepage links to targeted HATA searches in arXiv and Orbit, while each researcher card links to the individual Orbit profile. Orbit's combined search can miss records, so the individual profiles are the safer route for complete Orbit coverage.

There are verified sample papers from arXiv and Orbit committed into the initial cache. Publication records from Orbit's public pages were checked in October 2026 (for example, *Two results on polynomially-generated wavelet frames and nonorthogonal polynomial frames*, *Weaving information packets* and *Cyclic frames in finite-dimensional Hilbert spaces*). The Orbit parsing algorithm has fixtures and unit tests, but **a live Orbit refresh must still be checked after its first GitHub run**. A guaranteed feed would be better provided by DTU Library via an approved Pure/Orbit API or export.

The updater's automatic search does *not* require any institutional API key; if DTU Library provides one later, the scraper can be replaced without changing the webpage.

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

```sh
python3 -m unittest discover -s tests -v
python3 scripts/update_papers.py --offline  # renders last-known cache without network
python3 scripts/update_papers.py            # fetches from both sources
python3 -m http.server 8000 --directory site
# open http://localhost:8000
```

The deployable site is the complete **contents** of `site/`, not the project root.

```
site/
  index.html
  assets/styles.css
  assets/analysis.svg
  assets/people/                # Historical fallback headshots
  assets/papers/                # Optimized figure from supplied PDF
  data/papers.json              # Last known merged records
config/authors.json             # Authors and Orbit profile slugs
scripts/update_papers.py        # Fetch, merge, deduplicate, render
scripts/deploy_dtu.sh           # Optional GitHub → DTU SSH upload
scripts/pull_dtu.sh             # Optional DTU cron pull
.github/workflows/publish.yml   # Daily GitHub workflow and Pages publish
tests/test_update_papers.py     # Offline fixtures and tests
```

The PHP-based historical PmWiki website was used for background and locally hosted fallback photographs only. It is not deployed.
