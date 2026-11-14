# Integration of the job matching service
# Use sample resume if a resume is not given.

import requests

MATCH_URL = "http://127.0.0.1:3117/resume"

sample_resume = {
    "candidate_profile": {
        "inferred_seniority": "Junior",
        "primary_domain": "Software Development",
        "career_trajectory": "Backend Development"
    },
    "executive_summary": "Aspiring software developer with experience in Python and JavaScript.",
    "core_competencies": {
        "technical_skills": ["Python", "JavaScript", "C++", "SQL"],
        "domain_knowledge": ["Software Development", "Database Management"],
        "tools_and_frameworks": ["Flask", "React", "Git", "Docker"]
    },
    "professional_experience": [],
    "academic_and_project_portfolio": [
        {
            "title": "Job Hunting AI",
            "type": "Software Project",
            "description": "Developed a web application for resume and job matching."
        }
    ]
}

def rank_jobs(resume=sample_resume):
    """
    Return 5 jobs with the highest matching score.
    """
    response = requests.post(MATCH_URL, json=resume)
    return response.json()

if __name__ == "__main__":
    result = rank_jobs()
    for job in result:
        print(job["job_posting"])
        print(job["final_score"])
