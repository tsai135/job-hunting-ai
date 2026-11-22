# Ho Gia Bao Le

from flask import Flask, request, jsonify
from pathlib import Path
import chromadb
import os
from dotenv import load_dotenv
import json
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


# Load environment variables.
load_dotenv()

# Set the path to the Chroma database.
# Based on the current environment.
CHROMA_PATH_LOCAL = Path(__file__).parent.resolve() / "chroma_jobs"
CHROMA_PATH = os.getenv("CHROMA_PATH_VM", str(CHROMA_PATH_LOCAL))


# Embedding function.
embedding_function = DefaultEmbeddingFunction()


# Create the Chroma client and collection.
client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = client.get_or_create_collection(
    name="job_postings",
    metadata={"hnsw:space": "cosine"}
)


# Initialize the Flask application.
app = Flask(__name__)


# ========================================
# Calculate the scores.
# ========================================

def calculate_skill_score(job_skills: list, resume_skills: list) -> float:
    """
    Calculate the skill score based on the overlap between job skills and resume skills.
    """

    # Validate input types.
    if not isinstance(job_skills, list) or not isinstance(resume_skills, list):
        return 0.0

    # Normalize skills into sets.
    job_skills = {
        skill.lower().strip() for skill in job_skills if isinstance(skill, str)
    }
    resume_skills = {
        skill.lower().strip() for skill in resume_skills if isinstance(skill, str)
    }

    # Count the overlap.
    overlap_count = len(resume_skills & job_skills)

    # If there are no required job skills, -1.
    if not job_skills:
        return -1.0
    
    # Else, calculate the score as the ratio of overlap to job skills.
    return overlap_count / len(job_skills)


def calculate_semantic_score(distance: float) -> float:
    """
    Calculate the semantic score based on the semantic similarity.
    """
    return max(0, 1 - distance)


def calculate_final_score(skill_score:float, semantic_score:float) -> float:
    """
    Calculate the final score based on skill score and semantic score.
    final_score = skill_score * 0.4 + semantic_score * 0.6
    """

    # Validate input types.
    if (
        not isinstance(skill_score, (int, float)) 
        or not isinstance(semantic_score, (int, float))
    ):
        return 0.0

    # Validate semantic score range.
    if not 0 <= semantic_score <= 1:
        return 0.0

    # If no required job skills, return semantic score only.
    if skill_score == -1.0:
        return semantic_score
    
    # Validate skill score range.
    if not (0 <= skill_score <= 1):
        return 0.0

    # Calculate the final score as the average of skill and semantic scores.
    return (skill_score * 0.4 + semantic_score * 0.6)


# ========================================
# Prepare job postings and embeddings.
# ========================================

def prepare_job_text(job_posting: dict) -> str:
    """
    Prepare job postings for semantic search.
    """

    requirements = job_posting.get("requirements") or {}
    job_skills = requirements.get("job_skills") or []

    # Merge all fields into a single string.
    job_text = (
        "Title: " + job_posting.get("title", "") + "\n"
        "Description: " + job_posting.get("description", "") + "\n"
        "Company: " + job_posting.get("company", "") + "\n"
        "Location: " + job_posting.get("location", "") + "\n"
        "Requirements: " + ", ".join(job_skills) + "\n"
    )

    return job_text


def embed_job_postings(job_postings: list) -> None:
    """
    Embed job postings into the Chroma database.
    """

    # Variables for batch processing.
    job_ids = []
    job_texts = []
    job_metadatas = []

    # Prepare the job data.
    for job_posting in job_postings:
        job_id = job_posting.get("id")

        # Skip if no job_id.
        if not job_id:
            continue  

        # Fill the job data.
        # The full job data is dumped as a json string into metadata for storage.
        job_ids.append(str(job_id))
        job_texts.append(prepare_job_text(job_posting))
        job_metadatas.append({
            "job_data": json.dumps(job_posting)
        })

    # Upsert to the collection.
    collection.upsert(
        ids=job_ids,
        documents=job_texts,
        metadatas=job_metadatas
    )


# ========================================
# Job matching.
# ========================================


def match_resume_with_jobs(resume_vector, resume_skills, job_ids):
    """
    Rank only the jobs supplied for the current search.

    Jobs remain stored persistently in ChromaDB.
    """

    # Retrieve stored embeddings for the current search's jobs.
    stored = collection.get(
        ids=job_ids,
        include=["embeddings", "metadatas"]
    )

    embeddings = stored["embeddings"]
    metadatas = stored["metadatas"]

    if embeddings is None or len(embeddings) == 0:
        return []

    ranked_jobs = []

    import numpy as np

    resume_array = np.asarray(resume_vector, dtype=float)
    resume_norm = np.linalg.norm(resume_array)

    for embedding, metadata in zip(embeddings, metadatas):
        job_posting = json.loads(metadata["job_data"])

        if not isinstance(job_posting, dict):
            continue

        job_array = np.asarray(embedding, dtype=float)
        job_norm = np.linalg.norm(job_array)

        # Cosine similarity, clamped to [0, 1].
        if resume_norm == 0 or job_norm == 0:
            semantic_score = 0.0
        else:
            cosine_similarity = float(
                np.dot(resume_array, job_array)
                / (resume_norm * job_norm)
            )
            semantic_score = max(0.0, min(1.0, cosine_similarity))

        requirements = job_posting.get("requirements") or {}
        job_skills = requirements.get("job_skills") or []

        skill_score = calculate_skill_score(
            job_skills,
            resume_skills
        )

        final_score = calculate_final_score(
            skill_score,
            semantic_score
        )

        ranked_jobs.append({
            "job_posting": job_posting,
            "skill_score": skill_score,
            "semantic_score": semantic_score,
            "final_score": final_score
        })

    ranked_jobs.sort(
        key=lambda x: x["final_score"],
        reverse=True
    )

    return ranked_jobs[:5]



