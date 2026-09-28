# Video Generation — Phase 0 Audit (LOCAL ONLY)

## Scope

Video generation as a first-class Xninetzy MCP capability implemented
**entirely with local resources**: the `ffmpeg` and `ffprobe` binaries
already available on the host. No paid AI video providers, no
Veo/Runway/Replicate SDKs, no outbound video generation cost.

What the AI gets: the ability to **compose motion videos from
existing artifacts** (images + clips stored locally) using:

- `image → motion video` via pan/zoom (Ken Burns) or
  `still-image → looping clip` filters
- `clip + clip → concatenated video`
- `clip A + clip B → crossfaded transition`
- `image sequence → slideshow video`
- `text → burned-in overlay on a clip`
- `clip → trim / cut / scale`
- `clip → frames (sampling)`

The model never needs to know about the underlying `ffmpeg` filter
graph; it sees stable capability surfaces (see Phase 6).

## Tool runtime reality (verified)

- `which ffmpeg` → `/usr/bin/ffmpeg`
- `which ffprobe` → `/usr/bin/ffprobe`
- Stdlib `subprocess` is the existing execution primitive
  (`xninetzy/cli/supervisor.py:subprocess.run`, `xninetzy/skills/tools.py`,
  `xninetzy/os/graph/v3/neo4j_lifecycle.py`)

If ffmpeg is absent at runtime, capabilities are reported as `UNKNOWN`
/`OFFLINE` by the health probe and the orchestrator refuses with a
structured error (`VIDEO_BACKEND_UNAVAILABLE`). No silent fallbacks
to network services.

## Existing infrastructure (reusable)

| Component | Path | Reuse pattern |
|---|---|---|
| Persistence | `xninetzy/db/sqlite.py`, `xninetzy/db/migrations.py` | Add a `video_*` migration + reusable `connect()` / `init_db()` |
| Idempotency | `xninetzy/db/idempotency.py` | Wrap every mutating tool with the existing `storage_key` pattern |
| Risk classes | `xninetzy/os/policy/action_policy.py` | `RiskClass.READ` for inspect/list/get, `RiskClass.WRITE` for create/cut/trim/add_text/concat/transition, no `FINAL` (no-cost / no-approval gate) |
| Side-effect classes | `xninetzy/context/invocation/classify.py` | Mutating tools use `IDEMPOTENT_WRITE`; long-running operations use `EXTERNAL` (waits on a local subprocess) |
| Capability graph | `xninetzy/context/capability_graph/` | Seed `video_*` aliases so the model sees only capability names |
| Tool manifest | `xninetzy/tools/manifest.py` | New `VIDEO` feature pack or extend `MEDIA` |
| Tool registry | `xninetzy/tools/registry.py` (513 tools canonical) | Register `video_*` through the same channel |
| MCP tool adapter | `xninetzy/interfaces/mcp_tool_adapter.py` | Standard `add_tool` path |
| Domain context | `xninetzy/context/invocation/contract.py` | Same `validate_invocation_request` enforces idempotency keys for write-class calls |
| Event bus | `xninetzy/ecosystem/event_bus.py` (`record_event_in_transaction`) | Reused for `media.video.*` events |
| Observability | `xninetzy/observability/trace.py`, `perf.py` | `measure()` already wraps every MCP tool call |
| Existing media | `xninetzy/interfaces/media/media_store.py`, `media_tools.py` | Existing media understanding tools (analyze, read, OCR) untouched; we add `video_*` next to them |
| Tool retry budget | `xninetzy/os/tool_retry_budget.py` | Transient ffmpeg failures retried inside the same per-tool budget |
| Existing media store | `xninetzy/interfaces/media/media_store.py:media_items` | New `video_artifacts` table follows the same shape |
| Cache | `xninetzy/context/gateway/provider_cache.py` (TTL-bounded) | Reuse TTL pattern for capability cache |
| Identity / principal | `xninetzy/core/identity.py`, `MCPPrincipal` | Inject owner context into every video job |
| Auth + secret redaction | `xninetzy/core/security.py: sanitize_tool_output` | Reuse for tool output sanitization |
| Lifecycle memory | `xninetzy/os/memory/`, `xninetzy/os/lightning/` | Optional Lightning episode per job |

## Components that must be built

