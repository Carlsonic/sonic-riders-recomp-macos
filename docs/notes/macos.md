# Desktop macOS (Apple Silicon fork, 2026-11-13)

Implemented for Apple Silicon, macOS 14 Sonoma or newer. This fork adds a desktop target after
upstream c89e1eb; it is not an upstream release. Intel Macs have not been targeted or tested.

## Build and package

Install Xcode Command Line Tools (`xcode-select --install`), Python 3.11+ and CMake 3.24+.
From the repository root:

```sh
python3 tools/setup_macos.py --iso "/path/to/your/Sonic Riders.iso"
```

The setup checks the clean GXEE8P rev 0 disc, downloads SHA-256-pinned dtk, ImGui and SDL2
using `setup/toolchain.json`, installs Ninja in a local Python environment, builds genuine
SDL2 2.32.10, extracts and recompiles the game, then builds and ad-hoc signs the app:
`build/macos/Sonic Riders.app`. Dependencies and generated game files stay under ignored
`build/` and `baserom/`. Do not distribute the app: it contains your disc and recompiled game.
The original ISO is read only. On APFS, the packaged ISO is a separate clone sharing blocks.
No Apple developer membership, Rosetta, Dolphin or global SDL installation is needed to run it.

For subsequent runtime changes:

```sh
build/local-tools/python/bin/ninja -j4
python3 tools/package_macos.py --iso "/path/to/your/Sonic Riders.iso"
open "build/macos/Sonic Riders.app"
```

For configure changes use `python3 configure.py --target host --toolchain macos
--sdl build/local-tools/sdl2 --imgui build/local-tools/imgui` on one line, then rebuild.
The bare development executable needs `DYLD_LIBRARY_PATH=build/local-tools/sdl2/lib`;
the packaged executable uses its bundled SDL2 via `@rpath`.

## Runtime differences

- Clang arm64, deployment target 14.0, Apple pthread-backed C11 threads shim.
- Cocoa window creation and SDL event handling run on the process main thread. The game,
  audio and device helpers retain their existing worker threads.
- OpenGL 4.1 core, forward-compatible context; Apple's driver has no 3.3 core profile.
  Existing desktop GLSL 330 shaders are used. This route does not use MoltenVK.
- The bundle has its own SDL2 dylib and only system dependencies. The launcher changes the
  working directory to `~/Library/Application Support/Sonic Riders Native`, keeping
  saves (`saves/card_a.raw`), settings (`saves/settings.ini`), mods and `game.log` outside
  the app. Moving or replacing the app therefore preserves saves.
- Keyboard: WASD; J/K/L/I = A/B/X/Y; Enter = START; hold F1 = settings.

## Moving the checkout

The packaged app is self-contained and can move without rebuilding. For development, rerun
`tools/setup_macos.py --iso ...` after moving the checkout: it repairs Ninja's Python shebang,
refreshes CMake's absolute-path cache and regenerates the host build files. Saves stay in
Application Support and are unaffected.

## Validation

See the dated HISTORY entry and ignored NOTES.local.md for this machine's run results.
Use `SR_MINIMIZED=1 SR_NOAUDIO=1 SR_PERFTEST=1` for unattended graphics tests; use the
bundled executable and pass its `Contents/Resources/game.iso` explicitly when bypassing
LaunchGame. The automatic route uses a temporary memory card in RAM. Captures are
`build/shot_N.png` relative to the working directory (`SR_SCREENSHOT=N`).

## OpenGL performance fixes (2026-11-13)

- Desktop logs and performance JSON use `pc_scale`, not the mobile `resolution` field.
  The previous JSON's "1x (640x528)" label was misleading: default desktop GL actually
  used 2x (1280x1056 at 4:3). JSON also records MSAA, requested presentation rate and aspect.
  The default picture quality and user settings are unchanged.
- macOS foreground worker threads request USER_INITIATED QoS, the audio mixer's raise
  helper requests USER_INTERACTIVE, and diagnostic workers use UTILITY. No fixed CPU
  affinity or realtime scheduling is imposed. `SR_NOQOS=1` restores the old macOS
  no-op helpers for A/B testing; `SR_QOS_LOG=1` reports requested and actual QoS classes.
- Optional GL timer queries use an eight-slot ring. Only available results are read;
  a full ring skips measurement, never waits. Queries end before SwapWindow. The value
  measures elapsed GPU command time (including stalls, not just active shader work),
  excluding the swap/display wait. Unsupported drivers report unknown. `SR_NO_GPU_TIMER=1`
  disables measurement. Other threads read an atomic last-completed sample.
