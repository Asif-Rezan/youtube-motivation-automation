"""Prevent cache cleanup from failing an otherwise successful generation job."""
from pathlib import Path
import unittest

import yaml


def cache_conflicts(workflow):
    conflicts = []
    for name, job in workflow.get('jobs', {}).items():
        steps = job.get('steps', [])
        caches_pip = any(
            step.get('uses', '').startswith('actions/setup-python@')
            and step.get('with', {}).get('cache') == 'pip'
            for step in steps
        )
        bypasses_cache = any('--no-cache-dir' in step.get('run', '') for step in steps)
        if caches_pip and bypasses_cache:
            conflicts.append(name)
    return conflicts


class WorkflowCacheTests(unittest.TestCase):
    def test_active_workflows_do_not_cache_uncached_installations(self):
        root = Path(__file__).resolve().parent / '.github' / 'workflows'
        paths = sorted(root.glob('*.yml')) + sorted(root.glob('*.yaml'))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(workflow=path.name):
                workflow = yaml.safe_load(path.read_text())
                self.assertEqual(cache_conflicts(workflow), [],
                                 'Remove setup-python pip caching from jobs using '
                                 '--no-cache-dir; its post step can fail after generation.')

    def test_detects_conflict_without_flagging_regular_cache_or_reusable_jobs(self):
        cached = {'uses': 'actions/setup-python@v5', 'with': {'cache': 'pip'}}
        uncached = {'uses': 'actions/setup-python@v5'}
        install = {'run': 'pip install --no-cache-dir -r requirements.txt'}
        workflow = {'jobs': {
            'broken': {'steps': [cached, install]},
            'uncached': {'steps': [uncached, install]},
            'cached': {'steps': [cached, {'run': 'pip install -r requirements.txt'}]},
            'reusable': {'uses': './.github/workflows/shorts.yml'},
        }}
        self.assertEqual(cache_conflicts(workflow), ['broken'])
