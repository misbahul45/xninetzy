# Video MCP — Phase 0 Audit

**Mission source:** `BUILD VIDEO CREATION + VIDEO EDITING capability inside
Xninetzy MCP as a DETERMINISTIC media system (Remotion + FFmpeg + skills +
runtime tools). NO generative video models, NO Veo / Sora / Runway /
Kling / Pika integration. CPU-only runtime.**

This audit inventories the existing infrastructure that the video
subsystem must extend and identifies which pieces are reusable,
which are missing, and which integration points are reserved for the
deterministic video pipeline.

This document supersedes the earlier `docs/video-generation-audit.md`
which described an ffmpeg-only filter composition. The new video
system is broader (development video + project showcase + tutorial +
motion graphics + timeline editing) and adds a programmatic motion
engine + Remotion renderer on top of the same ffmpeg/artifact/job
primitives.

## 1. Scope and non-goals

### In scope

- Video project model (composition, scene, track, clip, asset,
  keyframe, transition, motion, audio, render, artifact).
- After-Effects-like deterministic motion primitives
  (FadeIn, SlideIn, Zoom, CameraPush, KenBurns, LowerThird,
  TitleCard, Callout, etc.).
- Frame-accurate motion graph evaluator with keyframe interpolation
  (linear, ease-in / ease-out / ease-in-out, cubic-bezier).
- Renderer abstraction with two deterministic engines:
  - **Remotion** (Node.js, React, frame-driven composition,
    CPU-only Chromium / `--no-sandbox --disable-gpu`).
  - **FFmpeg** (CPU, libx264 / libx265 / libvpx / libaom / libsvtav1).
- Engine selection by capability, NOT by generative provider.
- Determinism registry (renderer version, project version, asset
  hashes, motion graph hash, render settings) for reproducibility.
- Project capture via Playwright (reuse existing browser gateway) +
  desktop capture via FFmpeg / X11-grab.
- MCP tool surface (project, session, asset, timeline, scene,
  motion, preview, render, inspect, export).
- Skill surface (media.video.root + capture / edit / motion /
  render / project-demo / tutorial / development).
- Skeleton integration with the existing capability graph,
  skill router, provider router, jobs service, policy gate,
  and artifact persistence — without duplicating any of them.

### Out of scope (explicit non-goals)

- Any generative video model integration (Veo / Sora / Runway /
  Kling / Pika / Replicate / Luma / Hailuo / Wan / Vidu / etc.).
- AI image generation, AI audio generation, voice cloning, TTS,
  beat detection, music-video sync.
- Real-time live streaming or sub-second preview.
- A second MCP server, a second skill registry, a second tool
  registry, a second artifact store, a second background queue,
  a second routing architecture.
- Unrestricted `shell_exec(...)` style invocation. Process
  execution must go through typed command builders and an
  allowlisted executable set.
- GPU pipelines (NVENC, QSV, Vulkan, CUDA-FAISS,
  CUDA-Remotion, GPU compositor). CPU only.

### Runtime constraint

**CPU only.** Enforced at three layers:

- `scripts/verify_cpu_only.py` + `xninetzy.runtime.cpu_guard`
  validate at boot that no CUDA torch, no FAISS GPU, no
  forbidden accelerators are installed.
- FFmpeg invocations must use `-c:v libx264` / `libx265` /
  `libvpx-vp9` (CPU) or `libaom-av1` / `libsvtav1` (CPU). NVENC /
  QSV / AMF / VideoToolbox encoders are denied at the executor.
- Remotion render runs with `PUPPETEER_EXECUTABLE_PATH` and
  Chromium flags `--no-sandbox --disable-gpu --disable-software-rasterizer`
  to guarantee CPU canvas rendering.

## 2. Host runtime verification (audit day)

Verified via `which` + `--version` against the system PATH on the
development host:

| Binary | Path | Version | Notes |
|---|---|---|---|
| `ffmpeg` | `/usr/bin/ffmpeg` | `6.1.1-3ubuntu5` | Full filter set, libx264/libx265/libvpx/libaom/libsvtav1/libopus enabled |
| `ffprobe` | `/usr/bin/ffprobe` | bundled with ffmpeg | required for probe / validation |
| `node` | `~/.nvm/versions/node/v24.16.0/bin/node` | `v24.16.0` | runtime for Remotion + Chromium; CPU-only build available |
| `npm` | `~/.nvm/versions/node/v24.16.0/bin/npm` | `11.18.0` | package manager for Remotion deps |
| `npx` | `~/.nvm/versions/node/v24.16.0/bin/npx` | bundled | Remotion CLI entrypoint |

`xninetzy.runtime.cpu_guard.validate_cpu_only_runtime()` runs at MCP
boot to refuse environments that have pulled CUDA-enabled torch,
GPU-enabled FAISS, or other denied accelerators.

Remotion is **not** yet a Python dependency; it will be added as an
**opt-in extra** so the default CPU-only installation does not pull
Node packages. See §11 for the exact `pyproject.toml` extras entry.

## 3. Tooling already wired in `pyproject.toml`

CPU-aligned and already available:

| Concern | Tool / lib | Used as |
|---|---|---|
| MCP server | `mcp>=1.28.1,<2`, `fastapi`, `uvicorn` | already wired |
| Browser automation | `playwright>=1.40` (extra `browser`) | already wired — reuse for browser capture |
| Image inspection | `pillow>=10.0`, `opencv-python-headless>=5.0` | already wired |
| OCR | `pytesseract>=0.3.13` | already wired |
| Retrieval | `faiss-cpu>=1.8`, `sentence-transformers>=3.0` | already wired (CPU only) |
| Vector index | `numpy>=2.0` | already wired |
| Storage | `pydantic>=2.5`, `pydantic-settings>=2.1` | already wired |
| Documents | `python-docx`, `openpyxl`, `python-pptx`, `pypdf`, `pdfplumber`, `pypdfium2` (extra `documents`) | reuse for slide / doc assets |
| Process execution | stdlib `subprocess` is the established primitive; the CLI supervisor, skill tools, and `os/graph/v3/neo4j_lifecycle` already use it. | already wired — no `shellx` library needed |

Tools we must add:

| Tool | Why | Plan |
|---|---|---|
| `remotion` runtime (Node.js side) | render React compositions to MP4. Lives outside Python in a vendored project under `~/.local/share/xninetzy/video/remotion/<project_slug>/`. Invoked through a typed `NpxRunner` adapter with allowlisted argv. | install on first render via the existing `xninetzy_runtime_setup` |
| optional `ffmpeg-python` (or hand-rolled `subprocess` wrapper) | already have `subprocess`; hand-rolled is fine and keeps the dep tree lean. | prefer hand-rolled; only pull `ffmpeg-python` if a feature needs richer filter parsing |

## 4. Existing infrastructure — REUSE matrix

| Layer | Existing component | Path | What the video subsystem reuses |
|---|---|---|---|
| Persistence | SQLite + migrations | `xninetzy/db/sqlite.py`, `xninetzy/db/migrations.py` | New `video_*` migration; reuse `connect()`, idempotency keys (`xninetzy/db/idempotency.py`) |
| Risk / policy | `RiskClass`, `ActionPolicyDecision` | `xninetzy/os/policy/action_policy.py` | `RiskClass.READ` for `video_project_inspect`, `video_render_status`, `video_preview_status`; `RiskClass.WRITE` for create / update / delete / render; `RiskClass.FINAL` only if the owner decides render requires approval |
| Capability graph | typed capability nodes seeded from the tool registry | `xninetzy/context/capability_graph/graph.py` | Seed `media.video.*` aliases so the model sees capability names instead of tool names |
| Skill router | intent-class + keyword scoring | `xninetzy/skills/router.py` + `xninetzy/skills/registry.py` | Add `MEDIA` intent class; route `media.video.*` skills through the same pipeline |
| Provider router | `RouterCandidate`, `RouterDecision` | `xninetzy/context/gateway/router.py` | Use as the **renderer router** (Remotion + FFmpeg). NOT a new router; this is the existing one |
| Tool manifest | `ToolManifest`, `FeaturePack`, `manifest_for()` | `xninetzy/tools/manifest.py` | Add a `MEDIA` feature pack prefix or extend the existing `CORE` mapping for `video_*` tools |
| Tool registry | `get_all_tools()` + `get_tool_groups()` | `xninetzy/tools/registry.py` | Register `video_*` tools via the existing path |
| MCP tool adapter | `add_tool` | `xninetzy/interfaces/mcp_tool_adapter.py` | Same channel |
| Invocation contract | `InvocationRequest`, `validate_invocation_request` | `xninetzy/context/invocation/contract.py` | Enforces idempotency keys for `RiskClass.WRITE` actions; render job creation will receive `SIDE_EFFECT_EXTERNAL` |
| Policy gate | `evaluate_policy`, `record_audit_start` / `complete_audit_entry` | `xninetzy/context/policy/audit.py`, `xninetzy/context/policy/gate.py` | Every `video_*` mutation + every render logs through the audit ledger |
| Trust tiers | `TRUST_TIER_LOCAL`, `EXTERNAL`, `KNOWN_THIRD_PARTY`, `BLOCKED` | `xninetzy/context/gateway/trust.py` | Local FFmpeg / local Remotion render both stay in `TRUST_TIER_LOCAL` |
| Browser gateway | local Playwright / CDP / remote backends | `xninetzy/os/auth/browser/gateway.py`, `xninetzy/os/auth/browser/session_provider.py` | Capture user-approved browser tabs → video assets. NO new browser daemon |
| Job service | claim / lease / crash recovery | `xninetzy/os/jobs/service.py`, `store.py`, `tools.py` | Render jobs use the same scheduler; render is an `EXTERNAL` side-effect |
| Inbox | `capture_item`, `os_inbox`, `os_triage` | `xninetzy/os/inbox/service.py` | Manual capture markers use the same inbox |
| Tool retry budget | `xninetzy/os/tool_retry_budget.py` | existing | Transient ffmpeg / Remotion failures retry inside the same per-tool budget |
| Cache | TTL-bounded provider cache | `xninetzy/context/gateway/provider_cache.py` | Reuse TTL pattern for capability cache (e.g. ffmpeg-version-specific filter hash) |
| Identity / principal | `MCPPrincipal` | `xninetzy/core/identity.py` | Inject owner context into every render |
| Auth + secret redaction | `sanitize_tool_output` | `xninetzy/core/security.py` | Reuse to scrub cookies / tokens from screen capture events |
| Notification | `admin_notifier` | `xninetzy/os/notifications/admin_notifier.py` | Render-finished notifications go to the same admin channel |
| Event bus | `record_event_in_transaction` | `xninetzy/ecosystem/event_bus.py` | `media.video.*` events on the existing bus |
| Observability | `measure()` + `trace.py` | `xninetzy/observability/trace.py`, `perf.py` | `measure()` already wraps every MCP tool call |
| Lightning | episode store | `xninetzy/os/lightning/` | Optional `Lightning` episode per render for self-improvement |
| Existing media | `media_store`, `media_parser`, `media_tools` | `xninetzy/interfaces/media/media_store.py` | Ingest / read media already supported; **do not duplicate**. New `video_assets` table mirrors `media_items` |
| Existing image / OCR | `xninetzy/interfaces/media/image_parser.py` | existing | Frames captured / preview frames go through the same OCR pipeline |
| Skill catalogue | SKILL.md with YAML frontmatter | `.agents/skills/` (121 skill dirs today) | Add `media.video.*` skill folders using the same convention |
| Skill install script | `scripts/install_skills.py` | existing | Used to register the official Remotion Agent Skills (`npx skills add remotion-dev/skills`) |
| Skill repair | `scripts/repair_skill_yaml.py` | existing | Used to fix any broken frontmatter imported from the Remotion skill set |
| CPU guard | `validate_cpu_only_runtime()` + `xninetzy.runtime.cpu_guard` | existing | Enforces no GPU at boot |

## 5. Existing video STUB that this work extends

`xninetzy/context/media/video/` already exists with partial scaffolding
(stub only — `__init__.py` tries to import from `models.py` and
`storage.py` which **do not yet exist**):

```
xninetzy/context/media/video/
  __init__.py     # imports the planned-but-missing models.py + storage.py
  capabilities.py # VideoCapability, VideoMode, VideoAspectRatio enums + VideoModelCapabilities
  errors.py       # 22 VIDEO_* error codes + VideoError class + retryable/terminal classification
