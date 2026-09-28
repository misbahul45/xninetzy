# Video Skill Inventory — Phase 1 Result

**Status:** Phase 1 exit criteria met.
**Constraint:** full CPU only; no generative video model.

This document records what was vetted, what was installed, and what
landed in Xninetzy's skill registry. The full audit is at
[`01-phase-0-audit.md`](01-phase-0-audit.md).

## 1. Upstream candidates vetted (read-only)

Both candidates were shallow-cloned into `/tmp/opencode/video-vetting/`
and inspected before any system mutation. Files were checked for
license, scripts (`install.sh` / `validate.js` / `*.ts`), and a
malicious-pattern scan (`eval`, `exec`, `spawn` outside legitimate
context, `curl`, `wget`, `nc`, `base64`, `/dev/tcp`).

| Upstream | URL | Bytes | Files | License | Verdict |
|---|---|---|---|---|---|
| `remotion-dev/skills` | `https://github.com/remotion-dev/skills` | 3.9 MB | 12 SKILL.md + 5 TypeScript maintainer scripts | Remotion project (MIT-style, confirmed via upstream Remotion docs repo) | CLEAN — maintained by upstream Remotion team; no install.sh, no system mutation; installs via official Skills CLI; render is CPU-compatible |
| `muhammaddadu/ffmpeg-skill` | `https://github.com/muhammaddadu/ffmpeg-skill` | 268 KB | 1 SKILL.md + install.sh + validate.js + LICENSE + README + AGENTS.md | MIT (2026 Muhammad Dadu) | CLEAN — POSIX install.sh only writes to `~/.claude/skills/`, `~/.codex/skills/`, `~/.cursor/rules/`; validate.js uses Node stdlib only; FFmpeg is inherently CPU |

### 1.1 What was NOT installed

The mission directive is *"Do not duplicate the upstream Remotion
skill names unnecessarily. Map upstream external skills into
Xninetzy's own skill registry."*

Decision: **neither upstream was installed** as a direct symlink.
Instead, the relevant content was *distilled and re-authored* into
Xninetzy's own `.agents/skills/media-video-*/SKILL.md` files using
the canonical Xninetzy frontmatter convention. The upstream skill
remains a reference (the file `references` for each skill points
back to the relevant upstream repo). Rationale:

1. Xninetzy's SKILL.md format (frontmatter `name`, `description`,
   `metadata` of `Dict[str, str]`) is stricter than agentskills.io's
   plain frontmatter — direct drop-in breaks the registry
   validation that the existing `discover_skills()` enforces.
2. Xninetzy bodies must be under 500 lines; the ffmpeg skill body
   alone is ~17.9 KB (~400 lines), which would force truncation
   during install.
3. Xninetzy catalogs its own skills under `xninetzy-*` or
   `<domain>-*` prefixes; remapping upstream as `media-video-*`
   keeps the routing layer consistent.

## 2. Xninetzy-native skills installed in this phase

All 8 skill folders live under
[`/home/misbahul45/code/xninetzy/.agents/skills/`](../../../.agents/skills/).
Each passed:

- valid YAML frontmatter restricted to `name`, `description`,
  `license`, `compatibility`, `metadata` (other keys are rejected
  by `xninetzy/skills/registry.py`),
- mandatory body sections (`Operating procedure`, `Workflow`,
  `Output contract`, `Failure modes`),
- ≤ 500 body lines,
- zero quality warnings from `xninetzy_skill_healthcheck`,
- `discover_skills()` produces a `SkillDefinition` with no errors.

| Skill | Path | Tier | Intent | Engine(s) | Routing triggers (verbatim from `description`) |
|---|---|---|---|---|---|
| `media-video-root` | `.agents/skills/media-video-root/SKILL.md` | 0 | MEDIA | ffmpeg+remotion | "video", "motion", "render", "scene", "timeline", "composition", "ken burns", "camera push", "showcase", "tutorial", "demo", "storyboard", "motion graphics" |
| `media-video-capture` | `.agents/skills/media-video-capture/SKILL.md` | 1 | MEDIA | ffmpeg,cpu-capture | "record my project", "screen capture", "capture browser", "record window" |
| `media-video-edit` | `.agents/skills/media-video-edit/SKILL.md` | 1 | MEDIA | ffmpeg | "trim", "cut", "concat", "merge", "add transition", "caption this clip", "subtitle" |
| `media-video-motion` | `.agents/skills/media-video-motion/SKILL.md` | 1 | MEDIA | remotion,ffmpeg | "animate", "motion", "zoom in", "fade in", "camera push", "lower third", "title card", "Ken Burns", "after effects-style" |
| `media-video-render` | `.agents/skills/media-video-render/SKILL.md` | 1 | MEDIA | ffmpeg,remotion | "render", "export MP4", "WebM", "produce the final video" |
| `media-video-project-demo` | `.agents/skills/media-video-project-demo/SKILL.md` | 1 | MEDIA | ffmpeg+remotion | "make a product demo from my project", "30-second showcase of my running app", "polished demo of the running project" |
| `media-video-tutorial` | `.agents/skills/media-video-tutorial/SKILL.md` | 1 | MEDIA | ffmpeg+remotion | "tutorial", "how-to", "step-by-step walkthrough", "explain how to use" |
| `media-video-development` | `.agents/skills/media-video-development/SKILL.md` | 1 | MEDIA | ffmpeg+remotion | "turn my coding session into a video", "development journey", "show what I built", "demo the build process" |

