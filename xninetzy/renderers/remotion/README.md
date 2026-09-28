XNINETZY REMOTION RENDERER (CPU-only)

This is the stable React/TypeScript runtime consumed by the Python
`xninetzy.context.media.video.renderers.RemotionBackend` (which
lives at `xninetzy/interfaces/media/video_backends/remotion.py`).

Two-layer architecture:

  Layer 1 (Python, this repo)        Layer 2 (this directory)
  --------------------------          -----------------------------
  VideoProject (JSON)        --->    Root.tsx registers 4 compositions
  RenderRequest              --->    ProjectDemo / Tutorial /
  build_props(...)                   DevelopmentVideo / MotionGraphic
  RemotionAdapter subprocess  --->    npx remotion render

Python sends DATA only. This directory is the stable runtime that
never changes per-render.

DEPLOYMENT

The runtime is version-controlled here. On first render the Python
adapter copies this tree to:
    $XNINETZY_REMOTION_PROJECT_ROOT
        (default: ~/.local/share/xninetzy/video/remotion)
and runs `npm install` once.

CPU ENFORCEMENT

The Python adapter sets these Chromium flags before invoking
remotion:
    --no-sandbox
    --disable-gpu
    --disable-software-rasterizer
    --disable-dev-shm-usage
    --no-zygote

Do not add GPU compositing, GPU-accelerated encoders, or
hardware-accelerated filter graphs.

DO NOT DO

- generate a new React project per render
- reimplement useCurrentFrame / interpolate in Python
- call ffmpeg from this codebase (Python does that)
- add paid video providers
