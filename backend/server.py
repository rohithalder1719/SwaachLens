from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional
import json
import logging
import os
import re
import secrets
import uuid

import bcrypt
import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware
from google.oauth2 import id_token
from google.auth.transport import requests
from google import genai
from google.genai import types
import base64

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
STAFF_INVITE_CODE = os.environ.get("STAFF_INVITE_CODE", "SWACHH2026")
app = FastAPI(title="SwachhLens API")
api_router = APIRouter(prefix="/api")
logger = logging.getLogger("swachhlens")

# Lifecycle stages a report moves through.
STATUS_FLOW = ["Reported", "Assigned", "In Progress", "Resolved"]

CATEGORIES = {
    "overflowing_bin": ("Overflowing bin", 7, "Assign a sanitation team and mini truck"),
    "garbage_dump": ("Garbage dump", 8, "Dispatch extra workers and a mini truck"),
    "plastic_waste": ("Plastic waste", 6, "Assign the municipal recycling crew"),
    "construction_debris": ("Construction debris", 7, "Dispatch a debris vehicle and two workers"),
    "organic_waste": ("Organic waste", 5, "Schedule a wet-waste collection run"),
    "e_waste": ("E-waste", 8, "Assign the municipal e-waste handling team"),
    "hazardous_waste": ("Hazardous waste", 10, "Escalate immediately to the safety response team"),
    "drain_blockage": ("Drain blockage", 9, "Escalate to drain response and road safety team"),
}

# ----------------------------- Models -----------------------------
class SignupRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "citizen"
    invite_code: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class SessionRequest(BaseModel):
    session_id: str


class ClaimStaffRequest(BaseModel):
    invite_code: str


class PublicUser(BaseModel):
    user_id: str
    email: str
    name: str
    role: str
    picture: Optional[str] = None


class ReportCreate(BaseModel):
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


class StatusEvent(BaseModel):
    status: str
    at: str
    note: Optional[str] = None


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
    ai_summary: Optional[str] = None
    ai_powered: bool = False
    assigned_team: Optional[str] = None
    vehicle: Optional[str] = None
    verified_at: Optional[str] = None
    verification_image_base64: Optional[str] = None
    status_history: List[StatusEvent] = Field(default_factory=list)


# ----------------------------- Auth helpers -----------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def public_user(doc: dict) -> dict:
    return {"user_id": doc["user_id"], "email": doc["email"], "name": doc.get("name", ""),
            "role": doc.get("role", "citizen"), "picture": doc.get("picture")}


async def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    await db.user_sessions.insert_one({
        "session_token": token,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
    })
    return token


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = authorization.split(" ", 1)[1].strip()
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(401, "Invalid session")
    expires = session.get("expires_at")
    if expires is not None:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            raise HTTPException(401, "Session expired")
    user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(401, "User not found")
    return user


