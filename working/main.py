from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional
import uuid_utils as uuid  # for UUID v7 support

import models
import schemas
import services
from database import engine, get_db

# Create all DB tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Profile Intelligence Service")

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Custom exception handlers ─────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first  = errors[0] if errors else {}
    msg    = first.get("msg", "Validation error")
    loc    = first.get("loc", [])

    # Distinguish between missing field (400) and wrong type (422)
    if first.get("type") in ("missing",):
        status_code = 400
    elif "string" in msg.lower() or "str" in str(first.get("type", "")):
        status_code = 422
    else:
        status_code = 422

    return JSONResponse(
        status_code=status_code,
        content={"status": "error", "message": msg}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # If detail is already a dict (e.g. from services.py), use it directly
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail}
    )


# ── Helper ────────────────────────────────────────────────────────────────────

def profile_to_full_dict(profile: models.Profile) -> dict:
    """Convert a DB Profile row to the full response shape."""
    return {
        "id":                 profile.id,
        "name":               profile.name,
        "gender":             profile.gender,
        "gender_probability": profile.gender_probability,
        "sample_size":        profile.sample_size,
        "age":                profile.age,
        "age_group":          profile.age_group,
        "country_id":         profile.country_id,
        "country_probability":profile.country_probability,
        "created_at":         profile.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/api/profiles", status_code=201)
async def create_profile(
    payload: schemas.ProfileCreate,
    db: Session = Depends(get_db)
):
    name = payload.name  # already lowercased + stripped by validator

    # ── Idempotency check ─────────────────────────────────────────────────────
    existing = db.query(models.Profile).filter(models.Profile.name == name).first()
    if existing:
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Profile already exists",
                "data": profile_to_full_dict(existing),
            }
        )

    # ── Enrich via external APIs ──────────────────────────────────────────────
    enriched = await services.enrich_name(name)

    # ── Persist ───────────────────────────────────────────────────────────────
    profile = models.Profile(
        id         = str(uuid.uuid7()),
        name       = name,
        created_at = datetime.now(timezone.utc).replace(tzinfo=None),  # store as naive UTC
        **enriched
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return JSONResponse(
        status_code=201,
        content={
            "status": "success",
            "data": profile_to_full_dict(profile),
        }
    )


@app.get("/api/profiles/{profile_id}", status_code=200)
def get_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {
        "status": "success",
        "data": profile_to_full_dict(profile),
    }


@app.get("/api/profiles", status_code=200)
def list_profiles(
    gender:     Optional[str] = Query(default=None),
    country_id: Optional[str] = Query(default=None),
    age_group:  Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(models.Profile)

    # Case-insensitive filtering
    if gender:
        query = query.filter(models.Profile.gender.ilike(gender))
    if country_id:
        query = query.filter(models.Profile.country_id.ilike(country_id))
    if age_group:
        query = query.filter(models.Profile.age_group.ilike(age_group))

    profiles = query.all()

    data = [
        {
            "id":         p.id,
            "name":       p.name,
            "gender":     p.gender,
            "age":        p.age,
            "age_group":  p.age_group,
            "country_id": p.country_id,
        }
        for p in profiles
    ]

    return {
        "status": "success",
        "count":  len(data),
        "data":   data,
    }


@app.delete("/api/profiles/{profile_id}", status_code=204)
def delete_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = db.query(models.Profile).filter(models.Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    db.delete(profile)
    db.commit()
    return None  # 204 No Content
