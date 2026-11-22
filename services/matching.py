
"""Connect the main application to Bao's job matching microservice."""

import os

import requests


MATCH_SERVICE_URL = os.getenv(
    "MATCH_SERVICE_URL",
    "http://127.0.0.1:3117",
).rstrip("/")


def rank_jobs(profile: dict, jobs: list[dict]) -> list[dict]:
    """Store retrieved jobs, rank the resume, and normalize results."""

    if not jobs:
        return []

    try:
        # Upload Adzuna jobs into Bao's persistent ChromaDB.
        response = requests.post(
            f"{MATCH_SERVICE_URL}/jobs",
            json=jobs,
            timeout=120,
        )
        response.raise_for_status()

        # Rank only jobs from the current search.
        response = requests.post(
            f"{MATCH_SERVICE_URL}/resume",
            json={
                "resume": profile,
                "job_ids": [
                    str(job["id"])
                    for job in jobs
                    if job.get("id")
                ],
            },
            timeout=120,
        )
        response.raise_for_status()

    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(
            "The job matching service is currently unavailable. "
            "Please try again later."
        ) from exc

    except requests.exceptions.Timeout as exc:
        raise RuntimeError(
            "The job matching service took too long to respond. "
            "Please try again later."
        ) from exc

    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            "The job matching service encountered an error. "
            "Please try again later."
        ) from exc

    ranked_jobs = response.json()

    if not isinstance(ranked_jobs, list):
        raise ValueError(
            "Matching service returned an invalid response."
        )

    matches = []

    for result in ranked_jobs:
        job = result["job_posting"]
        score = round(float(result["final_score"]) * 100, 2)

        matches.append({
            "job": job,
            "score": score,
            "skill_score": result.get("skill_score"),
            "semantic_score": result.get("semantic_score"),
        })

    return matches
