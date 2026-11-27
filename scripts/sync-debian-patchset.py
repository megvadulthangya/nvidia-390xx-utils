#!/usr/bin/env python3
"""Update one package's debian-state worktree from a shallow Debian Salsa clone.

The source repository is provided by the workflow and is only cloned when its
branch commit differs from the SHA recorded in the target debian-state branch.
Only top-level patch payloads, series.resolved, PKGBUILD metadata, and the
source-commit marker are managed. Other package files are preserved.
"""

from __future__ import annotations

import argparse
import re
import shlex
import sys
from pathlib import Path
from typing import Iterable

SOURCE_PATCH_DIR = Path("debian/module/debian/patches")
PATCH_SERIES_TARGET = "series.resolved"
SOURCE_COMMIT_TARGET = ".debian-source-commit"


def parse_series(series_text: str) -> list[str]:
    """Resolve series.in, keeping #HAS_UVM# entries but removing the marker."""
    patches: list[str] = []
    for line_number, original in enumerate(series_text.splitlines(), start=1):
        entry = original.strip()
        if not entry:
            continue
        if entry.startswith("#HAS_UVM#"):
            entry = entry[len("#HAS_UVM#"):].strip()
        elif entry.startswith("#"):
            continue

        fields = entry.split()
        if len(fields) != 1:
            raise RuntimeError(
                f"Unsupported series.in syntax on line {line_number}: {original!r}"
            )

        name = fields[0]
        candidate = Path(name)
        if (
            candidate.is_absolute()
            or ".." in candidate.parts
            or len(candidate.parts) != 1
        ):
            raise RuntimeError(
                f"Patch entries must be flat filenames (series.in line {line_number}): {name!r}"
            )
        if candidate.suffix.lower() not in {".patch", ".diff"}:
            raise RuntimeError(
                f"Unexpected patch filename extension on series.in line {line_number}: {name!r}"
            )
        patches.append(name)

    if not patches:
        raise RuntimeError("Debian series.in resolved to an empty patch list")
    if len(patches) != len(set(patches)):
        duplicates = sorted({name for name in patches if patches.count(name) > 1})
        raise RuntimeError(f"Duplicate patch entries in Debian series.in: {duplicates}")
    return patches


def shell_array_tokens(body: str, description: str) -> list[str]:
    lexer = shlex.shlex(body, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = "#"
    try:
        return list(lexer)
    except ValueError as exc:
        raise RuntimeError(f"Cannot parse {description}: {exc}") from exc


def array_pattern(variable: str) -> re.Pattern[str]:
    """Match a Bash array closed either on its own line or after its last item.

    Both forms are valid in PKGBUILD files:

        sha256sums=(\n            '...'
        )

        sha256sums=(\n            '...')

    The closing parenthesis must be the last non-comment character on its line.
    """
    return re.compile(
        rf"(?ms)^{re.escape(variable)}=\((.*?)(?:\)[ \t]*(?:\#.*)?$)"
    )


def replace_array_block(text: str, variable: str, replacement: str) -> str:
    pattern = array_pattern(variable)
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one {variable}=(...) block; found {len(matches)}"
        )
    return pattern.sub(lambda _match: replacement, text, count=1)


def get_array_body(text: str, variable: str) -> str:
    matches = list(array_pattern(variable).finditer(text))
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one {variable}=(...) block; found {len(matches)}"
        )
    return matches[0].group(1)


def update_pkgbuild(pkgbuild_text: str, patches: list[str]) -> str:
    """Rewrite Debian patch list and regenerate every sha256sum as SKIP."""
    patch_lines = "\n".join(f"    {shlex.quote(name)}" for name in patches)
    updated = replace_array_block(
        pkgbuild_text,
        "_debian_patches",
        f"_debian_patches=(\n{patch_lines}\n)",
    )

    source_items = shell_array_tokens(get_array_body(updated, "source"), "source array")
    expansion = "${_debian_patches[@]}"
    if source_items.count(expansion) != 1:
        raise RuntimeError(
            'PKGBUILD source array must contain exactly one "${_debian_patches[@]}" expansion'
        )

    static_sources = [item for item in source_items if item != expansion]
    if static_sources.count(PATCH_SERIES_TARGET) != 1:
        raise RuntimeError(
            f"PKGBUILD source array must contain {PATCH_SERIES_TARGET!r} exactly once"
        )

    expected_count = len(static_sources) + len(patches)
    sums_block = "sha256sums=(\n" + "\n".join(
        "            'SKIP'" for _ in range(expected_count)
    ) + "\n)"
    updated = replace_array_block(updated, "sha256sums", sums_block)

    generated_sums = shell_array_tokens(
        get_array_body(updated, "sha256sums"), "regenerated sha256sums array"
    )
    if generated_sums != ["SKIP"] * expected_count:
        raise RuntimeError(
            "Internal error: sha256sums has an unexpected number or value of entries"
        )

    updated = re.sub(
        r"(?m)^(#\s*Átírva: Debian [^\n]*patch-sorozat használatára )\(\d+ patch\)\.$",
        rf"\g<1>({len(patches)} patch).",
        updated,
        count=1,
    )
    updated = re.sub(
        r"(?m)^# Hash-ek:.*$",
        "# Minden source elem checksumja SKIP; az elemszám automatikusan a source tömbhöz igazodik.",
        updated,
        count=1,
    )
    return updated


