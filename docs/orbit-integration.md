# DTU Orbit integration investigation

Checked 14 October 2026. No credentials, browser challenge solving, proxy rotation or alternative identities were used. The existing public HTML collector remains best effort, not an approved machine interface. The changes in this PR improve failure detection and cache retention; they do not restore Orbit discovery.

## What is established

- [14 October run](https://github.com/jakoblem/hata/actions/runs/38548599429): all three person publication pages returned 403; 65 fetched arXiv entries, zero Orbit entries, 70 retained papers and successful Pages deployment. [13 October run](https://github.com/jakoblem/hata/actions/runs/38399730185) has the same pattern. “65” counts fetched entries, not newly discovered papers.
- A fresh unauthenticated request to `https://orbit.dtu.dk/en/persons/jakob-lemvig/publications/` returned **403**, `Server: cloudflare`, `cf-mitigated: challenge`, with an HTML “Just a moment...” page. This establishes a challenge for this client/network, not the exact WAF rule applied to the GitHub runner. The historical logs do not contain enough response headers to prove that rule; DTU/Elsevier can confirm it using request time and Cloudflare request IDs.
- The script catches every profile failure and returns an empty list; with a valid cache it previously exited zero. Thus the old workflow tested site availability, not successful data refresh.
- `https://backend.orbit.dtu.dk/ws/oai?verb=Identify` returned HTTP 200 and an OAI-PMH Identify document naming Technical University of Denmark, protocol 2.0, base URL `/ws/oai`, UTC second granularity, earliest datestamp `2014-06-26T10:50:11Z`, and deletedRecord `no`.
- Separate unauthenticated calls to that base with `verb=ListMetadataFormats`, `verb=ListSets`, and `verb=ListRecords&metadataPrefix=oai_dc&from=2026-10-13T00:00:00Z` each returned **403**. Identify alone is not a working harvesting integration. The access policy for these verbs remains unconfirmed; no large harvest was attempted.
- The [DTU-hosted legacy Pure Swagger UI](https://backend.orbit.dtu.dk/ws/api/524/api-docs/index.html) was accessible. Public documentation does not establish permission to fetch records or supply a key. The unversioned `/ws/api/documentation/index.html` could not be retrieved through the research tool; this is not proof that DTU lacks a newer API.

Access can differ by network, time and operation. Do not describe these observations as universal endpoint availability guarantees.

## Options compared

| Route | Access and stability | Coverage / decision |
| --- | --- | --- |
| Current person-page HTML | No credential, but client challenged; undocumented HTML layout, first page only, maximum 12 parsed records per profile | Keep cache and explicit failure reporting pending replacement. Changing User-Agent, browser automation or copying challenge cookies is not the fix. |
| DTU-approved Pure API | Structured/versioned metadata and person associations; institution must confirm API version, endpoint and access definition/key | Preferred for a small three-person incremental integration. Generic Pure supports API keys tied to user privileges and endpoint/field filters; DTU's actual provisioning must be confirmed. |
| DTU backend OAI-PMH | Standard harvesting protocol with datestamps and resumption tokens; Identify works, data operations rejected in this test | Potential alternative after DTU confirms permitted access, schema and person/organisation set/filter. Avoid harvesting the entire university daily merely to find three authors. |
| Publication-list export / RIS / BibTeX | DTU documents publication-list exports from employee profiles; public record pages expose RIS and BibTeX citation text | Good controlled manual or DTU-scheduled export route. No stable, approved unattended export URL was verified. A citation export is not automatically a discovery feed and can omit stable person IDs or canonical Orbit URLs. |
| Orbit → ORCID → public ORCID API | DTU supports researcher-authorized export to ORCID; ORCID documents public-data reads and API client/token requirements | Possible supplement after verifying all three ORCID identities, public works and enabled synchronization. Not an automatic substitute for all Orbit records: visibility, approval, publication status and researcher authorization affect export. |
| Crossref REST | Official public metadata API for records deposited by members | Supplement for DOI publications, not a complete Orbit bibliography or reliable affiliation/person match. Cannot recover all reports, books, conference material or other Orbit-only output. |
| arXiv | Existing supported Atom API with exact byline matching | Retained unchanged; cannot cover publications absent from arXiv. |

## What to request from DTU Library

Contact **orbit@dtu.dk**, the contact published on DTU's About Orbit page. No request has been sent as part of this change. Ask for one supported, read-only integration for the HATA website's daily refresh of Ole Christensen, Jakob Lemvig and Marzieh Hasannasab:

1. Approval to retrieve and republish the required public bibliographic metadata on HATA, including attribution/reuse conditions. Only titles, public author names/associations, publication year, DOI/arXiv IDs and canonical public Orbit links are needed; not abstracts, email addresses, restricted records or full texts.
2. Supported base URL, API version and schema/documentation, authentication header and key provisioning/rotation procedure, or an approved scheduled export. If Pure API: a least-privilege read-only system account/key/access definition for persons and research outputs, restricted to public records/fields. Confirm endpoint permissions and field filters; an API key alone may not expose the needed fields.
3. Verified stable person UUIDs for all three researchers (especially Hasannasab's longer Orbit name), filtering syntax and canonical publication identifiers/URLs. Avoid matching initials alone.
4. Incremental modification timestamp semantics (distinct from publication year), pagination/resumption rules, initial backfill scope, rate limits, permitted frequency and support contact. If OAI: permitted verbs, metadataPrefix, setSpec/person scoping, resumptionToken behavior and deletion policy. Its observed `deletedRecord=no` must not cause local cache deletion assumptions.
5. Confirmation that GitHub-hosted Actions may call the endpoint. If fixed egress or an institutional network is required, agree on a DTU-managed scheduled export/runner rather than attempting to defeat Cloudflare.
6. One small representative response/export with title, authors, year, identifiers, links and multi-author associations, plus an empty-success example. Verify it against actual records before implementing the adapter. Store any resulting key in GitHub Actions secrets, never in the website or repository.

When access is supplied, replace `fetch_orbit` with a schema-validated, paginated adapter, reuse the existing merge/render functions and test identifier mapping, overlapping author results, changed titles, incremental updates, empty valid results and partial failures. Keep failure state independent of cache content. In the meantime, `content/papers.toml` is the supported manual route for missing publications; do not invent records to fill the gap.

## Operational behavior after this change

- Online updater writes the static page and merged cache before returning **exit 2** for degraded source health. Other errors remain fatal and prevent deployment.
- The workflow requires an explicit completion marker written only after rendering and diagnostics succeed, and handles only exit 2 as a cache fallback. Python startup/argument errors and unexpected failures cannot authorize publication. It uploads diagnostics, commits cache and health on a best-effort basis, and publishes Pages. A separate `source-health` job then fails the overall run when any required source/profile was unsuccessful. Partial Orbit success is also degraded.
- `site/data/source-status.json` records check time, per-source status, fetched-entry count, per-profile errors, consecutive failures and last successful source refresh. The first record does not fabricate historic success dates. If GitHub branch settings prevent the best-effort commit, counters cannot persist across fresh checkouts; the timestamped Actions artifacts still preserve each run's diagnostics.
- Offline rebuilds make no network requests and do not modify source health. Existing paper merge rules retain both arXiv/Orbit links and coalesce overlaps. The old 100-paper truncation is removed so growth cannot silently discard older cached papers. The arXiv query's existing 100-result limit remains; this change is not a complete historical backfill.

## Primary references

- [DTU Library: About DTU Orbit, exports, management and contact](https://www.bibliotek.dtu.dk/en/research-service/research-publishing/research-output/dtu-orbit)
- [DTU Library: system relationships and authorized ORCID export](https://www.bibliotek.dtu.dk/en/dress-up/relationship)
- [DTU's Orbit-to-ORCID quick guide](https://www.bibliotek.dtu.dk/english/-/media/Andre_Universitetsenheder/Bibliotek/pdf/DTU-ORBIT-ORCID-quickguide_2021.ashx)
- [Example public Orbit record with RIS and BibTeX](https://orbit.dtu.dk/en/publications/bayesian-decomposition-using-besov-priors/)
- [Pure API documentation: keys, user privileges and access definitions (TU Delft installation; general Pure behavior, not DTU provisioning)](https://pure.tudelft.nl/ws/api/documentation/user-guide/api-keys.html)
- [OAI-PMH specification](https://www.openarchives.org/OAI/openarchivesprotocol.html)
- [ORCID API: reading public records](https://info.orcid.org/documentation/api-tutorials/api-tutorial-read-data-on-a-record/)
- [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)

## Quality assurance — 16 October 2026

Reviewed PR #2 at `beecb4ae989e21483d81fe29e68afe8ba3ed6563`. The [updated PR run](https://github.com/jakoblem/hata/actions/runs/38963252005) passed all 21 tests and the offline build; production build, Pages deployment and source-health jobs were skipped as intended for a PR. Local offline rendering preserved both generated HTML and the full 70-publication JSON cache byte-for-byte.

An additional workflow defect was reproduced and fixed during review: Python startup failures (for example, an unavailable updater script) can also exit 2. Previously the shell accepted that as a completed cached build. The updater now emits `refresh_completed=true` only after rendering and health diagnostics complete; the shell requires this marker before considering exit 2 a safe source fallback. Regression tests execute the production shell with success, degraded refresh, fatal failure and missing completion, including a stale diagnostic file. Injected render errors, diagnostic write failures and unexpected source exceptions never authorize deployment.

The separate source-health shell was also exercised with `SOURCES_DEGRADED=false` (exit 0), `true`, empty and unexpected values (all exit 1). Pages depends only on the successful build, so this later health failure does not block publication. Source-health uses `always()` after build/deploy dependencies, conditioned on a successful build; an unsuccessful build blocks deployment and itself reports failure. A failed Pages deployment remains a deployment failure even when sources are healthy.

At this review stage, main and live production behavior remain unchanged and unverified for this PR; merging awaits production approval. After merge, verify the actual main run: successful cached build and Pages deployment, failed source-health on Orbit denial, uploaded per-profile diagnostics, unchanged valid publication records, and successful best-effort health-history commit. This is a required follow-up, not evidence supplied by the green PR run.

The [16 October 09:54 UTC production run](https://github.com/jakoblem/hata/actions/runs/38883670400) still used the old main code: all three Orbit profiles returned HTTP 403, arXiv returned 65 fetched entries and the site retained 70 distinct publications. The run and Pages deployment both reported success. The access problem therefore remains open. Obtain DTU-approved API/export access using the requirements above; neither this PR nor its completion marker grants Orbit access. No access request was sent.
