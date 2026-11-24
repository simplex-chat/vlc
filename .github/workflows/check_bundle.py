#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

MAGIC_SIZE = 4
ELF_MAGIC = b"\x7fELF"
MACHO_MAGICS = (b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xca\xfe\xba\xbe")
AVFORMAT_NAME = "avformat"
AVFORMAT_MARKER = b"AVFormatContext"
GLIBC_SYMBOL = re.compile(r"GLIBC_(\d+(?:\.\d+)+)")
LOAD_COMMAND = "Load command"
MACOS_MINIMUM_FIELDS = {"LC_BUILD_VERSION": "minos", "LC_VERSION_MIN_MACOSX": "version"}

Version = tuple[int, ...]


def version(text: str) -> Version:
    return tuple(int(part) for part in text.split("."))


def show(value: Version) -> str:
    return ".".join(map(str, value))


def files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def magic(path: Path) -> bytes:
    with path.open("rb") as file:
        return file.read(MAGIC_SIZE)


def plugin_name(path: Path) -> str | None:
    if path.name.startswith("lib") and "_plugin." in path.name:
        return path.name.removeprefix("lib").split("_plugin.")[0]
    return None


def check_plugins(plugins_dir: Path, expected_file: Path) -> list[str]:
    expected = set(expected_file.read_text().split())
    shipped = {name for name in map(plugin_name, files(plugins_dir)) if name}
    print(f"{len(shipped)} plugins in {plugins_dir}, {len(expected)} expected", flush=True)
    return [f"plugin missing: {name}" for name in sorted(expected - shipped)] + [
        f"plugin not expected: {name}" for name in sorted(shipped - expected)
    ]


def check_avformat(root: Path) -> list[str]:
    return [
        f"libavformat in {path.relative_to(root)}"
        for path in files(root)
        if AVFORMAT_NAME in path.name.lower() or AVFORMAT_MARKER in path.read_bytes()
    ]


def glibc_versions(path: Path) -> list[Version]:
    symbols = subprocess.run(["objdump", "-T", str(path)], capture_output=True, text=True).stdout
    return [version(match) for match in GLIBC_SYMBOL.findall(symbols)]


def check_glibc(root: Path, limit: Version) -> list[str]:
    failures = []
    highest: Version = ()
    for path in files(root):
        if magic(path) == ELF_MAGIC:
            found = max(glibc_versions(path), default=())
            highest = max(highest, found)
            if found > limit:
                failures.append(f"{path.relative_to(root)} requires glibc {show(found)}, above {show(limit)}")
    print(f"highest glibc symbol version: {show(highest)}", flush=True)
    return failures


def macos_minimums(path: Path) -> list[Version]:
    output = subprocess.run(["otool", "-l", str(path)], capture_output=True, text=True, check=True).stdout
    minimums = []
    for command in output.split(LOAD_COMMAND)[1:]:
        fields = dict(line.split(None, 1) for line in command.splitlines()[1:] if len(line.split(None, 1)) == 2)
        field = MACOS_MINIMUM_FIELDS.get(fields.get("cmd", ""))
        if field:
            minimums.append(version(fields[field].strip()))
    return minimums


def check_macos(root: Path, limit: Version) -> list[str]:
    failures = []
    for path in files(root):
        if magic(path) in MACHO_MAGICS:
            minimums = macos_minimums(path)
            if not minimums:
                failures.append(f"{path.relative_to(root)} has no minimum macOS version")
            failures += [
                f"{path.relative_to(root)} requires macOS {show(minimum)}, above {show(limit)}"
                for minimum in minimums
                if minimum > limit
            ]
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the plugins and binaries of a VLC bundle of the desktop app")
    parser.add_argument("plugins_dir", type=Path)
    parser.add_argument("expected_plugins", type=Path, help="file with the plugins of this bundle, one per line")
    parser.add_argument("root", type=Path, help="directory of the files that the bundle ships")
    limits = parser.add_mutually_exclusive_group()
    limits.add_argument("--max-glibc", type=version, help="highest glibc symbol version allowed in ELF files")
    limits.add_argument("--max-macos", type=version, help="highest minimum macOS version allowed in Mach-O files")
    args = parser.parse_args()
    failures = check_plugins(args.plugins_dir, args.expected_plugins) + check_avformat(args.root)
    if args.max_glibc:
        failures += check_glibc(args.root, args.max_glibc)
    if args.max_macos:
        failures += check_macos(args.root, args.max_macos)
    for failure in failures:
        print(f"FAIL {failure}", flush=True)
    print(f"{len(failures)} failures", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
