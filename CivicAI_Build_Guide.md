# CivicAI — Complete Build Guide

A step-by-step process from empty folder to deployed demo.

---

## Phase 0: Setup (Day 1)

1. Create a GitHub repo called `civicai` — everything lives here, all three platforms deploy straight from it.
2. Create the full folder structure locally:

```
civicai/
├── backend/
│   ├── main.py
│   ├── models/
│   │   └── classifier.py
│   ├── database.py
│   ├── duplicate_check.py
│   ├── priority_score.py
│   ├── geocode.py
│   └── requirements.txt
│
├── citizen-web/
│   ├── index.html
│   ├── report.html
│   ├── style.css
│   └── script.js
│
├── admin-dashboard/
│   ├── app.py
│   ├── .streamlit/
│   │   └── secrets.toml       (gitignored, never pushed)
│   └── requirements.txt
│
├── model-training/
│   ├── train_classifier.ipynb
│   ├── convert_model.py
│   └── dataset/                (gitignored, too large for GitHub)
│
├── shared/
│   └── schema.sql
│
├── .gitignore
└── README.md
```

3. Write `.gitignore` immediately (before your first commit), covering: `dataset/`, `.streamlit/secrets.toml`, `__pycache__/`, `.env`, `venv/`, `node_modules/`.
4. Create free accounts now, before you need them: Supabase, Render, Vercel, Streamlit Community Cloud, GitHub (already have), Google Colab.

---

## Phase 1: Database first (Day 1-2)

Everything else depends on this — do it before writing any app code.

1. Create a new Supabase project.
2. In Supabase's SQL editor, enable PostGIS: `create extension postgis;`
3. Run your `schema.sql` to create four tables: `users`, `wards`, `reports`, and optionally `issue_clusters`.
4. Get your ward boundary (Nagpur ward via OSM/Overpass Turbo, or trace manually on geojson.io as discussed) and insert it as a row in `wards`.
5. Manually create one test admin user directly in Supabase's Auth panel, tied to that ward — don't build the admin-creation UI, you don't need it for a demo.
6. Test: insert one dummy report row by hand, confirm it saves correctly with valid lat/lng.

---

## Phase 2: Model training (Day 2-5, run in parallel with Phase 3)

This can happen alongside backend/frontend work since it's on Colab, not blocking anything.

1. Collect images: 100-200 per class (pothole, waterlogging, garbage) from Kaggle + Roboflow Universe datasets, combined.
2. Fine-tune EfficientNetB0 in Colab — same pipeline you used for the cattle project (freeze base layers, train a new classification head, unfreeze partially if accuracy needs a boost).
3. Watch for the same normalization trap you hit before: don't manually divide by 255, EfficientNetB0's rescaling layer handles it internally.
4. Once validation accuracy is acceptable (aim for 80%+), export the model as `.h5` or `.keras`.
5. Keep it un-quantized this time — since inference runs server-side on your backend (not on-device like the Flutter cattle app), you don't need TFLite conversion. A regular Keras model loaded in FastAPI is simpler and fine.

---

## Phase 3: Backend (Day 2-7)

Build in this exact order — each piece depends on the one before it working.

1. `database.py` — Supabase client connection, test it can read/write.
2. `geocode.py` — function that calls Nominatim, takes lat/lng, returns address string.
3. Ward lookup function — a PostGIS query (`ST_Contains`) that takes lat/lng, returns matching `ward_id`.
4. `models/classifier.py` — loads your trained model once at startup, exposes a `predict(image)` function.
5. `priority_score.py` — the weighted formula function, takes confidence + duplicate_count + days_open + location_weight, returns a 0-1 score.
6. `duplicate_check.py` — geo-filter query first (PostGIS `ST_DWithin`), then CLIP embedding similarity only on the filtered candidates.
7. `main.py` — the actual FastAPI app, with your core endpoints:
   - `POST /upload-report` — ties together steps 2-6 into one flow
   - `GET /reports` — returns all reports (with optional filters) for the dashboard
   - `PATCH /reports/{id}` — lets admin update status
   - `POST /auth/login` — or just use Supabase Auth directly from frontend, skipping a custom endpoint
8. Test every endpoint locally with a tool like Postman or just `curl`, before touching any frontend.

---

## Phase 4: Citizen web app (Day 6-9)

1. `index.html` — login/signup form, calls Supabase Auth directly (no need to route through your backend for this part).
2. `report.html` — the core page:
   - `<input type="file" accept="image/*" capture="environment">` for camera/gallery
   - `navigator.geolocation.getCurrentPosition()` for GPS
   - a submit button that packages image + lat/lng into a request to your backend's `/upload-report`
3. `script.js` — handles the fetch call, shows upload progress, displays confirmation or error.
4. Style with plain CSS — keep it minimal, this doesn't need to be fancy, it needs to work reliably on a low-end Android browser.
5. Test the full loop yourself: take a real photo of something outside, submit it, confirm it lands correctly in Supabase with a ward match.

---

## Phase 5: Admin dashboard (Day 8-11)

You already have the working `app.py` from earlier in this conversation. From here:

1. Drop in your real Supabase credentials via `.streamlit/secrets.toml`.
2. Point `DEFAULT_LAT, DEFAULT_LNG` to your actual demo ward's center coordinates.
3. Test that reports submitted from the citizen web app in Phase 4 actually appear here after a refresh.
4. Add the status-update button (dropdown + submit) that calls your backend's `PATCH /reports/{id}` endpoint.
5. Polish: add the metric cards, filters, and table sorting shown in the code from before.

---

## Phase 6: Deployment (Day 11-13)

Deploy in this order — backend first, since both frontends depend on it being live.

1. **Backend → Render**: connect your GitHub repo, set root directory to `backend/`, set build command, add environment variables (Supabase keys) in Render's dashboard, deploy. Note the live URL it gives you (e.g. `civicai-backend.onrender.com`).
2. **Citizen web → Vercel**: connect repo, set root directory to `citizen-web/`, deploy as a static site. Update `script.js` to point at your live Render backend URL instead of `localhost`.
3. **Admin dashboard → Streamlit Community Cloud**: connect repo, set main file to `admin-dashboard/app.py`, add your Supabase secrets in Streamlit's secrets manager (same content as your local `secrets.toml`), deploy.
4. Test the entire loop end-to-end using only the live links — not localhost — exactly as faculty will see it.

---

## Phase 7: Polish + demo prep (Day 13-15)

1. Seed the database with 15-20 realistic-looking demo reports across your ward, at varied priority levels, so the heatmap and dashboard don't look empty on demo day.
2. Prepare a live walkthrough script: citizen reports a real pothole on your phone → switch to laptop → show it appear on the admin heatmap within seconds → click it → show AI category, confidence, priority score → change status → explain the duplicate-detection logic conceptually (don't need to demo a duplicate live unless you plan one).
3. Write your report/presentation framed around outcomes (faster municipal response, reduced duplicate effort, data-driven prioritization for authorities) before technical architecture.
4. Have a backup: screen-record the full working demo in advance, in case live wifi/GPS fails during presentation.

---

## Summary timeline

| Phase | Days | Depends on |
|---|---|---|
| Setup | 1 | — |
| Database | 1-2 | Setup |
| Model training | 2-5 | Setup (parallel with backend) |
| Backend | 2-7 | Database |
| Citizen web | 6-9 | Backend endpoints working |
| Admin dashboard | 8-11 | Backend endpoints working |
| Deployment | 11-13 | All three built |
| Polish + demo prep | 13-15 | Deployment |

~15 days total if worked steadily, compressible if you split backend and frontend work across your two-person team in parallel from Phase 3 onward.
