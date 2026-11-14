# Job Match Microservice

## 1. Overview

Flask API for job matching using ChromaDB embeddings and skill scoring.

## 2. Running the Service

```bash
python app.py
```

URL: `http://127.0.0.1:3117`

## 3. API Endpoints

### POST `/jobs`

Adds job postings to ChromaDB.

**Request:**

```json
[
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
```

**Successful response (200):**

```json
{
    "message": "Job postings processed successfully."
}
```

### POST `/resume`

Receives a parsed resume and returns the top 10 matching job postings, ranked by final score.

**Request:**

```json
{
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
}
```

**Successful response (200):**

```json
[
    {
        "job_posting": {
            "...": "Full original job posting"
        },
        "final_score": 0.85
    }
]
```

## 4. Testing

With the Flask service running, open another terminal:

```bash
python test_jobs.py
```

Adds five sample job postings through `POST /jobs`. Repeated runs update the same records.

## 5. Database Reset

Stop the Flask service and delete the `chroma_jobs` folder to reset the database.