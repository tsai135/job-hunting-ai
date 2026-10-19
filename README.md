Job Hunting AI CS 467 Capstone
A Flask web app that accepts a resume and job preferences, searches for jobs, ranks matches, and displays recommendations.

10/19/26 Current status: Working skeleton only. Resume parsing and job retrieval use placeholder data; matching is demo-only.

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