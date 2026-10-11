"""Tests for manually maintained TOML content and HTML rendering."""
import datetime as dt
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import content_build as c


class ManualContentTests(unittest.TestCase):
    def test_current_news_migrates_without_losing_content(self):
        news = c.read_news()
        self.assertEqual(len(news), 2)
        markup = c.render_group_news(news)
        self.assertIn('datetime="2026-10" class="orbit-year"', markup)
        self.assertIn('Ole Christensen and Marzieh Hasannasab to visit Jürgen Frikel', markup)
        self.assertIn('Jürgen Frikel · OTH Regensburg', markup)
        self.assertIn('datetime="2026-09-03"', markup)
        self.assertIn('<em>Quantum harmonic and time-frequency methods for concentration problems in phase space</em>', markup)
        self.assertNotIn('HATA_NEWS', markup)

    def test_manual_papers_disabled_initially(self):
        self.assertEqual(c.read_manual_papers(), [])
        self.assertEqual(c.render_manual_papers([], [], lambda a, b: False), '')

    def test_submitted_paper_escapes_and_disappears_on_matching_preprint(self):
        row = dict(title='Frames & <signals>', authors=['Ole Christensen', 'A. Coauthor'],
                   status='submitted', date_value='2026-10-09', date=dt.date(2026, 10, 9),
                   journal='Example Journal', url='', doi='')
        rendered = c.render_manual_papers([row], [], lambda a, b: a['title'] == b['title'])
        self.assertIn('SUBMITTED MANUSCRIPT · Example Journal', rendered)
        self.assertIn('Frames &amp; &lt;signals&gt;', rendered)
        self.assertIn('Not yet publicly available', rendered)
        self.assertEqual(c.render_manual_papers([row], [dict(title=row['title'])],
                         lambda a, b: a['title'] == b['title']), '')

    def test_accepted_and_published_paper_links(self):
        base = dict(title='Published frames', authors=['Marzieh Hasannasab'],
                    date_value='2026', date=dt.date(2026, 1, 1), journal='A journal',
                    url='https://example.org/paper', doi='10.5555/example')
        markup = c.render_manual_papers([dict(base, status='published')], [], lambda a, b: False)
        self.assertIn('JOURNAL PUBLICATION · A journal', markup)
        self.assertIn('https://doi.org/10.5555/example', markup)
        self.assertIn('https://example.org/paper', markup)
        markup = c.render_manual_papers([dict(base, status='accepted', doi='', url='')], [],
                                        lambda a, b: False)
        self.assertIn('ACCEPTED MANUSCRIPT', markup)
        self.assertIn('Publication link forthcoming', markup)

    def test_dates_and_unsafe_urls(self):
        self.assertEqual(c._date('2026-10', 'news')[1], dt.date(2026, 10, 1))
        self.assertEqual(c._date('2026', 'paper')[1], dt.date(2026, 1, 1))
        for invalid in ['2026-13', '2026-02-30', 'October 2026', '2026-1-2']:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                c._date(invalid, 'news')
        for invalid in ['javascript:alert(1)', 'http://example.org', '//example.org', 'https://user:pw@example.org/']:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                c._url(invalid, 'news')
        self.assertEqual(c._description('*A & B* <bad>'), '<em>A &amp; B</em> &lt;bad&gt;')

    def test_build_replaces_placeholders_once(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'index.html'
            path.write_text('before {{HATA_PAPERS}} middle {{HATA_NEWS}} after', encoding='utf-8')
            with patch.object(c, 'TEMPLATE', path):
                generated = c.build_html([], lambda _: 'AUTO', lambda a, b: False)
                self.assertIn('before AUTO middle ', generated)
                self.assertIn('Ole Christensen and Marzieh Hasannasab', generated)
                self.assertTrue(generated.endswith(' after'))
                path.write_text('{{HATA_PAPERS}} only', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'exactly one'):
                    c.build_html([], lambda _: '', lambda a, b: False)


if __name__ == '__main__':
    unittest.main()
