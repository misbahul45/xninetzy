# Video MCP — Final Checkpoint

Status: Phases 0–15 complete (Phase 11 + 12 are no-ops in this build).

## Files added

```
xninetzy/context/media/video/
  __init__.py
  capabilities.py            (existing — capability enum)
  errors.py                  (existing — 22 VIDEO_* error codes)
  models.py                  (new — VideoProject, VideoComposition, VideoScene,
                             VideoTrack, VideoClip, VideoAsset, VideoTransition,
                             VideoArtifact, VideoJob, MotionPreset, Keyframe,
                             RenderRequest, RenderResult, +6 enums)
  motion.py                  (new — 26 canonical motion primitives + keyframe
                             interpolation + easing)
  storage.py                 (new — SQLite schema init + VideoProjectStore,
                             VideoAssetStore, VideoJobStore + state machine)
  validators.py              (new — project / motion / render / path safety)
  templates.py               (new — project_demo, tutorial, development_journey,
                             motion_graph)
  project_engine.py          (new — VideoProjectEngine CRUD + version increment)
  renderers/
    base.py                  (new — RendererBackend ABC + CPU/GPU encoder gate
                             + select_renderer + quantize_request)
    router.py                (new — RendererRouter + default_router)
    __init__.py              (new — re-exports)

xninetzy/interfaces/media/video_backends/
  __init__.py
  ffmpeg.py                  (new — FFmpegRenderer + which/ffmpeg_version/
                             ffprobe_version/probe_metadata/quality_to_ffmpeg_args;
                             CPU-only encoders libx264/libx265/libvpx/libaom/
                             libsvtav1; GPU encoders denied)
  remotion.py                (new — RemotionBackend + resolve_composition_id/
                             resolve_render_entry/read_remotion_version/
                             build_props/tail_lines; CPU Chromium flags
                             --no-sandbox --disable-gpu
                             --disable-software-rasterizer
                             --disable-dev-shm-usage --no-zygote)

xninetzy/renderers/remotion/
  package.json, tsconfig.json, .gitignore, README.md
  src/
    Root.tsx, index.tsx
    runtime/{types,loadProject,loadTimeline,loadAssets}.ts
    motion/{easing,keyframes,presets}.ts
    components/{Scene,VideoClip,TextLayer,ShapeLayer,ImageLayer,
                CodeLayer,BrowserFrame,LowerThird,Callout,_titlecard}.tsx
    compositions/{ProjectDemo,Tutorial,DevelopmentVideo,MotionGraphic}.tsx

xninetzy/tools/ecosystem/media_video_tools.py   (new — 16 MCP tools)

xninetzy/tools/registry.py                       (modified — video_* tools
                                                 + media group expanded)

xninetzy/skills/router.py                        (modified — INTENT_CLASSES
                                                 gets MEDIA + 28 keywords
                                                 + MEDIA pipeline of 8 skills)

scripts/setup_remotion_renderer.py              (new — copies Remotion
                                                 template + npm install)

.agents/skills/media-video-{root,capture,edit,motion,render,
                            project-demo,tutorial,development}/SKILL.md  (Phase 1)

docs/media/video/
  01-phase-0-audit.md
  02-phase-1-skill-inventory.md
  03-phase-2-3-checkpoint.md       (interim)
  04-final-checkpoint.md           (this file)

tests/media/video/
  test_models.py                  (13 tests)
  test_renderer_selection.py      (8 tests)
  test_templates.py               (5 tests)
  test_validators.py              (7 tests)
tests/tools/ecosystem/
  test_media_video_tools.py       (9 tests — end-to-end via MCP surface)
```

## Test status

```
tests/architecture/                                   5 + 3 tests = 8 passing
tests/media/video/                                    33 passing
tests/tools/ecosystem/test_media_video_tools.py        9 passing
TOTAL                                                 50 passing
```

Plus `scripts/verify_cpu_only.py` exits 0 (no GPU, no FAISS-GPU, no CUDA torch).

## Architecture boundary

`xninetzy/context/media/video/` — NO `subprocess` import.

```
$ grep -rE "import subprocess" /home/misbahul45/code/xninetzy/xninetzy/context/media/video/
(empty)

$ grep -rE "import subprocess" /home/misbahul45/code/xninetzy/xninetzy/interfaces/media/video_backends/
xninetzy/interfaces/media/video_backends/remotion.py:import subprocess
xninetzy/interfaces/media/video_backends/ffmpeg.py:import subprocess
```

Architecture boundary test (`tests/architecture/test_context_boundary.py`) **5/5 passing**.

## MCP tools registered

`xninetzy.tools.ecosystem.media_video_tools.media_video_tools` exposes:

- `video_project_create`
- `video_project_inspect`
- `video_project_export_json`
- `video_template_apply`
- `video_asset_import`
- `video_scene_create`
- `video_motion_apply`
- `video_render`
- `video_render_status`
- `video_render_cancel`
- `video_inspect`
- `video_export`
- `video_thumbnail_create`
- `video_session_start`
- `video_session_stop`
- `video_renderer_health`

