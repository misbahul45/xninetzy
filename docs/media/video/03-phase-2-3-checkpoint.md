# Video MCP — Cross-Session Checkpoint

Status: Phases 0, 1, 2, 3, 13, 14 complete. Phases 8, 9, 15 deferred.

## Phase 0 + 1 (delivered earlier in this session)

- `docs/media/video/01-phase-0-audit.md` — 15-section repository audit.
- `docs/media/video/02-phase-1-skill-inventory.md` — vetting + 8 Xninetzy-native `media-video-*` skills.
- 8 skills live under `.agents/skills/media-video-{root,capture,edit,motion,render,project-demo,tutorial,development}/SKILL.md`.
- All 8 skills pass the Xninetzy frontmatter contract (`Dict[str, str]` metadata, body under 500 lines, all required sections).
- All 8 discoverable via `xninetzy.skills.registry.discover_skills()` (zero quality warnings).

## Phase 2 — domain model + motion + project engine + storage + validators + templates

Files (all comment-free, docstring-free, type-hinted):

- `xninetzy/context/media/video/models.py` — `VideoProject`, `VideoComposition`, `VideoScene`, `VideoTrack`, `VideoClip`, `VideoAsset`, `VideoTransition`, `VideoArtifact`, `VideoJob`, `VideoReference`, `VideoAspectRatio`, `Keyframe`, `MotionPreset`, `RenderRequest`, `RenderResult`. Enums: `CompositionPreset`, `RendererId`, `AssetKind`, `TrackKind`, `Easing`, `RendererSelectionReason`.
- `xninetzy/context/media/video/motion.py` — 26 canonical motion primitives resolved to keyframe graphs (`FadeIn/FadeOut/SlideIn/SlideOut/ScaleIn/ScaleOut/Zoom/Pan/Reveal/Typewriter/BlurIn/BlurOut/Pop/Spring/Stagger/Highlight/Spotlight/CameraPush/CameraPull/KenBurns/LowerThird/TitleCard/Callout/CodeHighlight/BrowserFrame/DeviceFrame`).
- `xninetzy/context/media/video/storage.py` — SQLite schema (no new DB file) with `video_projects`, `video_assets`, `video_jobs`, `video_render_events` tables and indexes; `VideoProjectStore`, `VideoAssetStore`, `VideoJobStore` (state machine with `_VALID_TRANSITIONS`).
- `xninetzy/context/media/video/validators.py` — `validate_project`, `validate_motion_preset`, `validate_render_request`, `validate_path_within_roots`.
- `xninetzy/context/media/video/templates.py` — `TemplateContext`, `project_demo_template`, `tutorial_template`, `development_journey_template`, `motion_graph_template`. Deterministic — no LLM.
- `xninetzy/context/media/video/project_engine.py` — `VideoProjectEngine` for create/inspect/version/add_scene/import_asset/build_from_template.
- `xninetzy/context/media/video/renderers/base.py` — `RendererBackend` ABC, `CPU_ALLOWED_ENCODERS`, `GPU_DENIED_ENCODERS`, `classify_encoder`, `select_renderer`, `quantize_request`.
- `xninetzy/context/media/video/renderers/router.py` — `RendererRouter`, `default_router` (capability-based dispatch).

Updated `xninetzy/context/media/video/__init__.py` to export everything.

## Phase 3 — renderer backends + canonical Remotion project

Per architecture-boundary rule (subprocess stays in `interfaces/`, not in `context/`):

- `xninetzy/interfaces/media/video_backends/ffmpeg.py` — `FFmpegRenderer` with libx264/libx265/libvpx/libaom/libsvtav1, GPU encoders explicitly denied via `classify_encoder()`, `ffmpeg_version()`, `ffprobe_version()`, `probe_metadata()`, `quality_to_ffmpeg_args()`.
- `xninetzy/interfaces/media/video_backends/remotion.py` — `RemotionBackend` (CPU-only Chromium flags `--no-sandbox --disable-gpu --disable-software-rasterizer --disable-dev-shm-usage --no-zygote`), JSON props bridge via `build_props()`, cancellation by tracked PID, max_runtime enforcement, structured `RenderResult`.

Canonical Remotion runtime (TS source, no `node_modules`):

```
xninetzy/renderers/remotion/
  package.json
  tsconfig.json
  README.md
  .gitignore
  src/
    Root.tsx
    index.tsx
    runtime/{types,loadProject,loadTimeline,loadAssets}.ts
    motion/{easing,keyframes,presets}.ts
    components/{Scene,VideoClip,TextLayer,ShapeLayer,ImageLayer,CodeLayer,BrowserFrame,LowerThird,Callout,_titlecard}.tsx
    compositions/{ProjectDemo,Tutorial,DevelopmentVideo,MotionGraphic}.tsx
```

