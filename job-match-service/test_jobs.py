"""
Test script for adding sample job postings to ChromaDB.
Make sure the Flask microservice is running before executing this script.
Simply delete the chroma_jobs folder to reset.
"""

import requests


URL = "http://127.0.0.1:3117/jobs"


# Sample job postings.
job_postings = [
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


# Send the job postings to the microservice.
try:
    response = requests.post(URL, json=job_postings)

    print("Status Code:", response.status_code)
    print("Response:", response.json())

except requests.exceptions.ConnectionError:
    print("Could not connect to the Flask microservice.")
    print("Make sure the application is running.")
