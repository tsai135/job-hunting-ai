
import chromadb
from pathlib import Path


CHROMADB_PATH = Path(__file__).resolve().parent / "chromadb_jobs"


def rank_jobs(profile: dict, jobs: list[dict]) -> list[dict]:
    """
    Rank job postings based on a candidate's profile using
    ChromaDB semantic similarity search.
    """

    # Create a persistent ChromaDB client.
    client = chromadb.PersistentClient(path=str(CHROMADB_PATH))

    # Create or reuse the collection for job postings.
    collection = client.get_or_create_collection(
        name="job_postings",
        configuration={"hnsw": {"space": "cosine"}}
    )

    # Prepare the job documents for embedding.
    job_ids = [job["id"] for job in jobs]

    job_documents = [
        "Title: " + job["title"] +
        ", Description: " + job["description"]
        for job in jobs
    ]

    job_metadatas = [
        {"title": job["title"]}
        for job in jobs
    ]

    # Add new jobs or update existing jobs.
    collection.upsert(
        ids=job_ids,
        documents=job_documents,
        metadatas=job_metadatas
    )

    # Prepare the candidate profile for embedding.
    resume_text = (
        "Skills: " + ", ".join(profile.get("skills", [])) +
        ", Experience: " +
        str(profile.get("experience_years", 0)) + " years"
    )

    # Retrieve the five closest jobs, or fewer if the collection is smaller.
    results = collection.query(
        query_texts=[resume_text],
        n_results=min(5, collection.count()),
        include=["distances"]
    )

    # Process the results.
    ranked_jobs = []

    for i, job_id in enumerate(results["ids"][0]):

        # Lower cosine distance means greater similarity.
        distance = results["distances"][0][i]

        # Convert cosine distance into a similarity score out of 100.
        score = (1 - distance) * 100

        # Find the corresponding job from the supplied list.
        job = next(
            (job for job in jobs if job["id"] == job_id),
            None
        )

        if job:
            ranked_jobs.append({
                "job": job,
                "score": score
            })

    # Sort from highest score to lowest score.
    ranked_jobs.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return ranked_jobs


if __name__ == "__main__":
    profile = {
        "skills": ["Python", "CSS"],
        "experience_years": 2
    }

    jobs = [
        {
            "id": "job001",
            "title": "Python Developer",
            "description": "Build backend APIs using Python and SQL."
        },
        {
            "id": "job002",
            "title": "Data Analyst",
            "description": "Analyze datasets using SQL and Excel."
        },
        {
            "id": "job003",
            "title": "Frontend Developer",
            "description": "Build websites using HTML, CSS, and JavaScript."
        }
    ]

    ranked_jobs = rank_jobs(profile, jobs)

    for rank, item in enumerate(ranked_jobs, start=1):
        print(
            f"Rank: {rank}\n"
            f"Job ID: {item['job']['id']}\n"
            f"Title: {item['job']['title']}\n"
            f"Similarity Score: {item['score']:.2f}/100\n"
        )