| Component | New path | Notes |
|---|---|---|
| Domain models | `xninetzy/context/media/video/models.py` | `VideoGenerationRequest`, `VideoJob`, `VideoArtifact`, `VideoCapability`, `VideoResult`, `VideoError`, `VideoReference`, `VideoComposition` |
| Capability catalogue | `xninetzy/context/media/video/capabilities.py` | Local-only matrix keyed on ffmpeg-version + filter availability |
| Error taxonomy | `xninetzy/context/media/video/errors.py` | 15 structured codes (no `VIDEO_QUOTA_EXCEEDED`, `VIDEO_WEBHOOK_INVALID`, no `VIDEO_RATE_LIMITED`-on-provider) |
| Job state machine | `xninetzy/context/media/video/jobs.py` | `CREATED → QUEUED → RUNNING → DOWNLOADING → COMPLETED` + `FAILED`, `CANCELLED`, `EXPIRED` |
| Job persistence | `xninetzy/context/media/video/storage.py` | Tables: `video_jobs`, `video_job_state_history`, `video_artifacts` |
| FFmpeg backend | `xninetzy/interfaces/media/video_backends/ffmpeg.py` | Subprocess wrapper; pre-flight capability detection |
| Capability probe | `xninetzy/interfaces/media/video_backends/capability_probe.py` | Hash-fingerprinted, cached per ffmpeg version |
| Health probe | `xninetzy/interfaces/media/video_backends/health.py` | `HEALTHY / DEGRADED / OFFLINE / UNKNOWN` |
| Composition engine | `xninetzy/context/media/video/composition.py` | Builds the per-operation ffmpeg argument list from a normalized `VideoComposition` |
| Validators | `xninetzy/context/media/video/validators.py` | Input validation (existing artifact path, duration bounds, codec whitelist, size limit) |
| Artifact pipeline | `xninetzy/context/media/video/artifacts.py` | Hash, ffprobe metadata, size check, retention mark |
| Worker | `xninetzy/context/media/video/worker.py` | Synchronous subprocess with bounded concurrency; claims job → executes → records state |
| MCP tools | `xninetzy/tools/ecosystem/media_video_tools.py` | `video_create_from_images`, `video_create_ken_burns`, `video_concat`, `video_transition`, `video_add_text`, `video_trim`, `video_slideshow`, `video_inspect`, `video_extract_frames`, `video_get`, `video_cancel`, `video_list` |
| Skill | `xninetzy/skills/media_video/` | `media.video-generation` prompts the model on the capability surface |
| Telemetry | `xninetzy/context/media/video/telemetry.py` | Lightning episode per job; `media.video.*` events on the existing bus |
| Tests | `tests/media/video/` + `tests/architecture/` extension | ffmpeg-mocked unit + capability parity + job state + idempotency + artifact + boundary + secrets-untouched |
| Documentation | `docs/media/video-generation.md` | Architecture, capability matrix, ffmpeg requirements, troubleshooting |

## Architecture boundary

Per `tests/architecture/test_context_boundary.py`:

- `xninetzy/context/**` — domain layer; **cannot import** httpx, fastapi,
  mcp, uvicorn, starlette, langchain, requests, urllib3, aiohttp.
- `xninetzy/interfaces/**` — adapters; CAN import external SDKs.
  **MAY** call local binaries via `subprocess` because the boundary
  test only blocks network/HTTP modules — `subprocess` is allowed at
  the context layer for binary execution against the local host,
  consistent with `xninetzy/skills/tools.py:subprocess.run` (currently
  in `skills/`) and the OS-level scheduler in
  `xninetzy/os/jobs/service.py` (which uses `subprocess` via
  `os.system`-free patterns).
- `xninetzy/tools/ecosystem/**` — MCP tool wrappers; use langchain
  `@tool`.

Therefore:

- Video domain logic (orchestrator, router, jobs, validators,
  composition) lives in `xninetzy/context/media/video/`.
- The ffmpeg-process invocation layer lives in
  `xninetzy/interfaces/media/video_backends/ffmpeg.py` so the
  orchestrator can be unit-tested without invoking a real binary.
- MCP tools live in `xninetzy/tools/ecosystem/media_video_tools.py`.

The boundary test will be extended with one rule: `subprocess`
imports are allowed in `xninetzy/context/media/video/` but
`subprocess.Popen` calls are not — workers dispatch into the
backend via the typed contract, not by calling subprocess inline.
(Inline subprocs outside the contract would break testability and
the existing deny-list for `INTAKE_FORBIDDEN_CALLABLES`.)