```

This audit documents the planned surface; Phase 2 will land the
missing `models.py`, `storage.py`, `jobs.py`, `composition.py`,
`validators.py`, `artifacts.py`, `worker.py`, plus the new
`remotion.py`, `motion.py`, `timeline.py`, `project.py`, `capture.py`,
`router.py`, `telemetry.py` modules.

The previous `docs/video-generation-audit.md` introduced 11 tool
names (`video_create_from_images`, `video_create_ken_burns`,
`video_concat`, `video_transition`, `video_add_text`, `video_trim`,
`video_slideshow`, `video_inspect`, `video_extract_frames`,
`video_get`, `video_cancel`, `video_list`). Those names stay valid
**only as legacy aliases** of the new higher-level tools
(Phase 8 explicitly defines the new surface). Old names should
not be added again — they are superseded by intent-level names.

## 6. Routing — reuse, do not duplicate

`xninetzy` already exposes two routing layers; the video subsystem
participates in both.

### 6.1 Skill router — extends, does not fork

`xninetzy/skills/router.py` defines `INTENT_CLASSES` (currently
`PROFESSIONAL, CONSULTING, PROPOSAL, ACADEMIC, RESEARCH,
TECHNICAL, EDITING, REVIEW`) and a keyword + intent-class scoring
function. **Add a `MEDIA` intent class and a `VIDEO` sub-family
within `MEDIA`**:

```python
INTENT_CLASSES = {
    "PROFESSIONAL", "CONSULTING", "PROPOSAL", "ACADEMIC",
    "RESEARCH", "TECHNICAL", "EDITING", "REVIEW", "MEDIA",
}

