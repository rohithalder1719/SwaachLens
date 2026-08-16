import os, uuid, requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("EXPO_BACKEND_URL")

def test_live_dashboard_and_reports():
    assert BASE_URL
    d=requests.get(f"{BASE_URL}/api/dashboard", timeout=15); assert d.status_code == 200
    body=d.json(); assert {"total","open","urgent","resolved","hotspots"} <= body.keys()
    r=requests.get(f"{BASE_URL}/api/reports", timeout=15); assert r.status_code == 200; assert isinstance(r.json(), list)

def test_report_ai_analysis_and_lifecycle():
    reporter=f"TEST_{uuid.uuid4()}"
    payload={"reporter_id":reporter,"reporter_name":"TEST reporter","category":"hazardous_waste","description":"spill near hospital","latitude":19.076,"longitude":72.8777,"location_label":"TEST location"}
    c=requests.post(f"{BASE_URL}/api/reports",json=payload,timeout=15); assert c.status_code == 200
    report=c.json(); assert report["category_label"]=="Hazardous waste"; assert report["severity"]==10; assert report["recommended_action"]
    rid=report["id"]
    g=requests.get(f"{BASE_URL}/api/reports/{rid}",timeout=15); assert g.status_code==200 and g.json()["description"]==payload["description"]
    u=requests.patch(f"{BASE_URL}/api/reports/{rid}",json={"status":"Resolved","assigned_team":"TEST team"},timeout=15); assert u.status_code==200
    updated=u.json(); assert updated["status"]=="Resolved" and updated["assigned_team"]=="TEST team" and updated["verified_at"]
