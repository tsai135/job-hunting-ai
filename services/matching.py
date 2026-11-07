import uuid

from services.ranking_service.embeddings import (
    embed_jobs,
    get_semantic_similarity
)

from services.ranking_service.scoring import (
    calculate_skill_score,
    calculate_final_score
)

from services.ranking_service.text_extractor import (
    extract_resume_skills,
    extract_job_requirements
)

def rank_jobs(profile: dict, jobs: list[dict]) -> list[dict]:
    """
    Rank job postings based on semantic similarity and skill matching.
    """

    # Handle empty inputs.
    if not profile or not jobs:
        return []

    # Extract skills from the candidate profile and job postings.
    resume_skills = extract_resume_skills(profile)

    # Generate a unique search ID.
    search_id = str(uuid.uuid4())

    # Embed the job postings.
    embed_jobs(jobs, search_id)

    # Get the semantic similarity scores.
    semantic_results = get_semantic_similarity(profile, jobs, search_id)

    # The final ranked jobs list.
    ranked_jobs = []

    for result in semantic_results:
        job = result.get("job")
        semantic_score = result.get("score", 0.0)

        # Extract job requirements.
        job_requirements = extract_job_requirements(job)

        # Calculate the skill score.
        skill_score = calculate_skill_score(resume_skills, job_requirements)

        # Calculate the final score.
        final_score = calculate_final_score(semantic_score, skill_score)

        ranked_jobs.append({
            "job": job,
            "semantic_score": semantic_score,
            "skill_score": skill_score,
            "final_score": final_score
        })
        
    # Sort the jobs by final score in descending order.
    ranked_jobs.sort(
        key=lambda x: x["final_score"], 
        reverse=True
    )

    return ranked_jobs


# Test the ranking pipeline with sample data.
# In the terminal, run python -m services.matching
if __name__ == "__main__":

    import json
    from pathlib import Path

    # Locate the sample JSON files.
    data_path = Path(__file__).resolve().parent / "ranking_service" / "data"

    resume_path = data_path / "sample_resume.json"
    jobs_path = data_path / "sample_jobs.json"

    # Load sample resume.
    with open(resume_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    # Load sample job postings.
    with open(jobs_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    print("Testing job matching pipeline...\n")

    # Run the complete matching pipeline.
    ranked_jobs = rank_jobs(profile, jobs)

    # Display ranking results.
    print(f"Number of jobs ranked: {len(ranked_jobs)}\n")

    for index, result in enumerate(ranked_jobs, start=1):
        job = result["job"]

        print(f"Rank #{index}: {job.get('title', 'Unknown')}")
        print(f"Company: {job.get('company', 'Unknown')}")
        print(f"Semantic Score: {result['semantic_score']:.4f}")
        print(f"Skill Score: {result['skill_score']:.4f}")
        print(f"Final Score: {result['final_score']:.4f}")
        print("-" * 40)

    # Test whether results are sorted by final score.
    for i in range(len(ranked_jobs) - 1):
        assert ranked_jobs[i]["final_score"] >= ranked_jobs[i + 1]["final_score"]

    print("PASS: Jobs are sorted by final score.")

    # Test empty input handling.
    assert rank_jobs({}, jobs) == []
    assert rank_jobs(profile, []) == []

    print("PASS: Empty input tests.")

    print("\nAll matching pipeline tests completed.")
    