def sync_patchset(source_dir: Path, target_dir: Path, source_sha: str) -> list[str]:
    """Prepare target_dir from source_dir without committing or pushing."""
    source_dir = source_dir.resolve()
    target_dir = target_dir.resolve()

    if not re.fullmatch(r"[0-9a-fA-F]{40,64}", source_sha):
        raise RuntimeError(f"Invalid source commit SHA: {source_sha!r}")

    patch_dir = source_dir / SOURCE_PATCH_DIR
    series_path = patch_dir / "series.in"
    if not series_path.is_file():
        raise RuntimeError(f"Missing Debian patch series: {series_path}")

    patch_names = parse_series(series_path.read_text(encoding="utf-8"))

    # Read and validate every listed patch before changing the target tree.
    patch_payloads: dict[str, bytes] = {}
    for name in patch_names:
        source_path = patch_dir / name
        if not source_path.is_file():
            raise RuntimeError(f"Patch listed in series.in is missing: {source_path}")
        patch_payloads[name] = source_path.read_bytes()

    pkgbuild_path = target_dir / "PKGBUILD"
    if not pkgbuild_path.is_file():
        raise RuntimeError(f"Target worktree has no top-level PKGBUILD: {pkgbuild_path}")

    original_pkgbuild = pkgbuild_path.read_text(encoding="utf-8")
    updated_pkgbuild = update_pkgbuild(original_pkgbuild, patch_names)
    series_content = "\n".join(patch_names) + "\n"

    changed: list[str] = []
    wanted = set(patch_names)

    # The target's top-level patch payloads are the managed Debian patch set.
    # Remove obsolete payloads, but preserve every non-patch package file.
    old_patches = list(target_dir.glob("*.patch")) + list(target_dir.glob("*.diff"))
    for old_patch in old_patches:
        if old_patch.is_file() and old_patch.name not in wanted:
            old_patch.unlink()
            changed.append(f"{old_patch.name} (deleted)")

    for name, payload in patch_payloads.items():
        destination = target_dir / name
        if not destination.is_file() or destination.read_bytes() != payload:
            destination.write_bytes(payload)
            changed.append(f"{name} (added/updated)")

    resolved_path = target_dir / PATCH_SERIES_TARGET
    if not resolved_path.is_file() or resolved_path.read_text(encoding="utf-8") != series_content:
        resolved_path.write_text(series_content, encoding="utf-8", newline="\n")
        changed.append(f"{PATCH_SERIES_TARGET} (updated)")

    if updated_pkgbuild != original_pkgbuild:
        pkgbuild_path.write_text(updated_pkgbuild, encoding="utf-8", newline="\n")
        changed.append("PKGBUILD (updated)")

    commit_path = target_dir / SOURCE_COMMIT_TARGET
    commit_content = source_sha.lower() + "\n"
    if not commit_path.is_file() or commit_path.read_text(encoding="utf-8") != commit_content:
        commit_path.write_text(commit_content, encoding="ascii", newline="\n")
        changed.append(f"{SOURCE_COMMIT_TARGET} (updated)")

    # Defensive checks: lists and patch files must represent the same set.
    resolved_names = resolved_path.read_text(encoding="utf-8").splitlines()
    if resolved_names != patch_names:
        raise RuntimeError("Generated series.resolved does not match the Debian series order")

    actual_patches = {
        path.name
        for path in list(target_dir.glob("*.patch")) + list(target_dir.glob("*.diff"))
        if path.is_file()
    }
    if actual_patches != wanted:
        missing = sorted(wanted - actual_patches)
        unexpected = sorted(actual_patches - wanted)
        raise RuntimeError(
            f"Target patch set mismatch; missing={missing}, unexpected={unexpected}"
        )

    pkgbuild_after = pkgbuild_path.read_text(encoding="utf-8")
    listed = shell_array_tokens(
        get_array_body(pkgbuild_after, "_debian_patches"), "_debian_patches array"
    )
    if listed != patch_names:
        raise RuntimeError("PKGBUILD _debian_patches does not match series.resolved")

    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path, help="shallow Debian Salsa clone")
    parser.add_argument("--target-dir", required=True, type=Path, help="debian-state Git worktree")
    parser.add_argument("--source-sha", required=True, help="commit SHA checked out from Salsa")
    args = parser.parse_args()

    try:
        changed = sync_patchset(args.source_dir, args.target_dir, args.source_sha)
    except Exception as exc:  # noqa: BLE001 - report a concise workflow failure
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Debian patch files in series: {len(parse_series((args.source_dir / SOURCE_PATCH_DIR / 'series.in').read_text(encoding='utf-8')))}")
    print(f"Files changed: {len(changed)}")
    for item in changed:
        print(f"  - {item}")
    if not changed:
        print("Target already matches this Debian Salsa commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
