"""Resume parsing adapter used by the Flask pipeline.

The live parser produces a detailed profile, while the matching and UI modules
need a small, stable profile contract.  This module owns that translation and
keeps local demo mode usable when optional AI dependencies are not installed.
"""

from __future__ import annotations

import io
import os
import re
from typing import Any


def _fallback_profile() -> dict[str, Any]:
    return {
        "skills": ["Python", "SQL", "Flask"],
        "experience_years": 2,
        "candidate_profile": {
            "inferred_seniority": "Early career",
            "primary_domain": "Software Engineering",
            "career_trajectory": "Backend and web application development",
        },
    }


def _normalise_profile(profile: dict[str, Any]) -> dict[str, Any]:
    competencies = profile.get("core_competencies") or {}
    skills: list[str] = []
    for key in ("technical_skills", "domain_knowledge", "tools_and_frameworks"):
        values = competencies.get(key, []) if isinstance(competencies, dict) else []
        skills.extend(str(value) for value in values if str(value).strip())

    experience = profile.get("professional_experience") or []
    return {
        **profile,
        "skills": list(dict.fromkeys(skills)),
        "experience_years": len(experience),
    }


def parse_resume(pdf_bytes: bytes) -> dict[str, Any]:
    """Parse uploaded PDF bytes into the profile contract used by the app.

    If ``OPENAI_API_KEY`` and the live parser dependencies are available, the
    detailed parser is used.  Otherwise the deterministic profile keeps the
    local prototype runnable without external services.
    """
    if not pdf_bytes:
        raise ValueError("The uploaded resume is empty.")

    if not os.getenv("OPENAI_API_KEY"):
        return _fallback_profile()

    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError, PyPdfError
        from services.resume_parser import structure_resume_text
    except ImportError as exc:
        raise RuntimeError(
            "AI resume parsing requires the dependencies in requirements.txt."
        ) from exc

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except (PdfReadError, PyPdfError, ValueError) as exc:
        raise ValueError("The uploaded file is not a readable PDF.") from exc
    text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    if not text:
        raise ValueError("The PDF contains no extractable text.")
    return _normalise_profile(structure_resume_text(text))
