# SwachhLens Product Requirements

## Problem statement
SwachhLens is an AI-powered waste response decision support system. Citizens report unwanted, overflowing, or misplaced waste using smartphone evidence and location data; municipal teams use the resulting intelligence to prioritize, assign, escalate, and verify cleanup.

## Architecture
- Expo SDK 54 / React Native mobile frontend with Expo Router.
- FastAPI backend on port 8001 with MongoDB via Motor.
- REST API under `/api` for reports, analysis, lifecycle updates, and dashboard metrics.
- Camera evidence is captured as base64; location is requested through Expo Location.
- Report analysis currently uses deterministic server-side classification, severity, volume, duplicate proximity, and intervention rules.

## User personas
- Citizen reporter: notices a cleanliness issue, submits evidence, and tracks community impact.
- Municipal operations staff: reviews priority signals, hotspots, and response teams, and handles all cleanup execution end to end.

## Core requirements
- Role-aware mobile entry for citizens, municipal staff, and recycling partners.
- Citizen report with camera evidence, live GPS/fallback coordinates, category, description, timestamp, and status.
- Waste categories: overflowing bin, garbage dump, plastic, construction debris, organic, e-waste, hazardous, and drain blockage.
- Analysis output: category label, estimated volume, severity 1–10, duplicate flag, and recommended intervention.
- Municipal overview with open, urgent, resolved, total, and hotspot metrics.
- Distinct municipal overview, priority queue, and teams workspaces.
- Mongo-backed persistence and report lifecycle update API.

## Implemented (2026-08-16)
- Replaced starter backend with live report CRUD, duplicate proximity detection, deterministic analysis, dashboard metrics, and verification fields.
- Built the SwachhLens mobile visual system with earthy green/blue municipal styling, role picker, citizen home, report composer, and staff operations dashboard.
- Added Expo camera/photo and foreground location permissions and base64 evidence handling.
- Added accessibility-friendly touch targets, test IDs, loading states, empty states, and press feedback.
- Verified with API regression and Expo preview testing at 390x844; no mocked APIs.

## Implemented (2026-08-17)
- Added report detail response actions: staff assign a response team and vehicle, then dispatch or verify cleanup.
- Added mandatory cleanup verification photo capture before a report can be marked Resolved.
- Enforced verification safety on the backend: `PATCH /api/reports/{id}` rejects a `Resolved` status unless base64 cleanup evidence exists, and stamps `verified_at`.
- Added a live hotspot map on the operations overview driven by open-report location clusters from `/api/dashboard`.
- Added in-app urgent-report alert banner for staff (severity >= 8, unresolved) that deep-links into the response actions.

## Implemented (2026-08-16 · accounts + AI + status)
- Added authentication: email/password (bcrypt) signup & login plus Emergent-managed Google one-tap login, unified 7-day session tokens.
- Roles stored on each account (citizen / staff); staff access is gated by a shared municipal invite code (`STAFF_INVITE_CODE`), enforced at signup and via an in-app "Become municipal staff" upgrade (`/api/auth/claim-staff`).
- Server-enforced RBAC: citizens see only their own reports; `/api/dashboard` and report PATCH are staff-only.
- Smart photo analysis: new reports with a photo are analyzed by Gemini 3 Flash (`gemini-3-flash-preview`) to auto-detect waste type, severity (1-10), volume, a recommended action, and a scene summary — with a deterministic fallback when no image/AI is available (`ai_powered` flag).
- Live status timeline: reports move Reported → Assigned → In Progress → Resolved, each stage stamped in `status_history`; citizens track progress in a report-detail timeline.
- Verified end-to-end: 14 backend + 13 frontend checks passed (iteration 5).

## Implemented (2026-08-16 · real hotspot map)
- Replaced the illustrative hotspot map with a real zoomable map (`react-native-maps` 1.26) showing severity-colored clustered pins; tapping a pin opens a callout with a "Get directions" action that launches the device's preferred maps app (Apple Maps on iOS, Google Maps/geo on Android).
- Backend now clusters open reports into ~110m geo-cells with a per-cluster count and max severity (`/api/dashboard` hotspots).
- Graceful fallback on web and inside Expo Go (native maps are disabled there): a stylized hotspot board plus a tappable hotspot list where each row has its own Directions button — directions work everywhere.
- Android builds read the Google Maps key from `GOOGLE_MAPS_API_KEY` via `app.config.js`; iOS uses Apple Maps (no key).

## Prioritized backlog
- P1: Replace the illustrative hotspot map with react-native-maps (clustered pins, routes).
- P1: Replace the in-app urgent banner with real push notifications on a native build.
- P2: Citizen leaderboard and verified impact history.
- P2: Report deletion/retention tooling for privacy management.
- P2: Refactor `frontend/app/index.tsx` into modular screen files.

## Next tasks
1. Upgrade hotspot map to react-native-maps and add real push notifications on a native build.
2. Add citizen rewards/leaderboard tied to resolved reports.
3. Modularize the large index.tsx screen file.