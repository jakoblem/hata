import unittest
import copy
import json
import tempfile
import urllib.error
from pathlib import Path
from unittest.mock import patch
from scripts import update_papers as p

MEMBERS = [
    {"name": "Jakob Lemvig", "arxiv_names": ["Jakob Lemvig"], "orbit_slug": "jakob-lemvig"},
    {"name": "Marzieh Hasannasab", "arxiv_names": ["Marzieh Hasannasab", "Marzieh Hasannasabjaldehbakhani"], "orbit_slug": "marzieh-hasannasabjaldehbakhani"},
]
FEED = b'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry><id>http://arxiv.org/abs/2701.12345v2</id><published>2027-01-19T12:00:00Z</published><updated>2027-02-02T13:00:00Z</updated>
  <title>An interesting &amp; structured &lt;signal&gt;</title><author><name>Jakob Lemvig</name></author><author><name>A Collaborator</name></author>
  <arxiv:primary_category term="math.FA"/></entry>
  <entry><id>http://arxiv.org/abs/2701.01010v1</id><published>2027-01-02T10:00:00Z</published><title>Directional frames</title>
  <author><name>Marzieh Hasannasab</name></author></entry>
  <entry><id>http://arxiv.org/abs/2701.77777v1</id><published>2027-01-22T10:00:00Z</published><title>Unrelated work</title>
  <author><name>A Different Person</name></author></entry>
  <entry><id>http://arxiv.org/abs/2701.88888v1</id><published>2027-01-23T10:00:00Z</published><title>Jakob-like but unrelated</title>
  <author><name>Jakob Lemvigg</name></author></entry>
</feed>'''
ORBIT = b'''<!doctype html><html><body>
<ul class="list-results">
 <li><div class="rendering rendering_researchoutput rendering_short">
  <h3 class="title"><a href="/en/publications/an-interesting-structured-signal/">An interesting &amp; structured &lt;signal&gt;</a></h3>
  <span class="persons">Lemvig, J. &amp; A. Collaborator, 2027, In: Sample journal.</span>
 </div></li>
 <li><div class="rendering">
  <h3><a href="/en/publications/only-on-orbit-in-2026/">A purely institutional journal article</a></h3>
  <span>Jakob Lemvig, 2026, In: Journal.</span>
 </div></li>
 <li><h3><a href="https://other.example/en/publications/spoofed/">Do not follow outside links</a></h3><span>2027</span></li>
