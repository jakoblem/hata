import unittest
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
    def test_submitted_template_inactive(self):
        self.assertEqual(p.read_submitted_papers(), [])
        self.assertEqual(p.render_submitted_papers([], []), "")

    def test_submitted_manuscript_and_deduplication(self):
        manuscript = {"title": "A study of Gabor frames", "authors": ["Marzieh Hasannasab"], "submitted": "2026-09-03", "journal": ""}
        output = p.render_submitted_papers([manuscript], [])
        self.assertIn("SUBMITTED MANUSCRIPT", output)
        self.assertIn("Not yet publicly available", output)
        self.assertNotIn("<a href=", output)
        self.assertEqual(p.render_submitted_papers([manuscript], [{"title": manuscript["title"], "arxiv_id": "2609.12345"}]), "")

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
