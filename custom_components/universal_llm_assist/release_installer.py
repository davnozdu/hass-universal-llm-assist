"""Validate a release ZIP and replace the installed integration safely."""

import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile
import zipfile

DOMAIN = "universal_llm_assist"
MAX_UNPACKED_SIZE = 10 * 1024 * 1024


class InstallError(Exception):
    """A release could not be installed safely."""


def install_archive(archive: bytes, version: str, target: Path) -> Path:
    """Validate and atomically replace target, retaining a backup directory."""
    prefix = f"custom_components/{DOMAIN}/"
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as package:
            infos = package.infolist()
            if not infos or len(infos) > 100:
                raise InstallError("Invalid number of files in release ZIP")
            if sum(item.file_size for item in infos) > MAX_UNPACKED_SIZE:
                raise InstallError("Release ZIP is too large when unpacked")
            for item in infos:
                path = PurePosixPath(item.filename)
                mode = item.external_attr >> 16
                if (
                    not item.filename.startswith(prefix)
                    or ".." in path.parts
                    or path.is_absolute()
                    or item.flag_bits & 0x1
                    or stat.S_ISLNK(mode)
                ):
                    raise InstallError("Unexpected path in release ZIP")
            manifest = json.loads(package.read(f"{prefix}manifest.json"))
            if manifest.get("domain") != DOMAIN or manifest.get("version") != version:
                raise InstallError("Release manifest does not match the tag")
            for item in infos:
                if item.filename.endswith(".py"):
                    compile(package.read(item), item.filename, "exec")

            with tempfile.TemporaryDirectory(
                prefix=f".{DOMAIN}_staging_", dir=target.parent
            ) as staging_dir:
                package.extractall(staging_dir)
                replacement = Path(staging_dir) / "custom_components" / DOMAIN
                if not replacement.is_dir():
                    raise InstallError("Release ZIP has no integration directory")
                backup_path = Path(
                    tempfile.mkdtemp(prefix=f".{DOMAIN}_backup_", dir=target.parent)
                )
                backup_path.rmdir()
                os.replace(target, backup_path)
                try:
                    os.replace(replacement, target)
                except OSError:
                    os.replace(backup_path, target)
                    raise
                return backup_path
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, SyntaxError) as err:
        raise InstallError("Could not safely install release ZIP") from err
