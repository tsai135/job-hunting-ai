import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, session, redirect

# Import functions from teammates' modules
from services.resume import parse_resume       # Sheyar
from services.job_data import search_jobs       # Lawrence
from services.matching import rank_jobs         # Bao

load_dotenv()
app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


@app.get("/")
def home():
    return render_template(
        "index.html",
        preferences=session.get("preferences", {})
    )

@app.get("/login")
def login_page():
    return render_template("login.html")


@app.get("/register")
def register_page():
    return render_template("register.html")


@app.get("/upload")
def upload_page():
    return render_template("upload.html")

@app.post("/save-preferences")
def save_preferences():
    preferences = {
        "role": request.form.get("role", "").strip(),
        "location": request.form.get("location", "").strip()
    }

    session["preferences"] = preferences

    return redirect("/")


@app.post("/match")
def match():
    # STEP 1: Receive input from Paulene's UI
    resume = request.files.get("resume")

    if not resume or not resume.filename.lower().endswith(".pdf"):
        return "Please upload a PDF resume.", 400

    pdf_bytes = resume.read()
    if not pdf_bytes:
        return "The uploaded resume is empty.", 400

    preferences = {
        "role": request.form.get("role", "").strip(),
        "location": request.form.get("location", "").strip()
    }

    # Save the user's career preferences
    session["preferences"] = preferences

    # STEP 2: Sheyar parses the resume
    profile = parse_resume(pdf_bytes)

    # STEP 3: Lawrence retrieves jobs
    jobs = search_jobs(profile, preferences)

    # STEP 4: Bao ranks the jobs
    matches = rank_jobs(profile, jobs)

    # STEP 5: Paulene's page displays the results
    return render_template(
        "results.html",
        matches=matches,
        profile=profile,
        preferences=preferences
    )

@app.get("/test-results")
def test_results():
    # Sample profile for frontend testing
    profile = {
        "skills": ["Python", "CSS"],
        "experience_years": 2
    }

    # Sample jobs based on Bao's test data
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

    preferences = {
        "role": "Software Engineer",
        "location": "Chino Hills, CA"
    }

    # Run the actual matching algorithm
    matches = rank_jobs(profile, jobs)

    return render_template(
        "results.html",
        matches=matches,
        profile=profile,
        preferences=preferences
    )

if __name__ == "__main__":
    app.run(debug=True)