INTENT_KEYWORDS = {
    ...,
    "MEDIA": [
        "video", "motion", "render", "scene", "timeline",
        "composition", "ken burns", "camera push", "showcase",
        "tutorial", "demo", "storyboard", "animasi", "video",
        "motion graphics", "remotion", "ffmpeg",
    ],
}

pipelines_for_intent["MEDIA"] = [
    "media.video.project-demo",   # or media.video.tutorial
    "media.video.capture",
    "media.video.motion",
    "media.video.render",
]
```

The keyword scorer, primary / secondary / `detected_classes`
output format, and skill-composer stays the same.

### 6.2 Provider / renderer router — reuse as-is

`xninetzy/context/gateway/router.py` already produces typed
`RouterDecision` with `RouterCandidate(provider_id, capability,
transport, trust_tier, health_state, score, reasons)` and supports
capability toggles, TTL cache, health adjustment, tier clamp. The
two rendering engines are registered as **providers**:

```python
ProviderRecord(
    provider_id="video.renderer.remotion",
    capability="video.motion.render",
    transport=TRANSPORT_LOCAL,
    trust_tier=TRUST_TIER_LOCAL,
    health_state="ok",
)
ProviderRecord(
    provider_id="video.renderer.ffmpeg",
    capability="video.compose.render",
    transport=TRANSPORT_LOCAL,
    trust_tier=TRUST_TIER_LOCAL,
    health_state="ok",
)
```

The existing `evaluate_action()` in `xninetzy/os/policy/action_policy.py`
decides whether to force `ActionMode.APPROVAL` (treat the
`Mode` result as `RiskClass.WRITE` by default — see §10). The
result-level `_FINAL_ACTIONS` set is currently:
`portal_krs_final_submit`, `portal_krs_war_execute`,
`portal_krs_war_arm`, `hebat_submit_submission`,
`hebat_submit_submission_direct`, `qa_submit_kuesioner`,
`tableau_publish_workbook`. Render is **not** added to this set
in Phase 8 (no paid provider, no irreversible side effect).

### 6.3 Capability graph — seed `media.video.*` aliases

`xninetzy/context/capability_graph/graph.py:seed_from_registry()`
walks `xninetzy.tools.registry.get_tool_groups()` and produces
`CapabilityNode(capability=group, surface="tool_group:group",
aliases=...)`. New tool group `media` will seed a
`tool_group:media` capability plus a per-tool capability for
every `video_*` tool that lands in Phase 8. **No separate
graph instance is created.**

## 7. Browser capture — reuse `os/auth/browser`

`xninetzy/os/auth/browser/gateway.py` already implements:

- `BrowserBackend = {NONE, LOCAL, CDP, REMOTE}` with a
  `BrowserBackendAdapter` Protocol.
- `LocalPlaywrightBackend` that uses persistent Chromium profiles
  under `~/.local/share/xninetzy/auth/profiles/<owner>/<session>`.
- `launch_local_browser(session_id, owner, headless, profile_dir)`
  returning the live playwright context.
- `close_local_browser(session_id)` and `active_local_handles()`.
- URL-policy enforcement through
  `xninetzy/os/auth/policies/url_policy.assert_safe_url`.

The video subsystem MUST launch browser capture through this
gateway. It does **not** instantiate its own playwright context.
The deliverable tools:

- `video_session_start` — start a capture session, returns
  `session_id`, `profile_dir`, backend.
- `video_session_capture` — capture currently-visible viewport,
  encode to MP4 via `ffmpeg -video_size WxH -framerate N -f x11grab -i :0.0+0,0`
  on Linux / X11, or `ffmpeg -f avfoundation` on macOS, or
  `ffmpeg -f gdigrab` on Windows. The backend probe lives in
  `xninetzy/interfaces/media/video_backends/capture.py`.
- `video_session_stop` — finalize the capture, store segments
  in the `.dev-video/` tree, emit `media.video.session_stopped`
  on the event bus.

For browser-tab capture, the video pipeline must:

1. Use `xninetzy.os.auth.browser.gateway.launch_local_browser`
   to obtain a session.
2. Use `page.video` (`page.context.new_cdp_session(page)` →
   `start_screencast`) or `context.add_init_script` to wire
   `cdp.Page.startScreencast`.
3. Pipe frames into an `ffmpeg -f image2pipe -framerate N -i - out.mp4`.

This is **exactly** the same pattern used by HEBAT / Cyber Campus
capture routines today (`xninetzy/os/hebat/` and `xninetzy/os/academic/mahasiswa_portal/`).

## 8. Jobs / background execution — reuse, do not duplicate

`xninetzy/os/jobs/` exposes:

- `JobStore` (SQLite-backed claim / lease / crash recovery).
- `service.JobSpec`, `due_job_specs()`, `owner_notification_jid()`,
  `MessageSender` / `HebatRunner` injection points.
- `jobs/tools.py` for MCP-tool registration.

Long video renders MUST be scheduled through `JobStore`, never
through an in-process `asyncio.create_task(...)`. The render
worker is a Python function scheduled as a `JOB_TYPE` in the
existing store, with the render args as JSON in
`JobSpec.payload`. Crash recovery (worker SIGKILL mid-render)
is handled by the existing lease expiry.

A render job has its own state machine independent of the
existing `JobSpec` types; this lives in the new
`xninetzy/context/media/video/jobs.py` module and uses the
existing audit ledger as the primary store.

## 9. Artifact handling — extend `media_store`, do not duplicate

`xninetzy/interfaces/media/media_store.py` already
manages a `media_items` table with `(message_id, local_path,
mime_type, extracted_text, ...)`. New tables:

- `video_projects` — `video-project.json` content + version.
- `video_compositions` — composition settings per project.
- `video_scenes` — ordered scenes per composition.
- `video_tracks` — tracks per scene.
- `video_clips` — clips per track.
- `video_assets` — assets imported into the project
  (path, mime, hash, duration, fps, codec).
- `video_motion_graph` — keyframe graph per clip / asset.
- `video_jobs` — render jobs with the state machine
  `CREATED → QUEUED → RUNNING → VALIDATING → COMPLETED | FAILED
  | CANCELLED | EXPIRED`.
- `video_renders` — render outputs (artifact_id, path, hash).

These are added to `xninetzy/db/migrations.py` as a new
`revision_id`; the existing `xninetzy.db.sqlite.connect()` is
reused. **No new database file. No new sqlite3 module.**

## 10. Security & policy — reuse gate

`xninetzy/os/policy/action_policy.py:evaluate_action(action, payload)`
returns `ActionPolicyDecision(action, risk, mode, allowed,
requires_approval, reason, action_hash)`. It enforces:

- `RiskClass.READ` → `ActionMode.AUTO`.
- `RiskClass.WRITE` → `ActionPolicyDecision` based on
  `ACTION_POLICY_DEFAULT_MODE` (default `APPROVAL`).
- `RiskClass.FINAL` + `ActionMode.AUTO` → forced `APPROVAL`.

The render tool registers as `RiskClass.WRITE` (no FINAL gate). If
the owner later decides render is FINAL, they edit
`_FINAL_ACTIONS` / `_RISK_OVERRIDES`. The CLI supervisor's
`xninetzy.cli.supervisor:subprocess.run` is the established
path for external binary invocation — there is no
`xninetzy.shell.exec_video(...)` shortcut. `tools/manifest.py:manifest_for()`
already encodes `requires_approval` and
`requires_idempotency_key` per tool.

Path policy lives at `xninetzy/os/auth/policies/url_policy.py`
and a sibling `path_policy.py` will be added for video source
validation:

```python
# xninetzy/os/auth/policies/path_policy.py
def assert_safe_asset_path(path: str) -> Path:
    """Reject ../, ssh keys, .env, /proc, /sys.
    Resolve to absolute path under known output / project roots.
    """
