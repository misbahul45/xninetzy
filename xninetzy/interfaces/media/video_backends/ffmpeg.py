from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any

from xninetzy.context.media.video.errors import VideoError
from xninetzy.context.media.video.models import (
    RenderRequest,
    RenderResult,
    RendererId,
    RendererSelectionReason,
)
from xninetzy.context.media.video.renderers.base import (
    RendererBackend,
    classify_encoder,
    quantize_request,
)


def which(binary: str) -> str:
    found = shutil.which(binary)
    if not found:
        raise VideoError(
            code="VIDEO_BACKEND_NOT_CONFIGURED",
            message=f"required binary '{binary}' not on PATH",
            backend="ffmpeg",
        )
    return found


def ffmpeg_version(binary: str) -> str:
    proc = subprocess.run(
        [binary, "-version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
        shell=False,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.split("\n", 1)[0].strip()


def ffprobe_version(binary: str) -> str:
    proc = subprocess.run(
        [binary, "-version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
        shell=False,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.split("\n", 1)[0].strip()


def probe_metadata(binary: str, path: str) -> dict[str, Any]:
    proc = subprocess.run(
        [
            binary,
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            path,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        shell=False,
    )
    if proc.returncode != 0:
        return {"error": proc.stderr.strip() or "ffprobe failed"}
    try:
        import json
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}


def quality_to_ffmpeg_args(quality: str, encoder: str) -> list[str]:
    q = quality.lower()
    if encoder == "libx264":
        if q == "fast":
            return ["-preset", "ultrafast", "-crf", "26"]
        if q == "high":
            return ["-preset", "slow", "-crf", "18"]
        return ["-preset", "medium", "-crf", "23"]
    if encoder == "libx265":
        if q == "fast":
            return ["-preset", "ultrafast", "-crf", "28"]
        if q == "high":
            return ["-preset", "slow", "-crf", "20"]
        return ["-preset", "medium", "-crf", "25"]
    if encoder in {"libvpx-vp9", "vp9"}:
        if q == "fast":
            return ["-deadline", "realtime", "-cpu-used", "8", "-b:v", "0", "-crf", "32"]
        if q == "high":
            return ["-deadline", "best", "-cpu-used", "0", "-b:v", "0", "-crf", "22"]
        return ["-deadline", "good", "-cpu-used", "2", "-b:v", "0", "-crf", "28"]
    if encoder == "libaom-av1":
        if q == "fast":
            return ["-cpu-used", "8", "-crf", "30"]
        if q == "high":
            return ["-cpu-used", "0", "-crf", "18"]
        return ["-cpu-used", "4", "-crf", "24"]
    return ["-crf", "23"]


CPU_FFMPEG_VERSION_REQUIRED: tuple[int, int] = (4, 0)


class FFmpegRenderer(RendererBackend):

    renderer_id = RendererId.FFMPEG_CPU
    version = "1.0.0-cpu"

    def __init__(
        self,
        *,
        ffmpeg_bin: str = "ffmpeg",
        ffprobe_bin: str = "ffprobe",
        default_encoder: str = "libx264",
    ) -> None:
        classify_encoder(default_encoder)
        self._ffmpeg_bin = ffmpeg_bin if shutil.which(ffmpeg_bin) else ""
        self._ffprobe_bin = ffprobe_bin if shutil.which(ffprobe_bin) else ""
        self._default_encoder = default_encoder

    def is_available(self) -> bool:
        return bool(self._ffmpeg_bin and self._ffprobe_bin)

    def health_snapshot(self) -> dict[str, Any]:
        snap = super().health_snapshot()
        snap["ffmpeg_version"] = (
            ffmpeg_version(self._ffmpeg_bin) if self.is_available() else ""
        )
        snap["ffprobe_version"] = (
            ffprobe_version(self._ffprobe_bin) if self.is_available() else ""
        )
        snap["default_encoder"] = self._default_encoder
        return snap

    def render(self, project, request: RenderRequest) -> RenderResult:
        if not self.is_available():
            raise VideoError(
                code="VIDEO_BACKEND_UNAVAILABLE",
                message="ffmpeg/ffprobe not in PATH",
                backend="ffmpeg",
            )

        composition_id = request.composition_id
        width, height, fps, duration_frames = quantize_request(
            project, composition_id, request
        )
        encoder = self._default_encoder
        classify_encoder(encoder)
        preset_args = quality_to_ffmpeg_args(request.quality, encoder)

        cmd = [
            self._ffmpeg_bin,
            "-y",
            "-nostdin",
            "-f", "lavfi",
            "-i",
            f"color=c=black:s={width}x{height}:r={fps}:d={duration_frames/fps:.4f}",
            "-c:v", encoder,
            "-pix_fmt", "yuv420p",
            *preset_args,
            "-r", str(fps),
            "-movflags", "+faststart",
            request.output_path,
        ]

        env = dict(os.environ)
        env["AV_LOG_FORCE_NOCOLOR"] = "1"

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                check=False,
                timeout=request.max_runtime_seconds,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise VideoError(
                code="VIDEO_BACKEND_TIMEOUT",
                message=f"ffmpeg timed out after {request.max_runtime_seconds}s",
                backend="ffmpeg",
            ) from exc

        if proc.returncode != 0:
            stderr_tail = (proc.stderr or "").strip().splitlines()[-12:]
            raise VideoError(
                code="VIDEO_GENERATION_FAILED",
                message=f"ffmpeg exit={proc.returncode}: " + "\n".join(stderr_tail),
                backend="ffmpeg",
            )

        size = (
            os.path.getsize(request.output_path)
            if os.path.exists(request.output_path) else 0
        )

        return RenderResult(
            render_id=request.project_id or "",
            status="completed",
            renderer=RendererId.FFMPEG_CPU,
            renderer_version=self.version,
            remotion_version="",
            output_path=request.output_path,
            duration_seconds=duration_frames / fps,
            width=width,
            height=height,
            fps=fps,
            codec=encoder,
            size_bytes=size,
            artifact_id=None,
            exit_code=proc.returncode,
            stderr_summary=_tail(proc.stderr, 4),
            stdout_summary=_tail(proc.stdout, 4),
            selection_reason=RendererSelectionReason.CAPABILITY_REQUIRES_FFMPEG,
        )

    def cancel(self, render_id: str) -> bool:
        return False


def _tail(text: str | None, n: int) -> str:
    if not text:
        return ""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines[-n:])


__all__ = [
    "FFmpegRenderer",
    "which",
    "ffmpeg_version",
    "ffprobe_version",
    "probe_metadata",
    "quality_to_ffmpeg_args",
    "CPU_FFMPEG_VERSION_REQUIRED",
]
