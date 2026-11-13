
from services.job_data import search_jobs
from services.matching import rank_jobs

# Simulated resume profile matching our original skeleton
profile = {
    "skills": ["Python", "SQL", "Flask"],
    "experience_years": 2
}

preferences = {
    "role": "Software Engineer",
    "location": "New York"
}

# Step 1: Retrieve real jobs
jobs = search_jobs(profile, preferences)
print(f"Retrieved {len(jobs)} real jobs")

# Step 2: Pass them into the matching module
matches = rank_jobs(profile, jobs)
print(f"Ranked {len(matches)} jobs")

# Step 3: Inspect results
for match in matches[:5]:
    print(
        match["job"]["title"],
        "- Score:",
        match["score"]
    )