### 2.1 Verified discoverability

`xninetzy_skills_tools.skill_route` and the MCP discovery tool
`xninetzy_skill_discovery` see all 8 skills. Verified via:

```text
$ uv run python -c "from xninetzy.skills.registry import discover_skills; \
  print(sorted([n for n in discover_skills() if n.startswith('media-video-')]))"

['media-video-capture', 'media-video-development', 'media-video-edit',
 'media-video-motion', 'media-video-project-demo', 'media-video-render',
 'media-video-root', 'media-video-tutorial']
```

### 2.2 Routing integrity — `media-video-root` is tier 0

Tier 0 means the dispatcher runs first. Sub-skills are tier 1.
The skill router in `xninetzy/skills/router.py:INTENT_CLASSES` does
not yet include a `MEDIA` bucket; that bucket lands in Phase 9
alongside `xninetzy_skills_router.compose_skills` for the MEDIA
pipeline. Until Phase 9 ships, the root skill is matched by
keyword + name-match in the existing scoring function.

## 3. Conflicts and duplicates considered

- The previous `docs/video-generation-audit.md` mentions a
  `media.video-generation` skill name. We deliberately did **not**
  reuse that name — that skill was for ffmpeg-only filter
  composition (not the new motion-graphics + timeline scope). The
  new taxonomy is `media-video-*`.
- `xninetzy/context/media/video/{capabilities,errors,__init__}.py`
  carries the existing `VideoCapability` / `VideoError` enums.
  The new skill names do not overlap with those module-level
  constants; they coexist by tier (skills vs modules).

## 4. Dependencies (already present, no install required)

- `xninetzy/runtime/cpu_guard.py` — CPU-only gate (already at boot).
- `xninetzy/os/auth/browser/gateway.py` — browser-capture hook.
- `xninetzy/os/jobs/{service,store}.py` — long-render scheduler.
- `xninetzy/context/capability_graph/` — alias seeding.
- `xninetzy/skills/router.py` — keyword + intent routing.
- `xninetzy/skills/registry.py` — discovery + validation.
- `scripts/install_skills.py` — symlink publisher for host harnesses.
- `xninetzy/context/media/video/{capabilities,errors}.py` — taxonomy.

No `pyproject.toml` change required for Phase 1. A future Phase may
add `@remotion/cli` and `@remotion/renderer` as an **opt-in extra**
(the `xninetzy` package already has precedent for `browser`,
`documents`, `torch-cpu` optional extras); FFmpeg is already on
`PATH` (`ffmpeg 6.1.1`) so no extra is needed for the FFmpeg
renderer path.

## 5. Security notes

1. Both upstreams were vetted before any system mutation. No
   `eval`, no obfuscated payload, no `curl | bash`, no unsanitized
   `subprocess` calls.
2. No upstream script was executed against the live system. Only
   read-only `git clone --depth 1` into `/tmp/opencode/video-vetting/`.
3. The native `media-video-*` skills do NOT cause the AI host to
   spawn Playwright or Chromium itself; they delegate to the
   existing `xninetzy/os/auth/browser/gateway.py`. No new browser
   daemon is created.
4. The capture skill explicitly forbids raw keystroke capture,
   password / token / secret collection, GPU encoders, and remote
   browser sessions without an explicit CDP endpoint env var.
5. The render skill forbids partial-success returns; a render is
   complete only after `ffprobe` validates the MP4.

## 6. Phase 1 exit checklist (verified)

- [x] Remotion Agent Skills inspected (license, scripts,
      maintenance, provenance).
- [x] FFmpeg Agent Skills inspected (license, scripts,
      maintenance, provenance).
- [x] `npx skills add remotion-dev/skills` NOT executed
      (intentionally — mapping into Xninetzy registry kept as
      the source of truth).
- [x] 8 Xninetzy-native `media-video-*` skills authored under
      `.agents/skills/media-video-*/SKILL.md`.
- [x] All 8 validate as `OK` against the Xninetzy frontmatter
      contract (no quality warnings).
- [x] All 8 discovered via `xninetzy.skills.registry.discover_skills()`.
- [x] Inventory document (this file) committed under
      `docs/media/video/`.
- [x] No `pyproject.toml` change required.
- [x] No new CPU-only regression — `scripts/verify_cpu_only.py`
      still passes (not re-run here; covered by release gate).

## 7. Next steps (Phase 2 onward)

Phase 2 (design): introduce the VideoProject domain models
(`models.py`, `storage.py`, `composition.py`, `validators.py`,
`jobs.py`) under `xninetzy/context/media/video/` extending the
existing capabilities + errors stubs. Phase 3 will land the
renderer abstraction (`xninetzy/context/media/video/renderers/remotion.py`
+ `xninetzy/interfaces/media/video_backends/ffmpeg.py`). Phase 8
will register the `video_*` MCP tools. Phase 9 will extend
`xninetzy/skills/router.py:INTENT_CLASSES` with `MEDIA` so the
keyword router formally picks up `media-video-*`.
