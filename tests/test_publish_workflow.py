"""Exercise the production shell gate without deploying or using the network."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import update_papers as p


def refresh_shell():
    lines = (p.ROOT / '.github/workflows/publish.yml').read_text().splitlines()
    start = lines.index('        id: refresh')
    start = lines.index('        run: |', start) + 1
    body = []
    for line in lines[start:]:
        if line and not line.startswith('          '):
            break
        body.append(line[10:])
    return '\n'.join(body)


class PublishWorkflowTests(unittest.TestCase):
    def test_production_shell_requires_completion_and_classifies_exit_codes(self):
        # A stale diagnostic file must not legitimize a startup failure.
        for code, completed, expected in [(0, True, 0), (2, True, 0),
                                          (1, True, 1), (127, False, 1),
                                          (2, False, 1), (0, False, 1)]:
            with self.subTest(code=code, completed=completed), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                (root / 'site/data').mkdir(parents=True)
                (root / 'site/data/source-status.json').write_text('{"healthy": false}')
                executable = root / 'python'
                executable.write_text('#!/bin/sh\n' + (
                    'echo refresh_completed=true >> "$GITHUB_OUTPUT"\n' if completed else ''
                ) + f'exit {code}\n')
                executable.chmod(0o755)
                output = root / 'output'
                output.touch()
                result = subprocess.run(
                    ['bash', '--noprofile', '--norc', '-e', '-o', 'pipefail', '-c', refresh_shell()],
                    cwd=root, env={**os.environ, 'PATH': str(root) + os.pathsep + os.environ['PATH'],
                                   'GITHUB_OUTPUT': str(output)}, capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
                if expected == 0:
                    self.assertIn(f'degraded={str(code == 2).lower()}', output.read_text())
                else:
                    self.assertNotIn('degraded=true', output.read_text())

    def test_updater_marks_completed_degraded_build_only_after_diagnostics(self):
        for failure in (None, 'render', 'diagnostics', 'unexpected-source'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                data, page, status, output = (root / n for n in ('papers.json', 'index.html', 'status.json', 'output'))
                data.write_bytes(p.DATA.read_bytes())
                output.touch()
                render = p.content_build.build_html
                health = p.write_health
                with patch.multiple(p, DATA=data, PAGE=page, STATUS=status), \
                     patch.dict(os.environ, {'GITHUB_OUTPUT': str(output), 'GITHUB_STEP_SUMMARY': ''}), \
                     patch.object(p, 'fetch_atom', side_effect=(TypeError('unexpected') if failure == 'unexpected-source' else RuntimeError('offline'))), \
                     patch.object(p, 'fetch_url', side_effect=RuntimeError('HTTP 403')), \
                     patch.object(p.content_build, 'build_html', side_effect=(ValueError('bad template') if failure == 'render' else render)), \
                     patch.object(p, 'write_health', side_effect=(OSError('disk full') if failure == 'diagnostics' else health)):
                    if failure:
                        with self.assertRaises((ValueError, OSError, TypeError)):
                            p.update()
                        self.assertEqual(output.read_text(), '')
                    else:
                        with self.assertRaises(SystemExit) as result:
                            p.update()
                        self.assertEqual(result.exception.code, 2)
                        self.assertEqual(output.read_text(), 'refresh_completed=true\n')
                        self.assertEqual(json.loads(data.read_text())['papers'], json.loads(p.ROOT.joinpath('site/data/papers.json').read_text())['papers'])
                        self.assertIn('<!doctype html>', page.read_text().lower())
                        self.assertFalse(json.loads(status.read_text())['healthy'])
