from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from xninetzy.context.media.video.models import (
    RenderRequest,
    RenderResult,
    RendererId,
    RendererSelectionReason,
    VideoProject,
)


CPU_ALLOWED_ENCODERS: frozenset[str] = frozenset(
    {"libx264", "libx265", "libvpx-vp9", "libaom-av1", "libsvtav1", "vp9"}
)

GPU_DENIED_ENCODERS: frozenset[str] = frozenset(
    {"h264_nvenc", "hevc_nvenc", "h264_qsv", "hevc_qsv",
     "h264_amf", "hevc_amf", "h264_vaapi", "hevc_vaapi",
     "h264_videotoolbox", "hevc_videotoolbox", "h264_mf", "hevc_mf"}
)


class RendererBackend(ABC):

    renderer_id: RendererId = RendererId.UNKNOWN
    version: str = "0"

    @abstractmethod
    def is_available(self) -> bool:
        ...

    @abstractmethod
    def render(
        self,
        project: VideoProject,
        request: RenderRequest,
    ) -> RenderResult:
        ...

    @abstractmethod
    def cancel(self, render_id: str) -> bool:
        ...

    def health_snapshot(self) -> dict[str, Any]:
        return {
            "renderer_id": self.renderer_id.value,
            "version": self.version,
            "available": self.is_available(),
        }


def classify_encoder(encoder: str) -> str:
    e = encoder.strip().lower()
    if e in GPU_DENIED_ENCODERS:
        raise ValueError(
            f"GPU encoder '{encoder}' is denied (CPU-only runtime)"
        )
    if e in CPU_ALLOWED_ENCODERS:
        return "cpu-allowed"
    raise ValueError(f"unknown encoder '{encoder}'")


def select_renderer(
    capability_requirements: frozenset[str],
    available: dict[RendererId, bool],
    user_override: RendererId | None = None,
) -> tuple[RendererId, RendererSelectionReason]:
    if user_override is not None:
        if available.get(user_override, False):
            return user_override, RendererSelectionReason.USER_OVERRIDE
        return RendererId.UNKNOWN, RendererSelectionReason.NO_RENDERER_AVAILABLE

    needs_remotion = {
        RendererSelectionReason.CAPABILITY_REQUIRES_REMOTION.value,
        "react_composition", "animated_ui", "browser_chrome",
        "device_chrome", "text_anim", "shape_anim",
    }
    if capability_requirements & needs_remotion:
        if available.get(RendererId.REMOTION_CPU, False):
            return RendererId.REMOTION_CPU, RendererSelectionReason.CAPABILITY_REQUIRES_REMOTION
        if available.get(RendererId.FFMPEG_CPU, False):
            return RendererId.FFMPEG_CPU, RendererSelectionReason.CAPABILITY_REQUIRES_FFMPEG
        return RendererId.UNKNOWN, RendererSelectionReason.NO_RENDERER_AVAILABLE

    if available.get(RendererId.FFMPEG_CPU, False):
        return RendererId.FFMPEG_CPU, RendererSelectionReason.DEFAULT_LOCAL_CPU_FFMPEG
    if available.get(RendererId.REMOTION_CPU, False):
        return RendererId.REMOTION_CPU, RendererSelectionReason.HEALTH_AWARE
    return RendererId.UNKNOWN, RendererSelectionReason.NO_RENDERER_AVAILABLE


def quantize_request(
    project: VideoProject, composition_id: str, request: RenderRequest,
) -> tuple[int, int, int, int]:
    composition = next(
        (c for c in project.compositions if c.composition_id == composition_id),
        None,
    )
    if composition is None:
        raise ValueError(
            f"composition_id {composition_id!r} not found in project"
        )
    width = request.width or composition.resolution.width
    height = request.height or composition.resolution.height
    fps = request.fps or composition.fps
    duration_frames = request.duration_frames or composition.duration_frames
    return width, height, fps, duration_frames


__all__ = [
    "RendererBackend",
    "CPU_ALLOWED_ENCODERS",
    "GPU_DENIED_ENCODERS",
    "classify_encoder",
    "select_renderer",
    "quantize_request",
]
