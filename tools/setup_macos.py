#!/usr/bin/env python3
"""Build and package the native Apple Silicon port from your own GXEE8P ISO."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import setup_linux


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--iso", type=Path, required=True)
    p.add_argument("--jobs", type=int, default=4)
    a = p.parse_args()
    iso = a.iso.resolve(strict=True)
    if sys.platform != "darwin" or platform.machine() != "arm64":
        p.error("This target requires Apple Silicon macOS and Xcode Command Line Tools")
    if a.jobs < 1:
        p.error("--jobs must be positive")
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    def run(*args):
        subprocess.run([str(x) for x in args], check=True)
    if (root / ".git").exists():
        run("git", "config", "core.hooksPath", "tools/git-hooks")
    config = json.loads((root / "setup/toolchain.json").read_text())
    local = root / "build/local-tools"
    dtk = setup_linux.ensure_tool(config["mac"]["dtk"], str(local))
    imgui = setup_linux.ensure_tool(config["imgui"], str(local))
    sdl_src = setup_linux.ensure_tool(config["mac"]["sdl2_src"], str(local))
    venv = local / "python"
    if not (venv / "bin/python").exists():
        run(sys.executable, "-m", "venv", venv)
    # Console-script shebangs retain the old interpreter path when the checkout moves.
    ninja_script = venv / "bin/ninja"
    header = ninja_script.read_bytes().split(b"\n", 1)[0] if ninja_script.exists() else b""
    moved = header.startswith(b"#!") and str(venv).encode() not in header
    pip_args = ["--force-reinstall"] if moved else []
    run(venv / "bin/python", "-m", "pip", "install", *pip_args, "ninja==1.13.0")
    ninja = venv / "bin/ninja"
    sdl = local / "sdl2"
    run("cmake", "--fresh", "-S", sdl_src, "-B", local / "sdl2-build", "-G", "Ninja",
        "-DCMAKE_MAKE_PROGRAM=" + str(ninja), "-DCMAKE_INSTALL_PREFIX=" + str(sdl),
        "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_OSX_ARCHITECTURES=arm64",
        "-DCMAKE_OSX_DEPLOYMENT_TARGET=14.0", "-DSDL_SHARED=ON", "-DSDL_STATIC=OFF", "-DSDL_TEST=OFF")
    run("cmake", "--build", local / "sdl2-build", "-j", a.jobs)
    run("cmake", "--install", local / "sdl2-build")
    run(sys.executable, "tools/extract_iso.py", iso, "baserom")
    run(Path(dtk) / "dtk", "dol", "split", "config/GXEE8P/config.yml", "build/GXEE8P")
    run(sys.executable, "configure.py", "--target", "host", "--toolchain", "macos",
        "--sdl", sdl, "--imgui", imgui)
    run(ninja, "-j", a.jobs)
    run(sys.executable, "tools/package_macos.py", "--iso", iso, "--sdl", sdl)


if __name__ == "__main__":
    main()