</ul></body></html>'''


class UpdateTests(unittest.TestCase):
    def test_access_denied_is_not_retried_and_reports_challenge(self):
        for code in (401, 403):
            error = urllib.error.HTTPError('https://orbit.dtu.dk/', code, 'Denied',
                                           {'cf-mitigated': 'challenge'}, None)
            with patch.object(p.urllib.request, 'urlopen', side_effect=error) as request, \
                 patch.object(p.time, 'sleep') as sleep:
                with self.assertRaisesRegex(RuntimeError, f'HTTP {code}.*Cloudflare challenge'):
                    p.fetch_url('https://orbit.dtu.dk/', attempts=3)
                self.assertEqual(request.call_count, 1)
                sleep.assert_not_called()

    def test_transient_http_error_still_retries(self):
        error = urllib.error.HTTPError('https://orbit.dtu.dk/', 503, 'Unavailable', {}, None)
        with patch.object(p.urllib.request, 'urlopen', side_effect=error) as request, \
             patch.object(p.time, 'sleep'):
            with self.assertRaisesRegex(RuntimeError, 'HTTP 503'):
                p.fetch_url('https://orbit.dtu.dk/', attempts=2)
            self.assertEqual(request.call_count, 2)

    def test_partial_profile_failure_and_empty_challenge_are_unhealthy(self):
        for bad in (RuntimeError('HTTP 403'), b'<html>Just a moment...</html>'):
            health = []
            with patch.object(p, 'fetch_url', side_effect=[ORBIT, bad]):
                papers = p.fetch_orbit(MEMBERS, health)
            self.assertEqual(len(papers), 2)
            self.assertEqual([x['status'] for x in health], ['ok', 'error'])
            self.assertIn('error', health[1])

    def test_degraded_update_preserves_real_cache_and_builds_before_exit(self):
        original = json.loads(p.DATA.read_text())
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / 'papers.json'
            page = Path(directory) / 'index.html'
            status = Path(directory) / 'source-status.json'
            summary = Path(directory) / 'summary.md'
            data.write_text(json.dumps(original))
            with patch.multiple(p, DATA=data, PAGE=page, STATUS=status), \
                 patch.dict(p.os.environ, {'GITHUB_STEP_SUMMARY': str(summary)}), \
                 patch.object(p, 'fetch_atom', side_effect=RuntimeError('arXiv offline')), \
                 patch.object(p, 'fetch_url', side_effect=RuntimeError('HTTP 403')):
                for expected_count in (1, 2):
                    with self.assertRaises(SystemExit) as result:
                        p.update()
                    self.assertEqual(result.exception.code, 2)
                    self.assertEqual(json.loads(data.read_text())['papers'], original['papers'])
                    report = json.loads(status.read_text())
                    self.assertFalse(report['healthy'])
                    self.assertEqual(report['sources']['orbit']['consecutive_failures'], expected_count)
                    self.assertEqual(len(report['sources']['orbit']['profiles']), 3)
                    self.assertIn('<!doctype html>', page.read_text().lower())
                last_report = status.read_bytes()
                p.update(offline=True)
                self.assertEqual(status.read_bytes(), last_report)
                self.assertIn('consecutive failed refreshes', summary.read_text())

    def test_recovery_resets_failures_and_retains_last_success_on_next_failure(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(p, 'STATUS', Path(directory) / 'status.json'), \
             patch.dict(p.os.environ, {'GITHUB_STEP_SUMMARY': ''}):
            good = {'orbit': {'status': 'ok', 'entries': 2}}
            bad = {'orbit': {'status': 'error', 'entries': 0}}
            self.assertFalse(p.write_health(copy.deepcopy(bad)))
            self.assertTrue(p.write_health(good))
            self.assertEqual(good['orbit']['consecutive_failures'], 0)
            self.assertIsNotNone(good['orbit']['last_success'])
            self.assertFalse(p.write_health(bad))
            self.assertEqual(bad['orbit']['last_success'], good['orbit']['last_success'])
            self.assertEqual(bad['orbit']['consecutive_failures'], 1)

    def test_fresh_arxiv_survives_orbit_failure_and_success_can_recover(self):
        original = json.loads(p.DATA.read_text())
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / 'papers.json'
            page = Path(directory) / 'index.html'
            status = Path(directory) / 'source-status.json'
            data.write_text(json.dumps(original))
            with patch.multiple(p, DATA=data, PAGE=page, STATUS=status), \
                 patch.dict(p.os.environ, {'GITHUB_STEP_SUMMARY': ''}), \
                 patch.object(p, 'fetch_atom', return_value=FEED), \
                 patch.object(p, 'fetch_url', side_effect=RuntimeError('HTTP 403')):
                with self.assertRaises(SystemExit):
                    p.update()
            updated = json.loads(data.read_text())['papers']
            self.assertTrue({x['id'] for x in original['papers']} <= {x['id'] for x in updated})
            self.assertIn('2701.12345', {x['id'] for x in updated})
            self.assertEqual(json.loads(status.read_text())['sources']['arxiv']['status'], 'ok')
            with patch.multiple(p, DATA=data, PAGE=page, STATUS=status), \
                 patch.dict(p.os.environ, {'GITHUB_STEP_SUMMARY': ''}), \
                 patch.object(p, 'fetch_atom', return_value=FEED), \
                 patch.object(p, 'fetch_url', return_value=ORBIT):
                p.update()
            report = json.loads(status.read_text())
            self.assertTrue(report['healthy'])
            self.assertEqual(report['sources']['orbit']['consecutive_failures'], 0)
            rows = json.loads(data.read_text())['papers']
            both = [x for x in rows if x.get('arxiv_id') == '2701.12345']
            self.assertEqual(len(both), 1)
            self.assertIsNotNone(both[0]['orbit_url'])

    def test_cache_does_not_drop_older_papers_at_100_records(self):
        rows = [dict(p.parse_atom(FEED, MEMBERS)[0], id=f'2701.{i:05}',
                     arxiv_id=f'2701.{i:05}', title=f'Paper {i}') for i in range(105)]
        self.assertEqual(len(p.merge_papers(rows, [])), 105)

    def test_query_contains_each_author(self):
        self.assertIn('au:"Jakob Lemvig"', p.create_query(MEMBERS))

    def test_parser_exact_name_and_first_submission(self):
        result = p.parse_atom(FEED, MEMBERS)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "2701.12345")
        self.assertEqual(result[0]["published"], "2027-01-19")
        self.assertEqual(result[0]["matched_members"], ["Jakob Lemvig"])

    def test_orbit_parser_and_year_not_day(self):
        result = p.parse_orbit(ORBIT, MEMBERS[0])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['published'], '2027-01-01')
        self.assertEqual(result[0]['date_precision'], 'year')
        self.assertEqual(result[1]['orbit_year'], 2026)
        self.assertTrue(all(u['orbit_url'].startswith('https://orbit.dtu.dk/') for u in result))

    def test_merge_deduplicates_by_title_preserves_both_links(self):
        fresh = p.parse_atom(FEED, MEMBERS)
        orbit = p.parse_orbit(ORBIT, MEMBERS[0])
        older = dict(fresh[0]); older['title'] = 'An older title'
        merged = p.merge_papers([older], orbit + fresh)
        self.assertEqual(len(merged), 3)
        both = next(x for x in merged if x.get('arxiv_id') == '2701.12345')
        self.assertIn('an-interesting', both['orbit_url'])
        self.assertIn('A Collaborator', both['authors'])
        self.assertEqual(both['published'], '2027-01-19')
        self.assertEqual(both['orbit_year'], 2027)
        self.assertEqual(p.merge_papers(merged, merged), merged)

    def test_render_escapes_and_shows_orbit_and_arxiv(self):
        merged = p.merge_papers(p.parse_orbit(ORBIT, MEMBERS[0]), p.parse_atom(FEED, MEMBERS))
        rendered = p.render_news(merged)
        self.assertIn('An interesting &amp; structured &lt;signal&gt;', rendered)
        self.assertNotIn('<signal>', rendered)
        self.assertIn('datetime="2027-01-19"', rendered)
        self.assertIn('datetime="2026" class="orbit-year"', rendered)
        self.assertIn('Orbit <span', rendered)
        self.assertIn('arXiv <span', rendered)
        self.assertNotIn('2701.77777', rendered)

    def test_untrusted_ids_and_urls_rejected(self):
        self.assertFalse(p.valid_cache_row({'id': '../../contact', 'title': 'x', 'authors': [], 'published': '2027-01-01'}))
        self.assertFalse(p.valid_cache_row({'id': '2701.12345', 'title': 'x', 'authors': [], 'published': 'not-date'}))
        self.assertFalse(p.valid_orbit_url('https://evil.example/en/publications/injected/'))
        self.assertFalse(p.valid_orbit_url('https://orbit.dtu.dk/en/publications/foo/?x=bad'))


if __name__ == '__main__':
    unittest.main()
