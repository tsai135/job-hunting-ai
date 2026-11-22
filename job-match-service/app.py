# Ho Gia Bao Le

# Standard libraries.
import uuid
import json

# Third-party libraries.
import chromadb
from flask import Flask, request, jsonify
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


# Embedding function.
embedding_function = DefaultEmbeddingFunction()


# Create the in-memory Chroma client.
client = chromadb.EphemeralClient()


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


def embed_job_postings(job_postings: list, collection) -> None:
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
    if job_ids:
        collection.upsert(
            ids=job_ids,
            documents=job_texts,
            metadatas=job_metadatas
        )


# ========================================
# Job matching.
# ========================================

def match_resume_with_jobs(resume_vector, resume_skills, collection):
    """
    Matches a resume with job postings.
    """

    # Query the Chroma DB.
    results = collection.query(
        query_embeddings=[resume_vector],
        n_results=collection.count(),
        include=["distances", "metadatas"]
    )

    # Process the results.
    ranked_jobs = []

    for i in range(len(results["ids"][0])):

        # Lower cosine distance means greater similarity.
        distance = results["distances"][0][i]

        # Get and the job posting object.
        job_data = results["metadatas"][0][i]["job_data"]
        job_posting = json.loads(job_data)

        if not isinstance(job_posting, dict):
            continue

        requirements = job_posting.get("requirements") or {}
        job_skills = requirements.get("job_skills") or []
        
        # Calculate the scores
        skill_score = calculate_skill_score(job_skills, resume_skills)
        semantic_score = calculate_semantic_score(distance)
        final_score = calculate_final_score(skill_score, semantic_score)

        ranked_jobs.append({
            "job_posting": job_posting,
            "skill_score": skill_score,
            "semantic_score": semantic_score,
            "final_score": final_score
        })

    # Sort the jobs by final score in descending order.
    ranked_jobs.sort(
        key=lambda x: x["final_score"], 
        reverse=True
    )

    return ranked_jobs[:20]



# ========================================
# Resume JSON Processing.
# ========================================

def extract_resume_skills(resume):
    """
    Extracts unique skills from a resume JSON object.
    """
    if not resume:
        return []

    core_competencies = resume.get("core_competencies", {})

    if not core_competencies:
        return []

    # Extract skills from all categories.
    resume_skills = [
        skill
        for category in ["technical_skills", "domain_knowledge", "tools_and_frameworks"]
        for skill in core_competencies.get(category, [])
    ]

    # Remove duplicates while preserving the original order.
    return list(dict.fromkeys(resume_skills)) 


def prepare_resume_text(resume):
    """
    Prepare a candidate profile text for embedding.
    """
    candidate_profile = resume.get("candidate_profile", {})
    core_competencies = resume.get("core_competencies", {})
    experiences = resume.get("professional_experience", [])
    projects = resume.get("academic_and_project_portfolio", [])

    # Prepare professional experience descriptions.
    full_experience_texts = [
        f"Title: {experience.get('title', '')}, "
        f"Organization: {experience.get('organization', '')}, "
        f"Duration: {experience.get('duration', '')}, "
        f"Responsibilities: {', '.join(experience.get('responsibilities', []))}"
        for experience in experiences
    ]

    # Prepare project descriptions.
    full_project_texts = [
        f"Title: {project.get('title', '')}, "
        f"Type: {project.get('type', '')}, "
        f"Description: {project.get('description', '')}"
        for project in projects
    ]

    # Combine resume information into a single text string.
    resume_text = (
        f"Seniority: {candidate_profile.get('inferred_seniority', '')}, "
        f"Domain: {candidate_profile.get('primary_domain', '')}, "
        f"Career Trajectory: {candidate_profile.get('career_trajectory', '')}, "
        f"Summary: {resume.get('executive_summary', '')}, "
        f"Technical Skills: {', '.join(core_competencies.get('technical_skills', []))}, "
        f"Domain Knowledge: {', '.join(core_competencies.get('domain_knowledge', []))}, "
        f"Tools and Frameworks: {', '.join(core_competencies.get('tools_and_frameworks', []))}, "
        f"Experience: {', '.join(full_experience_texts)}, "
        f"Projects: {', '.join(full_project_texts)}"
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


# Match and rank job postings based on the resume json.
@app.route("/match", methods=["POST"])
def match_resume_json():
    data = request.get_json(silent=True)

    # 400 Bad Request. Invalid data
    if not isinstance(data, dict):
        return jsonify({"error": "Expected a dictionary."}), 400

    resume = data.get("resume")
    job_postings = data.get("jobs")

    # 400 Bad Request. Validate the resume and job data.
    if not isinstance(resume, dict):
        return jsonify({"error": "Expected resume to be a dictionary."}), 400

    if not isinstance(job_postings, list) or not job_postings:
        return jsonify({"error": "Expected a non-empty list of job postings."}), 400

    if not all(isinstance(job, dict) for job in job_postings):
        return jsonify({"error": "Expected each job posting to be a dictionary."}), 400

    # Create a unique collection for each request.
    collection_name = f"jobs_{uuid.uuid4().hex}"
    collection = None

    try:
        collection = client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=embedding_function
        )

        # Embed the job postings.
        embed_job_postings(job_postings, collection)

        # 400 Bad Request. No job postings.
        if collection.count() == 0:
            return jsonify({"error": "No valid job postings to process."}), 400

        # Extract the resume skills.
        resume_skills = extract_resume_skills(resume)
        
        # Extract the resume vector.
        resume_text = prepare_resume_text(resume)
        resume_vector = embedding_function([resume_text])[0].tolist()

        # Return the results.
        ranked_jobs = match_resume_with_jobs(
            resume_vector, 
            resume_skills,
            collection
        )

        # 200 OK.
        return jsonify(ranked_jobs), 200

    # Delete the collection after each search.
    finally:
        if collection is not None:
            client.delete_collection(name=collection_name)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=3117)
