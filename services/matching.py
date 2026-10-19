
def rank_jobs(profile: dict, jobs: list[dict]) -> list[dict]:
    """Bao: rank jobs against a candidate profile.

    MVP toy algorithm: percentage of candidate skills mentioned in each
    job description. This is NOT a real job-fit score or AI model.
    """
    skills = [skill.lower() for skill in profile.get("skills", [])]
    matches = []

    for job in jobs:
        description = job["description"].lower()
        found = sum(skill in description for skill in skills)
        score = round(100 * found / len(skills)) if skills else 0
        matches.append({"job": job, "score": score})

    return sorted(matches, key=lambda match: match["score"], reverse=True)
