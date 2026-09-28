from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Any

from xninetzy.context.media.video.errors import VideoError
from xninetzy.context.media.video.models import (
    RenderRequest,
    RenderResult,
    RendererId,
    RendererSelectionReason,
    VideoProject,
)
from xninetzy.context.media.video.renderers.base import (
    RendererBackend,
    quantize_request,
)


REMOTION_PROJECT_ROOT: Path = Path(
    os.environ.get(
        "XNINETZY_REMOTION_PROJECT_ROOT",
        str(Path.home() / ".local" / "share" / "xninetzy" / "video" / "remotion"),
    )
)

REMOTION_ENTRY_FILE: str = os.environ.get(
    "XNINETZY_REMOTION_ENTRY_FILE", "src/index.tsx"
)

REMOTION_DEFAULT_COMPOSITION: str = os.environ.get(
    "XNINETZY_REMOTION_COMPOSITION_ID", "ProjectDemo"
)


def _node_version() -> str:
    if not shutil.which("node"):
        return ""
    proc = subprocess.run(
        ["node", "--version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
        shell=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _npm_version() -> str:
    if not shutil.which("npm"):
        return ""
    proc = subprocess.run(
        ["npm", "--version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
        shell=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _detect_composition_id(project_root: Path) -> str:
    index_tsx = project_root / "src" / "Root.tsx"
    if not index_tsx.is_file():
        return REMOTION_DEFAULT_COMPOSITION
    text = index_tsx.read_text(encoding="utf-8")
    if "ProjectDemo" in text:
        return "ProjectDemo"
    if "Tutorial" in text:
        return "Tutorial"
    if "DevelopmentVideo" in text:
        return "DevelopmentVideo"
    if "MotionGraphic" in text:
        return "MotionGraphic"
    return REMOTION_DEFAULT_COMPOSITION


def resolve_composition_id(requested: str, project_root: Path) -> str:
    if requested and requested != "auto":
        return requested
    return _detect_composition_id(project_root)


def resolve_render_entry(project_root: Path) -> Path:
    candidate = project_root / REMOTION_ENTRY_FILE
    if candidate.is_file():
        return candidate
    fallback = project_root / "src" / "index.tsx"
    if fallback.is_file():
        return fallback
    legacy = project_root / "src" / "Root.tsx"
    if legacy.is_file():
        return legacy
    raise VideoError(
        code="VIDEO_BACKEND_NOT_CONFIGURED",
        message=f"remotion entry not found under {project_root}",
        backend="remotion",
    )


def read_remotion_version(project_root: Path) -> str:
    pkg = project_root / "node_modules" / "@remotion" / "renderer" / "package.json"
    if not pkg.is_file():
        return ""
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    return data.get("version", "")


def tail_lines(text: str | None, n: int) -> str:
    if not text:
        return ""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines[-n:])


def build_props(
    project: VideoProject,
    request: RenderRequest,
    composition_id: str,
    width: int,
    height: int,
    fps: int,
    duration_frames: int,
) -> dict[str, Any]:
    scenes_out = []
    for s in project.scenes:
        if s.composition_id != composition_id:
            continue
        scenes_out.append({
            "scene_id": s.scene_id,
            "name": s.name,
            "purpose": s.purpose,
            "start_frame": s.start_frame,
            "duration_frames": s.duration_frames,
            "tracks": [t.to_dict() for t in s.tracks],
            "transition_in": s.transition_in.to_dict() if s.transition_in else None,
            "transition_out": s.transition_out.to_dict() if s.transition_out else None,
        })

    assets_out = [a.to_dict() for a in project.assets]
    composition_dict = next(
        (c.to_dict() for c in project.compositions if c.composition_id == composition_id),
        None,
    )

    return {
        "schema_version": project.schema_version,
        "render": {
            "width": width,
            "height": height,
            "fps": fps,
            "duration_frames": duration_frames,
            "quality": request.quality,
            "format": request.output_format,
        },
        "project_id": project.project_id,
        "project_name": project.name,
        "composition": composition_dict,
        "scenes": scenes_out,
        "assets": assets_out,
    }


class RemotionBackend(RendererBackend):

    renderer_id = RendererId.REMOTION_CPU
    version = "1.0.0-cpu"

    def __init__(
        self,
        *,
        project_root: Path | None = None,
        node_bin: str = "node",
        npm_bin: str = "npm",
        npx_bin: str = "npx",
        chromium_args: tuple[str, ...] = (
            "--no-sandbox",
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--disable-dev-shm-usage",
            "--no-zygote",
        ),
    ) -> None:
        self._project_root = (
            Path(project_root) if project_root else REMOTION_PROJECT_ROOT
        )
        self._node_bin = node_bin if shutil.which(node_bin) else ""
        self._npm_bin = npm_bin if shutil.which(npm_bin) else ""
        self._npx_bin = npx_bin if shutil.which(npx_bin) else ""
        self._chromium_args = chromium_args
        self._active: dict[str, subprocess.Popen] = {}

    def is_available(self) -> bool:
        if not (self._node_bin and self._npm_bin and self._npx_bin):
            return False
        if not (self._project_root / "package.json").is_file():
            return False
        return (self._project_root / "node_modules").is_dir()

    def health_snapshot(self) -> dict[str, Any]:
        snap = super().health_snapshot()
        snap["node_version"] = _node_version() if self._node_bin else ""
        snap["npm_version"] = _npm_version() if self._npm_bin else ""
        snap["project_root"] = str(self._project_root)
        snap["entry_file"] = REMOTION_ENTRY_FILE
        snap["chromium_args"] = list(self._chromium_args)
        snap["remotion_version"] = read_remotion_version(self._project_root)
        return snap

    def render(self, project: VideoProject, request: RenderRequest) -> RenderResult:
        if not self.is_available():
            raise VideoError(
                code="VIDEO_BACKEND_UNAVAILABLE",
                message=(
                    "remotion not available: missing node/npm/npx or "
                    f"Remotion project under {self._project_root}"
                ),
                backend="remotion",
            )

        composition_id = resolve_composition_id(request.composition_id, self._project_root)
        entry = resolve_render_entry(self._project_root)
        width, height, fps, duration_frames = quantize_request(
            project, composition_id, request
        )
        concurrency = max(1, min(4, request.concurrency))

        props_path = Path(request.props_path)
        props_path.parent.mkdir(parents=True, exist_ok=True)
        props_payload = build_props(
            project, request, composition_id, width, height, fps, duration_frames
        )
        props_path.write_text(
            json.dumps(props_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        env = dict(os.environ)
        existing_flags = env.get("CHROMIUM_FLAGS", "")
        env["CHROMIUM_FLAGS"] = (existing_flags + " " + " ".join(self._chromium_args)).strip()
        env["REMOTION_CACHE_DIR"] = str(self._project_root / ".cache")

        cmd = [
            self._npx_bin,
            "--no-install",
            "remotion",
            "render",
            str(entry),
            composition_id,
            request.output_path,
            "--props", str(props_path),
            "--width", str(width),
            "--height", str(height),
            "--fps", str(fps),
            "--concurrency", str(concurrency),
            "--quality", request.quality,
            "--codec", "h264",
            "--pixel-format", "yuv420p",
            "--log", "info",
        ]
        if request.preview:
            cmd.append("--preview")

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(self._project_root),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
            )
            self._active[request.project_id] = proc
        except FileNotFoundError as exc:
            raise VideoError(
                code="VIDEO_BACKEND_NOT_CONFIGURED",
                message=f"failed to launch remotion: {exc}",
                backend="remotion",
            ) from exc
        except OSError as exc:
            raise VideoError(
                code="VIDEO_GENERATION_FAILED",
                message=f"remotion spawn failed: {exc}",
                backend="remotion",
            ) from exc

        try:
            stdout, stderr = proc.communicate(timeout=request.max_runtime_seconds)
        except subprocess.TimeoutExpired:
            proc.kill()
            self._active.pop(request.project_id, None)
            raise VideoError(
                code="VIDEO_BACKEND_TIMEOUT",
                message=f"remotion timed out after {request.max_runtime_seconds}s",
                backend="remotion",
            )

        self._active.pop(request.project_id, None)

        exit_code = proc.returncode
        if exit_code != 0:
            raise VideoError(
                code="VIDEO_GENERATION_FAILED",
                message=f"remotion exit={exit_code}:\n{tail_lines(stderr, 24)}",
                backend="remotion",
            )

        if not Path(request.output_path).is_file():
            raise VideoError(
                code="VIDEO_OUTPUT_NOT_FOUND",
                message=f"remotion produced no output at {request.output_path}",
                backend="remotion",
            )

        size = Path(request.output_path).stat().st_size
        return RenderResult(
            render_id=request.project_id or "",
            status="completed",
            renderer=RendererId.REMOTION_CPU,
            renderer_version=self.version,
            remotion_version=read_remotion_version(self._project_root),
            output_path=request.output_path,
            duration_seconds=duration_frames / fps,
            width=width,
            height=height,
            fps=fps,
            codec="h264",
            size_bytes=size,
            artifact_id=None,
            exit_code=exit_code,
            stderr_summary=tail_lines(stderr, 4),
            stdout_summary=tail_lines(stdout, 4),
            selection_reason=RendererSelectionReason.CAPABILITY_REQUIRES_REMOTION,
        )

    def cancel(self, render_id: str) -> bool:
        proc = self._active.pop(render_id, None)
        if proc is None:
            return False
        try:
            proc.send_signal(signal.SIGTERM)
        except ProcessLookupError:
            return True
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)
        return True


__all__ = [
    "RemotionBackend",
    "REMOTION_PROJECT_ROOT",
    "REMOTION_ENTRY_FILE",
    "REMOTION_DEFAULT_COMPOSITION",
    "resolve_composition_id",
    "resolve_render_entry",
    "read_remotion_version",
    "build_props",
    "tail_lines",
]
