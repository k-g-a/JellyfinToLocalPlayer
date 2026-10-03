"""Build the fork's two Windows release archives.

Both packages use the Jellyfin-only application layout. Only python_embed is
borrowed from the pinned original-author runtime archive.
"""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[2]
SOURCE_ASSET = "JellyfinToLocalPlayer.zip"
EMBEDDED_ASSET = "JellyfinToLocalPlayer-python-embed-win32.zip"


def copy_project(destination: Path) -> None:
    destination.mkdir(parents=True)
    for filename in (
        "main.py", "config.ini", "launch.bat", "launch.command",
        "launch-via-screen.command", "LICENSE", "README.md", "requirements.txt",
    ):
        shutil.copy2(ROOT / filename, destination / filename)
    for directory in ("code", "scripts", "docs"):
        shutil.copytree(
            ROOT / directory, destination / directory,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )


def add_embedded_python(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as source:
        runtime_members = []
        for member in source.infolist():
            parts = PurePosixPath(member.filename).parts
            try:
                runtime_index = parts.index("python_embed")
            except ValueError:
                continue
            relative = parts[runtime_index:]
            if not relative or ".." in parts or "\\" in member.filename or ":" in member.filename:
                raise RuntimeError(f"Unsafe embedded runtime entry: {member.filename}")
            runtime_members.append((member, relative))

        if not runtime_members:
            raise RuntimeError("Pinned upstream archive does not contain python_embed")

        for member, relative in runtime_members:
            target = destination.joinpath(*relative)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open(member) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)

    if not (destination / "python_embed/python.exe").is_file():
        raise RuntimeError("Embedded Python extraction did not produce python_embed/python.exe")


def write_zip(source: Path, destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                output.write(path, path.relative_to(source).as_posix())


def validate_archive(path: Path, embedded: bool) -> None:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
    required = {
        "main.py",
        "config.ini",
        "launch.bat",
        "scripts/jellyfinToLocalPlayer.injector.js",
        "code/configs.py",
        "code/__init__.py",
        "docs/migration.md",
        "requirements.txt",
    }
    missing = required - names
    if missing:
        raise RuntimeError(f"{path.name} is missing: {sorted(missing)}")
    forbidden = [name for name in names if not name.startswith("python_embed/") and (name.startswith((
        "utils/", "user_script/", "emby", "qbittorrent", ".instances/"))
        or "__pycache__" in name or name.endswith((".user.js", ".lua", "_token.json")))]
    if forbidden:
        raise RuntimeError(f"Unexpected release files: {sorted(forbidden)}")
    has_python = "python_embed/python.exe" in names
    if has_python != embedded:
        raise RuntimeError(f"{path.name}: embedded Python state is {has_python}, expected {embedded}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedded-python-archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        system_package = work / "system-python"
        embedded_package = work / "embedded-python"
        copy_project(system_package)
        shutil.copytree(system_package, embedded_package)
        add_embedded_python(args.embedded_python_archive, embedded_package)

        system_zip = args.output / SOURCE_ASSET
        embedded_zip = args.output / EMBEDDED_ASSET
        write_zip(system_package, system_zip)
        write_zip(embedded_package, embedded_zip)
        validate_archive(system_zip, embedded=False)
        validate_archive(embedded_zip, embedded=True)

        print(f"Built {system_zip}")
        print(f"Built {embedded_zip}")


if __name__ == "__main__":
    main()