```

Bounded executables list lives in `xninetzy.security`
and will be extended with `{"ffmpeg", "ffprobe", "node", "npx"}`.
CPU enforcement (deny NVENC, `cuda`, `vaapi` filter paths) lives
in `xninetzy/interfaces/media/video_backends/ffmpeg.py`.

## 11. MCP tool surface — new additions only

| Tool | Domain | Sub-domain | Mode | Side-effect |
|---|---|---|---|---|
| `video_project_create` | media | project | WRITE | IDEMPOTENT_WRITE |
| `video_project_inspect` | media | project | READ | READ_ONLY |
| `video_asset_import` | media | asset | WRITE | IDEMPOTENT_WRITE |
| `video_session_start` | media | capture | WRITE | EXTERNAL |
| `video_session_capture` | media | capture | WRITE | EXTERNAL |
| `video_session_stop` | media | capture | WRITE | IDEMPOTENT_WRITE |
| `video_timeline_build` | media | timeline | WRITE | IDEMPOTENT_WRITE |
| `video_scene_create` | media | scene | WRITE | IDEMPOTENT_WRITE |
| `video_motion_apply` | media | motion | WRITE | IDEMPOTENT_WRITE |
| `video_preview` | media | render | READ | READ_ONLY |
| `video_render` | media | render | WRITE | EXTERNAL |
| `video_render_status` | media | render | READ | READ_ONLY |
| `video_render_cancel` | media | render | WRITE | IDEMPOTENT_WRITE |
| `video_inspect` | media | artifact | READ | READ_ONLY |
| `video_export` | media | artifact | WRITE | IDEMPOTENT_WRITE |
| `video_thumbnail_create` | media | artifact | WRITE | IDEMPOTENT_WRITE |
| `video_clip_add` | media | timeline | WRITE | IDEMPOTENT_WRITE |
| `video_clip_trim` | media | edit | WRITE | IDEMPOTENT_WRITE |
| `video_transition_add` | media | edit | WRITE | IDEMPOTENT_WRITE |
| `video_text_add` | media | motion | WRITE | IDEMPOTENT_WRITE |
| `video_audio_add` | media | audio | WRITE | IDEMPOTENT_WRITE |

Each tool is implemented in
`xninetzy/tools/ecosystem/media_video_tools.py` using
`langchain_core.tools.tool` (same pattern as
`xninetzy/tools/ecosystem/career_*.py`).

## 12. Skills — new catalogue entries only

Add the following folders under `.agents/skills/` (same YAML
frontmatter, progressive disclosure, COMMAND/CONTRACT/OUTPUT
sections as the 121 existing skills):

| Skill folder | Intent class | Domain | Description |
|---|---|---|---|
| `media-video-root/` | MEDIA | media | dispatcher skill for all video workflows |
| `media-video-capture/` | MEDIA | media | start / stop / inspect a screen-capture session |
| `media-video-edit/` | MEDIA | media | trim / concat / transition existing clips |
| `media-video-motion/` | MEDIA | media | apply deterministic motion presets to scenes |
| `media-video-render/` | MEDIA | media | render a project with deterministic engine selection |
| `media-video-project-demo/` | MEDIA | media | `MEDIA → media.video.project-demo` workflow |
| `media-video-tutorial/` | MEDIA | media | tutorial workflow from codebase + screenshots |
| `media-video-development/` | MEDIA | media | development-journey template (sessions, events) |

The official Remotion Agent Skills (`npx skills add remotion-dev/skills`)
land under `~/.local/share/xninetzy/skills/` (the catalog path in
`XNINETZY_SKILLS_DIR`) and are NOT exposed directly. Instead, the
human-readable knowledge from each upstream skill gets mapped to
the corresponding `media.video.*` skill in `xninetzy`'s own
catalogue (see `docs/video-skill-inventory.md`).

A vetted FFmpeg skill may be added if it integrates cleanly;
arXiv-listed options include `muhammaddadu/ffmpeg-skill`.
Each candidate is vetted per the policies in `scripts/install_skills.py`:
inspect the repository, license, maintenance status, and behaviour
before installation; never run an arbitrary `curl | bash`-style
installer.

## 13. Templates

Reusable, deterministic templates composed of the motion primitives
in §2. Stored under `xninetzy/context/media/video/templates/`:

- `project_demo.py` — intro → problem → architecture → live demo → result.
- `tutorial.py` — hook → context → step 1 / 2 / 3 → result → summary.
- `product_showcase.py` — intro → problem → product → feature → interaction → result → CTA.
- `development_journey.py` — problem → implementation → failure → debugging → resolution → demonstration.

Templates are **functions**, not gen-AI prompts. They take
`ProjectContext` (project root, detected entrypoints, asset list,
available screenshots) and return a populated
`VideoProject` with scenes, durations, and asset references.

## 14. Tests

New tree:

```
tests/media/video/
  test_models.py              # VideoProject, Composition, Scene, Track, Clip
  test_timeline.py            # build/extend/validate timeline
  test_keyframes.py           # linear / ease / cubic-bezier interpolation
  test_motion.py              # motion primitives + presets
  test_factories_video.py     # tiny synthetic mp4/png/svg fixtures
  test_ffmpeg_backend.py      # subprocess wrapper against tiny fixtures
  test_remotion_renderer.py   # composes a deterministic Remotion project
  test_renderer_selection.py  # capability routing for renderer choice
  test_providers_video.py     # health + capability toggle
  test_video_tools_routing.py # skill router sees the new intents
  test_video_jobs.py          # state machine + crash recovery
  test_video_paths.py         # path_policy + safe_asset_path
  tests/architecture/test_video_boundary.py  # context/ cannot import mcp/...
