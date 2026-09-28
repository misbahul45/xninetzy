from __future__ import annotations

import pytest

from xninetzy.skills.router import (
    INTENT_CLASSES,
    INTENT_KEYWORDS,
    pipeline_for_intent,
    route_request,
)


MEDIA_SKILLS = {
    "media-video-root",
    "media-video-capture",
    "media-video-edit",
    "media-video-motion",
    "media-video-render",
    "media-video-project-demo",
    "media-video-tutorial",
    "media-video-development",
}


def test_media_intent_class_registered():
    assert "MEDIA" in INTENT_CLASSES
    assert "video" in INTENT_KEYWORDS["MEDIA"]
    assert "motion" in INTENT_KEYWORDS["MEDIA"]
    assert "remotion" in INTENT_KEYWORDS["MEDIA"]


def test_media_pipeline_starts_with_dispatcher():
    pipeline = pipeline_for_intent("MEDIA")
    assert pipeline[0] == "media-video-root"
    assert set(pipeline) == MEDIA_SKILLS


def test_route_product_demo_request():
    r = route_request("Make a 30-second product demo of my running React app")
    assert r.primary.intent_class == "MEDIA"
    assert "MEDIA" in r.detected_classes
    assert r.primary.skill_name in MEDIA_SKILLS


def test_route_tutorial_request():
    r = route_request("Create a tutorial step-by-step for my API")
    assert r.primary.intent_class == "MEDIA"
    assert r.primary.skill_name in MEDIA_SKILLS


def test_route_development_request():
    r = route_request("Turn my coding session into a showcase video")
    assert r.primary.intent_class == "MEDIA"
    assert r.primary.skill_name in MEDIA_SKILLS


def test_route_render_request():
    r = route_request("Render the project to MP4")
    assert r.primary.intent_class == "MEDIA"
    assert r.primary.skill_name in MEDIA_SKILLS


def test_route_motion_request():
    r = route_request("Animate this UI with a camera push motion")
    assert r.primary.intent_class == "MEDIA"
    assert r.primary.skill_name in MEDIA_SKILLS


def test_route_edit_request():
    r = route_request("Edit this video with a crossfade transition")
    assert r.primary.intent_class == "MEDIA"
    assert r.primary.skill_name in MEDIA_SKILLS


def test_route_capture_request():
    r = route_request("Record my browser into a screen capture")
    assert r.primary.intent_class == "MEDIA"
    assert r.primary.skill_name in MEDIA_SKILLS


def test_root_skill_always_reachable_when_query_mentions_video():
    r = route_request("video")
    assert r.primary.intent_class == "MEDIA"


def test_research_intent_still_resolves_for_research_query():
    r = route_request("Write a research paper on adaptive learning theory")
    assert r.primary.skill_name in {
        "research", "research-proposal", "academic-writer",
        "literature-review-writer", "research-paper-writer",
    }


def test_media_intent_resolves_for_pure_video_query():
    r = route_request("Make me a polished video of this")
    assert r.primary.intent_class == "MEDIA"
    assert r.primary.skill_name in MEDIA_SKILLS


@pytest.mark.parametrize(
    "query,expected_in_pipeline",
    [
        ("Make a product demo of my app", "media-video-project-demo"),
        ("Tutorial for new users", "media-video-tutorial"),
        ("Capture my screen", "media-video-capture"),
        ("Animate this UI", "media-video-motion"),
        ("Edit the video clip", "media-video-edit"),
        ("Render to MP4", "media-video-render"),
        ("Show my development journey", "media-video-development"),
    ],
)
def test_pipeline_contains_correct_skill_for_query(query, expected_in_pipeline):
    pipeline = pipeline_for_intent("MEDIA")
    assert expected_in_pipeline in pipeline
