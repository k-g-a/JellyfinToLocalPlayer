# Development and releases

PRs target `main`. Develop changes on feature branches and review them before merging.
The project develops independently from its Jellyfin-only baseline. Adopt relevant upstream fixes selectively
in separate commits with attribution; there is no routine upstream rebase or translation requirement.

## Run and verify

```sh
python -m pip install -r requirements.txt
python main.py --config config.ini
```

`code/` is the application package; keep its `__init__.py`. It must take precedence over Python's standard
library module of the same name. Run from the repository root or use the provided entry points.

From the repository root:

```sh
python -m compileall -q main.py code tests
python tests/backend.py
python tests/instances.py
npm ci
npm test
```

The backend tests use fixtures/mocks for playback, reporting and updates. The instance test binds local
ports and checks isolated state/status/config validation. Injector tests use jsdom to check native-button
styling, discovery, payloads and preservation of browser APIs. Actual playback still needs a Windows
MPC-HC/MPC-BE check with Jellyfin: launch, resume, seek, close/report, next episode and local path mapping.

## Release cycle

`.github/workflows/release.yml` builds Windows packages for PRs targeting `main` and for pushes to `main`.
PR builds upload the tested packages as the `windows-packages` Actions artifact, without publishing a release.
Merging a PR into `main` automatically builds, tests and publishes a stable GitHub release from that commit.
Manual dispatch on `main` can rebuild/publish a release; dispatch on another branch only builds artifacts.

The publish job runs only after the build job succeeds and receives exactly the archives tested by that job.
Only the publish job has repository write permission. Releases use `release-YYYY.MM.dd.<run number>` tags
and include SHA-256 checksums. The updater's existing latest-release URL continues to work.
The old `translate` → `fork-release` promotion step is retired.
The release builder includes `main.py`, `config.ini`, `launch.bat`, `code/`, `scripts/`, docs and requirements:

- `JellyfinToLocalPlayer.zip`: system-Python package.
- `JellyfinToLocalPlayer-python-embed-win32.zip`: same code plus `python_embed/`.

Only `python_embed/` comes from the pinned original-author runtime archive. The application code, injector,
configuration and docs all come from this repository. No players are bundled. The runtime pin and source asset name
remain in the workflow. Change those separately when deliberately updating embedded Python.

Build locally with an existing runtime archive:

```sh
python .github/release/build_release.py --embedded-python-archive upstream-embed.zip --output artifacts
```

The updater downloads `JellyfinToLocalPlayer.zip` from this repository. Archive names, required files and updater
URL must be changed together if the layout changes again. See [migration.md](migration.md) for old installations.

## Attribution

Most credit belongs to [kjtsune](https://github.com/kjtsune), author of
[embyToLocalPlayer](https://github.com/kjtsune/embyToLocalPlayer). His prior work accounts for roughly 95%
of the implementation at the October 2026 transition to independent development. Preserve LICENSE and
this attribution when distributing code or packages. English docs, Jellyfin-only specialization and injector
integration are additions made in this repository.
