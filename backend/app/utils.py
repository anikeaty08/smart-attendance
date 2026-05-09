import io
from math import asin, ceil, cos, radians, sin, sqrt
from pathlib import Path
from random import SystemRandom

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def generate_session_code() -> str:
    return f"{SystemRandom().randint(0, 9999):04d}"


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_m = 6371000
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    r_lat1 = radians(lat1)
    r_lat2 = radians(lat2)
    a = sin(d_lat / 2) ** 2 + cos(r_lat1) * cos(r_lat2) * sin(d_lon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return earth_radius_m * c


def normalize_email(email: str) -> str:
    return email.strip().lower()


# ---------------------------------------------------------------------------
# Pagination helper
# ---------------------------------------------------------------------------

def paginate_query(db: Session, query, page: int = 1, page_size: int = 50):
    """Return paginated results with metadata."""
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": items,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": ceil(total / page_size) if total else 0,
        },
    }


# ---------------------------------------------------------------------------
# CSV / Excel parsing
# ---------------------------------------------------------------------------

async def parse_upload(file: UploadFile) -> list[dict[str, str]]:
    import pandas as pd

    content = await file.read()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(io.BytesIO(content))
    else:
        df = pd.read_csv(io.BytesIO(content))
    df = df.fillna("")
    return [{str(k).strip(): str(v).strip() for k, v in row.items()} for row in df.to_dict(orient="records")]


def build_csv(rows: list[dict], columns: list[str]) -> str:
    """Build a CSV string from a list of dicts."""
    import csv

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
