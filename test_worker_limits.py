import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from worker_limits import WorkerFailure, run_worker, service_command


class WorkerLimitsTests(unittest.TestCase):
    def test_limits_reserve_runner_resources_and_exclude_secrets(self):
        with patch.dict(os.environ, {'YOUTUBE_TOKEN_JSON': 'secret', 'ACESTEP_INIT_LLM': 'false'}, clear=True):
            args = service_command(['/python', 'worker.py'], 60, 'test-worker', 16 * 1024**2, 4)
        self.assertIn('MemoryMax=12884901888', args)
        self.assertIn('MemorySwapMax=4G', args)
        self.assertIn('CPUQuota=300%', args)
        self.assertIn('RuntimeMaxSec=60', args)
        self.assertIn('KillMode=control-group', args)
        self.assertIn('--setenv=ACESTEP_INIT_LLM=false', args)
        self.assertFalse(any('secret' in arg for arg in args))
        self.assertEqual(args[-3:], ['--', '/python', 'worker.py'])

    def test_small_runner_fails_before_launch(self):
        with self.assertRaises(WorkerFailure):
            service_command(['python'], 60, 'test', 1024**2, 2)

    def guarded(self, response):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        diagnostic = Path(directory.name)/'worker-resources.txt'
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            if 'systemd-run' in args:
                if isinstance(response, Exception):
                    raise response
                return subprocess.CompletedProcess(args, response)
            return subprocess.CompletedProcess(args, 0, 'Result=oom-kill\nExecMainStatus=9\n', '')
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true'}), patch('worker_limits.sys.platform', 'linux'), patch('worker_limits.Path.exists', return_value=True), patch('worker_limits.Path.read_text', return_value='MemTotal: 16384000 kB\n'), patch('worker_limits.subprocess.run', side_effect=run):
            try:
                run_worker(['python', 'worker.py'], 60, diagnostic)
            finally:
                with diagnostic.open() as saved:
                    self.assertIn('Result=oom-kill', saved.read())
                self.assertTrue(any('stop' in args for args in calls))
                self.assertTrue(any('reset-failed' in args for args in calls))

    def test_oom_is_actionable_and_not_retried(self):
        with self.assertRaisesRegex(WorkerFailure, 'oom-kill'):
            self.guarded(137)

    def test_timeout_stops_the_entire_service_and_records_diagnostics(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            self.guarded(subprocess.TimeoutExpired('worker', 60))

    def test_success_cleans_up_service(self):
        self.guarded(0)

    def test_no_cgroup_never_runs_unbounded_on_actions(self):
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true'}), patch('worker_limits.sys.platform', 'linux'), patch('worker_limits.Path.exists', return_value=False), patch('worker_limits.subprocess.run') as run:
            with self.assertRaisesRegex(WorkerFailure, 'refusing unbounded'):
                run_worker(['python'], 60, 'unused')
            run.assert_not_called()

    def test_local_subprocess_failure_propagates(self):
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'false'}):
            with self.assertRaises(subprocess.CalledProcessError):
                run_worker([sys.executable, '-c', 'raise SystemExit(7)'], 10, 'unused')


if __name__ == '__main__':
    unittest.main()
