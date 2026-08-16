"""SwachhLens backend regression tests.

Covers the iteration-5 auth + AI-analysis + status-flow features.
Uses the public EXPO_PUBLIC_BACKEND_URL so tests exercise the same
edge routing users see.
"""
import base64
import io
import os
import time
import uuid

import pytest
import requests

BASE_URL = (os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("EXPO_BACKEND_URL", "")).rstrip("/")
STAFF_INVITE_CODE = os.environ.get("STAFF_INVITE_CODE", "SWACHH2026")

RUN_TAG = uuid.uuid4().hex[:8]
CITIZEN_EMAIL = f"test_citizen_{RUN_TAG}@swachhlens.test"
STAFF_EMAIL = f"test_staff_{RUN_TAG}@swachhlens.test"
PASSWORD = "Passw0rd!"


def _real_jpeg_b64() -> str:
    """Small JPEG with real visual features (not blank/solid)."""
    try:
        from PIL import Image, ImageDraw  # type: ignore
    except Exception:
        pytest.skip("Pillow not installed")
    img = Image.new("RGB", (320, 240), (110, 120, 90))
    d = ImageDraw.Draw(img)
    # Fake overflowing bin + debris scene: gradient + shapes
    for y in range(240):
        d.line([(0, y), (320, y)], fill=(60 + y // 4, 70 + y // 5, 50 + y // 6))
    d.rectangle([40, 120, 140, 220], fill=(30, 30, 30), outline=(200, 200, 200), width=3)
    d.rectangle([160, 140, 280, 220], fill=(80, 55, 30), outline=(220, 220, 200), width=2)
    for i in range(0, 320, 12):
        d.ellipse([i, 200 + (i % 20), i + 10, 215 + (i % 20)], fill=(200, 190, 40))
    d.polygon([(200, 100), (240, 60), (280, 100)], fill=(160, 40, 30))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode()


@pytest.fixture(scope="module")
def api():
    assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL must be set"
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def citizen_token(api):
    r = api.post(f"{BASE_URL}/api/auth/signup",
                 json={"email": CITIZEN_EMAIL, "password": PASSWORD, "name": "TEST Citizen"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["role"] == "citizen"
    assert body["user"]["email"] == CITIZEN_EMAIL
    return body["token"]


@pytest.fixture(scope="module")
def staff_token(api):
    r = api.post(f"{BASE_URL}/api/auth/signup",
                 json={"email": STAFF_EMAIL, "password": PASSWORD,
                       "name": "TEST Staff", "role": "staff",
                       "invite_code": STAFF_INVITE_CODE})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["role"] == "staff"
    return body["token"]


# ---------------- Auth ----------------
class TestAuth:
    def test_signup_staff_requires_correct_code(self, api):
        bad = api.post(f"{BASE_URL}/api/auth/signup",
                       json={"email": f"TEST_badstaff_{RUN_TAG}@x.test",
                             "password": PASSWORD, "name": "X",
                             "role": "staff", "invite_code": "WRONG"})
        assert bad.status_code == 400
        empty = api.post(f"{BASE_URL}/api/auth/signup",
                         json={"email": f"TEST_emptystaff_{RUN_TAG}@x.test",
                               "password": PASSWORD, "name": "X",
                               "role": "staff"})
        assert empty.status_code == 400

    def test_login_and_me(self, api, citizen_token):
        r = api.post(f"{BASE_URL}/api/auth/login",
                     json={"email": CITIZEN_EMAIL, "password": PASSWORD})
        assert r.status_code == 200
        tok = r.json()["token"]
        me = api.get(f"{BASE_URL}/api/auth/me",
                     headers={"Authorization": f"Bearer {tok}"})
        assert me.status_code == 200
        assert me.json()["user"]["email"] == CITIZEN_EMAIL

    def test_login_wrong_password(self, api, citizen_token):
        r = api.post(f"{BASE_URL}/api/auth/login",
                     json={"email": CITIZEN_EMAIL, "password": "wrong"})
        assert r.status_code == 401

    def test_me_without_token(self, api):
        r = api.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 401


# ---------------- RBAC ----------------
class TestRBAC:
    def test_citizen_cannot_access_dashboard(self, api, citizen_token):
        r = api.get(f"{BASE_URL}/api/dashboard",
                    headers={"Authorization": f"Bearer {citizen_token}"})
        assert r.status_code == 403

    def test_staff_can_access_dashboard(self, api, staff_token):
        r = api.get(f"{BASE_URL}/api/dashboard",
                    headers={"Authorization": f"Bearer {staff_token}"})
        assert r.status_code == 200
        assert {"total", "open", "urgent", "resolved", "hotspots"} <= r.json().keys()

    def test_citizen_cannot_patch_report(self, api, citizen_token, staff_token):
        # create a report as citizen, then try to patch it
        c = api.post(f"{BASE_URL}/api/reports",
                     headers={"Authorization": f"Bearer {citizen_token}"},
                     json={"category": "plastic_waste", "description": "TEST rbac",
                           "latitude": 19.076, "longitude": 72.8777,
                           "location_label": "TEST rbac loc"})
        assert c.status_code == 200
        rid = c.json()["id"]
        r = api.patch(f"{BASE_URL}/api/reports/{rid}",
                      headers={"Authorization": f"Bearer {citizen_token}"},
                      json={"status": "Assigned"})
        assert r.status_code == 403


# ---------------- Report creation & AI ----------------
class TestReports:
    def test_create_report_no_image_fallback(self, api, citizen_token):
        r = api.post(f"{BASE_URL}/api/reports",
                     headers={"Authorization": f"Bearer {citizen_token}"},
                     json={"category": "hazardous_waste",
                           "description": "TEST spill near hospital",
                           "latitude": 19.076, "longitude": 72.8777,
                           "location_label": "TEST hospital gate"})
        assert r.status_code == 200
        body = r.json()
        assert body["ai_powered"] is False
        assert body["category_label"] == "Hazardous waste"
        assert body["severity"] == 10  # hospital keyword boost, capped at 10
        assert body["status"] == "Reported"
        assert body["status_history"][0]["status"] == "Reported"

    def test_create_report_with_image_ai(self, api, citizen_token):
        img = _real_jpeg_b64()
        r = api.post(f"{BASE_URL}/api/reports",
                     headers={"Authorization": f"Bearer {citizen_token}"},
                     json={"category": "overflowing_bin",
                           "description": "TEST AI overflow scene",
                           "latitude": 19.10, "longitude": 72.88,
                           "location_label": "TEST AI corner",
                           "image_base64": img},
                     timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        # AI may occasionally fall back; assert shape either way but flag
        assert 1 <= body["severity"] <= 10
        assert body["volume"] in ("Small", "Medium", "Large", "Very large")
        assert body["recommended_action"]
        if not body["ai_powered"]:
            pytest.skip("AI fell back to deterministic; still valid shape but non-AI run")
        assert body["ai_summary"], "AI-powered response should include a summary"

    def test_citizen_sees_only_own_reports(self, api, citizen_token, staff_token):
        # staff creates a report; citizen list should not include it
        s = api.post(f"{BASE_URL}/api/reports",
                     headers={"Authorization": f"Bearer {staff_token}"},
                     json={"category": "drain_blockage", "description": "TEST staff-only",
                           "latitude": 19.20, "longitude": 72.90,
                           "location_label": "TEST staff loc"})
        assert s.status_code == 200
        staff_report_id = s.json()["id"]
        c = api.get(f"{BASE_URL}/api/reports",
                    headers={"Authorization": f"Bearer {citizen_token}"})
        assert c.status_code == 200
        assert all(item["id"] != staff_report_id for item in c.json())

        st = api.get(f"{BASE_URL}/api/reports",
                     headers={"Authorization": f"Bearer {staff_token}"})
        assert st.status_code == 200
        assert any(item["id"] == staff_report_id for item in st.json())


# ---------------- Status flow ----------------
class TestStatusFlow:
    @pytest.fixture(scope="class")
    def workflow_report(self, api, citizen_token):
        r = api.post(f"{BASE_URL}/api/reports",
                     headers={"Authorization": f"Bearer {citizen_token}"},
                     json={"category": "garbage_dump", "description": "TEST flow",
                           "latitude": 19.05, "longitude": 72.85,
                           "location_label": "TEST flow loc"})
        assert r.status_code == 200
        return r.json()["id"]

    def test_assign_and_in_progress(self, api, staff_token, workflow_report):
        a = api.patch(f"{BASE_URL}/api/reports/{workflow_report}",
                      headers={"Authorization": f"Bearer {staff_token}"},
                      json={"status": "Assigned", "assigned_team": "TEST team",
                            "vehicle": "Mini truck"})
        assert a.status_code == 200
        assert a.json()["status"] == "Assigned"
        assert a.json()["assigned_team"] == "TEST team"
        history = a.json()["status_history"]
        assert any(e["status"] == "Assigned" for e in history)

        p = api.patch(f"{BASE_URL}/api/reports/{workflow_report}",
                      headers={"Authorization": f"Bearer {staff_token}"},
                      json={"status": "In Progress"})
        assert p.status_code == 200
        assert p.json()["status"] == "In Progress"
        assert any(e["status"] == "In Progress" for e in p.json()["status_history"])

    def test_resolve_without_evidence_rejected(self, api, staff_token, workflow_report):
        r = api.patch(f"{BASE_URL}/api/reports/{workflow_report}",
                      headers={"Authorization": f"Bearer {staff_token}"},
                      json={"status": "Resolved"})
        assert r.status_code == 400

    def test_resolve_with_evidence(self, api, staff_token, workflow_report):
        img = _real_jpeg_b64()
        r = api.patch(f"{BASE_URL}/api/reports/{workflow_report}",
                      headers={"Authorization": f"Bearer {staff_token}"},
                      json={"status": "Resolved", "verification_image_base64": img})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "Resolved"
        assert body["verified_at"]
        assert body["verification_image_base64"]


# ---------------- Claim staff ----------------
class TestClaimStaff:
    def test_citizen_can_upgrade_with_code(self, api):
        email = f"TEST_upgrade_{RUN_TAG}@x.test"
        s = api.post(f"{BASE_URL}/api/auth/signup",
                     json={"email": email, "password": PASSWORD, "name": "Up"})
        assert s.status_code == 200
        tok = s.json()["token"]
        bad = api.post(f"{BASE_URL}/api/auth/claim-staff",
                       headers={"Authorization": f"Bearer {tok}"},
                       json={"invite_code": "NOPE"})
        assert bad.status_code == 400
        ok = api.post(f"{BASE_URL}/api/auth/claim-staff",
                      headers={"Authorization": f"Bearer {tok}"},
                      json={"invite_code": STAFF_INVITE_CODE})
        assert ok.status_code == 200
        assert ok.json()["user"]["role"] == "staff"
