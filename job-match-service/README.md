# Job Match Microservice

## 1. Overview

Flask API for matching resumes with job postings using ChromaDB embeddings and skill scoring.

The service receives a resume and a list of job postings, then returns the top 5 matching jobs.

## 2. Running the Service

```bash
python app.py
```

URL: `http://127.0.0.1:3117`

## 3. API Endpoints

### POST `/match`

Receives a parsed resume and a list of job postings, then returns the top 5 matching jobs ranked by final score.

**Request:**

```json
{
    "resume": {
        "candidate_profile": {
            "inferred_seniority": "Junior",
            "primary_domain": "Software Development",
            "career_trajectory": "Backend Development"
        },
        "executive_summary": "Aspiring software developer.",
        "core_competencies": {
            "technical_skills": ["Python", "JavaScript"],
            "domain_knowledge": ["Software Development"],
            "tools_and_frameworks": ["Flask", "Git"]
        },
        "professional_experience": [],
        "academic_and_project_portfolio": []
    },
    "jobs": [
        {
            "id": "job-001",
            "title": "Python Developer",
            "description": "Develop backend applications using Python and Flask.",
            "company": "Tech Company",
            "location": "Remote",
            "requirements": {
                "job_skills": ["Python", "Flask", "SQL"]
            }
        }
    ]
}
```

**Successful response (200):**

```json
[
    {
        "job_posting": {
            "...": "Full original job posting"
        },
        "skill_score": 0.67,
        "semantic_score": 0.85,
        "final_score": 0.778
    }
]
```

## 4. Testing

With the Flask service running, open another terminal:

```bash
python test_match.py
```

Sends a sample resume and job postings through `POST /match` and displays the matching results.

## 5. Storage

Uses an in-memory ChromaDB collection created for each request. The collection is deleted after matching is complete. Job postings are not stored persistently.