```

Boundary test: `xninetzy/context/media/video/` must not import
`httpx`, `fastapi`, `mcp`, `uvicorn`, `langchain.*`. Same
boundary as the rest of `xninetzy/context/`.

## 15. Documentation updates

- `docs/video-mcp/architecture.md` — components + data flow.
- `docs/video-mcp/project-model.md` — VideoProject schema.
- `docs/video-mcp/timeline.md` — timeline + tracks + clips.
- `docs/video-mcp/motion.md` — keyframes + primitives + presets.
- `docs/video-mcp/renderers.md` — Remotion / FFmpeg selection.
- `docs/video-mcp/mcp-tools.md` — full tool reference.
- `docs/video-mcp/skills.md` — skill catalogue.
- `docs/video-mcp/routing.md` — how the video subsystem
  participates in the existing skill / provider / capability routers.
- `docs/video-mcp/security.md` — threat model + redaction.
- `docs/video-mcp/troubleshooting.md` — common errors.
- `docs/media/video/README.md` — top-level index pointing
  to the `docs/video-mcp/` set.
- `docs/SKILLS_INDEX.md` — append the eight `media-video-*` skills.
- `docs/runbooks/verify-cpu-only-video.md` — CPU-only verify
  for the video subsystem.
- `KNOWN_ISSUES.md` — add a section for the new video subsystem.
- `AGENTS.md` — append a `## Video capability` section that
  describes the routing extension, CPU-only constraint, and
  available skills.

