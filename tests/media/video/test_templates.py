from __future__ import annotations

from xninetzy.context.media.video.templates import (
    TemplateContext,
    project_demo_template,
    tutorial_template,
    development_journey_template,
    motion_graph_template,
)


def test_project_demo_template_scenes():
    ctx = TemplateContext(project_id="p1", name="Demo", duration_seconds=30.0)
    p = project_demo_template(ctx)
    purposes = [s.purpose for s in p.scenes]
    assert "intro" in purposes
    assert "architecture" in purposes
    assert "demo" in purposes
    assert "result" in purposes
    assert "outro" in purposes


def test_tutorial_template_scenes():
    ctx = TemplateContext(project_id="t1", name="Tutorial", duration_seconds=30.0)
    p = tutorial_template(ctx)
    purposes = [s.purpose for s in p.scenes]
    assert "hook" in purposes
    assert "context" in purposes
    assert purposes.count("step") == 3
    assert "summary" in purposes


def test_development_journey_template_scenes():
    ctx = TemplateContext(project_id="d1", name="Dev", duration_seconds=30.0)
    p = development_journey_template(ctx)
    purposes = [s.purpose for s in p.scenes]
    assert set(purposes) == {"problem", "implementation", "failure",
                              "debugging", "resolution", "demo"}


def test_motion_graph_template_scenes():
    ctx = TemplateContext(project_id="m1", name="Motion", duration_seconds=30.0)
    p = motion_graph_template(ctx)
    assert len(p.scenes) == 1
    assert len(p.scenes[0].motion_presets) == 3


def test_template_scene_durations_sum_to_composition():
    ctx = TemplateContext(project_id="p2", name="Demo", duration_seconds=30.0)
    p = project_demo_template(ctx)
    total = p.compositions[0].duration_frames
    scene_sum = sum(s.duration_frames for s in p.scenes)
    assert scene_sum == total
