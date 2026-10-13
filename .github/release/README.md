# Fork release pipeline

PRs targeting `translate` build and smoke-test the packages without publishing.
Push/merge to `fork-release` (or manually dispatch on that branch) to publish:

- `JellyfinToLocalPlayer.zip`: system Python.
- `JellyfinToLocalPlayer-python-embed-win32.zip`: portable Windows embedded Python.

Both archives contain `main.py`, `config.ini`, `launch.bat`, `code/`, `scripts/`, documentation and
requirements from this fork. Removed integrations, tests, tokens and instance state are not packaged.
Only `python_embed/` comes from the pinned original-author runtime archive. The source updater already
points to this fork; the builder does not rewrite source code.

The build validates the layout, compiles the backend and starts the packaged backend with both system
and embedded Python before publishing. Update `UPSTREAM_EMBED_RELEASE` and `UPSTREAM_EMBED_ASSET`
only when changing the runtime deliberately. See [development.md](../../docs/development.md).
