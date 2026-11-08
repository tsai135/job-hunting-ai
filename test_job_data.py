
"""Live smoke test: run `python3 test_job_data.py` from the project root."""

from services.job_data import JobSearchError, search_jobs


def main() -> int:
    # Sample inputs matching the interface used by app.py.
    profile = {
        "candidate_profile": {"primary_domain": "Software Engineering"}
    }
    preferences = {"role": "Python Developer", "location": "New York"}

    try:
        jobs = search_jobs(profile, preferences)
    except (JobSearchError, RuntimeError) as exc:
        print(f"Job search failed: {exc}")
        return 1

    print(f"API call succeeded. Found {len(jobs)} jobs.\n")
    if not jobs:
        print("No matching postings. Try a broader role or location.")

    required_fields = {"id", "title", "description", "company", "location", "url"}
    for job in jobs[:5]:
        assert required_fields.issubset(job), "Job result has missing fields"
        print(f"Title:    {job['title']}")
        print(f"Company:  {job['company']}")
        print(f"Location: {job['location']}")
        print(f"URL:      {job['url']}")
        print("-" * 50)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
