import os
import uuid
import requests

BASE = os.environ.get("EXPO_PUBLIC_BACKEND_URL").rstrip("/")

def test_report_crud_and_dashboard():
    s = requests.Session()
    payload = {"reporter_id": "TEST_" + str(uuid.uuid4()), "reporter_name": "TEST reporter",
               "category": "hazardous_waste", "description": "TEST hospital spill",
               "latitude": 19.076, "longitude": 72.8777, "location_label": "TEST Station"}
    created = s.post(f"{BASE}/api/reports", json=payload)
    assert created.status_code == 200, created.text
    data = created.json()
    assert data["category_label"] == "Hazardous waste"
    assert data["severity"] == 10 and data["volume"] == "Very large"
    assert isinstance(data["duplicate"], bool) and data["recommended_action"]
    rid = data["id"]
    fetched = s.get(f"{BASE}/api/reports/{rid}")
    assert fetched.status_code == 200 and fetched.json()["description"] == payload["description"]
    listed = s.get(f"{BASE}/api/reports", params={"reporter_id": payload["reporter_id"]})
    assert listed.status_code == 200 and any(x["id"] == rid for x in listed.json())
    updated = s.patch(f"{BASE}/api/reports/{rid}", json={"status": "Resolved", "assigned_team": "TEST team", "vehicle": "TEST van", "verification_image_base64": "abc"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "Resolved" and updated.json()["assigned_team"] == "TEST team" and updated.json()["verified_at"]
    dashboard = s.get(f"{BASE}/api/dashboard")
    assert dashboard.status_code == 200 and all(k in dashboard.json() for k in ("total", "open", "urgent", "resolved", "hotspots"))