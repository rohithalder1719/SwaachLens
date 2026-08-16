from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import logging
import os
import uuid

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
app = FastAPI(title="SwachhLens API")
api_router = APIRouter(prefix="/api")

CATEGORIES = {
    "overflowing_bin": ("Overflowing bin", 7, "Assign a sanitation team and mini truck"),
    "garbage_dump": ("Garbage dump", 8, "Dispatch extra workers and a mini truck"),
    "plastic_waste": ("Plastic waste", 6, "Route recyclable-heavy waste to a recycling partner"),
    "construction_debris": ("Construction debris", 7, "Dispatch a debris vehicle and two workers"),
    "organic_waste": ("Organic waste", 5, "Schedule a wet-waste collection run"),
    "e_waste": ("E-waste", 8, "Escalate to an authorized e-waste partner"),
    "hazardous_waste": ("Hazardous waste", 10, "Escalate immediately to the safety response team"),
    "drain_blockage": ("Drain blockage", 9, "Escalate to drain response and road safety team"),
}


class ReportCreate(BaseModel):
    reporter_id: str = "citizen-local"
    reporter_name: str = "Community reporter"
    category: str
    description: str = ""
    latitude: float
    longitude: float
    location_label: str = "Current location"
    image_base64: Optional[str] = None


class ReportUpdate(BaseModel):
    status: Optional[str] = None
    assigned_team: Optional[str] = None
    vehicle: Optional[str] = None
    verification_image_base64: Optional[str] = None


class Report(BaseModel):
    id: str
    reporter_id: str
    reporter_name: str
    category: str
    category_label: str
    description: str
    latitude: float
    longitude: float
    location_label: str
    image_base64: Optional[str] = None
    created_at: str
    status: str
    volume: str
    severity: int
    duplicate: bool
    recommended_action: str
    assigned_team: Optional[str] = None
    vehicle: Optional[str] = None
    verified_at: Optional[str] = None


def analyze_report(payload: ReportCreate, duplicate: bool = False) -> dict:
    label, base_severity, action = CATEGORIES.get(
        payload.category, ("General waste", 5, "Assign the nearest sanitation team")
    )
    text = f"{payload.description} {payload.category}".lower()
    severity = min(10, base_severity + (1 if any(word in text for word in ["school", "hospital", "market", "drain"]) else 0))
    volume = "Very large" if severity >= 9 else "Large" if severity >= 7 else "Medium" if severity >= 5 else "Small"
    return {"category_label": label, "severity": severity, "volume": volume, "duplicate": duplicate, "recommended_action": action}


@api_router.get("/")
async def root():
    return {"message": "SwachhLens API is ready"}


@api_router.post("/reports", response_model=Report)
async def create_report(payload: ReportCreate):
    now = datetime.now(timezone.utc).isoformat()
    nearby = await db.reports.find_one(
        {"reporter_id": {"$ne": payload.reporter_id}, "category": payload.category,
         "latitude": {"$gte": payload.latitude - 0.001, "$lte": payload.latitude + 0.001},
         "longitude": {"$gte": payload.longitude - 0.001, "$lte": payload.longitude + 0.001}},
        {"_id": 0, "id": 1},
    )
    report = {"id": str(uuid.uuid4()), **payload.model_dump(), "created_at": now, "status": "New",
              **analyze_report(payload, bool(nearby)), "assigned_team": None, "vehicle": None, "verified_at": None}
    await db.reports.insert_one(report.copy())
    return Report(**report)


@api_router.get("/reports", response_model=List[Report])
async def list_reports(reporter_id: Optional[str] = Query(default=None), status: Optional[str] = Query(default=None)):
    query = {}
    if reporter_id:
        query["reporter_id"] = reporter_id
    if status:
        query["status"] = status
    docs = await db.reports.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [Report(**doc) for doc in docs]


@api_router.get("/reports/{report_id}", response_model=Report)
async def get_report(report_id: str):
    doc = await db.reports.find_one({"id": report_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Report not found")
    return Report(**doc)


@api_router.patch("/reports/{report_id}", response_model=Report)
async def update_report(report_id: str, payload: ReportUpdate):
    changes = {key: value for key, value in payload.model_dump().items() if value is not None}
    if payload.status == "Resolved":
        changes["verified_at"] = datetime.now(timezone.utc).isoformat()
    await db.reports.update_one({"id": report_id}, {"$set": changes})
    return await get_report(report_id)


@api_router.get("/dashboard")
async def dashboard():
    docs = await db.reports.find({}, {"_id": 0, "status": 1, "severity": 1, "category_label": 1, "location_label": 1}).to_list(1000)
    open_reports = [doc for doc in docs if doc.get("status") != "Resolved"]
    hotspots = {}
    for doc in open_reports:
        label = doc.get("location_label") or "Unmapped area"
        hotspots[label] = hotspots.get(label, 0) + 1
    return {"total": len(docs), "open": len(open_reports), "urgent": sum(doc.get("severity", 0) >= 8 for doc in open_reports),
            "resolved": sum(doc.get("status") == "Resolved" for doc in docs),
            "hotspots": [{"label": label, "count": count} for label, count in sorted(hotspots.items(), key=lambda item: -item[1])[:5]]}


app.include_router(api_router)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
logging.basicConfig(level=logging.INFO)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()