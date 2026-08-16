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
- Municipal operations staff: reviews priority signals, hotspots, and response teams.
- Recycling partner: views the partner workspace context for recyclable-heavy response coordination.

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

## Prioritized backlog
- P0: Persist authenticated accounts and role permissions (email/phone account flow from the brief) with server-enforced role access.
- P1: Replace deterministic analysis with a production computer-vision/LLM service after credentials and provider are selected.
- P1: Replace the in-app urgent banner with real push notifications once the app is built on a real device.
- P1: Upgrade the illustrative hotspot map to a real map (react-native-maps) with clustered pins and route context.
- P2: Add citizen leaderboard and verified impact history.
- P2: Add report deletion/retention tooling for test and privacy management.
- P2: Refactor `frontend/app/index.tsx` into modular screen files (citizen home, staff dashboard, map, report detail, composer).

## Next tasks
1. Implement authentication and server-enforced role access (email/phone account flow).
2. Move deterministic analysis to a real AI provider once credentials are chosen.
3. Upgrade hotspot map to react-native-maps and add real push notifications on a native build.