"""
CivicAI backend - FastAPI
Endpoints: /upload-report, /reports, /reports/{id}
To be filled in: ties together geocode.py, duplicate_check.py,
priority_score.py, and models/classifier.py
"""

from fastapi import FastAPI

app = FastAPI(title="CivicAI Backend")


@app.get("/")
def health_check():
    return {"status": "CivicAI backend running"}


# TODO: POST /upload-report
# TODO: GET /reports
# TODO: PATCH /reports/{id}
