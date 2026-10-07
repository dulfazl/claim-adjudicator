"""The web API in front of the pipeline.

    uvicorn app.api:app --reload --port 8000     then open http://localhost:8000/docs
"""

import json
import os
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.adjudicate import POLICY, ROOT, SAMPLES, adjudicate, sample_images
from app.claims import Decision, Policy
from app.schemas import Bill

MAX_FILES = 4
MAX_BYTES = 5 * 1024 * 1024
IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
SAMPLE_CLAIMS = {path.stem: json.loads(path.read_text()) for path in sorted((ROOT / "claims").glob("*.json"))}

app = FastAPI(title="Claim adjudicator")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.mount("/sample-files", StaticFiles(directory=SAMPLES), name="sample-files")


class ClaimResult(BaseModel):
    decision: Decision
    documents: list[Bill]  # what the model read, so the decision can be checked against it


def run(member: dict, submitted_on: date, images: list[tuple[bytes, str]]) -> ClaimResult:
    try:
        decision, documents = adjudicate(member, submitted_on, images)
    except Exception as error:  # the model was overloaded, timed out, or answered in the wrong shape
        raise HTTPException(502, "The model could not read the documents just now. Please try again in a minute.") from error
    return ClaimResult(decision=decision, documents=documents)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/policy")
def policy() -> Policy:
    return POLICY


@app.get("/samples")
def samples() -> list[dict]:
    return [{"id": claim_id, **claim} for claim_id, claim in SAMPLE_CLAIMS.items()]


@app.post("/samples/{claim_id}")
def decide_sample(claim_id: str, version: Literal["clean", "photo", "rough"] = "clean") -> ClaimResult:
    if claim_id not in SAMPLE_CLAIMS:
        raise HTTPException(404, "No sample claim with that id.")
    claim = SAMPLE_CLAIMS[claim_id]
    return run(claim["member"], claim["submitted_on"], sample_images(claim["documents"], version))


@app.post("/claims")
def decide_claim(
    member_name: str = Form(...),
    submitted_on: date = Form(...),
    used_this_year: Decimal = Form(Decimal("0")),
    files: list[UploadFile] = File(...),
) -> ClaimResult:
    if len(files) > MAX_FILES:
        raise HTTPException(400, f"Send at most {MAX_FILES} documents.")
    images = []
    for file in files:
        if file.content_type not in IMAGE_TYPES:
            raise HTTPException(400, f"{file.filename}: only PNG, JPEG or WebP images are accepted.")
        data = file.file.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(400, f"{file.filename}: larger than 5 MB.")
        images.append((data, file.content_type))
    return run({"name": member_name, "used_this_year": used_this_year}, submitted_on, images)
