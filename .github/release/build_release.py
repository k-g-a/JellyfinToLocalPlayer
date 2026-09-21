"""Build the fork's two Windows release archives.

The source tree keeps upstream names and layout. The embedded archive borrows
only the pinned python_embed directory from upstream's binary release.
"""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_UPDATE_URL = (
    "https://github.com/kjtsune/embyToLocalPlayer/releases/latest/"
    "download/embyToLocalPlayer.zip"
)
FORK_UPDATE_URL = (
    "https://github.com/k-g-a/JellyfinToLocalPlayer/releases/latest/"
    "download/embyToLocalPlayer.zip"
)


def copy_project(destination: Path) -> None:
    destination.mkdir(parents=True)
    for filename in (
        "embyToLocalPlayer.py",
        "embyToLocalPlayer_config.ini",
        "LICENSE",
        "README.md",
    ):
        shutil.copy2(ROOT / filename, destination / filename)

    shutil.copy2(
        ROOT / "utils/others/embyToLocalPlayer_debug.bat",
        destination / "embyToLocalPlayer_debug.bat",
    )
    shutil.copytree(
        ROOT / "utils",
        destination / "utils",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copytree(ROOT / "user_script", destination / "user_script")

    updater = destination / "utils/update.py"
    content = updater.read_text(encoding="utf-8")
    if UPSTREAM_UPDATE_URL not in content:
        raise RuntimeError("Upstream updater URL changed; refusing to build a misleading release")
    updater.write_text(content.replace(UPSTREAM_UPDATE_URL, FORK_UPDATE_URL), encoding="utf-8")

    (destination / "requirements.txt").write_text(
        "requests>=2.28,<3\n",
        encoding="utf-8",
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
            if not relative or ".." in relative:
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
        "embyToLocalPlayer.py",
        "embyToLocalPlayer_config.ini",
        "embyToLocalPlayer_debug.bat",
        "user_script/embyToLocalPlayer.injector.js",
        "utils/configs.py",
        "requirements.txt",
    }
    missing = required - names
    if missing:
        raise RuntimeError(f"{path.name} is missing: {sorted(missing)}")
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

        system_zip = args.output / "embyToLocalPlayer.zip"
        embedded_zip = args.output / "etlp-python-embed-win32.zip"
        write_zip(system_package, system_zip)
        write_zip(embedded_package, embedded_zip)
        validate_archive(system_zip, embedded=False)
        validate_archive(embedded_zip, embedded=True)

        print(f"Built {system_zip}")
        print(f"Built {embedded_zip}")


if __name__ == "__main__":
    main()