## 16. Duplicate / reuse guardrails — non-negotiable

This audit explicitly forbids creating any of:

- a second MCP server,
- a second skill registry,
- a second tool registry,
- a second artifact store,
- a second background queue,
- a second capability graph,
- a second router (provider / skill / domain),
- a second FFmpeg subprocess path outside the typed contract,
- unrestricted `shell_exec(...)` style invocation,
- unrestricted GPU pipeline.

The architecture boundary test
(`tests/architecture/test_context_boundary.py`) is extended with
`video/*` denied imports. `scripts/verify_cpu_only.py` runs as a
mandatory pre-release gate alongside the existing release gate
(`xninetzy/cli/supervisor.py:release_check`).

## 17. Configuration gaps

`.env.example` already covers HEBAT, Cyber Campus, UACC, knowledge,
skill catalogue, MCP, RAG, jobs, security. New entries (Phase 1):

```ini
# Media / video
VIDEO_ENABLED=true
VIDEO_NODE_BIN=node
VIDEO_NPX_BIN=npx
VIDEO_FFMPEG_BIN=ffmpeg
VIDEO_FFPROBE_BIN=ffprobe
VIDEO_REMOTION_CACHE_DIR=~/.local/share/xninetzy/video/remotion
VIDEO_REMOTION_PNPM_BIN=
VIDEO_OUTPUT_DIR=~/Documents/xninetzy/output/video
VIDEO_MAX_INPUT_SIZE_MB=256
VIDEO_MAX_OUTPUT_SIZE_MB=4096
VIDEO_MAX_DURATION_SECONDS=600
VIDEO_MAX_CONCURRENCY=1
VIDEO_DEFAULT_FPS=30
VIDEO_DEFAULT_RESOLUTION=1920x1080
VIDEO_DEFAULT_CODEC=libx264
VIDEO_RENDER_TIMEOUT_SECONDS=1800
VIDEO_JOB_TTL_SECONDS=86400
VIDEO_BROWSER_CAPTURE_ALLOWLIST=localhost,127.0.0.1
VIDEO_REMOTE_SCREEN_CAPTURE_ENABLED=false
VIDEO_REMOTE_SCREEN_CAPTURE_DENY_WINDOWS=
```

