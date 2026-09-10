# CivicAI

Hyperlocal civic issue reporting platform — citizens report potholes, waterlogging,
and garbage via photo + GPS; AI classifies, deduplicates, and prioritizes them for
municipal admins.

## Structure
- `backend/` — FastAPI, handles model inference, geocoding, duplicate detection, priority scoring
- `citizen-web/` — plain HTML/JS, public reporting page
- `admin-dashboard/` — Streamlit, admin map + heatmap view
- `model-training/` — Colab notebooks, not deployed
- `shared/` — database schema

## Deployment
- Backend → Render
- Citizen web → Vercel
- Admin dashboard → Streamlit Community Cloud
- Database + Storage → Supabase

See CivicAI_Build_Guide.md for the full step-by-step process.
