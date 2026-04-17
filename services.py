import asyncio
import httpx
from fastapi import HTTPException


GENDERIZE_URL = "https://api.genderize.io"
AGIFY_URL     = "https://api.agify.io"
NATIONALIZE_URL = "https://api.nationalize.io"


# ── Helpers ───────────────────────────────────────────────────────────────────

def classify_age_group(age: int) -> str:
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    else:
        return "senior"


async def _fetch(client: httpx.AsyncClient, url: str, params: dict) -> dict:
    """Perform a single GET request and return parsed JSON."""
    response = await client.get(url, params=params, timeout=10.0)
    response.raise_for_status()
    return response.json()


# ── Main enrichment function ──────────────────────────────────────────────────

async def enrich_name(name: str) -> dict:
    """
    Call all three external APIs concurrently, validate responses,
    and return a clean enriched dict ready for storage.
    Raises HTTPException(502) on any invalid/missing data.
    """
    async with httpx.AsyncClient() as client:
        params = {"name": name}

        # Fire all three requests at once
        genderize_task    = _fetch(client, GENDERIZE_URL, params)
        agify_task        = _fetch(client, AGIFY_URL, params)
        nationalize_task  = _fetch(client, NATIONALIZE_URL, params)

        try:
            genderize_data, agify_data, nationalize_data = await asyncio.gather(
                genderize_task, agify_task, nationalize_task
            )
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail={"status": "502", "message": f"External API returned an invalid response: {exc}"}
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail={"status": "502", "message": f"Network error reaching external API: {exc}"}
            )

    # ── Validate Genderize ────────────────────────────────────────────────────
    gender = genderize_data.get("gender")
    count  = genderize_data.get("count", 0)

    if gender is None or count == 0:
        raise HTTPException(
            status_code=502,
            detail={"status": "502", "message": "Genderize returned an invalid response"}
        )

    gender_probability = genderize_data.get("probability")
    sample_size        = count  # renamed as required

    # ── Validate Agify ────────────────────────────────────────────────────────
    age = agify_data.get("age")

    if age is None:
        raise HTTPException(
            status_code=502,
            detail={"status": "502", "message": "Agify returned an invalid response"}
        )

    age_group = classify_age_group(age)

    # ── Validate Nationalize ──────────────────────────────────────────────────
    countries = nationalize_data.get("country", [])

    if not countries:
        raise HTTPException(
            status_code=502,
            detail={"status": "502", "message": "Nationalize returned an invalid response"}
        )

    # Pick the country with the highest probability
    top_country      = max(countries, key=lambda c: c.get("probability", 0))
    country_id       = top_country.get("country_id")
    country_probability = top_country.get("probability")

    return {
        "gender":              gender,
        "gender_probability":  gender_probability,
        "sample_size":         sample_size,
        "age":                 age,
        "age_group":           age_group,
        "country_id":          country_id,
        "country_probability": country_probability,
    }
