"""Rank normalized job postings against a candidate profile."""

from __future__ import annotations

import re
from typing import Any


def _profile_terms(profile: dict[str, Any]) -> set[str]:
    terms = set(str(skill).lower() for skill in profile.get("skills", []))
    candidate = profile.get("candidate_profile") or {}
    if isinstance(candidate, dict):
        terms.update(str(value).lower() for value in candidate.values())
    return {term for term in terms if term}


def rank_jobs(profile: dict[str, Any], jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return up to five jobs scored by transparent lexical relevance.

    This avoids requiring a local embedding model for the first prototype.
    The service boundary remains compatible with the previous ChromaDB result
    shape and can be replaced with semantic scoring later.
    """
    terms = _profile_terms(profile)
    ranked: list[dict[str, Any]] = []
    for index, job in enumerate(jobs):
        text = f"{job.get('title', '')} {job.get('description', '')}".lower()
        matches = sum(bool(re.search(rf"\b{re.escape(term)}\b", text)) for term in terms)
        score = min(100.0, round(35.0 + matches * 13.0, 2))
        ranked.append({"job": job, "score": score, "_index": index})

    ranked.sort(key=lambda item: (-item["score"], item["_index"]))
    return [{key: value for key, value in item.items() if key != "_index"} for item in ranked[:5]]
