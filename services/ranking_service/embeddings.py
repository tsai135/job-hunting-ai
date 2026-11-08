import chromadb
from pathlib import Path


CHROMADB_PATH = Path(__file__).resolve().parent / "chromadb_jobs"


def prepare_job_document(job):
    """
    Prepare one job text for embedding.
    """

    requirements = job.get("requirements", {})

    job_doc = (
        "Title: " + job.get("title", "") +
        ", Description: " + job.get("description", "") +
        ", Company: " + job.get("company", "") +
        ", Location: " + job.get("location", "") +
        ", Minimum Experience: " + str(requirements.get("minimum_experience_years", "")) + " years" +
        ", Education: " + requirements.get("education_requirement", "") +
        ", Seniority: " + requirements.get("seniority", "") +
        ", Required Skills: " + 
        ", ".join(requirements.get("required_skills", [])) +
        ", Preferred Skills: " + 
        ", ".join(requirements.get("preferred_skills", []))
    )

    return job_doc


def get_job_collection():
    """
    Get or create a ChromaDB collection for job postings.
    """

    # Create a persistent ChromaDB client.
    client = chromadb.PersistentClient(path=str(CHROMADB_PATH))

    # Create or reuse the collection for job postings.
    collection = client.get_or_create_collection(
        name="job_postings",
        configuration={"hnsw": {"space": "cosine"}}
    )

    return collection


def embed_jobs(jobs, search_id):
    """
    Embed job postings into the ChromaDB collection.
    """

    if not jobs:
        return

    collection = get_job_collection()

    # Prepare the job documents for embedding.
    job_ids = [
        search_id + "_" + job["id"] 
        for job in jobs
    ]

    job_documents = [
        prepare_job_document(job)
        for job in jobs
    ]

    job_metadatas = [
        {
            "title": job["title"],
            "search_id": search_id,
            "job_id": job["id"]
        }
        for job in jobs
    ]

    # Add new jobs or update existing jobs.
    collection.upsert(
        ids=job_ids,
        documents=job_documents,
        metadatas=job_metadatas
    )


def prepare_resume_document(profile):
    """
    Prepare a candidate profile text for embedding.
    """

    candidate_profile = profile.get("candidate_profile", {})
    core_competencies = profile.get("core_competencies", {})
    experiences = profile.get("professional_experience", [])
    projects = profile.get("academic_and_project_portfolio", [])

    full_experience_docs = []
    for experience in experiences:
        experience_doc = (
            "Title: " + experience.get("title", "") +
            ", Organization: " + experience.get("organization", "") +
            ", Duration: " + experience.get("duration", "") +
            ", Responsibilities: " + ", ".join(experience.get("responsibilities", []))
        )
        full_experience_docs.append(experience_doc)

    full_project_docs = []
    for project in projects:
        project_doc = (
            "Title: " + project.get("title", "") +
            ", Type: " + project.get("type", "") +
            ", Description: " + project.get("description", "")
        )
        full_project_docs.append(project_doc)


    resume_doc = (
        "Seniority: " + candidate_profile.get("inferred_seniority", "") +
        ", Domain: " + candidate_profile.get("primary_domain", "") +
        ", Career Trajectory: " + candidate_profile.get("career_trajectory", "") +
        ", Summary: " + profile.get("executive_summary", "") +
        ", Technical Skills: " + ", ".join(core_competencies.get("technical_skills", [])) +
        ", Domain Knowledge: " + ", ".join(core_competencies.get("domain_knowledge", [])) +
        ", Tools and Frameworks: " + ", ".join(core_competencies.get("tools_and_frameworks", [])) +
        ", Experience: " + ", ".join(full_experience_docs) +
        ", Projects: " + ", ".join(full_project_docs)
    )

    return resume_doc


def get_semantic_similarity(profile, jobs, search_id):
    """
    Get the semantic similarity scores between a profile and a list of job postings.
    """

    if not jobs or not profile or not search_id:
        return []

    # Get or create the ChromaDB collection for job postings.
    collection = get_job_collection()

    # Prepare the candidate profile for embedding.
    resume_doc = prepare_resume_document(profile)

    # Retrieve the all jobs.
    results = collection.query(
        query_texts=[resume_doc],
        where={"search_id": search_id},
        n_results=len(jobs),
        include=["distances"]
    )

    # Create a dictionary for looking up jobs by ChromaDB IDs.
    jobs_by_id = {
        search_id + "_" + job["id"]: job
        for job in jobs
    }

    # Process the results.
    job_with_semantic_score = []

    for i, job_id in enumerate(results["ids"][0]):

        # Lower cosine distance means greater similarity.
        distance = results["distances"][0][i]

        # Convert cosine distance into a similarity score.
        score = max(0, 1 - distance)

        # Find the corresponding job from the supplied list.
        job = jobs_by_id.get(job_id)

        if job:
            job_with_semantic_score.append({
                "job": job,
                "score": score
            })

    return job_with_semantic_score
