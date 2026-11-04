# Generation cache cleanup failure

Run 41751225429 failed in `Post Run actions/setup-python@v5` for
`short_images (2)`, `short_music`, and `images (10)` because the pip cache
directory did not exist. These jobs deliberately install with `--no-cache-dir`
to leave runner disk space for models and generated media. Enabling
`setup-python`'s `cache: pip` conflicts with that policy: cache saving can fail
after the generation and artifact-upload steps have succeeded.

The CPU music and image jobs in both `music.yml` and reusable `shorts.yml`
therefore omit pip caching. Lightweight jobs that use ordinary pip installs
keep their cache. Generation, dependency installation, and artifact errors
still fail the job; no `continue-on-error` hides a real failure.

`test_workflow_cache.py`, run by Component checks, rejects this configuration
across all active workflows. Run it locally with:

```sh
python -m pip install -r requirements-checks.txt
python -m unittest -v test_workflow_cache
```

Rerunning an old run uses its original workflow definition. Use a new manual
dispatch on the corrected branch after the fix is merged for the updated cache
policy. Before regenerating or publishing, inspect existing artifacts and
durable checkpoints so already completed work can be reused. Removing this
cache conflict does not guarantee that model, network, or publication steps
will always succeed.
