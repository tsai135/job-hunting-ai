Job Hunting AI CS 467 Capstone
A Flask web app that accepts a resume and job preferences, searches for jobs, ranks matches, and displays recommendations.

10/19/26 Current status: End-to-end local prototype. With credentials configured,
resume parsing uses OpenAI and jobs come from Adzuna. Without credentials, local
demo profiles and job postings are used so the full workflow can still be tested.

Run locally

Requires Python 3.10+.

# From the repository folder
python3 -m venv .venv
source .venv/bin/activate       # macOS / Linux
python -m pip install -r requirements.txt
python app.py

On Windows (PowerShell), use these commands instead to create and activate the environment:
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
Open http://127.0.0.1:5000 in your web browser. Upload any nonempty PDF and enter a role/location to test the demo flow. The PDF content does not matter yet.

For live integrations, copy `.env.example` to `.env` and set `OPENAI_API_KEY`,
`ADZUNA_APP_ID`, and `ADZUNA_APP_KEY`. Set `JOB_SEARCH_DEMO=0` to fail instead
of using demo jobs when Adzuna credentials are unavailable. The PDF content does not matter yet.