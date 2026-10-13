# Release packaging

The workflow is [.github/workflows/release.yml](../workflows/release.yml).
PRs targeting `main` build and smoke-test both packages and upload a `windows-packages` Actions artifact.
A push/merge to `main`, or a manual dispatch on `main`, publishes those tested packages as a stable release.
Manual dispatch on other branches builds artifacts only.

- `JellyfinToLocalPlayer.zip`: system Python.
- `JellyfinToLocalPlayer-python-embed-win32.zip`: portable Windows embedded Python.
- `SHA256SUMS.txt`: archive checksums.

Both archives contain `main.py`, `config.ini`, `launch.bat`, `code/`, `scripts/`, docs and requirements.
Removed integrations, tests, tokens and instance state are not packaged. Only `python_embed/` comes from
kjtsune's pinned original-author runtime archive. The updater targets this repository; the builder does not
rewrite application source code.

The build validates the layout, compiles the backend and starts the packaged backend with both system and
embedded Python before publication. Update `UPSTREAM_EMBED_RELEASE` and `UPSTREAM_EMBED_ASSET` only
when changing that runtime deliberately. No players are bundled.

Most credit for the playback implementation belongs to [kjtsune](https://github.com/kjtsune/embyToLocalPlayer).
See [development.md](../../docs/development.md) for the development flow, release commands and attribution.
