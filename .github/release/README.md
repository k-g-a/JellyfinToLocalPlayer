# Fork release pipeline

Every push or merge to the `fork-release` branch builds and publishes a GitHub release containing:

- `embyToLocalPlayer.zip` for Windows with an installed system Python;
- `etlp-python-embed-win32.zip` with the pinned upstream `python_embed` runtime.

Both archives retain the upstream filenames and contain this fork's backend, configuration, launcher,
documentation, userscripts, and Jellyfin JavaScript Injector script. Only the embedded runtime is taken from
the upstream binary archive. The packaged updater URL is changed to this fork's latest release; the tracked
source file is not changed.

To update the embedded runtime, change `UPSTREAM_EMBED_RELEASE` and, if needed,
`UPSTREAM_EMBED_ASSET` in `.github/workflows/fork-release.yml`. The build fails if the downloaded archive
does not contain `python_embed/python.exe` or either output archive is missing a required project file.