The 4 compositions are registered in `Root.tsx` (`ProjectDemo / Tutorial / DevelopmentVideo / MotionGraphic`). Python sends JSON props only; this tree never regenerates per render.

Bootstrap script: `scripts/setup_remotion_renderer.py` (copies template to `~/.local/share/xninetzy/video/remotion` and runs `npm install` once).

## Architecture boundary

`tests/architecture/test_context_boundary.py`: **5/5 passing**.

`subprocess` calls live exclusively under `xninetzy/interfaces/media/video_backends/`. `xninetzy/context/media/video/` has no `subprocess` import.

## CPU-only enforcement

`scripts/verify_cpu_only.py` returns `ok: true`:

- torch 2.13.0+cpu
- torch_cuda_available: false
- faiss_gpu_api: false
- forbidden_packages: []

Three layers of CPU enforcement:

1. `xninetzy.runtime.cpu_guard.validate_cpu_only_runtime()` at boot.
2. `classify_encoder()` denies `h264_nvenc / h264_qsv / h264_amf / h264_vaapi / hevc_vaapi / h264_videotoolbox / h264_mf / hevc_*` (covered by `GPU_DENIED_ENCODERS`).
3. `RemotionBackend` sets `--no-sandbox --disable-gpu --disable-software-rasterizer --disable-dev-shm-usage --no-zygote` on Chromium before each render.

## Test status

`tests/media/video/` — 33/33 passing:

- `test_models.py` (13): resolution envelope, easing endpoints, monotonicity, keyframe interpolation, motion preset canonical set, FFmpeg fallback, etc.
- `test_renderer_selection.py` (8): GPU encoder rejection, capability-based selection, user override, project quantization.
- `test_templates.py` (5): scene ordering, durations sum to composition, all four templates.
- `test_validators.py` (7): project validation, motion preset, render request, path safety, traversal rejection.

`tests/architecture/test_context_boundary.py` — 5/5 passing.

`tests/interfaces/media/` (existing) — 31/31 passing (no regression).

## End-to-end smoke test (executed in this session)

```text
FFmpeg available: True
Render result:
  status: completed
  renderer: ffmpeg-cpu
  codec: libx264
  size: 2606 bytes
  duration: 1.0s @ 30fps (640x360)
  output: /tmp/xninetzy-smoke-aoa9y37v/smoke.mp4
ffprobe version: ffprobe version 6.1.1-3ubuntu5 ...
  stream: h264 640x360 30/1
```

Real MP4 produced, ffprobe validates. No false success.

## Remaining work (deferred to next session)

- **Phase 8** — register MCP tools `video_project_create / video_project_inspect / video_asset_import / video_session_start / video_session_stop / video_timeline_build / video_scene_create / video_motion_apply / video_preview / video_render / video_render_status / video_render_cancel / video_inspect / video_export / video_thumbnail_create` under `xninetzy/tools/ecosystem/media_video_tools.py`.
- **Phase 9** — add `MEDIA` intent class to `xninetzy/skills/router.py` so `media-video-*` skills are picked up by the keyword router (currently they resolve via `discover_skills()` + name match only).
- **Phase 15** — render a real ProjectDemo via `VideoProjectEngine` + `RendererRouter` end-to-end; capture the rendered MP4 + thumbnail into the artifact system; produce an integration smoke test.
- Optional: tighten the architecture-boundary test so `subprocess.*` in `xninetzy/context/**` is rejected (current test has a gap for non-xninetzy stdlib imports).

## Resume hint for next session

1. Add MEDIA intent class to `xninetzy/skills/router.py:INTENT_CLASSES` with keyword set: `[video, motion, render, scene, timeline, composition, ken burns, camera push, showcase, tutorial, demo, storyboard, motion graphics]`.
2. Add `MEDIA` pipeline to `pipeline_for_intent()` routing through `media-video-root` → matched sub-skill.
3. Write `xninetzy/tools/ecosystem/media_video_tools.py` exposing ~12 MCP tools.
4. Wire the tools into `xninetzy/tools/registry.py:get_all_tools()` and `manifest_for()` with `RiskClass.READ` / `WRITE` (no FINAL gate).
5. End-to-end smoke test: `engine.create_project → template → engine.add_scene × N → router.dispatch(VideoProject, RenderRequest)` and assert a real MP4 lands in `OUTPUT_DIR`.
