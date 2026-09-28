from __future__ import annotations

from xninetzy.context.media.video.renderers.base import (
    CPU_ALLOWED_ENCODERS,
    GPU_DENIED_ENCODERS,
    classify_encoder,
    select_renderer,
    quantize_request,
)
from xninetzy.context.media.video.models import (
    RendererId,
    RendererSelectionReason,
    VideoComposition,
    Resolution,
    RenderRequest,
    VideoProject,
)


def test_classify_encoder_accepts_cpu():
    for e in CPU_ALLOWED_ENCODERS:
        assert classify_encoder(e) == "cpu-allowed"


def test_classify_encoder_rejects_gpu():
    for e in GPU_DENIED_ENCODERS:
        try:
            classify_encoder(e)
            assert False, f"{e} should be rejected"
        except ValueError:
            pass


def test_classify_encoder_unknown():
    try:
        classify_encoder("obscure_encoder")
        assert False
    except ValueError:
        pass


def test_select_renderer_default_ffmpeg():
    chosen, reason = select_renderer(
        frozenset(),
        {RendererId.FFMPEG_CPU: True, RendererId.REMOTION_CPU: True},
    )
    assert chosen == RendererId.FFMPEG_CPU
    assert reason == RendererSelectionReason.DEFAULT_LOCAL_CPU_FFMPEG


def test_select_renderer_requires_remotion():
    chosen, reason = select_renderer(
        frozenset({"react_composition"}),
        {RendererId.FFMPEG_CPU: True, RendererId.REMOTION_CPU: True},
    )
    assert chosen == RendererId.REMOTION_CPU
    assert reason == RendererSelectionReason.CAPABILITY_REQUIRES_REMOTION


def test_select_renderer_unavailable():
    chosen, reason = select_renderer(
        frozenset({"react_composition"}),
        {RendererId.FFMPEG_CPU: True, RendererId.REMOTION_CPU: False},
    )
    assert chosen == RendererId.FFMPEG_CPU


def test_select_renderer_user_override():
    chosen, reason = select_renderer(
        frozenset(),
        {RendererId.REMOTION_CPU: True, RendererId.FFMPEG_CPU: True},
        user_override=RendererId.REMOTION_CPU,
    )
    assert chosen == RendererId.REMOTION_CPU
    assert reason == RendererSelectionReason.USER_OVERRIDE


def test_quantize_request_falls_back_to_composition():
    composition = VideoComposition(
        composition_id="c",
        name="c",
        resolution=Resolution(1280, 720),
        fps=24,
        duration_frames=240,
    )
    project = VideoProject(
        project_id="p",
        name="p",
        source_project_root=None,
        schema_version="1",
        compositions=[composition],
        scenes=[],
        assets=[],
        created_at="t",
        updated_at="t",
        version=1,
    )
    req = RenderRequest(
        project_id="p",
        composition_id="c",
        project_version=1,
        output_format="mp4",
        output_path="/tmp/x.mp4",
        props_path="/tmp/x.json",
    )
    w, h, fps, dur = quantize_request(project, "c", req)
    assert (w, h, fps, dur) == (1280, 720, 24, 240)
