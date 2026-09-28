from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from xninetzy.context.routing.dataset import (
    DATASET_VERSION,
    adversarial_curated_set as _original_adversarial,
)


CONFUSION_PAIR_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "label": "research_knowledge",
        "positive": ("research",),
        "queries": (
            "find papers on transformer architecture",
            "summarize recent work on diffusion models",
            "research the literature on reinforcement learning",
            "look up papers about graph neural networks",
            "search the literature on meta-learning",
            "find arxiv papers on few-shot learning",
            "research benchmarks for question answering",
            "look up papers on causal inference",
            "find studies on transfer learning",
            "search papers about self-supervised learning",
            "look up recent papers on prompt engineering",
            "find surveys on retrieval augmented generation",
            "research papers on mixture of experts",
            "look up papers on chain of thought prompting",
            "find papers on in-context learning",
            "search for papers on RLHF",
            "research papers on constitutional AI",
            "find papers on mechanistic interpretability",
            "look up papers on neural architecture search",
            "find papers on model distillation",
        ),
        "tools": ("research_search_papers", "research_get_paper"),
    },
    {
        "label": "research_academic",
        "positive": ("research", "academic"),
        "queries": (
            "find papers on active learning",
            "research Bayesian optimization papers",
            "look up ICLR submissions on curriculum learning",
            "search for NeurIPS papers on multi-task learning",
            "find academic papers on continual learning",
            "look up ICML papers on Bayesian deep learning",
            "find CVPR papers on visual question answering",
            "research ACL papers on low-resource NLP",
            "find papers on knowledge graph embeddings",
        ),
        "tools": ("research_search_papers", "hebat_sync_assignments"),
    },
    {
        "label": "learning_academic",
        "positive": ("learning",),
        "queries": (
            "study for my exam tomorrow",
            "review my flash cards for calculus",
            "go through today's study plan",
            "do spaced repetition on JavaScript",
            "review what I learned this week",
            "master data structures for interview",
            "study for the GRE math section",
            "what should I study today",
            "build a learning roadmap for ML",
            "review flashcards for organic chemistry",
            "plan my study schedule for next week",
            "show me my weakest topics",
            "create flashcards from these notes",
            "record what I learned today",
            "schedule study time for linear algebra",
            "show me my mastery progress",
            "review concept maps for distributed systems",
            "build a study plan for the bar exam",
            "track my retention rate for organic chem",
            "find prerequisites for advanced calculus",
        ),
        "tools": ("learning_generate_today_plan", "learning_due_recall", "learning_create_recall_card"),
    },
    {
        "label": "software_security",
        "positive": ("security", "software"),
        "queries": (
            "scan this code for SQL injection",
            "audit my API for broken auth",
            "review dependencies for known CVEs",
            "check this repository for secrets",
            "find XSS vulnerabilities in my frontend",
            "do SAST on the xninetzy codebase",
            "audit my API endpoints for IDOR",
            "check my container image for vulns",
            "find hardcoded secrets in this code",
            "scan for path traversal in this endpoint",
            "audit authentication flow for bypass",
            "review rate limiting on my API",
            "check TLS configuration on my server",
            "scan for open redirects in my URLs",
            "audit CSRF protection on forms",
            "find insecure deserialization in input handlers",
        ),
        "tools": ("security_sast", "security_dependencies", "repo_search", "security_scope"),
    },
    {
        "label": "browser_academic",
        "positive": ("academic", "browser"),
        "queries": (
            "check HEBAT for new assignments",
            "look at my Moodle dashboard",
            "submit my paper to the journal portal",
            "browse Cyber Campus for grades",
            "check my enrollment status",
            "open Cyber Campus for KRS",
            "navigate to my HEBAT assignment page",
            "view the journal reviewer portal",
            "submit my paper through the journal site",
        ),
        "tools": ("hebat_sync_assignments", "web_discover", "web_fetch"),
    },
    {
        "label": "media_data",
        "positive": ("media",),
        "queries": (
            "render the video I just edited",
            "make a motion graphic intro",
            "produce a demo video for the project",
            "export the video to mp4",
            "build a tutorial video from my notes",
            "create a 30-second showcase of the app",
            "produce a motion graphic explainer",
            "render the project at 1080p",
            "add a camera push to the intro scene",
            "export the rendered video to my downloads",
        ),
        "tools": ("video_render", "video_project_create", "video_scene_create"),
    },
    {
        "label": "knowledge_productivity",
        "positive": ("knowledge", "os"),
        "queries": (
            "remember this for later",
            "what did I save last week about",
            "capture this idea",
            "recall the conversation I had yesterday",
            "find the notes I made about this",
            "search my saved articles on prompt engineering",
            "what did I bookmark about transformers",
            "find my note on graph databases",
            "recall the article I saved about RAG",
            "look up my notes on differential privacy",
        ),
        "tools": ("memory_add", "memory_relevance", "memory_search", "unified_search"),
    },
    {
        "label": "os_automation",
        "positive": ("os",),
        "queries": (
            "show my tasks for today",
            "what's on my plate this week",
            "list my open loops",
            "review my goals progress",
            "create a new task",
            "mark this task done",
            "what habits did I log today",
            "show my workout summary this week",
            "summarize my spending this month",
            "review my reminders for tomorrow",
        ),
        "tools": ("task_today", "task_list", "personal_open_loop_list", "goal_list", "task_capture"),
    },
    {
        "label": "career_academic",
        "positive": ("career",),
        "queries": (
            "find an internship at a research lab",
            "search ML engineer roles at a startup",
            "find academic industry research positions",
            "find a postdoc in machine learning",
            "search for research engineer roles",
            "find a senior data scientist role at a fintech",
            "search for ML research scientist positions",
            "find an internship doing RL research",
            "search for a CV/resume-tailored ML role",
        ),
        "tools": ("career_search_jobs", "career_search_internships"),
    },
    {
        "label": "data",
        "positive": ("data",),
        "queries": (
            "profile this CSV",
            "audit the data quality of this dataset",
            "generate an xlsx from this data",
            "make a dashboard from this sales CSV",
            "build a chart of monthly revenue",
            "run a quality audit on the user table",
            "compute stats on the production dataset",
            "export this query to Excel",
            "validate the schema of the input file",
        ),
        "tools": ("data_profile", "data_quality_audit", "data_generate_xlsx", "dashboard_generate"),
    },
    {
        "label": "negation",
        "positive": (),
        "queries": (
            "don't include any sources",
            "exclude academic results",
            "without using a browser",
            "never mind",
            "skip the dashboards",
            "don't use the embeddings model",
            "without the embeddings index",
            "exclude any code search",
            "skip the LLM call",
            "no academic content please",
            "don't add any tasks",
        ),
        "tools": (),
    },
    {
        "label": "state_dependent",
        "positive": (),
        "queries": (
            "render it",
            "submit it",
            "delete it",
            "open it",
            "send it",
            "update it",
            "approve it",
            "check it",
            "publish it",
            "analyze it",
        ),
        "tools": (),
    },
    {
        "label": "ambiguous",
        "positive": (),
        "queries": (
            "do that",
            "fix this",
            "make it better",
            "analyze it",
            "process the thing",
            "do the thing",
            "help with this",
            "figure it out",
            "do the work",
            "handle it",
            "process this",
            "work on it",
            "do something",
        ),
        "tools": (),
    },
    {
        "label": "files",
        "positive": ("files",),
        "queries": (
            "extract text from this PDF",
            "summarize this document",
            "convert the markdown to PDF",
            "extract tables from this report",
            "OCR this scanned image",
            "find files matching this pattern",
            "compare two document versions",
            "parse this CSV file",
            "create an ADR for this decision",
        ),
        "tools": ("media_read_document", "document_tables", "image_ocr", "adr_generate"),
    },
    {
        "label": "automation",
        "positive": ("automation",),
        "queries": (
            "set up a daily briefing workflow",
            "schedule a weekly review",
            "trigger the morning brief now",
            "check the status of the latest run",
            "list the most recent jobs",
        ),
        "tools": ("workflow_status", "workflow_latest", "os_job_status"),
    },
    {
        "label": "communication",
        "positive": (),
        "queries": (
            "send a notification to the owner",
            "notify me when this completes",
            "draft a status update",
            "alert the user about this",
        ),
        "tools": ("admin_notify_progress",),
    },
)


