"""Flatten structured resume JSON and embed it for semantic job matching."""

from __future__ import annotations

import argparse
import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
_WHITESPACE_RE = re.compile(r"\s+")

DUMMY_RESUME: dict[str, Any] = {
    "candidate_profile": {
        "inferred_seniority": "Mid-level",
        "primary_domain": "Backend engineering",
        "career_trajectory": "Moved from internships into full-stack product work.",
    },
    "executive_summary": (
        "Software engineer with Python and Flask experience. "
        "Focused on APIs, data pipelines, and search."
    ),
    "core_competencies": {
        "technical_skills": ["Python", "REST APIs", "SQL"],
        "domain_knowledge": ["Job matching", "Information retrieval"],
        "tools_and_frameworks": ["Flask", "PostgreSQL", "SentenceTransformers"],
    },
    "professional_experience": [
        {
            "title": "Software Engineer",
            "organization": "Acme Corp",
            "duration": "2023–2025",
            "responsibilities": [
                "Built resume parsing services",
                "Shipped semantic search for job recommendations",
            ],
        }
    ],
    "academic_and_project_portfolio": [
        {
            "title": "Job Hunt Matcher",
            "type": "project",
            "description": "Embedded resumes and queried ChromaDB for top roles.",
        }
    ],
}


def _clean_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value).strip()


def _join_phrases(values: Any) -> str:
    if not isinstance(values, list):
        return ""
    phrases = [_clean_text(str(item)) for item in values if str(item).strip()]
    return ", ".join(phrases)


def flatten_resume_for_search(resume: dict[str, Any]) -> str:
    """Flatten competencies, domain knowledge, and experience into search text."""
    if not isinstance(resume, dict):
        raise TypeError("resume must be a dictionary produced by parse_resume.")

    parts: list[str] = []
    competencies = resume.get("core_competencies") or {}
    if not isinstance(competencies, dict):
        competencies = {}

    technical_skills = _join_phrases(competencies.get("technical_skills"))
    domain_knowledge = _join_phrases(competencies.get("domain_knowledge"))
    tools = _join_phrases(competencies.get("tools_and_frameworks"))

    if technical_skills:
        parts.append(f"Technical skills: {technical_skills}.")
    if domain_knowledge:
        parts.append(f"Domain knowledge: {domain_knowledge}.")
    if tools:
        parts.append(f"Tools and frameworks: {tools}.")

    experience = resume.get("professional_experience") or []
    if isinstance(experience, list):
        for job in experience:
            if not isinstance(job, dict):
                continue
            title = _clean_text(str(job.get("title") or ""))
            organization = _clean_text(str(job.get("organization") or ""))
            duration = _clean_text(str(job.get("duration") or ""))
            responsibilities = _join_phrases(job.get("responsibilities"))

            header_bits = [bit for bit in (title, organization, duration) if bit]
            if header_bits:
                parts.append("Experience: " + " | ".join(header_bits) + ".")
            if responsibilities:
                parts.append(f"Responsibilities: {responsibilities}.")

    flattened = _clean_text(" ".join(parts))
    if not flattened:
        raise ValueError(
            "Resume JSON had no core competencies, domain knowledge, or experience to embed."
        )
    return flattened


@lru_cache(maxsize=1)
def get_embedding_model():
    """Load the MiniLM model once per process."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_text(text: str) -> list[float]:
    """Convert flattened resume text into a dense embedding vector."""
    cleaned = _clean_text(text)
    if not cleaned:
        raise ValueError("Cannot embed empty text.")

    vector = get_embedding_model().encode(
        cleaned,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vector.tolist()


def vectorize_resume(resume: dict[str, Any]) -> list[float]:
    """Flatten parse_resume JSON and return a SentenceTransformer embedding."""
    return embed_text(flatten_resume_for_search(resume))


def _load_resume_json(path: str | None) -> dict[str, Any]:
    if path is None:
        return DUMMY_RESUME
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON at {path} must be an object.")
    return payload


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="Flatten resume JSON and generate a MiniLM embedding."
    )
    parser.add_argument(
        "json_path",
        nargs="?",
        help="Optional path to a parse_resume JSON file. Uses a dummy profile if omitted.",
    )
    args = parser.parse_args()

    try:
        resume = _load_resume_json(args.json_path)
        flattened = flatten_resume_for_search(resume)
        embedding = embed_text(flattened)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("Flattened text:")
    print(flattened)
    print()
    print(f"Model: {EMBEDDING_MODEL_NAME}")
    print(f"Embedding dimensions: {len(embedding)}")
    print(f"First 8 values: {embedding[:8]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
