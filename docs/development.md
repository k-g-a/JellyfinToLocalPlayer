# Development and releases

PRs target `translate`. Keep upstream fixes relevant to retained playback features in separate commits,
with attribution. This Jellyfin-only branch has no dependency on the removed companion projects.

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

The release trigger remains a push/merge to `fork-release`, or manual dispatch of that branch's
`.github/workflows/fork-release.yml`. After reviewing and merging the PR into `translate`, merge that commit
into `fork-release` to publish. PRs against `translate` build and smoke-test the Windows packages without
publishing. Opening or merging a PR into `translate` does not publish a release.

The release builder includes `main.py`, `config.ini`, `launch.bat`, `code/`, `scripts/`, docs and requirements:

- `JellyfinToLocalPlayer.zip`: system-Python package.
- `JellyfinToLocalPlayer-python-embed-win32.zip`: same code plus `python_embed/`.

Only `python_embed/` comes from the pinned original-author runtime archive. The application code, injector,
configuration and docs all come from this fork. No players are bundled. The runtime pin and source asset name
remain in the workflow. Change those separately when deliberately updating embedded Python.

Build locally with an existing runtime archive:

```sh
python .github/release/build_release.py --embedded-python-archive upstream-embed.zip --output artifacts
```

The updater downloads `JellyfinToLocalPlayer.zip` from this fork. Archive names, required files and updater
URL must be changed together if the layout changes again. See [migration.md](migration.md) for old installations.
