
from services.seniority import (
    infer_job_seniority,
    adjust_seniority,
)

jobs = [
    {
        "id": "1",
        "title": "Embedded Software Engineer",
        "description": (
            "Requires 7+ years of experience, "
            "technical leadership and system architecture."
        ),
    },
    {
        "id": "2",
        "title": "Firmware Engineer",
        "description": (
            "Recent graduates welcome. "
            "0-2 years of experience preferred."
        ),
    },
    {
        "id": "3",
        "title": "Software Engineer II",
        "description": (
            "Requires 3-5 years of professional "
            "software development experience."
        ),
    },
]

classified = infer_job_seniority(jobs)

for job in classified:
    print(job["title"], "=>", job["seniority"])
