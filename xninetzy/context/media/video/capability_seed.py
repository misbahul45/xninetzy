"""MEDIA capability graph seed.

Inserts canonical ``media.video.*`` capability nodes so the
capability graph can resolve ``video``, ``render``, ``screen capture``
and similar queries to the corresponding tool surfaces.

Idempotent. Safe to call multiple times.
"""

from __future__ import annotations

from typing import Iterable

from xninetzy.context.capability_graph.graph import (
    CapabilityNode,
    SeedResult,
    seed_from_registry,
)


MEDIA_CAPABILITY_NODES: tuple[CapabilityNode, ...] = (
    CapabilityNode(
        capability="media.video",
        surface="tool_group:media",
        tool=None,
        aliases=(
            "media", "media.video", "media.video.root",
            "video", "video.mcp", "video-mcp",
        ),
        metadata={"kind": "tool_group", "domain": "media"},
    ),
    CapabilityNode(
        capability="media.video.capture",
        surface="tool:video_session_start",
        tool="video_session_start",
        aliases=(
            "media.video.capture", "video.capture", "video_session_start",
            "video-capture", "screen_capture", "screen-capture",
        ),
        metadata={
            "kind": "tool", "group": "media",
            "skill": "media-video-capture",
        },
    ),
    CapabilityNode(
        capability="media.video.edit",
        surface="tool:video_clip_trim",
        tool="video_clip_trim",
        aliases=(
            "media.video.edit", "video.edit", "video_clip_trim",
            "video-edit", "trim", "concat",
        ),
        metadata={
            "kind": "tool", "group": "media",
            "skill": "media-video-edit",
        },
    ),
    CapabilityNode(
        capability="media.video.motion",
        surface="tool:video_motion_apply",
        tool="video_motion_apply",
        aliases=(
            "media.video.motion", "video.motion", "video_motion_apply",
            "video-motion", "motion_graphics", "after_effects",
        ),
        metadata={
            "kind": "tool", "group": "media",
            "skill": "media-video-motion",
        },
    ),
    CapabilityNode(
        capability="media.video.render",
        surface="tool:video_render",
        tool="video_render",
        aliases=(
            "media.video.render", "video.render", "video_render",
            "video-render", "rendering", "ffmpeg", "remotion",
        ),
        metadata={
            "kind": "tool", "group": "media",
            "skill": "media-video-render",
        },
    ),
    CapabilityNode(
        capability="media.video.project_demo",
        surface="tool:video_template_apply",
        tool="video_template_apply",
        aliases=(
            "media.video.project_demo", "video.project_demo", "project_demo",
            "product_demo", "feature_demo", "video_template_apply",
        ),
        metadata={
            "kind": "tool", "group": "media",
            "skill": "media-video-project-demo",
        },
    ),
    CapabilityNode(
        capability="media.video.tutorial",
        surface="tool:video_template_apply",
        tool="video_template_apply",
        aliases=(
            "media.video.tutorial", "video.tutorial",
            "tutorial", "how-to", "walkthrough",
        ),
        metadata={
            "kind": "tool", "group": "media",
            "skill": "media-video-tutorial",
        },
    ),
    CapabilityNode(
        capability="media.video.development",
        surface="tool:video_template_apply",
        tool="video_template_apply",
        aliases=(
            "media.video.development", "video.development",
            "development", "dev_video", "coding_session",
        ),
        metadata={
            "kind": "tool", "group": "media",
            "skill": "media-video-development",
        },
    ),
)


def seed_media_capabilities(
    *,
    nodes: Iterable[CapabilityNode] | None = None,
) -> SeedResult:
    return seed_from_registry(nodes=list(nodes) if nodes else list(MEDIA_CAPABILITY_NODES))


__all__ = ["MEDIA_CAPABILITY_NODES", "seed_media_capabilities"]
