#!/usr/bin/env python3
"""Package the locally built arm64 macOS port with a copy of your own disc."""
import argparse
import hashlib
import os
from pathlib import Path
import plistlib
import shutil
import subprocess


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--iso", type=Path, required=True)
    p.add_argument("--sdl", type=Path, default=Path("build/local-tools/sdl2"))
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    iso = args.iso.resolve(strict=True)
    with iso.open("rb") as f:
        if hashlib.file_digest(f, "sha1").hexdigest() != "ce0cecf57034bef8bab7d6f588ce92c85a849613":
            p.error("Expected a clean, full GXEE8P rev 0 disc image")
    app = root / "build/macos/Sonic Riders.app"
    binary = root / "build/host-macos/sonicriders"
    if not binary.is_file():
        p.error("Build the macos host target first")
    mac = app / "Contents/MacOS"
    res = app / "Contents/Resources"
    fw = app / "Contents/Frameworks"
    for d in (mac, res, fw):
        d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binary, mac / "sonicriders")
    lib = "libSDL2-2.0.0.dylib"
    shutil.copy2(args.sdl / "lib" / lib, fw / lib)
    # Read the exact linked install name: the SDL prefix can be anywhere.
    deps = subprocess.check_output(["otool", "-L", str(mac / "sonicriders")], text=True)
    linked = next(line.strip().split(" (")[0] for line in deps.splitlines()[1:] if "libSDL2" in line)
    run("install_name_tool", "-change", linked, "@rpath/" + lib, mac / "sonicriders")
    run("install_name_tool", "-id", "@rpath/" + lib, fw / lib)
    launcher = mac / "LaunchGame"
    launcher.write_text('''#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DATA="$HOME/Library/Application Support/Sonic Riders Native"
mkdir -p "$DATA/saves" "$DATA/mods" "$DATA/build"
cd "$DATA"
exec "$HERE/sonicriders" "$HERE/../Resources/game.iso" >> "$DATA/game.log" 2>&1
''')
    launcher.chmod(0o755)
    dest = res / "game.iso"
    if not dest.exists():
        # APFS clone is a separate writable file, without duplicating the disc's blocks.
        result = subprocess.run(["cp", "-c", str(iso), str(dest)])
        if result.returncode:
            shutil.copy2(iso, dest)
    with dest.open("rb") as f:
        if hashlib.file_digest(f, "sha1").hexdigest() != "ce0cecf57034bef8bab7d6f588ce92c85a849613":
            p.error("Existing bundled disc differs; remove it before repackaging")
    icons = root / "build/macos/Game.iconset"
    icons.mkdir(parents=True, exist_ok=True)
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            suffix = "@2x" if scale == 2 else ""
            run("sips", "-z", size * scale, size * scale, root / "setup/icon.png",
                "--out", icons / f"icon_{size}x{size}{suffix}.png")
    run("iconutil", "-c", "icns", icons, "-o", res / "Game.icns")
    info = dict(CFBundleName="Sonic Riders", CFBundleDisplayName="Sonic Riders",
                CFBundleIdentifier="local.sonicriders.native", CFBundleExecutable="LaunchGame",
                CFBundlePackageType="APPL", CFBundleVersion="1", CFBundleShortVersionString="0.8.0-local",
                CFBundleIconFile="Game.icns", LSMinimumSystemVersion="14.0",
                NSHighResolutionCapable=True, NSPrincipalClass="NSApplication")
    with (app / "Contents/Info.plist").open("wb") as f:
        plistlib.dump(info, f)
    run("codesign", "--force", "--sign", "-", fw / lib)
    run("codesign", "--force", "--sign", "-", mac / "sonicriders")
    run("codesign", "--force", "--sign", "-", app)
    run("codesign", "--verify", "--deep", "--strict", app)
    print(app)


if __name__ == "__main__":
    main()
