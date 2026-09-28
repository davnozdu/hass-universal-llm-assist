"""Check the installer against a valid release and unsafe ZIP entries."""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components/universal_llm_assist/release_installer.py"
)
spec = importlib.util.spec_from_file_location("release_installer", MODULE_PATH)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
PREFIX = "custom_components/universal_llm_assist/"


def make_archive(extra: dict[str, bytes] | None = None, version: str = "0.2.1") -> bytes:
    files = {
        PREFIX + "manifest.json": json.dumps(
            {"domain": "universal_llm_assist", "version": version}
        ).encode(),
        PREFIX + "__init__.py": b"VALUE = 2\n",
    }
    files.update(extra or {})
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, contents in files.items():
            archive.writestr(name, contents)
    return buffer.getvalue()


class ReleaseInstallerTests(unittest.TestCase):
    def test_installs_and_keeps_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "universal_llm_assist"
            target.mkdir()
            (target / "old.txt").write_text("old")
            backup = installer.install_archive(make_archive(), "0.2.1", target)
            self.assertEqual((target / "__init__.py").read_text(), "VALUE = 2\n")
            self.assertEqual((backup / "old.txt").read_text(), "old")

    def test_rejects_path_traversal_and_preserves_current_install(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "universal_llm_assist"
            target.mkdir()
            (target / "old.txt").write_text("old")
            archive = make_archive({PREFIX + "../../escape.txt": b"bad"})
            with self.assertRaises(installer.InstallError):
                installer.install_archive(archive, "0.2.1", target)
            self.assertEqual((target / "old.txt").read_text(), "old")
            self.assertFalse((Path(directory) / "escape.txt").exists())

    def test_rejects_wrong_version(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "universal_llm_assist"
            target.mkdir()
            with self.assertRaises(installer.InstallError):
                installer.install_archive(make_archive(version="0.1.0"), "0.2.1", target)