## Duplication risks (and how we avoid them)

| Risk | Avoidance |
|---|---|
| A second routing architecture | Extend the existing semantic-match capability graph; add `media_video` aliases |
| A second artifact store | Reuse `xninetzy/interfaces/media/media_store.py`; add only the provider-specific fields (`width`, `height`, `fps`, `codec`, `duration_seconds`, `audio_codec`) to `video_artifacts` |
| A second background queue | Reuse `xninetzy/os/jobs/store.py`'s claim/lease pattern for the polling worker; same crash-recovery semantics as the OS scheduler |
| A second notification channel | Dispatch via `xninetzy/os/notifications/admin_notifier.py` and the existing ecosystem event bus |
| Inline ffmpeg subprocess scattered in MCP tools | Always go through `VideoJobManager` → `ffmpeg.run` contract |

## Configuration gaps

`xninetzy/core/config.py` and `.env.example` lack:

- `VIDEO_GENERATION_ENABLED` (default False)
- `VIDEO_FFMPEG_BIN` (default `ffmpeg`)
- `VIDEO_FFPROBE_BIN` (default `ffprobe`)
- `VIDEO_OUTPUT_DIR` (default under `DATA_DIR`)
- `VIDEO_MAX_CONCURRENCY` (default 1)
- `VIDEO_MAX_INPUT_SIZE_MB` (default 256)
- `VIDEO_MAX_OUTPUT_SIZE_MB` (default 2048)
- `VIDEO_MAX_DURATION_SECONDS` (default 120)
- `VIDEO_POLL_INTERVAL_SECONDS` (default 2)
- `VIDEO_MAX_RUNTIME_SECONDS` (default 600)
- `VIDEO_JOB_TTL_SECONDS` (default 86400)

These are added during Phase 1. No secret API keys needed.

## Risk scoring

Per `xninetzy/os/policy/action_policy.py` + `xninetzy/context/invocation/classify.py`:

- READ: `video_inspect`, `video_get`, `video_list`,
  `video_extract_frames`
- WRITE: `video_create_from_images`, `video_create_ken_burns`,
  `video_concat`, `video_transition`, `video_add_text`,
  `video_trim`, `video_slideshow`, `video_cancel`

No `FINAL` class is required because there is no paid provider and
no irreversible external commit. `video_cancel` only marks the job
cancelled locally and stops the in-flight subprocess.

## Out of scope (explicit non-goals)

- Generated-from-prompt synthesis via Veo / Runway / Replicate / Sora /
  any paid video model
- Style transfer, character animation, lip sync, camera motion from a
  learned model — these all require a learned generator
- Webhook callbacks from external providers (no providers)
- Polling of provider-side task state (no provider-side state)
- Real-time video streaming or live preview
- Speech-to-video, music-video sync, beat-detection

If the owner later enables a paid provider, the
`xninetzy/interfaces/media/video_backends/` directory can grow a
`provider.py` sibling without touching the domain layer or MCP
surface.

## Definition of done

The acceptance gate from the mission is reused, minus the
"external provider" items:

- [ ] Existing media domain audited (this doc)
- [ ] Existing artifact system reused
- [ ] Existing routing reused
- [ ] Existing provider abstraction NOT needed (local-only)
- [ ] All canonical video models exist
- [ ] Local ffmpeg backend fully implemented and stubbed for tests
- [ ] Async generation supported (job lifecycle)
- [ ] Job status + cancel supported
- [ ] Capability parity with `ffmpeg -filters` for advertised operations
- [ ] No external network calls in the video code path
- [ ] Job reconciliation on worker restart
- [ ] Artifact persistence + ffprobe metadata + content hash
- [ ] MCP tools registered
- [ ] `media.video-generation` skill registered
- [ ] Capability graph / dynamic routing wired
- [ ] Idempotency keys for every mutating tool
- [ ] Bounded retry for transient subprocess failures
- [ ] Backoff + timeout honored
- [ ] Capability / health probe reports backend state without leaking
      binary paths
- [ ] Cost guard present (defaults to local-only policy, never online)
- [ ] Secret redaction verified (no API keys ever logged)
- [ ] Crash recovery verified (worker survives mid-failure)
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Existing media, YouTube, Figma, PowerPoint, and image tools
      remain green
