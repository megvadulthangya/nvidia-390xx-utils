#!/usr/bin/env python3
"""Regression tests for the direct Debian Salsa -> debian-state synchronizer."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync-debian-patchset.py"
SPEC = importlib.util.spec_from_file_location("sync_debian_patchset", SCRIPT)
assert SPEC and SPEC.loader
SYNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNC)


def make_pkgbuild(
    static_source_count: int = 8,
    old_checksum_count: int = 99,
    inline_checksum_close: bool = False,
) -> str:
    static_sources = [f"'static-source-{i}.conf'" for i in range(static_source_count - 1)]
    static_sources.insert(0, "'series.resolved'")
    source_body = "\n".join(f"    {item}" for item in static_sources)
    checksum_body = "\n".join(f"    'old-hash-{i}'" for i in range(old_checksum_count))
    checksum_block = (
        f"sha256sums=(\n{checksum_body})\n"
        if inline_checksum_close
        else f"sha256sums=(\n{checksum_body}\n)\n"
    )
    return (
        "# Átírva: Debian 340xx/main patch-sorozat használatára (87 patch).\n"
        "pkgbase=nvidia-test\n"
        "_debian_patches=(\n    old.patch\n)\n"
        f"source=(\n{source_body}\n    \"${{_debian_patches[@]}}\"\n)\n"
        f"{checksum_block}"
    )


class ParseSeriesTests(unittest.TestCase):
    def test_keeps_has_uvm_entries_and_drops_marker(self) -> None:
        series = "# normal comment\nfirst.patch\n#HAS_UVM# second.patch\n\nthird.diff\n"
        self.assertEqual(SYNC.parse_series(series), ["first.patch", "second.patch", "third.diff"])

    def test_rejects_unsafe_paths(self) -> None:
        with self.assertRaises(RuntimeError):
            SYNC.parse_series("../outside.patch\n")

    def test_rejects_missing_or_invalid_extension_syntax(self) -> None:
        with self.assertRaises(RuntimeError):
            SYNC.parse_series("README.txt\n")


class PkgbuildChecksumTests(unittest.TestCase):
    def assert_all_skip(self, updated: str, expected: int) -> None:
        values = SYNC.shell_array_tokens(
            SYNC.get_array_body(updated, "sha256sums"), "sha256sums array"
        )
        self.assertEqual(values, ["SKIP"] * expected)

    def test_340xx_real_count(self) -> None:
        patches = [f"patch-{i:03}.patch" for i in range(87)]
        updated = SYNC.update_pkgbuild(make_pkgbuild(8, 99), patches)
        self.assert_all_skip(updated, 95)
        self.assertIn("(87 patch).", updated)

    def test_390xx_real_count(self) -> None:
        patches = [f"patch-{i:03}.patch" for i in range(83)]
        updated = SYNC.update_pkgbuild(make_pkgbuild(11, 100), patches)
        self.assert_all_skip(updated, 94)

    def test_470xx_inline_checksum_closing_parenthesis(self) -> None:
        patches = [f"patch-{i:03}.patch" for i in range(57)]
        original = make_pkgbuild(12, 73, inline_checksum_close=True)
        updated = SYNC.update_pkgbuild(original, patches)
        self.assert_all_skip(updated, 69)
        self.assertIn("sha256sums=(\n", updated)
        self.assertTrue(updated.rstrip().endswith(")"))

    def test_reorders_removals_and_is_idempotent(self) -> None:
        original = make_pkgbuild(8, 95)
        patches = ["second.patch", "first.patch"]
        once = SYNC.update_pkgbuild(original, patches)
        twice = SYNC.update_pkgbuild(once, patches)
        self.assertEqual(once, twice)
        listed = SYNC.shell_array_tokens(
            SYNC.get_array_body(once, "_debian_patches"), "_debian_patches"
        )
        self.assertEqual(listed, patches)
        self.assert_all_skip(once, 10)


class FullSyncTests(unittest.TestCase):
    def test_sync_updates_only_managed_files_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "salsa"
            target = root / "target"
            patch_dir = source / "debian/module/debian/patches"
            patch_dir.mkdir(parents=True)
            target.mkdir()

            (patch_dir / "series.in").write_text(
                "# comment\nfirst.patch\n#HAS_UVM# second.patch\n", encoding="utf-8"
            )
            (patch_dir / "first.patch").write_bytes(b"first payload\n")
            (patch_dir / "second.patch").write_bytes(b"second payload with inherited space \n")

            (target / "PKGBUILD").write_text(make_pkgbuild(8, 99), encoding="utf-8")
            (target / "obsolete.patch").write_text("remove me\n", encoding="utf-8")
            (target / "package.conf").write_text("preserve me\n", encoding="utf-8")

            changes = SYNC.sync_patchset(source, target, "a" * 40)
            self.assertTrue(changes)
            self.assertFalse((target / "obsolete.patch").exists())
            self.assertEqual((target / "package.conf").read_text(), "preserve me\n")
            self.assertEqual(
                (target / "series.resolved").read_text(), "first.patch\nsecond.patch\n"
            )
            self.assertEqual((target / ".debian-source-commit").read_text(), "a" * 40 + "\n")
            self.assertEqual((target / "second.patch").read_bytes(), b"second payload with inherited space \n")

            second_changes = SYNC.sync_patchset(source, target, "a" * 40)
            self.assertEqual(second_changes, [])

    def test_missing_patch_does_not_modify_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "salsa"
            target = root / "target"
            patch_dir = source / "debian/module/debian/patches"
            patch_dir.mkdir(parents=True)
            target.mkdir()
            (patch_dir / "series.in").write_text("missing.patch\n", encoding="utf-8")
            original = make_pkgbuild()
            (target / "PKGBUILD").write_text(original, encoding="utf-8")
            with self.assertRaises(RuntimeError):
                SYNC.sync_patchset(source, target, "b" * 40)
            self.assertEqual((target / "PKGBUILD").read_text(), original)
            self.assertFalse((target / ".debian-source-commit").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
