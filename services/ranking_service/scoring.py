def calculate_skill_score(resume_skills, job_requirements):
    """
    Calculate the skill score based on the overlap between resume skills and job requirements.
    The score is calculated as a weighted sum of the number of matching preferred and required skills.
    Score = (Preferred * 0.2) + (Required * 0.8)
    """

    # Validate input types.
    if not isinstance(resume_skills, list):
        return 0.0

    if not isinstance(job_requirements, dict):
        return 0.0

    # Extract the preferred and required skills.
    preferred_skills = job_requirements.get("preferred_skills", [])
    required_skills = job_requirements.get("required_skills", [])

    # Normalize the preferred and required skills.
    preferred_skills = {
        skill.lower().strip() for skill in preferred_skills 
        if isinstance(skill, str) and skill.strip()
    } if isinstance(preferred_skills, list) else set()

    required_skills = {
        skill.lower().strip() for skill in required_skills 
        if isinstance(skill, str) and skill.strip()
    } if isinstance(required_skills, list) else set()

    # Normalize the resume skills.
    resume_skills = {
        skill.lower().strip() for skill in resume_skills 
        if isinstance(skill, str) and skill.strip()
    } if isinstance(resume_skills, list) else set()


    # Count the matching skills.
    preferred_count = len(resume_skills & preferred_skills)
    required_count = len(resume_skills & required_skills)

    # Calculate each component of the score.
    preferred_score = (
        preferred_count / len(preferred_skills) 
        if preferred_skills else None
    )
    required_score = (
        required_count / len(required_skills) 
        if required_skills else None
    )

    # Calculate the skill score.
    # The job requires no preferred or required skills, so the score is 1.
    if required_score is None and preferred_score is None:
        skill_score = 1.0
    # The job requires no preferred skills, so the score is based solely on required skills.
    elif preferred_score is None:
        skill_score = required_score
    # The job requires no required skills, so the score is based solely on preferred skills.
    elif required_score is None:
        skill_score = preferred_score  
    else:
        skill_score = (preferred_score * 0.2) + (required_score * 0.8)


    return skill_score


def calculate_final_score(semantic_score, skill_score):
    """
    Calculate the final score based on semantic similarity and skill score.
    Final Score = (Semantic * 0.6) + (Skill * 0.4)
    """

    # Validate input types.
    if not isinstance(semantic_score, (int, float)):
        return 0.0

    if not isinstance(skill_score, (int, float)):
        return 0.0

    if not (0 <= semantic_score <= 1):
        return 0.0

    if not (0 <= skill_score <= 1):
        return 0.0

    # Calculate the final score.
    final_score = (semantic_score * 0.6) + (skill_score * 0.4)

    return final_score