`xninetzy/core/config.py` is the canonical Settings loader; the
new fields are added there with `getattr(settings, ..., default)`
calls so that operators can keep the subsystem disabled via
`VIDEO_ENABLED=false`.

## 18. Phase 0 exit checklist (verified)

- [x] Existing media / video infrastructure inventoried.
- [x] Existing artifact system reuse path documented.
- [x] Existing routing layer reuse path documented
      (skill router, provider router, capability graph, intent registry).
- [x] Existing skills install + repair + healthcheck scripts inventoried.
- [x] No generative video path proposed (out of scope by design).
- [x] CPU-only runtime confirmed; GPU path explicitly forbidden.
- [x] Browser capture path resolved to
      `xninetzy/os/auth/browser/gateway.py`.
- [x] Background render path resolved to `xninetzy/os/jobs/`.
- [x] Policy gate reuse path resolved to
      `xninetzy/os/policy/action_policy.py`.
- [x] Tool manifest / registry integration plan locked in
      (`xninetzy/tools/ecosystem/media_video_tools.py`).

Phase 0 is COMPLETE. Phase 1 (`docs/video-skill-inventory.md` +
Remotion skill vetting + map into `media.video.*` catalogue) is
the next deliverable.

## 19. Open items not yet decided

These are deferred to Phase 1 or Phase 8 decisions — flagged now so
they do not block the audit:

1. Whether `xninetzy` vendors a small subset of `@remotion/*`
   packages or relies on `npx remotion` to install on demand
   (CPU cache `~/.local/share/xninetzy/video/remotion/`).
2. Whether the small `ffmpeg-python` library is added as an
   optional dependency or whether a hand-rolled subprocess wrapper
   is preferred.
3. Whether `xninetzy/context/intake/` is extended with
   `LAYOUT_FILE_VIDEO_PROJECT_JSON` so that
   `video_project_inspect` can recognize
   `.dev-video/project.json` files.
4. Whether render results get a Lightning episode by default or
   only when `LIGHTNING_ENABLED=true`.
5. Whether the video tool group introduces a new
   `FeaturePack.MEDIA_VIDEO` enum value, or whether `video_*`
   tools continue to map to `FeaturePack.CORE`. Pick the smaller
   change in Phase 8.

End of audit.
