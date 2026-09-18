"""
CivicAI backend - FastAPI
"""

import os
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from database import supabase
from geocode import reverse_geocode
from models.classifier import predict
from duplicate_check import find_duplicate
from nlp_analysis import analyze_description, sentence_count, DescriptionAnalysis
from priority_score import calculate_priority

app = FastAPI(title="CivicAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_executor = ThreadPoolExecutor(max_workers=4)


@app.get("/")
def health_check():
    return {"status": "CivicAI backend running"}


@app.post("/upload-report")
async def upload_report(
    image: UploadFile = File(...),
    lat: float = Form(...),
    lng: float = Form(...),
    user_id: str = Form(...),
    description: str = Form("", max_length=500),
):
    description = description.strip()
    if description and sentence_count(description) > 3:
        raise HTTPException(status_code=422, detail="Please keep description to 3 sentences max.")

    image_bytes = await image.read()
    loop = asyncio.get_running_loop()

    # Run classification, geocoding, and NLP all in parallel
    tasks = [
        loop.run_in_executor(_executor, predict, image_bytes),
        loop.run_in_executor(_executor, reverse_geocode, lat, lng),
    ]
    if description:
        tasks.append(loop.run_in_executor(_executor, analyze_description, description))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Unpack results safely
    category, confidence = results[0] if not isinstance(results[0], Exception) else ("pothole", 0.5)
    address = results[1] if not isinstance(results[1], Exception) else f"{lat:.5f}, {lng:.5f}"
    if description:
        description_analysis = results[2] if not isinstance(results[2], Exception) else DescriptionAnalysis(0.0, "neutral", "low", 0.25)
    else:
        description_analysis = DescriptionAnalysis(0.0, "neutral", "low", 0.25)

    print(f"[upload] category={category} conf={confidence:.2f} addr={address}", flush=True)

    # Duplicate check + image upload in parallel
    dup_task = loop.run_in_executor(_executor, find_duplicate, supabase, lat, lng, category)
    
    file_name = f"{uuid.uuid4()}.jpg"
    upload_task = loop.run_in_executor(_executor, lambda: supabase.storage.from_("report-images").upload(file_name, image_bytes))

    duplicate_id, _ = await asyncio.gather(dup_task, upload_task, return_exceptions=False)
    if isinstance(duplicate_id, Exception):
        duplicate_id = None

    image_url = supabase.storage.from_("report-images").get_public_url(file_name)

    # Ward lookup — non-blocking, best effort
    try:
        ward_result = supabase.rpc("find_ward", {"lat": lat, "lng": lng}).execute()
        ward_id = ward_result.data if ward_result.data else None
    except Exception:
        ward_id = None

    priority = calculate_priority(
        confidence=confidence,
        duplicate_count=1 if duplicate_id else 0,
        days_open=0,
        location_weight=0.5,
        severity_score=description_analysis.severity_score,
        sentiment_score=description_analysis.sentiment_score,
    )

    new_report = {
        "user_id": user_id if len(user_id) == 36 else "00000000-0000-0000-0000-000000000000",
        "image_url": image_url,
        "lat": lat,
        "lng": lng,
        "address": address,
        "ward_id": ward_id,
        "category": category,
        "confidence": confidence,
        "description": description,
        "sentiment_score": description_analysis.sentiment_score,
        "sentiment_label": description_analysis.sentiment_label,
        "severity": description_analysis.severity,
        "priority_score": priority,
        "status": "pending",
        "duplicate_of": duplicate_id,
    }

    inserted = supabase.table("reports").insert(new_report).execute()
    saved_report = inserted.data[0]
    print(f"[upload] saved {saved_report['id']}", flush=True)

    return {
        "message": "Your report has been accepted.",
        "report_id": saved_report["id"],
        "category": category,
        "confidence": round(confidence, 2),
        "sentiment": description_analysis.sentiment_label,
        "severity": description_analysis.severity,
        "address": address,
        "status": "pending",
        "is_duplicate_of_existing": duplicate_id is not None,
    }


@app.get("/reports")
def get_reports(category: str = None, status: str = None, ward_id: str = None):
    query = supabase.table("reports").select("*")
    if category:
        query = query.eq("category", category)
    if status:
        query = query.eq("status", status)
    if ward_id:
        query = query.eq("ward_id", ward_id)
    return query.order("priority_score", desc=True).execute().data


@app.get("/reports/user/{user_id}")
def get_user_reports(user_id: str):
    return (
        supabase.table("reports")
        .select("id, category, address, severity, status, priority_score, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    ).data


@app.patch("/reports/{report_id}")
def update_report_status(report_id: str, status: str = Form(...)):
    valid_statuses = ["pending", "in-progress", "resolved"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid_statuses}")
    response = (
        supabase.table("reports")
        .update({"status": status})
        .eq("id", report_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Report not found")
    return response.data[0]