# ========================================
# Resume JSON Processing.
# ========================================

def extract_resume_skills(resume):
    """
    Extracts skills from a resume json object.
    """

    resume_skills = []
    if not resume:
        return resume_skills

    # Extract skills from the resume.
    core_competencies = resume.get("core_competencies", {})

    if not core_competencies:
        return resume_skills

    technical_skills = core_competencies.get("technical_skills", [])
    domain_knowledge = core_competencies.get("domain_knowledge", [])
    tools_and_frameworks = core_competencies.get("tools_and_frameworks", [])

    # Append the extracted skills to the skills list.
    resume_skills.extend(technical_skills)
    resume_skills.extend(domain_knowledge)
    resume_skills.extend(tools_and_frameworks)

    # Remove duplicates by converting the list to a set and back to a list.
    resume_skills = list(set(resume_skills))

    return resume_skills 


def prepare_resume_text(resume):
    """
    Prepare a candidate profile text for embedding.
    """

    candidate_profile = resume.get("candidate_profile", {})
    core_competencies = resume.get("core_competencies", {})
    experiences = resume.get("professional_experience", [])
    projects = resume.get("academic_and_project_portfolio", [])

    full_experience_texts = []
    for experience in experiences:
        experience_doc = (
            "Title: " + experience.get("title", "") +
            ", Organization: " + experience.get("organization", "") +
            ", Duration: " + experience.get("duration", "") +
            ", Responsibilities: " + ", ".join(experience.get("responsibilities", []))
        )
        full_experience_texts.append(experience_doc)

    full_project_texts = []
    for project in projects:
        project_doc = (
            "Title: " + project.get("title", "") +
            ", Type: " + project.get("type", "") +
            ", Description: " + project.get("description", "")
        )
        full_project_texts.append(project_doc)


    resume_text = (
        "Seniority: " + candidate_profile.get("inferred_seniority", "") +
        ", Domain: " + candidate_profile.get("primary_domain", "") +
        ", Career Trajectory: " + candidate_profile.get("career_trajectory", "") +
        ", Summary: " + resume.get("executive_summary", "") +
        ", Technical Skills: " + ", ".join(core_competencies.get("technical_skills", [])) +
        ", Domain Knowledge: " + ", ".join(core_competencies.get("domain_knowledge", [])) +
        ", Tools and Frameworks: " + ", ".join(core_competencies.get("tools_and_frameworks", [])) +
        ", Experience: " + ", ".join(full_experience_texts) +
        ", Projects: " + ", ".join(full_project_texts)
    )

    return resume_text


# ========================================
# Flask endpoints.
# ========================================

# The index page.
@app.route("/", methods=["GET"])
def index():
    return (
        "Welcome to the Job Match Microservice!\n"
        "By Ho Gia Bao Le\n"
    )


# Add and embed new job postings to the ChromaDB.
@app.route("/jobs", methods=["POST"])
def add_job_postings():
    job_postings = request.get_json(silent=True)

    # 400 Bad Request.
    if not job_postings or not isinstance(job_postings, list):
        return jsonify({"error": "Expected a list of job postings."}), 400

    if not all(isinstance(job, dict) for job in job_postings):
        return jsonify({"error": "Expected each job posting to be a dictionary."}), 400

    # 200 OK.
    embed_job_postings(job_postings)
    return jsonify({"message": "Job postings processed successfully."}), 200


# Match and rank job postings based on the resume json.

@app.route("/resume", methods=["POST"])
def match_resume_json():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({"error": "Expected a JSON object."}), 400

    resume = payload.get("resume")
    job_ids = payload.get("job_ids")

    if not isinstance(resume, dict):
        return jsonify({"error": "Expected a resume dictionary."}), 400

    if (
        not isinstance(job_ids, list)
        or not job_ids
        or not all(isinstance(job_id, str) and job_id for job_id in job_ids)
    ):
        return jsonify({"error": "Expected a nonempty list of job IDs."}), 400

    if collection.count() == 0:
        return jsonify({"error": "No jobs are stored."}), 404

    resume_skills = extract_resume_skills(resume)
    resume_text = prepare_resume_text(resume)
    resume_vector = embedding_function([resume_text])[0].tolist()

    ranked_jobs = match_resume_with_jobs(
        resume_vector,
        resume_skills,
        job_ids
    )

    return jsonify(ranked_jobs), 200



if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=3117)
