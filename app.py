
import os
import secrets
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, redirect, render_template, request, session, url_for
from openai import OpenAIError

import database
from services.resume_parser import UnreadablePDFError, parse_resume
from services.job_data import search_jobs
from services.matching import rank_jobs


load_dotenv()


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.update(
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY") or os.getenv("SECRET_KEY"),
        DATABASE=os.getenv(
            "DATABASE_PATH",
            str(Path(app.instance_path) / "job_search.sqlite3"),
        ),
    )

    if test_config:
        app.config.update(test_config)

    # Keep a stable development session key across application restarts.
    if not app.config["SECRET_KEY"]:
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)
        key_path = Path(app.instance_path) / "session.key"

        try:
            with open(
                key_path,
                "x",
                opener=lambda path, flags: os.open(path, flags, 0o600),
            ) as handle:
                handle.write(secrets.token_hex(32))
        except FileExistsError:
            pass

        app.config["SECRET_KEY"] = key_path.read_text().strip()

    database.init_app(app)

    @app.before_request
    def ensure_session():
        if "owner_id" not in session:
            session["owner_id"] = secrets.token_urlsafe(32)

        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)

    def owner_id():
        return session["owner_id"]

    def check_csrf():
        token = request.form.get("csrf_token", "")

        if not token or not secrets.compare_digest(
            token, session["csrf_token"]
        ):
            abort(400, description="Invalid form token. Reload the history page.")

    # --------------------------------------------------
    # Frontend routes
    # --------------------------------------------------

    @app.get("/")
    def home():
        return render_template(
            "index.html",
            preferences=session.get("preferences", {}),
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
            "location": request.form.get("location", "").strip(),
        }

        session["preferences"] = preferences
        return redirect(url_for("home"))

    # --------------------------------------------------
    # Main matching pipeline
    # --------------------------------------------------

    @app.post("/match")
    def match():
        resume = request.files.get("resume")

        if not resume or not resume.filename.lower().endswith(".pdf"):
            return "Please upload a PDF resume.", 400

        pdf_bytes = resume.read()

        if not pdf_bytes:
            return "The uploaded resume is empty.", 400

        preferences = {
            "role": request.form.get("role", "").strip(),
            "location": request.form.get("location", "").strip(),
        }

        session["preferences"] = preferences

        # Sheyar -> Lawrence -> Bao
        try:
            profile = parse_resume(pdf_bytes)
            jobs = search_jobs(profile, preferences)
            matches = rank_jobs(profile, jobs)
        except (OpenAIError, RuntimeError, ValueError, UnreadablePDFError) as exc:
            return render_template("upload.html", error=str(exc)), 503

        # Clifton: persist completed searches
        try:
            search_id = database.save_search(
                owner_id(), profile, preferences, matches
            )
        except (sqlite3.Error, TypeError, ValueError):
            app.logger.exception("Saving completed search failed.")
            return (
                "Search completed, but could not be saved. Please try again later.",
                503,
            )

        return render_template(
            "results.html",
            matches=matches,
            profile=profile,
            preferences=preferences,
            search_id=search_id,
        )

    # --------------------------------------------------
    # Frontend sample results (PR #9)
    # --------------------------------------------------

    @app.get("/test-results")
    def test_results():
        profile = {
            "skills": ["Python", "CSS"],
            "experience_years": 2,
        }

        jobs = [
            {
                "id": "job001",
                "title": "Python Developer",
                "description": "Build backend APIs using Python and SQL.",
            },
            {
                "id": "job002",
                "title": "Data Analyst",
                "description": "Analyze datasets using SQL and Excel.",
            },
            {
                "id": "job003",
                "title": "Frontend Developer",
                "description": "Build websites using HTML, CSS, and JavaScript.",
            },
        ]

        preferences = {
            "role": "Software Engineer",
            "location": "Chino Hills, CA",
        }

        matches = rank_jobs(profile, jobs)

        return render_template(
            "results.html",
            matches=matches,
            profile=profile,
            preferences=preferences,
        )

    # --------------------------------------------------
    # Search history (PR #10)
    # --------------------------------------------------

    @app.get("/history")
    def history():
        try:
            page = int(request.args.get("page", "1"))
        except ValueError:
            abort(400)

        if page < 1:
            abort(400)

        searches = database.list_searches(
            owner_id(),
            limit=20,
            offset=(page - 1) * 20,
        )

        return render_template(
            "history.html",
            searches=searches,
            page=page,
        )

    @app.get("/history/<search_id>")
    def saved_search(search_id):
        saved = database.get_search(owner_id(), search_id)

        if saved is None:
            abort(404)

        return render_template(
            "results.html",
            matches=saved["matches"],
            profile=saved["profile"],
            preferences=saved["preferences"],
            search_id=search_id,
        )

    @app.post("/history/<search_id>/delete")
    def remove_search(search_id):
        check_csrf()

        if not database.delete_search(owner_id(), search_id):
            abort(404)

        return redirect(url_for("history"), code=303)

    @app.post("/history/delete-all")
    def remove_all_searches():
        check_csrf()
        database.delete_owner_data(owner_id())

        return redirect(url_for("history"), code=303)

    @app.errorhandler(sqlite3.Error)
    def storage_error(_error):
        app.logger.exception("Search history storage operation failed.")
        return (
            "Search history is temporarily unavailable. Please try again later.",
            503,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run()