async def require_staff(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "staff":
        raise HTTPException(403, "Municipal staff access required")
    return user


# ----------------------------- AI analysis -----------------------------
def deterministic_analysis(category: str, description: str, duplicate: bool) -> dict:
    label, base_severity, action = CATEGORIES.get(
        category, ("General waste", 5, "Assign the nearest sanitation team")
    )
    text = f"{description} {category}".lower()
    severity = min(10, base_severity + (1 if any(w in text for w in ["school", "hospital", "market", "drain"]) else 0))
    volume = "Very large" if severity >= 9 else "Large" if severity >= 7 else "Medium" if severity >= 5 else "Small"
    return {"category_label": label, "severity": severity, "volume": volume,
            "duplicate": duplicate, "recommended_action": action, "ai_summary": None, "ai_powered": False}


async def ai_analyze_image(image_base64: str, category: str, description: str, duplicate: bool) -> dict:
    fallback = deterministic_analysis(category, description, duplicate)
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not (image_base64 and gemini_key):
        return fallback
    try:
        client_genai = genai.Client(api_key=gemini_key)
        
        prompt = (
            f"Analyze this waste scene. The citizen tagged it as category '{category}'. "
            f"Note: '{description or 'none'}'. "
            "Return JSON with exactly these keys: "
            '{"waste_type": short label, "severity": integer 1-10 (10=hazardous/urgent), '
            '"volume": one of "Small"|"Medium"|"Large"|"Very large", '
            '"recommended_action": one concise sentence for the crew, '
            '"summary": one short sentence describing what is visible}.'
        )
        
        response = client_genai.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(
                    data=base64.b64decode(image_base64),
                    mime_type='image/jpeg',
                ),
                prompt,
            ],
            config=types.GenerateContentConfig(
                system_instruction="You are a municipal waste triage analyst. Look at the photo and classify the waste for a city cleanup crew. Reply with STRICT JSON only, no markdown."
            )
        )
        
        text = response.text if isinstance(response.text, str) else str(response.text)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return fallback
        data = json.loads(match.group(0))
        severity = int(round(float(data.get("severity", fallback["severity"]))))
        severity = max(1, min(10, severity))
        volume = data.get("volume") or fallback["volume"]
        if volume not in ("Small", "Medium", "Large", "Very large"):
            volume = fallback["volume"]
        return {
            "category_label": str(data.get("waste_type") or fallback["category_label"])[:60],
            "severity": severity,
            "volume": volume,
            "duplicate": duplicate,
            "recommended_action": str(data.get("recommended_action") or fallback["recommended_action"])[:200],
            "ai_summary": str(data.get("summary"))[:240] if data.get("summary") else None,
            "ai_powered": True,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("AI analysis failed, using deterministic fallback: %s", exc)
        return fallback


# ----------------------------- Auth routes -----------------------------
@api_router.post("/auth/signup")
async def signup(payload: SignupRequest):
    email = payload.email.lower().strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(400, "Please enter a valid email address")
    if len(payload.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    role = payload.role if payload.role in ("citizen", "staff") else "citizen"
    if role == "staff" and (payload.invite_code or "").strip() != STAFF_INVITE_CODE:
        raise HTTPException(400, "Invalid municipal invite code")
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "An account with this email already exists")
    user = {
        "user_id": f"user_{uuid.uuid4().hex[:12]}",
        "email": email,
        "name": payload.name.strip() or email.split("@")[0],
        "role": role,
        "password_hash": hash_password(payload.password),
        "picture": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user.copy())
    token = await create_session(user["user_id"])
    return {"token": token, "user": public_user(user)}


@api_router.post("/auth/login")
async def login(payload: LoginRequest):
    email = payload.email.lower().strip()
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not user.get("password_hash") or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(401, "Incorrect email or password")
    token = await create_session(user["user_id"])
    return {"token": token, "user": public_user(user)}


@api_router.post("/auth/session")
async def google_session(payload: SessionRequest):
    try:
        idinfo = id_token.verify_oauth2_token(
            payload.session_id, 
            requests.Request(), 
            os.environ.get("GOOGLE_CLIENT_ID")
        )
        email = idinfo.get("email").lower().strip()
        name = idinfo.get("name")
        picture = idinfo.get("picture")
    except ValueError:
        raise HTTPException(401, "Invalid or expired Google token")
    
    if not email:
        raise HTTPException(401, "Token did not return an email")
        
    user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if not user:
        user = {
            "user_id": f"user_{uuid.uuid4().hex[:12]}",
            "email": email,
            "name": name or email.split("@")[0],
            "role": "citizen",
            "password_hash": None,
            "picture": picture,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(user.copy())
    token = await create_session(user["user_id"])
    return {"token": token, "user": public_user(user)}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"user": public_user(user)}


@api_router.post("/auth/logout")
async def logout(authorization: Optional[str] = Header(default=None)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        await db.user_sessions.delete_one({"session_token": token})
    return {"ok": True}


@api_router.post("/auth/claim-staff")
async def claim_staff(payload: ClaimStaffRequest, user: dict = Depends(get_current_user)):
    if payload.invite_code.strip() != STAFF_INVITE_CODE:
        raise HTTPException(400, "Invalid municipal invite code")
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"role": "staff"}})
    user["role"] = "staff"
    return {"user": public_user(user)}


# ----------------------------- Report routes -----------------------------
@api_router.get("/")
async def root():
    return {"message": "SwachhLens API is ready"}