- Performance JSON records `gpu_ms_sample_mean` and `gpu_observations`: latest completed
  GPU samples observed at game steps, not necessarily distinct samples or exact frame pairs.
  Unknown is -1 with zero observations. `tools/perf_test.py show` displays GPU values when
  available and can still load old records without them.
- Repeated presentations of a held frame reuse immutable XF tables and, when unchanged,
  uniforms and transform chunks. Interpolated values are uploaded each time and the
  original values restored on the real frame. Frame recycling invalidates the cache.
  `SR_GL_UPLOAD_CACHE=0` disables reuse; `SR_GL_UPLOAD_STATS=1` reports upload counts.
- `SR_GL_VERIFY_UPLOADS=1` occasionally reads actual GPU buffers and compares them against
  the current source/interpolated state, aborting on mismatch. This intentionally stalls
  the GPU and is a correctness diagnostic, not a performance measurement mode.

Validation of the performance fixes: normal 2x route completed both races at 59.91 / 59.34 fps;
GPU sampled means 13.615 / 14.187 ms. Target-120 diagnostic route completed with 108 buffer
checks passing; 10348 static-table uploads for 13800 executions (25% fewer). Its readbacks
intentionally stall the GPU, and its race frame rate is not proof of sustained 120 fps.
One baseline/patched run each cannot establish an isolated QoS benefit or general FPS gain.

## High-resolution investigation (2026-11-13)

[confirmed] M1, same minimized 1280x800 window, Fit window (16:10), MSAA 1x, fresh RAM card,
silent automatic 1P/2P demos; one serial run per case, no concurrent build or other game process
observed. The test checkout used default picture options. These results differ from the earlier
4:3 / 640x480 smoke tests because screen shape, visible scene and presentation size differ.

| Case | 1P fps | 2P fps | 1P GPU ms | 2P GPU ms |
|---|---:|---:|---:|---:|
| 2x, original pictures | 43.39 | 45.33 | 18.84 | 18.11 |
| 3x, original pictures | 25.08 | 24.90 | 40.22 | 40.82 |
| 3x, requested 120 | 26.61 | 25.17 | 37.95 | 40.53 |
| 3x, flat diagnostic | 58.67 | 59.91 | 3.75 | 3.67 |
| 3x, GPU timer disabled | 26.06 | 26.74 | unknown | unknown |

GPU ms is the sampled elapsed GL command interval, not pure active shader time. Single runs
and uncontrolled background activity cannot establish small differences between cases.

- Actual EFB allocations were 1536x1056 at 2x and 2304x1584 at 3x. The latter is 3.65 million
  pixels, rather than Full HD's 2.07 million; 2x -> 3x multiplies buffer area by 2.25. These
  are intermediate allocations: viewport/scissor and final window size remain distinct.
- With full graphics, GPU command time rose roughly 2.1-2.3x while game-thread work stayed
  around 1-2 ms per step. Game simulation stayed near 60 steps/s while pictures dropped.
  The severe 3x slowdown remains with interpolation and GPU timing both disabled.
- The separate flat diagnostic replaced only the fragment shader with vertex-colour output,
  retaining the guest/game code, geometry submission and renderer. It removes texture/TEV,
  fog and alpha-test work and changes pixel coverage/appearance. Its speed is diagnostic
  evidence about the graphics path, not an achievable full-graphics performance claim.
  This binary stays ignored/local and is never packaged as the game.
- Shared shader sources and tools/embed_shaders.py match upstream c89e1eb unchanged. Desktop
  GL uses the universal fragment program, including dynamic TEV control and optional paths;
  the existing specialized shader infrastructure is used by other backends. This inherited
  architecture is the next optimization target. Mac driver contribution is not isolated;
  these results are not measurements of Windows/Linux or other GPUs.
- GPU queries now run only when SR_GPU_TIMER=1 or in SR_PERFTEST. SR_GPU_TIMER=0 and
  SR_NO_GPU_TIMER=1 disable them. Normal play submits no timer queries. This keeps diagnostic
  work out of ordinary play; the disabled-timer control still ran only ~26-27 fps at 3x.
- Resolution labels in the desktop settings now include the actual widescreen width and
  explain the quadratic pixel cost, instead of suggesting universal monitor-resolution presets.

The supported graphics remain intact. Substantial full-graphics acceleration is still pending:
reuse the project's material-specific shader generation in desktop GL and validate output
against the universal program. Measure compilation/prewarm hitches and transparent passes too.