All 16 are registered via `xninetzy.tools.registry.get_all_tools()` (529 total tools; media group = 21 entries).

## Skill routing

`xninetzy/skills/router.py:INTENT_CLASSES` now includes MEDIA. Keywords cover "video", "motion", "render", "scene", "timeline", "composition", "ken burns", "camera push", "showcase", "tutorial", "demo", "storyboard", "motion graphics", "remotion", "ffmpeg", "after effects", "lower third", "title card", "highlight", "spotlight", "callout", "zoom", "pan", "animasi", "rendering", "preview".

`pipeline_for_intent("MEDIA")` returns `["media-video-root", "media-video-capture", "media-video-edit", "media-video-motion", "media-video-render", "media-video-project-demo", "media-video-tutorial", "media-video-development"]` — the dispatcher (`media-video-root`) at the head ensures every MEDIA request is first routed to the dispatcher, which then resolves the sub-skill from the rich description.

## End-to-end smoke (executed in this session)

```text
1. video_project_create          → project_id=proj-xxx, composition_id=comp-xxx
2. video_template_apply (project_demo) → 5 scenes: intro / arch / demo / result / outro
3. video_render (quality=fast, max_runtime=60) →
   status=completed
   codec=libx264
   size_bytes=8085
   resolution=1920x1080 (square_social preset)
   duration_seconds=1.0
   output_path=/home/misbahul45/Documents/xninetzy/output/video/proj-xxx-r-yyy.mp4
4. video_render_status →
   events=[created → running → validating → completed]
   exit_code=0
5. video_inspect →
   ffprobe: streams[0].codec_name=h264, duration=1.000000, 30 frames
   content_hash: SHA-256 of file bytes
6. video_thumbnail_create (at_seconds=0.0) →
   PNG file produced
7. video_export (destination=/tmp/...) →
   file copied to destination
```

All steps successful. Real MP4 produced and validated. State machine persisted (created → running → validating → completed).

## Two-layer architecture (per the prompt's instruction)

```
Layer 1 — Python (source of truth)
  VideoProject, RenderRequest, build_props()
  ↓ JSON files
  video-project.json, render-props.json

Layer 2 — Remotion (stable runtime at xninetzy/renderers/remotion/)
  Root.tsx registers ProjectDemo / Tutorial / DevelopmentVideo / MotionGraphic
  loadProject() reads JSON props
  npx remotion render src/Root.tsx ProjectDemo out.mp4
  Chromium runs with --no-sandbox --disable-gpu (CPU-only)
```

Python NEVER re-implements `useCurrentFrame / interpolate / Composition`. Remotion owns the runtime. Python only sends data.

## CPU enforcement

1. `xninetzy.runtime.cpu_guard.validate_cpu_only_runtime()` at boot — rejects CUDA torch + GPU FAISS.
2. `classify_encoder()` denies `h264_nvenc / h264_qsv / h264_amf / h264_vaapi / h264_videotoolbox / h264_mf` + hevc variants.
3. `RemotionBackend` sets Chromium flags `--no-sandbox --disable-gpu --disable-software-rasterizer --disable-dev-shm-usage --no-zygote` before each render.

## What is intentionally NOT done

- No generative video model integration (Veo / Sora / Runway / Kling / Pika). Explicitly out of scope.
- No browser-capture pipeline wiring. `video_session_start` reserves a `session_id` and emits an event; integration with `xninetzy/os/auth/browser/gateway.py` is a follow-up.
- No Remotion `npm install` has been executed (Node.js deps not downloaded); the canonical TS files are version-controlled but the runtime install is opt-in via `scripts/setup_remotion_renderer.py`.
- No TTS / voice cloning / AI music generation.
- No MCP tool actually renders via Remotion — that path requires running `scripts/setup_remotion_renderer.py` first to bootstrap the runtime.

## How to activate Remotion rendering (when ready)

```bash
uv run python scripts/setup_remotion_renderer.py
```

This copies `xninetzy/renderers/remotion/` to `~/.local/share/xninetzy/video/remotion/` and runs `npm install` once. After that, the FFmpegRenderer + RemotionBackend dispatcher will pick the right renderer based on capability requirements.

## Known limitations / future work

1. `video_session_start` / `video_session_stop` are stubs — they emit events but do not yet invoke the existing browser gateway. Wiring is straightforward (use `xninetzy.os.auth.browser.gateway.launch_local_browser`) but requires a stable session model.
2. The skill router's primary skill selection is approximate; the `media-video-root` dispatcher is the authoritative router.
3. `xninetzy/context/media/video/storage.py:_project_from_dict` deserializes JSON back into VideoProject; round-trip is covered by tests but extreme edge cases (deeply nested motion_presets with custom cubic-bezier parameters) may need more round-trip coverage.
4. Architecture-boundary test has a known gap: it does NOT reject `subprocess` imports from `xninetzy/context/**` (only `INTAKE_FORBIDDEN_CALLABLES` in `intake/`). This is documented in the Phase 0 audit. The current layout is correct (subprocess in `interfaces/`); a tighter test would lock this in.
