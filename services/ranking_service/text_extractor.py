def extract_resume_skills(resume):
    """
    Extracts skills from a resume json object.
    """

    skills = []
    if not resume:
        return skills

    # Extract skills from the resume.
    core_competencies = resume.get("core_competencies", {})

    if not core_competencies:
        return skills

    technical_skills = core_competencies.get("technical_skills", [])
    domain_knowledge = core_competencies.get("domain_knowledge", [])
    tools_and_frameworks = core_competencies.get("tools_and_frameworks", [])

    # Append the extracted skills to the skills list.
    skills.extend(technical_skills)
    skills.extend(domain_knowledge)
    skills.extend(tools_and_frameworks)

    # Remove duplicates by converting the list to a set and back to a list.
    skills = list(set(skills))

    return skills


def extract_job_requirements(job):
    """
    Extracts requirements from a job posting json object.
    """

    requirements = []
    
    if not job:
        return requirements

    # Extract requirements from the job posting.
    requirements = job.get("requirements", {})

    return requirements
