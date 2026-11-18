"""
Test script for matching a sample resume with job postings.
Make sure the Flask microservice is running before executing this script.
"""

import requests


URL = "http://127.0.0.1:3117/match"


# Sample resume.
resume = {
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


# Sample job postings.
jobs = [
    {
        "id": "test-job-001",
        "title": "Junior Python Developer",
        "description": (
            "Develop and maintain backend applications using Python and Flask. "
            "Work with REST APIs and relational databases."
        ),
        "company": "Tech Solutions",
        "location": "San Francisco, CA",
        "requirements": {
            "job_skills": ["Python", "Flask", "SQL", "REST APIs"]
        }
    },
    {
        "id": "test-job-002",
        "title": "Frontend Developer",
        "description": (
            "Build responsive web applications and user interfaces. "
            "Collaborate with designers and backend developers."
        ),
        "company": "WebWorks",
        "location": "Remote",
        "requirements": {
            "job_skills": ["JavaScript", "React", "HTML", "CSS"]
        }
    },
    {
        "id": "test-job-003",
        "title": "Software Engineer",
        "description": (
            "Develop software applications, write maintainable code, "
            "and participate in code reviews."
        ),
        "company": "Innovate Inc.",
        "location": "Seattle, WA"
    },
    {
        "id": "test-job-004",
        "title": "Machine Learning Engineer",
        "description": (
            "Build machine learning pipelines and develop data-driven "
            "solutions using Python and machine learning frameworks."
        ),
        "company": "AI Labs",
        "location": "New York, NY",
        "requirements": {
            "job_skills": ["Python", "Machine Learning", "TensorFlow", "SQL"]
        }
    },
    {
        "id": "test-job-005",
        "title": "Backend Developer",
        "description": (
            "Design and implement backend services using Python, "
            "databases, and RESTful APIs."
        ),
        "company": "Cloud Systems",
        "location": "Austin, TX",
        "requirements": {
            "job_skills": []
        }
    }
]


# Prepare the request data.
data = {
    "resume": resume,
    "jobs": jobs
}

# Send the request to the microservice.
try:
    response = requests.post(URL, json=data)
    response.raise_for_status()

    results = response.json()

    # Print the ranked job results.
    print("\n========== Job Matching Results ==========")

    for index, result in enumerate(results, start=1):
        job = result["job_posting"]

        print(f"\nRank #{index}: {job.get('title', 'N/A')}")
        print(f"Company:         {job.get('company', 'N/A')}")
        print(f"Location:        {job.get('location', 'N/A')}")
        print(f"URL:             {job.get('url', 'N/A')}")
        print(f"Skill Score:     {result['skill_score']:.2f}")
        print(f"Semantic Score:  {result['semantic_score']:.2f}")
        print(f"Final Score:     {result['final_score']:.2f}")

    print("\n==========================================")

except requests.exceptions.ConnectionError:
    print("Could not connect to the Flask microservice.")
    print("Make sure the application is running.")

except requests.exceptions.HTTPError as error:
    print("Request failed:", error)
    print(response.text)
