from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class VideoCapability(StrEnum):
    CREATE_FROM_IMAGES = "create_from_images"
    CREATE_KEN_BURNS = "create_ken_burns"
    CONCAT = "concat"
    TRANSITION = "transition"
    ADD_TEXT = "add_text"
    TRIM = "trim"
    SCALE = "scale"
    SLIDESHOW = "slideshow"
    INSPECT = "inspect"
    EXTRACT_FRAMES = "extract_frames"


LOCAL_BACKEND_ID: str = "ffmpeg"


class VideoMode(StrEnum):
    IMAGES_TO_VIDEO = "images_to_video"
    KEN_BURNS = "ken_burns"
    CONCAT_CLIPS = "concat_clips"
    CROSSFADE = "crossfade"
    OVERLAY_TEXT = "overlay_text"
    TRIM = "trim"
    SLIDESHOW = "slideshow"


class VideoAspectRatio(StrEnum):
    R_16_9 = "16:9"
    R_9_16 = "9:16"
    R_1_1 = "1:1"
    R_4_3 = "4:3"
    R_21_9 = "21:9"


@dataclass(frozen=True, slots=True)
class VideoModelCapabilities:
    backend: str
    modes: frozenset[VideoMode] = field(default_factory=frozenset)
    capabilities: frozenset[VideoCapability] = field(default_factory=frozenset)
    min_duration_seconds: float = 0.5
    max_duration_seconds: float = 120.0
    supported_ratios: frozenset[VideoAspectRatio] = field(
        default_factory=lambda: frozenset(VideoAspectRatio)
    )
    supported_output_codecs: frozenset[str] = field(
        default_factory=lambda: frozenset({"h264", "h265", "vp9", "copy"})
    )
    supported_input_codecs: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {"h264", "h265", "vp9", "mpeg4", "mpeg2", "mpeg1", "av1", "png", "jpeg", "webp", "pnm"}
        )
    )
    max_input_size_mb: int = 256
    max_output_size_mb: int = 2048

    def supports(self, capability: VideoCapability) -> bool:
        return capability in self.capabilities

    def supports_mode(self, mode: VideoMode) -> bool:
        return mode in self.modes


DEFAULT_LOCAL_CAPABILITIES: VideoModelCapabilities = VideoModelCapabilities(
    backend=LOCAL_BACKEND_ID,
    modes=frozenset(VideoMode),
    capabilities=frozenset(VideoCapability),
    min_duration_seconds=0.5,
    max_duration_seconds=120.0,
    supported_ratios=frozenset(VideoAspectRatio),
    supported_output_codecs=frozenset({"h264", "h265", "vp9", "copy"}),
    supported_input_codecs=frozenset(
        {"h264", "h265", "vp9", "mpeg4", "mpeg2", "mpeg1", "av1", "png", "jpeg", "webp", "pnm"}
    ),
    max_input_size_mb=256,
    max_output_size_mb=2048,
)


@dataclass(frozen=True, slots=True)
class VideoCapabilityMatrix:
    entries: tuple[VideoModelCapabilities, ...] = (DEFAULT_LOCAL_CAPABILITIES,)

    def capabilities_for(self, backend: str) -> VideoModelCapabilities | None:
        for entry in self.entries:
            if entry.backend == backend:
                return entry
        return None

    def supported_capabilities(self) -> frozenset[VideoCapability]:
        out: set[VideoCapability] = set()
        for entry in self.entries:
            out.update(entry.capabilities)
        return frozenset(out)

    def supported_modes(self) -> frozenset[VideoMode]:
        out: set[VideoMode] = set()
        for entry in self.entries:
            out.update(entry.modes)
        return frozenset(out)

    def all_backends(self) -> tuple[str, ...]:
        return tuple(entry.backend for entry in self.entries)
