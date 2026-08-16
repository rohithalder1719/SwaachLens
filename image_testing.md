# Image Integration Testing Playbook

## Image Handling Rules
- Always use base64-encoded images for all tests and requests.
- Accepted formats: JPEG, PNG, WEBP only. Do not use SVG, BMP, HEIC.
- Do not upload blank, solid-color, or uniform-variance images.
- Every image must contain real visual features (objects, edges, textures, shadows).
- If not PNG/JPEG/WEBP, transcode to PNG or JPEG before upload and re-detect MIME.
- If animated (GIF/APNG/animated WEBP), extract the first frame only.
- Resize large images to reasonable bounds to avoid oversized payloads.

## SwachhLens specifics
- AI model: `gemini-3-flash-preview` via emergentintegrations, key `EMERGENT_LLM_KEY`.
- Endpoint under test: `POST /api/reports` (auth required) — sends `image_base64`.
- Expected: server returns `ai_powered: true`, a `severity` 1-10, a `volume`, a
  `recommended_action`, and an `ai_summary` describing the scene.
- Fallback: if the key is missing or AI errors, server returns deterministic analysis
  with `ai_powered: false` (report creation must still succeed).
