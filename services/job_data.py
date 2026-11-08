
"""Retrieve real job postings from Adzuna for the matching pipeline."""

import os

import requests
from dotenv import load_dotenv

load_dotenv()  # Read .env from the project directory (if present).


class JobSearchError(RuntimeError):
    """Raised when Adzuna cannot return a usable job-search response."""


DEMO_JOBS = [
    {
        "id": "demo-python",
        "title": "Python Backend Developer",
        "description": "Build Flask APIs and data services using Python and SQL.",
        "company": "Demo Labs",
        "location": "Remote",
        "url": "https://example.com/jobs/demo-python",
    },
    {
        "id": "demo-software",
        "title": "Software Engineer",
        "description": "Develop reliable web applications and collaborate on product features.",
        "company": "Prototype Systems",
        "location": "Remote",
        "url": "https://example.com/jobs/demo-software",
    },
    {
        "id": "demo-data",
        "title": "Data Analyst",
        "description": "Use SQL and Python to analyze datasets and communicate insights.",
        "company": "Sample Analytics",
        "location": "New York",
        "url": "https://example.com/jobs/demo-data",
    },
]


def search_jobs(profile: dict, preferences: dict) -> list[dict]:
    """Search Adzuna and return normalized job dictionaries.

    Each result has: id, title, description, company, location, url.
    """
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        if os.getenv("JOB_SEARCH_DEMO", "1").lower() in {"1", "true", "yes"}:
            return DEMO_JOBS.copy()
        raise RuntimeError("Set ADZUNA_APP_ID and ADZUNA_APP_KEY in your .env file.")

    # Prefer the user's chosen role; fall back to Sheyar's resume schema.
    role = str(preferences.get("role") or "").strip()
    if not role:
        candidate = profile.get("candidate_profile") or {}
        if isinstance(candidate, dict):
            role = str(candidate.get("primary_domain") or "").strip()
    if not role:
        role = "Software Engineer"

    location = str(preferences.get("location") or "").strip()
    country = (os.getenv("ADZUNA_COUNTRY") or "us").strip().lower()
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": role,
        "results_per_page": 20,
    }
    if location:
        params["where"] = location

    try:
        response = requests.get(url, params=params, timeout=15)
    except requests.Timeout:
        raise JobSearchError("Adzuna request timed out.") from None
    except requests.RequestException:
        raise JobSearchError("Could not connect to Adzuna.") from None

    # Avoid raise_for_status(): its error message can include the API key in the URL.
    if not 200 <= response.status_code < 300:
        raise JobSearchError(f"Adzuna API returned HTTP {response.status_code}.")

    try:
        data = response.json()
    except ValueError:
        raise JobSearchError("Adzuna returned invalid JSON.") from None

    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise JobSearchError("Adzuna response is missing a results list.")

    jobs = []
    for item in data["results"]:
        if not isinstance(item, dict) or not item.get("title"):
            continue

        company = item.get("company") or {}
        job_location = item.get("location") or {}
        jobs.append({
            "id": str(item.get("id") or ""),
            "title": item["title"],
            "description": item.get("description") or "",
            "company": company.get("display_name", "") if isinstance(company, dict) else "",
            "location": job_location.get("display_name", "") if isinstance(job_location, dict) else "",
            "url": item.get("redirect_url") or "",
        })

    return jobs