@api_router.post("/reports", response_model=Report)
async def create_report(payload: ReportCreate, user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    nearby = await db.reports.find_one(
        {"reporter_id": {"$ne": user["user_id"]}, "category": payload.category,
         "latitude": {"$gte": payload.latitude - 0.001, "$lte": payload.latitude + 0.001},
         "longitude": {"$gte": payload.longitude - 0.001, "$lte": payload.longitude + 0.001}},
        {"_id": 0, "id": 1},
    )
    analysis = await ai_analyze_image(payload.image_base64 or "", payload.category, payload.description, bool(nearby))
    report = {
        "id": str(uuid.uuid4()),
        "reporter_id": user["user_id"],
        "reporter_name": user.get("name", "Community reporter"),
        **payload.model_dump(),
        "created_at": now,
        "status": "Reported",
        **analysis,
        "assigned_team": None,
        "vehicle": None,
        "verified_at": None,
        "verification_image_base64": None,
        "status_history": [{"status": "Reported", "at": now, "note": "Signal received from citizen"}],
    }
    await db.reports.insert_one(report.copy())
    return Report(**report)


@api_router.get("/reports", response_model=List[Report])
async def list_reports(status: Optional[str] = Query(default=None), user: dict = Depends(get_current_user)):
    query: dict = {}
    if user.get("role") != "staff":
        query["reporter_id"] = user["user_id"]
    if status:
        query["status"] = status
    docs = await db.reports.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [Report(**doc) for doc in docs]


@api_router.get("/reports/{report_id}", response_model=Report)
async def get_report(report_id: str, user: dict = Depends(get_current_user)):
    doc = await db.reports.find_one({"id": report_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Report not found")
    if user.get("role") != "staff" and doc.get("reporter_id") != user["user_id"]:
        raise HTTPException(403, "Not allowed to view this report")
    return Report(**doc)


@api_router.patch("/reports/{report_id}", response_model=Report)
async def update_report(report_id: str, payload: ReportUpdate, user: dict = Depends(require_staff)):
    existing = await db.reports.find_one({"id": report_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Report not found")
    if payload.status == "Resolved" and not (payload.verification_image_base64 or existing.get("verification_image_base64")):
        raise HTTPException(400, "Cleanup verification evidence is required before resolving a report")

    changes = {k: v for k, v in payload.model_dump().items() if v is not None}
    now = datetime.now(timezone.utc).isoformat()
    if payload.status == "Resolved":
        changes["verified_at"] = now

    history = existing.get("status_history") or []
    if payload.status and payload.status != existing.get("status"):
        note = None
        if payload.status == "Assigned" and payload.assigned_team:
            note = f"Assigned to {payload.assigned_team}"
        elif payload.status == "Resolved":
            note = "Cleanup verified with field evidence"
        history = history + [{"status": payload.status, "at": now, "note": note}]
        changes["status_history"] = history

    await db.reports.update_one({"id": report_id}, {"$set": changes})
    doc = await db.reports.find_one({"id": report_id}, {"_id": 0})
    return Report(**doc)


@api_router.get("/dashboard")
async def dashboard(user: dict = Depends(require_staff)):
    docs = await db.reports.find(
        {}, {"_id": 0, "status": 1, "severity": 1, "location_label": 1, "latitude": 1, "longitude": 1}
    ).to_list(1000)
    open_reports = [d for d in docs if d.get("status") != "Resolved"]
    buckets: dict = {}
    for d in open_reports:
        lat = float(d.get("latitude", 19.076))
        lng = float(d.get("longitude", 72.8777))
        key = (round(lat, 3), round(lng, 3))
        item = buckets.get(key)
        if not item:
            item = {"label": d.get("location_label") or "Unmapped area", "count": 0,
                    "latitude": lat, "longitude": lng, "severity": 0}
            buckets[key] = item
        item["count"] += 1
        item["severity"] = max(item["severity"], int(d.get("severity", 0)))
        if item["label"] in ("Unmapped area", "Location unavailable") and d.get("location_label"):
            item["label"] = d["location_label"]
    return {
        "total": len(docs),
        "open": len(open_reports),
        "urgent": sum(d.get("severity", 0) >= 8 for d in open_reports),
        "resolved": sum(d.get("status") == "Resolved" for d in docs),
        "hotspots": sorted(buckets.values(), key=lambda i: (-i["count"], -i["severity"]))[:8],
    }


app.include_router(api_router)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
logging.basicConfig(level=logging.INFO)


@app.on_event("startup")
async def create_indexes():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("user_id", unique=True)
    await db.user_sessions.create_index("session_token", unique=True)
    await db.user_sessions.create_index("user_id")
    await db.user_sessions.create_index("expires_at", expireAfterSeconds=0)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()