def _row_id(prefix: str, seed: str) -> str:
    return "rt-curated-" + hashlib.sha256(f"{prefix}|{seed}".encode("utf-8")).hexdigest()[:16]


def _build_row(*, prefix: str, text: str, domains: tuple[str, ...], tools: tuple[str, ...], task: str, difficulty: str = "medium") -> dict[str, Any]:
    return {
        "id": _row_id(prefix, text),
        "version": DATASET_VERSION,
        "split": "adversarial",
        "input": {
            "text": text,
            "language": "en",
            "language_mode": "natural",
            "entities": list(tools),
            "constraints": (),
            "desired_output": "tool-call",
        },
        "context": {"chat_id": "<hashed>", "interface": "internal", "turn_index": 0},
        "state": {},
        "task_family": "execute",
        "expected": {
            "domains": list(domains),
            "skills": (),
            "task": task,
            "capabilities": list(domains),
            "tools": list(tools),
            "providers": (),
            "risk_class": "read" if "submit" not in text and "delete" not in text else "write",
            "fallback_tools": (),
            "explanation": "auto-curated from confusion-pair templates",
        },
        "acceptable_alternatives": {"domains": [], "tools": []},
        "risk": "low",
        "difficulty": difficulty,
        "expected_layer": "L6",
        "source": {
            "kind": "auto-curated",
            "label": prefix,
            "extracted_at": "2026-09-28T00:00:00+00:00",
            "extractor": "adversarial_expansion@1.0.0",
            "privacy_pass": "pii_filter",
            "human_validated": False,
        },
    }


def expanded_adversarial_set() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_text: set[str] = set()
    for template in CONFUSION_PAIR_TEMPLATES:
        for query in template["queries"]:
            if query in seen_text:
                continue
            seen_text.add(query)
            rows.append(
                _build_row(
                    prefix=template["label"],
                    text=query,
                    domains=template["positive"],
                    tools=template["tools"],
                    task=template["label"],
                    difficulty="hard" if template["label"] in ("negation", "state_dependent", "ambiguous") else "medium",
                )
            )
    for row in _original_adversarial():
        text = row["input"]["text"]
        if text in seen_text:
            continue
        seen_text.add(text)
        rows.append(row)
    return rows


def write_expanded_adversarial(
    output_path: str | Path = "data/routing_dataset/adversarial_curated.jsonl",
) -> int:
    rows = expanded_adversarial_set()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    import json

    output_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )
    return len(rows)
