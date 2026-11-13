# State (2026-11-13; macOS fork)

## Scope

Desktop Apple Silicon fork of teclilla18/sonic-riders-recomp, based on c89e1eb.
Upstream attribution and license preserved. Other platforms remain upstream code;
this fork's changes target macOS. No game data or playable binaries are published.

## macOS

- **Implemented:** Clang arm64 target, macOS 14+, OpenGL 4.1 core, existing Apple C11
  threads shim, Cocoa/SDL main-thread event loop; game remains on a worker thread.
- **Implemented:** verified local dependency setup, genuine SDL2 2.32.10, signed app
  packaging, separate Application Support saves/settings/mods/log.
- **Tested [confirmed]:** M1 / Sonoma 14.8.9, native title/race captures; full minimized
  automatic route: 1P speed/fps 59.94/59.94, 2P 59.93/59.00. Concurrent compilation means
  these are smoke-test figures, not an isolated benchmark.
- **Tested [confirmed]:** full cached setup through packaging; strict app signature;
  LaunchServices startup; real 32 kHz audio device initialized (quality not assessed).
- **Accepted (original port):** user confirmed the game works (2026-11-13).
- **Performance fixes tested:** desktop resolution metadata, macOS QoS, asynchronous GL
  GPU queries, and immutable-table reuse. Normal 2x route: 1P 59.91 fps / GPU 13.62 ms,
  2P 59.34 fps / GPU 14.19 ms (sampled elapsed command time, not pure active GPU work).
  No established FPS gain from single runs; game speed ~59.94/59.97 steps/s.
- **Interpolation correctness:** target 120 route completed; 108 GPU-buffer readback
  checks passed, static-table uploads 10348/13800 (-25%). Diagnostic readbacks stall
  the GPU: that run is not a performance benchmark or proof of 120 fps in races.
  Original presentation rate and picture quality remain unchanged.
- **Relocation [confirmed]:** full setup and signed app packaging passed in the independent
  checkout outside the matching-decomp project. Setup repairs
  moved Ninja shebangs, refreshes CMake cache and regenerates build paths.
- **Unverified:** full story completion, all picture options, controllers, Intel Macs.
- **Release:** source fork only; no game-containing app release.

## Reference

Build: `python3 tools/setup_macos.py --iso "/path/to/your/Sonic Riders.iso"`.
Output: `build/macos/Sonic Riders.app`. Details: docs/notes/macos.md.
Dated evidence and upstream history: docs/HISTORY.md.
Machine-specific paths and logs: ignored NOTES.local.md.

## Next work

Keep macOS changes distinct from upstream; validate controllers and more play routes.
Do not treat inherited Windows/Switch/phone results as tests of this fork.
