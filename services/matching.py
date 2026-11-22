
"""Connect the main application to Bao's job matching microservice."""

import os

import requests


MATCH_SERVICE_URL = os.getenv(
    "MATCH_SERVICE_URL",
    "http://127.0.0.1:3117",
).rstrip("/")


def rank_jobs(profile: dict, jobs: list[dict]) -> list[dict]:
    """Send resume and job postings to Bao's matching microservice."""

    if not jobs:
        return []

    try:
        # Send the resume and job postings for matching and ranking.
        response = requests.post(
            f"{MATCH_SERVICE_URL}/match",
            json={
                "resume": profile,
                "jobs": jobs,
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


# Test script for integration.
if __name__ == "__main__":
    profile = {
        "candidate_profile": {
            "inferred_seniority": "Junior",
            "primary_domain": "Software Development",
        },
        "executive_summary": "Junior developer with Python experience.",
        "core_competencies": {
            "technical_skills": ["Python", "JavaScript", "SQL"],
            "domain_knowledge": ["Software Development"],
            "tools_and_frameworks": ["Flask", "Git"],
        },
        "professional_experience": [],
        "academic_and_project_portfolio": [],
    }

    jobs = [
        {
            "id": "1",
            "title": "Junior Python Developer",
            "description": "Develop backend applications using Python and Flask.",
            "company": "ABC Technologies",
            "location": "California",
            "requirements": {
                "job_skills": ["Python", "Flask", "SQL"],
            },
        },
        {
            "id": "2",
            "title": "Frontend Developer",
            "description": "Build web applications using JavaScript and React.",
            "company": "XYZ Solutions",
            "location": "Remote",
            "requirements": {
                "job_skills": ["JavaScript", "React", "HTML"],
            },
        },
    ]

    results = rank_jobs(profile, jobs)

    for index, result in enumerate(results, start=1):
        print(f"\nRank #{index}: {result['job']['title']}")
        print(f"Score:          {result['score']:.2f}")
